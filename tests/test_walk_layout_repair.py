"""Pose-guide and lossless-subject regridding; never certify model gait by file hashes."""
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image,ImageDraw

SCRIPTS=Path(__file__).resolve().parents[1]/'skill/progress-bar-studio/scripts'
sys.path.insert(0,str(SCRIPTS))
from regrid_walk_sheet import regrid,components
from build_walk_pose_guide import guide
from asset_validation import visible_bounds,default_contact


def visible_pixels(image):return Counter(p for p in image.getdata() if p[3]>32)


class LayoutRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def sheet(self,grid=False):
        size=(400,350) if grid else (537,160)
        positions=[(20,20),(220,20),(20,200),(220,200)] if grid else [(20,20),(150,20),(300,20),(420,20)]
        im=Image.new('RGBA',size);d=ImageDraw.Draw(im)
        for i,(x,y) in enumerate(positions):
            d.rectangle((x,y,x+72,y+100),fill=(40+i*30,110,80,255))
            d.rectangle((x+55,y+85,x+83+i,y+107),fill=(20,40+i*20,70,255))
        return im
    def test_scanline_components_keep_diagonal_pixels_connected(self):
        mask=Image.new('L',(10,10));d=ImageDraw.Draw(mask)
        d.point((3,3),fill=255);d.point((4,4),fill=255)
        self.assertEqual(len(components(mask)),1)
        self.assertEqual(components(mask)[0]['area'],2)
    def test_non_divisible_unequal_spacing_preserves_all_visible_rgba(self):
        im=self.sheet();before=im.tobytes();out,report=regrid(im)
        self.assertEqual(out.width%4,0);self.assertEqual(visible_pixels(im),visible_pixels(out))
        self.assertEqual(before,im.tobytes());self.assertFalse(report['userApproved'])
        self.assertEqual(report['gaitReview'],'pending');self.assertTrue(report['substantialAlphaPixelsPreserved'])
        self.assertTrue(all(t['scale']==1 for t in report['sourceTransforms']))
    def test_source_pixels_can_cross_old_equal_cell_lines_without_clipping(self):
        im=self.sheet();out,report=regrid(im)
        self.assertEqual(visible_pixels(im),visible_pixels(out))
        cw=out.width//4;ground=[]
        for i in range(4):
            frame=out.crop((i*cw,0,(i+1)*cw,out.height));box=visible_bounds(frame)
            self.assertGreaterEqual(min(box[0],box[1],cw-box[2],out.height-box[3]),8)
            ground.append(default_contact(frame)[1])
        self.assertEqual(len(set(ground)),1)
    def test_2x2_row_major_order_and_common_scale(self):
        im=self.sheet(True);out,report=regrid(im,arrangement='2x2')
        self.assertEqual(visible_pixels(im),visible_pixels(out));cw=out.width//4
        for i in range(4):
            colors=visible_pixels(out.crop((i*cw,0,(i+1)*cw,out.height)))
            self.assertIn((40+i*30,110,80,255),colors)
        self.assertFalse(report['independentScale'])
    def test_merged_subjects_rejected_instead_of_sliced(self):
        im=self.sheet();ImageDraw.Draw(im).line((90,40,160,40),fill='black',width=4)
        with self.assertRaisesRegex(ValueError,'separate complete'):regrid(im)
    def test_original_canvas_clipping_rejected(self):
        im=self.sheet();ImageDraw.Draw(im).rectangle((0,20,21,30),fill='black')
        with self.assertRaisesRegex(ValueError,'original canvas edge'):regrid(im)
    def test_far_visible_fragment_is_not_silently_dropped(self):
        im=self.sheet();ImageDraw.Draw(im).rectangle((260,145,265,150),fill='black')
        with self.assertRaisesRegex(ValueError,'fragment'):regrid(im)
    def test_near_detached_hair_and_antialiasing_are_preserved(self):
        im=self.sheet();im.putpixel((25,16),(30,20,10,255));im.putpixel((19,30),(60,80,90,20))
        out,report=regrid(im)
        self.assertEqual(visible_pixels(im),visible_pixels(out))
        self.assertEqual(sum(p[3]==20 for p in im.getdata()),sum(p[3]==20 for p in out.getdata()))
    def test_remote_faint_noise_is_reported_not_used_as_a_foot(self):
        im=self.sheet();im.putpixel((535,158),(255,0,255,1))
        out,report=regrid(im)
        self.assertEqual(report['faintPixelsOmitted'],1)
        self.assertEqual(visible_pixels(im),visible_pixels(out))
    def test_translucent_interiors_are_not_recolored_or_forced_opaque(self):
        im=self.sheet();im.putpixel((50,50),(255,255,255,148))
        out,report=regrid(im)
        self.assertEqual(visible_pixels(im),visible_pixels(out))
        self.assertIn((255,255,255,148),visible_pixels(out))
    def test_regrid_does_not_turn_duplicate_poses_into_walk_frames(self):
        im=Image.new('RGBA',(600,160));d=ImageDraw.Draw(im)
        for i in range(4):d.rectangle((20+i*150,20,100+i*150,125),fill='#457627')
        with self.assertRaisesRegex(ValueError,'same pose'):regrid(im)
    def test_opaque_background_needs_real_extraction_first(self):
        with self.assertRaises(ValueError):regrid(self.sheet().convert('RGB'))
    def test_invalid_layout_padding_and_wrong_arrangement(self):
        for kwargs in ({'padding':0},{'arrangement':'unknown'},{'arrangement':'horizontal'}):
            im=self.sheet(True) if kwargs.get('arrangement')=='horizontal' else self.sheet()
            with self.assertRaises(ValueError):regrid(im,**kwargs)
    def test_cli_refuses_overwrite_and_keeps_original(self):
        source=self.root/'source.png';self.sheet().save(source);before=source.read_bytes();out=self.root/'out'
        args=[sys.executable,str(SCRIPTS/'regrid_walk_sheet.py'),'--input',str(source),'--out-dir',str(out)]
        first=subprocess.run(args,capture_output=True,text=True);self.assertEqual(first.returncode,0,first.stderr)
        files={p.name:p.read_bytes() for p in out.iterdir()}
        second=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(second.returncode,0)
        self.assertEqual(files,{p.name:p.read_bytes() for p in out.iterdir()});self.assertEqual(before,source.read_bytes())
    def test_pose_guide_swaps_depth_roles_in_second_half(self):
        image,report=guide();p=report['phases']
        self.assertEqual(image.size,(1040,1236));self.assertEqual(report['role'],'pose-reference-only')
        for a,b in ((0,2),(1,3)):
            self.assertEqual(p[a]['nearLeg'],p[b]['farLeg']);self.assertEqual(p[a]['farLeg'],p[b]['nearLeg'])
            self.assertEqual(p[a]['nearArm'],p[b]['farArm']);self.assertEqual(p[a]['farArm'],p[b]['nearArm'])
        self.assertFalse(report['userApproved'])


if __name__=='__main__':unittest.main()
