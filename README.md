# CurvatureTech FastAPI service

A production-ready FastAPI backend for the CurvatureTech contact form, secure
file downloads, and a lightweight administration portal.

## Features

- Contact enquiries are validated, rate limited, and saved to SQLite.
- Optional Discord webhook and Gmail SMTP notifications are failure-isolated;
  an unavailable notification provider never loses the saved enquiry.
- A signed-session admin portal manages enquiries and downloadable files.
- Anonymous website interaction analytics can be paused or resumed by an admin.
- Analytics records page views, clicks, focus, scrolling, section visibility,
  and engagement without typed values, cookies, or IP addresses.
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
| `POST` | `/api/v1/analytics/events` | Record an anonymous website action |
| `GET` | `/api/v1/payloadconfig/?user_ip_address={ip}` | Get the newest active payload configuration for an IP |
| `POST` | `/api/v1/payloadconfig/` | Update replacement for one user or every row |
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

### Analytics event request

`POST /api/v1/analytics/events` accepts one event per request:

```json
{
  "sessionId": "f14a8cb8-0f59-497a-a87a-c32d862923e2",
  "eventType": "section_view",
  "pageUrl": "https://example.com/services?campaign=summer",
  "pageTitle": "Services",
  "section": "ai-integration",
  "elementTag": "section",
  "elementId": "ai-integration",
  "elementLabel": "AI integration",
  "durationMs": 12800,
  "scrollDepth": 72.5,
  "pointerX": 44.2,
  "pointerY": 61.8,
  "viewportWidth": 1440,
  "viewportHeight": 900,
  "occurredAt": "2026-07-25T12:00:00Z",
  "metadata": {
    "source": "navigation",
    "visible": true
  }
}
```

Allowed `eventType` values are `page_view`, `navigation`, `click`, `focus`,
`blur`, `scroll`, `section_view`, and `engagement`. Only `sessionId`,
`eventType`, and `pageUrl` are required. URL query strings and fragments are
removed before storage.

The endpoint returns HTTP `202`:

```json
{"recorded": true, "event_id": 1, "reason": "recorded"}
```

When the admin pauses collection, the same endpoint returns:

```json
{"recorded": false, "event_id": null, "reason": "recording_disabled"}
```

Generate `sessionId` with `crypto.randomUUID()` and retain it in
`sessionStorage`, not a cookie. Never send input values or typed text. The API
also rejects metadata keys associated with passwords, tokens, cookies, email,
phone numbers, messages, and payment-card data.

### Payload configuration

Payload configuration fields use `snake_case` consistently in the database and
API. `GET /api/v1/payloadconfig/` requires a `user_ip_address` query parameter
and returns the newest active matching row:

```http
GET /api/v1/payloadconfig/?user_ip_address=203.0.113.10
```

```json
{
  "id": 4,
  "should_replace_payload": false,
  "url": "https://example.com/resource",
  "remote_host": "edge.example.com",
  "remote_port": 443,
  "user_ip_address": "203.0.113.10",
  "user_host_name": "workstation-10",
  "is_active": true,
  "created_at": "2026-07-28T10:00:00Z",
  "updated_at": "2026-07-28T10:00:00Z"
}
```

`POST /api/v1/payloadconfig/` changes `should_replace_payload`:

```json
{
  "user_ip_address": "203.0.113.10",
  "should_replace_payload": true
}
```

Selection precedence is:

1. `user_ip_address`: update the newest active row for that IP.
2. Otherwise `user_host_name`: update the newest active row for that hostname.
3. Neither identifier: update every row, including inactive rows.

`should_replace_payload` defaults to `false` when omitted. An empty request
body therefore sets every row to `false`. If both identifiers are provided,
`user_ip_address` takes precedence. A targeted update returns HTTP `404` when
no active match exists. All rows are also editable from `/admin/payload-configs`.

## Configuration

Copy `.env.example` to `.env` and replace the placeholders. `.env` is ignored
by Git and must never be committed.

```dotenv
APP_ENV=development
ADMIN_USERNAME=replace-with-admin-username
ADMIN_PASSWORD="replace-with-a-strong-password"
SESSION_SECRET="replace-with-a-long-random-value"
CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,https://your-frontend.example"

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

The committed `data/app_seed.db` contains only the empty schema and the default
analytics collection setting. On first startup it is copied to the ignored
runtime database `data/app.db`. Contact and analytics data therefore survive
application restarts but are not committed.

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
