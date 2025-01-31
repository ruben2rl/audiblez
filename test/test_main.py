import os
import unittest
from pathlib import Path

from kokoro import KPipeline

from audiblez import main


class MainTest(unittest.TestCase):
    def base(self, file_path, **kwargs):
        os.system('rm mini_chapter_*.wav')
        pipeline = KPipeline(lang_code='a')
        main(pipeline, file_path=file_path, voice='af_sky', pick_manually=False, speed=1, **kwargs)

    def test_1_allan_poe(self):
        Path('poe.m4b').unlink(missing_ok=True)
        os.system('rm poe_chapter_*.wav')
        self.base(file_path='../epub/poe.epub')
        self.assertTrue(Path('poe.m4b').exists())

    def test_2_mini(self):
        Path('mini.m4b').unlink(missing_ok=True)
        os.system('rm mini_chapter_*.wav')
        self.base(file_path='../epub/mini.epub')
        self.assertTrue(Path('mini.m4b').exists())

    def test_3_orwell(self):
        Path('orwell.m4b').unlink(missing_ok=True)
        os.system('rm orwell_chapter_*.wav')
        self.base(file_path='../epub/orwell.epub')
        self.assertTrue(Path('orwell.m4b').exists())
        for i in range(8):
            self.assertTrue(Path(f'orwell_chapter_{i}.wav').exists())
            self.assertTrue(Path(f'orwell_chapter_{i}.wav').stat().st_size > 300 * 1024, 'file should be larger than 300KB, surely failed')
