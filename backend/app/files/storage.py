"""Lưu tệp: kiểm tra định dạng bằng chữ ký nhị phân (không tin phần mở rộng/Content-Type)."""
import os
import secrets
from pathlib import Path

from app.core.config import get_settings

MAX_BYTES = 10 * 1024 * 1024
SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/webp": (b"RIFF",),
    "application/pdf": (b"%PDF-",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (b"PK\x03\x04",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04",),
}
EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "application/pdf": ".pdf",
       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
       "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"}
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


def sniff(content: bytes) -> str | None:
    for ctype, sigs in SIGNATURES.items():
        if any(content.startswith(sig) for sig in sigs):
            if ctype == "image/webp" and content[8:12] != b"WEBP":
                continue
            return ctype
    return None


def _root() -> Path:
    return Path(os.environ.get("STORAGE_DIR") or get_settings().STORAGE_DIR)


def save(tenant_id: int, content: bytes, ctype: str) -> str:
    key = secrets.token_urlsafe(24)
    d = _root() / str(tenant_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / (key + EXT[ctype])).write_bytes(content)
    return key


def load(tenant_id: int, key: str, ctype: str) -> bytes:
    return (_root() / str(tenant_id) / (key + EXT[ctype])).read_bytes()
