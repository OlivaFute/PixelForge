"""Pixel-art atlases, GIF loops and nearest-neighbor H.264 previews."""
from itertools import accumulate
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageColor


def export_atlas(output, frames, durations, tags):
    width, height = frames[0].size
    columns = min(8, len(frames))
    atlas = Image.new('RGBA', (width * columns, height * ((len(frames) + columns - 1) // columns)))
    entries = []
    for index, (frame, duration) in enumerate(zip(frames, durations)):
        x, y = index % columns * width, index // columns * height
        atlas.paste(frame, (x, y))
        entries.append({
            'filename': f'frame_{index:03d}.png',
            'frame': {'x': x, 'y': y, 'w': width, 'h': height},
            'duration': duration,
        })
    atlas.save(output / 'atlas.png')
    metadata = {'frames': entries, 'meta': {
        'image': 'atlas.png', 'size': {'w': atlas.width, 'h': atlas.height},
        'duration_ms': sum(durations), 'frameTags': tags,
    }}
    (output / 'atlas.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf8')
    with Image.open(output / 'atlas.png') as saved:
        for frame, entry in zip(frames, entries):
            rect = entry['frame']
            x, y = rect['x'], rect['y']
            if saved.crop((x, y, x + width, y + height)).tobytes() != frame.tobytes():
                raise RuntimeError('Atlas frames differ from the source PNG frames')
    return metadata


def export_gif(path, frames, durations, scale):
    boundaries = [0, *((total + 5) // 10 * 10 for total in accumulate(durations))]
    times = [end - start for start, end in zip(boundaries, boundaries[1:])]
    if any(time == 0 for time in times):
        raise ValueError('GIF cannot retain every frame at this timing. Use longer frames or omit GIF.')
    scaled = [
        frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
        for frame in frames
    ]
    scaled[0].save(path, save_all=True, append_images=scaled[1:], duration=times,
                   loop=0, disposal=2, optimize=False)
    with Image.open(path) as gif:
        actual = 0
        for index in range(gif.n_frames):
            gif.seek(index)
            actual += gif.info.get('duration', 0)
        if actual != boundaries[-1]:
            raise RuntimeError(f'GIF timing mismatch: expected {boundaries[-1]} ms, read {actual} ms')
        return {'frames': gif.n_frames, 'duration_ms': actual}


def export_video(path, frames, durations, scale, fps, background, audio=None):
    from imageio_ffmpeg import get_ffmpeg_exe, read_frames, write_frames

    width, height = (dimension * scale for dimension in frames[0].size)
    size = (width + width % 2, height + height % 2)
    boundaries = [0, *((total * fps + 500) // 1000 for total in accumulate(durations))]
    repeats = [end - start for start, end in zip(boundaries, boundaries[1:])]
    if any(repeat == 0 for repeat in repeats):
        raise ValueError('MP4 cannot retain every frame at this rate. Increase video_fps or omit MP4.')
    matte = ImageColor.getrgb(background)
    if len(matte) != 3:
        raise ValueError('video_background must be an opaque color')

    video = path if audio is None else path.with_name('silent.mp4')
    writer = write_frames(str(video), size, fps=fps, codec='libx264', pix_fmt_in='rgb24',
                          pix_fmt_out='yuv420p', macro_block_size=1,
                          output_params=['-movflags', '+faststart'])
    try:
        next(writer)
        for frame, repeat in zip(frames, repeats):
            scaled = frame.resize((width, height), Image.Resampling.NEAREST)
            image = Image.new('RGB', size, matte)
            image.paste(scaled, (0, 0), scaled.getchannel('A'))
            pixels = image.tobytes()
            for _ in range(repeat):
                writer.send(pixels)
    finally:
        writer.close()

    if audio is not None:
        result = subprocess.run([
            get_ffmpeg_exe(), '-v', 'error', '-i', str(video), '-i', str(audio),
            '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac',
            '-af', 'apad', '-t', f'{boundaries[-1] / fps:.9f}', '-movflags', '+faststart', str(path),
        ], capture_output=True, text=True, encoding='utf8', errors='replace', timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f'FFmpeg audio export failed: {result.stderr.strip()}')
        video.unlink()

    reader = read_frames(str(path))
    try:
        metadata = next(reader)
        count = sum(1 for _ in reader)
    finally:
        reader.close()
    if metadata['size'] != size or metadata['fps'] != fps or count != boundaries[-1]:
        raise RuntimeError('MP4 verification failed: resolution, frame rate or decoded frame count differs')
    return {'size': list(size), 'fps': fps, 'frames': count, 'duration_ms': count * 1000 / fps,
            'audio': audio is not None}

def export_media(output:Path,frames:list[Image.Image],durations:list[int]):
    output=Path(output); width,height=frames[0].size; count=len(frames)
    sheet=Image.new('RGBA',(width*10,height*((count+9)//10)))
    records=[]
    for i,frame in enumerate(frames):
        x=(i%10)*width; y=(i//10)*height; sheet.paste(frame,(x,y))
        records.append({'filename':f'frame_{i:03}.png','frame':{'x':x,'y':y,'w':width,'h':height},
                        'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':width,'h':height},
                        'sourceSize':{'w':width,'h':height},'duration':durations[i]})
    sheet.save(output/'city_walk.png')
    (output/'city_walk.json').write_text(json.dumps({'frames':records,'meta':{
        'app':'PixelForge + Aseprite','image':'city_walk.png','format':'RGBA8888',
        'size':{'w':sheet.width,'h':sheet.height},'scale':'1','fps':12,'duration_ms':sum(durations),
        'frameTags':[{'name':'city_walk','from':0,'to':count-1,'direction':'forward'}]}},indent=2),encoding='utf8')
    scaled=[im.resize((width*3,height*3),Image.Resampling.NEAREST) for im in frames]
    # GIF permits 10ms units, so distribute 5000ms over 60 frames as 80/90ms.
    gif_times=[(round((i+1)*500/count)-round(i*500/count))*10 for i in range(count)]
    palette=frames[0].quantize(colors=128,method=Image.Quantize.MEDIANCUT)
    gifs=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in scaled]
    gifs[0].save(output/'city_walk.gif',save_all=True,append_images=gifs[1:],duration=gif_times,loop=0,optimize=False,disposal=2)
    scaled[0].save(output/'preview.png')
    # A compact contact sheet shows all 12 gait poses without scaling blur.
    board=Image.new('RGB',(width*4,height*3))
    for i in range(12): board.paste(frames[i],((i%4)*width,(i//4)*height))
    board.save(output/'contact_sheet.png')
    import imageio_ffmpeg
    exe=imageio_ffmpeg.get_ffmpeg_exe()
    command=[exe,'-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width*3}x{height*3}',
             '-r','12','-i','pipe:0','-an','-c:v','libx264','-crf','16','-preset','medium',
             '-pix_fmt','yuv420p','-movflags','+faststart',str(output/'city_walk.mp4')]
    result=subprocess.run(command,input=b''.join(im.tobytes() for im in scaled),capture_output=True,timeout=90)
    (output/'ffmpeg.log').write_text(result.stderr.decode('utf8',errors='replace'),encoding='utf8')
    if result.returncode: raise RuntimeError('MP4 encode failed; see ffmpeg.log')
    probe=subprocess.run([exe,'-i',str(output/'city_walk.mp4'),'-f','null','-'],capture_output=True,timeout=30)
    (output/'mp4_probe.log').write_text(probe.stderr.decode('utf8',errors='replace'),encoding='utf8')
    return {'gif_duration_ms':sum(gif_times),'video_frames':count,'fps':12,'video_size':[width*3,height*3]}
