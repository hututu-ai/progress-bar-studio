"""Marked, short review output. Does not grant asset, design or export approval."""
import copy
import math
from PIL import Image,ImageDraw
from font_validation import require_glyphs


class DraftRenderer:
    def __init__(self,renderer):
        self.renderer=renderer;self.config=copy.deepcopy(renderer.config)
        c=self.config
        self.font=(c.font_path if hasattr(c,'font_path') else renderer.overlay.reg)
        require_glyphs(self.font,'待审方案 / DRAFT')
        self.band=max(32,math.ceil(c.width/30))
        if (c.height+self.band)%2:self.band+=1
        c.height+=self.band
        if c.height>4320 or c.width*c.height>16_777_216:raise ValueError('Draft label exceeds safe canvas')

    def frame(self,time):
        from render_progress import font_at
        content=self.renderer.frame(time)
        out=Image.new('RGBA',(self.config.width,self.config.height))
        out.alpha_composite(content,(0,self.band))
        d=ImageDraw.Draw(out)
        d.rounded_rectangle((4,4,self.config.width-4,self.band-4),radius=6,fill='#242424')
        d.text((max(12,self.config.width//50),self.band//2),'待审方案 / DRAFT',anchor='lm',
               font=font_at(str(self.font),max(16,round(self.band*.48))),fill='white')
        return out
