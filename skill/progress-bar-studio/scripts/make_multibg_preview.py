#!/usr/bin/env python3
"""Portable six-background review. A review image is not automatic visual approval."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageColor
from asset_validation import read_image, image_bytes, publish_new_files


def make_preview(image, brand='#247A63', tile_size=384):
    color=ImageColor.getrgb(brand)
    if len(color)!=3:raise ValueError('Brand color must be opaque RGB')
    image=image.copy(); image.thumbnail((tile_size,tile_size))
    w,h=image.size; pad=12; label=28
    output=Image.new('RGB',(2*(w+2*pad),3*(h+label+2*pad)),'#ededed')
    for i,(name,bg) in enumerate(zip(('WHITE','BLACK','RED','BLUE','BRAND','CHECKER'),('white','black','red','blue',color,None))):
        back=Image.new('RGBA',(w,h),bg or 'white')
        if bg is None:
            draw=ImageDraw.Draw(back)
            for y in range(0,h,16):
                for x in range(0,w,16):
                    if (x//16+y//16)%2:draw.rectangle((x,y,x+15,y+15),fill='#c8c8c8')
        back.alpha_composite(image)
        x=(i%2)*(w+2*pad)+pad; y=(i//2)*(h+label+2*pad)+pad
        ImageDraw.Draw(output).text((x,y),name,fill='black')
        output.paste(back.convert('RGB'),(x,y+label))
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('brand',nargs='?',default='#247A63')
    args=parser.parse_args()
    try:
        image=read_image(args.input,transparent=True,image_format='PNG')
        preview=make_preview(image,args.brand)
        publish_new_files(args.output.parent,{args.output.name:image_bytes(preview)})
        print(args.output)
        return 0
    except (ValueError,OSError) as exc:
        parser.exit(2,str(exc)+'\n')


if __name__=='__main__':raise SystemExit(main())
