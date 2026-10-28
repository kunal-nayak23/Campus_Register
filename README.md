# AWS Student Registration System — Project #7

A working student registration application built with Flask. It provides **create, display, search, edit and delete** operations, and supports local SQLite development followed by a separate **AWS RDS MySQL** database in deployment.

## Features

- Register students: registration number, name, email, optional phone, course and study year.
- Show all records and the total number of students.
- Search by registration number, name, or email.
- Edit or delete an existing record.
- Input validation and duplicate registration/email checks.
- Server-side database persistence and CSRF-protected forms.

## User interface

Built with **Bootstrap 5.3** and Bootstrap Icons (loaded from the jsDelivr CDN, so the browser needs internet access).

- Dashboard with total count, year-of-study bar and per-course breakdown (click a course to filter).
- Instant search plus course and year filters, without reloading the page. Press `/` to jump to search.
- Sortable columns, a details drawer when you click a row, and a confirmation dialog before delete.
- Registration form with live validation, a live record preview and a progress bar for required fields.
- Toast notifications for success and errors, light/dark theme toggle, and a mobile-friendly layout.
- The badge on the dashboard shows which database is connected: `SQLite (local)` or `MySQL (AWS RDS)`. Useful as proof during the demo.

## Phase 1 — Run locally on Windows (PowerShell / VS Code Terminal)

Install **Python 3.10+** and open the `student-registration-aws` project folder in VS Code. Run these commands one at a time:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m flask --app app init-db
python -m flask --app app run --debug
```

The app also creates missing tables automatically on startup, so it will not crash with `no such table` if `init-db` was skipped.

Open **http://127.0.0.1:5000** in your browser.

If PowerShell blocks activating virtual environments, run the following commands **without activation**:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m flask --app app init-db
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

Or use Command Prompt:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
copy .env.example .env
python -m flask --app app init-db
python -m flask --app app run --debug
```

**The local SQLite database is saved at `instance/students.db`.** You can stop and restart Flask without losing records. SQLite is **only for local development**. The graded AWS demonstration must use an EC2-hosted application and **RDS MySQL**.

## Run functional tests

With the virtual environment active:

```powershell
python -m unittest discover -s tests -v
```

The tests use their own temporary SQLite database and do not modify your registration records.

## AWS deployment — Phase 2 onward (not yet done)

1. Create an RDS MySQL database named `student_registration`, with a dedicated DB user (`studentapp`).
2. Create an EC2 instance in the **same VPC** as RDS.
3. Keep RDS **private**, and allow its inbound MySQL TCP port **3306 only from the EC2 security group**.
4. Create `.env` on EC2 with a random `SECRET_KEY`, set `FLASK_ENV=production`, and define:

   ```env
   DATABASE_URL=mysql+pymysql://studentapp:URL_ENCODED_PASSWORD@RDS_ENDPOINT:3306/student_registration?charset=utf8mb4
   ```

   If the MySQL password has special characters, URL-encode it. Do not commit `.env` to Git. Never use placeholder passwords in deployment.
5. Install dependencies using `requirements-prod.txt` and run `python -m flask --app app init-db` **after RDS is reachable**.
6. Run the app behind Gunicorn and a properly configured Nginx reverse proxy. HTTPS and access controls are needed before public internet exposure.
7. Create a student, restart EC2, load the app again, and verify the student record is still in RDS. Show it using a SELECT query as evidence.

**Do not expose RDS port 3306 publicly** and do not open SSH to all IPs. Stop or delete chargeable AWS resources after the demo, after saving any necessary evidence.

## Project structure

```text
student-registration-aws/
├── app.py                 Flask routes, model, validation, database configuration
├── wsgi.py                Gunicorn entry point for AWS
├── requirements.txt       Local dependencies
├── requirements-prod.txt  Linux production dependencies
├── .env.example           Environment variable template
├── .gitignore             Excludes secrets and local database
├── templates/
│   ├── base.html
│   ├── index.html
│   └── form.html
├── static/
│   └── style.css
└── tests/
    └── test_app.py
```

## Why separate EC2 and RDS?

EC2 runs application code, while RDS stores the database on its own managed service. Restarting/replacing EC2 does not erase data already committed to RDS. It also allows different access permissions, backups, scaling, and maintenance for the application and database tiers. **An EC2 restart alone is evidence of separation, not proof of backups or high availability.**

## Demonstration checklist

- [ ] Student registration form submits and saves a record.
- [ ] Dashboard shows the new record and student count.
- [ ] Edit and delete work correctly.
- [ ] Invalid values and duplicate registrations are rejected.
- [ ] EC2 hosts the live application.
- [ ] MySQL RDS is configured and application connections succeed.
- [ ] Restart EC2 and confirm the existing student remains in RDS.
- [ ] Show RDS MySQL query and security-group configuration.
- [ ] Explain architecture, persistence, and why separate tiers are useful.

**Current completion:** Phase 1 (local project). AWS EC2/RDS creation and cloud demonstration remain to be done.
