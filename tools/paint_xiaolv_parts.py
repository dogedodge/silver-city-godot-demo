#!/usr/bin/env python3
"""Paint 小绿 (Xiaolv) clay-chibi body-part textures for Skeleton2D cutout animation.

All parts are drawn in one shared left-facing standing pose (hips at origin, Y down),
then cropped and rotated so Bone2D's +X axis runs joint → distal. Pivots go to parts.json.

Regenerate: python3 tools/paint_xiaolv_parts.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "assets" / "sprites" / "xiaolv_parts"

# Bright clay / Nendoroid palette (side-view reference).
HAIR = (0.86, 0.87, 0.89)
HAIR_D = (0.72, 0.73, 0.76)
SKIN = (0.98, 0.86, 0.80)
SKIN_D = (0.93, 0.74, 0.70)
EYE = (0.38, 0.68, 0.36)
MINT = (0.67, 0.81, 0.64)
MINT_D = (0.50, 0.68, 0.50)
DRESS = (0.22, 0.22, 0.25)
DRESS_H = (0.36, 0.36, 0.40)
WHITE = (0.97, 0.96, 0.95)
WHITE_D = (0.88, 0.87, 0.85)
INK = (0.12, 0.12, 0.14)
BLUSH = (0.98, 0.72, 0.70)

# Shared rig (pixels). Godot scripts mirror these numbers.
HIPS = (0.0, 0.0)
NECK = (0.0, -74.0)
CROWN = (4.0, -150.0)
SHOULDER = (-4.0, -58.0)
ELBOW = (-10.0, -16.0)
HAND = (-18.0, 22.0)
HIP_JOINT = (0.0, 6.0)
KNEE = (-2.0, 52.0)
ANKLE = (-4.0, 100.0)
WING_ROOT = (18.0, -52.0)
WING_TIP = (56.0, -64.0)
TAIL0 = (20.0, 8.0)
TAIL1 = (52.0, 2.0)
TAIL2 = (80.0, -18.0)
TAIL3 = (98.0, -46.0)

ORIGIN = (220.0, 280.0)  # canvas placement of hips


def W(x, y):
    """Character space → canvas pixels."""
    return (ORIGIN[0] + x, ORIGIN[1] + y)


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-8), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Canvas:
    def __init__(self, w=440, h=520):
        self.w = w
        self.h = h
        self.rgba = np.zeros((h, w, 4), np.float32)
        ys, xs = np.mgrid[0:h, 0:w]
        self.xs = xs.astype(np.float32) + 0.5
        self.ys = ys.astype(np.float32) + 0.5

    def stamp(self, sdf, color, softness=1.25, light=(-0.28, -0.9), spec=0.28, k=1.0):
        g_y, g_x = np.gradient(sdf)
        nlen = np.sqrt(g_x * g_x + g_y * g_y) + 1e-6
        nx, ny = g_x / nlen, g_y / nlen
        ndotl = np.clip(nx * light[0] + ny * light[1], 0.0, 1.0)
        wrap = 0.70 + 0.30 * ndotl
        highlight = np.power(ndotl, 10.0) * spec
        col = np.array(color, np.float32) * k
        rgb = np.clip(col[None, None, :] * wrap[..., None] + highlight[..., None], 0, 1)
        a = _smoothstep(softness, -softness, sdf)
        dst = self.rgba
        src_a = a
        self.rgba[..., :3] = rgb * src_a[..., None] + dst[..., :3] * (1.0 - src_a[..., None])
        self.rgba[..., 3] = src_a + dst[..., 3] * (1.0 - src_a)

    def circle(self, xy, r, color, **kw):
        cx, cy = xy
        sdf = np.sqrt((self.xs - cx) ** 2 + (self.ys - cy) ** 2) - r
        self.stamp(sdf, color, **kw)

    def ellipse(self, xy, rx, ry, color, rot=0.0, **kw):
        cx, cy = xy
        ca, sa = math.cos(rot), math.sin(rot)
        dx, dy = self.xs - cx, self.ys - cy
        lx = ca * dx + sa * dy
        ly = -sa * dx + ca * dy
        sdf = (np.sqrt((lx / (rx + 1e-6)) ** 2 + (ly / (ry + 1e-6)) ** 2) - 1.0) * 0.5 * (rx + ry)
        self.stamp(sdf, color, **kw)

    def capsule(self, a, b, r, color, **kw):
        x1, y1 = a
        x2, y2 = b
        px, py = self.xs, self.ys
        vx, vy = x2 - x1, y2 - y1
        l2 = vx * vx + vy * vy + 1e-6
        t = np.clip(((px - x1) * vx + (py - y1) * vy) / l2, 0.0, 1.0)
        sdf = np.sqrt((px - (x1 + t * vx)) ** 2 + (py - (y1 + t * vy)) ** 2) - r
        self.stamp(sdf, color, **kw)

    def stripe_capsule(self, a, b, r, c_a, c_b, period, phase=0.0, **kw):
        x1, y1 = a
        x2, y2 = b
        px, py = self.xs, self.ys
        vx, vy = x2 - x1, y2 - y1
        length = math.hypot(vx, vy) + 1e-6
        l2 = vx * vx + vy * vy + 1e-6
        t = np.clip(((px - x1) * vx + (py - y1) * vy) / l2, 0.0, 1.0)
        sdf = np.sqrt((px - (x1 + t * vx)) ** 2 + (py - (y1 + t * vy)) ** 2) - r
        stripe = np.floor((t * length + phase) / period) % 2.0
        self.stamp(sdf, c_a, **kw)
        self.stamp(np.where(stripe > 0.5, sdf, sdf + 80.0), c_b, **kw)

    def to_image(self) -> Image.Image:
        return Image.fromarray(np.clip(self.rgba * 255.0, 0, 255).astype(np.uint8), "RGBA")


def crop_and_pivot(im: Image.Image, pivot, pad=5):
    a = np.array(im)[..., 3]
    ys, xs = np.where(a > 10)
    if len(xs) == 0:
        return im, (float(pivot[0]), float(pivot[1]))
    x0 = max(0, int(xs.min()) - pad)
    y0 = max(0, int(ys.min()) - pad)
    x1 = min(im.width, int(xs.max()) + 1 + pad)
    y1 = min(im.height, int(ys.max()) + 1 + pad)
    return im.crop((x0, y0, x1, y1)), (pivot[0] - x0, pivot[1] - y0)


def rotate_around(im: Image.Image, pivot, angle_deg: float):
    px, py = float(pivot[0]), float(pivot[1])
    w, h = im.size
    rad = int(math.hypot(max(px, w - px), max(py, h - py)) + 8)
    canvas = Image.new("RGBA", (rad * 2, rad * 2), (0, 0, 0, 0))
    canvas.paste(im, (rad - int(round(px)), rad - int(round(py))), im)
    rot = canvas.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=False)
    return rot, (float(rad), float(rad))


def orient_along_bone(im: Image.Image, pivot, distal):
    dx = float(distal[0] - pivot[0])
    dy = float(distal[1] - pivot[1])
    angle = -math.degrees(math.atan2(dy, dx))
    rot, new_pivot = rotate_around(im, pivot, angle)
    return crop_and_pivot(rot, new_pivot, pad=3)


def save_part(name, im, pivot, distal, catalog):
    oriented, opivot = orient_along_bone(im, pivot, distal)
    oriented.save(OUT / f"{name}.png")
    catalog[name] = {
        "file": f"{name}.png",
        "pivot": [round(float(opivot[0]), 2), round(float(opivot[1]), 2)],
        "width": oriented.width,
        "height": oriented.height,
    }
    upright, upivot = crop_and_pivot(im, pivot, pad=3)
    return upright, upivot


# ----- parts (each on its own layer, same character space) -----
def paint_head():
    c = Canvas()
    hair_c = W(-4, -112)
    # Bun (back)
    bun = W(50, -122)
    c.circle(bun, 22, HAIR)
    c.circle((bun[0] + 3, bun[1] + 5), 16, HAIR_D, k=0.96)
    # Hair sphere
    c.circle(hair_c, 64, HAIR)
    c.ellipse((hair_c[0] + 8, hair_c[1] + 10), 54, 52, HAIR_D, k=0.95)
    c.circle((hair_c[0] - 6, hair_c[1] - 6), 50, HAIR)
    # Hair tie + ribbons
    tie = W(52, -102)
    c.circle(tie, 9, INK)
    c.ellipse((tie[0] - 7, tie[1] + 20), 5.5, 14, INK, rot=0.28)
    c.ellipse((tie[0] + 9, tie[1] + 18), 5.0, 13, INK, rot=-0.38)
    # Headdress
    hat = W(-2, -150)
    c.ellipse(hat, 38, 14, WHITE, rot=-0.06)
    c.ellipse((hat[0] - 20, hat[1] + 4), 13, 9, WHITE)
    c.ellipse((hat[0] + 20, hat[1] + 2), 13, 9, WHITE)
    for dx in (-28, -14, 0, 14, 28):
        c.circle((hat[0] + dx, hat[1] + 12), 7.5, WHITE)
    # Horn grows out of the bun/headdress, curves up and a bit forward
    h0 = W(22, -142)
    h1 = W(8, -166)
    h2 = W(-4, -178)
    c.capsule(h0, h1, 7.5, MINT)
    c.capsule(h1, h2, 6.2, MINT)
    c.circle(h2, 6.5, MINT)
    c.circle(h0, 7.0, MINT_D, k=0.95)
    # Pointed ear
    ear = W(30, -110)
    c.ellipse(ear, 12, 20, SKIN, rot=-0.62)
    c.ellipse((ear[0] + 1, ear[1] + 2), 7, 12, SKIN_D, rot=-0.62, k=0.97)
    # Face sits on the front-left of the sphere
    face = W(-36, -108)
    c.circle(face, 34, SKIN)
    c.ellipse((face[0] + 4, face[1] + 8), 26, 24, SKIN_D, k=0.96)
    c.circle((face[0] - 2, face[1] - 4), 22, SKIN)
    # Bangs
    c.ellipse(W(-24, -134), 24, 15, HAIR, rot=-0.32)
    c.ellipse(W(-48, -122), 13, 16, HAIR, rot=0.18)
    # Eye centered on the face
    eye = W(-48, -110)
    c.ellipse(eye, 9, 12.5, EYE)
    c.circle((eye[0] - 3, eye[1] - 4), 3.1, WHITE, spec=0.0)
    # Cute U-smile + blush
    c.capsule(W(-56, -92), W(-50, -90), 1.5, (0.55, 0.32, 0.32), spec=0.0)
    c.capsule(W(-50, -90), W(-44, -92), 1.5, (0.55, 0.32, 0.32), spec=0.0)
    c.circle(W(-60, -98), 6.5, BLUSH, spec=0.0, k=0.8)
    # Neck
    c.capsule(W(0, -80), W(0, -66), 10, SKIN)
    return c.to_image(), W(*NECK), W(*CROWN)


def paint_torso():
    c = Canvas()
    waist = W(*HIPS)
    neck = W(0, -66)
    # Bodice
    c.capsule(neck, W(0, -12), 20, DRESS)
    c.ellipse(W(0, -42), 24, 26, DRESS)
    # Knee-length skirt bell (leave room for boots)
    c.ellipse(W(2, 18), 40, 28, DRESS)
    c.ellipse(W(2, 28), 46, 22, DRESS)
    # Petticoat scallops at hem
    for dx in (-40, -24, -8, 8, 24, 40):
        c.circle(W(dx, 46), 10, WHITE)
    c.ellipse(W(0, 38), 46, 10, WHITE)
    # Off-shoulder white trim
    c.capsule(W(-22, -64), W(22, -64), 5.5, WHITE)
    c.circle(W(-24, -62), 6.5, WHITE)
    c.circle(W(24, -62), 6.5, WHITE)
    # Chest X
    c.capsule(W(-7, -46), W(7, -34), 2.2, WHITE, spec=0.0)
    c.capsule(W(7, -46), W(-7, -34), 2.2, WHITE, spec=0.0)
    # Choker
    c.ellipse(W(0, -70), 14, 6, INK)
    c.circle(W(0, -64), 3.0, (0.62, 0.62, 0.65), spec=0.4)
    # Apron (front / left) — smaller, sits on the skirt
    c.ellipse(W(-22, 6), 18, 24, WHITE)
    for dx, dy in ((-32, 26), (-22, 30), (-12, 30), (-4, 26)):
        c.circle(W(dx, dy), 7, WHITE)
    # Waistband
    c.capsule(W(-20, -6), W(20, -6), 4.5, WHITE_D)
    # Back bow
    c.ellipse(W(30, -14), 12, 8, INK, rot=0.45)
    c.ellipse(W(44, -12), 12, 8, INK, rot=-0.45)
    c.circle(W(36, -8), 5, INK)
    return c.to_image(), waist, neck


def paint_upper_arm():
    c = Canvas()
    a, b = W(*SHOULDER), W(*ELBOW)
    c.ellipse(((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5 - 4), 18, 24, DRESS)
    c.circle(a, 14, DRESS_H, k=1.04)
    c.circle(b, 12, DRESS)
    c.ellipse(b, 12, 6, WHITE)
    return c.to_image(), a, b


def paint_forearm():
    c = Canvas()
    a, b = W(*ELBOW), W(*HAND)
    c.capsule(a, b, 9, SKIN)
    c.circle(a, 9.5, SKIN)
    c.circle(b, 12.5, SKIN)
    c.circle((b[0] - 10, b[1] + 2), 6, SKIN)  # thumb toward facing
    c.circle((b[0] - 2, b[1] + 10), 5.5, SKIN)
    return c.to_image(), a, b


def paint_thigh():
    c = Canvas()
    a, b = W(*HIP_JOINT), W(*KNEE)
    c.capsule(a, b, 13, DRESS)
    c.circle(a, 14, DRESS)
    c.circle(b, 12, DRESS)
    return c.to_image(), a, b


def paint_shin():
    c = Canvas()
    a = W(*KNEE)
    boot = W(*ANKLE)
    toe = W(-24, 106)
    c.capsule(a, boot, 11, DRESS)
    c.circle(a, 12, DRESS)
    c.ellipse(boot, 18, 20, DRESS)
    c.capsule(boot, toe, 11, DRESS)
    c.circle(toe, 9, DRESS)
    c.circle(W(-10, 96), 4.0, MINT, spec=0.4)
    c.circle(W(2, 90), 3.2, MINT, spec=0.4)
    c.circle(W(-20, 106), 3.0, MINT, spec=0.4)
    return c.to_image(), a, boot


def paint_wing():
    c = Canvas()
    root = W(*WING_ROOT)
    tip = W(*WING_TIP)
    # Cute small bat wing: two soft lobes, not hard triangles.
    c.circle(root, 9, MINT_D)
    c.ellipse((root[0] + 22, root[1] - 16), 24, 16, MINT, rot=-0.35)
    c.ellipse((root[0] + 26, root[1] + 6), 22, 15, MINT, rot=0.25)
    c.ellipse((root[0] + 8, root[1] + 16), 14, 12, MINT, rot=0.6)
    c.capsule(root, tip, 8, MINT)
    c.capsule(root, (root[0] + 20, root[1] - 22), 3.0, MINT_D, spec=0.0)
    c.capsule(root, (root[0] + 28, root[1] + 10), 3.0, MINT_D, spec=0.0)
    return c.to_image(), root, tip


def paint_tail(a, b, r, phase, tip=False):
    c = Canvas()
    aa, bb = W(*a), W(*b)
    if tip:
        c.stripe_capsule(aa, bb, r, MINT, INK, period=16, phase=phase)
        c.circle(bb, r + 1.5, MINT)
    else:
        c.stripe_capsule(aa, bb, r, INK, MINT, period=16, phase=phase)
    c.circle(aa, r - 0.5, INK if not tip else MINT)
    return c.to_image(), aa, bb


def paste(dst, src, pivot, world_xy):
    dst.alpha_composite(src, (int(round(world_xy[0] - pivot[0])), int(round(world_xy[1] - pivot[1]))))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {
        "layout": {
            "hips": list(HIPS),
            "neck": list(NECK),
            "crown": list(CROWN),
            "shoulder": list(SHOULDER),
            "elbow": list(ELBOW),
            "hand": list(HAND),
            "hip_joint": list(HIP_JOINT),
            "knee": list(KNEE),
            "ankle": list(ANKLE),
            "wing_root": list(WING_ROOT),
            "wing_tip": list(WING_TIP),
            "tail0": list(TAIL0),
            "tail1": list(TAIL1),
            "tail2": list(TAIL2),
            "tail3": list(TAIL3),
        }
    }
    previews = {}

    jobs = [
        ("head", paint_head),
        ("torso", paint_torso),
        ("upper_arm", paint_upper_arm),
        ("forearm", paint_forearm),
        ("thigh", paint_thigh),
        ("shin", paint_shin),
        ("wing", paint_wing),
        ("tail_a", lambda: paint_tail(TAIL0, TAIL1, 11, 0.0, False)),
        ("tail_b", lambda: paint_tail(TAIL1, TAIL2, 10, 8.0, False)),
        ("tail_c", lambda: paint_tail(TAIL2, TAIL3, 9, 0.0, True)),
    ]
    for name, fn in jobs:
        im, pivot, distal = fn()
        upright, upivot = save_part(name, im, pivot, distal, catalog)
        previews[name] = (upright, upivot)
        meta = catalog[name]
        print(f"  {name:12s} {meta['width']}x{meta['height']}  pivot={meta['pivot']}")

    preview = Image.new("RGBA", (440, 520), (0, 0, 0, 0))
    # Back → front, matching Godot z-order.
    paste(preview, *previews["wing"], W(*WING_ROOT))
    paste(preview, *previews["tail_a"], W(*TAIL0))
    paste(preview, *previews["tail_b"], W(*TAIL1))
    paste(preview, *previews["tail_c"], W(*TAIL2))
    paste(preview, *previews["upper_arm"], W(*SHOULDER))
    paste(preview, *previews["forearm"], W(*ELBOW))
    paste(preview, *previews["thigh"], W(*HIP_JOINT))
    paste(preview, *previews["shin"], W(*KNEE))
    paste(preview, *previews["torso"], W(*HIPS))
    paste(preview, *previews["thigh"], W(-6, 6))
    paste(preview, *previews["shin"], W(-8, 52))
    paste(preview, *previews["head"], W(*NECK))
    paste(preview, *previews["upper_arm"], W(-10, -58))
    paste(preview, *previews["forearm"], W(-16, -16))
    preview, _ = crop_and_pivot(preview, W(*HIPS), pad=10)
    # Flatten onto white for a readable rest silhouette.
    bg = Image.new("RGBA", preview.size, (250, 249, 247, 255))
    bg.alpha_composite(preview)
    bg.convert("RGB").save(OUT / "preview_rest.png")
    catalog["_note"] = (
        "Pivots are in the bone-oriented PNG (joint on the left, distal +X). "
        "Parent Sprite2D to Bone2D with centered=false and position=-pivot."
    )
    (OUT / "parts.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"Wrote parts to {OUT}")


if __name__ == "__main__":
    main()
