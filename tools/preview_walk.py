#!/usr/bin/env python3
"""Composite Labrynth parts with a 2D bone hierarchy and render a walk cycle."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "assets" / "labrynth"
PARTS = LAB / "parts"
EXTRACT = json.loads((LAB / "rig_extract.json").read_text())
OUT_REST = LAB / "preview_rest.png"
OUT_GIF = LAB / "preview_walk.gif"

SCALE = 1.0
CANVAS_W, CANVAS_H = 480, 560
ORIGIN = (CANVAS_W // 2, 430)  # feet-ish


def load_part(name: str) -> tuple[Image.Image, tuple[float, float]]:
    info = EXTRACT["parts"][name]
    im = Image.open(PARTS / f"{name}.png").convert("RGBA")
    px, py = info["pivot"]
    return im, (float(px), float(py))


def child_joint(name: str, key: str) -> tuple[float, float]:
    info = EXTRACT["parts"][name]
    jx, jy = info[key]
    px, py = info["pivot"]
    return (float(jx - px), float(jy - py))


def affine_from_matrix(m: np.ndarray) -> tuple[float, ...]:
    inv = np.linalg.inv(m)
    return (
        float(inv[0, 0]),
        float(inv[0, 1]),
        float(inv[0, 2]),
        float(inv[1, 0]),
        float(inv[1, 1]),
        float(inv[1, 2]),
    )


def blit(
    canvas: Image.Image,
    im: Image.Image,
    pivot: tuple[float, float],
    world: np.ndarray,
) -> None:
    """world maps bone-local metres (joint at origin) to canvas pixels."""
    px, py = pivot
    local = np.array(
        [[1.0, 0.0, -px], [0.0, 1.0, -py], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    m = world @ local
    w, h = im.size
    corners = np.array([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]], dtype=np.float64).T
    dest = m @ corners
    xs, ys = dest[0], dest[1]
    minx, maxx = int(np.floor(xs.min())) - 1, int(np.ceil(xs.max())) + 1
    miny, maxy = int(np.floor(ys.min())) - 1, int(np.ceil(ys.max())) + 1
    minx = max(minx, 0)
    miny = max(miny, 0)
    maxx = min(maxx, canvas.size[0])
    maxy = min(maxy, canvas.size[1])
    if maxx <= minx or maxy <= miny:
        return
    shift = np.array(
        [[1.0, 0.0, -minx], [0.0, 1.0, -miny], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    box_w, box_h = maxx - minx, maxy - miny
    piece = im.transform(
        (box_w, box_h),
        Image.AFFINE,
        affine_from_matrix(shift @ m),
        resample=Image.Resampling.BICUBIC,
    )
    canvas.alpha_composite(piece, (minx, miny))


def T(x: float, y: float) -> np.ndarray:
    return np.array([[1.0, 0.0, x], [0.0, 1.0, y], [0.0, 0.0, 1.0]], dtype=np.float64)


def R(deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)


def walk_angles(phase: float, moving: bool) -> dict[str, float]:
    """phase in radians. Bone local rotations in degrees, added on rest."""
    # Rest keeps the drawn A-pose; walk adds modest in-place motion.
    # Arm PNGs both point down-left, so left/right rest angles are not mirrors.
    rest_arm_l, rest_arm_r = -60.0, 15.0
    rest_elbow_l, rest_elbow_r = 8.0, -6.0
    if not moving:
        breath = math.sin(phase * 0.35) * 1.2
        return {
            "hip_x": 0.0,
            "hip_y": breath * 0.4,
            "hip": breath * 0.3,
            "torso": -breath * 0.4,
            "head": breath * 0.6,
            "skirt": breath * 0.5,
            "thigh_l": 3.0,
            "thigh_r": -3.0,
            "calf_l": 4.0,
            "calf_r": -4.0,
            "arm_l": rest_arm_l,
            "arm_r": rest_arm_r,
            "elbow_l": rest_elbow_l,
            "elbow_r": rest_elbow_r,
            "sleeve_l": rest_arm_l * 0.45,
            "sleeve_r": rest_arm_r * 0.45,
        }
    s = math.sin(phase)
    c = math.cos(phase)
    # Contact at phase 0 / pi (cos = ±1). Passing at ±pi/2.
    swing = 14.0
    knee_max = 22.0
    arm_swing = 16.0
    left_swing = max(0.0, -s)  # 1 at 3pi/2
    right_swing = max(0.0, s)  # 1 at pi/2
    return {
        "hip_x": s * 2.0,
        "hip_y": abs(c) * 5.0,  # +Y down: drop on contact
        "hip": s * 4.0,
        "torso": -s * 3.0,
        "head": -s * 2.2,
        "skirt": -s * 8.0,
        "thigh_l": 3.0 + c * swing,
        "thigh_r": -3.0 - c * swing,
        "calf_l": 4.0 + left_swing * knee_max,
        "calf_r": -(4.0 + right_swing * knee_max),
        "arm_l": rest_arm_l + c * arm_swing,
        "arm_r": rest_arm_r + c * arm_swing,
        "elbow_l": rest_elbow_l + left_swing * 10.0,
        "elbow_r": rest_elbow_r - right_swing * 10.0,
        "sleeve_l": rest_arm_l * 0.45 + c * (arm_swing * 0.45),
        "sleeve_r": rest_arm_r * 0.45 + c * (arm_swing * 0.45),
    }


def render_pose(phase: float, moving: bool) -> Image.Image:
    a = walk_angles(phase, moving)
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))

    parts = {n: load_part(n) for n in EXTRACT["parts"] if n != "assembled"}
    elbow_l = child_joint("upper_arm_l", "elbow")
    elbow_r = child_joint("upper_arm_r", "elbow")
    knee_l = child_joint("thigh_l", "knee")
    knee_r = child_joint("thigh_r", "knee")

    hip = T(ORIGIN[0] + a["hip_x"], ORIGIN[1] - 200.0 + a["hip_y"]) @ R(a["hip"])
    torso = hip @ T(2.0, 2.0) @ R(a["torso"])
    head = torso @ T(5.0, -80.0) @ R(a["head"])
    skirt = hip @ T(1.0, 6.0) @ R(a["skirt"])

    sh_l = torso @ T(38.0, -74.0)  # character left / viewer's right
    sh_r = torso @ T(-34.0, -76.0)

    arm_l = sh_l @ R(a["arm_l"])
    arm_r = sh_r @ R(a["arm_r"])
    forearm_l = arm_l @ T(*elbow_l) @ R(a["elbow_l"])
    forearm_r = arm_r @ T(*elbow_r) @ R(a["elbow_r"])
    sleeve_l = sh_l @ T(6.0, -4.0) @ R(a["sleeve_l"])
    sleeve_r = sh_r @ T(-8.0, -4.0) @ R(a["sleeve_r"])

    thigh_l = hip @ T(14.0, 16.0) @ R(a["thigh_l"])
    thigh_r = hip @ T(-12.0, 16.0) @ R(a["thigh_r"])
    calf_l = thigh_l @ T(*knee_l) @ R(a["calf_l"])
    calf_r = thigh_r @ T(*knee_r) @ R(a["calf_r"])

    # Legs stay under the dress; only shoes peek below the hem.
    order = [
        ("sleeve_l", sleeve_l),
        ("upper_arm_l", arm_l),
        ("forearm_l", forearm_l),
        ("thigh_l", thigh_l),
        ("thigh_r", thigh_r),
        ("calf_l", calf_l),
        ("calf_r", calf_r),
        ("skirt", skirt),
        ("torso", torso),
        ("head", head),
        ("sleeve_r", sleeve_r),
        ("upper_arm_r", arm_r),
        ("forearm_r", forearm_r),
    ]
    for name, world in order:
        im, pivot = parts[name]
        blit(canvas, im, pivot, world)
    return canvas


def checker_bg(size: tuple[int, int]) -> Image.Image:
    w, h = size
    arr = np.zeros((h, w, 4), np.uint8)
    for y in range(0, h, 16):
        for x in range(0, w, 16):
            c = (214, 214, 220, 255) if ((x // 16) + (y // 16)) % 2 == 0 else (236, 236, 240, 255)
            arr[y : y + 16, x : x + 16] = c
    return Image.fromarray(arr, "RGBA")


def main() -> None:
    rest = render_pose(0.0, False)
    sheet = checker_bg(rest.size)
    sheet.alpha_composite(rest)
    sheet.save(OUT_REST)
    print("wrote", OUT_REST)

    frames: list[Image.Image] = []
    n = 16
    sheet_w = CANVAS_W * 4
    sheet_h = CANVAS_H * 4
    sheet = checker_bg((sheet_w, sheet_h))
    for i in range(n):
        phase = (i / n) * math.tau
        layer = render_pose(phase, True)
        bg = checker_bg(layer.size)
        bg.alpha_composite(layer)
        frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE, colors=240))
        col, row = i % 4, i // 4
        sheet.alpha_composite(layer, (col * CANVAS_W, row * CANVAS_H))
    frames[0].save(
        OUT_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=70,
        loop=0,
        disposal=2,
    )
    sheet.save(LAB / "preview_walk_sheet.png")
    print("wrote", OUT_GIF)
    print("wrote", LAB / "preview_walk_sheet.png")


if __name__ == "__main__":
    main()
