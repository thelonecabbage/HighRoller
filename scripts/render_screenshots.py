"""Render README preview images from the animation frames (no watch or simulator needed).

Usage (from high-roller/): python3 scripts/render_screenshots.py
Requires: Pillow. Writes to docs/images/.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FRAMES = ROOT / "assets" / "gt.r" / "anim"
OUT = ROOT / "docs" / "images"
SCREEN = 466  # Amazfit GTR 4
SCALE = SCREEN / 480  # px() in the app
DICE = ["d4", "d6", "d8", "d10", "d12", "d20"]
COLORS = {
    "d4": (0x28, 0xC8, 0x5A),
    "d6": (0x4D, 0x8B, 0xFF),
    "d8": (0x96, 0x46, 0xFF),
    "d10": (0xFF, 0x8C, 0x1E),
    "d12": (0xF0, 0x32, 0x3C),
    "d20": (0x14, 0xD2, 0xC8),
}
GOLD = (0xFF, 0xC1, 0x07)
FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def font(size):
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def frame(die, i):
    return Image.open(FRAMES / die / f"{die}_{i}.png").convert("RGB")


def px(v):
    return v * SCALE


def slot_centre(slot, slots=12, start=315):
    radius = SCREEN / 2 - px(40)
    rad = math.radians(start + slot * 360 / slots)
    return SCREEN / 2 + radius * math.sin(rad), SCREEN / 2 - radius * math.cos(rad)


def round_mask(img):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, img.width - 1, img.height - 1), fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def watch_screen(die, die_x_offset=0, extra=None, rolls=()):
    """Compose one watch screen: die in the centre, rolls around the edge."""
    img = Image.new("RGB", (SCREEN, SCREEN), (0, 0, 0))
    d = ImageDraw.Draw(img)
    top = (SCREEN - 200) // 2
    img.paste(frame(die, 5), ((SCREEN - 200) // 2 + die_x_offset, top))
    if extra:
        name, x = extra
        img.paste(frame(name, 5), (x, top))
    text_font = font(round(px(30)))
    for slot, (value, colour_die) in enumerate(rolls):
        cx, cy = slot_centre(slot)
        d.text((cx, cy), str(value), font=text_font, fill=COLORS[colour_die], anchor="mm")
    if len(rolls) >= 2:
        cx, cy = slot_centre(len(rolls))
        w, h = px(76), px(40)
        d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=h / 2, fill=GOLD)
        d.text((cx, cy), f"+{sum(v for v, _ in rolls)}", font=text_font, fill=(0, 0, 0), anchor="mm")
    return round_mask(img)


def on_dark(img, pad=24):
    canvas = Image.new("RGB", (img.width + pad * 2, img.height + pad * 2), (24, 24, 28))
    canvas.paste(img, (pad, pad), img)
    return canvas


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    rolls = [(14, "d20"), (5, "d6"), (17, "d20"), (2, "d4"), (9, "d12")]
    on_dark(watch_screen("d20", rolls=rolls)).save(OUT / "rolls.png")

    # Mid-swipe: the D6 is leaving left while the D8 scrolls in from the right.
    on_dark(watch_screen("d6", die_x_offset=-120, extra=("d8", 240))).save(OUT / "swipe.png")

    # One screen per die.
    sample = {"d4": 3, "d6": 5, "d8": 6, "d10": 8, "d12": 11, "d20": 17}
    shots = [on_dark(watch_screen(die, rolls=[(sample[die], die)])) for die in DICE]
    w, h = shots[0].size
    sheet = Image.new("RGB", (w * 3, h * 2), (24, 24, 28))
    for i, shot in enumerate(shots):
        sheet.paste(shot, ((i % 3) * w, (i // 3) * h))
    sheet.save(OUT / "dice.png")

    # Looping spin of the D20 at the app's playback rate (17 fps).
    spin = [frame("d20", i).convert("P", palette=Image.ADAPTIVE, colors=128) for i in range(24)]
    spin[0].save(OUT / "d20-spin.gif", save_all=True, append_images=spin[1:], duration=round(1000 / 17), loop=0)
    print("wrote", ", ".join(p.name for p in sorted(OUT.iterdir())))


if __name__ == "__main__":
    main()
