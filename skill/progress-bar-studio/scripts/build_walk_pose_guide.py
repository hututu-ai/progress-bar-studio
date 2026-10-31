#!/usr/bin/env python3
"""Deterministic pose-only guide. Not an IP image, animation, or gait approval."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from asset_validation import image_bytes,publish_new_files


def guide(layout='2x2'):
    # Near/far refer to camera depth, avoiding ambiguous anatomical left/right.
    poses=[
        {'phase':'01 CONTACT A','nearLeg':[(.50,.65),(.60,.80),(.75,.94)],'farLeg':[(.50,.65),(.39,.80),(.29,.94)],
         'nearArm':[(.50,.43),(.36,.50),(.28,.61)],'farArm':[(.50,.43),(.63,.49),(.72,.56)]},
        {'phase':'02 PASS A','nearLeg':[(.50,.63),(.48,.79),(.48,.94)],'farLeg':[(.50,.63),(.66,.72),(.53,.83)],
         'nearArm':[(.50,.41),(.47,.53),(.52,.63)],'farArm':[(.50,.41),(.54,.53),(.49,.63)]},
        {'phase':'03 CONTACT B','nearLeg':[(.50,.65),(.39,.80),(.29,.94)],'farLeg':[(.50,.65),(.60,.80),(.75,.94)],
         'nearArm':[(.50,.43),(.63,.49),(.72,.56)],'farArm':[(.50,.43),(.36,.50),(.28,.61)]},
        {'phase':'04 PASS B','nearLeg':[(.50,.63),(.66,.72),(.53,.83)],'farLeg':[(.50,.63),(.48,.79),(.48,.94)],
         'nearArm':[(.50,.41),(.54,.53),(.49,.63)],'farArm':[(.50,.41),(.47,.53),(.52,.63)]}]
    cw,ch=520,580;cols=2 if layout=='2x2' else 4;rows=2 if layout=='2x2' else 1
    out=Image.new('RGB',(cw*cols,ch*rows+76),'white');d=ImageDraw.Draw(out)
    font=None
    for name in ('DejaVuSans.ttf','Arial.ttf','/System/Library/Fonts/Helvetica.ttc','C:/Windows/Fonts/arial.ttf'):
        try:font=ImageFont.truetype(name,20);break
        except OSError:pass
    if font is None:font=ImageFont.load_default()
    d.text((18,12),'POSE ONLY: cyan = near / orange = far. Do not copy colors.',font=font,fill='#17202a')
    d.text((18,40),'Facing right. Frames 3/4 EXCHANGE near and far limbs, not repeat 1/2.',font=font,fill='#17202a')
    for i,p in enumerate(poses):
        ox=(i%cols)*cw;oy=(i//cols)*ch+76
        d.rectangle((ox+6,oy+6,ox+cw-6,oy+ch-6),outline='#d1d5db',width=2)
        d.text((ox+18,oy+16),p['phase'],font=font,fill='#111827')
        def point(v):return (round(ox+v[0]*cw),round(oy+v[1]*ch))
        def limb(key,color,width):
            points=[point(p) for p in p[key]];d.line(points,fill=color,width=width,joint='curve')
            for x,y in points:d.ellipse((x-7,y-7,x+7,y+7),fill=color)
        # Back limbs first; near limbs overlap them, making depth observable.
        limb('farLeg','#E78A24',12);limb('farArm','#E78A24',10)
        shoulder=p['nearArm'][0];hip=p['nearLeg'][0]
        d.line([point(shoulder),point(hip)],fill='#9CA3AF',width=18)
        cx,cy=point((.50,.28 if i%2==0 else .26));radius=68
        d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline='#9CA3AF',width=5)
        d.polygon([(cx+radius-2,cy-4),(cx+radius+16,cy+7),(cx+radius-2,cy+10)],fill='#9CA3AF')
        limb('nearLeg','#147FAD',18);limb('nearArm','#147FAD',14)
        y=point((0,.95))[1];d.line([(ox+42,y),(ox+cw-42,y)],fill='#8BBF5A',width=3)
        for key in ('nearLeg','farLeg'):
            x,y=point(p[key][-1]);d.line([(x-8,y),(x+20,y)],fill='#147FAD' if key=='nearLeg' else '#E78A24',width=8)
    return out,{'schemaVersion':1,'layout':layout,'role':'pose-reference-only','phases':poses,
                'gaitReview':'not-assessed','userApproved':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--layout',choices=('horizontal','2x2'),default='2x2');a=p.parse_args()
    im,report=guide(a.layout)
    try:
        publish_new_files(a.out_dir,{'pose-guide.png':image_bytes(im),'pose-guide.json':(json.dumps(report,indent=2)+'\n').encode()})
        print(a.out_dir/'pose-guide.png');return 0
    except (ValueError,OSError) as exc:p.exit(2,str(exc)+'\n')


if __name__=='__main__':raise SystemExit(main())
