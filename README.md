# CurvatureTech FastAPI service

A production-ready FastAPI backend for the CurvatureTech contact form, secure
file downloads, and a lightweight administration portal.

## Features

- Contact enquiries are validated, rate limited, and saved to SQLite.
- Optional Discord webhook and Gmail SMTP notifications are failure-isolated;
  an unavailable notification provider never loses the saved enquiry.
- A signed-session admin portal manages enquiries and downloadable files.
- Files are discovered dynamically from `media/downloadable_files/`.
- Nested paths, symlinks, traversal attempts, and duplicate uploads are blocked.
- Application construction, persistence, notifications, and business logic are
  separated behind small interfaces so additional APIs and providers can be
  added without rewriting existing routes.

## API

| Method | URL | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service links |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/contact` | Save a contact enquiry |
| `GET` | `/api/v1/files` | List downloadable files |
| `GET` | `/api/v1/files/{filename}` | Download an exact filename |
| `GET` | `/admin` | Administration portal |
| `GET` | `/docs` | Interactive OpenAPI documentation |

### Contact request

`POST /api/v1/contact` accepts JSON:

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "company": "Analytical Engines",
  "projectType": "Web app or SaaS product",
  "budget": "$8k–$20k",
  "message": "We would like to discuss a new client portal."
}
```

Successful requests return HTTP `201`:

```json
{
  "id": 1,
  "status": "received",
  "message": "Thank you. Your enquiry has been received."
}
```

The optional `company`, `projectType`, and `budget` fields may be empty. `name`,
`email`, and `message` are required. A hidden field named `website` may be sent
as a honeypot and must remain empty for human submissions.

Frontend example:

```js
const response = await fetch(
  "https://ryzenshivansh.pythonanywhere.com/api/v1/contact",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      email,
      company,
      projectType,
      budget,
      message,
      website: "",
    }),
  },
);

const result = await response.json();
if (!response.ok) {
  throw new Error(result.detail ?? "Unable to send your message.");
}
```

## Configuration

Copy `.env.example` to `.env` and replace the placeholders. `.env` is ignored
by Git and must never be committed.

```dotenv
APP_ENV=development
ADMIN_USERNAME=replace-with-admin-username
ADMIN_PASSWORD="replace-with-a-strong-password"
SESSION_SECRET="replace-with-a-long-random-value"
CORS_ALLOWED_ORIGINS="http://localhost:3000,https://your-frontend.example"

DISCORD_WEBHOOK_URL=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_APP_PASSWORD=
NOTIFICATION_EMAIL_TO=
```

Notification providers are optional. A contact is always stored in SQLite even
when no provider is configured or a provider is temporarily unavailable.

### Discord

In Discord, open the destination channel's **Edit Channel → Integrations →
Webhooks**, create a webhook, copy its URL, and store it as
`DISCORD_WEBHOOK_URL`.

### Gmail

Enable 2-Step Verification on the sending Google account, create an App
Password, then configure:

```dotenv
SMTP_USERNAME=sender@gmail.com
SMTP_APP_PASSWORD="the-16-character-app-password"
NOTIFICATION_EMAIL_TO=recipient@example.com
```

Do not use or store the normal Google account password.

### WhatsApp

No unofficial browser automation is included. The official WhatsApp Business
Platform uses per-message pricing outside its free service-message conditions,
so it is intentionally not used for owner notifications from this form. A
future provider can implement the `ContactNotifier` interface without changing
the contact endpoint.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and
`http://127.0.0.1:8000/admin`.

The committed `data/app_seed.db` contains only the empty schema. On first
startup it is copied to the ignored runtime database `data/app.db`. Contact
data therefore survives application restarts but is not committed.

## Downloadable files

Add files through the admin portal or directly to
`media/downloadable_files/`. The API discovers the current contents on every
request; no manifest or restart is needed. Commit a file only when it should be
part of every deployment.

## PythonAnywhere deployment

Create the production `.env` at
`/home/RyzenShivansh/live_python_server/.env`, set `APP_ENV=production`, and use
a fresh `SESSION_SECRET`.

```bash
cd ~
git clone https://github.com/Shivansh1980/live_python_server.git
python3.10 -m venv ~/.virtualenvs/live_python_server
~/.virtualenvs/live_python_server/bin/python -m pip install -r \
  ~/live_python_server/requirements.txt
pip install --upgrade pythonanywhere
pa website create \
  --domain RyzenShivansh.pythonanywhere.com \
  --command '/home/RyzenShivansh/.virtualenvs/live_python_server/bin/uvicorn --app-dir /home/RyzenShivansh/live_python_server --uds ${DOMAIN_SOCKET} app.main:app'
```

For later releases:

```bash
cd ~/live_python_server
git pull --ff-only
~/.virtualenvs/live_python_server/bin/python -m pip install -r requirements.txt
pa website reload --domain RyzenShivansh.pythonanywhere.com
```
