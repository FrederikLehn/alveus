import wx
import wx.lib.buttons as buttons

ID_RIGHT = 0
ID_LEFT = 1


class TextButtonCtrl(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, bitmap=wx.NullBitmap, side=ID_RIGHT, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name='TextButtonControl'):

        super().__init__(parent, id, pos, size, style, name)

        self.text_ctrl = wx.TextCtrl(self, wx.ID_ANY)
        self.button = buttons.ThemedGenBitmapButton(self, wx.ID_ANY, bitmap=bitmap, size=(26, 24))
        self.button.SetUseFocusIndicator(False)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        if side == ID_RIGHT:
            sizer.Add(self.text_ctrl, 1, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.button, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
        else:
            sizer.Add(self.button, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)
            sizer.Add(self.text_ctrl, 1, wx.ALIGN_CENTER_VERTICAL)

        self.SetSizer(sizer)
        sizer.Layout()

    def Enable(self, *args, **kwargs):
        wx.Panel.Enable(self, *args, **kwargs)
        self.Refresh()

    def Disable(self, *args, **kwargs):
        wx.Panel.Disable(*args, **kwargs)
        self.Refresh()

    def GetValue(self):
        return self.text_ctrl.GetValue()

    def SetValue(self, value):
        self.text_ctrl.SetValue(value)
