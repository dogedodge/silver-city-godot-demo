# 白银城 / Silver City — Godot 4 2.5D Mini Demo

黏土 Q 版城主在草地上行走的迷你演示。A tiny 2.5D walk demo: clay-chibi 城主 on a tiled grass field.

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

`godot --path .` **runs** the main scene (`scenes/main.tscn`); it does not open the editor. Without a prior import, textures fail to load (`*.ctex` missing) and `player.gd` cannot `preload` the walk sheet.

### Controls

| Input | Action |
| --- | --- |
| **W A S D** or **Arrow keys** | Move |
| No input | Idle (last facing) |

Movement is screen-space with a slight Y squash so it reads as a ~45° 2.5D ground plane. Walk animation plays while moving; the first sheet frame is used for idle.

**Facings** (2 sheet rows × `flip_h` = 4 directions):

| Direction | Sheet | `flip_h` |
| --- | --- | --- |
| SE (down-right) | Front row | off |
| SW (down-left) | Front row | on |
| NE (up-right) | Back row | off |
| NW (up-left) | Back row | on |

Camera2D follows the player.

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

Expect `SMOKE TEST PASSED` (exit 0). Covers scene load, 8-frame walk / idle, SE·SW·NE·NW facings, WASD/arrows, camera follow, and map clamp.

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

`godot --path .` 是**直接运行**主场景 `scenes/main.tscn`，不会打开编辑器。若尚未导入，贴图会加载失败（缺少 `*.ctex`），`player.gd` 也无法 `preload` 行走图。

### 操作

| 按键 | 作用 |
| --- | --- |
| **W A S D** 或 **方向键** | 移动 |
| 无输入 | 待机（保持上次朝向） |

移动为屏幕坐标系，并略微压缩 Y 轴，以贴近约 45° 的 2.5D 地面。移动时播放行走动画，停下时使用该朝向的待机帧。

**朝向**（sprite sheet 两行 + `flip_h` 得到四个方向）：

| 方向 | Sheet | `flip_h` |
| --- | --- | --- |
| 东南 SE（下右） | 正面行 | 关闭 |
| 西南 SW（下左） | 正面行 | 开启 |
| 东北 NE（上右） | 背面行 | 关闭 |
| 西北 NW（上左） | 背面行 | 开启 |

Camera2D 跟随角色。

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

成功时打印 `SMOKE TEST PASSED`（退出码 0）。覆盖场景加载、8 帧行走/待机、东南·西南·东北·西北朝向、WASD/方向键、镜头跟随与地图边界。
