"""Actual GIF timing, order, looping and unapproved review state."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image,ImageDraw
SCRIPTS=Path(__file__).resolve().parents[1]/'skill/progress-bar-studio/scripts'
sys.path.insert(0,str(SCRIPTS))
from build_walk_review import build,gif_durations,tiles


class GifReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.frames=[];sheet=Image.new('RGBA',(128,32))
        for i in range(4):
            im=Image.new('RGBA',(32,32));ImageDraw.Draw(im).rectangle((8,6,23,25),fill=(50+i*30,120,70,255))
            self.frames.append(im);sheet.paste(im,(i*32,0))
        source=self.root/'sheet.png';sheet.save(source)
        result=subprocess.run([sys.executable,str(SCRIPTS/'split_walk_cycle.py'),'--input',str(source),
            '--out-dir',str(self.root/'cycle'),'--fps','6'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.cycle=self.root/'cycle/character-walk-cycle.json'
    def test_centisecond_timing_does_not_silently_speed_up_8fps(self):
        self.assertEqual(sum(gif_durations(8)),500);self.assertEqual(sum(gif_durations(6)),670)
        self.assertTrue(all(v%10==0 for fps in (6,8) for v in gif_durations(fps)))
    def test_unsupported_speed_rejected(self):
        for fps in (0,12,24):
            with self.assertRaises(ValueError):gif_durations(fps)
    def test_actual_gifs_have_four_frames_in_correct_order_and_loop(self):
        files,report=build(self.cycle)
        for fps in (6,8):
            with Image.open(io.BytesIO(files[f'walk-{fps}fps.gif'])) as im:
                self.assertEqual(im.n_frames,4);self.assertEqual(im.info['loop'],0)
                for i in range(4):
                    im.seek(i);self.assertEqual(im.info['duration'],gif_durations(fps)[i])
                    actual=im.convert('RGB').getpixel((156,57));expected=(50+i*30,120,70)
                    self.assertTrue(all(abs(a-b)<=2 for a,b in zip(actual,expected)),(i,actual,expected))
        self.assertFalse(report['userApproved']);self.assertEqual(report['gaitReview'],'pending')
        self.assertEqual(report['wrapTransition'],'4->1');self.assertEqual(report['interpolatedFrames'],0)
    def test_source_frames_never_rewritten_or_reapproved(self):
        paths=list((self.root/'cycle').glob('*'));before={p.name:p.read_bytes() for p in paths}
        build(self.cycle)
        self.assertEqual(before,{p.name:p.read_bytes() for p in paths})
    def test_visible_color_change_is_not_hidden_by_identical_alpha(self):
        _,report=build(self.cycle)
        for transition in report['transitionDiagnostics']:
            self.assertEqual(transition['changeBox'],[8,6,24,26])
    def test_manifest_playback_order_is_preserved_in_report_and_actual_gif(self):
        manifest=json.loads(self.cycle.read_text());order=[3,1,4,2]
        manifest['playbackOrder']=order;self.cycle.write_text(json.dumps(manifest))
        frames=[Image.open(self.cycle.parent/name).convert('RGBA') for name in manifest['frames']]
        chosen=[frames[index-1] for index in order]
        chosen[0].save(self.cycle.parent/manifest['preview'],'WEBP',save_all=True,
            append_images=chosen[1:],duration=167,loop=0,lossless=True,kmin=1,kmax=1)
        files,report=build(self.cycle)
        self.assertEqual(report['order'],order);self.assertEqual(report['wrapTransition'],'2->3')
        self.assertEqual([(row['from'],row['to']) for row in report['transitionDiagnostics']],
                         [(3,1),(1,4),(4,2),(2,3)])
        with Image.open(io.BytesIO(files['walk-6fps.gif'])) as gif:
            for i,source in enumerate(order):
                gif.seek(i);pixel=gif.convert('RGB').getpixel((156,57))
                self.assertLessEqual(abs(pixel[0]-(50+(source-1)*30)),2)
    def test_shared_ground_required_before_review(self):
        images=[im.copy() for im in self.frames];images[3].putpixel((10,31),(255,255,255,255))
        with self.assertRaisesRegex(ValueError,'Ground'):tiles(images,6)
    def test_cli_refuses_overwrite(self):
        out=self.root/'review';args=[sys.executable,str(SCRIPTS/'build_walk_review.py'),
            '--cycle',str(self.cycle),'--out-dir',str(out)]
        result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
        before={p.name:p.read_bytes() for p in out.iterdir()}
        result=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(result.returncode,0)
        self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})


if __name__=='__main__':unittest.main()
