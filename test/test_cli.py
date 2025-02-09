import os
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile


class CliTest(unittest.TestCase):
    def cli(self, args):
        cmd = f'cd .. && python -m audiblez.cli {args}'
        f = os.popen(cmd)
        out, ret = f.read(), f.close()
        return out, ret

    def test_help(self):
        out, ret = self.cli('--help')
        self.assertIn('af_sky', out)
        self.assertIn('usage:', out)
        self.assertEqual(ret, None)

    def test_epub(self):
        out, ret = self.cli('epub/mini.epub')
        self.assertIn('Found cover image', out)
        self.assertIn('Creating M4B file', out)
        self.assertEqual(ret, None)
        self.assertTrue(Path('../mini.m4b').exists())
        self.assertTrue(Path('../mini.m4b').stat().st_size > 256 * 1024)

    def test_epub_voice_and_output_folder(self):
        out, ret = self.cli('epub/mini.epub -v af_sky -o prova')
        self.assertIn('Found cover image', out)
        self.assertIn('Creating M4B file', out)
        self.assertEqual(ret, None)
        self.assertTrue(Path('../prova/mini.m4b').exists())
        self.assertTrue(Path('../prova/mini.m4b').stat().st_size > 256 * 1024)

    def test_md(self):
        out, ret = self.cli('markdown.md')
        self.assertIn('Creating M4B file', out)
        self.assertEqual(ret, None)
        self.assertTrue(Path('markdown.mp4').exists())
        self.assertTrue(Path('markdown.mp4').stat().st_size > 256 * 1024)

    def test_txt(self):
        content = (
            'Italy, officially the Italian Republic, is a country in Southern and Western Europe. '
            'It consists of a peninsula that extends into the Mediterranean Sea, '
            'with the Alps on its northern land border, '
            'as well as nearly 800 islands, notably Sicily and Sardinia.')
        file_name = NamedTemporaryFile('w', suffix='.txt', delete=False).write(content)
        out, ret = self.cli(file_name)
        self.assertIn('Creating M4B file', out)
        self.assertEqual(ret, None)
        self.assertTrue(Path('text.mp4').exists())
        self.assertTrue(Path('text.mp4').stat().st_size > 256 * 1024)
