"""Build a tested, allowlisted production archive without touching local app files."""
import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DEPLOY = ROOT / "deployment" / "hostinger"

def main():
    # A failed regression prevents creating or replacing the release archive.
    subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")], cwd=ROOT, check=True)
    files = {}
    sources = [BACKEND / name for name in ("app.py", "config.py", "extensions.py")]
    for folder in ("models", "routes", "services", "middleware", "utils"):
        sources.extend(sorted((BACKEND / folder).glob("*.py")))
    for folder in ("templates", "static"):
        sources.extend(sorted(p for p in (BACKEND / folder).rglob("*")
                              if p.is_file() and p.suffix.lower() in (".html", ".css", ".js", ".jpeg", ".jpg", ".png", ".svg", ".ico", ".woff", ".woff2")))
    originals = {p: p.read_bytes() for p in sources}
    for p, content in originals.items():
        name = p.relative_to(BACKEND).as_posix()
        if name == "config.py":
            text = content.decode("utf-8")
            tree = ast.parse(text)
            test_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "TestConfig")
            lines = text.splitlines(keepends=True)
            del lines[test_class.lineno - 1:test_class.end_lineno]
            content = "".join(lines).encode("utf-8")
        elif name == "templates/login.html":
            text = content.decode("utf-8")
            text = re.sub(r'(<input\b(?=[^>]*\bname="(?:username|password)")[^>]*?)\svalue="[^"]*"', r'\1', text)
            content = text.encode("utf-8")
        files[name] = content
    for name in ("wsgi.py", "gunicorn.conf.py", "manage_production.py", "requirements.txt", ".python-version"):
        files[name] = (DEPLOY / name).read_bytes()
    files["HOSTINGER_DEPLOYMENT.md"] = (ROOT / "docs" / "HOSTINGER_DEPLOYMENT.md").read_bytes()
    forbidden = (b"Admin@123", b"Executive@123", b"Manager@123", b"Hr@12345", b"test-session-secret-not-for-deployment", b"test-secret-key-that-is-at-least-32-bytes-long", b"BEGIN PRIVATE KEY")
    for name, content in files.items():
        assert not any(part in ("mobile_app", "venv", "__pycache__", ".pytest_cache", "instance", "uploads") for part in Path(name).parts), name
        assert not name.endswith((".pyc", ".db", ".log", ".env", "-secrets.json")), name
        assert not any(secret in content for secret in forbidden), f"Secret-like content in {name}"
        if name.endswith(".py"):
            compile(content, name, "exec")
    logo = files["static/branding/global_link_logo.jpeg"]
    assert logo == (BACKEND / "static/branding/global_link_logo.jpeg").read_bytes()
    target = ROOT / "dist" / "globallink_hostinger_backend.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_suffix(".zip.pending")
    with ZipFile(pending, "w", ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)
    with ZipFile(pending) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(files)
    assert all(p.read_bytes() == content for p, content in originals.items()), "Local application changed during packaging"
    pending.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(digest + "  " + target.name + "\n", encoding="utf-8")
    print(f"Created {target}; {len(files)} files; {target.stat().st_size} bytes")
    print(f"SHA-256: {digest}")
    print("Runtime source preserved; package-only demo/test sanitization applied; local app files unchanged.")

if __name__ == "__main__":
    main()
