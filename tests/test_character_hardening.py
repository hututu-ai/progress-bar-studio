"""Negative regressions from actual cross-host testing; no paid generation."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw

SCRIPTS=Path(__file__).resolve().parents[1]/'skill/progress-bar-studio/scripts'
sys.path.insert(0,str(SCRIPTS))
import asset_validation as av
import style_router as router
import render_progress as classic
from prepare_walk_sheet import prepare, remove_exterior
from make_multibg_preview import make_preview
from font_validation import require_glyphs


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.font=str(classic.choose_font(None,self.root))
        self.frames=[]
        for i in range(4):
            im=Image.new('RGBA',(64,80))
            d=ImageDraw.Draw(im);d.rectangle((20,10,44,50),fill='white')
            d.rectangle((28,12,34,17),fill='#FF00FF')
            d.rectangle((18+i*3,48,26+i*3,69),fill='black')
            self.frames.append(im)
    def env(self,option='01',character=None):
        key=router.selected_style(option)['styleKey']
        palette=router.DEFAULT if key.startswith('gallery') else classic.PALETTE_PRESETS['sage']
        return router.new_config(option,{'duration':4,'fps':24,'chapters':[
            {'start':0,'label':'问题'},{'start':1,'label':'方法'},{'start':2.5,'label':'验证'}]},
            self.font,self.font,1080,palette,character)
    def paths(self,frames):
        paths=[]
        for i,im in enumerate(frames):
            path=self.root/f'f{i}.png';im.save(path);paths.append(str(path))
        return paths
    def test_duplicate_and_translation_only_frames_rejected(self):
        translated=[]
        for i in range(4):
            im=Image.new('RGBA',(80,80));im.paste(self.frames[0],(i,0));translated.append(im)
        for frames in ([self.frames[0]]*4,translated):
            with self.assertRaises(ValueError):av.validate_frames(frames)
    def test_dimensions_and_alpha_rejected(self):
        with self.assertRaises(ValueError):av.validate_frames(self.frames[:3]+[self.frames[3].resize((65,80))])
        with self.assertRaises(ValueError):av.require_transparency(Image.new('RGBA',(10,10),'white'),'opaque')
        semi=self.frames[0].copy();semi.putalpha(semi.getchannel('A').point(lambda a: min(148,a)))
        with self.assertRaises(ValueError):av.require_transparency(semi,'semi')
    def test_both_engines_reject_transparent_and_noisy_anchors(self):
        self.frames[0].putpixel((0,0),(255,255,255,1));paths=self.paths(self.frames)
        for option in ('01','08'):
            char=({'mode':'walk-cycle','approved':True,'frames':paths,'height':50,'contacts':[[0,0]]*4}
                if option=='01' else {'mode':'four-frame','frames':paths,'anchors':[{'x':0,'y':0}]*4,'visibleHeight':24})
            with self.assertRaises(ValueError):router.build_renderer(self.env(option,char),self.root)
    def test_noise_does_not_set_geometry_or_rewrite_source(self):
        im=self.frames[0];im.putpixel((63,79),(255,255,255,1))
        before=im.tobytes();self.assertEqual(av.default_contact(im)[1],69)
        self.assertEqual(av.visible_bounds(im)[3],70);self.assertEqual(before,im.tobytes())
    def test_new_shared_body_pivot_stops_foot_x_jitter_both_engines(self):
        paths=self.paths(self.frames);points=[av.default_contact(im) for im in self.frames]
        for option in ('01','08'):
            char=({'mode':'walk-cycle','approved':True,'frames':paths,'height':50,'contacts':points,'cadence':6,'bodyPivotX':32}
                if option=='01' else {'mode':'four-frame','frames':paths,'anchors':[{'x':x,'y':y} for x,y in points],
                    'visibleHeight':24,'cycleFps':6,'bodyPivotX':32})
            if option=='01':char['contacts']=[list(p) for p in points]
            renderer=router.build_renderer(self.env(option,char),self.root);offsets=[]
            for i in range(4):
                t=i/6;im=renderer.frame(t)
                xs=[x for y in range(im.height) for x in range(im.width)
                    if (lambda p:p[0]>230 and p[1]<20 and p[2]>230 and p[3]>128)(im.getpixel((x,y)))]
                self.assertTrue(xs)
                if option=='01':edge=renderer.x0+renderer.config.state(t).progress*(renderer.x1-renderer.x0)
                else:
                    o=renderer.overlay;edge=(o.x0+o.state(t)[1]*(o.x1-o.x0))*o.scale
                offsets.append((min(xs)+max(xs))/2-edge)
            self.assertLess(max(offsets)-min(offsets),1.5)
    def test_background_extraction_preserves_white_body(self):
        im=Image.new('RGB',(80,80),'#00B8FF');d=ImageDraw.Draw(im)
        d.ellipse((10,10,70,70),fill='white',outline='black',width=3)
        before=im.tobytes();out,key=remove_exterior(im)
        self.assertEqual(out.getpixel((40,40)),(255,255,255,255))
        self.assertEqual(out.getpixel((0,0))[3],0);self.assertEqual(before,im.tobytes())
    def test_bad_translucent_body_is_reported_not_approved(self):
        sheet=Image.new('RGBA',(256,80))
        for i,frame in enumerate(self.frames):
            im=frame.copy();alpha=im.getchannel('A');d=ImageDraw.Draw(alpha)
            d.rectangle((21,11,43,49),fill=148);im.putalpha(alpha)
            sheet.paste(im,(64*i,0))
        out,report=prepare(sheet)
        self.assertFalse(report['userApproved'])
        self.assertTrue(all(s['fractionBelow240']>.1 for s in report['interiorAlpha']))
        self.assertTrue(any('translucent' in s for s in report['warnings']))
    def test_checkerboard_exterior_not_silently_keyed(self):
        im=Image.new('RGB',(80,80),'white');d=ImageDraw.Draw(im)
        for y in range(0,80,10):
            for x in range(0,80,10):
                if (x//10+y//10)%2:d.rectangle((x,y,x+9,y+9),fill='#AAAAAA')
        with self.assertRaisesRegex(ValueError,'not near-uniform'):remove_exterior(im)
    def test_2x2_prepare_keeps_shared_canvases_and_pending_approval(self):
        sheet=Image.new('RGBA',(128,160))
        for i,im in enumerate(self.frames):sheet.paste(im,((i%2)*64,(i//2)*80))
        out,report=prepare(sheet,'2x2')
        self.assertEqual(out.size,(256,80));self.assertFalse(report['userApproved'])
        self.assertEqual(report['gaitReview'],'pending')
        for i,im in enumerate(self.frames):self.assertEqual(out.crop((64*i,0,64*(i+1),80)).tobytes(),im.tobytes())
    def test_prepare_rejects_clipped_or_opaque_input(self):
        sheet=Image.new('RGBA',(256,80))
        for i,im in enumerate(self.frames):sheet.paste(im,(i*64,0))
        sheet.putpixel((64,10),(0,0,0,255))
        with self.assertRaisesRegex(ValueError,'boundary'):prepare(sheet)
        with self.assertRaisesRegex(ValueError,'Opaque'):prepare(sheet.convert('RGB'))
    def test_publisher_never_overwrites_or_leaves_new_partial_files(self):
        folder=self.root/'out';av.publish_new_files(folder,{'old.txt':b'original'})
        with self.assertRaises(ValueError):av.publish_new_files(folder,{'new.txt':b'new','old.txt':b'bad'})
        self.assertEqual((folder/'old.txt').read_bytes(),b'original');self.assertFalse((folder/'new.txt').exists())
    def test_split_rerun_preserves_all_existing_bytes(self):
        sheet=Image.new('RGBA',(256,80))
        for i,im in enumerate(self.frames):sheet.paste(im,(i*64,0))
        path=self.root/'sheet.png';sheet.save(path);folder=self.root/'cycle'
        args=[sys.executable,str(SCRIPTS/'split_walk_cycle.py'),'--input',str(path),'--out-dir',str(folder)]
        result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
        before={p.name:p.read_bytes() for p in folder.iterdir()}
        result=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(result.returncode,0)
        self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})
    def test_portable_multibg_has_six_actual_backgrounds(self):
        out=make_preview(self.frames[0],'#00FF00')
        w,h=64,80;pitch=h+28+24
        for i,color in enumerate(((255,255,255),(0,0,0),(255,0,0),(0,0,255),(0,255,0))):
            self.assertEqual(out.getpixel(((i%2)*(w+24)+12,(i//2)*pitch+40)),color)
    def test_actual_cjk_regular_and_bold_font_coverage(self):
        require_glyphs(self.font,'章节ABC012')
        latin=next((p for p in (Path('/System/Library/Fonts/Helvetica.ttc'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')) if p.exists()),None)
        if not latin:self.skipTest('No Latin-only test font installed')
        require_glyphs(latin,'ABC012')
        with self.assertRaisesRegex(ValueError,'missing'):require_glyphs(latin,'章节')
        for option in ('01','08'):
            env=self.env(option);cfg=env['rendererConfig']
            cfg['fontBold']=str(latin)
            with self.assertRaisesRegex(ValueError,'missing'):router.build_renderer(env,self.root)
    def test_all_eight_none_modes_never_open_role_images_and_label_is_separate(self):
        for spec in router.creator_catalog():
            base=self.env(spec['id']);plain=router.build_renderer(copy.deepcopy(base),self.root)
            base['synthetic']=True
            with patch.object(Image,'open',side_effect=AssertionError('none opened an image')):
                marked=router.build_renderer(base,self.root)
                a=plain.frame(1.5);b=marked.frame(1.5)
            self.assertGreater(b.height,a.height)
            self.assertEqual(a.tobytes(),b.crop((0,b.height-a.height,b.width,b.height)).tobytes())


if __name__=='__main__':unittest.main()
