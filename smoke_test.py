"""One-off smoke test for the selfie-studio plugin (run from anywhere)."""

import asyncio
import importlib
import shutil
import sys
import tempfile
import types
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

PLUGIN_DIR = Path(__file__).resolve().parent
PLUGIN_ID = "kira-ai-plugin-selfie-studio"

# Load the plugin folder as a package, the way PluginManager does.
pkg = types.ModuleType("smoke_selfie_studio")
pkg.__path__ = [str(PLUGIN_DIR)]
sys.modules["smoke_selfie_studio"] = pkg

from core.plugin import registry  # noqa: E402

main = importlib.import_module("smoke_selfie_studio.main")
storage = importlib.import_module("smoke_selfie_studio.storage")
compose = importlib.import_module("smoke_selfie_studio.compose")

comp = registry._plugin_components.get(PLUGIN_ID)
assert comp is not None, "components not registered"
assert len(comp.pages) == 1, f"pages: {comp.pages}"
assert comp.pages[0]["route"] == "/studio"
assert len(comp.api_routes) == 7, f"api routes: {[r['path'] for r in comp.api_routes]}"
assert any(r["path"].lstrip("/") == "items/upload" and "UploadFile" in str(r["func"].__annotations__)
           for r in comp.api_routes)
assert "dressup" in comp.tag_funcs, "tag not registered"
hooks = [(h.event_type.name, h.handler.__name__) for h in comp.hooks]
assert ("ON_LLM_REQUEST", "inject_catalog") in hooks, f"hooks: {hooks}"
widgets = [(w["label"], w["icon"]) for w in comp.widgets]
print("pages:", [(p["route"], p["menu"].dict()) for p in comp.pages])
print("apis:", [(r["method"], r["path"]) for r in comp.api_routes])
print("tags:", [(t["name"], t["parent"]) for t in comp.tags])
print("hooks:", hooks)
print("widgets:", widgets)

# Tag registry catalog text
assert "dressup" in main.DRESSUP_TAG_DESCRIPTION

# Storage round-trip inside an isolated data dir (never the plugin folder)
from PIL import Image  # noqa: E402

data_dir = Path(tempfile.mkdtemp(prefix="selfie-studio-smoke-"))
buf = BytesIO()
Image.new("RGB", (64, 64), (80, 120, 200)).save(buf, format="PNG")
png_bytes = buf.getvalue()

async def flow():
    await asyncio.to_thread(storage.configure, data_dir / "plugin_data")

    record = await asyncio.to_thread(
        storage.add_item, "wardrobe", png_bytes, "  测试   上衣  ", "top", "冒烟测试用")
    assert record["name"] == "测试 上衣" and record["file"].endswith(".png")
    path = await asyncio.to_thread(storage.item_path, record)
    assert path.is_file()
    assert storage.base_dir() in path.parents, "item must live under the data dir"
    assert PLUGIN_DIR not in path.parents, "item must NOT live inside the plugin source dir"

    w, _ = await asyncio.to_thread(storage.catalog_lines)
    assert w == ["- 测试 上衣 [top] — 冒烟测试用"], w

    updated = await asyncio.to_thread(
        storage.update_item, record["id"], {"enabled": False})
    assert updated["enabled"] is False
    w2, _ = await asyncio.to_thread(storage.catalog_lines)
    assert w2 == [], "disabled item must not appear in catalog"

    # Resolution logic used by the dressup tag
    resolve = main.SelfieStudioPlugin._resolve_records
    assert resolve(storage.load_library(), "wardrobe", "测试 上衣") == []
    assert resolve(storage.load_library(), "wardrobe", "不存在") == []

    # Invalid upload rejected
    for bad in (b"", b"not an image", png_bytes[:20]):
        try:
            await asyncio.to_thread(storage.add_item, "scene", bad, "x", "", "")
            raise AssertionError("bad upload accepted")
        except storage.StorageError:
            pass

    # Path traversal refused
    try:
        await asyncio.to_thread(storage.item_path, {**record, "file": "../evil.png"})
        raise AssertionError("traversal accepted")
    except storage.StorageError:
        pass

    # Outfit sheet composition (2 and 3 cells, mixed aspect ratios)
    sheet_records = []
    for size, name in (((300, 400), "白衬衫"), ((500, 320), "帆布鞋"), ((800, 1000), "牛仔外套")):
        b = BytesIO()
        Image.new("RGB", size, (120, 140, 160)).save(b, format="JPEG")
        sheet_records.append(await asyncio.to_thread(
            storage.add_item, "wardrobe", b.getvalue(), name, "top", ""))
    for records, min_width in ((sheet_records[:2], 2), (sheet_records, 3)):
        sheet = await asyncio.to_thread(compose.compose_outfit_sheet, records)
        assert sheet is not None
        with Image.open(BytesIO(sheet)) as sheet_image:
            assert sheet_image.format == "JPEG"
            assert sheet_image.width >= min_width * 100
            assert sheet_image.height >= 400
    assert await asyncio.to_thread(compose.compose_outfit_sheet, []) is None

    await asyncio.to_thread(storage.delete_item, record["id"])
    assert await asyncio.to_thread(storage.get_item, record["id"]) is None
    assert not path.exists()

asyncio.run(flow())
shutil.rmtree(data_dir, ignore_errors=True)

# The plugin source folder must not contain any runtime library artifacts.
assert not (PLUGIN_DIR / "uploads" / "library.json").exists(), \
    "runtime data must not live next to the plugin source"
print("SMOKE TEST OK")
