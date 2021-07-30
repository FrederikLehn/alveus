import wx
from wx.lib.fancytext import StaticFancyText

from utilities import Latex2HTML

VGAP = 10
HGAP = 20
GAP = 4
INTRA_GAP = 4
INTER_GAP = 2
FLEX_GAP = 3
SMALL_GAP = 2
BTN_SIZE = 26


def String2TextCtrl(parent, text):
    # returns a wx.TextCtrl if text does not contain either a ^{} or a _{}
    # else returns a StaticFancyText with sub, super
    text, fancy = Latex2HTML(text)

    if fancy:
        return StaticFancyText(parent, wx.ID_ANY, text)
    else:
        return wx.StaticText(parent, label=text)


class PropertySizer(wx.FlexGridSizer):
    def __init__(self, rows, cols):
        super().__init__(rows, cols, vgap=VGAP, hgap=FLEX_GAP)

        self._skip_units = False if cols == 3 else True

    def AddCtrl(self, parent, ctrl, label=None, unit=None):

        if label is None:
            label = String2TextCtrl(parent, ctrl.GetFrameLabel())

        elif isinstance(label, str):
            label = String2TextCtrl(parent, label)

        label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)

        if self._skip_units:

            self.AddMany([(label_sizer, 0, wx.EXPAND), (ctrl, 1, wx.EXPAND | wx.ALL, FLEX_GAP)])

        else:

            if unit is None:
                unit = ctrl.GetUnit()

            if isinstance(unit, str):
                unit = String2TextCtrl(parent, unit)
            elif unit is None:
                unit = wx.StaticText(parent, label='')

            unit_sizer = wx.BoxSizer(wx.HORIZONTAL)
            unit_sizer.Add(unit, 0, wx.ALIGN_CENTER_VERTICAL)

            self.AddMany([(label_sizer, 0, wx.EXPAND), (ctrl, 1, wx.EXPAND | wx.ALL, FLEX_GAP), (unit_sizer, 0, wx.EXPAND)])


class AlignedFlexSizer(wx.FlexGridSizer):
    def __init__(self, *args, grow_col=1):

        row = len(args[0])
        col = len(args)

        super().__init__(row, col, vgap=VGAP, hgap=FLEX_GAP)

        for ctrls in zip(*args):

            for i, ctrl in enumerate(ctrls):

                if i != grow_col:
                    sizer = wx.BoxSizer(wx.HORIZONTAL)
                    sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
                    self.Add(sizer, 0, wx.EXPAND)

                else:
                    self.Add(ctrl, 1, wx.EXPAND | wx.ALL, FLEX_GAP)

        if grow_col is not None:
            self.AddGrowableCol(grow_col, 1)


class SeparatorSizer(wx.BoxSizer):
    def __init__(self, parent, label='', bitmap=None):
        super().__init__(orient=wx.HORIZONTAL)

        if bitmap is not None:
            self.Add(wx.StaticBitmap(parent, wx.ID_ANY, bitmap), 0, wx.ALL & ~wx.LEFT, GAP)

        self.Add(wx.StaticText(parent, label=label), 0, wx.ALL & ~wx.LEFT, GAP)
        self.Add(wx.StaticLine(parent), 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, GAP)


class SectionSeparator(wx.Panel):
    def __init__(self, parent, label='', bitmap=None, checkbox=False):
        super().__init__(parent)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        if checkbox:
            self.checkbox = wx.CheckBox(self, label='')
            sizer.Add(self.checkbox, 0, wx.ALL & ~wx.LEFT, GAP)

        else:
            self.checkbox = None

        sizer.Add(SeparatorSizer(self, label, bitmap), 1, wx.EXPAND)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def SetValue(self, state):
        if self.checkbox is not None:
            self.checkbox.SetValue(state)

    def EnableCheckBox(self, state):
        if self.checkbox is not None:
            self.checkbox.Enable(state)

    def IsChecked(self):
        if self.checkbox is not None:
            return self.checkbox.IsChecked()
        else:
            return True


class ObjectFrame(wx.Frame):
    def __init__(self, parent, title):
        super().__init__(parent=parent, title=title,
                         style=wx.CAPTION | wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR)

        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # custom panel -------------------------------------------------------------------------------------------------
        self.custom = wx.Panel(self.panel, style=wx.SIMPLE_BORDER)
        self.custom.SetBackgroundColour(wx.WHITE)

        # buttons ------------------------------------------------------------------------------------------------------
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.apply_button = wx.Button(self.panel, label='Apply')
        self.ok_button = wx.Button(self.panel, label='OK')

        self.cancel_button = wx.Button(self.panel, label='Cancel')
        self.cancel_button.Bind(wx.EVT_BUTTON, self.OnCancelButton)

        button_sizer.Add(self.apply_button, 1, wx.RIGHT, GAP)
        button_sizer.Add(self.ok_button, 1, wx.RIGHT, GAP)
        button_sizer.Add(self.cancel_button, 1)

        # setting layout -----------------------------------------------------------------------------------------------
        self.sizer.Add(self.custom, 1, wx.ALL | wx.EXPAND, GAP)
        self.sizer.Add(button_sizer, 0, (wx.ALL & ~wx.TOP) | wx.ALIGN_RIGHT, GAP)
        self.panel.SetSizer(self.sizer)

    def Realize(self):
        self.sizer.Fit(self)

    def OnCancelButton(self, event):
        self.Close(True)


class ObjectDialog(wx.Dialog):
    def __init__(self, parent, title):
        super().__init__(parent=parent, title=title,
                         style=wx.CAPTION | wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR)

        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # custom panel -------------------------------------------------------------------------------------------------
        self.custom = wx.Panel(self.panel, style=wx.SIMPLE_BORDER)
        self.custom.SetBackgroundColour(wx.WHITE)

        # buttons ------------------------------------------------------------------------------------------------------
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.ok_button = wx.Button(self.panel, label='OK')

        self.cancel_button = wx.Button(self.panel, label='Cancel')
        self.cancel_button.Bind(wx.EVT_BUTTON, self.OnCancelButton)

        button_sizer.Add(self.ok_button, 1, wx.RIGHT, GAP)
        button_sizer.Add(self.cancel_button, 1)

        # setting layout -----------------------------------------------------------------------------------------------
        self.sizer.Add(self.custom, 1, wx.ALL | wx.EXPAND, GAP)
        self.sizer.Add(button_sizer, 0, (wx.ALL & ~wx.TOP) | wx.ALIGN_RIGHT, GAP)
        self.panel.SetSizer(self.sizer)

    def Realize(self):
        self.sizer.Fit(self)

    def OnCancelButton(self, event):
        self.Close(True)