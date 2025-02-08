import io
import os
import subprocess
import numpy as np
import soundfile
import wx
import wx.lib.newevent
import wx.lib.mixins.listctrl as listmix
from wx.lib.scrolledpanel import ScrolledPanel
from PIL import Image
import threading

from voices import voices, flags

EventCoreStarted, EVENT_CORE_STARTED = EVT_MEDIA_STARTED = wx.lib.newevent.NewEvent()


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        w = 1600
        super().__init__(parent, title=title, size=(w, w * 3 // 4))
        self.chapters_panel = None
        self.preview_threads = []
        self.selected_chapter = None
        self.selected_book = None

        self.create_menu()
        self.create_layout()
        self.Centre()
        self.Show(True)
        self.open_epub('../epub/solenoid.epub')

    def create_menu(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        open_item = wx.MenuItem(file_menu, wx.ID_OPEN, "&Open\tCtrl+O")
        file_menu.Append(open_item)
        self.Bind(wx.EVT_MENU, self.on_open, open_item)  # Bind the event

        exit_item = wx.MenuItem(file_menu, wx.ID_EXIT, "&Exit\tCtrl+Q")
        file_menu.Append(exit_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)

        menubar.Append(file_menu, "&File")
        self.SetMenuBar(menubar)

        self.Bind(EVENT_CORE_STARTED, self.event_core_started)

    def event_core_started(self, event):
        print('EVENT_CORE_STARTED')

    def create_layout(self):
        # Panels layout looks like this:
        # splitter
        #   splitter_left
        #   splitter_right
        #       center_panel
        #       right_panel
        #           book_info_panel_box
        #               book_info_panel
        #                   cover_bitmap
        #                   book_details_panel
        #           param_panel_box

        top_panel = wx.Panel(self)
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_panel.SetSizer(top_sizer)

        # Open Epub button
        open_epub_button = wx.Button(top_panel, label="📁 Open EPUB")
        open_epub_button.Bind(wx.EVT_BUTTON, self.on_open)
        top_sizer.Add(open_epub_button, 0, wx.ALL, 5)

        # About button
        help_button = wx.Button(top_panel, label="ℹ️ About")
        help_button.Bind(wx.EVT_BUTTON, lambda event: self.about_dialog())
        top_sizer.Add(help_button, 0, wx.ALL, 5)

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.main_sizer)

        self.splitter = wx.SplitterWindow(self, -1, wx.Point(10, 0), wx.Size(900, -1), wx.SP_3D)
        self.splitter.SetMinimumPaneSize(50)
        self.main_sizer.Add(top_panel, 0, wx.ALL | wx.EXPAND, 5)
        self.main_sizer.Add(self.splitter, 1, wx.EXPAND)

    def create_layout_for_ebook(self, splitter):
        splitter_left = wx.Panel(splitter, -1)
        splitter_right = wx.Panel(self.splitter)
        self.splitter_left, self.splitter_right = splitter_left, splitter_right

        # self.main_sizer.Add(splitter_left, 1, wx.ALL | wx.EXPAND, 5)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)
        # self.left_sizer.SetMinSize(50, 0)
        splitter_left.SetSizer(self.left_sizer)

        # add center panel with large text area
        self.center_panel = wx.Panel(splitter_right)
        self.center_sizer = wx.BoxSizer(wx.VERTICAL)
        self.center_panel.SetSizer(self.center_sizer)
        self.text_area = wx.TextCtrl(self.center_panel, style=wx.TE_MULTILINE, size=(200, -1))
        font = wx.Font(14, wx.MODERN, wx.NORMAL, wx.NORMAL)
        self.text_area.SetFont(font)
        # On text change, update the extracted_text attribute of the selected_chapter:
        self.text_area.Bind(wx.EVT_TEXT, lambda event: setattr(self.selected_chapter, 'extracted_text', self.text_area.GetValue()))

        label = wx.StaticText(self.center_panel, label="View / Edit Chapter content:")
        preview_button = wx.Button(self.center_panel, label="🔊 Preview")
        preview_button.Bind(wx.EVT_BUTTON, self.on_preview_chapter)

        self.center_sizer.Add(label, 0, wx.ALL, 5)
        self.center_sizer.Add(preview_button, 0, wx.ALL, 5)
        self.center_sizer.Add(self.text_area, 1, wx.ALL | wx.EXPAND, 5)

        splitter_right_sizer = wx.BoxSizer(wx.HORIZONTAL)
        splitter_right.SetSizer(splitter_right_sizer)

        self.create_right_panel(splitter_right)

        splitter_right_sizer.Add(self.center_panel, 1, wx.ALL | wx.EXPAND, 5)
        splitter_right_sizer.Add(self.right_panel, 1, wx.ALL, 5)

        splitter.SplitVertically(splitter_left, splitter_right)
        # self.Layout()

    def about_dialog(self):
        msg = "A simple tool to generate audiobooks from EPUB files using Kokoro-82M models\n\n" + \
              "by Claudio Santini 2025\nand many contributors.\n\n"
        wx.MessageBox(msg, "Audiblez")

    def create_right_panel(self, splitter_right):
        # right_panel is a vertical layout with book info on top and parameters on the bottom
        self.right_panel = wx.Panel(splitter_right)
        self.right_panel.SetSize((500, -1))
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_panel.SetSizer(self.right_sizer)

        self.book_info_panel_box = wx.Panel(self.right_panel, style=wx.SUNKEN_BORDER)
        book_info_panel_box_sizer = wx.StaticBoxSizer(wx.VERTICAL, self.book_info_panel_box, "Book Details")
        self.book_info_panel_box.SetSizer(book_info_panel_box_sizer)
        self.right_sizer.Add(self.book_info_panel_box, 1, wx.ALL | wx.EXPAND, 5)

        self.book_info_panel = wx.Panel(self.book_info_panel_box, style=wx.BORDER_NONE)
        self.book_info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.book_info_panel.SetSizer(self.book_info_sizer)
        book_info_panel_box_sizer.Add(self.book_info_panel, 1, wx.ALL | wx.EXPAND, 5)

        # Add cover image
        self.cover_bitmap = wx.StaticBitmap(self.book_info_panel, -1)
        self.book_info_sizer.Add(self.cover_bitmap, 0, wx.ALL, 5)
        self.book_info_panel.SetSize(500, -1)

        self.cover_bitmap.Refresh()
        self.book_info_panel.Refresh()
        self.book_info_panel.Layout()
        self.cover_bitmap.Layout()

        self.create_book_details_panel()
        self.create_param_panel()

    def create_book_details_panel(self):
        book_details_panel = wx.Panel(self.book_info_panel)
        book_details_sizer = wx.GridBagSizer(10, 10)
        book_details_panel.SetSizer(book_details_sizer)
        self.book_info_sizer.Add(book_details_panel, 1, wx.ALL, 5)

        # Add title
        title_label = wx.StaticText(book_details_panel, label="Title:")
        title_text = wx.StaticText(book_details_panel, label=self.selected_book_title)
        book_details_sizer.Add(title_label, pos=(0, 0), flag=wx.ALL, border=5)
        book_details_sizer.Add(title_text, pos=(0, 1), flag=wx.ALL, border=5)

        # Add Author
        author_label = wx.StaticText(book_details_panel, label="Author:")
        author_text = wx.StaticText(book_details_panel, label=self.selected_book_author)
        book_details_sizer.Add(author_label, pos=(1, 0), flag=wx.ALL, border=5)
        book_details_sizer.Add(author_text, pos=(1, 1), flag=wx.ALL, border=5)

        # Add Total length
        length_label = wx.StaticText(book_details_panel, label="Total Length:")
        if not hasattr(self, 'document_chapters'):
            total_len = 0
        else:
            total_len = sum([len(c.extracted_text) for c in self.document_chapters])
        length_text = wx.StaticText(book_details_panel, label=f'{total_len:,} characters')
        book_details_sizer.Add(length_label, pos=(2, 0), flag=wx.ALL, border=5)
        book_details_sizer.Add(length_text, pos=(2, 1), flag=wx.ALL, border=5)

    def create_param_panel(self):
        # Add on the bottom right side, 3 dropdowns and a button
        self.param_panel_box = wx.Panel(self.right_panel, style=wx.SUNKEN_BORDER)
        param_panel_box_sizer = wx.StaticBoxSizer(wx.VERTICAL, self.param_panel_box, "Audiobook Parameters")
        self.param_panel_box.SetSizer(param_panel_box_sizer)

        self.param_panel = wx.Panel(self.param_panel_box, style=wx.SUNKEN_BORDER)
        param_panel_box_sizer.Add(self.param_panel, 1, wx.ALL | wx.EXPAND, 5)
        self.right_sizer.Add(self.param_panel_box, 1, wx.ALL | wx.EXPAND, 5)
        self.param_sizer = wx.GridBagSizer(10, 10)
        self.param_panel.SetSizer(self.param_sizer)

        border = 10

        # Create a list of voices with flags
        flag_and_voice_list = []
        for code, l in voices.items():
            for v in l:
                flag_and_voice_list.append(f'{flags[code]} {v}')

        voice_label = wx.StaticText(self.param_panel, label="Voice:")
        default_voice = flag_and_voice_list[0]
        self.selected_voice = default_voice
        voice_dropdown = wx.ComboBox(self.param_panel, choices=flag_and_voice_list, value=default_voice)
        voice_dropdown.Bind(wx.EVT_COMBOBOX, self.on_select_voice)
        self.param_sizer.Add(voice_label, pos=(0, 0), flag=wx.ALL, border=border)
        self.param_sizer.Add(voice_dropdown, pos=(0, 1), flag=wx.ALL, border=border)

        # Add dropdown for speed
        speed_label = wx.StaticText(self.param_panel, label="Speed:")
        speed_text_input = wx.TextCtrl(self.param_panel, value="1.0")
        self.selected_speed = '1.0'
        speed_text_input.Bind(wx.EVT_TEXT, self.on_select_speed)
        self.param_sizer.Add(speed_label, pos=(1, 0), flag=wx.ALL, border=border)
        self.param_sizer.Add(speed_text_input, pos=(1, 1), flag=wx.ALL, border=border)

        # Add Start button
        start_button = wx.Button(self.param_panel, label="🚀 Start Audiobook Synthesis")
        start_button.Bind(wx.EVT_BUTTON, self.on_start)
        self.param_sizer.Add(start_button, pos=(2, 0), span=(1, 2), flag=wx.ALL, border=border)
        return self.param_panel

    def on_selected_chapter(self, chapter):
        def handle_event(event):
            print('Selecting chapter', chapter, len(chapter.extracted_text))
            self.selected_chapter = chapter
            self.text_area.SetValue(chapter.extracted_text)

        return handle_event

    def on_select_voice(self, event):
        print('Selected voice', event.GetString())
        self.selected_voice = event.GetString()

    def on_select_speed(self, event):
        speed = float(event.GetString())
        print('Selected speed', speed)
        self.selected_speed = speed

    def open_epub(self, file_path):
        # Cleanup previous layout
        if hasattr(self, 'selected_book'):
            self.splitter.DestroyChildren()

        self.selected_file_path = file_path
        print(f"Opening file: {file_path}")  # Do something with the filepath (e.g., parse the EPUB)

        from ebooklib import epub
        from core import find_document_chapters_and_extract_texts, find_good_chapters, find_cover
        book = epub.read_epub(file_path)
        meta_title = book.get_metadata('DC', 'title')
        self.selected_book_title = meta_title[0][0] if meta_title else ''
        meta_creator = book.get_metadata('DC', 'creator')
        self.selected_book_author = meta_creator[0][0] if meta_creator else ''
        self.selected_book = book

        self.document_chapters = find_document_chapters_and_extract_texts(book)
        good_chapters = find_good_chapters(self.document_chapters)

        self.create_layout_for_ebook(self.splitter)

        # Update Cover
        cover = find_cover(book)
        pil_image = Image.open(io.BytesIO(cover.content))
        wx_img = wx.EmptyImage(pil_image.size[0], pil_image.size[1])
        wx_img.SetData(pil_image.convert("RGB").tobytes())
        w = 200
        wx_img.Rescale(w, int(w * wx_img.GetHeight() / wx_img.GetWidth()))
        self.cover_bitmap.SetBitmap(wx_img.ConvertToBitmap())

        # Update book info
        # TODO

        chapters_panel = self.create_chapters_panel(good_chapters)

        #  chapters_panel to left_sizer, or replace if it exists already
        if self.chapters_panel:
            self.left_sizer.Replace(self.chapters_panel, chapters_panel)
            self.chapters_panel.Destroy()
            self.chapters_panel = chapters_panel
        else:
            self.left_sizer.Add(chapters_panel, 1, wx.ALL | wx.EXPAND, 5)
            self.chapters_panel = chapters_panel

        # These two are very important:
        self.splitter_right.Layout()
        self.splitter_left.Layout()

    def create_chapters_panel(self, good_chapters):
        # Create a chapters_panel with chapters_grid layout and scrollable
        chapters_panel = ScrolledPanel(self.splitter_left, -1, style=wx.TAB_TRAVERSAL | wx.SUNKEN_BORDER)
        chapters_panel.SetupScrolling(scroll_x=False, scroll_y=True)
        chapters_grid = wx.GridBagSizer(5, 5)
        self.chapters_grid = chapters_grid
        chapters_panel.SetSizer(chapters_grid)
        chapters_panel.SetScrollRate(10, 10)

        # Add title
        title_text = wx.StaticText(chapters_panel, label=f"Select chapters to include in the audiobook:")
        chapters_grid.Add(title_text, pos=(0, 0), flag=wx.ALL, border=5, span=(1, 3))

        # Add row for each chapter, add a row with a checkbox (with the chapter_title) and a button to play the chapter
        i = 1
        for chapter in self.document_chapters:
            chapter_title = chapter.get_name().replace('.xhtml', '').replace('xhtml/', '').replace('.html', '').replace('Text/', '')
            chapter.checkbox = wx.CheckBox(chapters_panel, label=chapter_title)
            chapter.is_selected = (chapter in good_chapters)
            chapter.checkbox.SetValue(chapter.is_selected)
            chapter.checkbox.Bind(wx.EVT_CHECKBOX, lambda event: setattr(chapter, 'is_selected', event.IsChecked()))
            chapters_grid.Add(chapter.checkbox, pos=(i, 0), flag=wx.ALL, border=5)

            # Add label with chapter size in characters
            chapter_size_label = wx.StaticText(chapters_panel, label=f"({len(chapter.extracted_text):,} chars)")
            chapters_grid.Add(chapter_size_label, pos=(i, 1), flag=wx.ALL, border=5)

            view_button = wx.Button(chapters_panel, label="📝 Edit")
            view_button.Bind(wx.EVT_BUTTON, self.on_selected_chapter(chapter))
            chapters_grid.Add(view_button, pos=(i, 2), flag=wx.ALL, border=5)

            # add preview button
            # preview_button = wx.Button(chapters_panel, label="🔊 Preview")
            # preview_button.chapter = chapter
            # preview_button.Bind(wx.EVT_BUTTON, self.on_preview_chapter(chapter))
            # chapters_grid.Add(preview_button, pos=(i, 3), flag=wx.ALL, border=5)

            # Add divier line:
            # line = wx.StaticLine(chapters_panel)
            # chapters_grid.Add(line, pos=(i + 1, 0), span=(1, 3), flag=wx.EXPAND | wx.ALL, border=5)

            i += 1
        return chapters_panel

    def get_selected_voice(self):
        return self.selected_voice.split(' ')[1]

    def get_selected_speed(self):
        return float(self.selected_speed)

    # def reset_play_button_init_state(self, button):
    #     button.SetLabel("🔊 Preview")
    #     button.Bind(wx.EVT_BUTTON, self.on_preview_chapter(button.chapter))

    def on_preview_chapter(self, event):
        lang_code = self.get_selected_voice()[0]
        button = event.GetEventObject()
        button.SetLabel("⏳")
        button.Disable()

        def generate_preview():
            import core
            from kokoro import KPipeline
            pipeline = KPipeline(lang_code=lang_code)
            core.load_spacy()
            text = self.selected_chapter.extracted_text[:300]
            if len(text) == 0: return
            audio_segments = core.gen_audio_segments(
                pipeline,
                text,
                voice=self.get_selected_voice(),
                speed=self.get_selected_speed())
            final_audio = np.concatenate(audio_segments)
            soundfile.write('preview.wav', final_audio, core.sample_rate)
            # TODO: https://www.blog.pythonlibrary.org/2010/07/24/wxpython-creating-a-simple-media-player/
            cmd = ['ffplay', '-autoexit', '-nodisp', 'preview.wav']
            # subprocess.run(cmd)
            play_proc = subprocess.Popen(' '.join(cmd), stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
            button.SetLabel("🔊 Preview")
            button.Enable()

        if len(self.preview_threads) > 0:
            for thread in self.preview_threads:
                thread.join()
            self.preview_threads = []
        thread = threading.Thread(target=generate_preview)
        thread.start()
        self.preview_threads.append(thread)

    def on_start(self, event):
        file_path = self.selected_file_path
        voice = self.selected_voice.split(' ')[1]  # Remove the flag
        speed = float(self.selected_speed)
        selected_chapters = [chapter for chapter in self.document_chapters if chapter.is_selected]
        print('Starting Audiobook Synthesis', dict(file_path=file_path, voice=voice, pick_manually=False, speed=speed))
        self.core_thread = CoreThread(params=dict(
            file_path=file_path, voice=voice, pick_manually=False, speed=speed, selected_chapters=selected_chapters))
        self.core_thread.start()

    def on_open(self, event):
        with wx.FileDialog(self, "Open EPUB File", wildcard="*.epub", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return  # User cancelled

            file_path = dialog.GetPath()
            if not file_path:
                print('No filepath?')
                return
            wx.CallAfter(self.open_epub, file_path)

    def on_exit(self, event):
        self.Close()


class CoreThread(threading.Thread):
    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        # wx.PostEvent(wx.GetApp().GetTopWindow(), wx.PyCommandEvent(EVENT_CORE_STARTED))
        import core
        core.main(**self.params)


class TableCtrl(wx.ListCtrl, listmix.ColumnSorterMixin, listmix.CheckListCtrlMixin):
    def __init__(self, parent, *args, **kw):
        wx.ListCtrl.__init__(self, parent, *args, **kw)
        listmix.CheckListCtrlMixin.__init__(self)
        # listmix.ColumnSorterMixin.__init__(self, 3)
        self.InsertColumn(0, "Inlcude in Audiobook")
        self.InsertColumn(1, "Chapter Name")
        self.InsertColumn(2, "Chapter Length")
        self.InsertColumn(3, "View / Edit")
        self.SetColumnWidth(0, 50)
        self.SetColumnWidth(1, 150)
        self.SetColumnWidth(2, 150)
        self.SetColumnWidth(3, 50)

    def OnCheckItem(self, index, flag):
        "flag is True if the item was checked, False if unchecked"
        pass

    def GetListCtrl(self):  # For ColumnSorterMixin
        return self


def main():
    print('Starting GUI...')
    app = wx.App(False)
    frame = MainWindow(None, "Audiblez - Generate Audiobooks from E-books")
    frame.Show(True)
    frame.Layout()
    app.SetTopWindow(frame)
    print('Done.')
    app.MainLoop()


if __name__ == '__main__':
    main()
