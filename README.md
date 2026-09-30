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

The saved model file is written to `backend/artifacts/`, or to Vercel Blob when `BLOB_READ_WRITE_TOKEN` is set.

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

### Vercel

`vercel.json` deploys both parts as one Vercel project with two services on one domain:

- `backend` (Django) receives every request under `/api/`, which matches the API's `/api/v1/` routes.
- `frontend` (Vite) serves everything else. Page reloads on routes such as `/students` fall back to `index.html`.

The browser calls the API at the relative path `/api/v1`, so previews and production each talk to their own backend.

Vercel's own hostnames are added to `ALLOWED_HOSTS` automatically, debug mode defaults to off, and password-reset links use the domain the request arrived on.

#### 1. Database (Aiven for MySQL)

The Docker database only exists on your computer, so production needs a hosted MySQL 8.

1. Create an account at [aiven.io](https://aiven.io), then create a **MySQL** service on the free plan in a region close to your Vercel region.
2. When the service is running, its overview page shows the host, port, user (`avnadmin`), password and database (`defaultdb`). Download the **CA certificate** from the same page.
3. Apply the schema from your computer, reading the values from the overview page:

   ```bash
   cd backend
   DB_HOST=<host> DB_PORT=<port> DB_USER=avnadmin DB_PASSWORD='<password>' DB_NAME=defaultdb \
   DB_SSL_CA=~/Downloads/ca.pem python manage.py migrate
   ```

4. Create your own administrator with `createsuperuser` using the same variables. Avoid `seed_sample_data` on a public deployment: it creates accounts whose shared password is printed in this README.

#### 2. Model storage (Vercel Blob)

Vercel functions cannot keep files, so trained models are stored in Vercel Blob. In the Vercel project, open **Storage**, create a **Blob** store with **private** access, and connect it to the project. Vercel adds `BLOB_READ_WRITE_TOKEN`, and from then on every training run uploads its model there. Without the token, models are saved to `backend/artifacts/` as before.

After the first deploy, sign in as an administrator and train the model from **Analytics**. If you train from your computer against the production database instead, set `BLOB_READ_WRITE_TOKEN` in your shell too, or the deployed backend will not find the model file.

#### 3. Environment variables

Set these for the Production and Preview environments:

- `DJANGO_SECRET_KEY`: required. The backend refuses to start on Vercel without it.
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: from the Aiven overview page.
- `DB_SSL_CA_PEM`: the full text of the Aiven CA certificate, including the `BEGIN` and `END` lines. The backend writes it to `/tmp` and verifies the database server with it.
- `BLOB_READ_WRITE_TOKEN`: added for you when the Blob store is connected.
- Optional: `DJANGO_ALLOWED_HOSTS` for a custom domain, and SMTP settings via `EMAIL_BACKEND`.

Test both services together locally with `vercel dev`.

### Your own server

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
