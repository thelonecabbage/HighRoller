"""Render the D6 spin animation as a PNG frame sequence for IMG_ANIM.

Usage (from high-roller/): python3 scripts/render_d6.py
Requires: Pillow, numpy.
"""
import math
from itertools import product
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

FRAMES = 24
OUT_SIZE = 200
SS = 3  # supersampling factor
BASE_COLOR = np.array([40, 110, 255], dtype=float)
CHAMFER = 0.74  # inset of the bevelled edges; 1.0 would be a sharp cube
LIGHT = np.array([-0.4, 0.6, 0.7])
LIGHT /= np.linalg.norm(LIGHT)
CAMERA_DIST = 6.0

ROOT = Path(__file__).resolve().parent.parent
OUT_DIRS = [ROOT / "assets" / shape / "anim" / "d6" for shape in ("gt.r", "gt.s")]

# D6 pip layout per face (axis index, sign) -> pip count; opposite faces sum to 7.
FACE_VALUES = {(2, 1): 1, (0, 1): 2, (1, 1): 3, (1, -1): 4, (0, -1): 5, (2, -1): 6}
PIP_GRID = {
    1: [(0, 0)],
    2: [(-1, 1), (1, -1)],
    3: [(-1, 1), (0, 0), (1, -1)],
    4: [(-1, 1), (1, 1), (-1, -1), (1, -1)],
    5: [(-1, 1), (1, 1), (0, 0), (-1, -1), (1, -1)],
    6: [(-1, 1), (1, 1), (-1, 0), (1, 0), (-1, -1), (1, -1)],
}


def unit(axis, value):
    v = np.zeros(3)
    v[axis] = value
    return v


def build_chamfered_cube():
    """Return (kind, polygon vertices Nx3) for every facet of a chamfered cube."""
    c = CHAMFER
    facets = []
    for a, s in product(range(3), (1, -1)):
        b, t = [i for i in range(3) if i != a]
        quad = []
        for sb, st in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            quad.append(unit(a, s) + unit(b, sb * c) + unit(t, st * c))
        facets.append(("face", np.array(quad), (a, s)))
    for a, b in ((0, 1), (0, 2), (1, 2)):
        t = 3 - a - b
        for sa, sb in product((1, -1), repeat=2):
            quad = [
                unit(a, sa) + unit(b, sb * c) + unit(t, -c),
                unit(a, sa) + unit(b, sb * c) + unit(t, c),
                unit(b, sb) + unit(a, sa * c) + unit(t, c),
                unit(b, sb) + unit(a, sa * c) + unit(t, -c),
            ]
            facets.append(("edge", np.array(quad), None))
    for sx, sy, sz in product((1, -1), repeat=3):
        tri = [
            np.array([sx, sy * c, sz * c]),
            np.array([sx * c, sy, sz * c]),
            np.array([sx * c, sy * c, sz]),
        ]
        facets.append(("corner", np.array(tri), None))
    return facets


def build_pips(face_key):
    a, s = face_key
    b, t = [i for i in range(3) if i != a]
    spacing = CHAMFER * 0.5
    radius = 0.15
    pips = []
    for gu, gv in PIP_GRID[FACE_VALUES[face_key]]:
        centre = unit(a, s * 1.002) + unit(b, gu * spacing) + unit(t, gv * spacing)
        ring = []
        for k in range(20):
            ang = 2 * math.pi * k / 20
            ring.append(centre + unit(b, radius * math.cos(ang)) + unit(t, radius * math.sin(ang)))
        pips.append(np.array(ring))
    return pips


def rotation(t):
    ax, ay, az = 2 * math.pi * t, 4 * math.pi * t, 2 * math.pi * t * 0
    rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    tilt = math.radians(28)
    rt = np.array([[1, 0, 0], [0, math.cos(tilt), -math.sin(tilt)], [0, math.sin(tilt), math.cos(tilt)]])
    return rt @ ry @ rx


def project(points, size):
    scale = 0.29 * size
    persp = CAMERA_DIST / (CAMERA_DIST - points[:, 2])
    xs = size / 2 + points[:, 0] * persp * scale
    ys = size / 2 - points[:, 1] * persp * scale
    return [(float(x), float(y)) for x, y in zip(xs, ys)]


def shade(normal):
    front = normal[2] > 0
    diff = max(0.0, float(normal @ LIGHT))
    half = LIGHT + np.array([0, 0, 1.0])
    half /= np.linalg.norm(half)
    spec = max(0.0, float(normal @ half)) ** 24
    if not front:
        # Back facets glimpse through the glass, darker and fainter.
        rgb = BASE_COLOR * 0.35
        alpha = 0.16
    else:
        rgb = BASE_COLOR * (0.45 + 0.55 * diff) + 255 * spec * 0.7
        alpha = 0.30 + 0.25 * diff + 0.35 * spec
    rgb = np.clip(rgb, 0, 255)
    return tuple(int(v) for v in rgb), min(alpha, 0.95), front


def composite(canvas, draw_fn):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    return Image.alpha_composite(canvas, layer)


def render_frame(facets, pips_by_face, t):
    size = OUT_SIZE * SS
    rot = rotation(t)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 255))

    items = []
    for kind, verts, key in facets:
        world = verts @ rot.T
        normal = np.cross(world[1] - world[0], world[2] - world[0])
        normal /= np.linalg.norm(normal)
        # Winding differs per facet type; make the normal point away from the centre.
        if normal @ world.mean(axis=0) < 0:
            normal = -normal
        depth = float(world[:, 2].mean())
        items.append((depth, "facet", world, normal, kind))
        if key is not None:
            for ring in pips_by_face[key]:
                pw = ring @ rot.T
                items.append((depth + 0.01, "pip", pw, normal, kind))
    items.sort(key=lambda it: it[0])

    line_w = max(1, SS)
    for _, what, world, normal, _kind in items:
        poly = project(world, size)
        rgb, alpha, front = shade(normal)
        if what == "facet":
            fill = rgb + (int(alpha * 255),)
            edge_alpha = int((0.75 if front else 0.25) * 255)
            canvas = composite(canvas, lambda d: d.polygon(poly, fill=fill))
            canvas = composite(
                canvas,
                lambda d: d.line(poly + [poly[0]], fill=(190, 225, 255, edge_alpha), width=line_w),
            )
        else:
            pip_alpha = int((0.9 if front else 0.22) * 255)
            canvas = composite(canvas, lambda d: d.polygon(poly, fill=(225, 240, 255, pip_alpha)))

    rgb_img = canvas.convert("RGB")
    glow = rgb_img.filter(ImageFilter.GaussianBlur(12 * SS)).point(lambda v: int(v * 0.6))
    rgb_img = ImageChops.add(rgb_img, glow)
    return rgb_img.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)


def main():
    facets = build_chamfered_cube()
    pips_by_face = {key: build_pips(key) for key in FACE_VALUES}
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(FRAMES):
        frame = render_frame(facets, pips_by_face, i / FRAMES)
        for out_dir in OUT_DIRS:
            frame.save(out_dir / f"d6_{i}.png", optimize=True)
        print(f"frame {i + 1}/{FRAMES}")


if __name__ == "__main__":
    main()
