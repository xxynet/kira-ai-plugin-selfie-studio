"""Selfie Studio — a wardrobe & scene library serving the character selfie flow.

The WebUI page lets the owner upload outfit pieces (tops, bottoms, dresses,
shoes, accessories) and scenes. Everything is stored under the plugin data
directory (``ctx.get_plugin_data_dir()``) and exposed to the character through
LLM-native extension points:

- an ``@on.llm_request`` hook appends the current catalog to the system prompt
  so the character knows what is available;
- the ``<dressup>`` tag resolves outfit/scene names from that catalog into
  extra reference images and renders the selfie with the persona reference
  image first, mirroring the builtin ``<selfie>`` tag contract.
"""

from __future__ import annotations

import asyncio
import base64
import warnings
from io import BytesIO
from pathlib import Path

from fastapi import File, Form, UploadFile
from fastapi.responses import FileResponse
from PIL import Image as PILImage

from core.chat.message_elements import Image
from core.plugin import BasePlugin, PageMenu, PluginPage, logger, on, register
from core.plugin.handlers import Priority
from core.prompt_manager import Prompt
from core.utils.common_utils import image_to_base64, image_to_image

from . import storage

PLUGIN_ID = "kira-ai-plugin-selfie-studio"

DRESSUP_TAG_DESCRIPTION = (
    '<dressup outfit="name1,name2" scene="name">selfie description: pose, framing, '
    "expression, use 'the character' to refer to the person</dressup> # Take a selfie "
    "wearing outfits from the selfie_wardrobe catalog and/or inside a scene from it. "
    "Copy name(s) exactly from the catalog; both attributes are optional. Do NOT "
    "describe the character's appearance — the persona reference image already has it. "
    "Fall back to <selfie> when the catalog is absent or nothing in it fits."
)

_CATALOG_HEADER = (
    "<selfie_wardrobe>\n"
    "The user curates a private wardrobe & scene library for your selfies "
    "(managed on the WebUI Selfie Studio page). To take a selfie wearing specific "
    "pieces or inside a specific scene, send a <msg> containing:\n"
    '<dressup outfit="outfit name(s), comma separated" scene="scene name">'
    "selfie description: pose, framing, expression, mood</dressup>\n"
    "Rules:\n"
    "- Copy names exactly from the catalog below; either attribute may be omitted.\n"
    "- Multiple outfits may be combined in one shot (e.g. a top + shoes).\n"
    "- Do not describe your own appearance; your reference image already has it.\n"
    "- If the catalog is irrelevant to the moment, use the plain <selfie> tag instead.\n"
)


def _reference_mime(b64_data: str) -> str:
    """Validate reference image bytes and return their actual MIME type."""
    content = base64.b64decode(b64_data, validate=True)
    with warnings.catch_warnings():
        warnings.simplefilter("error", PILImage.DecompressionBombWarning)
        with PILImage.open(BytesIO(content)) as image:
            mime = PILImage.MIME.get(image.format)
            if not mime:
                raise ValueError(f"Unknown image MIME type for format {image.format}")
    return mime


def build_catalog_text(wardrobe_lines: list[str], scene_lines: list[str]) -> str:
    parts = [_CATALOG_HEADER]
    if wardrobe_lines:
        parts.append("Outfits:\n" + "\n".join(wardrobe_lines))
    if scene_lines:
        parts.append("Scenes:\n" + "\n".join(scene_lines))
    parts.append("</selfie_wardrobe>")
    return "\n".join(p for p in parts if p)


class SelfieStudioPlugin(BasePlugin):

    def __init__(self, ctx, cfg: dict):
        super().__init__(ctx, cfg)
        self._lock = asyncio.Lock()

    async def initialize(self):
        data_dir = self.ctx.get_plugin_data_dir()
        if data_dir is None:
            raise RuntimeError("Could not resolve the plugin data directory")
        await asyncio.to_thread(storage.configure, data_dir)
        records = await asyncio.to_thread(storage.load_library)
        logger.info(f"[selfie-studio] initialized with {len(records)} library items, "
                    f"data dir: {storage.base_dir()}")

    async def terminate(self):
        pass

    # ── Library helpers ───────────────────────────────────────────────────

    @staticmethod
    def _resolve_records(records: list[dict], kind: str, raw: str) -> list[dict]:
        """Resolve a comma-separated name list into enabled records (exact, then fuzzy)."""
        wanted = [n.strip() for n in (raw or "").split(",") if n.strip()]
        pool = [r for r in records if r.get("kind") == kind and r.get("enabled")]
        resolved: list[dict] = []
        seen: set[str] = set()
        for name in wanted:
            record = next((r for r in pool if r.get("name") == name), None)
            if record is None:
                record = next(
                    (r for r in pool
                     if name in str(r.get("name") or "") or str(r.get("name") or "") in name),
                    None,
                )
            if record and record["id"] not in seen:
                seen.add(record["id"])
                resolved.append(record)
        return resolved

    async def _load_reference(self, path: Path, name: str) -> Image:
        b64_data = await image_to_base64(str(path))
        mime = await asyncio.to_thread(_reference_mime, b64_data)
        return Image(image=b64_data, name=name, mime=mime)

    # ── LLM integration ───────────────────────────────────────────────────

    @register.tag("dressup", DRESSUP_TAG_DESCRIPTION, parent="msg")
    async def dressup_tag(self, value: str, outfit: str | None = None,
                          scene: str | None = None, **kwargs):
        """Render a selfie wearing wardrobe items / inside a library scene."""
        try:
            ref_file = await self.ctx.persona_mgr.get_reference_image()
            if ref_file is None:
                logger.warning(
                    "[selfie-studio] active persona has no reference image, dressup skipped")
                return []
            client = self.ctx.provider_mgr.get_default_image()
            if not client:
                logger.error(
                    "[selfie-studio] no default image model configured, dressup skipped")
                return []

            records = await asyncio.to_thread(storage.load_library)
            references = [await self._load_reference(ref_file, ref_file.name)]
            for record in self._resolve_records(records, "wardrobe", outfit or ""):
                references.append(await self._load_reference(
                    storage.item_path(record), str(record.get("name") or record["file"])))
            for record in self._resolve_records(records, "scene", scene or ""):
                references.append(await self._load_reference(
                    storage.item_path(record), str(record.get("name") or record["file"])))

            img_res = await image_to_image(client, value, image=references)
            if img_res:
                return [img_res]
            logger.warning("[selfie-studio] dressup generation returned no image")
        except Exception as e:
            logger.error(f"[selfie-studio] dressup failed: {e}")
        return []

    @on.llm_request(priority=Priority.LOW)
    async def inject_catalog(self, event, req, tag_set, *args, **kwargs):
        """Append the current wardrobe & scene catalog to the system prompt."""
        if not (self.plugin_cfg or {}).get("inject_catalog", True):
            return
        try:
            wardrobe_lines, scene_lines = await asyncio.to_thread(storage.catalog_lines)
        except Exception as e:
            logger.error(f"[selfie-studio] failed to read library for catalog: {e}")
            return
        if not wardrobe_lines and not scene_lines:
            return
        req.system_prompt.append(Prompt(
            content=build_catalog_text(wardrobe_lines, scene_lines),
            name=f"{PLUGIN_ID}:catalog",
            source=PLUGIN_ID,
            persist=False,
        ))

    # ── Widget ────────────────────────────────────────────────────────────

    @register.widget(
        label={"zh": "自拍衣橱", "en": "Selfie Wardrobe"},
        icon="Camera", color="purple", order=64,
    )
    def widget_wardrobe(self) -> str:
        try:
            records = storage.load_library()
        except Exception:
            records = []
        wardrobe = sum(1 for r in records if r.get("kind") == "wardrobe")
        scenes = sum(1 for r in records if r.get("kind") == "scene")
        if (self.ctx.get_lang() or "en").startswith("zh"):
            return f"{wardrobe} 件穿搭 · {scenes} 个场景"
        return f"{wardrobe} outfits · {scenes} scenes"

    # ── API: library CRUD ─────────────────────────────────────────────────

    @register.api("GET", "/items")
    async def api_items(self):
        try:
            records = await asyncio.to_thread(storage.load_library)
            return {"ok": True, "items": records}
        except Exception as e:
            logger.error(f"[selfie-studio] list items failed: {e}")
            return {"ok": False, "error": str(e)}

    @register.api("POST", "/items/upload")
    async def api_upload(self, file: UploadFile = File(...), kind: str = Form("wardrobe"),
                         name: str = Form(""), category: str = Form(""), note: str = Form("")):
        try:
            data = await file.read()
            async with self._lock:
                record = await asyncio.to_thread(
                    storage.add_item, kind, data, name, category, note)
            logger.info(f"[selfie-studio] uploaded {kind} item: {record['name']}")
            return {"ok": True, "item": record}
        except storage.StorageError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"[selfie-studio] upload failed: {e}")
            return {"ok": False, "error": str(e)}

    @register.api("POST", "/items/update")
    async def api_update(self, payload: dict):
        try:
            item_id = str(payload.get("id") or "")
            if not item_id:
                return {"ok": False, "error": "Missing item id"}
            allowed = {k: payload[k] for k in ("name", "category", "note", "enabled")
                       if k in payload}
            async with self._lock:
                record = await asyncio.to_thread(storage.update_item, item_id, allowed)
            return {"ok": True, "item": record}
        except storage.StorageError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"[selfie-studio] update failed: {e}")
            return {"ok": False, "error": str(e)}

    @register.api("POST", "/items/delete")
    async def api_delete(self, payload: dict):
        try:
            item_id = str(payload.get("id") or "")
            if not item_id:
                return {"ok": False, "error": "Missing item id"}
            async with self._lock:
                await asyncio.to_thread(storage.delete_item, item_id)
            return {"ok": True}
        except storage.StorageError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"[selfie-studio] delete failed: {e}")
            return {"ok": False, "error": str(e)}

    @register.api("GET", "/image/{item_id}")
    async def api_image(self, item_id: str):
        try:
            record = await asyncio.to_thread(storage.get_item, item_id)
            if record is None:
                return {"ok": False, "error": "Item not found"}
            path = await asyncio.to_thread(storage.item_path, record)
            if not path.is_file():
                return {"ok": False, "error": "Image file missing"}
            return FileResponse(
                path,
                headers={
                    "Cache-Control": "private, max-age=3600",
                    "Content-Disposition": 'inline; filename="%s"' % record["file"],
                },
            )
        except storage.StorageError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"[selfie-studio] serve image failed: {e}")
            return {"ok": False, "error": str(e)}

    @register.api("GET", "/catalog")
    async def api_catalog(self):
        """Preview the catalog text injected into the system prompt."""
        try:
            wardrobe_lines, scene_lines = await asyncio.to_thread(storage.catalog_lines)
            return {"ok": True,
                    "enabled": bool((self.plugin_cfg or {}).get("inject_catalog", True)),
                    "text": build_catalog_text(wardrobe_lines, scene_lines)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── API: test shot ────────────────────────────────────────────────────

    @register.api("POST", "/testshot")
    async def api_testshot(self, payload: dict):
        try:
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                return {"ok": False, "error": "Describe the pose or framing first"}

            ref_file = await self.ctx.persona_mgr.get_reference_image()
            if ref_file is None:
                return {"ok": False, "error": "The active persona has no reference image"}
            client = self.ctx.provider_mgr.get_default_image()
            if not client:
                return {"ok": False, "error": "No default image model is configured"}

            records = await asyncio.to_thread(storage.load_library)
            by_id = {r["id"]: r for r in records}
            references = [await self._load_reference(ref_file, ref_file.name)]
            for item_id in payload.get("outfit_ids") or []:
                record = by_id.get(str(item_id))
                if record and record.get("kind") == "wardrobe" and record.get("enabled"):
                    references.append(await self._load_reference(
                        storage.item_path(record), str(record.get("name") or record["file"])))
            scene_id = str(payload.get("scene_id") or "")
            if scene_id and scene_id in by_id:
                record = by_id[scene_id]
                if record.get("kind") == "scene" and record.get("enabled"):
                    references.append(await self._load_reference(
                        storage.item_path(record), str(record.get("name") or record["file"])))

            img_res = await image_to_image(client, prompt, image=references)
            if not img_res:
                return {"ok": False, "error": "Image generation returned no result"}
            data_url = await img_res.to_data_url()
            return {"ok": True, "image": data_url, "mime": img_res.mime or "image/png"}
        except Exception as e:
            logger.error(f"[selfie-studio] testshot failed: {e}")
            return {"ok": False, "error": str(e)}

    # ── WebUI page ────────────────────────────────────────────────────────

    @register.page(
        "/studio",
        auth=True,
        menu=PageMenu(
            label={"zh": "自拍工坊", "en": "Selfie Studio"},
            icon="icon.svg",
            order=40,
        ),
    )
    def page_studio(self) -> PluginPage:
        return PluginPage.from_folder("./web")
