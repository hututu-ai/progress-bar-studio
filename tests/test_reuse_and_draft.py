"""First approved run -> persistent IP -> new-video reuse, plus honest draft review."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw

SCRIPTS=Path(__file__).resolve().parents[1]/'skill/progress-bar-studio/scripts'
sys.path.insert(0,str(SCRIPTS))
import character_library as lib
import style_router as router
import visual_profile as profiles
from asset_validation import default_contact
from verify_alpha_portable import verify


class ReturningUserTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'first-project';self.source.mkdir()
        self.library=self.root/'private-library'
        self.font=str(router.classic.choose_font(None,self.root));self.frames=[]
        for i in range(4):
            im=Image.new('RGBA',(64,80));d=ImageDraw.Draw(im)
            d.ellipse((20,8,44,40),fill='white',outline='black',width=2)
            d.rectangle((24,36,40,54),fill='#548337')
            d.rectangle((17+i*4,51,25+i*4,70),fill='black')
            path=self.source/f'f{i}.png';im.save(path);self.frames.append(path)
        self.spec={'label':'我的小怪','frames':[p.name for p in self.frames],
                   'cadence':6,'heightRatio':.06,'bodyPivotX':32}
    def saved(self):
        return Path(lib.save(self.spec,self.source,self.library,True,True)['character'])
    def timeline(self,duration=4):
        return {'duration':duration,'fps':24,'chapters':[
            {'start':0,'label':'新问题'},{'start':duration/4,'label':'新方法'},
            {'start':duration*.625,'label':'新验证'}]}
    def env(self,option='01',char=None):
        palette=router.DEFAULT if router.selected_style(option)['styleKey'].startswith('gallery:') else router.classic.PALETTE_PRESETS['sage']
        return router.new_config(option,self.timeline(),self.font,self.font,1080,palette,char)
    def test_approved_four_frames_are_copied_not_only_referenced(self):
        path=self.saved();data=lib.read(path)
        for source,row in zip(self.frames,data['frames']):
            self.assertEqual(source.read_bytes(),(path.parent/row['path']).read_bytes())
        shutil.rmtree(self.source)
        self.assertEqual(lib.read(path)['label'],'我的小怪')
        self.assertFalse(data['currentProjectApprovalsInherited'])
    def test_requires_actual_asset_approval_and_no_timeline_storage(self):
        with self.assertRaises(ValueError):lib.save(self.spec,self.source,self.library)
        for field in ('timeline','sourceVideo','reviewState','style'):
            with self.assertRaises(ValueError):lib.save(self.spec|{field:'draft'},self.source,self.library,True)
        self.assertFalse(self.library.exists())
    def test_repeat_save_is_idempotent_and_originals_unchanged(self):
        before=[p.read_bytes() for p in self.frames];first=self.saved()
        again=lib.save(self.spec,self.source,self.library,True,True)
        self.assertTrue(again['alreadySaved']);self.assertEqual(first,Path(again['character']))
        self.assertEqual(before,[p.read_bytes() for p in self.frames])
        self.assertEqual(len(list((self.library/'characters').iterdir())),1)
    def test_missing_and_tampered_cached_frames_refused_without_generation(self):
        path=self.saved();data=lib.read(path);frame=path.parent/data['frames'][0]['path']
        old=frame.read_bytes();frame.write_bytes(old+b'changed')
        with self.assertRaises(ValueError):lib.read(path)
        frame.unlink()
        with self.assertRaises(ValueError):lib.export_character(path,'classic',2160,reuse_authorized=True)
        self.assertEqual(len(list((self.library/'characters').iterdir())),1)
    def test_metadata_tamper_and_outside_default_pointer_refused(self):
        path=self.saved();data=lib.read(path);data['label']='tampered';path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):lib.read(path)
        (self.library/'default-character.json').write_text(json.dumps({'character':'../outside.json'}))
        with self.assertRaises(ValueError):lib.locate_default(self.library)
    def test_corrupt_cached_frame_rows_fail_cleanly_without_mutation(self):
        path=self.saved();original=json.loads(path.read_text())
        pointer=(self.library/'default-character.json').read_bytes()
        for bad in (None,7,[], 'frame.png', {'path':123,'sha256':'a'*64}):
            data=copy.deepcopy(original);data['frames'][0]=bad
            data['checksum']=lib.checksum({k:v for k,v in data.items() if k!='checksum'})
            path.write_text(json.dumps(data));before=path.read_bytes()
            with self.assertRaises(ValueError):lib.read(path)
            result=subprocess.run([sys.executable,str(SCRIPTS/'character_library.py'),'show',
                '--default','--library-dir',str(self.library)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertNotIn('Traceback',result.stderr)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual((self.library/'default-character.json').read_bytes(),pointer)
    def test_missing_or_malformed_cached_geometry_is_explained(self):
        path=self.saved();data=lib.read(path);data['geometry']=None
        data['checksum']=lib.checksum({k:v for k,v in data.items() if k!='checksum'})
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):lib.read(path)
    def test_explicit_empty_contacts_are_not_silently_replaced(self):
        images=[Image.open(p).convert('RGBA') for p in self.frames]
        with self.assertRaises(ValueError):lib.check_geometry({'contacts':[]},images)
    def test_portable_copied_library_still_resolves_default(self):
        self.saved();moved=self.root/'different-host';shutil.copytree(self.library,moved)
        path=lib.locate_default(moved);self.assertEqual(lib.read(path)['label'],'我的小怪')
        exported=lib.export_character(path,'gallery',2160,reuse_authorized=True)
        self.assertTrue(all(Path(p).is_relative_to(moved.resolve()) for p in exported['frames']))
    def test_reuse_authorization_required_and_no_renderer_fingerprint_dependency(self):
        path=self.saved()
        with self.assertRaises(ValueError):lib.export_character(path,'classic',2160)
        with patch.object(profiles,'renderer_fingerprint',return_value='new-renderer'):
            self.assertEqual(lib.read(path)['label'],'我的小怪')
            self.assertEqual(lib.export_character(path,'classic',2160,reuse_authorized=True)['mode'],'walk-cycle')
    def test_one_saved_ip_runs_all_eight_styles_on_a_new_timeline(self):
        path=self.saved();saved_hash=path.read_bytes()
        for item in router.creator_catalog():
            engine='classic' if item['styleKey'].startswith('classic:') else 'gallery'
            char=lib.export_character(path,engine,1080,reuse_authorized=True)
            env=self.env(item['id'],char);env=router.with_timeline(env,self.timeline(7))
            renderer=router.build_renderer(env,self.root)
            self.assertEqual(renderer.config.duration,7)
            self.assertEqual(renderer.frame(2).getchannel('A').getextrema(),(0,255))
        self.assertEqual(saved_hash,path.read_bytes())
    def test_none_routes_do_not_open_the_character_library(self):
        self.saved()
        with patch.object(lib,'read',side_effect=AssertionError('none read cached role')):
            for item in router.creator_catalog():
                env=self.env(item['id'],{'mode':'none'})
                router.build_renderer(env,self.root).frame(1)
    def test_default_missing_is_normal_and_does_not_create_private_folder(self):
        self.assertIsNone(lib.locate_default(self.library));self.assertFalse(self.library.exists())
        result=subprocess.run([sys.executable,str(SCRIPTS/'character_library.py'),'show','--default',
            '--library-dir',str(self.library)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'not_found');self.assertFalse(self.library.exists())
    def test_platform_locations_do_not_point_inside_skill(self):
        with patch.object(lib.sys,'platform','win32'),patch.dict(os.environ,{'LOCALAPPDATA':str(self.root/'win')}):
            self.assertEqual(lib.default_library(),self.root/'win/ProgressBarStudio')
        with patch.object(lib.sys,'platform','linux'),patch.dict(os.environ,{'XDG_DATA_HOME':str(self.root/'linux')}):
            self.assertEqual(lib.default_library(),self.root/'linux/ProgressBarStudio')


class DraftTests(unittest.TestCase):
    setUp=ReturningUserTests.setUp
    saved=ReturningUserTests.saved
    timeline=ReturningUserTests.timeline
    env=ReturningUserTests.env
    def draft(self,option='01'):
        engine='classic' if option=='01' else 'gallery'
        char=lib.export_character(self.saved(),engine,1080,reuse_authorized=True)
        if engine=='classic':char['approved']=False
        env=self.env(option,char);env['reviewState']='draft';return env
    def test_draft_accepts_unapproved_valid_assets_without_rewriting_approval(self):
        env=self.draft();before=copy.deepcopy(env)
        renderer=router.build_renderer(env,self.root,draft=True)
        self.assertEqual(renderer.frame(1).getchannel('A').getextrema(),(0,255))
        self.assertEqual(env,before);self.assertFalse(renderer.renderer.config.character['approved'])
    def test_draft_cannot_be_final_sample_debug_or_saved_profile(self):
        env=self.draft();path=self.root/'draft.json';path.write_text(json.dumps(env))
        for purpose in ('final','sample','debug'):
            with self.assertRaises(ValueError):router.export_mov(env,self.root,self.root/f'{purpose}.mov',purpose,final_approved=purpose=='final')
        with self.assertRaises(ValueError):profiles.save(path,self.root/'bad-profile',True,True)
        self.assertFalse((self.root/'bad-profile').exists())
    def test_draft_requires_explicit_review_state_and_cannot_skip_technical_gates(self):
        env=self.draft();no_state=copy.deepcopy(env);no_state.pop('reviewState')
        with self.assertRaises(ValueError):router.build_renderer(no_state,self.root,draft=True)
        env['rendererConfig']['character']['frames']=[str(self.frames[0])]*4
        with self.assertRaises(ValueError):router.build_renderer(env,self.root,draft=True)
    def test_all_eight_none_drafts_have_a_visible_review_band(self):
        for item in router.creator_catalog():
            env=self.env(item['id']);plain=router.build_renderer(env,self.root);env['reviewState']='draft'
            marked=router.build_renderer(env,self.root,draft=True)
            a=plain.frame(1);b=marked.frame(1)
            self.assertGreater(b.height,a.height)
            a=Image.alpha_composite(Image.new('RGBA',a.size),a)
            crop=b.crop((0,b.height-a.height,b.width,b.height))
            self.assertEqual(a.tobytes(),crop.tobytes())
            self.assertGreater(b.getpixel((10,10))[3],0)
    def test_cli_draft_preview_and_validation_require_explicit_flag(self):
        for option in ('01','08'):
            env=self.draft(option);path=self.root/f'draft-{option}.json';path.write_text(json.dumps(env))
            prefix=[sys.executable,str(SCRIPTS/'style_router.py')]
            for command in ('validate','preview'):
                args=prefix+[command,str(path)]
                if command=='preview':args+=[str(self.root/f'draft-{option}.png')]
                rejected=subprocess.run(args,capture_output=True,text=True)
                self.assertNotEqual(rejected.returncode,0)
                result=subprocess.run(args+['--draft'],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            with Image.open(self.root/f'draft-{option}.png') as im:self.assertGreater(im.getpixel((10,10))[3],0)
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
    def test_real_draft_mov_and_duration_limit(self):
        env=self.draft();movie=self.root/'draft.mov'
        report=router.export_mov(env,self.root,movie,'draft',start=.75,seconds=.5)
        self.assertFalse(report['userApproved']);self.assertFalse(report['finalDelivery'])
        self.assertEqual(report['reviewState'],'draft');self.assertTrue(verify(movie)['ok'])
        with self.assertRaises(ValueError):router.export_mov(env,self.root,self.root/'long.mov','draft',seconds=16)
        self.assertFalse((self.root/'long.mov').exists())


if __name__=='__main__':unittest.main()
