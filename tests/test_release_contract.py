"""Current catalog, full-label layouts and opt-in visual reuse regression fixtures."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skill/progress-bar-studio/scripts'))
import style_router as router
import visual_profile as profiles
from PIL import Image,ImageDraw

class ReleaseContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.font=str(router.classic.choose_font(None,self.root))
        self.labels=['提出问题','建立观点','理由分析','案例说明','操作演示','效果对比','总结要点']
    def timeline(self,count=3,duration=10):
        return {'duration':duration,'fps':24,'chapters':[{'start':i*duration/count,'label':self.labels[i],'kicker':f'理由{i+1}'} for i in range(count)]}
    def config(self,option='01',count=3):
        key=router.selected_style(option)['styleKey']
        palette=dict(router.DEFAULT) if key.startswith('gallery:') else dict(router.classic.PALETTE_PRESETS['sage'])
        return router.new_config(option,self.timeline(count),self.font,self.font,960,palette)
    def test_catalog_revision_is_the_actual_new_config_revision(self):
        for item in router.creator_catalog():
            env=self.config(item['id'])
            self.assertEqual(env['rendererConfig']['visualRevision'],item['visualRevision'])
            self.assertEqual(env['rendererConfig']['progressMode'],item['progressMode'])
            self.assertEqual(env['styleKey'],item['styleKey'])
            router.build_renderer(env,self.root).frame(4.5)
        self.assertEqual(self.config('07')['rendererConfig']['visualRevision'],'editorial-20261030')
    def test_multichapter_layouts_keep_exact_text_and_fixed_height(self):
        for option in ('01','02','08'):
            for count in (3,4,5):
                with self.subTest(option=option,count=count):
                    env=self.config(option,count);renderer=router.build_renderer(env,self.root)
                    size=None
                    for t in (0,2.999,3,4.5,6.999,7,9.99,10):
                        frame=renderer.frame(t)
                        self.assertEqual(frame.getchannel('A').getextrema(),(0,255))
                        if size is None:size=frame.size
                        self.assertEqual(frame.size,size)
                        if option=='08':
                            shown=[b['text'] for b in renderer.overlay.bounds]
                            self.assertTrue(all(label in shown for label in self.labels[:count]))
                        elif renderer.chapter_grid:
                            self.assertEqual([b['title'] for b in renderer.grid_bounds],self.labels[:count])
                            for b in renderer.grid_bounds:
                                self.assertGreaterEqual(b['box'][1],0)
                                self.assertLessEqual(b['box'][3],frame.height)
                                self.assertEqual(renderer.fit_lines(b['title'],b['box'][2]-b['box'][0],renderer.font_size,1),[b['title']])
    def test_new_projects_enforce_three_to_five_but_history_still_renders(self):
        for count in (2,6,7):
            with self.assertRaises(ValueError):self.config('01',count)
        env=self.config('01')
        env=router.with_timeline(env,self.timeline(7))
        self.assertEqual(len(router.build_renderer(env,self.root).config.chapters),7)
        timeline=self.timeline();timeline['chapters'][1]['needsReview']=True
        with self.assertRaises(ValueError):router.check_new_chapters(timeline)
    def test_five_long_labels_are_full_size_multiline_not_ellipsis(self):
        for option in ('01','02','08'):
            env=self.config(option,5)
            key='chapters' if option!='08' else None
            chapters=env['rendererConfig']['chapters'] if key else env['timeline']['chapters']
            labels=['内容定位方法','操作步骤拆分','案例使用方式','标题提炼规则','成品效果检查']
            for c,label in zip(chapters,labels):c['title' if key else 'label']=label
            renderer=router.build_renderer(env,self.root)
            for t in (0,2,4.5,6,8,10):
                renderer.frame(t)
                if key:
                    self.assertTrue(renderer.chapter_grid)
                    self.assertEqual([b['title'] for b in renderer.grid_bounds],labels)
                    if t==10:self.assertTrue(all(b['status']=='completed' for b in renderer.grid_bounds))
                else:
                    self.assertGreater(renderer.overlay.label_rows,1)
                    self.assertTrue(all(label in [b['text'] for b in renderer.overlay.bounds] for label in labels))
    def test_visual_profile_round_trip_all_eight_routes_and_new_timing(self):
        for item in router.creator_catalog():
            option=item['id'];env=self.config(option)
            source=self.root/f'{option}.json';source.write_text(json.dumps(env))
            result=profiles.save(source,self.root/f'profile-{option}',True,True,{'x':0,'y':32,'scale':1})
            path=Path(result['profile']);profile=profiles.read(path)
            self.assertNotIn('timeline',profile['template'])
            self.assertFalse(any(k in profile['template']['rendererConfig'] for k in ('duration','fps','chapters')))
            output=self.root/f'restored-{option}.json'
            result=profiles.restore(path,self.timeline(),output)
            restored=router.build_renderer(router.load(output),output.parent)
            original=router.build_renderer(env,self.root)
            self.assertEqual(original.frame(4.5).tobytes(),restored.frame(4.5).tobytes())
            self.assertFalse(result['currentProjectApprovalsInherited'])
            changed=self.root/f'new-source-{option}.json'
            profiles.restore(path,self.timeline(duration=16),changed)
            self.assertEqual(router.build_renderer(router.load(changed),self.root).config.duration,16)
    def test_profiles_reject_waiver_overwrite_and_modified_assets(self):
        source=self.root/'source.json';source.write_text(json.dumps(self.config()))
        with self.assertRaises(ValueError):profiles.save(source,self.root/'unapproved')
        result=profiles.save(source,self.root/'approved',True,True)
        with self.assertRaises(ValueError):profiles.save(source,self.root/'approved',True,True)
        path=Path(result['profile']);p=profiles.read(path)
        asset=next(iter(p['assets']));(path.parent/asset).write_bytes(b'changed')
        with self.assertRaises(ValueError):profiles.read(path)
    def test_no_character_restore_does_not_read_character_files(self):
        env=self.config();frames=[]
        for i in range(4):
            path=self.root/f'frame-{i}.png';im=Image.new('RGBA',(40,40))
            ImageDraw.Draw(im).rectangle((5+i,5,25+i,34),fill=(50+i*40,100,20,255));im.save(path);frames.append(str(path))
        env['rendererConfig']['character']={'mode':'walk-cycle','approved':True,'frames':frames,'height':42,'cadence':6}
        source=self.root/'ip.json';source.write_text(json.dumps(env))
        saved=profiles.save(source,self.root/'ip-profile',True,True);path=Path(saved['profile']);p=profiles.read(path)
        for relative,asset in p['assets'].items():
            if asset['role']=='character':(path.parent/relative).unlink()
        output=self.root/'no-ip.json';profiles.restore(path,self.timeline(),output,no_character=True)
        self.assertEqual(router.load(output)['rendererConfig']['character'],{'mode':'none'})
        with self.assertRaises(ValueError):profiles.read(path)

if __name__=='__main__':unittest.main()
