# PixelForge

PixelForge 是基于 Python 和 Aseprite 的本地像素美术构建工具。它读取已有的 Aseprite 工程或分层 PNG，生成可编辑的源工程、透明逐帧图和浏览器预览，并可导出精灵图集、GIF、MP4 和 Godot 4 工程。

## 安装

准备 Python 3.11+ 和 [Aseprite](https://www.aseprite.org/)。在仓库根目录安装 Python 依赖。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

以下命令以 Windows PowerShell 为例。其他系统使用虚拟环境中的 Python，并将 `--aseprite` 指向对应的 Aseprite 可执行文件。按规格构建在本机运行，无需 API 密钥。

## 快速开始

### 从已有 Aseprite 工程导出

将以下内容保存为 `project.json`，与 `character.aseprite` 放在同一目录。构建会保留源工程的画布、图层、帧时长和标签。

```json
{
  "name": "角色行走",
  "source": "character.aseprite",
  "formats": ["atlas", "gif", "mp4", "godot"],
  "preview_scale": 3,
  "video_fps": 60
}
```

替换 Aseprite 的安装路径，并为每次构建指定一个尚未创建的输出目录。

```powershell
.\.venv\Scripts\python.exe main.py build --spec .\project.json --output .\output\character_v1 --aseprite "C:\Path\To\Aseprite.exe"
```

在浏览器打开 `output/character_v1/index.html` 查看循环预览。在 Aseprite 打开 `source.aseprite` 继续编辑。

### 从分层 PNG 构建

在 JSON 中用 `size` 和 `layers` 描述静态素材或动画，然后运行同一条构建命令。

```json
{
  "name": "像素道具",
  "size": [32, 32],
  "layers": [
    {"name": "轮廓", "frames": ["base.png"]},
    {"name": "高光", "frames": ["highlight.png"]}
  ],
  "formats": ["png"]
}
```

- 素材路径以 JSON 所在目录为基准。图层顺序从底到顶，每张 PNG 的尺寸须与 `size` 一致。
- 静态作品默认一帧，时长为 100 毫秒。动画可用 `"durations_ms": [100, 120, 100]` 指定帧时长，每个图层的 `frames` 都应提供等量条目。用 `null` 表示该帧的图层全透明。

## 输出文件

| 文件 | 用途 |
| --- | --- |
| `source.aseprite` | 可编辑的 Aseprite 工程 |
| `frames/frame_000.png` 等 | Aseprite 渲染的原生尺寸逐帧 PNG |
| `index.html` | 本地循环预览和导出链接 |
| `manifest.json`、`verify.json` | 构建规格、产物清单和技术检查结果 |
| `atlas.png`、`atlas.json` | 精灵图集和每帧元数据，选择 `atlas` 或 `godot` 时生成 |
| `preview.gif`、`preview.mp4` | 按 `gif`、`mp4` 选项生成的预览 |
| `godot/project.godot` | Godot 4 示例工程，选择 `godot` 时生成 |

省略 `formats` 时，单帧作品使用 `png`，多帧作品使用 `atlas` 和 `gif`。逐帧 PNG 始终导出。选择 `png` 可在预览页中列出全部逐帧文件。

Aseprite 和图集保留毫秒级帧时长。GIF 以 10 毫秒为单位，MP4 按 `video_fps` 转换为固定帧率。导出 MP4 时可用 `video_background` 指定透明区域的底色，也可用 `audio` 加入现有音轨。音轨按画面时长裁齐或补静音。

构建完成后查看 `verify.json`，再在预览页检查实际画面的透明边缘、节奏和循环接缝。

## 可选入口

- `main.py demo` 在本地生成城市行走示例。运行时可传 `--aseprite` 指定安装路径，或传 `--no-aseprite` 跳过原生工程导出。
- 安装 `requirements-optional.txt` 后，`main.py serve` 可在 `127.0.0.1:8765` 启动城市行走示例的本地 API。接口说明位于 `/docs`。
- 命令行示例支持 `--langgraph` 和 `--llm`。显式选择 `--llm` 时需要设置 `OPENAI_API_KEY`。
