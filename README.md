# game-ui-image-to-godot

一个可安装到 Codex 的 Agent Skill，用于把游戏 UI 设计图拆成图片素材，并生成 Godot 4 的 UI 场景和 GDScript。

## 它能做什么

1. 检查设计图尺寸，并建立 UI 元素 JSON 清单。
2. 按照清单中的矩形坐标批量裁切 PNG，保留原图 Alpha 透明通道。
3. 生成裁切结果预览图，便于人工检查边界。
4. 自动生成 Godot 4 的 `.tscn` 和 `.gd` 文件。
5. 支持 `Control`、`TextureRect`、`TextureButton`、`NinePatchRect` 和 `Label`。
6. 可调用 Godot 命令行进行 headless 导入和场景启动验证。

**重要：** 图片识别和 Bounding Box 判断由 Codex 的视觉能力完成；随包脚本负责精确、可重复的矩形裁切和 Scene 生成。矩形裁切不等于图像分割：如果按钮或图标已经和背景合成在一张扁平图片里，裁切不会自动抠出透明背景，也不会补回被遮挡的像素。

## 环境要求

- Codex CLI / IDE / Codex 桌面端（支持本地 Skill）
- Python 3.9+
- Pillow：`python -m pip install -r requirements.txt`
- Godot 4.x（仅在需要自动运行验证时必需，并建议配置到 PATH）

## 安装到 Codex

### 用户级安装（所有项目可用）

**macOS / Linux**

```bash
mkdir -p "$HOME/.agents/skills"
unzip game-ui-image-to-godot.zip -d "$HOME/.agents/skills/"
python -m pip install -r "$HOME/.agents/skills/game-ui-image-to-godot/requirements.txt"
```

安装后应为：

```text
~/.agents/skills/game-ui-image-to-godot/SKILL.md
```

**Windows PowerShell**

```powershell
$skills = Join-Path $HOME ".agents\skills"
New-Item -ItemType Directory -Force -Path $skills | Out-Null
Expand-Archive -Force .\game-ui-image-to-godot.zip $skills
py -m pip install -r (Join-Path $skills "game-ui-image-to-godot\requirements.txt")
```

如果 Codex 没有显示此 Skill，重启 Codex，并确认 `SKILL.md` 就在该 Skill 文件夹的第一层。若你的 Codex 配置了自定义 `CODEX_HOME`，也可以把文件夹安装到 `$CODEX_HOME/skills`。

### 项目级安装（与 Godot 项目一起提交 Git）

```bash
mkdir -p /path/to/godot-project/.agents/skills
cp -R /path/to/game-ui-image-to-godot /path/to/godot-project/.agents/skills/
```

然后从 Codex 打开这个 Godot 项目目录。

## ChatGPT 兼容性

这是一份独立的本地 Agent Skill，主要面向 Codex；在支持本地 Skills 的 ChatGPT 桌面端也可按其本地 Skills 目录使用。ChatGPT 网页端的 Chat / Work 分发方式与独立本地 Skill 不同，通常需要将 Skill 进一步打包成 Plugin；当前 ZIP 本身不是 ChatGPT Plugin。

## 在 Codex 中使用

可以显式调用 `$game-ui-image-to-godot`，也可以直接描述需求让 Codex 根据 Skill 的描述自动选择。

示例提示词：

> `$game-ui-image-to-godot 请把 design/main_menu.png 还原成当前 Godot 4 项目的主菜单。先识别背景、Logo、开始/设置/退出按钮和面板，生成待检查的 manifest；确认边界后裁切素材、生成 Scene 和脚本，并用 headless Godot 检查。不要覆盖已有文件。`

## 手动运行命令

在 Skill 目录下执行：

```bash
python -m pip install -r requirements.txt
python scripts/inspect_design.py /path/to/design.png --output /path/to/ui_manifest.json --project-name MainMenu
# 编辑 ui_manifest.json，添加 UI 元素的 bbox、类型和输出路径
python scripts/validate_manifest.py /path/to/ui_manifest.json --check-source
python scripts/slice_assets.py /path/to/ui_manifest.json --project-root /path/to/godot-project
python scripts/make_contact_sheet.py /path/to/godot-project/.ui-slicing-report.json --output /path/to/godot-project/ui_contact_sheet.png
python scripts/generate_godot_ui.py /path/to/ui_manifest.json --project-root /path/to/godot-project
```

只有在确实要替换已有裁切素材或生成文件时，才添加 `--force`。

## 当前限制

- 使用矩形 Bounding Box 裁切；相互重叠、带复杂阴影或已经与背景合成的素材可能需要手动蒙版、抠图或修图。
- 图片中的文字不会自动变成可编辑文本；建议把它声明为 `label`，或为按钮填写 `text`。
- 生成的锚点根据设计图比例进行比例布局。宽高比差异较大的设备仍需在 Godot 中检查并微调。
- 自动生成的按钮回调只是占位函数，需要连接到你自己的游戏逻辑。

## 开源许可

MIT License，详见 `LICENSE`。
