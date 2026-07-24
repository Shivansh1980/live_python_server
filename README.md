# Downloadable Files API

A production-ready FastAPI service that dynamically lists and downloads files
stored directly in `downloadable_files/`.

## API

| Method | URL | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service links |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/files` | List currently available files |
| `GET` | `/api/v1/files/{filename}` | Download a file by its exact filename |
| `GET` | `/docs` | Interactive OpenAPI documentation |

Files added directly to `downloadable_files/` are discovered on every request.
No code or manifest update is required. Nested files and symbolic links are
intentionally excluded, and requested names cannot traverse outside that
directory.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs>.

## Add a downloadable file

Copy the file into `downloadable_files/`, commit it, and push. It will appear in
`GET /api/v1/files` after the deployed application is updated.

## PythonAnywhere deployment

These commands use PythonAnywhere's ASGI website support:

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

After later code updates:

```bash
cd ~/live_python_server
git pull
pa website reload --domain RyzenShivansh.pythonanywhere.com
```
