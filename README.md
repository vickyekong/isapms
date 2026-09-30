# Intelligent Student Academic Performance Monitoring System

Web application for a Nigerian university setting. It keeps student records, attendance, and results in one place, flags students who may need support, and uses a scikit-learn decision tree to estimate grades.

The sample institution is **Nexus State University**. Every seeded record is marked as sample data.

Predictions are decision support only. They do not replace professional academic judgement and they are not final results.

## What you need

- Python 3.11 or newer
- Node.js 18 or newer
- Docker Desktop, used to run MySQL 8

## First-time setup

From the project folder:

```bash
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example backend/.env
cd frontend && cp .env.example .env && cd ..
```

The Docker database and `.env.example` share a placeholder password so this works as written on your own computer. To use a different one, run `export DB_PASSWORD=your-password` before the first `docker compose up -d`, and put the same value in `backend/.env`.

Create the database tables and sample records:

```bash
cd backend
python manage.py migrate
python manage.py seed_sample_data
```

Start the API:

```bash
python manage.py runserver
```

In a second terminal, start the interface:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Sample sign-in

All sample passwords are `Sample@12345`.

| Role | Identifier |
| --- | --- |
| Administrator | `sample.admin@nexusstate.edu.ng` |
| Lecturer | `sample.lecturer01@nexusstate.edu.ng` |
| Student | `sample.student001@nexusstate.edu.ng` |

Students and lecturers can also sign in with a matriculation number or staff ID, for example `NSU/SAMPLE/2023/001`.

Change these passwords before any real deployment. The seed command can be run again; it replaces previous sample records and retrains the model.

## Everyday commands

```bash
# Backend tests (SQLite, no MySQL required)
cd backend && python manage.py test

# Frontend tests
cd frontend && npm test

# Browser journeys (both servers and sample data must be running)
cd frontend && npx playwright install chromium && npm run test:e2e
```

API reference: [http://localhost:8000/api/v1/docs/](http://localhost:8000/api/v1/docs/)

## Roles

- **Administrator:** users, students, lecturers, faculties, departments, sessions, courses, enrolments, all records, predictions, reports, and settings.
- **Lecturer:** assigned courses, enrolment into those courses, attendance, scores, course predictions, at-risk students, and course reports.
- **Student:** own profile, courses, attendance, results, permitted predictions, alerts, and personal reports.

The React routes hide pages by role. The API enforces the same limits, so hiding a menu is not the only protection.

## Grading

The default scale is A 70–100, B 60–69, C 50–59, D 45–49, and F below 45, on a 5-point grade-point scale. Continuous assessment is capped at 40 and the examination at 60. An administrator can change the scale, caps, and attendance threshold under Settings.

Semester GPA and cumulative GPA are credit-weighted from results stored in the system. Prior CGPA is the student's standing before those results.

## Predictions

The model is a `DecisionTreeClassifier`. Features are attendance percentage, continuous assessment, examination score, number of registered courses, previously failed courses, previous CGPA, and historical average score.

- A and B are low risk.
- C is medium risk.
- D and F are high risk.

Training uses a stratified train/test split and records accuracy, precision, recall, F1-score, and a confusion matrix. If a student has no usable records, the API returns a clear message instead of a guess. A missing examination score can still produce a partial prediction, and the screen says the data was incomplete.

The sample model reports about 100% accuracy because the seed grades are calculated directly from the same continuous assessment and examination scores used as features. That figure describes the sample dataset. Predictions made before an examination score exists are marked partial and are the early-warning case.

Retrain from Analytics, or with:

```bash
python manage.py seed_sample_data
```

The saved model file is written to `backend/artifacts/`.

## Reports

Reports can be filtered by session, semester, faculty, department, level, course, student, and risk level, then downloaded as PDF, Excel, or CSV.

## Project layout

```text
backend/     Django 5, Django REST Framework, Simple JWT, MySQL
frontend/    React 18, Vite, Tailwind, Recharts, Axios
docker-compose.yml
```

Main API prefix: `/api/v1/`.

## Deployment

1. Set `DJANGO_DEBUG=False` and replace `DJANGO_SECRET_KEY`, database password, and `DJANGO_ALLOWED_HOSTS`.
2. Point `CORS_ALLOWED_ORIGINS` and `FRONTEND_URL` at the public site.
3. Use a managed MySQL 8 database. Do not commit `.env`.
4. Run `python manage.py migrate` and `python manage.py collectstatic`.
5. Serve Django with Gunicorn behind HTTPS, for example `gunicorn config.wsgi:application --bind 0.0.0.0:8000`.
6. Build the interface with `npm run build` and serve `frontend/dist` from Nginx or another static host.
7. Configure SMTP instead of the console email backend so password reset messages leave the server.
8. Keep `SECURE_SSL_REDIRECT` enabled in production. The project turns secure cookies and HSTS on when debug is off.

Do not train the model on identifiable student data outside an approved institutional environment. The included dataset is simulated.

## Tests cover

Administrator login, student registration, lecturer creation, course assignment, enrolment, attendance, score upload, grade calculation, prediction, at-risk identification, dashboards, reports, and role restrictions.
