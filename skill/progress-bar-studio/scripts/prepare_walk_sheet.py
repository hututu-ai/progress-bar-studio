#!/usr/bin/env python3
"""Prepare a four-cell sheet without generating, approving or repainting the IP."""
import argparse
from collections import deque
import json
import math
from pathlib import Path
from statistics import median
from PIL import Image
from asset_validation import (visible_bounds, default_contact, validate_frames,
                              image_bytes, publish_new_files, sha256, interior_alpha_stats)
from make_multibg_preview import make_preview


def remove_exterior(image, tolerance=24):
    """Only remove near-uniform, border-connected RGB; never global white-key."""
    rgb=image.convert('RGB'); w,h=rgb.size; pixels=rgb.load()
    border=[(x,0) for x in range(w)]+[(x,h-1) for x in range(w)]
    border += [(0,y) for y in range(1,h-1)]+[(w-1,y) for y in range(1,h-1)]
    sample=[pixels[p] for p in border]
    key=tuple(round(median(c[i] for c in sample)) for i in range(3))
    def near(p):return max(abs(p[i]-key[i]) for i in range(3))<=tolerance
    if sum(near(p) for p in sample)/len(sample)<.98:
        raise ValueError('Exterior is not near-uniform. Use a reviewed segmentation mask; checkerboards/floors are not transparent.')
    mask=bytearray(w*h); pending=deque()
    for x,y in border:
        at=y*w+x
        if not mask[at] and near(pixels[x,y]):mask[at]=1;pending.append((x,y))
    while pending:
        x,y=pending.popleft()
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0<=nx<w and 0<=ny<h:
                at=ny*w+nx
                if not mask[at] and near(pixels[nx,ny]):mask[at]=1;pending.append((nx,ny))
    out=image.convert('RGBA'); alpha=out.getchannel('A')
    alpha.putdata([0 if bg else a for bg,a in zip(mask,alpha.getdata())]);out.putalpha(alpha)
    return out,key


def prepare(source, layout='horizontal', remove_flat=False, tolerance=24, body_pivot_x=None):
    if source.width*source.height>16_777_216:raise ValueError('Sheet exceeds safe pixel budget')
    cols,rows=(4,1) if layout=='horizontal' else (2,2)
    if source.width%cols or source.height%rows:raise ValueError('Sheet needs four equal cells; no guessed cropping')
    # Genuine alpha takes precedence. An RGB image must explicitly request extraction.
    has_alpha='A' in source.getbands() or 'transparency' in source.info
    rgba=source.convert('RGBA'); key=None
    if rgba.getchannel('A').getextrema()[0]!=0:
        if not remove_flat:raise ValueError('Opaque image: request reviewed flat-background extraction or supply genuine Alpha')
        rgba,key=remove_exterior(rgba,tolerance)
    elif not has_alpha:raise ValueError('No genuine Alpha')
    cw,ch=rgba.width//cols,rgba.height//rows
    frames=[rgba.crop(((i%cols)*cw,(i//cols)*ch,(i%cols+1)*cw,(i//cols+1)*ch)) for i in range(4)]
    validate_frames(frames)
    for i,im in enumerate(frames):
        l,t,r,b=visible_bounds(im)
        if min(l,t,cw-r,ch-b)<2:
            raise ValueError(f'Frame {i+1} touches a cell boundary; re-generate/review regions, never clip a tail or foot')
    pivot=cw/2 if body_pivot_x is None else body_pivot_x
    if not math.isfinite(pivot) or not 0<=pivot<cw:raise ValueError('Shared body pivot must be inside a cell')
    # No per-frame trim/scale. Source must already have a consistent head/torso position.
    sheet=Image.new('RGBA',(cw*4,ch))
    for i,im in enumerate(frames):sheet.paste(im,(i*cw,0))
    report={'schemaVersion':1,'layout':layout,'frameSize':{'width':cw,'height':ch},
            'contacts':[list(default_contact(im)) for im in frames], 'bodyPivotX':pivot,
            'sampledBackground':key,'technicalValidation':'passed','identityReview':'pending',
            'gaitReview':'pending','userApproved':False,
            'warnings':['Inspect identity, four gait phases, interior opacity, halos and shared body alignment. No visual approval is inferred.']}
    report['interiorAlpha']=[interior_alpha_stats(im) for im in frames]
    if any((row['fractionBelow240'] or 0)>.1 for row in report['interiorAlpha']):
        report['warnings'].append('Substantial translucent interior: inspect for a damaged white/body area on red and blue before use.')
    return sheet,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--layout',choices=('horizontal','2x2'),required=True)
    p.add_argument('--remove-flat-background',action='store_true')
    p.add_argument('--tolerance',type=int,default=24);p.add_argument('--body-pivot-x',type=float)
    p.add_argument('--brand',default='#247A63')
    a=p.parse_args()
    try:
        if not 1<=a.tolerance<=60:raise ValueError('Tolerance must be 1–60; inspect the actual background first')
        with Image.open(a.input) as image:
            image.load();sheet,report=prepare(image,a.layout,a.remove_flat_background,a.tolerance,a.body_pivot_x)
        report['sourceSha256']=sha256(a.input)
        files={'prepared-sheet.png':image_bytes(sheet),'multibg-review.png':image_bytes(make_preview(sheet,a.brand,768)),
               'preparation.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()}
        publish_new_files(a.out_dir,files)
        print(json.dumps(report,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError) as exc:p.exit(2,str(exc)+'\n')


if __name__=='__main__':raise SystemExit(main())
