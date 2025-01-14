#!/usr/bin/env python3
# audiblez - A program to convert e-books into audiobooks using high-quality
# Kokoro-82M text-to-speech model.
# Distributed under the MIT License for educational purposes.
# by Claudio Santini (2025) - https://claudio.uk

import argparse
import sys
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
from pydub import AudioSegment

kokoro = Kokoro('kokoro-v0_19.onnx', 'voices.json')


def main(file_path, lang, voice):
    filename = Path(file_path).name
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
    if not has_ffmpeg:
        print('\033[91m' + 'ffmpeg not found. Please install ffmpeg to create mp3 and m4b audiobook files.' + '\033[0m')
    total_chars = sum([len(t) for t in texts])
    print('Started at:', time.strftime('%H:%M:%S'))
    print(f'Total characters: {total_chars:,}')
    print('Total words:', len(' '.join(texts).split(' ')))

    i = 1
    chapter_mp3_files = []
    for text in texts:
        if i > 8:
            continue
        chapter_filename = filename.replace('.epub', f'_chapter_{i}.wav')
        chapter_mp3_files.append(chapter_filename)
        if Path(chapter_filename).exists() or Path(chapter_filename.replace('.wav', '.mp3')).exists():
            print(f'File for chapter {i} already exists. Skipping')
            i += 1
            continue
        print(f'Reading chapter {i} ({len(text):,} characters)...')
        if i == 1:
            text = intro + '.\n\n' + text
        start_time = time.time()
        samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang=lang)
        sf.write(f'{chapter_filename}', samples, sample_rate)
        end_time = time.time()
        delta_seconds = end_time - start_time
        chars_per_sec = len(text) / delta_seconds
        print('Chapter written to', chapter_filename)
        print(f'Chapter {i} read in {delta_seconds:.2f} seconds ({chars_per_sec:.0f} characters per second)')
        remaining_chars = sum([len(t) for t in texts[i - 1:]])
        remaining_time = remaining_chars / chars_per_sec
        print(f'Estimated time remaining: {strfdelta(remaining_time)}')
        progress = int((total_chars - remaining_chars) / total_chars * 100)
        print(f'Progress: {progress}%')
        print()
        # if has_ffmpeg:
        #     convert_to_mp3(chapter_filename)
        i += 1

    if has_ffmpeg:
        create_m4b(chapter_mp3_files, filename)


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


# def convert_to_mp3(wav_file):
#     mp3_file = wav_file.replace('.wav', '.mp3')
#     print(f'In parallel, converting {wav_file} to {mp3_file}...')
#     subprocess.Popen(['ffmpeg', '-i', wav_file, mp3_file, '&& rm', wav_file, '&& echo "mp3 convertion done."'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# def create_m4b(chapter_files, filename):
#     if shutil.which('ffmpeg') is None:
#         return
#     print('Creating M4B file...')
#     filename_m4b = filename.replace('.epub', '.m4b')
#     concat_str = '|'.join(chapter_files)
#     cmd = ['ffmpeg', '-i', f'concat:{concat_str}', '-c:a', 'aac', '-b:a', '64k', '-f', 'mp4', f'{filename_m4b}']
#     print(cmd)
#     proc = subprocess.run(cmd)
#     if proc.returncode == 0:
#         print(f'{filename_m4b} created. Enjoy your audiobook.')


def create_m4b(chaptfer_files, filename):
    tmp_filename = filename.replace('.epub', '.tmp.m4a')
    if not Path(tmp_filename).exists():
        combined_audio = AudioSegment.empty()
        for wav_file in chaptfer_files:
            audio = AudioSegment.from_wav(wav_file)
            combined_audio += audio
        print('Creating M4A file...')
        combined_audio.export(tmp_filename, format="mp4", codec="aac", bitrate="64k")
    final_filename = filename.replace('.epub', '.m4b')
    print('Creating M4B file...')
    proc = subprocess.run(['ffmpeg', '-i', f'{tmp_filename}', '-c', 'copy', '-f', 'mp4', f'{final_filename}'])
    Path(tmp_filename).unlink()
    if proc.returncode == 0:
        print(f'{final_filename} created. Enjoy your audiobook.')
        print('Feel free to delete the intermediary .wav chapter files, the .m4b is all you need.')


if __name__ == '__main__':
    voices = list(kokoro.get_voices())
    voices_str = ', '.join(voices)
    epilog = 'example:\n' + \
             '  audiblez book.epub -l en-us -v af_sky'
    default_voice = 'af_sky' if 'af_sky' in voices else voices[0]
    parser = argparse.ArgumentParser(epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('epub_file_path', help='Path to the epub file')
    parser.add_argument('-l', '--lang', default='en-gb', help='Language code: en-gb, en-us, fr-fr, ja, ko, cmn')
    parser.add_argument('-v', '--voice', default=default_voice, help=f'Choose narrating voice: {voices_str}')
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    main(args.epub_file_path, args.lang, args.voice)
