"""Library storage for Selfie Studio.

All bytes written by this plugin live under the plugin data directory
(``ctx.get_plugin_data_dir()`` → ``data/plugin_data/<plugin_id>/uploads``),
never next to the plugin source. Records are referenced by absolute path
when handed to the selfie / dressup tags.
"""

import json
import os
import re
import tempfile
import time
import uuid
import warnings
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from core.utils.path_utils import is_within_directory

_KIND_DIRECTORIES = {"wardrobe": "wardrobe", "scene": "scenes"}
WARDROBE_CATEGORIES = ("top", "bottom", "dress", "shoes", "accessory", "other")
SCENE_CATEGORIES = ("indoor", "outdoor", "urban", "nature", "vehicle", "other")
KINDS = tuple(_KIND_DIRECTORIES)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_NAME_LENGTH = 40
MAX_NOTE_LENGTH = 200
MAX_ITEMS = 200

_FORMAT_EXTENSIONS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}

_data_dir: Path | None = None


class StorageError(ValueError):
    """Raised for invalid uploads, malformed updates or unconfigured storage."""


def base_dir() -> Path:
    """Return the configured plugin data directory."""
    if _data_dir is None:
        raise StorageError("Storage is not configured; call configure() first")
    return _data_dir


def uploads() -> Path:
    return base_dir() / "uploads"


def manifest_path() -> Path:
    return uploads() / "library.json"


def configure(data_dir) -> None:
    """Point the library at ``<data_dir>/uploads``."""
    global _data_dir
    if not data_dir:
        raise StorageError("Plugin data directory is not available")
    _data_dir = Path(data_dir).resolve()
    ensure_dirs()


def ensure_dirs() -> None:
    for directory in _KIND_DIRECTORIES.values():
        (uploads() / directory).mkdir(parents=True, exist_ok=True)


def categories_for(kind: str) -> tuple[str, ...]:
    if kind == "wardrobe":
        return WARDROBE_CATEGORIES
    if kind == "scene":
        return SCENE_CATEGORIES
    raise StorageError(f"Unknown kind: {kind}")


def _valid_category(kind: str, category: str) -> str:
    categories = categories_for(kind)
    return category if category in categories else "other"


def _clean_text(value: object, limit: int, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit] if text else fallback


def load_library() -> list[dict]:
    try:
        with manifest_path().open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    items = raw.get("items") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def save_library(items: list[dict]) -> None:
    ensure_dirs()
    payload = json.dumps({"version": 1, "items": items}, ensure_ascii=False, indent=2)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=uploads(), prefix=".library-", suffix=".tmp",
            mode="w", encoding="utf-8", delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
        os.replace(temporary_path, manifest_path())
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def get_item(item_id: str, items: list[dict] | None = None) -> dict | None:
    records = load_library() if items is None else items
    for record in records:
        if record.get("id") == item_id:
            return record
    return None


def _verify_image(data: bytes) -> str:
    """Validate uploaded bytes and return the detected image format."""
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise StorageError("Image must be nonempty and at most 10 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                image_format = image.format
                if image_format not in _FORMAT_EXTENSIONS:
                    raise StorageError("Supported image formats: PNG, JPEG, WebP")
                image.verify()
        return image_format
    except StorageError:
        raise
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise StorageError("Invalid image file") from exc


def item_path(record: dict) -> Path:
    """Resolve the on-disk path of a record, refusing anything outside uploads/."""
    kind = record.get("kind")
    filename = str(record.get("file") or "")
    directory = uploads() / _KIND_DIRECTORIES.get(kind, "")
    path = (directory / filename).resolve()
    if (path.parent != directory.resolve() or path.is_symlink()
            or not is_within_directory(uploads(), path)):
        raise StorageError("Invalid item path")
    return path


def add_item(kind: str, data: bytes, name: str, category: str, note: str) -> dict:
    if kind not in _KIND_DIRECTORIES:
        raise StorageError(f"Unknown kind: {kind}")
    items = load_library()
    if len(items) >= MAX_ITEMS:
        raise StorageError(f"Library is full (max {MAX_ITEMS} items)")

    image_format = _verify_image(data)
    item_id = uuid.uuid4().hex
    filename = f"{item_id}{_FORMAT_EXTENSIONS[image_format]}"
    directory = uploads() / _KIND_DIRECTORIES[kind]
    ensure_dirs()

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(data)
        os.replace(temporary_path, directory / filename)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    record = {
        "id": item_id,
        "kind": kind,
        "name": _clean_text(name, MAX_NAME_LENGTH) or "Untitled",
        "category": _valid_category(kind, category),
        "note": _clean_text(note, MAX_NOTE_LENGTH),
        "file": filename,
        "enabled": True,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    items.append(record)
    save_library(items)
    return record


def update_item(item_id: str, changes: dict) -> dict:
    items = load_library()
    record = get_item(item_id, items)
    if record is None:
        raise StorageError("Item not found")
    if "name" in changes:
        record["name"] = _clean_text(changes.get("name"), MAX_NAME_LENGTH) or record["name"]
    if "note" in changes:
        record["note"] = _clean_text(changes.get("note"), MAX_NOTE_LENGTH)
    if "category" in changes:
        record["category"] = _valid_category(record["kind"], str(changes.get("category") or ""))
    if "enabled" in changes:
        record["enabled"] = bool(changes.get("enabled"))
    record["updated_at"] = int(time.time())
    save_library(items)
    return record


def delete_item(item_id: str) -> None:
    items = load_library()
    record = get_item(item_id, items)
    if record is None:
        raise StorageError("Item not found")
    try:
        item_path(record).unlink(missing_ok=True)
    except OSError:
        pass
    items.remove(record)
    save_library(items)


def catalog_lines() -> tuple[list[str], list[str]]:
    """Render the enabled library as prompt-ready lines, grouped by kind."""
    wardrobe_lines: list[str] = []
    scene_lines: list[str] = []
    for record in load_library():
        if not record.get("enabled"):
            continue
        label = str(record.get("name") or "")
        note = str(record.get("note") or "")
        category = str(record.get("category") or "other")
        suffix = f" — {note}" if note else ""
        line = f"- {label} [{category}]{suffix}"
        if record.get("kind") == "wardrobe":
            wardrobe_lines.append(line)
        else:
            scene_lines.append(line)
    return wardrobe_lines, scene_lines
