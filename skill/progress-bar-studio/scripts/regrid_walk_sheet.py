#!/usr/bin/env python3
"""Recover four complete disjoint subjects; never repair poses, flip limbs or approve gait."""
import argparse
from collections import deque
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw
from asset_validation import (require_transparency,validate_frames,visible_bounds,default_contact,
                              publish_new_files,image_bytes,sha256,interior_alpha_stats)
from make_multibg_preview import make_preview


def components(alpha):
    """8-connected scanline components, using only stdlib/Pillow."""
    w,h=alpha.size;pixels=alpha.tobytes();parents=[];runs=[];previous=[]
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for y in range(h):
        current=[];x=0;offset=y*w;j=0
        while x<w:
            if pixels[offset+x]<=32:x+=1;continue
            start=x
            while x<w and pixels[offset+x]>32:x+=1
            label=len(parents);parents.append(label);run=(start,x,y,label)
            current.append(run);runs.append(run)
            while j<len(previous) and previous[j][1]<start:j+=1
            k=j
            while k<len(previous) and previous[k][0]<=x:
                a,b=root(label),root(previous[k][3])
                if a!=b:parents[a]=b
                k+=1
        previous=current
    grouped={}
    for x0,x1,y,label in runs:
        key=root(label)
        c=grouped.setdefault(key,{'area':0,'box':[w,h,0,0],'runs':[]})
        c['area']+=x1-x0;c['runs'].append((x0,x1,y))
        box=c['box'];box[0]=min(box[0],x0);box[1]=min(box[1],y);box[2]=max(box[2],x1);box[3]=max(box[3],y+1)
    return sorted(grouped.values(),key=lambda c:c['area'],reverse=True)


def gap(a,b):
    return math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))


def regrid(source, padding=24, arrangement='horizontal'):
    if source.width*source.height>16_777_216:raise ValueError('Source exceeds safe pixel budget')
    if not 8<=padding<=256:raise ValueError('padding must be 8–256 source pixels')
    rgba=require_transparency(source,'Source sheet');alpha=rgba.getchannel('A');w,h=rgba.size
    cc=components(alpha)
    if not cc:raise ValueError('Empty source')
    threshold=max(24,cc[0]['area']*.15)
    major=[c for c in cc if c['area']>=threshold]
    if len(major)!=4:raise ValueError(f'Expected four separate complete subjects, found {len(major)}; touching/merged bodies need reviewed masks, never forced splitting')
    heights=[c['box'][3]-c['box'][1] for c in major]
    if max(heights)>min(heights)*1.3 or major[0]['area']>min(c['area'] for c in major)*2:
        raise ValueError('Subjects differ too much in scale/completeness; inspect before regridding')
    if arrangement=='horizontal':
        major.sort(key=lambda c:(c['box'][0]+c['box'][2])/2)
        centers=[(c['box'][1]+c['box'][3])/2 for c in major]
        if max(centers)-min(centers)>max(heights)*.35:raise ValueError('Not a single row; specify 2x2 or review order')
    elif arrangement=='2x2':
        major.sort(key=lambda c:(c['box'][1]+c['box'][3])/2)
        if major[2]['box'][1]<=min(c['box'][3] for c in major[:2]):raise ValueError('Ambiguous row order; review subject regions')
        major=sorted(major[:2],key=lambda c:c['box'][0])+sorted(major[2:],key=lambda c:c['box'][0])
    else:raise ValueError('Arrangement must be horizontal or 2x2')
    owners=bytearray(w*h);core_ids={id(c):i+1 for i,c in enumerate(major)}
    assignments=[]
    for c in cc:
        owner=core_ids.get(id(c))
        if owner is None:
            distances=sorted((gap(c['box'],body['box']),i+1) for i,body in enumerate(major))
            distance,owner=distances[0]
            if distance>max(heights)*.08 or abs(distance-distances[1][0])<1:
                raise ValueError('Detached visible fragment cannot be assigned safely; review hair/accessories/text rather than dropping it')
        assignments.append((c,owner))
        for x0,x1,y in c['runs']:owners[y*w+x0:y*w+x1]=bytes([owner])*(x1-x0)
    # Retain nearby antialiasing, without a global Alpha cutoff or recoloring.
    raw_alpha=alpha.tobytes();pending=deque()
    for index,owner in enumerate(owners):
        if not owner:continue
        x=index%w;y=index//w
        if any(0<=nx<w and 0<=ny<h and raw_alpha[ny*w+nx] and not owners[ny*w+nx]
               for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))):pending.append(index)
    for _ in range(4):
        new=deque()
        while pending:
            at=pending.popleft();x=at%w;y=at//w;owner=owners[at]
            for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=nx<w and 0<=ny<h:
                    pos=ny*w+nx
                    if raw_alpha[pos] and not owners[pos]:owners[pos]=owner;new.append(pos)
        pending=new
    omitted=[a for a,owner in zip(raw_alpha,owners) if a and not owner]
    if omitted and (max(omitted)>32 or sum(omitted)/sum(raw_alpha)>.002):
        raise ValueError('Substantial unassigned edge/fragment; use reviewed masks, do not clip artwork')
    figures=[];boxes=[];pivots=[];feet=[]
    for owner,body in enumerate(major,1):
        mask=Image.frombytes('L',(w,h),bytes(a if tag==owner else 0 for a,tag in zip(raw_alpha,owners)))
        im=rgba.copy();im.putalpha(mask);box=mask.getbbox();hard=visible_bounds(im)
        if min(hard[0],hard[1],w-hard[2],h-hard[3])<2:
            raise ValueError('Subject touches the original canvas edge; lost pixels cannot be recovered by regridding')
        # Upper-body Alpha mass is a candidate pivot, not an anatomy/identity approval.
        top=body['box'][1];bottom=top+max(1,round((body['box'][3]-top)*.45))
        mass=total=0
        for y in range(top,bottom):
            for x in range(body['box'][0],body['box'][2]):
                a=raw_alpha[y*w+x] if owners[y*w+x]==owner else 0
                if a>32:mass+=x*a;total+=a
        pivot=round(mass/total);foot=default_contact(im)
        figures.append(im);boxes.append(box);pivots.append(pivot);feet.append(foot)
    left=max(p-b[0] for p,b in zip(pivots,boxes));right=max(b[2]-p for p,b in zip(pivots,boxes))
    above=max(f[1]-b[1] for f,b in zip(feet,boxes));below=max(b[3]-f[1] for f,b in zip(feet,boxes))
    cw=left+right+2*padding;ch=above+below+2*padding;px=left+padding;ground=above+padding
    if cw*ch*4>16_777_216:raise ValueError('Regridded sheet exceeds safe pixel budget')
    frames=[];transforms=[]
    for im,box,pivot,foot in zip(figures,boxes,pivots,feet):
        frame=Image.new('RGBA',(cw,ch));dx=px-pivot;dy=ground-foot[1]
        # Paste exact RGBA, without an Alpha mask (which would multiply Alpha twice).
        frame.paste(im.crop(box),(box[0]+dx,box[1]+dy));frames.append(frame)
        transforms.append({'sourceBox':list(box),'translation':[dx,dy],'scale':1,'sourceBodyPivotX':pivot,'sourceContact':list(foot)})
    validate_frames(frames)
    sheet=Image.new('RGBA',(cw*4,ch))
    for i,frame in enumerate(frames):sheet.paste(frame,(i*cw,0))
    report={'schemaVersion':1,'layout':'regridded-horizontal','sourceArrangement':arrangement,
        'frameSize':{'width':cw,'height':ch},'contacts':[[f[0]+t['translation'][0],ground] for f,t in zip(feet,transforms)],
        'bodyPivotX':px,'sourceTransforms':transforms,'substantialAlphaPixelsPreserved':True,
        'faintPixelsOmitted':len(omitted),'faintAlphaMassOmitted':sum(omitted),'independentScale':False,
        'technicalValidation':'passed','identityReview':'pending','gaitReview':'pending','userApproved':False,
        'interiorAlpha':[interior_alpha_stats(im) for im in frames],
        'warnings':['Regridding fixes framing only, not gait. Inspect upper-body pivots, original completeness, small details and four near/far phases.']}
    if omitted:report['warnings'].append('Some unassigned Alpha<=32 pixels were omitted only in this derivative; inspect fine hair/shadows, do not assume every faint pixel was noise. Original is unchanged.')
    return sheet,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--arrangement',choices=('horizontal','2x2'),default='horizontal');p.add_argument('--padding',type=int,default=24)
    p.add_argument('--brand',default='#247A63');a=p.parse_args()
    try:
        with Image.open(a.input) as im:im.load();sheet,report=regrid(im,a.padding,a.arrangement)
        report['sourceSha256']=sha256(a.input)
        files={'prepared-sheet.png':image_bytes(sheet),'preparation.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),
               'multibg-review.png':image_bytes(make_preview(sheet,a.brand,768))}
        publish_new_files(a.out_dir,files);print(json.dumps(report,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError) as exc:p.exit(2,str(exc)+'\n')


if __name__=='__main__':raise SystemExit(main())
