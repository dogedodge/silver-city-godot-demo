#!/usr/bin/env python3
"""Cut Labrynth parts from the breakdown sheet and write pivot metadata."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "labrynth_src" / "parts_sheet.png"
OUT_DIR = ROOT / "assets" / "labrynth" / "parts"
META = ROOT / "assets" / "labrynth" / "rig_extract.json"

# Redrawn or mirrored after the original sheet; do not overwrite on re-extract.
SKIP_WRITE = {"torso", "skirt", "upper_arm_l", "forearm_l"}

# Tight boxes that avoid Chinese/English labels under each part.
REGIONS = {
    "assembled": (52, 58, 252, 472),
    "head": (352, 72, 522, 268),
    "torso": (568, 138, 662, 248),
    "skirt": (722, 102, 888, 266),
    "sleeve_l": (952, 108, 1034, 272),
    "sleeve_r": (1120, 108, 1196, 272),
    "upper_arm_l": (388, 318, 456, 432),
    "forearm_l": (544, 318, 656, 442),
    "upper_arm_r": (764, 318, 842, 434),
    "forearm_r": (940, 320, 1040, 442),
    "thigh_l": (374, 488, 436, 638),
    "calf_l": (552, 488, 630, 648),
    "thigh_r": (768, 478, 828, 642),
    "calf_r": (962, 478, 1028, 652),
}


def _is_magenta(px: np.ndarray) -> bool:
    r, g, b, a = (int(px[0]), int(px[1]), int(px[2]), int(px[3]))
    return a > 40 and r > 155 and g < 155 and b > 100 and r > g + 30 and b > g


def _flood_background(crop: np.ndarray, tol: int = 18) -> np.ndarray:
    """Edge flood-fill of the flat gray sheet background → alpha."""
    h, w = crop.shape[:2]
    bg = crop[0, 0, :3].astype(np.int16)
    # Prefer a corner that is actually background gray.
    for cy, cx in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1), (1, 1)):
        pix = crop[cy, cx, :3]
        if int(pix.max()) - int(pix.min()) < 8 and 180 <= int(pix[0]) <= 230:
            bg = pix.astype(np.int16)
            break

    alpha = np.full((h, w), 255, np.uint8)
    visited = np.zeros((h, w), dtype=np.uint8)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        q.append((0, x))
        q.append((h - 1, x))
    for y in range(h):
        q.append((y, 0))
        q.append((y, w - 1))

    while q:
        y, x = q.popleft()
        if visited[y, x]:
            continue
        visited[y, x] = 1
        diff = np.abs(crop[y, x, :3].astype(np.int16) - bg)
        if int(diff.max()) > tol:
            continue
        alpha[y, x] = 0
        if y > 0:
            q.append((y - 1, x))
        if y + 1 < h:
            q.append((y + 1, x))
        if x > 0:
            q.append((y, x - 1))
        if x + 1 < w:
            q.append((y, x + 1))
    return alpha


def _cluster_magenta(crop: np.ndarray) -> list[dict]:
    h, w = crop.shape[:2]
    pts: list[tuple[int, int]] = []
    for y in range(h):
        row = crop[y]
        for x in range(w):
            if row[x, 3] > 80 and _is_magenta(row[x]):
                pts.append((x, y))
    clusters: list[dict] = []
    used = [False] * len(pts)
    for i, (x, y) in enumerate(pts):
        if used[i]:
            continue
        group = [(x, y)]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j, (x2, y2) in enumerate(pts):
                if used[j]:
                    continue
                if any((x2 - gx) ** 2 + (y2 - gy) ** 2 < 20 * 20 for gx, gy in group):
                    group.append((x2, y2))
                    used[j] = True
                    changed = True
        if len(group) < 8:
            continue
        clusters.append(
            {
                "x": int(round(sum(p[0] for p in group) / len(group))),
                "y": int(round(sum(p[1] for p in group) / len(group))),
                "n": len(group),
            }
        )
    clusters.sort(key=lambda c: c["y"])
    return clusters


def _inpaint_magenta(crop: np.ndarray) -> None:
    h, w = crop.shape[:2]
    mag = np.zeros((h, w), dtype=bool)
    skin_samples: list[np.ndarray] = []
    for y in range(h):
        for x in range(w):
            px = crop[y, x]
            if px[3] < 80:
                continue
            if _is_magenta(px):
                mag[y, x] = True
            else:
                r, g, b = int(px[0]), int(px[1]), int(px[2])
                if r > 180 and g > 140 and b > 140 and abs(r - g) < 50:
                    skin_samples.append(px[:3].copy())
    if not mag.any():
        return
    # Dilate marker so the ring around the joint is gone.
    dil = mag.copy()
    ys, xs = np.where(mag)
    for y, x in zip(ys, xs):
        y0, y1 = max(0, y - 5), min(h, y + 6)
        x0, x1 = max(0, x - 5), min(w, x + 6)
        dil[y0:y1, x0:x1] = True
    if skin_samples:
        skin = np.median(np.stack(skin_samples), axis=0).astype(np.uint8)
    else:
        skin = np.array([236, 214, 208], np.uint8)
    crop[dil, :3] = skin
    crop[dil, 3] = np.maximum(crop[dil, 3], 230)


def _drop_small_dark(crop: np.ndarray, min_area: int = 400) -> None:
    """Remove leftover caption glyphs (small dark blobs)."""
    h, w = crop.shape[:2]
    vis = np.zeros((h, w), dtype=bool)
    opaque = crop[:, :, 3] > 40
    dark = opaque & (crop[:, :, :3].min(axis=2) < 90)
    for y in range(h):
        for x in range(w):
            if not dark[y, x] or vis[y, x]:
                continue
            q = deque([(y, x)])
            vis[y, x] = True
            cells: list[tuple[int, int]] = []
            while q:
                cy, cx = q.popleft()
                cells.append((cy, cx))
                for ny, nx in (
                    (cy - 1, cx),
                    (cy + 1, cx),
                    (cy, cx - 1),
                    (cy, cx + 1),
                ):
                    if 0 <= ny < h and 0 <= nx < w and dark[ny, nx] and not vis[ny, nx]:
                        vis[ny, nx] = True
                        q.append((ny, nx))
            if len(cells) < min_area:
                for cy, cx in cells:
                    crop[cy, cx, 3] = 0


def _mass_point(trim: np.ndarray, band: str) -> list[float]:
    a = trim[:, :, 3] > 40
    ys, xs = np.where(a)
    if len(xs) == 0:
        return [trim.shape[1] / 2.0, trim.shape[0] / 2.0]
    h = trim.shape[0]
    if band == "top":
        keep = ys <= ys.min() + max(6, int(h * 0.12))
    elif band == "bottom":
        keep = ys >= ys.max() - max(6, int(h * 0.12))
    else:
        keep = np.ones(len(xs), dtype=bool)
    return [float(xs[keep].mean()), float(ys[keep].mean())]


def extract_region(sheet: np.ndarray, name: str, box: tuple[int, int, int, int]) -> dict:
    x0, y0, x1, y1 = box
    crop = sheet[y0:y1, x0:x1].copy()
    crop[:, :, 3] = _flood_background(crop)
    _drop_small_dark(crop)
    mag = _cluster_magenta(crop)
    _inpaint_magenta(crop)

    ys, xs = np.where(crop[:, :, 3] > 24)
    if len(xs) == 0:
        raise RuntimeError(f"empty extract: {name}")
    tx0, tx1 = int(xs.min()), int(xs.max())
    ty0, ty1 = int(ys.min()), int(ys.max())
    trim = crop[ty0 : ty1 + 1, tx0 : tx1 + 1]
    for c in mag:
        c["x"] -= tx0
        c["y"] -= ty0

    if name not in SKIP_WRITE:
        Image.fromarray(trim, "RGBA").save(OUT_DIR / f"{name}.png")
    th, tw = trim.shape[:2]
    info = {
        "file": f"parts/{name}.png",
        "size": [int(tw), int(th)],
        "top": [round(v, 1) for v in _mass_point(trim, "top")],
        "bottom": [round(v, 1) for v in _mass_point(trim, "bottom")],
        "magenta": mag,
    }
    return _with_pivot(name, info)


def _with_pivot(name: str, info: dict) -> dict:
    mag = info["magenta"]
    w, h = info["size"]
    if name == "head":
        # Neck sits under the chin, not at the hanging hair tip.
        info["pivot"] = [round(w * 0.48, 1), round(h * 0.82, 1)]
    elif name == "torso":
        info["pivot"] = [round(w * 0.50, 1), round(h * 0.92, 1)]
    elif name in ("skirt", "sleeve_l", "sleeve_r"):
        info["pivot"] = info["top"]
    elif name.startswith("upper_arm"):
        info["pivot"] = info["top"]
        if mag:
            info["elbow"] = [mag[-1]["x"], mag[-1]["y"]]
        else:
            info["elbow"] = info["bottom"]
    elif name.startswith("forearm"):
        info["pivot"] = [mag[0]["x"], mag[0]["y"]] if mag else info["top"]
    elif name.startswith("thigh"):
        if len(mag) >= 2:
            info["pivot"] = [mag[0]["x"], mag[0]["y"]]
            info["knee"] = [mag[-1]["x"], mag[-1]["y"]]
        elif mag:
            info["pivot"] = info["top"]
            info["knee"] = [mag[0]["x"], mag[0]["y"]]
        else:
            info["pivot"] = info["top"]
            info["knee"] = info["bottom"]
    elif name.startswith("calf"):
        info["pivot"] = [mag[0]["x"], mag[0]["y"]] if mag else info["top"]
    else:
        info["pivot"] = [round(w / 2.0, 1), round(h / 2.0, 1)]
    return info


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet = np.array(Image.open(SRC).convert("RGBA"))
    parts = {name: extract_region(sheet, name, box) for name, box in REGIONS.items()}
    meta = {"source": "parts_sheet.png", "parts": parts}
    META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("wrote", META)
    for name, info in parts.items():
        print(f"  {name:12s} {info['size']} pivot={info['pivot']} mag={info['magenta']}")


if __name__ == "__main__":
    main()
