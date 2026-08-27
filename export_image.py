"""Render a Qi Men chart and its AI reading into one downloadable PNG."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1440
MARGIN = 72
CONTENT_WIDTH = WIDTH - MARGIN * 2
PALACE_ORDER = ("4", "9", "2", "3", "5", "7", "8", "1", "6")
PALACE_NAMES = {
    "1": "坎一宫", "2": "坤二宫", "3": "震三宫", "4": "巽四宫", "5": "中五宫",
    "6": "乾六宫", "7": "兑七宫", "8": "艮八宫", "9": "离九宫",
}
PALACE_META = {
    "1": ("正北", "水"), "2": ("西南", "土"), "3": ("正东", "木"),
    "4": ("东南", "木"), "5": ("中宫", "土"), "6": ("西北", "金"),
    "7": ("正西", "金"), "8": ("东北", "土"), "9": ("正南", "火"),
}
HARM_COLORS = {
    "空亡": ((239, 235, 248), (101, 86, 141)),
    "门迫": ((252, 237, 220), (167, 89, 19)),
    "击刑": ((250, 229, 226), (164, 49, 37)),
    "入墓": ((244, 234, 228), (112, 68, 47)),
}
FONT_CANDIDATES = {
    "regular": (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ),
    "bold": (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansSC-Bold.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
}


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a deployment-safe CJK font, with DejaVu as a last-resort fallback."""
    key = "bold" if bold else "regular"
    for candidate in FONT_CANDIDATES[key]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default(size=size)


def _text_width(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.ImageFont) -> float:
    return draw.textlength(value, font=font)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Wrap Chinese and Latin text without requiring a word-segmentation dependency."""
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for character in text:
        if character == "\n":
            lines.append(current)
            current = ""
            continue
        candidate = current + character
        if current and _text_width(draw, candidate, font) > max_width:
            lines.append(current.rstrip())
            current = character.lstrip()
        else:
            current = candidate
    lines.append(current.rstrip())
    return lines


def _clean_markdown(value: str) -> str:
    value = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"(\*\*|__)(.*?)\1", r"\2", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", value)
    value = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"\1", value)
    value = value.replace("`", "").replace("~~", "")
    return value.strip()


def _reading_blocks(markdown: str) -> list[tuple[str, str]]:
    """Convert the small Markdown subset returned by the model into styled text blocks."""
    blocks: list[tuple[str, str]] = []
    for raw_line in markdown.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            if blocks and blocks[-1][0] != "space":
                blocks.append(("space", ""))
            continue
        heading = re.match(r"^#{1,6}\s*(.+)$", line)
        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        ordered = re.match(r"^(\d+)[.)、]\s*(.+)$", line)
        if heading:
            blocks.append(("heading", _clean_markdown(heading.group(1))))
        elif bullet:
            blocks.append(("body", f"• {_clean_markdown(bullet.group(1))}"))
        elif ordered:
            blocks.append(("heading", f"{ordered.group(1)}. {_clean_markdown(ordered.group(2))}"))
        else:
            blocks.append(("body", _clean_markdown(line)))
    while blocks and blocks[-1][0] == "space":
        blocks.pop()
    return blocks or [("body", "暂无 AI 解读。")]


def _layout_reading(draw: ImageDraw.ImageDraw, markdown: str, max_width: int) -> tuple[list[dict], int]:
    layout: list[dict] = []
    y = 0
    for style, value in _reading_blocks(markdown):
        if style == "space":
            y += 16
            continue
        heading = style == "heading"
        font = _font(32 if heading else 27, bold=heading)
        line_height = 48 if heading else 43
        if heading and y:
            y += 12
        for line in _wrap_text(draw, value, font, max_width):
            layout.append({"text": line, "font": font, "y": y, "fill": (57, 48, 42) if heading else (77, 69, 64)})
            y += line_height
        y += 7 if heading else 5
    return layout, y


def _draw_pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    label: str,
    font: ImageFont.ImageFont,
    background: tuple[int, int, int],
    foreground: tuple[int, int, int],
    *,
    padding_x: int = 13,
    height: int = 35,
) -> int:
    x, y = xy
    width = int(_text_width(draw, label, font)) + padding_x * 2
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, fill=background)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_y = y + (height - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x + padding_x, text_y), label, font=font, fill=foreground)
    return width


def _palace_value(pan: dict, section: str, gong: str) -> str:
    return str(pan.get(section, {}).get(gong) or "—")


def _draw_palace(draw: ImageDraw.ImageDraw, pan: dict, gong: str, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    harms = pan.get("siHai", {}).get("byGong", {}).get(gong, [])
    fill = (255, 249, 245) if harms else (255, 253, 250)
    outline = (197, 91, 56) if harms else (218, 208, 198)
    draw.rounded_rectangle(box, radius=20, fill=fill, outline=outline, width=4 if len(harms) > 1 else 2)

    title_font = _font(29, bold=True)
    meta_font = _font(19)
    label_font = _font(18)
    value_font = _font(28, bold=True)
    stem_font = _font(25, bold=True)
    pill_font = _font(18, bold=True)
    draw.text((x1 + 24, y1 + 18), PALACE_NAMES[gong], font=title_font, fill=(52, 44, 39))
    direction, element = PALACE_META[gong]
    draw.text((x1 + 24, y1 + 52), f"{direction} · {element}", font=meta_font, fill=(133, 120, 110))

    marker_labels = []
    if str(pan.get("zhiFuGong")) == gong:
        marker_labels.append("值符")
    if str(pan.get("zhiShiGong")) == gong:
        marker_labels.append("值使")
    if str(pan.get("maStar", {}).get("gong")) == gong:
        marker_labels.append("驿马")
    marker_x = x2 - 24
    for label in reversed(marker_labels):
        width = int(_text_width(draw, label, pill_font)) + 18
        marker_x -= width
        _draw_pill(draw, (marker_x, y1 + 18), label, pill_font, (232, 239, 235), (52, 111, 84), padding_x=9, height=31)
        marker_x -= 7

    column_width = (x2 - x1 - 48) // 3
    for index, (label, section) in enumerate((("神", "baShen"), ("星", "jiuXing"), ("门", "baMen"))):
        center_x = x1 + 24 + column_width * index + column_width // 2
        value = _palace_value(pan, section, gong)
        draw.text((center_x, y1 + 82), label, font=label_font, fill=(151, 138, 128), anchor="ma")
        draw.text((center_x, y1 + 113), value, font=value_font, fill=(57, 48, 42), anchor="ma")

    draw.line((x1 + 24, y1 + 144, x2 - 24, y1 + 144), fill=(228, 219, 211), width=2)
    for index, (label, section) in enumerate((("天盘", "tianPan"), ("地盘", "diPan"), ("暗干", "anGan"))):
        center_x = x1 + 24 + column_width * index + column_width // 2
        value = _palace_value(pan, section, gong)
        draw.text((center_x, y1 + 167), label, font=label_font, fill=(151, 138, 128), anchor="ma")
        draw.text((center_x, y1 + 200), value, font=stem_font, fill=(80, 69, 61), anchor="ma")

    pill_x = x1 + 24
    if harms:
        for harm in harms:
            name = str(harm.get("type", ""))
            background, foreground = HARM_COLORS.get(name, ((239, 236, 232), (90, 82, 76)))
            pill_x += _draw_pill(draw, (pill_x, y1 + 230), name, pill_font, background, foreground, height=31) + 8
    else:
        draw.text((pill_x, y1 + 236), "四害未见", font=label_font, fill=(173, 163, 154))


def generate_qimen_report_png(pan: dict, question: str, ai_reading: str) -> bytes:
    """Return a complete PNG containing chart facts, Four Harms and the AI reading."""
    probe = Image.new("RGB", (WIDTH, 200), (249, 246, 241))
    probe_draw = ImageDraw.Draw(probe)
    body_font = _font(25)
    question_lines = _wrap_text(probe_draw, question.strip() or "综合趋势", body_font, CONTENT_WIDTH - 48)
    reading_layout, reading_height = _layout_reading(probe_draw, ai_reading, CONTENT_WIDTH - 64)

    header_height = 230 + len(question_lines) * 39
    overview_height = 86
    grid_gap = 18
    card_height = 278
    grid_height = card_height * 3 + grid_gap * 2
    ai_card_height = reading_height + 76
    image_height = (
        MARGIN + header_height + overview_height + 28 + grid_height
        + 58 + 54 + ai_card_height + 120
    )

    image = Image.new("RGB", (WIDTH, image_height), (249, 246, 241))
    draw = ImageDraw.Draw(image)
    title_font = _font(47, bold=True)
    eyebrow_font = _font(20, bold=True)
    meta_font = _font(23)
    section_font = _font(34, bold=True)
    count_font = _font(25, bold=True)

    y = MARGIN
    _draw_pill(draw, (MARGIN, y), "奇门遁甲 · AI 合盘报告", eyebrow_font, (237, 229, 217), (111, 79, 53), height=38)
    y += 57
    draw.text((MARGIN, y), "奇门盘与 AI 解读", font=title_font, fill=(48, 41, 36))
    chart_date = str(pan.get("basicInfo", {}).get("date") or "时间未记录")
    ju_name = str(pan.get("juShu", {}).get("fullName") or "局数未记录")
    y += 68
    draw.text((MARGIN, y), f"占卦时间  {chart_date}    ·    {ju_name}", font=meta_font, fill=(113, 101, 92))
    y += 47
    question_top = y
    question_height = 34 + len(question_lines) * 39
    draw.rounded_rectangle((MARGIN, question_top, WIDTH - MARGIN, question_top + question_height), radius=16, fill=(255, 252, 247))
    draw.text((MARGIN + 22, question_top + 15), "所问事项", font=_font(20, bold=True), fill=(158, 92, 49))
    for index, line in enumerate(question_lines):
        draw.text((MARGIN + 130, question_top + 13 + index * 39), line, font=body_font, fill=(71, 62, 56))
    y = question_top + question_height + 24

    si_hai = pan.get("siHai", {})
    summary = si_hai.get("summary", {})
    counts = summary.get("counts", {})
    total = int(summary.get("total", sum(int(counts.get(name, 0)) for name in HARM_COLORS)))
    affected_gongs = summary.get("affectedGongs")
    affected = len(affected_gongs if affected_gongs is not None else [gong for gong, harms in si_hai.get("byGong", {}).items() if harms])
    overview_bottom = y + overview_height
    draw.rounded_rectangle((MARGIN, y, WIDTH - MARGIN, overview_bottom), radius=18, fill=(255, 252, 247), outline=(226, 214, 202), width=2)
    draw.text((MARGIN + 24, y + 19), "本盘四害", font=_font(21, bold=True), fill=(105, 91, 80))
    draw.text((MARGIN + 145, y + 15), str(total), font=_font(34, bold=True), fill=(177, 69, 44))
    draw.text((MARGIN + 190, y + 24), f"共影响 {affected} 宫", font=_font(20), fill=(135, 121, 111))
    pill_x = MARGIN + 430
    for name in HARM_COLORS:
        background, foreground = HARM_COLORS[name]
        label = f"{name}  {int(counts.get(name, 0))}"
        pill_x += _draw_pill(draw, (pill_x, y + 23), label, count_font, background, foreground, height=42) + 16
    y = overview_bottom + 28

    card_gap = grid_gap
    card_width = (CONTENT_WIDTH - card_gap * 2) // 3
    for index, gong in enumerate(PALACE_ORDER):
        row, column = divmod(index, 3)
        x1 = MARGIN + column * (card_width + card_gap)
        y1 = y + row * (card_height + card_gap)
        _draw_palace(draw, pan, gong, (x1, y1, x1 + card_width, y1 + card_height))
    y += grid_height + 58

    draw.text((MARGIN, y), "AI 分析解读", font=section_font, fill=(48, 41, 36))
    draw.text((WIDTH - MARGIN, y + 9), "内容由模型依据盘面生成", font=_font(20), fill=(145, 133, 123), anchor="ra")
    y += 54
    ai_top = y
    draw.rounded_rectangle((MARGIN, ai_top, WIDTH - MARGIN, ai_top + ai_card_height), radius=22, fill=(255, 253, 250), outline=(226, 216, 207), width=2)
    text_x = MARGIN + 32
    text_y = ai_top + 30
    for item in reading_layout:
        draw.text((text_x, text_y + item["y"]), item["text"], font=item["font"], fill=item["fill"])
    y = ai_top + ai_card_height + 35
    draw.line((MARGIN, y, WIDTH - MARGIN, y), fill=(220, 211, 203), width=2)
    footer = "传统文化研究与排盘辅助 · AI 解读不构成医疗、法律或投资建议"
    draw.text((MARGIN, y + 25), footer, font=_font(20), fill=(139, 128, 119))
    draw.text((WIDTH - MARGIN, y + 25), "qimen-test", font=_font(20, bold=True), fill=(139, 128, 119), anchor="ra")

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
