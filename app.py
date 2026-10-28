"""Student Registration System: Flask web tier with interchangeable SQLite/MySQL storage."""

import os
from datetime import datetime, timezone

import click
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm, CSRFProtect
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from wtforms import SelectField, StringField
from wtforms.validators import DataRequired, Length, Optional, Regexp


db = SQLAlchemy()
csrf = CSRFProtect()


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    registration_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(10), nullable=True)
    course = db.Column(db.String(50), nullable=False)
    study_year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)


class StudentForm(FlaskForm):
    registration_no = StringField(
        "Registration number",
        validators=[DataRequired(), Length(min=3, max=20), Regexp(r"^[A-Za-z0-9-]+$", message="Use only letters, numbers, and hyphens.")],
        render_kw={"placeholder": "e.g. CSE2026001", "maxlength": "20"},
    )
    full_name = StringField(
        "Full name", validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "e.g. Aarav Sharma", "maxlength": "100"},
    )
    email = StringField(
        "Email address",
        validators=[DataRequired(), Length(max=150), Regexp(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", message="Enter a valid email address.")],
        render_kw={"placeholder": "student@example.com", "type": "email", "maxlength": "150"},
    )
    phone = StringField(
        "Phone (optional)", validators=[Optional(), Regexp(r"^[0-9]{10}$", message="Enter a 10-digit phone number.")],
        render_kw={"placeholder": "10-digit number", "maxlength": "10", "inputmode": "numeric"},
    )
    course = SelectField(
        "Course", validators=[DataRequired()],
        choices=[("", "Select a course"), ("B.Tech CSE", "B.Tech CSE"),
                 ("B.Tech IT", "B.Tech IT"), ("B.Tech ETC", "B.Tech ETC"), ("B.Tech ECE", "B.Tech ECE"), ("BCA", "BCA"), ("MCA", "MCA"), ("Other", "Other")],
    )
    study_year = SelectField(
        "Year of study", validators=[DataRequired()], coerce=int,
        choices=[(0, "Select year"), (1, "1st Year"), (2, "2nd Year"), (3, "3rd Year"), (4, "4th Year")],
    )


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "local-dev-key-not-for-production"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///students.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    if os.getenv("FLASK_ENV") == "production":
        unsafe_secrets = {"local-dev-key-not-for-production", "change-this-to-a-long-random-secret-for-production"}
        if app.config["SECRET_KEY"] in unsafe_secrets or len(app.config["SECRET_KEY"]) < 32:
            raise RuntimeError("Use a unique random SECRET_KEY (32+ characters) for production.")
        # Secure cookies are only sent over HTTPS. Keep false while the demo runs on plain HTTP (port 80).
        app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

    db.init_app(app)
    csrf.init_app(app)

    # Create missing tables on startup (never drops data), so a skipped init-db step cannot crash the app.
    with app.app_context():
        db.create_all()

    @app.cli.command("init-db")
    def init_db():
        """Create missing tables in the configured database (does not delete rows)."""
        db.create_all()
        click.echo("Database tables are ready.")

    @app.get("/")
    def index():
        search = request.args.get("q", "").strip()[:100]
        query = Student.query
        if search:
            pattern = f"%{search}%"
            query = query.filter(or_(
                Student.full_name.ilike(pattern),
                Student.registration_no.ilike(pattern),
                Student.email.ilike(pattern),
            ))
        students = query.order_by(Student.id.desc()).all()
        total_students = db.session.query(Student).count()
        year_counts = dict(db.session.query(Student.study_year, func.count(Student.id)).group_by(Student.study_year).all())
        course_counts = db.session.query(Student.course, func.count(Student.id)).group_by(Student.course).order_by(func.count(Student.id).desc()).all()
        db_engine = "MySQL (AWS RDS)" if db.engine.dialect.name == "mysql" else "SQLite (local)"
        return render_template(
            "index.html", students=students, q=search, total_students=total_students,
            year_counts=year_counts, course_counts=course_counts, db_engine=db_engine,
        )

    @app.route("/students/new", methods=["GET", "POST"])
    def create_student():
        form = StudentForm()
        if form.validate_on_submit():
            student = Student(
                registration_no=form.registration_no.data.strip().upper(),
                full_name=form.full_name.data.strip(),
                email=form.email.data.strip().lower(),
                phone=(form.phone.data or "").strip() or None,
                course=form.course.data,
                study_year=form.study_year.data,
            )
            db.session.add(student)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Registration number or email already exists.", "error")
            else:
                flash("Student registered successfully!", "success")
                return redirect(url_for("index"))
        return render_template("form.html", form=form, title="Register a student", submit_label="Register student", mode="create")

    @app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
    def edit_student(student_id):
        student = db.get_or_404(Student, student_id)
        form = StudentForm(obj=student)
        if request.method == "GET":
            form.study_year.data = student.study_year
        if form.validate_on_submit():
            student.registration_no = form.registration_no.data.strip().upper()
            student.full_name = form.full_name.data.strip()
            student.email = form.email.data.strip().lower()
            student.phone = (form.phone.data or "").strip() or None
            student.course = form.course.data
            student.study_year = form.study_year.data
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Registration number or email already exists.", "error")
            else:
                flash("Student details updated successfully!", "success")
                return redirect(url_for("index"))
        return render_template("form.html", form=form, title="Edit student", submit_label="Save changes", mode="edit", student=student)

    @app.post("/students/<int:student_id>/delete")
    def delete_student(student_id):
        student = db.get_or_404(Student, student_id)
        db.session.delete(student)
        db.session.commit()
        flash("Student deleted successfully.", "success")
        return redirect(url_for("index"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
