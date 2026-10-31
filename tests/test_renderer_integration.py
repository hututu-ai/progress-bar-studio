"""Candidate integration checks for preset/render boundaries and bundled inputs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skill/progress-bar-studio'
SCRIPTS = SKILL / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import render_progress as renderer


class RendererIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def command(self, *args, expected=0):
        result = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return result

    def test_all_builtin_routes_round_trip_and_explicit_palette_mapping(self):
        palette = renderer.PALETTE_PRESETS['lavender']
        for style in renderer.STYLE_NAMES:
            with self.subTest(style=style):
                args = [SCRIPTS / 'preset_library.py', 'save', '--name', style,
                        '--library-dir', self.root / 'presets', '--character-mode', 'none',
                        '--style', style, '--style-variant', renderer.STYLE_NAMES[style][0],
                        '--overlay-scale', '1', '--placement', 'top', '--position-x', '0',
                        '--position-y', '0', '--sample-approved', '--final-export-approved', '--json']
                for key, value in palette.items():
                    args += ['--palette', f'{key}={value}']
                result = json.loads(self.command(*args).stdout)
                path = Path(result['preset'])
                saved = json.loads(self.command(SCRIPTS / 'preset_library.py', 'show', '--preset', path,
                                                '--require-verified', '--json').stdout)
                self.assertTrue(saved['reuseEligible'])
                self.assertEqual(saved['style']['route'], style)
                self.assertEqual(saved['palette'], palette)
                # Deliberate manual mapping. Whole preset JSON is NOT the renderer schema.
                config = renderer.demo_config(style)
                config['palette'] = saved['palette']
                config['character'] = {'mode': saved['character']['mode']}
                frame = renderer.Renderer(renderer.validate_config(config)).frame(3)
                self.assertEqual(frame.getchannel('A').getextrema(), (0, 255))
                with self.assertRaises(renderer.ConfigError):
                    renderer.validate_config(json.loads(path.read_text()))

    def test_invalid_palette_encoding_still_rejected(self):
        for value in ('#12345', '#1234567', '#123456789', '#ZZZZZZ', '#12 45678'):
            with self.subTest(value=value):
                result = self.command(SCRIPTS / 'preset_library.py', 'save', '--name', 'bad',
                    '--library-dir', self.root / 'presets', '--character-mode', 'none',
                    '--style', 'S7', '--style-variant', 'hanging-tabs', '--palette', f'shadow={value}',
                    '--overlay-scale', '1', '--placement', 'top', '--position-x', '0', '--position-y', '0',
                    '--sample-approved', '--final-export-approved', '--json', expected=2)
                self.assertNotIn('Traceback', result.stderr)
                self.assertFalse((self.root / 'presets/bad').exists())

    def test_palette_asset_matches_renderer_and_examples_are_safe_synthetic_inputs(self):
        bank = json.loads((SKILL / 'assets/palettes/reference-palettes.json').read_text())
        self.assertEqual(bank['palettes'], renderer.PALETTE_PRESETS)
        examples = sorted((SKILL / 'assets/examples').glob('*-render.json'))
        self.assertGreaterEqual(len(examples), 8)
        for path in examples:
            with self.subTest(example=path.name):
                data = json.loads(path.read_text())
                self.assertIs(data['demoLabel'], True)
                config = renderer.load_config(path)
                self.assertEqual(renderer.Renderer(config).frame(config.chapters[1].start).getchannel('A').getextrema(), (0, 255))
                result = self.command(SCRIPTS / 'render_progress.py', 'mov', path,
                    self.root / (path.stem + '.mov'), '--purpose', 'final', '--final-approved', expected=2)
                self.assertIn('synthetic labeled demo', result.stderr)
                self.assertFalse((self.root / (path.stem + '.mov')).exists())

    def test_custom_route_stays_separate_from_s7(self):
        from PIL import Image
        reference = self.root / 'reference.png'
        Image.new('RGB', (12, 12), 'white').save(reference)
        result = json.loads(self.command(SCRIPTS / 'preset_library.py', 'save', '--name', 'Custom',
            '--library-dir', self.root / 'presets', '--character-mode', 'none', '--style', 'custom',
            '--style-variant', 'reviewed-independent-design', '--style-reference', reference,
            '--palette', 'text=#112233', '--overlay-scale', '1', '--placement', 'top',
            '--position-x', '0', '--position-y', '0', '--sample-approved', '--final-export-approved', '--json').stdout)
        saved = json.loads(self.command(SCRIPTS / 'preset_library.py', 'show', '--preset', result['preset'],
                                       '--require-verified', '--json').stdout)
        self.assertEqual(saved['style']['route'], 'custom')
        data = renderer.demo_config('S7')
        data['style'] = 'custom'
        with self.assertRaises(renderer.ConfigError):
            renderer.validate_config(data)


if __name__ == '__main__':
    unittest.main()
