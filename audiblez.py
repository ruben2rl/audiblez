# audiblez - A program to convert e-books into audiobooks using high-quality
# Kokoro-82M text-to-speech model.
# Distributed under the MIT License for educational purposes.
# by Claudio Santini (2025) - https://claudio.uk

import argparse
import time
import shutil
import subprocess
import soundfile as sf
import ebooklib
import warnings
from pathlib import Path
from string import Formatter
from bs4 import BeautifulSoup
from kokoro_onnx import Kokoro
from ebooklib import epub

kokoro = Kokoro('kokoro-v0_19.onnx', 'voices.json')


def main(file_path, lang, voice):
    file_name = Path(file_path).name
    with warnings.catch_warnings():
        book = epub.read_epub(file_path)
    title = book.get_metadata('DC', 'title')[0][0]
    creator = book.get_metadata('DC', 'creator')[0][0]
    intro = f'{title} by {creator}'
    print(intro)
    chapters = find_chapters(book)
    print([c.get_name() for c in chapters])
    texts = extract_texts(chapters)
    has_ffmpeg = shutil.which('ffmpeg') is not None
    use_fmmpeg = has_ffmpeg and not args.wav

    i = 1
    for text in texts:
        chapter_filename = file_name.lower().replace('.epub', f'_chapter_{i}.wav')
        if Path(chapter_filename).exists() or Path(chapter_filename.replace('.wav', '.mp3')).exists():
            print(f'File for chapter {i} already exists. Skipping')
            i += 1
            continue
        print(f'Reading chapter {i} ({len(text):,} characters)...')
        start_time = time.time()
        samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang=lang)
        sf.write(f'{chapter_filename}', samples, sample_rate)
        end_time = time.time()
        delta_seconds = end_time - start_time
        charters_per_second = len(text) / delta_seconds
        print('Chapter written to', chapter_filename)
        print(f'Chapter {i} read in {delta_seconds:.2f} seconds ({charters_per_second:.0f} charters per second')
        remaining_characters = sum([len(t) for t in texts[i - 1:]])
        remaining_time = remaining_characters / charters_per_second
        print(f'Estimated time remaining: {strfdelta(remaining_time)}')
        print()
        if use_fmmpeg:
            print(f'In parallel, converting chapter {i} to mp3...')
            convert_to_mp3(chapter_filename)
        i += 1


def extract_texts(chapters):
    texts = []
    for chapter in chapters:
        xml = chapter.get_body_content()
        soup = BeautifulSoup(xml, features='lxml')
        chapter_text = ''
        html_content_tags = ['title', 'p', 'h1', 'h2', 'h3', 'h4']
        for child in soup.find_all(html_content_tags):
            inner_text = child.text.strip() if child.text else ""
            if inner_text:
                chapter_text += inner_text + '\n'
        texts.append(chapter_text)
    return texts


def find_chapters(book, verbose=False):
    is_chapter = lambda c: 'chapter' in c.get_name().lower() or 'part' in c.get_name().lower()
    chapters = [c for c in book.get_items() if c.get_type() == ebooklib.ITEM_DOCUMENT and is_chapter(c)]
    if verbose:
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                print((item.get_name(), len(item.get_body_content()), 'YES' if item in chapters else '-'))
    return chapters


def strfdelta(tdelta, fmt='{D:02}d {H:02}h {M:02}m {S:02}s'):
    remainder = int(tdelta)
    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ('W', 'D', 'H', 'M', 'S')
    constants = {'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            values[field], remainder = divmod(remainder, constants[field])
    return f.format(fmt, **values)


def convert_to_mp3(wav_file):
    if shutil.which('ffmpeg') is None:
        print('ffmpeg not found. Please install ffmpeg to convert .wav files to .mp3')
        return
    mp3_file = wav_file.replace('.wav', '.mp3')
    print(f'Converting {wav_file} to {mp3_file}...')
    subprocess.Popen(['ffmpeg', '-i', wav_file, mp3_file, ' && rm ', wav_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


if __name__ == '__main__':
    voices = list(kokoro.get_voices())
    voices_str = ', '.join(voices)
    epilog = 'example:\n' + \
             '  audiblez book.epub -l en-us -v af_sky'
    parser = argparse.ArgumentParser(epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('epub_file_path', help='Path to the epub file')
    parser.add_argument('-l', '--lang', default='en-gb', help='Language code: en-gb, en-us, fr-fr, ja, ko, cmn')
    parser.add_argument('-v', '--voice', default=voices[0], help=f'Choose narrating voice: {voices_str}')
    parser.add_argument('-w', '--wav', help="Don't convert to .mp3, just create .wav files", action='store_true')
    args = parser.parse_args()
    main(args.epub_file_path, args.lang, args.voice)
