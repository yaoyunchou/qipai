import base64
import mimetypes
import uuid
from pathlib import Path

from app.config import settings

_CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def upload_root() -> Path:
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def decode_base64_payload(data_base64: str) -> bytes:
    raw = data_base64
    if raw.startswith("data:"):
        raw = raw.split(",", 1)[-1]
    return base64.b64decode(raw, validate=True)


def _guess_ext(filename: str, content_type: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext:
        return ext
    return _CONTENT_TYPE_EXT.get(content_type, mimetypes.guess_extension(content_type) or ".bin")


def save_attachment(claim_id: int, filename: str, content_type: str, data_base64: str) -> str:
    data = decode_base64_payload(data_base64)
    rel = f"expenses/{claim_id}/{uuid.uuid4().hex}{_guess_ext(filename, content_type)}"
    dest = upload_root() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return rel.replace("\\", "/")


def attachment_url(file_path: str) -> str:
    prefix = settings.upload_url_prefix.rstrip("/")
    return f"{prefix}/{file_path.lstrip('/')}"


def delete_attachment_file(file_path: str | None) -> None:
    if not file_path:
        return
    full = upload_root() / file_path
    if full.is_file():
        full.unlink()


def delete_claim_attachment_files(file_paths: list[str | None]) -> None:
    for path in file_paths:
        delete_attachment_file(path)
