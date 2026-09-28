# Global Link Flask deployment

Target domain: https://globallink.co.in
Prepared: 9 September 2026. This package contains the Flask admin website and /api backend only.

## Hosting compatibility — read first

Hostinger currently documents **Web Apps Hosting as a Node.js runtime** and **Flask/Python as requiring VPS hosting**. Therefore this ZIP is ready for a Python-capable Linux VPS setup, including Hostinger VPS; it is not a supported drop-in upload to the standard Node.js Web Apps product. A ZIP upload alone cannot add a Python runtime. No live deployment or domain/DNS change has been performed.

Official sources checked on 9 September 2026:
- https://www.hostinger.com/web-apps-hosting (Custom Node.js apps)
- https://www.hostinger.com/support/which-programming-languages-and-frameworks-are-supported-at-hostinger/ (Python/Flask requires VPS)

If your particular Hostinger plan explicitly offers a Python runtime, configurable start commands and persistent storage, confirm those capabilities with Hostinger before using the commands below. Otherwise use a Linux VPS and reverse proxy.

## 1. Python version

Use **CPython 3.14.x**; the existing backend tests passed on **3.14.5**. The package includes `.python-version` with `3.14`. Production dependency resolution was checked against Linux x86_64 Python 3.14 wheels (glibc 2.28+). Gunicorn requires Linux/Unix; the local development machine is Windows.

## 2. Build/install command

Extract the ZIP into a private application directory, for example `/srv/globallink/app`, not a publicly served document root. Files such as `wsgi.py` and `requirements.txt` are at the ZIP root.

Create a server-side virtual environment once:

```sh
python3.14 -m venv /srv/globallink/venv
```

From the extracted application directory, with that environment activated, the exact build/install command is:

```sh
python -m pip install --no-cache-dir -r requirements.txt
```

No frontend build, Node.js install, Flutter SDK or Flutter source is required. The packaged requirements include Flask, Flask-SQLAlchemy, Flask-JWT-Extended, python-dotenv, Pillow, SQLAlchemy, Werkzeug, Gunicorn, Psycopg and PyMySQL with RSA authentication support. Transitive dependencies are installed by pip. Pytest is intentionally absent from production requirements; the local development requirements and tests remain untouched.

## 3. Production entry point and exact start command

Working directory: the extracted ZIP root. WSGI entry point: **`wsgi:application`**.

With the environment activated:

```sh
gunicorn --config gunicorn.conf.py wsgi:application
```

Equivalent absolute service command for the example directory:

```sh
/srv/globallink/venv/bin/gunicorn --chdir /srv/globallink/app --config gunicorn.conf.py wsgi:application
```

Run this through a service manager configured to restart on failure and start after reboot. Do not use `python app.py` or Flask's development server in production. Gunicorn defaults to `127.0.0.1:8000`, one worker and four threads. Logs go to stdout/stderr for the service manager; there are no bundled log files.

## 4. Environment variables

Set these in a private host environment/secret manager before importing the WSGI application. Do not paste real values into source, this guide, public files, or ZIP archives.

| Variable | Required | Meaning |
|---|---|---|
| `SECRET_KEY` | Yes | Independently generated random session-signing secret, at least 32 characters. |
| `JWT_SECRET_KEY` | Yes | Different independently generated random JWT-signing secret, at least 32 characters. |
| `DATABASE_URL` | Yes | SQLAlchemy URL for the production database; examples below. |
| `UPLOAD_FOLDER` | Yes | Absolute writable persistent directory for uploaded photos, outside the release directory and public web root. |
| `PORT` | No | Gunicorn port; default `8000`. |
| `BIND_HOST` | No | Default `127.0.0.1` behind a local reverse proxy. Use `0.0.0.0` only when a container/platform explicitly requires it and provides network isolation. |
| `WEB_CONCURRENCY` | No | Worker count; default `1`. Keep one worker for the initial SQLite deployment. |
| `MAX_CONTENT_LENGTH` | No | Existing request body limit in bytes; default `8388608` (8 MiB). |

Generate each signing secret privately, independently, using a cryptographically secure generator (for example Python's `secrets.token_hex(32)`). Keep the same values across workers, restarts and redeployments. Rotating them invalidates existing sessions. No values are supplied in the package.

The production adapter forces debug mode off and secure session cookies on. No JWT expiry, role checks, route handlers or API payloads are changed. Use HTTPS for browser sessions; HTTP local smoke checks do not exercise secure-cookie login.

## 5. Database configuration and first deployment

Choose one database. These examples contain placeholders, not credentials:

- SQLite: `sqlite:////var/lib/globallink/field_manager.db` (four slashes for an absolute Linux path).
- PostgreSQL: `postgresql+psycopg://<user>:<url-encoded-password>@<host>:5432/<database>?sslmode=require`
- MySQL: `mysql+pymysql://<user>:<url-encoded-password>@<host>:3306/<database>?charset=utf8mb4`

Use an absolute persistent SQLite path, never a relative database path in a replaceable release. PostgreSQL and MySQL drivers are included; supply provider-specific TLS/certificate options through the SQLAlchemy URL. URL-encode special characters in credentials. Create the database and least-privilege application database user outside this package. Ensure database connectivity and back up the database before release changes.

For a **new, empty production database**, after setting the required environment variables:

```sh
python manage_production.py init-db
python manage_production.py create-admin
```

`init-db` creates missing tables using the existing models and inserts missing role definitions. It does not drop tables or load demo records. `create-admin` prompts interactively for a unique username, employee code, display name and password; password input is hidden and hashed through the existing User model. It will not overwrite an existing account. These are explicit deployment operations and were not run against the local project database.

For an existing production database, restore/migrate it through a separate controlled process before starting the application. `create_all()` does not migrate existing columns. No local SQLite database, user accounts, demo seed script, photos or test data are included in this ZIP. Never run the local demo seed script in production: it is deliberately excluded because it drops tables and creates demo credentials.

The package's routes/models are unchanged. SQLite tests passed; PostgreSQL/MySQL production connectivity and database-specific behavior still require validation against your selected server.

## 6. Persistent uploaded-photo storage

Provision, for example, `/var/lib/globallink/uploads` and set `UPLOAD_FOLDER` to that absolute path. The service account must be able to create/read/write files there. Keep it across restarts and deploys and back it up together with the database. All instances need the same shared filesystem if horizontally scaled. The application currently uses filesystem storage; a remote object-store URL is not a supported upload-directory value.

Do **not** expose this directory through a public Nginx alias or static file server. Existing authenticated photo routes enforce access rules and must serve these files. Existing photo references require their original files to be transferred separately through a secure migration process.

The unchanged app startup also creates local `instance/` and `uploads/` directories. Allow the service account to create these directories in its private application directory. Production photo writes use `UPLOAD_FOLDER` after the adapter is loaded. Existing security provisioning can write `instance/security.json`; explicit required environment secrets take precedence. Do not serve, package or rely on that generated file for production secrets.

## 7. Domain, reverse proxy and health check

Point `globallink.co.in` to the selected VPS, configure HTTPS, and reverse-proxy **all paths unchanged** to Gunicorn. The Flask root redirects to the admin login; the same origin serves both the website and `/api`. Do not rewrite `/api` away.

Example Nginx location inside your TLS-enabled server block:

```nginx
server_name globallink.co.in;
client_max_body_size 8m;
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 130s;
}
```

TLS certificate directives and HTTP-to-HTTPS redirect belong to your server configuration. Keep the Gunicorn port private. Serve public static assets through Flask initially; never expose the application directory, environment files or uploaded photos directly. Admin templates retain their existing Bootstrap CDN link and Global Link logo/static assets.

- **Health-check URL:** `https://globallink.co.in/health`
- Expected health result: HTTP 200 JSON with `success: true`.
- Admin login: `https://globallink.co.in/admin/login`
- API base: `https://globallink.co.in/api`

`/health` is the existing liveness endpoint; it does not test database readiness. Also verify authenticated login, admin rendering, database reads and authorized photo retrieval after deployment. No mobile API configuration was changed.

## Packaging and validation

Local deployment sources live under `deployment/hostinger/`. `scripts/package_hostinger_backend.py` assembles `dist/globallink_hostinger_backend.zip` from a runtime allowlist. It runs backend tests before creating the archive.

Only two packaging-time source sanitizations are made: remove the unused development TestConfig class from the packaged config, and clear the prefilled demo username/password in the packaged admin login form. Local versions remain unchanged. No API contracts, models, security checks or business logic are altered.

Excluded: Flutter source, venv, caches, bytecode, tests, fixtures, logs, local databases/backups, uploads, `.env` files, signing secrets and demo seed scripts. This guide is also included in the archive. Production database contents and secrets must be supplied separately by the operator.
