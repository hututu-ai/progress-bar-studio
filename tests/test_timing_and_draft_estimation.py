"""Reproduce the independent forward-test failures using real probed video."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skill/progress-bar-studio/scripts'
sys.path.insert(0, str(SCRIPTS))
import style_router as router
import validate_chapters as chapters


class VideoFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='source-timing-')
        cls.root = Path(cls.tmp.name)
        cls.video = cls.root / '12s-24fps.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=c=blue:s=64x32:r=24:d=12', '-an', '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', str(cls.video)], check=True)
        cls.source_id = 'sha256:' + hashlib.sha256(cls.video.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class SourceTimingTests(VideoFixture):
    def setUp(self):
        self.transcript = {'sourceId': self.source_id, 'segments': [
            {'id': str(i), 'start': i * 4 + (.2 if i == 0 else 0), 'end': i * 4 + 3.8,
             'text': text} for i, text in enumerate(('提出问题。', '提供方法。', '检查结果。'))]}
        self.plan = {'sourceId': self.source_id, 'duration': 12, 'fps': 24,
                     'chapters': [{'start': i * 4, 'end': (i + 1) * 4,
                                   'label': s['text'], 'summary': s['text'],
                                   'openingQuote': s['text'], 'boundaryReason': '独立任务',
                                   'segmentIds': [s['id']], 'needsReview': False}
                                  for i, s in enumerate(self.transcript['segments'])]}

    def validate(self):
        return chapters.validate(self.plan, self.transcript, self.video,
                                 current_policy=True, require_reviewed=True)

    def test_real_source_timing_passes_without_semantic_claim(self):
        result = self.validate()
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['sourceVideoVerified'])
        self.assertIn('not assessed', result['semanticQuality'])

    def test_wrong_fps_cannot_expand_duration_tolerance(self):
        self.plan.update(duration=12.6, fps=1)
        self.plan['chapters'][-1]['end'] = 12.6
        result = self.validate()
        self.assertFalse(result['ok'])
        self.assertFalse(result['sourceVideoVerified'])
        self.assertIn('source frame rate differs', result['errors'])
        self.assertIn('source duration differs', result['errors'])

    def test_wrong_rate_fails_even_with_correct_duration(self):
        self.plan['fps'] = 1
        self.assertIn('source frame rate differs', self.validate()['errors'])

    def test_wrong_duration_fails_with_correct_rate(self):
        self.plan['duration'] = self.plan['chapters'][-1]['end'] = 12.6
        self.assertIn('source duration differs', self.validate()['errors'])

    def test_one_real_frame_rounding_still_passes_but_two_do_not(self):
        for delta, expected in ((1 / 24, True), (2 / 24, False)):
            self.plan['duration'] = self.plan['chapters'][-1]['end'] = 12 + delta
            result = self.validate()
            self.assertEqual(result['ok'], expected, result)

    def test_rational_and_numeric_fps_are_equivalent(self):
        for rate in ('24/1', '24', 24.0):
            self.plan['fps'] = rate
            self.assertTrue(self.validate()['ok'])

    def test_invalid_rates_rejected_without_false_verification(self):
        for rate in (True, False, None, {}, [], '0/0', '1/0', 'nan', 'inf', -1, 0):
            self.plan['fps'] = rate
            result = self.validate()
            self.assertFalse(result['ok'], rate)
            self.assertFalse(result['sourceVideoVerified'], rate)

    def test_video_duration_precedes_longer_audio_container(self):
        payload = {'streams': [{'duration': '12', 'avg_frame_rate': '24/1'}],
                   'format': {'duration': '13.5'}}
        with patch.object(chapters.subprocess, 'check_output', return_value=json.dumps(payload)):
            self.assertEqual(chapters.source_timing(self.video), (12, 24))
            self.assertTrue(self.validate()['ok'])

    def test_missing_stream_rate_or_duration_fails_closed(self):
        for payload in ({'streams': [], 'format': {'duration': '12'}},
                        {'streams': [{'duration': '12', 'avg_frame_rate': '0/0'}]},
                        {'streams': [{'duration': 'N/A', 'avg_frame_rate': '24/1'}]}):
            with patch.object(chapters.subprocess, 'check_output', return_value=json.dumps(payload)):
                with self.assertRaises(ValueError):
                    chapters.source_timing(self.video)

    def test_probe_fallback_and_fractional_rounding(self):
        payload = {'streams': [{'duration': 'N/A', 'avg_frame_rate': '0/0',
                                'r_frame_rate': '30000/1001'}], 'format': {'duration': '12'}}
        with patch.object(chapters.subprocess, 'check_output', return_value=json.dumps(payload)):
            self.assertAlmostEqual(chapters.source_timing(self.video)[1], 30000 / 1001)
            for rate in ('30000/1001', 29.97):
                self.plan['fps'] = rate
                self.assertTrue(self.validate()['ok'])
            self.plan['fps'] = 30
            self.assertFalse(self.validate()['ok'])


class DraftEstimationTests(VideoFixture):
    def estimate(self, config, *options, expected=0):
        path = self.root / 'estimate-config.json'
        path.write_text(json.dumps(config), encoding='utf-8')
        before = path.read_bytes()
        result = subprocess.run([sys.executable, str(SCRIPTS / 'estimate_export_size.py'),
                                 str(self.video), '--config', str(path), '--output-dir',
                                 str(self.root), '--json', *options], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(path.read_bytes(), before)
        return json.loads(result.stdout) if expected == 0 else result.stderr

    def config(self, draft=False, option='01'):
        font = str(router.classic.choose_font(None, self.root))
        timeline = {'duration': 12, 'fps': 24, 'chapters': [
            {'start': 0, 'label': '发现问题'}, {'start': 4, 'label': '解决方法'},
            {'start': 8, 'label': '实际验证'}]}
        palette = router.DEFAULT if option == '08' else router.classic.PALETTE_PRESETS['sage']
        config = router.new_config(option, timeline, font, font, 2160, palette)
        if draft:
            config['reviewState'] = 'draft'
        return config

    def test_draft_estimate_uses_actual_height_and_preserves_pending_state(self):
        for option in ('01', '08'):
            config = self.config(True, option)
            original = copy.deepcopy(config)
            actual = router.build_renderer(config, self.root, draft=True).config
            result = self.estimate(config, '--draft')
            self.assertEqual(config, original)
            self.assertEqual(result['reviewState'], 'draft')
            self.assertEqual([(e['width'], e['height']) for e in result['estimates']],
                             [(actual.width, actual.height)])
            self.assertFalse(result['upperBoundGuaranteed'])
            self.assertIn('not a guaranteed upper bound', result['note'])
            self.assertNotIn('approved', config)

    def test_pending_draft_requires_explicit_flag(self):
        self.assertIn('explicit draft route', self.estimate(self.config(True), expected=2))

    def test_draft_flag_cannot_silently_change_approved_route(self):
        self.assertIn('explicit draft route', self.estimate(self.config(), '--draft', expected=2))

    def test_normal_estimate_remains_compatible(self):
        config = self.config()
        actual = router.build_renderer(config, self.root).config
        result = self.estimate(config)
        self.assertEqual(result['estimates'][0]['height'], actual.height)
        self.assertEqual(result['reviewState'], 'unchanged')

    def test_draft_still_rejects_conflicting_dimensions_and_old_timeline(self):
        self.assertIn('dimensions conflict', self.estimate(self.config(True), '--draft',
                      '--width', '2560', expected=2))
        config = self.config(True)
        config['rendererConfig']['duration'] = 12.6
        config['rendererConfig']['chapters'][-1]['end'] = 12.6
        self.assertIn('duration differs', self.estimate(config, '--draft', expected=2))

    def test_draft_flag_needs_config(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'estimate_export_size.py'),
                                 str(self.video), '--draft', '--json'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--draft requires --config', result.stderr)


if __name__ == '__main__':
    unittest.main()
