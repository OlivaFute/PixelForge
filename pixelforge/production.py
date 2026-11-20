"""Build an editable pixel asset and verify exports from its Aseprite frames."""
from __future__ import annotations

from collections.abc import Sequence
from html import escape
from itertools import accumulate
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from PIL import Image

from .aseprite import execute_aseprite, render_project
from .exporter import export_atlas, export_gif, export_video
from .godot import export_pixel_asset


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf8')


def positive_int(value):
    return type(value) is int and value > 0


class RenderedFrames(Sequence):
    def __init__(self, folder, count, size):
        self.paths = tuple(folder / f'frame_{index:03d}.png' for index in range(count))
        self.size = size

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        path = self.paths[index]
        with Image.open(path) as image:
            if image.size != self.size:
                raise RuntimeError(f'Aseprite frame {path.name} has an unexpected size')
            return image.convert('RGBA')


def materialize_layers(spec, inputs, work, executable):
    size = spec.get('size')
    if not isinstance(size, list) or len(size) != 2 or not all(map(positive_int, size)):
        raise ValueError('size must contain the positive integer width and height')
    layers = spec.get('layers')
    if not isinstance(layers, list) or not layers:
        raise ValueError('layers must be a non-empty list ordered from bottom to top')
    durations = spec.get('durations_ms', [100])
    if not isinstance(durations, list) or not durations or not all(map(positive_int, durations)):
        raise ValueError('durations_ms must contain one positive integer per frame')
    (work / 'layers').mkdir()
    names = []
    for layer_index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise ValueError(f'Layer {layer_index + 1} must specify name and frames')
        name = layer.get('name')
        if not isinstance(name, str) or not name.strip() or not name.isprintable() or name in names:
            raise ValueError(f'Layer {layer_index + 1} must have a unique, printable name')
        sources = layer.get('frames')
        if not isinstance(sources, list) or len(sources) != len(durations):
            raise ValueError(f'Layer {name} needs one PNG path or null per frame')
        names.append(name)
        for frame_index, source in enumerate(sources):
            target = work / 'layers' / f'layer_{layer_index:02d}_{frame_index:03d}.png'
            if source is None:
                Image.new('RGBA', size).save(target)
                continue
            if not isinstance(source, str) or Path(source).suffix.lower() != '.png':
                raise ValueError(f'Layer {name}, frame {frame_index + 1}: expected a PNG path or null')
            with Image.open(inputs / source) as image:
                if image.format != 'PNG' or image.size != tuple(size) or image.n_frames != 1:
                    raise ValueError(f'{source} must be a single {size[0]}×{size[1]} PNG')
                image.convert('RGBA').save(target)
    native = execute_aseprite(work, names, durations, executable, *size, stem='source')
    if native['durations_ms'] != durations or native['layers'] != len(layers):
        raise RuntimeError('Saved Aseprite timeline or layer count differs from the specification')
    return native


def preview_page(output, name, frame_paths, durations, assets, scale):
    timeline = json.dumps({'frames': frame_paths, 'ends': list(accumulate(durations))})
    links = ''.join(f'<li><a href="{escape(path)}">{escape(path)}</a></li>' for path in assets)
    video = ('<video controls loop playsinline preload="metadata" src="preview.mp4"></video>'
             if 'preview.mp4' in assets else '')
    (output / 'index.html').write_text(f'''<!doctype html>
<html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(name)}</title>
<style>
body {{font: 16px system-ui; background: #20232b; color: #f2f2f5; margin: 2rem}}
a {{color: #b5d8ff}}
video {{display: block; max-width: 100%; margin-bottom: 1rem}}
canvas {{image-rendering: pixelated; max-width: 100%; background: #777;
  background-image: conic-gradient(#555 25%, transparent 0 50%, #555 0 75%, transparent 0);
  background-size: 16px 16px}}
</style>
<h1>{escape(name)}</h1>
{video}
<canvas aria-label="像素素材预览"></canvas>
<p id="status" role="status">正在载入逐帧画面</p>
<ul>{links}</ul>
<script>
const timeline = {timeline};
const canvas = document.querySelector('canvas');
const context = canvas.getContext('2d');
const duration = timeline.ends.at(-1);
const count = timeline.frames.length;
const status = document.querySelector('#status');
const cache = new Map();
const start = performance.now();
let previous = -1;
function draw(now) {{
  const index = timeline.ends.findIndex(end => end > Math.max(0, now - start) % duration);
  const wanted = Array.from({{length: Math.min(12, count)}}, (_, offset) => (index + offset) % count);
  for (const key of cache.keys()) {{
    if (!wanted.includes(key)) cache.delete(key);
  }}
  for (const key of wanted) {{
    if (!cache.has(key)) {{
      const image = new Image();
      image.onerror = () => {{status.textContent = '无法加载预览帧';}};
      image.src = timeline.frames[key];
      cache.set(key, image);
    }}
  }}
  const image = cache.get(index);
  if (index !== previous && image.complete && image.naturalWidth > 0) {{
    if (previous === -1) {{
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      canvas.style.width = (canvas.width * {scale}) + 'px';
      status.textContent = count + ' 帧 · ' + duration + ' ms';
    }}
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0);
    previous = index;
  }}
  if (count > 1 || !image.complete) requestAnimationFrame(draw);
}}
requestAnimationFrame(draw);
</script></html>''', encoding='utf8')


def run_production(spec_path: Path, output: Path, executable=None):
    spec_path, output = spec_path.resolve(), output.resolve()
    spec = json.loads(spec_path.read_text(encoding='utf-8-sig'))
    if not isinstance(spec, dict):
        raise ValueError('The specification must be a JSON object')
    if ('source' in spec) == ('layers' in spec):
        raise ValueError('Specify either an editable source or a list of PNG layers')
    name = spec.get('name', spec_path.stem)
    if not isinstance(name, str) or not name.strip():
        raise ValueError('name must be a non-empty string')
    scale = spec.get('preview_scale', 3)
    if not positive_int(scale):
        raise ValueError('preview_scale must be a positive integer')
    formats = spec.get('formats')
    if 'formats' in spec and (not isinstance(formats, list) or any(
            item not in ('png', 'atlas', 'gif', 'mp4', 'godot') for item in formats)):
        raise ValueError('formats must be a list containing png, atlas, gif, mp4 or godot')
    if output.exists():
        raise FileExistsError(f'Output already exists. Choose a new version directory: {output}')

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.pixelforge-', dir=output.parent) as directory:
        staging = Path(directory)
        work = staging / 'work'
        work.mkdir()
        delivery = staging / 'delivery'
        delivery.mkdir()
        if 'source' in spec:
            source = spec['source']
            if not isinstance(source, str) or Path(source).suffix.lower() not in ('.aseprite', '.ase'):
                raise ValueError('source must be an .aseprite or .ase file')
            if 'durations_ms' in spec or 'size' in spec:
                raise ValueError('Use the editable project timeline and size when specifying source')
            shutil.copyfile(spec_path.parent / source, work / 'source.aseprite')
            native = render_project(work, work / 'source.aseprite', executable)
        else:
            native = materialize_layers(spec, spec_path.parent, work, executable)

        size = (native['width'], native['height'])
        durations = native['durations_ms']
        native_frames = sorted((work / 'aseprite_frames').glob('frame_*.png'))
        if len(native_frames) != len(durations) or len(durations) != native['frames'] or (
                not durations or not all(map(positive_int, durations))):
            raise RuntimeError('Aseprite frame files do not match the reported timeline')
        rendered_folder = delivery / 'frames'
        if formats is None:
            formats = ['png'] if len(durations) == 1 else ['atlas', 'gif']
        audio = None
        if 'audio' in spec:
            if 'mp4' not in formats or not isinstance(spec['audio'], str) or not spec['audio']:
                raise ValueError('audio must be a file path when mp4 is selected')
            audio = (spec_path.parent / spec['audio']).resolve()
            if not audio.is_file():
                raise FileNotFoundError(audio)
        shutil.copyfile(work / 'source.aseprite', delivery / 'source.aseprite')
        (work / 'aseprite_frames').rename(rendered_folder)
        frames = RenderedFrames(rendered_folder, len(durations), size)
        for frame in frames:
            frame.close()
        frame_paths = [f'frames/frame_{index:03d}.png' for index in range(len(frames))]
        assets = ['source.aseprite', frame_paths[0]]
        checks = {}
        if 'png' in formats and len(frames) > 1:
            assets.extend(frame_paths[1:])
        if 'atlas' in formats or 'godot' in formats:
            tags = native.get('tags') or []
            atlas = export_atlas(delivery, frames, durations, tags)
            checks['atlas'] = {'frames': len(atlas['frames']), 'duration_ms': sum(durations)}
            assets.extend(['atlas.png', 'atlas.json'])
        if 'godot' in formats:
            export_pixel_asset(delivery, size, durations)
            assets.extend(['godot/project.godot', 'godot/frames.tres'])
        if 'gif' in formats:
            checks['gif'] = export_gif(delivery / 'preview.gif', frames, durations, scale)
            assets.append('preview.gif')
        if 'mp4' in formats:
            fps = spec.get('video_fps', 60)
            if not positive_int(fps):
                raise ValueError('video_fps must be a positive integer')
            background = spec.get('video_background', '#20232b')
            if not isinstance(background, str):
                raise ValueError('video_background must be an opaque color')
            checks['mp4'] = export_video(delivery / 'preview.mp4', frames, durations, scale, fps,
                                         background, audio)
            assets.append('preview.mp4')

        manifest = {
            'name': name, 'size': list(size), 'frames': len(frames), 'layers': native['layers'],
            'durations_ms': durations, 'duration_ms': sum(durations), 'source': 'source.aseprite',
            'spec_path': str(spec_path), 'spec': spec, 'frame_directory': 'frames',
            'artifacts': assets, 'preview': 'index.html',
        }
        write_json(delivery / 'manifest.json', manifest)
        write_json(delivery / 'verify.json', {
            'passed': True, 'aseprite': native['version'], 'size': list(size),
            'frames': len(frames), 'duration_ms': sum(durations), 'exports': checks,
            'visual_review': 'pending',
        })
        preview_page(delivery, name, frame_paths, durations, [*assets, 'manifest.json', 'verify.json'], scale)
        delivery.rename(output)
    return {**manifest, 'output': str(output)}
