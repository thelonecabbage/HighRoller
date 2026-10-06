"""Render README preview images from the animation frames (no watch or simulator needed).

Usage (from high-roller/): python3 scripts/render_screenshots.py
Requires: Pillow. Writes to docs/images/, plus 360x360 sets to docs/images/demo/ (round)
and docs/images/demo-square/ (square).
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FRAMES = ROOT / "assets" / "gt.r" / "anim"
OUT = ROOT / "docs" / "images"
SCREEN = 466  # Amazfit GTR 4
SQUARE_SCREEN = 390  # square-screen layout (width of the Amazfit GTS series)
DEMO_SIZE = 360
ICON_SIZE = 240
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


def px(v, screen=SCREEN):
    return v * screen / 480  # same scaling as px() in the app


def slot_centre(slot, screen, slots=12, start=315):
    radius = screen / 2 - px(40, screen)
    rad = math.radians(start + slot * 360 / slots)
    return screen / 2 + radius * math.sin(rad), screen / 2 - radius * math.cos(rad)


def screen_mask(img, shape):
    mask = Image.new("L", img.size, 0)
    box = (0, 0, img.width - 1, img.height - 1)
    if shape == "round":
        ImageDraw.Draw(mask).ellipse(box, fill=255)
    else:
        ImageDraw.Draw(mask).rounded_rectangle(box, radius=img.width // 9, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def watch_screen(die, die_x_offset=0, extra=None, rolls=(), index=5, screen=SCREEN, shape="round"):
    """Compose one watch screen: die in the centre, rolls around the edge.

    extra is (die name, x offset from centre) for a second die mid-swipe.
    """
    img = Image.new("RGB", (screen, screen), (0, 0, 0))
    d = ImageDraw.Draw(img)
    left = (screen - 200) // 2
    top = left
    img.paste(frame(die, index), (left + die_x_offset, top))
    if extra:
        name, x_offset = extra
        img.paste(frame(name, 5), (left + x_offset, top))
    text_font = font(round(px(30, screen)))
    for slot, (value, colour_die) in enumerate(rolls):
        cx, cy = slot_centre(slot, screen)
        d.text((cx, cy), str(value), font=text_font, fill=COLORS[colour_die], anchor="mm")
    if len(rolls) >= 2:
        cx, cy = slot_centre(len(rolls), screen)
        w, h = px(76, screen), px(40, screen)
        d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=h / 2, fill=GOLD)
        d.text((cx, cy), f"+{sum(v for v, _ in rolls)}", font=text_font, fill=(0, 0, 0), anchor="mm")
    return screen_mask(img, shape)


def on_dark(img, pad=24):
    canvas = Image.new("RGB", (img.width + pad * 2, img.height + pad * 2), (24, 24, 28))
    canvas.paste(img, (pad, pad), img)
    return canvas


def write_demo(folder, screen, shape, rolls, sample):
    """One DEMO_SIZE x DEMO_SIZE image per screen, plus a spinning D20 GIF."""
    folder.mkdir(parents=True, exist_ok=True)

    def shot(*args, **kwargs):
        img = watch_screen(*args, screen=screen, shape=shape, **kwargs)
        return on_dark(img).resize((DEMO_SIZE, DEMO_SIZE), Image.LANCZOS)

    shot("d20", rolls=rolls).save(folder / "rolls.png")
    shot("d6", die_x_offset=-120, extra=("d8", 107), rolls=rolls[:3]).save(folder / "swipe.png")
    for die in DICE:
        shot(die, rolls=sample[die]).save(folder / f"{die}.png")
    spin = [
        shot("d20", rolls=rolls, index=i).convert("P", palette=Image.ADAPTIVE, colors=128)
        for i in range(24)
    ]
    spin[0].save(folder / "d20-spin.gif", save_all=True, append_images=spin[1:], duration=round(1000 / 17), loop=0)


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    rolls = [(14, "d20"), (5, "d6"), (17, "d20"), (2, "d4"), (9, "d12")]
    on_dark(watch_screen("d20", rolls=rolls)).save(OUT / "rolls.png")

    # Mid-swipe: the D6 is leaving left while the D8 scrolls in from the right.
    on_dark(watch_screen("d6", die_x_offset=-120, extra=("d8", 107), rolls=rolls[:3])).save(OUT / "swipe.png")

    # One screen per die.
    sample = {
        "d4": [(3, "d4"), (2, "d4"), (4, "d4")],
        "d6": [(5, "d6"), (2, "d6"), (6, "d6")],
        "d8": [(6, "d8"), (3, "d8"), (8, "d8")],
        "d10": [(8, "d10"), (10, "d10"), (4, "d10")],
        "d12": [(11, "d12"), (7, "d12"), (12, "d12")],
        "d20": [(17, "d20"), (9, "d20"), (20, "d20")],
    }
    shots = [on_dark(watch_screen(die, rolls=sample[die])) for die in DICE]
    w, h = shots[0].size
    sheet = Image.new("RGB", (w * 3, h * 2), (24, 24, 28))
    for i, shot in enumerate(shots):
        sheet.paste(shot, ((i % 3) * w, (i // 3) * h))
    sheet.save(OUT / "dice.png")

    # Looping spin of the D20 at the app's playback rate (17 fps).
    spin = [frame("d20", i).convert("P", palette=Image.ADAPTIVE, colors=128) for i in range(24)]
    spin[0].save(OUT / "d20-spin.gif", save_all=True, append_images=spin[1:], duration=round(1000 / 17), loop=0)
    print("wrote", ", ".join(p.name for p in sorted(OUT.iterdir())))

    write_demo(OUT / "demo", SCREEN, "round", rolls, sample)
    write_demo(OUT / "demo-square", SQUARE_SCREEN, "square", rolls, sample)
    print("wrote demo and demo-square sets")
    icon_dir = ROOT / "docs" / "app-icon"
    icon_dir.mkdir(exist_ok=True)
    icon = Image.open(ROOT / "assets" / "gt.r" / "icon.png").convert("RGBA")
    icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS).save(icon_dir / "app-icon.png", optimize=True)


if __name__ == "__main__":
    main()
