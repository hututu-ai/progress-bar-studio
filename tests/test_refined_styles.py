"""New style revision never silently alters existing render contracts."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skill/progress-bar-studio/scripts'))
import render_progress as r
from compat_gallery.render_overlay import Overlay,DEFAULT

class RefinedStyles(unittest.TestCase):
    def test_legacy_is_unchanged_and_revision_is_explicit(self):
        for style in ('S1','S2','S7'):
            cfg=r.demo_config(style);cfg['demoLabel']=False
            original=r.Renderer(r.validate_config(cfg))
            cfg['visualRevision']='legacy'
            self.assertEqual(original.frame(4).tobytes(),r.Renderer(r.validate_config(cfg)).frame(4).tobytes())
            cfg['visualRevision']='refined-20261030'
            revised=r.Renderer(r.validate_config(cfg))
            self.assertGreaterEqual(revised.font_size/revised.config.width*480,16)
            self.assertNotEqual(original.frame(4).tobytes(),revised.frame(4).tobytes())
            for t in (0,2.999,3,6.999,7,9.99):
                self.assertEqual(revised.frame(t).getchannel('A').getextrema(),(0,255))
    def test_unknown_revision_is_rejected(self):
        cfg=r.demo_config();cfg['visualRevision']='guess'
        with self.assertRaises(r.ConfigError):r.validate_config(cfg)
    def test_editorial_navigation_keeps_all_titles_and_completion_state(self):
        cfg=r.demo_config('S7');cfg.update({'demoLabel':False,'visualRevision':'editorial-20261030','progressMode':'chapter-weighted'})
        renderer=r.Renderer(r.validate_config(cfg))
        for t, expected in ((0,['current','upcoming','upcoming']),
                            (3,['completed','current','upcoming']),
                            (7,['completed','completed','current']),
                            (10,['completed']*3)):
            items=renderer.navigation_items(renderer.config.state(t))
            self.assertEqual([item['title'] for item in items],renderer.full_titles)
            self.assertEqual([item['status'] for item in items],expected)
            self.assertEqual(renderer.frame(t).getchannel('A').getextrema(),(0,255))
        # Full labels must survive floating-point text-box measurements.
        seen=[]
        original=renderer.label
        def record(draw,title,box,*args,**kwargs):
            seen.extend(renderer.fit_lines(title,box[2]-box[0],renderer.font_size,1))
            return original(draw,title,box,*args,**kwargs)
        renderer.label=record
        renderer.frame(4.5)
        self.assertEqual(seen,renderer.full_titles)
    def test_editorial_navigation_is_explicit_and_rejects_truncated_titles(self):
        cfg=r.demo_config('S1');cfg['visualRevision']='editorial-20261030'
        with self.assertRaises(r.ConfigError):r.validate_config(cfg)
        cfg=r.demo_config('S7');cfg['visualRevision']='editorial-20261030'
        cfg['chapters'][0]['title']='这里的标题实在太长不能完整放入'
        with self.assertRaises(r.ConfigError):r.Renderer(r.validate_config(cfg))
    def test_equal_slot_progress_enters_new_active_slot_at_boundary(self):
        for style in ('S1','S7'):
            cfg=r.demo_config(style);cfg['progressMode']='chapter-weighted'
            state=r.validate_config(cfg).state(3)
            self.assertEqual(state.chapter,1)
            self.assertAlmostEqual(state.progress,1/3)
    def test_refined_dots_keep_every_title_without_status_clutter(self):
        regular=str(r.choose_font(None,Path.cwd()))
        cfg={'style':'08','outputWidth':960,'displayWidth':480,'fontRegular':regular,'fontBold':regular,
             'labelSize':18,'kickerSize':11,'character':{'mode':'none'},'palette':DEFAULT,
             'visualRevision':'refined-20261030'}
        chapters=[{'start':0,'label':'问题'},{'start':3,'label':'方法'},{'start':7,'label':'验证'}]
        renderer=Overlay(cfg,chapters,10)
        for t in (0,3,7,10):
            renderer.frame(t)
            self.assertEqual([b['text'] for b in renderer.bounds],['问题','方法','验证'])
        self.assertLess(renderer.h/renderer.scale,90)

if __name__=='__main__':unittest.main()
