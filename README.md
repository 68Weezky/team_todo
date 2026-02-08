# Team Todo

A production-ready Django app for team task management with role-based access, dashboards, notifications, and analytics.

---

## About the project

**Team Todo** is a web application that helps teams plan work, assign tasks, and track progress in one place. It is built with Django and is suitable for small to medium teams (e.g. product, engineering, or support) that need a simple way to manage tasks by team and by person.

**What it does:** Administrators can register users and assign roles (Admin, Team Leader, or Team Member). Team leaders create teams, invite members, and create tasks that they assign to members. Members see their assigned tasks, update status (Not Started → In Progress → Review → Completed), add comments and attachments, and view their own dashboard and calendar. Leaders get a dashboard with charts (tasks by priority, completion trend, workload), upcoming deadlines, and recent activity. Everyone can search tasks and export data; leaders get team analytics and reports. The app can send in-app and email notifications for new assignments, status changes, comments, and deadlines, and it can run a daily check for overdue tasks and reminders.

**Tech stack:** Django 5, Bootstrap 5, Chart.js, FullCalendar; SQLite for development and PostgreSQL for production; optional deployment on Render with Gunicorn and WhiteNoise.

---

## Features

- **Roles**: Admin, Team Leader, Team Member (custom user model)
- **Auth**: Register, login, logout, password reset (email-based)
- **Teams**: Create/manage teams, add/remove members, leave team
- **Tasks**: CRUD, priority, status, due dates, assignees, comments, attachments
- **Dashboards**: Leader dashboard (charts, activity, deadlines), member dashboard (personal stats, calendar)
- **Notifications**: In-app bell + email (task assigned, status change, comment, deadline/overdue)
- **Analytics**: Team performance (date range, completion trend, productivity), personal stats, CSV/PDF export
- **Search**: Global task search with filters; export to CSV or PDF
- **Background**: `check_deadlines` management command (cron) for 24h and overdue notifications
- **UI**: Bootstrap 5, Chart.js, FullCalendar; responsive

---

## Prerequisites

- Python 3.10+
- pip
- PostgreSQL 12+ (production) or SQLite (development)
- Git

---

## Quick Start (Local)

```bash
cd team_todo
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: DEBUG=True, USE_POSTGRES=False for SQLite
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000/** and log in.

---

## Environment Variables

Copy `.env.example` to `.env` and set:

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret (change in production) | `your-secret-key` |
| `DEBUG` | Debug mode | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1,yourapp.onrender.com` |
| **Database** | | |
| `USE_POSTGRES` | Use PostgreSQL | `False` (SQLite) / `True` |
| `DB_NAME` | PostgreSQL database name | `team_todo_db` |
| `DB_USER` | PostgreSQL user | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | (your password) |
| `DB_HOST` | PostgreSQL host | `localhost` or Render internal host |
| `DB_PORT` | PostgreSQL port | `5432` |
| **Optional (Render)** | | |
| `DATABASE_URL` | Full Postgres URL (overrides DB_* if set) | `postgres://user:pass@host:5432/dbname` |
| **Email** | | |
| `EMAIL_BACKEND` | Backend | `django.core.mail.backends.console.EmailBackend` (dev) or `smtp` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_USE_TLS` | Use TLS | `True` |
| `EMAIL_HOST_USER` | SMTP user | your email |
| `EMAIL_HOST_PASSWORD` | SMTP password / app password | (your password) |
| `DEFAULT_FROM_EMAIL` | From address | `noreply@teamtodo.com` |
| **Other** | | |
| `CORS_ALLOWED_ORIGINS` | CORS origins (comma-separated) | `http://localhost:3000` |

---

## Project Structure

```
team_todo/
├── manage.py
├── requirements.txt
├── Procfile              # Render / Gunicorn
├── .env.example
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/users/
│   ├── models.py         # CustomUser, Team, Task, Notification, TaskActivity, etc.
│   ├── views.py          # Auth, profile
│   ├── team_views.py
│   ├── task_views.py     # Tasks, dashboards, analytics, search, export
│   ├── notification_views.py
│   ├── forms.py
│   ├── urls.py
│   └── management/commands/
│       ├── check_deadlines.py
│       ├── create_sample_teams.py
│       └── create_sample_tasks.py
├── templates/
└── static/
```

---

## Main URLs (under `/users/`)

| Page | URL |
|------|-----|
| Login / Register | `/users/login/`, `/users/register/` |
| Dashboard (role-based) | `/users/dashboard/` |
| Leader dashboard | `/users/dashboard/leader/` |
| Member dashboard | `/users/dashboard/member/` |
| Teams | `/users/teams/`, `/users/teams/<id>/` |
| Team tasks | `/users/teams/<id>/tasks/` |
| Task detail | `/users/teams/<id>/tasks/<id>/` |
| My tasks | `/users/my-tasks/` |
| Notifications | `/users/notifications/` |
| Team analytics | `/users/analytics/team/<id>/` |
| Personal stats | `/users/analytics/personal/` |
| Search | `/users/search/?q=...` |
| Export CSV | `/users/reports/export-csv/` |
| Export PDF | `/users/reports/export-personal-pdf/` |
| Admin | `/admin/` |

---

## Database: SQLite vs PostgreSQL

**Development (SQLite):** `USE_POSTGRES=False` in `.env`. No extra setup.

**Production (PostgreSQL):** `USE_POSTGRES=True` and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.  
On Render you can use `DATABASE_URL` instead (see below).

**Migrating data from SQLite to PostgreSQL:**

1. With SQLite active:  
   `python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --indent 2 -o sqlite_data.json`  
   (PowerShell: run as one line, no backslashes.)
2. Create Postgres DB and set `.env` for Postgres.
3. `python manage.py migrate`
4. `python manage.py loaddata sqlite_data.json`  
   (Ensure the JSON file is UTF-8; avoid saving it in Notepad as UTF-16.)

---

## Deadline Notifications (Cron)

Run daily to notify assignees for tasks due in 24h and overdue:

```bash
python manage.py check_deadlines
```

**Cron (Linux/macOS):**  
`0 8 * * * /path/to/venv/bin/python /path/to/team_todo/manage.py check_deadlines >> /var/log/team_todo_deadlines.log 2>&1`

**Render:** Use a **Cron Job** service; command: `python manage.py check_deadlines`, schedule daily.

---

## Email

- **Development:** `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` (logs to console).
- **Production:** Use SMTP (Gmail app password, SendGrid, Mailgun, etc.) and set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS=True`.

---

## Deploy on Render

### 1. Repo

Push code to GitHub (no `venv/`, `.env`, `db.sqlite3`, or `sqlite_data.json` in repo).

### 2. Render services

- **Web Service**: Django app.
- **PostgreSQL**: Database (create first, then link to Web Service).

### 3. Web Service settings

- **Build Command:**  
  `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start Command:** Either leave **blank** (Render uses the Procfile) or set:  
  `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`  
  Migrations run on every deploy so you don’t need a paid Shell to run them.
- **Root Directory:** Leave blank if `manage.py` is at repo root; if app is in `team_todo/`, set **Root Directory** to `team_todo`.

### 4. Environment variables (Render dashboard)

Set in Web Service → Environment:

- `DEBUG` = `False`
- `SECRET_KEY` = (generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `ALLOWED_HOSTS` = `yourapp.onrender.com` (optional on Render; the app auto-allows `RENDER_EXTERNAL_HOSTNAME`). Add this if you use a custom domain.
- `USE_POSTGRES` = `True`
- Either:
  - **Option A:** Add **PostgreSQL** as linked resource and set `DATABASE_URL` (Render sets it automatically), **or**
  - **Option B:** Set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` from the Render Postgres info.

Optional: `EMAIL_*` for production email.

### 5. First-time setup after deploy

Migrations run automatically on every deploy (see Procfile / Start Command). You do **not** need to run them manually.

- **Create an admin user:** Use Render **Shell** (if available) or run locally with `DATABASE_URL` or `DB_*` set to your Render Postgres:  
  `python manage.py createsuperuser`
- **Optional – load existing data:** If you have `sqlite_data.json`, upload it (e.g. via Shell) and run:  
  `python manage.py loaddata sqlite_data.json`

### 6. Cron Job (Render)

- New **Cron Job**; same repo and root directory.
- **Command:** `python manage.py check_deadlines`
- **Schedule:** `0 8 * * *` (daily 8:00 UTC) or as desired.

### 7. Static files

The app uses WhiteNoise to serve static files in production. No separate static server needed on Render.

---

## Production Checklist

- [ ] `DEBUG=False`
- [ ] New `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` includes your host(s)
- [ ] PostgreSQL in use; migrations applied
- [ ] Static: `collectstatic` in build; WhiteNoise in use
- [ ] Env vars set on host (no `.env` in repo)
- [ ] Gunicorn start command
- [ ] HTTPS (Render provides it)
- [ ] Cron for `check_deadlines`
- [ ] Email configured if you need notifications

---

## Troubleshooting

**"no such table: users_notification"**  
Run: `python manage.py migrate`

**"Team object has no attribute 'team'"**  
Fixed in code: use `task.team.name` or `team.name`, not `team.team.name`.

**UnicodeDecodeError on loaddata**  
Fixture must be UTF-8. Re-export with `dumpdata ... -o sqlite_data.json` and avoid editing in Notepad (or save as UTF-8).

**PostgreSQL connection refused**  
Check `DB_HOST`, `DB_PORT`, firewall; ensure Postgres is running and credentials match.

**Static files 404**  
Run `python manage.py collectstatic --noinput` and ensure WhiteNoise is in `MIDDLEWARE` (see settings).

**Permission denied**  
Ensure user role is set correctly in Admin (`/admin/`).

**400 Bad Request on Render**  
The app auto-adds Render’s host to `ALLOWED_HOSTS`. If you use a custom domain, add it in Environment: `ALLOWED_HOSTS=yourapp.onrender.com,yourdomain.com`.

**500 on register (or after deploy)**  
Migrations must run before the app serves traffic. Use the Start Command that includes `python manage.py migrate --noinput &&` (or leave Start Command blank so the Procfile is used).

---

## Tech Stack

- **Backend:** Django 5, Gunicorn
- **DB:** PostgreSQL / SQLite
- **Frontend:** Bootstrap 5, Chart.js, FullCalendar
- **APIs:** Django REST Framework
- **Static in prod:** WhiteNoise

---

## License

MIT.
