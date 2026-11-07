"""Compose multiple outfit reference images into a single labelled sheet.

Some image models accept only a limited number of reference images. When the
``merge_references`` option is enabled and a selfie uses several wardrobe
pieces, this module renders them as one JPEG contact sheet — each cell
resized to a common height, the item name written underneath (when a
CJK-capable system font is available) — so the model still sees every piece.
"""

import io

from PIL import Image, ImageDraw, ImageFont

from . import storage

CELL_HEIGHT = 640
CELL_MAX_WIDTH = 520
GUTTER = 24
LABEL_HEIGHT = 56
MARGIN = 32
PER_ROW = 3
BACKGROUND = (245, 245, 245)
TEXT_COLOR = (70, 70, 70)

_FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
)


def _label_font(size: int):
    """Return the first available CJK-capable font, or None to skip labels."""
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return None


def _load_cell(record: dict) -> Image.Image | None:
    try:
        path = storage.item_path(record)
        with Image.open(path) as image:
            image.load()
            rgba = image.convert("RGBA")
    except (OSError, ValueError):
        return None
    rgba.thumbnail((CELL_MAX_WIDTH, CELL_HEIGHT), Image.LANCZOS)
    return rgba


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…"


def compose_outfit_sheet(records: list[dict]) -> bytes | None:
    """Render wardrobe records into one JPEG sheet.

    Records that cannot be read are skipped; returns ``None`` when nothing
    is composable, letting callers fall back to separate references.
    """
    cells: list[tuple[str, Image.Image]] = []
    for record in records:
        image = _load_cell(record)
        if image is not None:
            cells.append((str(record.get("name") or ""), image))
    if not cells:
        return None

    rows = [cells[i:i + PER_ROW] for i in range(0, len(cells), PER_ROW)]
    font = _label_font(28)

    row_heights: list[int] = []
    row_widths: list[int] = []
    for row in rows:
        image_height = max(im.height for _, im in row)
        width = sum(im.width for _, im in row) + GUTTER * (len(row) - 1)
        row_heights.append(image_height + LABEL_HEIGHT)
        row_widths.append(width)
    sheet_width = max(row_widths) + MARGIN * 2
    sheet_height = sum(row_heights) + GUTTER * (len(rows) - 1) + MARGIN * 2

    sheet = Image.new("RGB", (sheet_width, sheet_height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    y = MARGIN
    for row, row_height, row_width in zip(rows, row_heights, row_widths):
        image_height = max(im.height for _, im in row)
        x = MARGIN + max(0, (sheet_width - MARGIN * 2 - row_width) // 2)
        for name, image in row:
            top = y + (image_height - image.height) // 2
            sheet.paste(image.convert("RGB"), (x, top), image)
            if font is not None and name:
                label = _fit_text(draw, name, font, image.width)
                text_width = draw.textlength(label, font=font)
                draw.text(
                    (x + (image.width - text_width) / 2, y + image_height + 8),
                    label, font=font, fill=TEXT_COLOR,
                )
            x += image.width + GUTTER
        y += row_height + GUTTER

    buffer = io.BytesIO()
    sheet.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()
