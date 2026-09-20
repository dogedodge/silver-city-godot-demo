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
RIG = json.loads((LAB / "rig.json").read_text())
OUT_REST = LAB / "preview_rest.png"
OUT_GIF = LAB / "preview_walk.gif"
OUT_APOSE = LAB / "preview_a_pose.png"

CANVAS_W, CANVAS_H = 640, 780
ORIGIN = (CANVAS_W // 2, 700)


def load_part(name: str) -> tuple[Image.Image, tuple[float, float]]:
    info = RIG["parts"][name]
    filename = Path(str(info["file"]).replace("res://assets/labrynth/", "")).name
    im = Image.open(PARTS / filename).convert("RGBA")
    px, py = info["pivot"]
    return im, (float(px), float(py))


def child_joint(key: str) -> tuple[float, float]:
    j = RIG["joints"][key]
    return (float(j[0]), float(j[1]))


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
    piece = im.transform(
        (maxx - minx, maxy - miny),
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
    rest = RIG["rest"]
    walk = RIG["walk"]
    rest_arm_l = float(rest["arm_l"])
    rest_arm_r = float(rest["arm_r"])
    rest_elbow_l = float(rest["elbow_l"])
    rest_elbow_r = float(rest["elbow_r"])
    if not moving:
        breath = math.sin(phase * 0.35) * 1.2
        return {
            "hip_x": 0.0,
            "hip_y": breath * 0.4,
            "hip": breath * 0.3,
            "torso": -breath * 0.4,
            "head": breath * 0.6,
            "skirt": breath * 0.5,
            "thigh_l": float(rest["thigh_l"]),
            "thigh_r": float(rest["thigh_r"]),
            "calf_l": float(rest["calf_l"]),
            "calf_r": float(rest["calf_r"]),
            "arm_l": rest_arm_l,
            "arm_r": rest_arm_r,
            "elbow_l": rest_elbow_l,
            "elbow_r": rest_elbow_r,
            "sleeve_l": 0.0,
            "sleeve_r": 0.0,
        }
    s = math.sin(phase)
    c = math.cos(phase)
    swing = float(walk["thigh_swing"])
    knee_max = float(walk["knee_max"])
    arm_swing = float(walk["arm_swing"])
    left_swing = max(0.0, -s)
    right_swing = max(0.0, s)
    return {
        "hip_x": s * float(walk["hip_x"]),
        "hip_y": abs(c) * float(walk["hip_bob"]),
        "hip": s * float(walk["hip_sway"]),
        "torso": -s * float(walk["torso_counter"]),
        "head": -s * float(walk["head_counter"]),
        "skirt": -s * float(walk["skirt_sway"]),
        "thigh_l": float(rest["thigh_l"]) + c * swing,
        "thigh_r": float(rest["thigh_r"]) - c * swing,
        "calf_l": float(rest["calf_l"]) + left_swing * knee_max,
        "calf_r": float(rest["calf_r"]) - right_swing * knee_max,
        "arm_l": rest_arm_l + c * arm_swing,
        "arm_r": rest_arm_r + c * arm_swing,
        "elbow_l": rest_elbow_l + left_swing * 10.0,
        "elbow_r": rest_elbow_r - right_swing * 10.0,
        "sleeve_l": 0.0,
        "sleeve_r": 0.0,
    }


def _off(name: str) -> tuple[float, float]:
    a = RIG["offsets"][name]
    return (float(a[0]), float(a[1]))


def render_pose(phase: float, moving: bool) -> Image.Image:
    a = walk_angles(phase, moving)
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    parts = {n: load_part(n) for n in RIG["parts"]}
    hip_h = float(RIG["hip_from_feet"])

    hip = T(ORIGIN[0] + a["hip_x"], ORIGIN[1] - hip_h + a["hip_y"]) @ R(a["hip"])
    torso = hip @ T(*_off("torso")) @ R(a["torso"])
    head = torso @ T(*_off("head")) @ R(a["head"])
    skirt = hip @ T(*_off("skirt")) @ R(a["skirt"])
    sh_l = torso @ T(*_off("shoulder_l"))
    sh_r = torso @ T(*_off("shoulder_r"))
    arm_l = sh_l @ R(a["arm_l"])
    arm_r = sh_r @ R(a["arm_r"])
    forearm_l = arm_l @ T(*child_joint("elbow_l")) @ R(a["elbow_l"])
    forearm_r = arm_r @ T(*child_joint("elbow_r")) @ R(a["elbow_r"])
    sleeve_l = arm_l @ T(*_off("sleeve_l")) @ R(a["sleeve_l"])
    sleeve_r = arm_r @ T(*_off("sleeve_r")) @ R(a["sleeve_r"])
    thigh_l = hip @ T(*_off("hip_l")) @ R(a["thigh_l"])
    thigh_r = hip @ T(*_off("hip_r")) @ R(a["thigh_r"])
    calf_l = thigh_l @ T(*child_joint("knee_l")) @ R(a["calf_l"])
    calf_r = thigh_r @ T(*child_joint("knee_r")) @ R(a["calf_r"])

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


def solid_bg(size: tuple[int, int], rgb: tuple[int, int, int] = (210, 210, 214)) -> Image.Image:
    w, h = size
    arr = np.zeros((h, w, 4), np.uint8)
    arr[:, :] = (*rgb, 255)
    return Image.fromarray(arr, "RGBA")


def crop_character(im: Image.Image, margin: int = 24) -> Image.Image:
    a = np.array(im)
    ys, xs = np.where(a[:, :, 3] > 12)
    if len(xs) == 0:
        return im
    x0, x1 = max(0, int(xs.min()) - margin), min(im.size[0], int(xs.max()) + 1 + margin)
    y0, y1 = max(0, int(ys.min()) - margin), min(im.size[1], int(ys.max()) + 1 + margin)
    return im.crop((x0, y0, x1, y1))


def main() -> None:
    rest = render_pose(0.0, False)
    sheet = checker_bg(rest.size)
    sheet.alpha_composite(rest)
    sheet.save(OUT_REST)
    print("wrote", OUT_REST)

    apose = solid_bg(rest.size)
    apose.alpha_composite(rest)
    crop_character(apose).save(OUT_APOSE)
    print("wrote", OUT_APOSE)

    frames: list[Image.Image] = []
    n = 16
    for i in range(n):
        phase = (i / n) * math.tau
        layer = render_pose(phase, True)
        bg = checker_bg(layer.size)
        bg.alpha_composite(layer)
        frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE, colors=240))
    frames[0].save(
        OUT_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=70,
        loop=0,
        disposal=2,
    )
    print("wrote", OUT_GIF)


if __name__ == "__main__":
    main()
