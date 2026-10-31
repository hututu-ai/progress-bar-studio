#!/usr/bin/env python3
"""Actual infinite GIF review at 6/8 fps; never invent in-between poses or grant gait approval."""
import argparse
import io
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops
from asset_validation import cycle_files,read_image,publish_new_files,image_bytes,default_contact


def gif_durations(fps):
    if fps not in (6,8):raise ValueError('Compare the supported 6 or 8 fps; do not accelerate to hide bad poses')
    # GIF stores centiseconds. Cumulative rounding avoids four 125ms frames becoming 480ms.
    return [10*(round((i+1)*100/fps)-round(i*100/fps)) for i in range(4)]


def tiles(images,fps,order=(1,2,3,4)):
    factor=min(1,280/images[0].height);w=max(320,round(images[0].width*factor)+64);h=round(images[0].height*factor)+84
    x=(w-round(images[0].width*factor))//2;y=42
    contacts=[default_contact(im) for im in images]
    if max(p[1] for p in contacts)-min(p[1] for p in contacts)>2:
        raise ValueError('Ground is not aligned; review/regrid complete subjects first, not per-frame scaling')
    ground=y+round(contacts[0][1]*factor)
    try:font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',15)
    except OSError:font=ImageFont.load_default()
    result=[]
    for im in images:
        tile=Image.new('RGBA',(w,h),'white');d=ImageDraw.Draw(tile)
        sequence='-'.join(str(index) for index in (*order,order[0]))
        d.text((16,12),f'DRAFT  |  {fps} fps  |  {sequence}',font=font,fill='#26352A')
        d.line((16,ground,w-16,ground),fill='#9CC365',width=2)
        scaled=im.resize((round(im.width*factor),round(im.height*factor)),Image.Resampling.LANCZOS)
        tile.alpha_composite(scaled,(x,y));result.append(tile.convert('RGB'))
    return result


def build(cycle):
    cycle=Path(cycle);manifest,_=cycle_files(cycle.parent,cycle.name)
    images=[read_image(cycle.parent/name,transparent=True,image_format='PNG') for name in manifest['frames']]
    order=manifest['playbackOrder']
    images=[images[i-1] for i in order]
    files={};rows=[]
    for fps in (6,8):
        frames=tiles(images,fps,order);stack=Image.new('RGB',(frames[0].width*4,frames[0].height))
        for i,im in enumerate(frames):stack.paste(im,(i*im.width,0))
        palette=stack.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
        quantized=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
        durations=gif_durations(fps)
        payload=image_bytes(quantized[0],'GIF',save_all=True,append_images=quantized[1:],loop=0,
                            duration=durations,disposal=2,optimize=False)
        with Image.open(io.BytesIO(payload)) as decoded:
            if decoded.n_frames!=4 or decoded.info.get('loop')!=0:raise ValueError('Actual GIF did not retain four looping frames')
            actual=[]
            for i in range(4):decoded.seek(i);decoded.load();actual.append(decoded.info['duration'])
        if actual!=durations:raise ValueError('GIF timing readback changed')
        name=f'walk-{fps}fps.gif';files[name]=payload
        rows.append({'file':name,'targetFps':fps,'frameDurationsMs':actual,'cycleMs':sum(actual),
                     'decodedFrames':4,'loop':0,'size':list(frames[0].size)})
    transition=[]
    for i in range(4):
        a=Image.alpha_composite(Image.new('RGBA',images[i].size),images[i])
        b=Image.alpha_composite(Image.new('RGBA',images[i].size),images[(i+1)%4])
        # RGBA.getbbox() normally looks only at Alpha. Union the channels so
        # equal silhouettes with changed visible limbs/colors are not called unchanged.
        boxes=[channel.getbbox() for channel in ImageChops.difference(a,b).split()]
        boxes=[box for box in boxes if box]
        box=([min(b[0] for b in boxes),min(b[1] for b in boxes),
              max(b[2] for b in boxes),max(b[3] for b in boxes)] if boxes else None)
        transition.append({'from':order[i],'to':order[(i+1)%4],'changeBox':box})
    wrap=f'{order[-1]}->{order[0]}'
    report={'schemaVersion':1,'purpose':'unapproved-continuous-gait-review','order':order,
            'wrapTransition':wrap,'variants':rows,'transitionDiagnostics':transition,
            'gaitReview':'pending','userApproved':False,'interpolatedFrames':0,
            'note':f'GIF review is opaque on white to avoid palette-alpha halos; transparent source PNGs remain unchanged. Watch at least 6 cycles including {wrap}. Change boxes describe pixels, not gait quality.'}
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>四帧连续步态待审</title>
<style>body{font-family:system-ui;background:#f5f5ef;color:#20251b;margin:30px}main{max-width:900px;margin:auto}section{display:flex;gap:24px;flex-wrap:wrap}figure{margin:0;padding:18px;background:white;border:1px solid #ddd;border-radius:14px}img{max-width:100%;height:auto}h1{font-size:24px}p{line-height:1.7}</style>
<main><h1>四帧连续步态 · 待审</h1><p>实际原帧顺序：__ORDER__。至少连续看六个周期，特别检查最后一帧回第一帧的接缝。观察是否踢腿、单脚跳、头身抖动、节奏突兀。加速不能代替修复错误关键姿势。</p>
<section><figure><figcaption>正常：约6fps</figcaption><img src="walk-6fps.gif" alt="6fps实际GIF无限循环"></figure><figure><figcaption>稍快：8fps</figcaption><img src="walk-8fps.gif" alt="8fps实际GIF无限循环"></figure></section>
<p>本页不表示动作已通过，不生成新姿势或中间帧，不批准成品或写入角色库。两版都怪就继续保留未通过。</p></main></html>'''
    html=html.replace('__ORDER__',' → '.join(str(index) for index in (*order,order[0])))
    files['review.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
    files['index.html']=html.encode();return files,report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cycle',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True)
    a=p.parse_args()
    try:
        files,report=build(a.cycle);publish_new_files(a.out_dir,files)
        print(json.dumps(report,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError) as exc:p.exit(2,str(exc)+'\n')


if __name__=='__main__':raise SystemExit(main())
