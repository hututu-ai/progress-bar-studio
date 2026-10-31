import copy
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skill/progress-bar-studio/scripts/validate_chapters.py'
sys.path.insert(0,str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('chapters', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ChapterEvidenceTests(unittest.TestCase):
    def setUp(self):
        source = 'sha256:' + 'a' * 64
        self.transcript = {'sourceId': source, 'segments': [
            {'id': 'a', 'start': .2, 'end': 1.8, 'text': '发现排版问题。'},
            {'id': 'b', 'start': 2, 'end': 3.8, 'text': '开始解决问题。'}]}
        self.plan = {'sourceId': source, 'duration': 4, 'fps': 30, 'chapters': [
            {'start': 0, 'end': 2, 'label': '排版问题', 'summary': '指出问题', 'boundaryReason': '片头', 'openingQuote': '发现排版问题。', 'segmentIds': ['a']},
            {'start': 2, 'end': 4, 'label': '解决方法', 'summary': '提供方法', 'boundaryReason': '新任务', 'openingQuote': '开始解决问题。', 'segmentIds': ['b']}]}

    def check_invalid(self, mutate):
        plan, transcript = copy.deepcopy(self.plan), copy.deepcopy(self.transcript)
        mutate(plan, transcript)
        self.assertFalse(module.validate(plan, transcript)['ok'])

    def test_valid_does_not_claim_semantic_or_source_verification(self):
        result = module.validate(self.plan, self.transcript)
        self.assertTrue(result['ok'])
        self.assertFalse(result['sourceVideoVerified'])
        self.assertIn('not assessed', result['semanticQuality'])

    def test_rejects_timing_identity_and_evidence_regressions(self):
        cases = [
            lambda p,t: t.update(sourceId='sha256:' + 'b' * 64),
            lambda p,t: p.update(duration=5),
            lambda p,t: p.update(fps=0),
            lambda p,t: p['chapters'][1].update(start=2.01),
            lambda p,t: p['chapters'][1].update(start=1.99),
            lambda p,t: p['chapters'][0].update(openingQuote='不存在的原话'),
            lambda p,t: p['chapters'][0].update(segmentIds=['b']),
            lambda p,t: p['chapters'][1].update(segmentIds=[]),
            lambda p,t: t['segments'][1].update(start=2.2),
            lambda p,t: t['segments'][0].update(end=2.5),
            lambda p,t: p.update(chapters=[]),
            lambda p,t: p['chapters'][0].update(label=''),
            lambda p,t: p.update(duration=float('nan')),
        ]
        for index, mutation in enumerate(cases):
            with self.subTest(index=index):
                self.check_invalid(mutation)

    def test_review_flag_survives_structural_pass(self):
        self.plan['chapters'][1]['needsReview'] = True
        result = module.validate(self.plan, self.transcript)
        self.assertTrue(result['ok'])
        self.assertTrue(result['warnings'])

    def test_export_gate_blocks_unresolved_boundary_and_malformed_inputs(self):
        for chapter in self.plan['chapters']:
            chapter['needsReview']=False
        self.plan['chapters'][1]['needsReview']=True
        self.assertFalse(module.validate(self.plan,self.transcript,require_reviewed=True)['ok'])
        self.plan['chapters'][1]['needsReview']=False
        self.assertTrue(module.validate(self.plan,self.transcript,require_reviewed=True)['ok'])
        for bad in ([],None,'text'):
            self.assertFalse(module.validate(bad,self.transcript)['ok'])
        self.assertFalse(module.validate(self.plan,self.transcript,current_policy=True)['ok'])
        # A legacy two-chapter source stays readable; it is not silently padded to four.
        self.assertTrue(module.validate(self.plan,self.transcript)['ok'])

    def test_missing_review_flag_is_not_export_approval(self):
        result=module.validate(self.plan,self.transcript)
        self.assertTrue(result['ok'])  # Legacy evidence remains analyzable.
        self.assertTrue(result['warnings'])
        self.assertFalse(module.validate(self.plan,self.transcript,require_reviewed=True)['ok'])
        self.assertTrue(all('review' in warning.lower() for warning in result['warnings']))
        for chapter in self.plan['chapters']:chapter['needsReview']=False
        self.assertTrue(module.validate(self.plan,self.transcript,require_reviewed=True)['ok'])

    def test_review_flag_must_be_boolean_not_false_like(self):
        for value in ('false',0,None,[],{}):
            with self.subTest(value=value):
                plan=copy.deepcopy(self.plan);plan['chapters'][0]['needsReview']=value
                self.assertFalse(module.validate(plan,self.transcript)['ok'])

    def test_malformed_transcript_text_reports_error_without_crashing(self):
        for value in (42,None,[],{}):
            transcript=copy.deepcopy(self.transcript);transcript['segments'][0]['text']=value
            self.assertFalse(module.validate(self.plan,transcript)['ok'])


if __name__ == '__main__':
    unittest.main()
