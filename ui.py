import wx
import wx.lib.mixins.listctrl as listmix
import os


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(800, 600))

        self.create_menu()
        self.create_layout()

        self.Centre()
        self.Show(True)

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

    def create_layout(self):
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Left Panel (Checkboxes and List)
        left_panel = wx.Panel(self)
        left_sizer = wx.BoxSizer(wx.VERTICAL)

        open_button = wx.Button(left_panel, label="Open EPUB File")
        open_button.Bind(wx.EVT_BUTTON, self.on_open)
        left_sizer.Add(open_button, 0, wx.ALL, 5)

        # Checkboxes
        self.checkbox1 = wx.CheckBox(left_panel, label="Option 1")
        self.checkbox2 = wx.CheckBox(left_panel, label="Option 2")
        left_sizer.Add(self.checkbox1, 0, wx.ALL, 5)
        left_sizer.Add(self.checkbox2, 0, wx.ALL, 5)

        # Simple ListCtrl (You can customize it further)
        self.list_ctrl = wx.ListCtrl(left_panel, style=wx.LC_REPORT)
        self.list_ctrl.InsertColumn(0, "Item")  # Example column
        left_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)  # 1 for proportional sizing

        left_panel.SetSizer(left_sizer)
        main_sizer.Add(left_panel, 0, wx.EXPAND | wx.ALL, 5)  # 0 for not proportional sizing

        # Right Panel (Table - using a simple ListCtrl for now)
        right_panel = wx.Panel(self)
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        self.table_ctrl = MyListCtrl(right_panel, style=wx.LC_REPORT)  # Use the custom ListCtrl
        right_sizer.Add(self.table_ctrl, 1, wx.EXPAND | wx.ALL, 5)  # 1 for proportional sizing

        right_panel.SetSizer(right_sizer)
        main_sizer.Add(right_panel, 1, wx.EXPAND | wx.ALL, 5)  # 1 for proportional sizing

        self.SetSizer(main_sizer)
        self.Layout()

    def on_open(self, event):
        with wx.FileDialog(self, "Open EPUB File", wildcard="*.epub", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return  # User cancelled

            filepath = dialog.GetPath()
            if filepath:
                print(f"Opening file: {filepath}")  # Do something with the filepath (e.g., parse the EPUB)
                # Example: Add the file name to the list control
                self.list_ctrl.Append([os.path.basename(filepath)])

                # Add a row to the table (example)
                self.table_ctrl.Append([None, "EPUB File", os.path.basename(filepath)])

    def on_exit(self, event):
        self.Close()


class MyListCtrl(wx.ListCtrl, listmix.ColumnSorterMixin, listmix.CheckListCtrlMixin):
    def __init__(self, parent, *args, **kw):
        wx.ListCtrl.__init__(self, parent, *args, **kw)
        listmix.CheckListCtrlMixin.__init__(self)
        # listmix.ColumnSorterMixin.__init__(self, 3)
        self.InsertColumn(0, "Inlcude in Audiobook")
        self.InsertColumn(1, "Column 2")
        self.InsertColumn(2, "Column 3")
        # self.CheckItem(0, True)
        self.SetColumnWidth(0, 150)  # Example width
        self.SetColumnWidth(1, 150)
        self.SetColumnWidth(2, 150)

    def OnCheckItem(self, index, flag):
        "flag is True if the item was checked, False if unchecked"
        pass

    def GetListCtrl(self):  # For ColumnSorterMixin
        return self


if __name__ == '__main__':
    app = wx.App(False)
    frame = MainWindow(None, "EPUB Reader")
    frame.Show(True)
    app.MainLoop()
