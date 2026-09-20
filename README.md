# 白银城 / Silver City — Godot 4 2.5D Mini Demo

黏土 Q 版城主在草地上行走的迷你演示。用 **Skeleton2D 部件骨骼**（肘、膝可动）播放走路循环。A tiny 2.5D walk demo: clay-chibi 城主 on a tiled grass field, driven by a cutout **Skeleton2D** (bendable elbows and knees).

![Skeletal walk cycle](assets/labrynth/preview_walk.gif)

---

## English

### Open in Godot 4

1. Install **[Godot 4.7](https://godotengine.org/download)** (4.7.x; this repo is tagged for 4.7).
2. Clone this repo, then pull binary assets (see Git LFS below).
3. **Import once** (creates the gitignored `.godot/` cache). Either:
   - Open the editor: `godot -e --path .` then press **F5**, or
   - From the CLI (required before `godot --path .` on a fresh clone):

```bash
godot --headless --path . --import
godot --path .
```

`godot --path .` **runs** the main scene (`scenes/main.tscn`); it does not open the editor. Without a prior import, textures fail to load (`*.ctex` missing).

### Controls

| Input | Action |
| --- | --- |
| **W A S D** or **Arrow keys** | Move |
| No input | Idle (last facing) |

Movement is screen-space with a slight Y squash so it reads as a ~45° 2.5D ground plane. While moving, the puppet plays a looping skeletal walk (hip bob, opposite arm/leg swing, elbow and knee bend, skirt sway). Idle uses a small breath on the same rig.

**Facings:** the cutout is a camera-facing 3/4 A-pose. `scale.x` flips for east vs west (native art is unflipped when moving left).

| Direction | Flip |
| --- | --- |
| East (right) | `scale.x < 0` |
| West (left) | `scale.x > 0` |

Camera2D follows the player.

### Rig

Parts live in `assets/labrynth/parts/` (head, torso, skirt, sleeves, upper/lower arms, thighs/calves). Pivots and rest pose are in `assets/labrynth/rig.json`. `scripts/labrynth_puppet.gd` builds the `Skeleton2D` at runtime:

- **Elbow:** `UpperArmL/R` → `LowerArmL/R`
- **Knee:** `ThighL/R` → `CalfL/R`

`tools/extract_labrynth_parts.py` recuts `tools/labrynth_src/parts_sheet.png`; `tools/preview_walk.py` renders a GIF preview of the same walk math.

### Git LFS

PNG (and other binary) assets are stored with **Git LFS**. After clone:

```bash
git lfs install
git lfs pull
```

If sprites or the grass floor are missing / tiny pointer files, you skipped `git lfs pull`.

### Smoke test

```bash
godot --version   # expect 4.7.x
godot --headless --path . res://tests/smoke.tscn
```

Expect `SMOKE TEST PASSED` (exit 0). Covers scene load, Skeleton2D elbow/knee chains, walk vs idle, left/right facing, WASD/arrows, camera follow, and map clamp.

---

## 中文

### 用 Godot 4 打开

1. 安装 **[Godot 4.7](https://godotengine.org/download)**（4.7.x；本仓库按 4.7 对齐）。
2. 克隆本仓库，并拉取二进制资源（见下方 Git LFS）。
3. **先导入一次**（生成被 gitignore 的 `.godot/` 缓存）。两种方式均可：
   - 打开编辑器：`godot -e --path .`，再按 **F5**；或
   - 命令行（新克隆后若直接 `godot --path .`，必须先做这一步）：

```bash
godot --headless --path . --import
godot --path .
```

`godot --path .` 是**直接运行**主场景 `scenes/main.tscn`，不会打开编辑器。若尚未导入，贴图会加载失败（缺少 `*.ctex`）。

### 操作

| 按键 | 作用 |
| --- | --- |
| **W A S D** 或 **方向键** | 移动 |
| 无输入 | 待机（保持上次朝向） |

移动为屏幕坐标系，并略微压缩 Y 轴，以贴近约 45° 的 2.5D 地面。移动时播放骨骼走路循环（身体起伏、四肢反向摆动、肘膝弯曲、裙摆跟随）；停下时同一套骨骼做轻微呼吸。

**朝向：** 部件图是镜头方向的 3/4 A-pose。朝右时用 `scale.x` 镜像。

镜头跟随角色。

### 骨骼

部件在 `assets/labrynth/parts/`。轴心与 A-pose 在 `assets/labrynth/rig.json`。`scripts/labrynth_puppet.gd` 运行时搭建 `Skeleton2D`：

- **肘：** 上臂 → 前臂
- **膝：** 大腿 → 小腿

### Git LFS

PNG 等二进制资源使用 **Git LFS** 存储。克隆后请执行：

```bash
git lfs install
git lfs pull
```

若角色图或草地贴图缺失（或只是很小的 pointer 文件），请先执行 `git lfs pull`。

### 冒烟测试

```bash
godot --version   # 应为 4.7.x
godot --headless --path . res://tests/smoke.tscn
```

成功时打印 `SMOKE TEST PASSED`（退出码 0）。覆盖场景加载、肘/膝关节链、行走/待机、左右朝向、WASD/方向键、镜头跟随与地图边界。
