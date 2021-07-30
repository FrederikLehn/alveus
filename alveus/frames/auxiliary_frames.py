import wx
from pubsub import pub

from _ids import *
import _icons as ico
from frames.frame_design import ObjectDialog, GAP, INTER_GAP
import frames.property_panels as pp


# ======================================================================================================================
# GENERIC DIALOGS
# ======================================================================================================================
class MessageObjectDialog(wx.Dialog):
    def __init__(self, parent, title, icon, label):
        super().__init__(parent=parent,
                         style=wx.CAPTION | wx.CLOSE_BOX | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR)

        self.SetTitle(title)
        self.SetIcon(icon)

        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self._answer = ID_PROMPT_CANCEL  # default if cancelled by wx.CLOSE_BOX

        # custom panel -------------------------------------------------------------------------------------------------
        self.custom = wx.Panel(self.panel)
        self.custom.SetBackgroundColour(wx.WHITE)

        # text and icon ------------------------------------------------------------------------------------------------
        message = wx.StaticText(self.custom, label=label)
        bmp = wx.ArtProvider.GetBitmap(wx.ART_WARNING, wx.ART_MESSAGE_BOX, (32, 32))
        icon = wx.StaticBitmap(self.custom, -1, bmp)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add((10, 10))
        vbox.Add(message)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add((10, 10), 1)
        hbox.Add(icon)
        hbox.Add((10, 10))
        hbox.Add(vbox)
        hbox.Add((10, 10), 1)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add((10, 10), 1)
        box.Add(hbox, 0, wx.EXPAND)
        box.Add((10, 10), 2)

        self.custom.SetSizer(box)

        # buttons ------------------------------------------------------------------------------------------------------
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)

    # external functions -----------------------------------------------------------------------------------------------
    def GetAnswer(self):
        return self._answer

    def Realize(self):
        self.sizer.Add(self.custom, 1, wx.EXPAND)
        self.sizer.Add(self.button_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, GAP)
        self.panel.SetSizer(self.sizer)
        self.sizer.Fit(self)


class YesNoItemDialog(MessageObjectDialog):
    def __init__(self, parent, title, icon, label):
        super().__init__(parent, title, icon, label)

        # buttons ------------------------------------------------------------------------------------------------------
        self.yes_button = wx.Button(self.panel, label='Yes')
        self.no_button = wx.Button(self.panel, label='No')

        self.button_sizer.Add(self.yes_button, 1, wx.RIGHT, GAP)
        self.button_sizer.Add(self.no_button, 1)

        # setting layout -----------------------------------------------------------------------------------------------
        self.Realize()
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.yes_button.Bind(wx.EVT_BUTTON, self.OnYesButton)
        self.no_button.Bind(wx.EVT_BUTTON, self.OnNoButton)

    # events -----------------------------------------------------------------------------------------------------------
    def OnYesButton(self, event):
        self._answer = ID_PROMPT_YES
        self.Close(True)

    def OnNoButton(self, event):
        self._answer = ID_PROMPT_NO
        self.Close(True)


class YesToAllNoItemsDialog(MessageObjectDialog):
    def __init__(self, parent, title, icon, label):
        super().__init__(parent, title, icon, label)

        # buttons ------------------------------------------------------------------------------------------------------
        self.yestoall_button = wx.Button(self.panel, label='Yes to all')
        self.yes_button = wx.Button(self.panel, label='Yes')
        self.no_button = wx.Button(self.panel, label='No')
        self.cancel_button = wx.Button(self.panel, label='Cancel')

        self.button_sizer.Add(self.yestoall_button, 1, wx.RIGHT, GAP)
        self.button_sizer.Add(self.yes_button, 1, wx.RIGHT, GAP)
        self.button_sizer.Add(self.no_button, 1, wx.RIGHT, GAP)
        self.button_sizer.Add(self.cancel_button, 1)

        # setting layout -----------------------------------------------------------------------------------------------
        self.Realize()
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.yestoall_button.Bind(wx.EVT_BUTTON, self.OnYestoallButton)
        self.yes_button.Bind(wx.EVT_BUTTON, self.OnYesButton)
        self.no_button.Bind(wx.EVT_BUTTON, self.OnNoButton)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.OnCancelButton)

    # events -----------------------------------------------------------------------------------------------------------
    def OnYestoallButton(self, event):
        self._answer = ID_PROMPT_YESTOALL
        self.Close(True)

    def OnYesButton(self, event):
        self._answer = ID_PROMPT_YES
        self.Close(True)

    def OnNoButton(self, event):
        self._answer = ID_PROMPT_NO
        self.Close(True)

    def OnCancelButton(self, event):
        self._answer = ID_PROMPT_CANCEL
        self.Close(True)


# ======================================================================================================================
# CUSTOM DIALOGS
# ======================================================================================================================
class DuplicateFrame(ObjectDialog):
    def __init__(self, parent, entity_mgr, object_menu_page, item):
        super().__init__(parent, '')

        self._entity_mgr = entity_mgr
        self._object_menu_page = object_menu_page
        self._entity = entity_mgr.GetEntity(*item.GetData().GetPointer())
        self._item = item

        self.duplicates = pp.DuplicatePanel(self.custom)

        self.custom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.InitUI()
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_BUTTON, self.OnOKButton, self.ok_button)

    def InitUI(self):
        self.SetIcon(ico.field_16x16.GetIcon())
        self.SetTitle('Duplicate - {}'.format(self._item.GetText()))

        if not self._entity.AllowControl():
            self.duplicates.EnableCtrls(False, from_=1)

        self.custom_sizer.Add(self.duplicates, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.custom.SetSizer(self.custom_sizer)

        self.Realize()

    def OnOKButton(self, event):
        n, control = self.duplicates.Get()

        parent = self._item.GetParent()

        for i in range(n):

            duplicate = self._entity_mgr.CreateDuplicate(self._entity, control)
            duplicate.SetName('{}_{}'.format(duplicate.GetName(), i + 1))

            self._object_menu_page.AddEntity(parent, duplicate)
            pub.sendMessage('entity_added', id_=duplicate.GetId(), type_=duplicate.GetType())

        self.Close(True)


class DeleteItemDialog(YesNoItemDialog):
    def __init__(self, parent, item_text):
        super().__init__(parent, 'Delete', ico.delete_16x16.GetIcon(),
                         'Are you sure you want to delete \'{}\'?'.format(item_text))


class DeleteItemsDialog(YesToAllNoItemsDialog):
    def __init__(self, parent, item_text):
        super().__init__(parent, 'Delete', ico.delete_16x16.GetIcon(),
                         'Are you sure you want to delete \'{}\'?'.format(item_text))


class MoveFolderDialog(YesNoItemDialog):
    def __init__(self, parent, item_text):
        super().__init__(parent, 'Move', ico.folder_closed_16x16.GetIcon(),
                         'Do you want to drop it into \'{}\'?'.format(item_text))