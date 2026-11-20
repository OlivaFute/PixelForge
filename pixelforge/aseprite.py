"""Generate trusted Lua and execute the local Aseprite binary without a shell."""
from pathlib import Path
import json
import os
import subprocess
import shutil

DEFAULT_ASEPRITE=Path(r'D:\Steam\steamapps\common\Aseprite\Aseprite.exe')

def locate_aseprite(path=None):
    value=path or os.environ.get('ASEPRITE_PATH') or shutil.which('aseprite') or DEFAULT_ASEPRITE
    result=Path(value).expanduser().resolve()
    if not result.is_file(): raise FileNotFoundError(f'Aseprite not found: {result}; set ASEPRITE_PATH.')
    return result

def build_lua(output:Path,layers:list[str],durations:list[int],width=320,height=180,stem='city_walk'):
    output=Path(output).resolve(); script=output/'create_city.lua'
    # Paths and layer names use UTF-8 and exclude control characters.
    root=json.dumps(output.as_posix(),ensure_ascii=False)
    names='{'+','.join(json.dumps(s,ensure_ascii=False) for s in layers)+'}'
    times='{'+','.join(str(v) for v in durations)+'}'
    script.write_text(f'''-- PixelForge generated project: run with Aseprite --batch --script.
-- Reusable with --script-param root=/path/to/output, with sibling layers folder.
local root = app.params["root"] or {root}
local names = {names}
local durations = {times}
local sprite = Sprite({width}, {height}, ColorMode.RGB)
sprite:deleteLayer(sprite.layers[1])
local layers = {{}}
for i,name in ipairs(names) do
  layers[i] = sprite:newLayer()
  layers[i].name = name
end
for f=1,#durations do
  if f > 1 then sprite:newEmptyFrame() end
  sprite.frames[f].duration = durations[f]/1000
  for i,layer in ipairs(layers) do
    local filename = string.format("%s/layers/layer_%02d_%03d.png",root,i-1,f-1)
    local pixels = Image{{ fromFile=filename }}
    sprite:newCel(layer,f,pixels,Point(0,0))
  end
end
local tag = sprite:newTag(1,#durations)
tag.name = {json.dumps(stem)}
sprite:saveAs(root .. "/{stem}.aseprite")
-- Aseprite exports its own render so the Python images can be roundtrip checked.
for f=1,#durations do
  local image = Image(sprite.spec)
  image:drawSprite(sprite,f)
  image:saveAs(string.format("%s/aseprite_frames/frame_%03d.png",root,f-1))
end
local frameTimes = {{}}
for i, frame in ipairs(sprite.frames) do
  frameTimes[i] = math.floor(frame.duration * 1000 + 0.5)
end
local file = io.open(root .. "/aseprite_manifest.json","w")
file:write(json.encode({{width=sprite.width,height=sprite.height,frames=#sprite.frames,layers=#sprite.layers,total_ms={sum(durations)},durations_ms=frameTimes,tags={{{{name=tag.name,from=0,to=#sprite.frames-1}}}},version=tostring(app.version)}}))
file:close()
sprite:close()
''',encoding='utf8')
    return script

def execute_aseprite(output:Path,layers:list[str],durations:list[int],executable=None,width=320,height=180,stem='city_walk'):
    output=Path(output).resolve()
    (output/'aseprite_frames').mkdir(exist_ok=True)
    script=build_lua(output,layers,durations,width,height,stem)
    return run_aseprite_script(output, script, executable)


def render_project(output: Path, source: Path, executable=None):
    """Export the real composite and timing of an existing editable project."""
    (output / 'aseprite_frames').mkdir(exist_ok=True)
    root = json.dumps(output.as_posix(), ensure_ascii=False)
    project = json.dumps(source.as_posix(), ensure_ascii=False)
    script = output / 'render_project.lua'
    script.write_text(f'''local root = {root}
local sprite = assert(app.open({project}), 'Cannot open Aseprite project')
local durations = {{}}
local tags = {{}}
for i, frame in ipairs(sprite.frames) do
  local image = Image(sprite.spec)
  image:drawSprite(sprite, i)
  image:saveAs(string.format('%s/aseprite_frames/frame_%03d.png', root, i - 1))
  durations[i] = math.floor(frame.duration * 1000 + 0.5)
end
for _, tag in ipairs(sprite.tags) do
  tags[#tags + 1] = {{name=tag.name, from=tag.fromFrame.frameNumber-1, to=tag.toFrame.frameNumber-1}}
end
local file = assert(io.open(root .. '/aseprite_manifest.json', 'w'))
file:write(json.encode({{width=sprite.width, height=sprite.height, frames=#sprite.frames,
                        layers=#sprite.layers, durations_ms=durations, tags=tags,
                        version=tostring(app.version)}}))
file:close()
sprite:close()
''', encoding='utf8')
    return run_aseprite_script(output, script, executable)


def run_aseprite_script(output: Path, script: Path, executable):
    exe=locate_aseprite(executable)
    # Keep Aseprite's temporary/config files under this project.
    env=os.environ.copy()
    profile=output/'.aseprite_profile'; profile.mkdir(exist_ok=True)
    env['APPDATA']=str(profile); env['LOCALAPPDATA']=str(profile)
    proc=subprocess.run([str(exe),'--batch','--script',str(script)],env=env,capture_output=True,timeout=120)
    log=(proc.stdout+proc.stderr).decode('utf8',errors='replace')
    (output/'aseprite.log').write_text(log,encoding='utf8')
    manifest=output/'aseprite_manifest.json'
    if proc.returncode or not manifest.exists():
        raise RuntimeError(f'Aseprite creation failed (exit {proc.returncode}). See {output / "aseprite.log"}: {log[-1000:]}')
    info=json.loads(manifest.read_text(encoding='utf8'))
    info['executable']=str(exe); info['script']=str(script)
    return info
