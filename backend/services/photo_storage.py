"""Validated, normalized images stored under server-generated names."""
import hashlib
import io
import uuid
import warnings
from pathlib import Path
from flask import current_app, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError


def prepare_photo(file):
    if not file or not file.filename:
        raise ValueError("A camera photo is required")
    raw = file.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Photo must be smaller than 8 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 40_000_000:
                    raise ValueError("Use a JPG, PNG or WebP photo up to 40 megapixels")
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((2048, 2048))
                output = io.BytesIO()
                # Re-encode pixels, discarding EXIF GPS and other embedded metadata.
                image.save(output, format="JPEG", quality=85)
                return output.getvalue(), hashlib.sha256(raw).hexdigest()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError("The photo is not a valid image") from exc


def save_photo(data):
    folder = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    try:
        with (folder / name).open("xb") as stream:
            stream.write(data)
    except OSError:
        (folder / name).unlink(missing_ok=True)
        raise
    return name


def remove_photo(name):
    folder = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    target = (folder / name).resolve()
    if target.parent != folder:
        raise ValueError("Invalid stored photo path")
    target.unlink(missing_ok=True)


def photo_response(name):
    response = send_from_directory(current_app.config["UPLOAD_FOLDER"], name, mimetype="image/jpeg", max_age=0)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response

