"""Functional checks using an isolated temporary database (no AWS account needed)."""
import os
import tempfile
import unittest

from app import Student, create_app, db


class StudentAppTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        db_file = os.path.join(self.directory.name, "test.db").replace("\\", "/")
        self.app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
        })
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.directory.cleanup()

    def student_data(self, **overrides):
        data = {
            "registration_no": "CSE2026001",
            "full_name": "Aarav Sharma",
            "email": "aarav@example.com",
            "phone": "9876543210",
            "course": "B.Tech CSE",
            "study_year": "3",
        }
        data.update(overrides)
        return data

    def add_student(self, **overrides):
        return self.client.post("/students/new", data=self.student_data(**overrides), follow_redirects=True)

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Dashboard", response.data)

    def test_insert_and_display(self):
        response = self.add_student()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student registered successfully!", response.data)
        self.assertIn(b"Aarav Sharma", response.data)
        with self.app.app_context():
            self.assertEqual(db.session.query(Student).count(), 1)

    def test_duplicate_registration_rejected(self):
        self.add_student()
        response = self.add_student(email="another@example.com")
        self.assertIn(b"already exists", response.data)
        with self.app.app_context():
            self.assertEqual(db.session.query(Student).count(), 1)

    def test_invalid_phone_rejected(self):
        response = self.add_student(phone="123")
        self.assertIn(b"10-digit phone number", response.data)
        with self.app.app_context():
            self.assertEqual(db.session.query(Student).count(), 0)

    def test_edit(self):
        self.add_student()
        with self.app.app_context():
            sid = db.session.query(Student).first().id
        response = self.client.post(f"/students/{sid}/edit", data=self.student_data(full_name="Aarav S."), follow_redirects=True)
        self.assertIn(b"updated successfully", response.data)
        self.assertIn(b"Aarav S.", response.data)

    def test_search(self):
        self.add_student()
        self.assertIn(b"Aarav Sharma", self.client.get("/?q=Aarav").data)
        self.assertNotIn(b"Aarav Sharma", self.client.get("/?q=nonmatching").data)

    def test_delete(self):
        self.add_student()
        with self.app.app_context():
            sid = db.session.query(Student).first().id
        response = self.client.post(f"/students/{sid}/delete", follow_redirects=True)
        self.assertIn(b"deleted successfully", response.data)
        with self.app.app_context():
            self.assertEqual(db.session.query(Student).count(), 0)

    def test_get_delete_not_allowed(self):
        self.add_student()
        with self.app.app_context():
            sid = db.session.query(Student).first().id
        self.assertEqual(self.client.get(f"/students/{sid}/delete").status_code, 405)

    def test_database_persists_between_app_instances(self):
        self.add_student()
        second_app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": self.app.config["SQLALCHEMY_DATABASE_URI"],
        })
        with second_app.app_context():
            self.assertEqual(db.session.query(Student).count(), 1)


if __name__ == "__main__":
    unittest.main()
