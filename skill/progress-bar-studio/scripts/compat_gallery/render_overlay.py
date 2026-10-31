#!/usr/bin/env python3
"""Eight recommended presets plus legacy layouts; same drawing for PNG/WebP/ProRes."""
import argparse, bisect, hashlib, json, math, shutil, subprocess
from fractions import Fraction
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageColor
from .reference_presets import REFERENCE_STYLES, setup_reference, draw_reference
from asset_validation import read_image, validate_frames, visible_bounds, visible_contact
from font_validation import require_glyphs

STYLES={"S1":"双层胶囊","S2":"分段跑道","S3":"极简下划线","S5":"里程碑圆点",
        "S6":"章节卡片","S7":"书签页签","S8":"当前章节聚焦","S9":"数字计时条"}
STYLES.update(REFERENCE_STYLES)
STYLE_ALIASES={"01":"S1","02":"R1","03":"R2","04":"R3","05":"R4","06":"R5","07":"R6","08":"R7"}
RECOMMENDED={code:STYLES[internal] for code,internal in STYLE_ALIASES.items()}
STYLES.update(RECOMMENDED)
DEFAULT={"surface":"#FFFFFF","active":"#E89AB3","inactive":"#F7DDE5",
         "pill":"#FBE9EE","text":"#4D3A40","quiet":"#806B74","outline":"#F2C2D0",
         "selected":"#AF4268","onSelected":"#FFFFFF"}

def contrast(a,b):
    def lum(color):
        c=[v/255 for v in ImageColor.getrgb(color)[:3]]
        c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
        return .2126*c[0]+.7152*c[1]+.0722*c[2]
    lo,hi=sorted((lum(a),lum(b)))
    return (hi+.05)/(lo+.05)

class Overlay:
    def __init__(self, cfg, chapters, duration, base=Path(".")):
        self.cfg,self.chapters,self.duration=cfg,chapters,float(duration)
        revision=cfg.get("visualRevision","legacy")
        if revision not in ("legacy","refined-20261030","readable-20261030"):raise ValueError("Unknown visualRevision")
        self.refined=revision in ("refined-20261030","readable-20261030")
        self.readable=revision=="readable-20261030"
        requested=str(cfg.get("style","01"))
        if requested.isdigit():requested=requested.zfill(2)
        self.style_id=next((code for code,old in STYLE_ALIASES.items() if old==requested),requested)
        self.style=STYLE_ALIASES.get(requested,requested)
        if self.readable and self.style!='S1':raise ValueError('readable-20261030 is the double-layer capsule revision')
        if self.style not in STYLES: raise ValueError("Unknown preset; S4 is legacy, do not remap")
        self.dw=float(cfg.get("displayWidth",480)); self.w=int(cfg.get("outputWidth",2160))
        if not all(math.isfinite(v) for v in (self.dw,self.w,self.duration)) or self.dw<240 or self.w<240 or self.duration<=0: raise ValueError("Invalid dimensions/duration")
        self.scale=self.w/self.dw; self.p=DEFAULT|cfg.get("palette",{})
        if self.style in ("S1","R1","R2","R7") and contrast(self.p["selected"],self.p["onSelected"])<4.5:
            raise ValueError("选中底色与反白文字对比不足4.5:1，请加深selected或调整onSelected")
        def path(v): return Path(v) if Path(v).is_absolute() else base/str(v)
        # Explicit paths make font choice reproducible on each host.
        self.reg=path(cfg["fontRegular"]); self.bold=path(cfg["fontBold"])
        actual_text=''.join(ch['label']+ch.get('kicker','') for ch in chapters)
        require_glyphs(self.reg,actual_text); require_glyphs(self.bold,actual_text)
        self.main=float(cfg.get("labelSize",18)); self.small=float(cfg.get("kickerSize",11))
        if self.main<16 or self.main<self.small*1.5: raise ValueError("主标题过小或层级不足")
        self.fonts={}
        for size,bold in [(self.small,False),(self.main,True),(12,False),(14,True)]:
            self.fonts[size,bold]=ImageFont.truetype(str(self.bold if bold else self.reg),round(size*self.scale))
        self.char=cfg.get("character",{"mode":"none"}); mode=self.char.get("mode","none")
        if mode not in ("none","single","four-frame"): raise ValueError("Unknown character mode")
        self.frames=[]; self.anchors=[]
        if mode!="none":
            expected=4 if mode=="four-frame" else 1
            paths=self.char.get("frames",[]); anchors=self.char.get("anchors",[])
            if len(paths)!=expected or len(anchors)!=expected: raise ValueError("角色帧和脚点数不匹配")
            dims=set(); signatures=set(); originals=[]; bounds=[]
            for name,anchor in zip(paths,anchors):
                im=read_image(path(name),transparent=True,image_format='PNG')
                if im.mode!='RGBA':raise ValueError('角色需要真实 RGBA PNG')
                dims.add(im.size)
                signatures.add(hashlib.sha256(im.tobytes()).hexdigest())
                if im.getchannel("A").getextrema()!=(0,255): raise ValueError("角色需要真实透明和不透明像素")
                ax,ay=float(anchor["x"]),float(anchor["y"])
                visible_contact(im,(ax,ay))
                if 'bodyPivotX' in self.char:
                    ax=self.char['bodyPivotX']
                    if isinstance(ax,bool) or not isinstance(ax,(float,int)) or not math.isfinite(ax) or not 0<=ax<im.width:raise ValueError('bodyPivotX must be inside the source canvas')
                originals.append((im,ax,ay));bounds.append(visible_bounds(im))
            if mode=='four-frame':validate_frames([im for im,ax,ay in originals])
            if len(dims)!=1: raise ValueError("四帧必须同画布")
            if len(signatures)!=expected: raise ValueError("四帧含重复图片，不能冒充逐帧步态")
            if not 0<float(self.char.get("cycleFps",6))<=24: raise ValueError("Invalid walk cycle FPS")
            # Shared visible-height scaling: transparent padding must not shrink the IP.
            visible=max(b[3] for b in bounds)-min(b[1] for b in bounds)
            height=float(self.char.get("visibleHeight",42))
            if not 16<=height<=100:raise ValueError("Character visibleHeight must be 16–100 display pixels")
            factor=height/visible
            for im,ax,ay in originals:
                self.frames.append(im.resize((round(im.width*factor*self.scale),round(im.height*factor*self.scale)),Image.Resampling.LANCZOS))
                self.anchors.append((ax*factor,ay*factor))
        self.mode=mode
        self.trackY=max(60,max(ay for ax,ay in self.anchors)+8) if self.frames else 24
        self.labelY=self.trackY+18
        self.h=round((self.labelY+68)*self.scale)
        if self.style in REFERENCE_STYLES:setup_reference(self)
        self.starts=[float(c["start"]) for c in chapters]
        if not self.starts or not all(math.isfinite(v) for v in self.starts) or self.starts[0]!=0 or any(b<=a for a,b in zip(self.starts,self.starts[1:])) or self.starts[-1]>=duration:
            raise ValueError("Invalid chapter times")
        self.ends=self.starts[1:]+[duration]
        self.progress_mode=cfg.get("progressMode","chapter-weighted" if self.style in ("R2","R3","R5","R6") else "time-linear")
        if self.progress_mode not in ("time-linear","chapter-weighted"): raise ValueError("Unknown progress mode")
        self.bounds=[]
        # Track end room includes frame padding and visible overhang, so start/end cannot clip.
        left=right=0
        for im,(ax,ay) in zip(self.frames,self.anchors):
            left=max(left,ax); right=max(right,im.width/self.scale-ax)
        self.x0=18+left; self.x1=self.dw-18-right
        if self.x1<=self.x0: raise ValueError("角色过宽")
        self.label_columns=len(chapters)
        self.label_rows=1
        if self.readable:
            measure=ImageDraw.Draw(Image.new('RGBA',(1,1)))
            widest=max(max(measure.textlength(ch['label'],font=self.font(self.main,True))/self.scale,
                           measure.textlength(ch.get('kicker',''),font=self.font(self.small,False))/self.scale) for ch in chapters)
            columns=next((n for n in range(len(chapters),0,-1)
                          if widest+20 <= (self.dw-36-8*(n-1))/n),0)
            if not columns:raise ValueError('完整章名超过整行宽度，请准确简称，不能隐藏历史章节。')
            self.label_columns=columns if columns==len(chapters) else min(columns,4)
            self.label_rows=math.ceil(len(chapters)/self.label_columns)
            self.h=math.ceil((self.labelY+(self.label_rows-1)*66+68)*self.scale)
        # Check all labels before costly full render.
        for i in range(len(chapters)): self.frame(self.starts[i])

    def font(self,size,bold=False): return self.fonts[size,bold]
    def rect(self,d,box,fill,r=0,outline=None,width=1):
        b=tuple(round(v*self.scale) for v in box)
        d.rounded_rectangle(b,radius=round(r*self.scale),fill=fill,outline=outline,width=max(1,round(width*self.scale)))
    def text(self,d,txt,cx,cy,size,bold,fill,maxw):
        f=self.font(size,bold); bb=d.textbbox((0,0),txt,font=f)
        w,h=bb[2]-bb[0],bb[3]-bb[1]
        if w/self.scale>maxw: raise ValueError(f"标题「{txt}」在手机尺寸放不下；请准确简称，或选择新版「章节胶囊／分段跑道／双层胶囊」多行布局，不能缩字或隐藏历史")
        x=cx*self.scale-w/2-bb[0]; y=cy*self.scale-h/2-bb[1]
        d.text((round(x),round(y)),txt,font=f,fill=fill)
        box=[(x+bb[0])/self.scale,(y+bb[1])/self.scale,(x+bb[2])/self.scale,(y+bb[3])/self.scale]
        if box[0]<0 or box[1]<0 or box[2]>self.dw or box[3]>self.h/self.scale: raise ValueError("文字越界")
        self.bounds.append({"text":txt,"box":box})
    def line(self,d,x0,x1,y,color,width=3):
        if x1>x0:self.rect(d,(x0,y-width/2,x1,y+width/2),color,width/2)
    def state(self,t):
        t=max(0,min(t,self.duration)); i=min(len(self.starts)-1,bisect.bisect_right(self.starts,t)-1)
        local=(t-self.starts[i])/(self.ends[i]-self.starts[i])
        p=t/self.duration if self.progress_mode=="time-linear" else (i+local)/len(self.starts)
        return i,p,local
    def frame(self,t):
        im=Image.new("RGBA",(self.w,self.h),(0,0,0,0)); d=ImageDraw.Draw(im); self.bounds=[]
        i,p,local=self.state(t); n=len(self.chapters); y=self.trackY; x=self.x0+p*(self.x1-self.x0)
        if self.style in REFERENCE_STYLES:
            draw_reference(self,im,d,t,i,p,local,x)
            if self.frames:self.draw_character(im,t,x,y)
            return im
        if self.style!="S3":self.rect(d,(4,4,self.dw-4,self.h/self.scale-4),self.p["surface"],16,self.p["outline"])
        # Base line always shows remaining progress.
        if self.style=="S2":
            seg=(self.x1-self.x0)/n
            for j in range(n):
                a=self.x0+j*seg; b=a+seg-5
                self.line(d,a,b,y,self.p["inactive"],5)
                self.line(d,a,max(a,min(x,b)),y,self.p["active"],5)
        else:
            self.line(d,self.x0,self.x1,y,self.p["inactive"])
            self.line(d,self.x0,x,y,self.p["active"])
        gap=8; sx=18; columns=self.label_columns if self.readable else n; cw=(self.dw-2*sx-gap*(columns-1))/columns
        if self.style in ("S8","S9"):
            label=self.chapters[i]["label"]; kicker=self.chapters[i].get("kicker","")
            self.text(d,f"{i+1:02d} / {n:02d}",42,self.labelY+20,14,True,self.p["quiet"],50)
            self.text(d,kicker,self.dw/2,self.labelY+10,self.small,False,self.p["quiet"],self.dw-136)
            self.text(d,label,self.dw/2,self.labelY+35,self.main,True,self.p["text"],self.dw-136)
            if self.style=="S9":
                # Time is separate from the title box, no right-edge squeeze.
                def clock(v):return f"{int(v)//60:02d}:{int(v)%60:02d}"
                self.text(d,clock(t)+" / "+clock(self.duration),self.dw/2,self.labelY+55,12,False,self.p["quiet"],self.dw-40)
        else:
            for j,ch in enumerate(self.chapters):
                row,col=divmod(j,columns)
                a=sx+col*(cw+gap); b=a+cw; cx=(a+b)/2; active=j==i and not(self.readable and t>=self.duration)
                top=self.labelY+row*66; bot=top+54; color=self.p["active"] if active else self.p["pill"]
                if self.style=="S1":
                    self.rect(d,(a,top,b,bot),self.p["selected"] if active else color,24,self.p["outline"])
                elif self.style=="S6":
                    self.rect(d,(a,top,b,bot),self.p["pill"] if active else self.p["surface"],9,self.p["outline"])
                    self.line(d,a+10,b-10,bot-4,self.p["inactive"],2)
                    self.line(d,a+10,a+10+(cw-20)*(1 if j<i else local if active else 0),bot-4,self.p["active"],2)
                elif self.style=="S7":
                    self.rect(d,(a,top,b,bot),color,4)
                    self.rect(d,(a,top,a+3,bot),self.p["text"] if active else self.p["outline"])
                elif self.style=="S3" and active:
                    self.line(d,a+6,b-6,bot,self.p["active"],3)
                if self.style=="S5":
                    nodep=self.starts[j]/self.duration if self.progress_mode=="time-linear" else j/n
                    nx=self.x0+nodep*(self.x1-self.x0)
                    self.rect(d,(nx-4,y-4,nx+4,y+4),self.p["active"] if nx<=x else self.p["surface"],4,self.p["outline"])
                inverse=active and self.style=="S1"
                self.text(d,ch.get("kicker",""),cx,top+15,self.small,False,self.p["onSelected"] if inverse else self.p["quiet"],cw-16)
                self.text(d,ch["label"],cx,top+36,self.main,True,self.p["onSelected"] if inverse else self.p["text"] if active else self.p["quiet"],cw-16)
                # Visible glyph bounds, not nominal drawing y, determine safe bottom.
                if self.bounds[-1]["box"][3]>bot-8:raise ValueError("主标题距胶囊底部不足8px")
        if self.frames:
            self.draw_character(im,t,x,y)
        else:
            self.rect(d,(x-3,y-3,x+3,y+3),self.p["active"],3)
        return im

    def draw_character(self,im,t,x,y):
        k=int(max(0,t)*float(self.char.get("cycleFps",6)))%len(self.frames)
        ax,ay=self.anchors[k]; frame=self.frames[k]
        pos=(round((x-ax)*self.scale),round((y-ay)*self.scale))
        if pos[0]<0 or pos[1]<0 or pos[0]+frame.width>self.w or pos[1]+frame.height>self.h:raise ValueError("角色越界")
        im.alpha_composite(frame,pos)
