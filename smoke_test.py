"""One-off smoke test for the selfie-studio plugin (run from anywhere)."""

import asyncio
import base64
import importlib
import shutil
import sys
import tempfile
import types
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

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

    # Outfit sheet composition — exact layout math (2-cell and 4-cell wrap)
    sheet_records = []
    for size, name in (((300, 400), "白衬衫"), ((500, 320), "帆布鞋"),
                       ((800, 1000), "牛仔外套"), ((300, 400), "贝雷帽")):
        b = BytesIO()
        Image.new("RGB", size, (120, 140, 160)).save(b, format="PNG")
        sheet_records.append(await asyncio.to_thread(
            storage.add_item, "wardrobe", b.getvalue(), name, "top", ""))

    sheet = await asyncio.to_thread(compose.compose_outfit_sheet, sheet_records[:2])
    with Image.open(BytesIO(sheet)) as sheet_image:
        assert sheet_image.format == "JPEG" and sheet_image.size == (888, 520)

    sheet = await asyncio.to_thread(compose.compose_outfit_sheet, sheet_records)
    with Image.open(BytesIO(sheet)) as sheet_image:
        # row 1: three cells (tallest 640) — row 2: one wrapped cell
        assert sheet_image.size == (1424, 1240)

    # Unreadable records are skipped with a warning, sheet still composes
    bad = BytesIO()
    Image.new("RGB", (100, 100), (0, 0, 0)).save(bad, format="PNG")
    bad_record = await asyncio.to_thread(
        storage.add_item, "wardrobe", bad.getvalue(), "坏图", "other", "")
    await asyncio.to_thread(storage.item_path(bad_record).write_bytes, b"corrupt")
    sheet = await asyncio.to_thread(
        compose.compose_outfit_sheet, [sheet_records[0], bad_record, sheet_records[1]])
    with Image.open(BytesIO(sheet)) as sheet_image:
        assert sheet_image.size == (888, 520)

    # _fit_text truncates long names to the cell width (needs a CJK font)
    font = compose._label_font(28)
    if font is not None:
        draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        long_name = "超长单品名称" * 8
        fitted = compose._fit_text(draw, long_name, font, 120)
        assert fitted != long_name and fitted.endswith("…")
        assert draw.textlength(fitted, font=font) <= 120

    assert await asyncio.to_thread(compose.compose_outfit_sheet, []) is None

    # EXIF orientation must be applied before composing (phone portrait photos)
    b = BytesIO()
    exif = Image.Exif()
    exif[274] = 6  # display = stored pixels rotated 90 degrees clockwise
    Image.new("RGB", (200, 400), (90, 120, 90)).save(b, format="JPEG", exif=exif)
    rotated_record = await asyncio.to_thread(
        storage.add_item, "wardrobe", b.getvalue(), "竖拍照片", "top", "")
    cell = await asyncio.to_thread(compose._load_cell, rotated_record)
    assert cell is not None and cell.size == (400, 200), \
        f"EXIF orientation not applied: {cell.size if cell else None}"
    await asyncio.to_thread(storage.delete_item, rotated_record["id"])

    # _build_references: persona first, outfits then scene; merge gated by config
    persona = data_dir / "persona.jpg"
    Image.new("RGB", (120, 150), (20, 20, 20)).save(persona, format="JPEG")
    scene_b = BytesIO()
    Image.new("RGB", (640, 400), (150, 150, 170)).save(scene_b, format="PNG")
    scene_record = await asyncio.to_thread(
        storage.add_item, "scene", scene_b.getvalue(), "咖啡厅", "indoor", "")

    plugin = main.SelfieStudioPlugin(ctx=None, cfg={})
    refs = await plugin._build_references(persona, sheet_records[:2], [scene_record])
    assert [r.name for r in refs] == ["persona.jpg", "白衬衫", "帆布鞋", "咖啡厅"]
    assert refs[0].mime.startswith("image/")

    # a single outfit is never merged even when the switch is on
    plugin_on = main.SelfieStudioPlugin(ctx=None, cfg={"merge_references": True})
    refs = await plugin_on._build_references(persona, [sheet_records[0]], [scene_record])
    assert [r.name for r in refs] == ["persona.jpg", "白衬衫", "咖啡厅"]

    refs = await plugin_on._build_references(persona, sheet_records[:2], [scene_record])
    assert [r.name for r in refs] == ["persona.jpg", "outfit-sheet", "咖啡厅"]
    assert refs[1].mime == "image/jpeg"
    with Image.open(BytesIO(base64.b64decode(refs[1].image))) as sheet_image:
        assert sheet_image.size == (888, 520)

    # partially unreadable outfits still merge into a one-cell sheet
    refs = await plugin_on._build_references(persona, [bad_record, sheet_records[1]], [])
    assert [r.name for r in refs] == ["persona.jpg", "outfit-sheet"]

    await asyncio.to_thread(storage.delete_item, record["id"])
    assert await asyncio.to_thread(storage.get_item, record["id"]) is None
    assert not path.exists()

asyncio.run(flow())
shutil.rmtree(data_dir, ignore_errors=True)

# The plugin source folder must not contain any runtime library artifacts.
assert not (PLUGIN_DIR / "uploads" / "library.json").exists(), \
    "runtime data must not live next to the plugin source"
print("SMOKE TEST OK")
