"""Compact, reference-led video overlays. No screenshot, logo, or third-party IP copying."""
from PIL import Image, ImageDraw, ImageColor, ImageChops
import math

REFERENCE_STYLES={"R1":"浮标气泡","R2":"贯穿章节带","R3":"短横线分段","R4":"细线节点",
                  "R5":"箭头阶梯","R6":"渐变分段","R7":"点阵进度"}

def setup_reference(r):
    tracks={"R1":48,"R2":18,"R3":42,"R4":24,"R5":18,"R6":18,"R7":42}
    below={"R1":64,"R2":60,"R3":50 if r.frames else 24,"R4":50,"R5":68,"R6":54,"R7":60}
    r.trackY=max(r.trackY,68) if r.frames else tracks[r.style]
    r.h=round((r.trackY+below[r.style])*r.scale)
    if r.style=="R7" and r.refined:
        r.trackY=max(r.trackY,68) if r.frames else 20
        r.h=round((r.trackY+53)*r.scale)
        return
    if r.style in ("R1","R7"):
        # Keep EVERY chapter visible. Select columns once, never reflow at transitions.
        measure=ImageDraw.Draw(Image.new("RGBA",(1,1)))
        widths=[]
        for ch in r.chapters:
            b=measure.textbbox((0,0),ch["label"],font=r.font(r.main,True))
            widths.append((b[2]-b[0])/r.scale)
        available=r.dw-36;gap=10
        r.chapter_columns=next((c for c in range(min(3,len(r.chapters)),0,-1)
             if max(widths)<=(available-gap*(c-1))/c-20),0)
        if not r.chapter_columns:raise ValueError("章名在整行仍放不下，请提供准确简称，不能隐藏历史章节")
        r.chapter_rows=math.ceil(len(r.chapters)/r.chapter_columns)
        r.chapter_top=r.trackY+(48 if r.frames and r.style=="R1" else 15)
        r.h=round((r.chapter_top+r.chapter_rows*(48 if r.style=="R7" else 57)+8)*r.scale)

def chapter_states(r,t):
    current=r.state(t)[0]
    return ["done" if t>=r.duration or j<current else "current" if j==current else "upcoming"
            for j in range(len(r.chapters))]

def draw_chapter_history(r,d,t):
    states=chapter_states(r,t);gap=10;left=18
    cell=(r.dw-36-gap*(r.chapter_columns-1))/r.chapter_columns
    for j,(ch,state) in enumerate(zip(r.chapters,states)):
        row,col=divmod(j,r.chapter_columns);a=left+col*(cell+gap);cx=a+cell/2;top=r.chapter_top+row*(48 if r.style=="R7" else 57)
        if r.style=="R7":
            # A quiet index row and one clear title row; retain all chapter history.
            ink=r.p["onSelected"] if state=="current" else r.p["text"] if state=="done" else r.p["quiet"]
            marker=f"{j+1:02d}" + (" · 已讲" if state=="done" else " · 当前" if state=="current" else "")
            r.text(d,marker,cx,top+5,r.small,False,r.p["text"] if state=="current" else r.p["quiet"],cell-12)
            if state=="current":r.rect(d,(a+3,top+16,a+cell-3,top+43),r.p["selected"],13)
            r.text(d,ch["label"],cx,top+29,r.main,True,ink,cell-24)
            continue
        # Only the current label has a filled background; finished titles remain legible.
        color=r.p["text"] if state=="done" else r.p["quiet"]
        status={"done":"已讲过","current":"正在讲","upcoming":"未讲到"}[state]
        r.text(d,status,cx,top+9,r.small,False,r.p["selected"] if state=="current" else r.p["quiet"],cell-12)
        if state=="current":
            r.rect(d,(a,top+22,a+cell,top+52),r.p["selected"],8)
            color=r.p["onSelected"]
        r.text(d,ch["label"],cx,top+37,r.main,True,color,cell-20)

def poly(r,d,points,fill):
    d.polygon([(round(x*r.scale),round(y*r.scale)) for x,y in points],fill=fill)

def gradient(r,im,box,c1,c2,radius=0):
    x0,y0,x1,y1=[round(v*r.scale) for v in box]
    if x1<=x0:return
    w,h=x1-x0,max(1,y1-y0);a=ImageColor.getrgb(c1);b=ImageColor.getrgb(c2)
    strip=Image.new("RGBA",(w,1));strip.putdata([tuple(round(a[k]+(b[k]-a[k])*i/max(1,w-1)) for k in range(3))+(255,) for i in range(w)])
    strip=strip.resize((w,h));mask=Image.new("L",(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=round(radius*r.scale),fill=255)
    im.paste(strip,(x0,y0),mask)

def draw_reference(r,im,d,t,i,p,local,x):
    y=r.trackY;left,right=r.x0,r.x1;n=len(r.chapters);width=right-left
    active=r.p["selected"];pale=r.p["inactive"];text=r.p["text"]
    percent=f"{round(p*100)}%" if r.progress_mode=="time-linear" else f"{i+1:02d} / {n:02d}"
    def dot(px,py,size=4,fill=active):r.rect(d,(px-size,py-size,px+size,py+size),fill,size)
    def title(ch,cx,cy,maxw,color=text):r.text(d,ch["label"],cx,cy,r.main,True,color,maxw)
    def bubble(py):
        # Clamp the tag, not the progress point; connector still ends at true x.
        bw=64;cx=max(left+bw/2,min(right-bw/2,x))
        r.rect(d,(cx-bw/2,py-12,cx+bw/2,py+12),active,12)
        r.text(d,percent,cx,py,14,True,r.p["onSelected"],bw-12)
        if py<y:poly(r,d,[(cx-4,py+10),(cx+4,py+10),(x,y-9)],active)
    def labels(cy,gap=10):
        cell=width/n
        for j,ch in enumerate(r.chapters):
            ink=(text if j<=i else r.p["quiet"]) if r.refined else (active if j==i else r.p["quiet"])
            title(ch,left+(j+.5)*cell,cy,cell-gap,ink)
    if r.style=="R1":
        r.line(d,left,right,y,pale,8);gradient(r,im,(left,y-4,x,y+4),r.p["active"],active,4)
        if not r.frames:
            dot(x,y,7);r.rect(d,(x-7,y-7,x+7,y+7),active,7,r.p["surface"],2);bubble(y-28)
        else:
            bubble(y+24)
        draw_chapter_history(r,d,t)
    elif r.style=="R2":
        # Text is inverted exactly where the progressive fill passes behind it.
        top,bot=y,y+40;r.rect(d,(left,top,right,bot),r.p["pill"],20)
        mask=Image.new("L",im.size);md=ImageDraw.Draw(mask)
        r.rect(md,(left,top,right,bot),255,20)
        clip=Image.new("L",im.size);ImageDraw.Draw(clip).rectangle((0,0,round(x*r.scale),r.h),fill=255)
        fillmask=ImageChops.multiply(mask,clip);im.paste(active,(0,0,im.width,im.height),fillmask)
        overlay=Image.new("RGBA",im.size);od=ImageDraw.Draw(overlay);cell=width/n
        for j,ch in enumerate(r.chapters):
            cx=left+(j+.5)*cell;title(ch,cx,y+20,cell-24)
            r.text(od,ch["label"],cx,y+20,r.main,True,r.p["onSelected"],cell-24)
            if j:
                sx=left+j*cell
                d.line([(round(sx*r.scale),round((y+11)*r.scale)),(round(sx*r.scale),round((y+29)*r.scale))],fill=r.p["outline"],width=max(1,round(r.scale)))
        overlay.putalpha(ImageChops.multiply(overlay.getchannel("A"),fillmask));im.alpha_composite(overlay)
    elif r.style=="R3":
        cell=width/n;gap=10
        for j in range(n):
            a=left+j*cell+gap/2;b=left+(j+1)*cell-gap/2
            r.line(d,a,b,y,pale,5);r.line(d,a,max(a,min(x,b)),y,active,5)
        labels(y+27 if r.frames else y-23)
    elif r.style=="R4":
        r.line(d,left,right,y,pale,2);r.line(d,left,x,y,active,2)
        for j in range(n):
            nodep=r.starts[j]/r.duration if r.progress_mode=="time-linear" else j/n
            px=left+nodep*width;dot(px,y,3,active if px<=x else r.p["surface"])
            r.rect(d,(px-3,y-3,px+3,y+3),None,3,r.p["outline"])
        labels(y+27)
        if not r.frames:dot(x,y,5)
    elif r.style=="R5":
        cell=width/n;h=22
        for j in range(n):
            a=left+j*cell;b=left+(j+1)*cell-3
            points=[(a,y),(b-9,y),(b,y+h/2),(b-9,y+h),(a,y+h),(a+9,y+h/2)]
            mask=Image.new("L",im.size);poly(r,ImageDraw.Draw(mask),points,255)
            im.paste(pale,(0,0,r.w,r.h),mask)
            clip=Image.new("L",im.size);ImageDraw.Draw(clip).rectangle((0,0,round(x*r.scale),r.h),fill=255)
            im.paste(active,(0,0,r.w,r.h),ImageChops.multiply(mask,clip))
        labels(y+44)
    elif r.style=="R6":
        cell=width/n;gap=5
        for j in range(n):
            a=left+j*cell;b=left+(j+1)*cell-gap
            r.rect(d,(a,y,b,y+12),pale,4)
            gradient(r,im,(a,y,max(a,min(x,b)),y+12),r.p["active"],active,4)
        labels(y+35)
    elif r.style=="R7":
        if r.refined:
            # One restrained dot track and one title row. No badges, index row or ring.
            for j in range(21):
                px=left+j/20*width;dot(px,y,1.6,active if px<=x else pale)
            if not r.frames:dot(x,y,3,text)
            cell=width/n
            for j,ch in enumerate(r.chapters):
                cx=left+(j+.5)*cell
                title(ch,cx,y+27,cell-14,text if j<=i else r.p["quiet"])
                if j==i and t<r.duration:r.line(d,cx-8,cx+8,y+43,text,2)
            return
        dots=41
        for j in range(dots):
            px=left+j/(dots-1)*width;dot(px,y,2.3,active if px<=x else pale)
        if not r.frames:
            r.rect(d,(x-6,y-6,x+6,y+6),r.p["surface"],6,active,2)
            dot(x,y,2.4,active)
        draw_chapter_history(r,d,t)
    # Character sits at the track top for thick bands, or the line centre for thin tracks.
    if r.frames:return
    if r.style in ("R3","R5","R6"):dot(x,y,2.5)
