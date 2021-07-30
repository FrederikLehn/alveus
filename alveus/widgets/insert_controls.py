import wx
import wx.lib.buttons as buttons

import _icons as ico


DEFAULT_ITEM_WIDTH = 100


def chop_text(dc, text, max_size):
    """
    Chops the input `text` if its size does not fit in `max_size`, by cutting the
    text and adding ellipsis at the end.

    :param `dc`: a `wx.DC` device context;
    :param `text`: the text to chop;
    :param `max_size`: the maximum size in which the text should fit.
    """

    # first check if the text fits with no problems
    x, y = dc.GetMultiLineTextExtent(text)

    if x <= max_size:
        return text

    for i in range(len(text)):
        s = text[:i] + '...'

        x, y = dc.GetTextExtent(s)
        last_good_length = i

        if x > max_size:
            return text[:last_good_length-1] + "..."

    return '...'


# ======================================================================================================================
# InsertControl - Subclassed into the 3 below widgets
# ======================================================================================================================
class InsertCtrl(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, label='', bitmap=wx.NullBitmap, client_data=None, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name='InsertControl'):

        super().__init__(parent, id, pos, size, style, name)

        self.custom_textctrl = CustomTextCtrl(self, -1, label=label, bitmap=bitmap, client_data=client_data)

    def Insert(self, label, bitmap=wx.NullBitmap, client_data=None):
        self.custom_textctrl.Insert(label, bitmap, client_data)

    def GetClientData(self):
        return self.custom_textctrl.GetClientData()

    def Enable(self, *args, **kwargs):
        wx.Panel.Enable(self, *args, **kwargs)
        self.Refresh()

    def Disable(self, *args, **kwargs):
        wx.Panel.Disable(*args, **kwargs)
        self.Refresh()

    def Clear(self):
        self.custom_textctrl.Clear()


# ======================================================================================================================
# ButtonInsertControl (takes multiple buttons)
# ======================================================================================================================
class ButtonsInsertCtrl(InsertCtrl):
    def __init__(self, parent, id=wx.ID_ANY, label='', bitmap=wx.NullBitmap, client_data=None, btn_bitmaps=(),
                 pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, name='ButtonsInsertControl'):

        super().__init__(parent, id, label, bitmap, client_data, pos, size, style, name)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.custom_textctrl, 1, wx.ALIGN_CENTER_VERTICAL)

        self._buttons = []
        for btn in btn_bitmaps:
            self._buttons.append(buttons.ThemedGenBitmapButton(self, -1, bitmap=btn, size=(26, 24)))
            self._buttons[-1].SetUseFocusIndicator(False)
            sizer.Add(self._buttons[-1], 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.SetSizer(sizer)
        sizer.Layout()


# ======================================================================================================================
# ArrowInsertControl
# ======================================================================================================================
class ArrowInsertCtrl(InsertCtrl):
    def __init__(self, parent, id=wx.ID_ANY, label='', bitmap=wx.NullBitmap, client_data=None, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name='ArrowInsertControl'):

        super().__init__(parent, id, label, bitmap, client_data, pos, size, style, name)

        self.arrow = buttons.ThemedGenBitmapButton(self, -1, bitmap=ico.right_arrow_16x16.GetBitmap(), size=(26, 24))
        self.arrow.SetUseFocusIndicator(False)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.arrow, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.custom_textctrl, 1, wx.ALIGN_CENTER_VERTICAL)

        self.SetSizer(sizer)
        sizer.Layout()


# ======================================================================================================================
# ArrowButtonInsertControl
# ======================================================================================================================
class ArrowButtonsInsertCtrl(InsertCtrl):
    def __init__(self, parent, id=wx.ID_ANY, label='', bitmap=wx.NullBitmap, client_data=None, btn_bitmaps=(),
                 pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, name='ArrowButtonsInsertControl'):

        super().__init__(parent, id, label, bitmap, client_data, pos, size, style, name)

        self.arrow = buttons.ThemedGenBitmapButton(self, -1, bitmap=ico.right_arrow_16x16.GetBitmap(), size=(26, 24))
        self.arrow.SetUseFocusIndicator(False)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.arrow, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.custom_textctrl, 1, wx.ALIGN_CENTER_VERTICAL)

        self._buttons = []
        for btn in btn_bitmaps:
            self._buttons.append(buttons.ThemedGenBitmapButton(self, -1, bitmap=btn, size=(26, 24)))
            self._buttons[-1].SetUseFocusIndicator(False)
            sizer.Add(self._buttons[-1], 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.SetSizer(sizer)
        sizer.Layout()


# ======================================================================================================================
# Basis of the above widgets
# ======================================================================================================================
class CustomTextCtrl(wx.Control):

    def __init__(self, parent, id=wx.ID_ANY, label='', bitmap=wx.NullBitmap, client_data=None):

        super().__init__(parent, id)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self._label = label
        self._bitmap = bitmap
        self._client_data = client_data
        self._x_shown = False
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

        self._active_close_bmp = ico.delete_16x16.GetBitmap()
        self._disabled_close_bmp = ico.delete_16x16.GetBitmap()

        self._hover_close_bmp = self._active_close_bmp
        self._pressed_close_bmp = self._active_close_bmp

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)

    def OnSize(self, event):

        event.Skip()
        self.Refresh()

    def DoGetBestSize(self):
        """
        Returns the best size for this panel, based upon the font
        assigned to this window, and the caption string
        """

        return wx.Size(DEFAULT_ITEM_WIDTH + 40, 22)

    def OnPaint(self, event):

        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

        self.DrawControl(dc)

    def DrawControl(self, dc):

        width, height = self.GetSize()
        x_start = 2

        original_brush = dc.GetBrush()
        if not self.IsEnabled():
            dc.SetPen(wx.TRANSPARENT_PEN)
            brush = wx.Brush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))
            dc.SetBackground(brush)
            dc.Clear()

            dc.SetBrush(original_brush)

        if self._bitmap.IsOk():
            bmp_y = (height - self._bitmap.GetHeight())/2 - 2
            dc.DrawBitmap(self._bitmap, x_start, bmp_y)
        else:
            bmp_y = (height - 16)/2.0-1

        x_start += 16 + 4
        remaining = width - x_start - 22

        new_text = chop_text(dc, self._label, remaining)

        text_width, text_height, descent, external_leading = dc.GetFullTextExtent(new_text, self.GetFont())
        dc.SetFont(self.GetFont())
        text_y = (height - text_height)/2.0 - 2
        dc.DrawText(new_text, x_start, text_y)

        if self._x_shown:
            x_start = width - 20
            dc.DrawBitmap(self._active_close_bmp, x_start, bmp_y, True)

    def Clear(self):
        self._label = ''
        self._bitmap = wx.NullBitmap
        self._client_data = None
        self.Refresh()

    def IsMouseOnX(self, event):

        width, height = self.GetSize()
        x_start = width - 20

        pos = event.GetPosition()
        rect = wx.Rect(x_start, 0, 20, height)
        return rect.Contains(pos)

    def OnMouseDown(self, event):

        event.Skip()

        if not self._x_shown:
            return

        if self.IsMouseOnX(event):
            self.Clear()

    def OnMouseMove(self, event):

        x_shown = self.IsMouseOnX(event)

        # only show cancel button on hover in cancel area and if an item is inserted
        if x_shown != self._x_shown and self._label:
            self._x_shown = x_shown
            self.Refresh()

    def OnLeaveWindow(self, event):

        self._x_shown = False
        self.Refresh()

    def Insert(self, label, bitmap=wx.NullBitmap, client_data=None):
        self._label = label
        self._bitmap = bitmap
        self._client_data = client_data

        self.Refresh()

    def GetClientData(self):
        return self._client_data
