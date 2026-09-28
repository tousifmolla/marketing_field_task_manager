"""Production-only WSGI adapter; the existing Flask routes are unchanged."""
import os
from pathlib import Path

for key in ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "UPLOAD_FOLDER"):
    if not os.environ.get(key, "").strip():
        raise RuntimeError(f"Required production environment variable is missing: {key}")
for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
    value = os.environ[key]
    if len(value) < 32 or value.startswith(("dev-", "replace-", "test-")):
        raise RuntimeError(f"Set {key} to an independently generated random secret (32+ characters)")
if os.environ["SECRET_KEY"] == os.environ["JWT_SECRET_KEY"]:
    raise RuntimeError("Use independent session and JWT secrets")
uploads = Path(os.environ["UPLOAD_FOLDER"])
if not uploads.is_absolute():
    raise RuntimeError("UPLOAD_FOLDER must be an absolute persistent directory")
uploads.mkdir(parents=True, exist_ok=True)

from app import app as application
application.config.update(UPLOAD_FOLDER=str(uploads), DEBUG=False, SESSION_COOKIE_SECURE=True)
