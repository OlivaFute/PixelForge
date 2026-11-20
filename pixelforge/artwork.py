"""Hand-authored integer pixel art. No antialiasing or external image assets."""
from pathlib import Path
from math import sin, cos, pi
import json
import random
from PIL import Image, ImageDraw, ImageFont

W, H, COUNT, FPS = 320, 180, 60, 12
C = {
    'ink':'#181c35', 'deep':'#23233f', 'purple':'#433651', 'wall':'#53415c',
    'brick':'#785366', 'edge':'#b17b80', 'rose':'#e79993', 'cream':'#ffe2b4',
    'gold':'#ffb66e', 'orange':'#e57862', 'cyan':'#79d5d1', 'teal':'#39949f',
    'darkteal':'#285667', 'blue':'#445778', 'pave':'#504c69', 'pavelight':'#76657f',
    'green':'#426761', 'leaf':'#719578', 'hair':'#363149', 'skin':'#efbd98',
    'skinshade':'#bc827e', 'coat':'#dc775e', 'coatlight':'#f3a16e', 'pants':'#324967',
    'far':'#5d4c69','cloud':'#986277','shoe':'#181c35',
}
SKY_BANDS=['#38334f','#473653','#5c405c','#784b65','#a56377','#c77a85','#e29692','#ecae9c']
THEME='sunset'

def canvas():
    return Image.new('RGBA', (W,H), (0,0,0,0))

def r(d, box, color):
    d.rectangle(tuple(int(v) for v in box), fill=C.get(color,color))

def line(d, points, color, width=1):
    d.line([(int(x),int(y)) for x,y in points], fill=C.get(color,color), width=width)

FONT = ImageFont.load_default(size=8)

def label(d,x,y,s,color='cream'):
    # Bitmap font masks are explicitly thresholded to keep hard pixel edges.
    mask=Image.new('L',(90,12)); md=ImageDraw.Draw(mask); md.text((0,-1),s,font=FONT,fill=255)
    mask=mask.point(lambda p:255 if p>=100 else 0)
    d.bitmap((int(x),int(y)),mask,fill=C.get(color,color))

def sky(f):
    im=canvas(); d=ImageDraw.Draw(im)
    bands=SKY_BANDS
    for n,col in enumerate(bands): r(d,(0,n*11,W-1,(n+1)*11),col)
    d.ellipse((243,12,263,32),fill=C['cream'])
    if THEME!='day': d.ellipse((239,9,258,27),fill=bands[1])
    for x,y in [(18,14),(89,9),(174,22),(222,6),(295,34),(130,28)]:
        r(d,(x,y,x+1,y),'rose')
    # The cloud band travels one 80 pixel repeat over exactly one loop.
    off=round(f*80/COUNT)
    for base in range(-80,400,80):
        x=base-off
        r(d,(x+5,43,x+42,44),'cloud'); r(d,(x+12,40,x+32,42),'cloud')
        r(d,(x+54,59,x+78,60),'#c58489')
    return im

def skyline(f):
    im=canvas(); d=ImageDraw.Draw(im); off=round(f*160/COUNT)
    heights=[43,64,33,58,46,76,51,38]
    for base in (-160,0,160,320):
        rng=random.Random(13)
        for n,h in enumerate(heights):
            x=base+n*20-off; y=100-h
            r(d,(x,y,x+17,113),'far'); r(d,(x+2,y+2,x+16,y+3),'edge')
            for wx in range(x+3,x+17,5):
                for wy in range(y+7,108,8):
                    if rng.random()>.45: r(d,(wx,wy,wx+1,wy+2),'#b78c97')
            if n==5:
                line(d,[(x+8,y),(x+8,y-11)],'purple'); r(d,(x+7,y-12,x+9,y-11),'rose')
    return im

def shop(d,x,y,w,h,kind):
    r(d,(x,y,x+w-1,139),'ink'); r(d,(x+2,y+3,x+w-3,138),'wall')
    r(d,(x,y,x+w-1,y+2),'edge'); r(d,(x-2,y-3,x+w+1,y-1),'deep')
    r(d,(x+3,y+5,x+w-4,y+6),'brick')
    for by in range(y+12,112,6):
        for bx in range(x+4+(by%12),x+w-4,15):
            line(d,[(bx,by),(bx+6,by)],'brick')
    # Upper floor framed windows and tiny sill highlights.
    for wx in range(x+8,x+w-10,22):
        r(d,(wx,y+12,wx+12,y+30),'deep'); r(d,(wx+2,y+14,wx+10,y+27),'gold')
        r(d,(wx+3,y+14,wx+4,y+27),'cream'); line(d,[(wx+6,y+14),(wx+6,y+28)],'brick')
        line(d,[(wx,y+22),(wx+12,y+22)],'brick'); r(d,(wx-1,y+31,wx+13,y+32),'edge')
    # Cable, air conditioning and rooftop water tank.
    r(d,(x+6,y-11,x+20,y-4),'blue'); r(d,(x+8,y-10,x+18,y-9),'edge')
    line(d,[(x+8,y-3),(x+8,y)],'ink'); line(d,[(x+19,y-3),(x+19,y)],'ink')
    r(d,(x+w-17,y+39,x+w-4,y+48),'pavelight')
    for v in range(3): line(d,[(x+w-15,y+41+v*2),(x+w-6,y+41+v*2)],'purple')
    sign_y=106
    signcol=('orange','teal','brick')[kind]
    r(d,(x+3,sign_y-1,x+w-4,sign_y+11),'ink')
    r(d,(x+5,sign_y,x+w-6,sign_y+9),signcol)
    name=('MOON CAFE','ARCADE','NIGHT MART')[kind]
    label(d,x+9,sign_y+1,name)
    # Bright storefront glass.
    r(d,(x+5,119,x+w-6,137),'deep')
    for wx in range(x+8,x+w-7,19):
        r(d,(wx,120,min(wx+15,x+w-8),135),'darkteal')
        line(d,[(wx+1,121),(wx+1,134)],'cyan')
        line(d,[(wx+4,121),(wx+12,128)],'teal')
    door=x+w-24
    r(d,(door,119,door+15,138),'ink'); r(d,(door+2,120,door+13,134),'teal')
    r(d,(door+10,128,door+11,129),'cream')
    # Striped canopy.
    for a in range(0,w-6,8):
        r(d,(x+3+a,115,min(x+10+a,x+w-4),118),'rose' if (a//8)%2==0 else 'orange')
    r(d,(x,138,x+w-1,140),'deep')

def streets(f):
    im=canvas(); d=ImageDraw.Draw(im); off=round(f*320/COUNT)
    for base in (-320,0,320,640):
        x=base-off
        shop(d,x,59,103,81,0); shop(d,x+108,49,94,91,1); shop(d,x+207,65,109,75,2)
        # Vertical neon signage, side alley, overhead wires.
        r(d,(x+96,84,x+106,109),'ink'); r(d,(x+98,86,x+104,107),'teal')
        for yy in (88,94,100):
            r(d,(x+100,yy,x+102,yy+3),'cyan')
        line(d,[(x,44),(x+70,55),(x+167,47),(x+320,57)],'deep')
        # Potted plant and bicycle silhouette.
        r(d,(x+17,133,x+25,140),'brick')
        for leaf in [(21,126),(17,128),(25,128),(19,131),(23,132)]:
            d.ellipse((leaf[0]+x-2,leaf[1]-2,leaf[0]+x+2,leaf[1]+2),fill=C['leaf'])
        for cx in (x+223,x+238): d.ellipse((cx-5,134,cx+5,144),outline=C['edge'])
        line(d,[(x+223,139),(x+229,132),(x+238,139),(x+227,139),(x+233,128)],'orange')
        line(d,[(x+231,128),(x+237,128)],'edge')
    return im

def pavement(f):
    im=canvas(); d=ImageDraw.Draw(im)
    r(d,(0,141,319,165),'pave'); r(d,(0,141,319,142),'pavelight')
    off=round(f*320/COUNT)
    for yy in (145,151,159):
        line(d,[(0,yy),(319,yy)],'purple')
        for xx in range(-32,353,32):
            x=(xx-off)%352-32
            line(d,[(x+(16 if yy==151 else 0),yy),(x+(16 if yy==151 else 0),yy+5)],'pavelight')
    r(d,(0,164,319,166),'edge'); r(d,(0,167,319,170),'deep'); r(d,(0,171,319,179),'ink')
    for xx in range(-320,641,80):
        x=xx-off
        r(d,(x,177,x+34,178),'pavelight')
    # Wet pavement reflections, hard-edged and understated.
    for base in (-320,0,320,640):
        x=base-off
        for q in range(3):
            r(d,(x+30-q*5,148+q*4,x+66+q*5,148+q*4),'#916572')
            r(d,(x+139-q*3,147+q*5,x+171+q*3,147+q*5),'#537c8a')
    return im

def character(phase):
    """32x48 right-facing walker, contact/passing/high-contact/passing poses."""
    im=Image.new('RGBA',(32,48)); d=ImageDraw.Draw(im)
    a=phase*2*pi; bob=int(round(-abs(sin(a))*1.4)); hip=(15,32+bob)
    # Back arm and back leg are darker to keep the silhouette readable.
    leg=int(round(sin(a)*7)); lift=max(0,int(round(-cos(a)*4)))
    line(d,[(15,31+bob),(14-leg//2,37),(14-leg,43-lift)],'ink',5)
    line(d,[(15,32+bob),(14-leg//2,37),(14-leg,43-lift)],'blue',3)
    r(d,(12-leg,43-lift,18-leg,45-lift),'ink'); r(d,(13-leg,44-lift,18-leg,44-lift),'edge')
    arm=int(round(sin(a)*4))
    line(d,[(16,23+bob),(19+arm,29+bob),(20+arm,32+bob)],'ink',4)
    line(d,[(16,23+bob),(19+arm,29+bob),(20+arm,32+bob)],'orange',2)
    # Backpack and coat.
    r(d,(7,21+bob,12,32+bob),'ink'); r(d,(8,23+bob,11,30+bob),'teal')
    r(d,(11,20+bob,20,32+bob),'ink'); r(d,(12,21+bob,19,31+bob),'coat')
    r(d,(16,22+bob,19,29+bob),'coatlight'); r(d,(12,30+bob,19,31+bob),'orange')
    # Neck, face profile, dark hair tuft and single bright eye.
    r(d,(15,17+bob,18,21+bob),'skinshade')
    r(d,(12,8+bob,21,18+bob),'ink'); r(d,(15,10+bob,21,17+bob),'skin')
    r(d,(21,13+bob,23,15+bob),'skin'); r(d,(20,12+bob,20,13+bob),'ink')
    r(d,(12,8+bob,21,11+bob),'hair'); r(d,(11,10+bob,15,16+bob),'hair')
    r(d,(13,7+bob,19,8+bob),'hair'); r(d,(13,9+bob,17,9+bob),'blue')
    r(d,(15,15+bob,16,16+bob),'skinshade')
    # Front leg, bent knee, foot lifted only in the swing portion.
    lift2=max(0,int(round(cos(a)*4)))
    line(d,[hip,(16+leg//2,37),(16+leg,43-lift2)],'ink',5)
    line(d,[hip,(16+leg//2,37),(16+leg,43-lift2)],'pants',3)
    r(d,(15+leg,43-lift2,21+leg,45-lift2),'ink'); r(d,(16+leg,44-lift2,21+leg,44-lift2),'cream')
    # Forearm swings opposite the forward leg.
    line(d,[(13,23+bob),(12-arm,28+bob),(13-arm,32+bob)],'ink',4)
    line(d,[(13,23+bob),(12-arm,28+bob),(13-arm,31+bob)],'coatlight',2)
    r(d,(12-arm,31+bob,14-arm,33+bob),'skin')
    line(d,[(12,22+bob),(13,28+bob)],'darkteal')
    return im

def actors(f):
    shadow=canvas(); d=ImageDraw.Draw(shadow); d.ellipse((148,160,174,164),fill=C['deep'])
    actor=canvas(); actor.alpha_composite(character((f%12)/12),(144,118))
    return shadow,actor

def atmosphere(f):
    im=canvas(); d=ImageDraw.Draw(im); off=round(f*320/COUNT)
    # Streetlamp in the world plane, with pale yellow integer pixels.
    for base in (-320,0,320,640):
        x=base+279-off
        r(d,(x,102,x+2,160),'ink'); r(d,(x-3,160,x+5,162),'deep')
        line(d,[(x+1,103),(x+1,95),(x+9,95)],'ink',2)
        r(d,(x+5,96,x+12,98),'gold'); r(d,(x+6,97,x+11,98),'cream')
        r(d,(x+6,99,x+11,99),'rose')
        # Two repeating neon beats, with a brief deliberate electrical flicker.
        neon='cyan' if f%30 not in (19,21) else 'teal'
        r(d,(base+115-off,116,base+193-off,116),neon)
    # Steam puffs from cafe vents: continuous phases across the loop.
    for n in range(3):
        t=(f/COUNT+n/3)%1
        x=round(45-off+sin(t*2*pi)*3)%320; y=round(108-t*16)
        for dx,dy in [(0,0),(2,-2),(4,-1),(3,-3)]:
            r(d,(x+dx,y+dy,x+dx+1,y+dy+1),'edge' if t>.65 else 'rose')
    # A pair of distant birds arcs through the peach sky.
    bx=round((f*160/COUNT+72)%160)
    for x,y in [(bx,39),(bx+13,35)]:
        flap=1 if f%6<3 else -1
        line(d,[(x-2,y+flap),(x,y),(x+2,y+flap)],'purple')
    return im

LAYERS=['01 Sky','02 Distant skyline','03 Storefronts','04 Pavement','05 Contact shadow','06 Walker','07 Atmosphere']

def render_artwork(output:Path, style:str='sunset', palette=None):
    global SKY_BANDS,THEME
    THEME=style
    if style=='night': SKY_BANDS=['#131426','#19182e','#201c36','#292443','#332a49','#41324f','#53405b','#67516a']
    elif style=='day': SKY_BANDS=['#93c8d2','#9bcdd5','#a5d3d6','#add8d6','#b6ddd5','#c6e4d8','#d1e9d9','#e3ebdd']
    else: SKY_BANDS=['#38334f','#473653','#5c405c','#784b65','#a56377','#c77a85','#e29692','#ecae9c']
    output=Path(output); frames_dir=output/'frames'; layers_dir=output/'layers'
    frames_dir.mkdir(parents=True,exist_ok=True); layers_dir.mkdir(parents=True,exist_ok=True)
    originals=dict(C)
    # Optional designer palette substitutions are applied to named materials only.
    if palette:
        aliases={'outline':'ink','building_shadow':'purple','building':'wall','building_light':'edge',
                 'street':'pave','street_light':'pavelight','neon_cyan':'cyan','neon_pink':'rose',
                 'warm_light':'gold','jacket':'coat','jacket_light':'coatlight','white':'cream',
                 'far_building':'far'}
        for source,target in aliases.items():
            if source in palette: C[target]=palette[source]
        for key,value in palette.items():
            if key in C and isinstance(value,str) and value.startswith('#'): C[key]=value
        # Preserve the hand-designed sunset ramp; use designer endpoints in other themes.
        if 'sky' in palette and 'sky_light' in palette and (style!='sunset' or palette['sky']!='#38334f' or palette['sky_light']!='#ecae9c'):
            start=tuple(int(palette['sky'][i:i+2],16) for i in (1,3,5))
            end=tuple(int(palette['sky_light'][i:i+2],16) for i in (1,3,5))
            SKY_BANDS=['#'+''.join(f'{round(a+(b-a)*n/7):02x}' for a,b in zip(start,end)) for n in range(8)]
    frames=[]
    for f in range(COUNT):
        shadow,actor=actors(f)
        images=[sky(f),skyline(f),streets(f),pavement(f),shadow,actor,atmosphere(f)]
        composite=canvas()
        for n,layer in enumerate(images):
            layer.save(layers_dir/f'layer_{n:02}_{f:03}.png'); composite.alpha_composite(layer)
        rgb=composite.convert('RGB'); rgb.save(frames_dir/f'frame_{f:03}.png'); frames.append(rgb)
    strip=Image.new('RGBA',(32*8,48))
    for f in range(8): strip.alpha_composite(character(f/8),(f*32,0))
    strip.save(output/'walk_character.png')
    (output/'walk_character.json').write_text(json.dumps({'frame_width':32,'frame_height':48,'frames':8,'fps':8,'animations':{'walk':{'from':0,'to':7,'loop':True}}},indent=2),encoding='utf8')
    C.clear(); C.update(originals)
    return frames,LAYERS
