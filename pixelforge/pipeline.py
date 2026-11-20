"""End-to-end director -> designer -> render -> Aseprite -> review -> Godot."""
from pathlib import Path
import json
import os
import struct
from PIL import Image, ImageChops
from .agents.planner import plan_request
from .agents.designer import design_asset
from .agents.critic import inspect_frames, review_with_vision
from .agents.fixer import repair_plan
from .artwork import render_artwork, LAYERS
from .aseprite import execute_aseprite
from .exporter import export_media
from .godot import export_godot

def save_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf8')

def verify_deliverables(output,frames,native):
    checks=[]
    def check(name,passed,detail): checks.append({'name':name,'passed':bool(passed),'detail':detail})
    metadata=json.loads((output/'city_walk.json').read_text(encoding='utf8'))
    check('scene_timing',sum(f['duration'] for f in metadata['frames'])==5000,'60 frames / 12 fps / 5000 ms')
    with Image.open(output/'city_walk.gif') as gif:
        count=gif.n_frames; total=0
        for i in range(count): gif.seek(i); total+=gif.info['duration']
    check('gif_timing',count==60 and total==5000,{'frames':count,'duration_ms':total})
    poses=set()
    for i in range(12):
        with Image.open(output/'layers'/f'layer_05_{i:03}.png') as actor: poses.add(actor.tobytes())
    check('walking_character',len(poses)>=8,{'distinct_poses':len(poses),'anchor':[160,164]})
    if native:
        errors=[]
        for i,frame in enumerate(frames):
            with Image.open(output/'aseprite_frames'/f'frame_{i:03}.png') as exported:
                if ImageChops.difference(frame.convert('RGB'),exported.convert('RGB')).getbbox(): errors.append(i)
        check('aseprite_roundtrip',not errors,{'checked_frames':len(frames),'mismatched_frames':errors})
        data=(output/'city_walk.aseprite').read_bytes()
        _,magic,count,w,h=struct.unpack_from('<I4H',data)
        pos=128; times=[]
        for i in range(count):
            size,frame_magic,chunks,ms=struct.unpack_from('<I3H',data,pos)
            if frame_magic!=0xF1FA: raise RuntimeError('Invalid Aseprite frame header')
            times.append(ms); pos+=size
        check('editable_aseprite',magic==0xA5E0 and count==60 and (w,h)==(320,180) and sum(times)==5000,
              {'canvas':[w,h],'frames':count,'duration_ms':sum(times),'layers':native['layers'],'aseprite_version':native['version']})
    import imageio_ffmpeg
    reader=imageio_ffmpeg.read_frames(str(output/'city_walk.mp4'),pix_fmt='rgb24')
    info=next(reader); decoded=sum(1 for _ in reader)
    check('mp4_timing',decoded==60 and abs(info['duration']-5)<.01 and info['size']==(960,540),
          {'frames':decoded,'duration':info['duration'],'size':info['size'],'fps':info['fps']})
    report={'passed':all(c['passed'] for c in checks),'checks':checks,
            'godot_validation':'Resources exported; engine launch requires Godot 4.'}
    save_json(output/'verify.json',report)
    if not report['passed']: raise RuntimeError(f'Acceptance failed; see {output / "verify.json"}')
    return report

def preview_page(output,plan):
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PixelForge · 城市漫步</title><style>*{box-sizing:border-box}body{margin:0;background:#121523;color:#eee9de;font:16px system-ui}main{max-width:1100px;margin:60px auto;padding:0 28px}small{letter-spacing:4px;color:#82d8ca}h1{font-size:42px;font-weight:500;margin:14px 0}p{color:#aaa8b7;line-height:1.8}video{width:100%;image-rendering:pixelated;border:1px solid #45425a;border-radius:8px;margin:24px 0}a{color:#8fdfd2;margin-right:24px}.tag{display:inline-block;padding:7px 12px;margin:12px 12px 0 0;border:1px solid #424154;border-radius:30px;color:#cbc4d0}footer{margin-top:35px;border-top:1px solid #343445;padding-top:18px}</style><main>
<small>PIXELFORGE / A LITTLE CITY IN MOTION</small><h1>黄昏，沿街漫步。</h1><p>暖灯亮起的像素城市。跟随中央的背包行人，走过咖啡店、街机厅与深夜便利店。</p>
<span class="tag">5 秒循环</span><span class="tag">320 × 180 原生像素</span><span class="tag">60 帧 · 12 fps</span><span class="tag">7 个可编辑图层</span>
<video src="city_walk.mp4" autoplay muted loop controls poster="preview.png"></video>
<footer><a href="city_walk.gif">GIF 动画</a><a href="city_walk.mp4">MP4 视频</a><a href="city_walk.aseprite">Aseprite 工程</a><a href="godot/project.godot">Godot 项目</a><a href="verify.json">验收报告</a></footer></main></html>'''
    titles={'sunset':'黄昏，沿街漫步。','night':'夜色，沿街漫步。','day':'晴日，沿街漫步。'}
    page=page.replace('黄昏，沿街漫步。',titles[plan.style])
    if plan.style=='day': page=page.replace('暖灯亮起的像素城市。','晴日下的像素城市。')
    if not (output/'city_walk.aseprite').exists(): page=page.replace('<a href="city_walk.aseprite">Aseprite 工程</a>','')
    (output/'index.html').write_text(page,encoding='utf8')

def run_pipeline(prompt:str,output:Path,aseprite=None,use_llm:bool=False)->dict:
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    history=[]
    def render(design):
        images,_=render_artwork(output,design.plan.style,design.palette)
        return images
    if os.getenv('PIXELFORGE_USE_LANGGRAPH')=='1':
        from .agents.graph import compile_asset_graph
        state=compile_asset_graph(render,use_llm=use_llm).invoke({'prompt':prompt})
        design=state['design']; plan=design.plan; frames=state['frames']; review=state['review']
        history.append({'stage':'langgraph','review':review.to_dict()})
    else:
        plan=plan_request(prompt,use_llm); design=design_asset(plan,use_llm); frames=render(design)
        review=review_with_vision(frames,plan) if use_llm else inspect_frames(frames,plan)
        history.append({'stage':'initial_review','review':review.to_dict()})
        if review.issues:
            repaired=repair_plan(plan,review)
            if repaired.palette!=plan.palette or repaired.frame_durations_ms!=plan.frame_durations_ms:
                design.plan=repaired; design.palette=repaired.palette; plan=repaired; frames=render(design)
                review=inspect_frames(frames,plan); history.append({'stage':'repair_review','review':review.to_dict()})
    if not review.passed:
        save_json(output/'critic.json',review.to_dict())
        raise RuntimeError(f'Art review failed; see {output / "critic.json"}')
    native=execute_aseprite(output,LAYERS,plan.frame_durations_ms,aseprite) if aseprite else None
    media=export_media(output,frames,plan.frame_durations_ms)
    godot=export_godot(output)
    save_json(output/'plan.json',plan.to_dict()); save_json(output/'design.json',design.to_dict())
    save_json(output/'critic.json',review.to_dict()); save_json(output/'workflow.json',history)
    verification=verify_deliverables(output,frames,native)
    preview_page(output,plan)
    result={'status':'complete','output':str(output),'duration_seconds':5,'canvas':[320,180],
            'frames':60,'fps':12,'aseprite':native,'media':media,'godot':godot,
            'verification':verification,'llm_used':use_llm,'preview':str(output/'index.html')}
    save_json(output/'manifest.json',result)
    return result
