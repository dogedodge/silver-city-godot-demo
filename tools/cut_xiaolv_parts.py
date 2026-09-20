#!/usr/bin/env python3
"""Cut 小绿 (Xiaolv) Skeleton2D parts from the clay three-view side figure.

Source: tools/refs/xiaolv_side_nendo.png (side panel matching the Nendoroid
three-view). GrabCut + flood-fill remove the studio background, then region
and color masks extract head, torso, arms, legs, wing, and tail.

Each part is rotated so Bone2D +X runs joint → distal. Crops keep the joint
pixel on the bitmap (transparent pad if the pivot sits above visible pixels).

Regenerate:
    python3 tools/cut_xiaolv_parts.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "refs" / "xiaolv_side_nendo.png"
OUT = ROOT / "assets" / "sprites" / "xiaolv_parts"
DEBUG = Path("/tmp/xiaolv_cut_debug")

# Downscale cutouts so the in-game puppet is ~280px tall (crop is ~1050px).
SCALE = 0.30


def grabcut_fg(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    mask[:12, :] = cv2.GC_BGD
    mask[-12:, :] = cv2.GC_BGD
    mask[:, :12] = cv2.GC_BGD
    mask[:, -12:] = cv2.GC_BGD
    cv2.ellipse(
        mask, (w // 2, int(h * 0.48)), (int(w * 0.18), int(h * 0.32)),
        0, 0, 360, int(cv2.GC_FGD), -1,
    )
    cv2.ellipse(
        mask, (w // 2, int(h * 0.48)), (int(w * 0.28), int(h * 0.42)),
        0, 0, 360, int(cv2.GC_PR_FGD), -1,
    )
    mask[:12, :] = cv2.GC_BGD
    mask[-12:, :] = cv2.GC_BGD
    mask[:, :12] = cv2.GC_BGD
    mask[:, -12:] = cv2.GC_BGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(rgb, mask, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    fg = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0
    ).astype(np.uint8)
    fg = cv2.morphologyEx(
        fg, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    )
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    fg = (lab == keep).astype(np.uint8)
    inv = 1 - fg
    ff = inv.copy()
    cv2.floodFill(ff, None, (0, 0), 2)
    fg[(inv == 1) & (ff == 1)] = 1
    return fg


def ellipse_mask(h, w, cx, cy, rx, ry) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    cv2.ellipse(m, (int(cx), int(cy)), (int(rx), int(ry)), 0, 0, 360, 1, -1)
    return m


def rect_mask(h, w, x0, y0, x1, y1) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (int(x0), int(y0)), (int(x1), int(y1)), 1, -1)
    return m


def poly_mask(h, w, pts) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m


def capsule_mask(h, w, x1, y1, x2, y2, r) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    cv2.line(m, (int(x1), int(y1)), (int(x2), int(y2)), 1, thickness=max(1, int(r) * 2))
    cv2.circle(m, (int(x1), int(y1)), int(r), 1, -1)
    cv2.circle(m, (int(x2), int(y2)), int(r), 1, -1)
    return m


def polyline_mask(h, w, pts, r) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    for i in range(len(pts) - 1):
        m |= capsule_mask(h, w, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], r)
    return m


def mint_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    return ((g.astype(np.int16) > r.astype(np.int16) + 12)
            & (g.astype(np.int16) > b.astype(np.int16) + 8)
            & (g > 130)).astype(np.uint8)


def skin_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[:, :, 0].astype(np.int16), rgb[:, :, 1].astype(np.int16), rgb[:, :, 2].astype(np.int16)
    return ((r > 165) & (g > 135) & (g < 220) & (b > 105) & (b < 195)
            & (r > b + 8) & (r > g - 8) & (r - b > 12)).astype(np.uint8)


def largest_cc(mask: np.ndarray) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    if n <= 1:
        return mask.astype(np.uint8)
    keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (lab == keep).astype(np.uint8)


def keep_seed(mask: np.ndarray, seed_xy) -> np.ndarray:
    sx, sy = int(seed_xy[0]), int(seed_xy[1])
    m = mask.astype(np.uint8)
    if not (0 <= sy < m.shape[0] and 0 <= sx < m.shape[1]) or m[sy, sx] == 0:
        return largest_cc(m)
    n, lab = cv2.connectedComponents(m)
    return (lab == lab[sy, sx]).astype(np.uint8)


def morph_close(mask: np.ndarray, k: int) -> np.ndarray:
    return cv2.morphologyEx(
        mask.astype(np.uint8), cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)),
    )


def dilate(mask: np.ndarray, k: int) -> np.ndarray:
    return cv2.dilate(
        mask.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)),
    )


def apply_mask(rgba: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = rgba.copy()
    out[mask == 0, 3] = 0
    return out


def strip_bg_fringe(rgba: np.ndarray) -> np.ndarray:
    """Drop near-white pixels that touch transparency (paper halo)."""
    a = rgba[:, :, 3]
    mn = rgba[:, :, :3].min(axis=2)
    trans = (a == 0).astype(np.uint8)
    edge = cv2.dilate(trans, np.ones((3, 3), np.uint8))
    kill = (mn > 248) & (edge > 0) & (a > 0)
    out = rgba.copy()
    out[kill, 3] = 0
    return out


def crop_alpha(rgba: np.ndarray, pivot, pad=4):
    """Crop to opaque pixels, but always keep the pivot on-canvas."""
    a = rgba[:, :, 3]
    ys, xs = np.where(a > 8)
    px, py = float(pivot[0]), float(pivot[1])
    xs_all = [px]
    ys_all = [py]
    if len(xs):
        xs_all += [float(xs.min()), float(xs.max())]
        ys_all += [float(ys.min()), float(ys.max())]
    x0 = max(0, int(math.floor(min(xs_all) - pad)))
    y0 = max(0, int(math.floor(min(ys_all) - pad)))
    x1 = min(rgba.shape[1], int(math.ceil(max(xs_all) + pad)) + 1)
    y1 = min(rgba.shape[0], int(math.ceil(max(ys_all) + pad)) + 1)
    return rgba[y0:y1, x0:x1], (px - x0, py - y0)


def rotate_around(im: Image.Image, pivot, angle_deg: float):
    px, py = float(pivot[0]), float(pivot[1])
    w, h = im.size
    rad = int(math.hypot(max(px, w - px), max(py, h - py)) + 8)
    canvas = Image.new("RGBA", (rad * 2, rad * 2), (0, 0, 0, 0))
    canvas.paste(im, (rad - int(round(px)), rad - int(round(py))), im)
    rot = canvas.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=False)
    return rot, (float(rad), float(rad))


def orient_along_bone(rgba, pivot, distal):
    im = Image.fromarray(rgba)
    dx = float(distal[0] - pivot[0])
    dy = float(distal[1] - pivot[1])
    angle = math.degrees(math.atan2(dy, dx))
    rot, new_pivot = rotate_around(im, pivot, angle)
    arr = np.array(rot)
    cropped, opivot = crop_alpha(arr, new_pivot, pad=3)
    return cropped, opivot


def scale_rgba(rgba, pivot, s):
    if abs(s - 1.0) < 1e-6:
        return rgba, pivot
    im = Image.fromarray(rgba)
    nw, nh = max(1, int(round(im.width * s))), max(1, int(round(im.height * s)))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    return np.array(im), (pivot[0] * s, pivot[1] * s)


def save_debug(name, rgba):
    DEBUG.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba).save(DEBUG / f"{name}.png")


def color_overlay(rgb, masks_and_colors):
    out = rgb.astype(np.float32)
    for mask, color in masks_and_colors:
        m = mask.astype(bool)
        if not m.any():
            continue
        col = np.array(color, np.float32)
        out[m] = out[m] * 0.35 + col * 0.65
    return out.clip(0, 255).astype(np.uint8)


def main():
    rgb = np.array(Image.open(SRC).convert("RGB"))
    fg = grabcut_fg(rgb)
    h, w = fg.shape
    ys, xs = np.where(fg)
    x0, y0 = int(xs.min()) - 6, int(ys.min()) - 6
    x1, y1 = int(xs.max()) + 7, int(ys.max()) + 7
    x0, y0 = max(0, x0), max(0, y0)
    rgba_full = np.zeros((h, w, 4), np.uint8)
    rgba_full[fg > 0, :3] = rgb[fg > 0]
    rgba_full[fg > 0, 3] = 255
    rgba = rgba_full[y0:y1, x0:x1]
    rgb_c = rgb[y0:y1, x0:x1]
    ch, cw = rgba.shape[:2]
    print(f"crop {cw}x{ch} origin=({x0},{y0})")
    save_debug("00_fg", rgba)

    mint = mint_mask(rgb_c)
    dark = (rgb_c.mean(axis=2) < 90).astype(np.uint8)
    skin = skin_mask(rgb_c)
    opaque = (rgba[:, :, 3] > 0).astype(np.uint8)

    # Hanging chain + mint blades (not a rigged part).
    weapon = rect_mask(ch, cw, 0, 580, 148, ch)
    weapon |= rect_mask(ch, cw, 0, 740, 175, ch)

    head_m = rect_mask(ch, cw, 40, 0, 620, 478) & opaque
    # Drop choker/chest only — keep the round chin.
    head_m &= ~rect_mask(ch, cw, 230, 470, 360, 540)
    head_m = largest_cc(head_m)

    wing_m = (mint & rect_mask(ch, cw, 345, 490, 540, 665)).astype(np.uint8)
    wing_m = morph_close(wing_m, 11)
    wing_m = largest_cc(wing_m)
    wing_m = dilate(wing_m, 3)
    wing_m &= opaque

    tail_pts = [
        (398, 718), (435, 758), (475, 808),
        (525, 842), (575, 848), (615, 808), (642, 762),
    ]
    tail_tube = polyline_mask(ch, cw, tail_pts, 30)
    tail_m = tail_tube & opaque
    tail_m &= ~head_m
    tail_m &= ~wing_m
    # Drop leftover dress pixels at the root.
    tail_m &= ~rect_mask(ch, cw, 0, 0, 385, 780)

    # Whole puffy sleeve (the blob that must leave the torso).
    apron_white = (
        (rgb_c.min(axis=2) > 200)
        & (np.arange(cw)[None, :] > 230)
        & (np.arange(ch)[:, None] > 610)
    ).astype(np.uint8)
    sleeve_zone = poly_mask(ch, cw, [
        (218, 536), (250, 552), (255, 605), (232, 648),
        (188, 652), (172, 615), (178, 558), (200, 538),
    ])
    sleeve_zone |= ellipse_mask(ch, cw, 208, 595, 50, 48)
    upper_m = sleeve_zone & opaque
    upper_m &= ~head_m
    upper_m &= ~rect_mask(ch, cw, 0, 0, cw, 526)
    upper_m &= ~weapon
    upper_m &= ~apron_white
    upper_m = morph_close(upper_m, 5)

    forearm_m = capsule_mask(ch, cw, 198, 630, 165, 695, 26)
    forearm_m |= ellipse_mask(ch, cw, 158, 705, 36, 30)
    forearm_m &= opaque
    forearm_m &= ~weapon
    forearm_m &= ~head_m
    elbow_keep = ellipse_mask(ch, cw, 198, 630, 14, 14)
    forearm_m &= ~(upper_m & ~elbow_keep)

    thigh_m = skin & rect_mask(ch, cw, 255, 848, 355, 928)
    thigh_m = morph_close(thigh_m, 5)
    thigh_m = keep_seed(thigh_m, (305, 890))

    # Near boot only — polygon follows the front shoe (toe + heel), not the far boot.
    shin_m = poly_mask(ch, cw, [
        (275, 912), (348, 912), (358, 980), (350, 1046),
        (275, 1046), (250, 1018), (258, 965), (270, 920),
    ]) & opaque
    shin_m &= (dark | mint | (rgb_c.mean(axis=2) < 120).astype(np.uint8))
    shin_m &= ~thigh_m
    shin_m = morph_close(shin_m, 7)
    shin_m = keep_seed(shin_m, (310, 980))

    # Full maid dress + apron + petticoat. Sleeve overlap is subtracted next.
    torso_box = poly_mask(ch, cw, [
        (245, 456), (338, 456), (352, 515), (368, 580),
        (410, 720), (445, 892),
        (155, 898), (148, 800), (150, 650),
        (175, 560), (220, 500),
    ])
    torso_m = torso_box & opaque
    torso_m &= ~head_m
    torso_m &= ~wing_m
    torso_m &= ~tail_m
    torso_m &= ~upper_m
    torso_m &= ~sleeve_zone
    torso_m &= ~forearm_m
    torso_m &= ~weapon
    torso_m &= ~shin_m
    torso_m &= ~thigh_m
    torso_m = morph_close(torso_m, 5)
    torso_m &= ~upper_m
    torso_m &= ~sleeve_zone
    torso_m &= ~forearm_m
    torso_m &= ~thigh_m
    torso_m &= ~shin_m
    torso_m &= ~head_m
    torso_m &= ~wing_m
    torso_m &= ~tail_m
    torso_keep = torso_m
    torso_rgba = np.dstack([rgb_c, (torso_keep * 255).astype(np.uint8)])

    tail_a = tail_m & polyline_mask(ch, cw, tail_pts[0:3], 32)
    tail_b = tail_m & polyline_mask(ch, cw, tail_pts[2:5], 32)
    tail_c = tail_m & polyline_mask(ch, cw, tail_pts[4:], 32)
    # Later segments own the overlap so the tip stays intact.
    tail_a &= ~(tail_b | tail_c)
    tail_b &= ~tail_c
    # Tiny overlap at each tail joint so the stripe doesn't gap.
    tail_a |= tail_m & ellipse_mask(ch, cw, *tail_pts[2], 14, 14)
    tail_b |= tail_m & ellipse_mask(ch, cw, *tail_pts[4], 14, 14)

    joints = {
        "neck": (270, 460),
        "crown": (305, 35),
        "hips": (290, 700),
        "shoulder": (232, 548),
        "elbow": (200, 632),
        "hand": (158, 708),
        "hip_joint": (300, 710),
        "knee": (305, 918),
        "ankle": (310, 1008),
        "wing_root": (375, 555),
        "wing_tip": (520, 600),
        "tail0": (400, 722),
        "tail1": (475, 808),
        "tail2": (575, 848),
        "tail3": (642, 762),
    }

    parts = {
        "head": (head_m, joints["neck"], joints["crown"], rgba),
        "torso": (torso_keep, joints["hips"], joints["neck"], torso_rgba),
        "upper_arm": (upper_m, joints["shoulder"], joints["elbow"], rgba),
        "forearm": (forearm_m, joints["elbow"], joints["hand"], rgba),
        "thigh": (thigh_m, joints["hip_joint"], joints["knee"], rgba),
        "shin": (shin_m, joints["knee"], joints["ankle"], rgba),
        "wing": (wing_m, joints["wing_root"], joints["wing_tip"], rgba),
        "tail_a": (tail_a, joints["tail0"], joints["tail1"], rgba),
        "tail_b": (tail_b, joints["tail1"], joints["tail2"], rgba),
        "tail_c": (tail_c, joints["tail2"], joints["tail3"], rgba),
    }

    overlay = color_overlay(rgb_c, [
        (head_m, (255, 210, 80)),
        (torso_keep, (80, 160, 255)),
        (upper_m, (255, 80, 80)),
        (forearm_m, (255, 140, 80)),
        (thigh_m, (80, 255, 140)),
        (shin_m, (40, 200, 80)),
        (wing_m, (180, 80, 255)),
        (tail_a, (80, 255, 255)),
        (tail_b, (40, 180, 220)),
        (tail_c, (20, 120, 200)),
    ])
    save_debug("00_parts_overlay", overlay)

    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {"layout": {}, "_note": (
        "Cut from the clay three-view side figure (tools/refs/xiaolv_side_nendo.png) "
        "via tools/cut_xiaolv_parts.py. Pivots are in the bone-oriented PNG "
        "(joint on the bone-root side, distal along +X)."
    )}
    uprights = {}

    hips = joints["hips"]
    for key, (x, y) in joints.items():
        catalog["layout"][key] = [
            round((x - hips[0]) * SCALE, 2),
            round((y - hips[1]) * SCALE, 2),
        ]

    for name, (mask, pivot, distal, src) in parts.items():
        cut = strip_bg_fringe(apply_mask(src, mask))
        save_debug(name, cut)
        oriented, opivot = orient_along_bone(cut, pivot, distal)
        oriented, opivot = scale_rgba(oriented, opivot, SCALE)
        Image.fromarray(oriented).save(OUT / f"{name}.png")
        catalog[name] = {
            "file": f"{name}.png",
            "pivot": [round(float(opivot[0]), 2), round(float(opivot[1]), 2)],
            "width": int(oriented.shape[1]),
            "height": int(oriented.shape[0]),
        }
        u, up = crop_alpha(cut, pivot, pad=3)
        u, up = scale_rgba(u, up, SCALE)
        uprights[name] = (Image.fromarray(u), up)
        pv = catalog[name]["pivot"]
        print(f"  {name:12s} {catalog[name]['width']}x{catalog[name]['height']} pivot={pv}")

    preview = Image.new("RGBA", (int(cw * SCALE) + 80, int(ch * SCALE) + 80), (0, 0, 0, 0))

    def paste(name, world):
        im, piv = uprights[name]
        x = int(round(world[0] * SCALE + 40 - piv[0]))
        y = int(round(world[1] * SCALE + 40 - piv[1]))
        preview.alpha_composite(im, (x, y))

    paste("wing", joints["wing_root"])
    paste("tail_a", joints["tail0"])
    paste("tail_b", joints["tail1"])
    paste("tail_c", joints["tail2"])
    paste("upper_arm", joints["shoulder"])
    paste("forearm", joints["elbow"])
    paste("thigh", joints["hip_joint"])
    paste("shin", joints["knee"])
    paste("torso", joints["hips"])
    paste("head", joints["neck"])
    arr = np.array(preview)
    ys, xs = np.where(arr[:, :, 3] > 8)
    if len(xs):
        preview = preview.crop((max(0, xs.min() - 8), max(0, ys.min() - 8),
                                xs.max() + 9, ys.max() + 9))
    bg = Image.new("RGBA", preview.size, (250, 249, 247, 255))
    bg.alpha_composite(preview)
    bg.convert("RGB").save(OUT / "preview_rest.png")

    (OUT / "parts.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"Wrote parts to {OUT}")
    print("layout", json.dumps(catalog["layout"], indent=2))


if __name__ == "__main__":
    main()
