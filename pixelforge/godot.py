"""Export a portable Godot 4 project using the pipeline's native pixel assets."""

from __future__ import annotations

from pathlib import Path
import shutil


def _sprite_frames(texture: str, width: int, height: int, frames: int,
                   columns: int, fps: int, animation: str, durations_ms=None) -> str:
    sections = [
        f'[gd_resource type="SpriteFrames" load_steps={frames + 2} format=3]',
        "",
        f'[ext_resource type="Texture2D" path="res://assets/{texture}" id="1_texture"]',
    ]
    for i in range(frames):
        sections += [
            "",
            f'[sub_resource type="AtlasTexture" id="AtlasTexture_{i:03d}"]',
            'atlas = ExtResource("1_texture")',
            f'region = Rect2({i % columns * width}, {i // columns * height}, {width}, {height})',
        ]
    durations = [duration / 1000 for duration in durations_ms] if durations_ms is not None else [1.0] * frames
    entries = [
        '{"duration": %s, "texture": SubResource("AtlasTexture_%03d")}' % (duration, i)
        for i, duration in enumerate(durations)
    ]
    sections += [
        "",
        "[resource]",
        'animations = [{',
        '"frames": [\n' + ',\n'.join(entries) + '\n],',
        '"loop": true,',
        f'"name": &"{animation}",',
        f'"speed": {float(fps):.1f}',
        '}]',
        "",
    ]
    return "\n".join(sections)


def export_pixel_asset(output: Path, size, durations):
    project = output / 'godot'
    (project / 'assets').mkdir(parents=True)
    shutil.copyfile(output / 'atlas.png', project / 'assets' / 'atlas.png')
    resource = _sprite_frames('atlas.png', *size, len(durations),
                              min(8, len(durations)), 1, 'preview', durations)
    (project / 'frames.tres').write_text(resource, encoding='utf8')
    (project / 'project.godot').write_text(f'''config_version=5

[application]
config/name="PixelForge"
run/main_scene="res://Preview.tscn"

[display]
window/size/viewport_width={size[0]}
window/size/viewport_height={size[1]}
window/size/window_width_override={size[0] * 3}
window/size/window_height_override={size[1] * 3}
window/stretch/mode="canvas_items"
window/stretch/scale_mode="integer"

[rendering]
renderer/rendering_method="gl_compatibility"
''', encoding='utf8')
    position = f'Vector2({size[0] / 2:g}, {size[1] / 2:g})'
    (project / 'Preview.tscn').write_text(f'''[gd_scene load_steps=2 format=3]

[ext_resource type="SpriteFrames" path="res://frames.tres" id="1_frames"]

[node name="Preview" type="AnimatedSprite2D"]
texture_filter = 1
position = {position}
sprite_frames = ExtResource("1_frames")
animation = &"preview"
autoplay = "preview"
''', encoding='utf8')


def export_godot(output: Path, width: int = 320, height: int = 180,
                 frames: int = 60, fps: int = 12) -> dict:
    """Write a self-contained Godot 4 project; return relative artifact paths.

    The full scene already includes its walking character. Main plays that
    composite once every ``frames / fps`` seconds. Character.tscn and walk.tres
    expose the separate reusable character, without drawing it twice in Main.
    """
    output = Path(output)
    if width <= 0 or height <= 0 or frames <= 0 or fps <= 0:
        raise ValueError("Dimensions, frame count, and frame rate must be positive")
    columns = 10
    if frames % columns:
        raise ValueError("The scene spritesheet requires complete rows of 10 frames")
    sources = [output / "city_walk.png", output / "walk_character.png"]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
    project = output / "godot"
    assets = project / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for source in sources:
        shutil.copyfile(source, assets / source.name)
    (project / "scene.tres").write_text(
        _sprite_frames("city_walk.png", width, height, frames, columns, fps, "city_walk"),
        encoding="utf-8",
    )
    (project / "walk.tres").write_text(
        _sprite_frames("walk_character.png", 32, 48, 8, 8, 8, "walk"),
        encoding="utf-8",
    )
    (project / "project.godot").write_text(f'''config_version=5

[application]
config/name="PixelForge — City Walk"
run/main_scene="res://Main.tscn"
run/max_fps=60
config/features=PackedStringArray("4.0", "GL Compatibility")

[display]
window/size/viewport_width={width}
window/size/viewport_height={height}
window/size/window_width_override={width * 3}
window/size/window_height_override={height * 3}
window/stretch/mode="canvas_items"
window/stretch/scale_mode="integer"

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
textures/default_filters/use_nearest_mipmap_filter=false
textures/canvas_textures/default_texture_filter=0
environment/defaults/default_clear_color=Color(0.035, 0.047, 0.086, 1)

[physics]
common/physics_ticks_per_second=60
''', encoding="utf-8")
    (project / "Main.tscn").write_text(f'''[gd_scene load_steps=2 format=3]

[ext_resource type="SpriteFrames" path="res://scene.tres" id="1_scene"]

[node name="CityWalk" type="Node2D"]
texture_filter = 1

[node name="Scene" type="AnimatedSprite2D" parent="."]
position = Vector2({width / 2:g}, {height / 2:g})
sprite_frames = ExtResource("1_scene")
animation = &"city_walk"
autoplay = "city_walk"
''', encoding="utf-8")
    (project / "Character.tscn").write_text('''[gd_scene load_steps=2 format=3]

[ext_resource type="SpriteFrames" path="res://walk.tres" id="1_walk"]

[node name="WalkingCharacter" type="AnimatedSprite2D"]
texture_filter = 1
sprite_frames = ExtResource("1_walk")
animation = &"walk"
autoplay = "walk"
''', encoding="utf-8")
    return {
        "project": "godot/project.godot",
        "main_scene": "godot/Main.tscn",
        "scene_animation": "godot/scene.tres",
        "character_animation": "godot/walk.tres",
        "character_scene": "godot/Character.tscn",
        "duration_seconds": frames / fps,
        "fps": fps,
        "frame_count": frames,
    }
