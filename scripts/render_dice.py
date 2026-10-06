"""Render D4/D8/D10/D12/D20 spin animations as PNG frame sequences for IMG_ANIM.

Usage (from high-roller/): python3 scripts/render_dice.py [d4 d8 ...]
Requires: Pillow, numpy. The D6 (pips, blue) lives in render_d6.py.
"""
import math
import sys
from itertools import product
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from render_d6 import FRAMES, LIGHT, OUT_SIZE, SS, composite, project, rotation

ROOT = Path(__file__).resolve().parent.parent
CIRCUMRADIUS = 1.4
PHI = (1 + math.sqrt(5)) / 2
FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
TEXTURE = 96

COLORS = {
    "d4": (40, 200, 90),
    "d8": (150, 70, 255),
    "d10": (255, 140, 30),
    "d12": (240, 50, 60),
    "d20": (20, 210, 200),
}


def faces_from_normals(verts, normals):
    """Group vertices lying on each supporting plane and order them around the normal."""
    faces = []
    for n in normals:
        n = np.asarray(n, dtype=float)
        n /= np.linalg.norm(n)
        dots = verts @ n
        idx = [i for i, d in enumerate(dots) if d > dots.max() - 1e-5]
        centre = verts[idx].mean(axis=0)
        ref = verts[idx[0]] - centre
        ref /= np.linalg.norm(ref)
        side = np.cross(n, ref)
        idx.sort(key=lambda i: math.atan2((verts[i] - centre) @ side, (verts[i] - centre) @ ref))
        faces.append(idx)
    return faces


def tetrahedron():
    v = np.array([(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)], dtype=float)
    return v, faces_from_normals(v, -v)


def octahedron():
    v = np.array([s * np.eye(3)[a] for a in range(3) for s in (1, -1)], dtype=float)
    return v, faces_from_normals(v, list(product((1, -1), repeat=3)))


def dodecahedron():
    ip = 1 / PHI
    v = [p for p in product((1, -1), repeat=3)]
    for a, b in product((1, -1), repeat=2):
        v += [(0, a * ip, b * PHI), (a * ip, b * PHI, 0), (b * PHI, 0, a * ip)]
    v = np.array(v, dtype=float)
    normals = []
    for a, b in product((1, -1), repeat=2):
        normals += [(a, 0, b * PHI), (b * PHI, a, 0), (0, b * PHI, a)]
    return v, faces_from_normals(v, normals)


def icosahedron():
    v = []
    for a, b in product((1, -1), repeat=2):
        v += [(0, a, b * PHI), (a, b * PHI, 0), (b * PHI, 0, a)]
    v = np.array(v, dtype=float)
    ip = 1 / PHI
    normals = list(product((1, -1), repeat=3))
    for a, b in product((1, -1), repeat=2):
        normals += [(a * ip, 0, b * PHI), (b * PHI, a * ip, 0), (0, b * PHI, a * ip)]
    return v, faces_from_normals(v, normals)


def trapezohedron():
    """Pentagonal trapezohedron (D10): kite faces meeting at the two apexes."""
    c36 = math.cos(math.radians(36))
    height = 1.0
    ring_z = height * (1 - c36) / (1 + c36)  # keeps each kite planar
    radius = 0.9
    verts = [(0, 0, height), (0, 0, -height)]
    for k in range(5):
        a_up, a_low = math.radians(72 * k), math.radians(72 * k + 36)
        verts.append((radius * math.cos(a_up), radius * math.sin(a_up), ring_z))
        verts.append((radius * math.cos(a_low), radius * math.sin(a_low), -ring_z))
    upper = lambda k: 2 + 2 * (k % 5)
    lower = lambda k: 3 + 2 * (k % 5)
    faces = []
    for k in range(5):
        faces.append([0, upper(k), lower(k), upper(k + 1)])
        faces.append([1, lower(k), upper(k + 1), lower(k + 1)])
    return np.array(verts, dtype=float), faces


SHAPES = {
    "d4": tetrahedron,
    "d8": octahedron,
    "d10": trapezohedron,
    "d12": dodecahedron,
    "d20": icosahedron,
}


def load_font(size):
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


_texture_cache = {}


def number_texture(label):
    if label not in _texture_cache:
        img = Image.new("RGBA", (TEXTURE, TEXTURE), (240, 248, 255, 0))
        d = ImageDraw.Draw(img)
        size = 84
        while size > 8:
            font = load_font(size)
            box = d.textbbox((0, 0), str(label), font=font)
            if box[2] - box[0] <= TEXTURE * 0.9 and box[3] - box[1] <= TEXTURE * 0.9:
                break
            size -= 2
        d.text((TEXTURE / 2, TEXTURE / 2), str(label), font=font, fill=(240, 248, 255, 255), anchor="mm")
        _texture_cache[label] = img
    return _texture_cache[label]


def homography(dst, src):
    """Coefficients for PIL PERSPECTIVE: maps output points (dst) to input texture points (src)."""
    a, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        a.append([x, y, 1, 0, 0, 0, -x * u, -y * u])
        b.append(u)
        a.append([0, 0, 0, x, y, 1, -x * v, -y * v])
        b.append(v)
    return np.linalg.solve(np.array(a), np.array(b)).tolist()


def label_layout(verts):
    """Centre, up axis, and half-size of the number square on a face (model space)."""
    centre = verts.mean(axis=0)
    n = np.cross(verts[1] - verts[0], verts[2] - verts[0])
    n /= np.linalg.norm(n)
    if n @ centre < 0:
        n = -n
    up = verts[0] - centre
    up -= (up @ n) * n
    up /= np.linalg.norm(up)
    inradius = min(
        np.linalg.norm(np.cross(verts[(i + 1) % len(verts)] - verts[i], centre - verts[i]))
        / np.linalg.norm(verts[(i + 1) % len(verts)] - verts[i])
        for i in range(len(verts))
    )
    return centre, n, up, 0.72 * inradius


def shade(normal, base, front):
    diff = max(0.0, float(normal @ LIGHT))
    half = LIGHT + np.array([0, 0, 1.0])
    half /= np.linalg.norm(half)
    spec = max(0.0, float(normal @ half)) ** 24
    base = np.array(base, dtype=float)
    if not front:
        return tuple(int(v) for v in base * 0.35), 0.16
    # Flat facets reflect uniformly, so keep the highlight gentle to leave numbers legible.
    rgb = np.clip(base * (0.45 + 0.55 * diff) + 255 * spec * 0.22, 0, 255)
    return tuple(int(v) for v in rgb), min(0.30 + 0.25 * diff + 0.1 * spec, 0.95)


def render_frame(shape, faces, layouts, color, t):
    size = OUT_SIZE * SS
    rot = rotation(t)
    verts = shape @ rot.T
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 255))

    order = sorted(range(len(faces)), key=lambda i: verts[faces[i]][:, 2].mean())
    line_w = max(1, SS)
    for i in order:
        world = verts[faces[i]]
        centre, n, up, half = layouts[i]
        normal = rot @ n
        front = normal[2] > 0
        rgb, alpha = shade(normal, color, front)
        poly = project(world, size)
        fill = rgb + (int(alpha * 255),)
        edge = (200, 230, 255, int((0.75 if front else 0.25) * 255))
        canvas = composite(canvas, lambda d: d.polygon(poly, fill=fill))
        canvas = composite(canvas, lambda d: d.line(poly + [poly[0]], fill=edge, width=line_w))

        right = np.cross(up, n)
        corners = np.array(
            [centre + up * half - right * half, centre + up * half + right * half,
             centre - up * half + right * half, centre - up * half - right * half]
        )
        dst = project(corners @ rot.T, size)
        src = [(0, 0), (TEXTURE, 0), (TEXTURE, TEXTURE), (0, TEXTURE)]
        coeffs = homography(dst, src)
        text = number_texture(i + 1).transform((size, size), Image.PERSPECTIVE, coeffs, Image.BILINEAR)
        a = text.getchannel("A").point(lambda v: int(v * (0.95 if front else 0.2)))
        text.putalpha(a)
        canvas = Image.alpha_composite(canvas, text)

    rgb_img = canvas.convert("RGB")
    glow = rgb_img.filter(ImageFilter.GaussianBlur(12 * SS)).point(lambda v: int(v * 0.6))
    rgb_img = ImageChops.add(rgb_img, glow)
    return rgb_img.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)


def render_die(name):
    verts, faces = SHAPES[name]()
    verts = verts * (CIRCUMRADIUS / np.linalg.norm(verts, axis=1).max())
    layouts = [label_layout(verts[f]) for f in faces]
    out_dirs = [ROOT / "assets" / shape / "anim" / name for shape in ("gt.r", "gt.s")]
    for d in out_dirs:
        d.mkdir(parents=True, exist_ok=True)
    for i in range(FRAMES):
        frame = render_frame(verts, faces, layouts, COLORS[name], i / FRAMES)
        for d in out_dirs:
            frame.save(d / f"{name}_{i}.png", optimize=True)
    print(f"{name}: {len(faces)} faces, {FRAMES} frames")


if __name__ == "__main__":
    for die in sys.argv[1:] or list(SHAPES):
        render_die(die)
