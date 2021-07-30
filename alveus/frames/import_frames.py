import wx
from xlrd import XLRDError

from frames.frame_design import ObjectDialog, SectionSeparator, VGAP, HGAP, GAP
from frames.frame_utilities import GetFilePath
from import_ import FromExcel

import _icons as ico

LIQUID_UNITS = ['stb/day', 'Mstb/day']
GAS_UNITS = ['Mscf/day', 'MMscf/day']
UPTIME_UNITS = ['days', '%']


class VariableLabelPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label='Variable:'), 1,(wx.ALL & ~wx.RIGHT), GAP)
        sizer.Add(wx.StaticText(self, label='Unit:'), 1, (wx.ALL & ~wx.RIGHT), GAP)
        sizer.Add(wx.StaticText(self, label='Column:'), 1, (wx.ALL & ~wx.RIGHT), GAP)

        self.SetSizer(sizer)
        sizer.Fit(self)


class VariableSelectionPanel(wx.Panel):
    def __init__(self, parent, units=None, label='', bitmap=None, checkbox=True):
        super().__init__(parent)

        sizer = wx.BoxSizer(wx.VERTICAL)

        if checkbox:
            self.checkbox = wx.CheckBox(self, label=label)
            self.Bind(wx.EVT_CHECKBOX, self.OnCheckBox, self.checkbox)

            check_box_sizer = wx.BoxSizer(wx.HORIZONTAL)

            if bitmap is not None:
                check_box_sizer.Add(wx.StaticBitmap(self, wx.ID_ANY, bitmap), 0, wx.ALIGN_CENTER_VERTICAL | (wx.ALL & ~wx.LEFT), GAP)

            check_box_sizer.Add(self.checkbox, 0,  wx.ALIGN_CENTER_VERTICAL | wx.ALL, GAP)
            sizer.Add(check_box_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, GAP)

        else:

            self.checkbox = None

            header_sizer = wx.BoxSizer(wx.HORIZONTAL)

            if bitmap is not None:
                header_sizer.Add(wx.StaticBitmap(self, wx.ID_ANY, bitmap), 0, wx.ALIGN_CENTER_VERTICAL | (wx.ALL & ~wx.LEFT), GAP)

            header_sizer.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, GAP)
            sizer.Add(header_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, GAP)

        if units is not None:
            self.units = wx.Choice(self, choices=units)
            sizer.Add(self.units, 0, wx.ALL | wx.EXPAND, GAP)

        else:

            self.units = None
            sizer.Add(wx.StaticText(self, label=''), 0, wx.ALL | wx.EXPAND, GAP)

        self.column = wx.TextCtrl(self, value='')
        sizer.Add(self.column, 0, wx.ALL | wx.EXPAND, GAP)

        self.SetSizer(sizer)
        sizer.Fit(self)

    # events -----------------------------------------------------------------------------------------------------------
    def OnCheckBox(self, event):
        self.EnableCtrls(event.IsChecked())

    def EnableCtrls(self, state):
        self.units.Enable(state)
        self.column.Enable(state)

    def GetColumn(self):
        try:

            column = int(self.column.GetValue())

            if column < 1:

                raise ValueError('Column number must be greater than 0')

        except TypeError:

            raise TypeError('Columns must be numbers')

        return column - 1  # -1 accounts for zero indexing

    def GetUnit(self):
        return self.units.GetString(self.units.GetSelection())

    def IsChecked(self):
        return self.checkbox.IsChecked()

    def SetChecked(self, state):
        self.checkbox.SetValue(state)

    def SetColumn(self, value):
        self.column.SetValue(value)

    def SetDefault(self, column, checked=None, unit=None):
        self.SetColumn(column)

        if checked is not None:
            self.SetChecked(checked)
            self.EnableCtrls(checked)

        if unit is not None:
            self.SetUnit(unit)

    def SetUnit(self, idx):
        self.units.SetSelection(idx)


class ProfileImportFrame(wx.Dialog):
    def __init__(self, parent, profile):
        super().__init__(parent=parent, title='Import Profile...',
                         style=wx.CAPTION | wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR)

        self._imported = False
        self._path = None
        self._profile = profile

        self.panel = self.panel = wx.Panel(self)
        self.custom = wx.Panel(self.panel, style=wx.SIMPLE_BORDER)
        self.custom.SetBackgroundColour(wx.WHITE)

        # paths
        self.path = wx.TextCtrl(self.custom, value='')
        self.browse = wx.Button(self.custom, label='Browse')
        self.sheet = wx.TextCtrl(self.custom, value='')

        # options
        self.first_row = wx.TextCtrl(self.custom, value='2')
        self.includes_lift = wx.CheckBox(self.custom, label='Total-gas includes lift gas')

        # variable row labels
        self.row_label1 = VariableLabelPanel(self.custom)
        self.row_label2 = VariableLabelPanel(self.custom)
        self.row_label3 = VariableLabelPanel(self.custom)

        # variables
        self.date = VariableSelectionPanel(self.custom,                                 label='Dates',             bitmap=ico.time_16x16.GetBitmap(), checkbox=False)
        self.lift_uptime = VariableSelectionPanel(self.custom,      units=UPTIME_UNITS, label='Lift-gas uptime',   bitmap=ico.uptime_16x16.GetBitmap())
        self.lift_gas = VariableSelectionPanel(self.custom,         units=GAS_UNITS,    label='Lift-gas pot.',     bitmap=ico.lift_gas_rate_16x16.GetBitmap())
        self.prod_uptime = VariableSelectionPanel(self.custom,      units=UPTIME_UNITS, label='Production uptime', bitmap=ico.uptime_16x16.GetBitmap())
        self.oil = VariableSelectionPanel(self.custom,              units=LIQUID_UNITS, label='Oil pot.',          bitmap=ico.oil_rate_16x16.GetBitmap())
        self.total_gas = VariableSelectionPanel(self.custom,        units=GAS_UNITS,    label='Total-gas pot.',    bitmap=ico.total_gas_rate_16x16.GetBitmap())
        self.water = VariableSelectionPanel(self.custom,            units=GAS_UNITS,    label='Water pot.',        bitmap=ico.water_rate_16x16.GetBitmap())
        self.gas_inj_uptime = VariableSelectionPanel(self.custom,   units=UPTIME_UNITS, label='Gas inj. uptime',   bitmap=ico.uptime_16x16.GetBitmap())
        self.water_inj_uptime = VariableSelectionPanel(self.custom, units=UPTIME_UNITS, label='Water inj. uptime', bitmap=ico.uptime_16x16.GetBitmap())
        self.gas_inj = VariableSelectionPanel(self.custom,          units=GAS_UNITS,    label='Gas inj. pot.',     bitmap=ico.gas_injection_rate_16x16.GetBitmap())
        self.water_inj = VariableSelectionPanel(self.custom,        units=GAS_UNITS,    label='Water inj. pot.',   bitmap=ico.water_injection_rate_16x16.GetBitmap())

        self.InitUI()
        self.Default()

        self.SetMinSize(self.GetSize())
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.browse.Bind(wx.EVT_BUTTON, self.OnBrowseButton)

    def InitUI(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        custom_sizer = wx.BoxSizer(wx.VERTICAL)
        path_sizer = wx.FlexGridSizer(2, 3, vgap=VGAP, hgap=HGAP)
        options_sizer = wx.FlexGridSizer(1, 3, vgap=VGAP, hgap=HGAP)
        variables_sizer = wx.FlexGridSizer(3, 5, vgap=VGAP, hgap=HGAP)

        # file path ----------------------------------------------------------------------------------------------------

        path_sizer.AddMany([(wx.StaticText(self.custom, label='Path:'), 0, (wx.ALL & ~wx.RIGHT), GAP),
                            (self.path, 1, wx.EXPAND | wx.ALL, GAP),
                            (self.browse, 0, wx.EXPAND | wx.RIGHT, GAP),
                            (wx.StaticText(self.custom, label='Sheet:'), 0, (wx.ALL & ~wx.RIGHT), GAP),
                            (self.sheet, 1, wx.EXPAND | wx.ALL, GAP),
                            wx.StaticText(self.custom, label='')])

        path_sizer.AddGrowableCol(1, 1)

        # Options ------------------------------------------------------------------------------------------------------
        options_sizer.AddMany([(wx.StaticText(self.custom, label='First row:'), 0, (wx.ALL & ~wx.RIGHT), GAP),
                               (self.first_row, 1, wx.EXPAND | wx.ALL, GAP),
                               (self.includes_lift, 1, wx.EXPAND | wx.ALL, GAP)])

        # variables ----------------------------------------------------------------------------------------------------
        # first row
        variables_sizer.Add(self.row_label1, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.date, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.lift_uptime, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.lift_gas, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(wx.StaticText(self.custom, label=''), 0, wx.ALL | wx.EXPAND, GAP)

        # second row
        variables_sizer.Add(self.row_label2, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.prod_uptime, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.oil, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.total_gas, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.water, 0, wx.ALL | wx.EXPAND, GAP)

        # third row
        variables_sizer.Add(self.row_label3, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.gas_inj_uptime, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.water_inj_uptime, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.gas_inj, 0, wx.ALL | wx.EXPAND, GAP)
        variables_sizer.Add(self.water_inj, 0, wx.ALL | wx.EXPAND, GAP)

        # sizing input -------------------------------------------------------------------------------------------------
        custom_sizer.Add(SectionSeparator(self.custom, 'Path'),    0, wx.ALL | wx.EXPAND, GAP)
        custom_sizer.Add(path_sizer, 0, wx.EXPAND)
        custom_sizer.Add(SectionSeparator(self.custom, 'Options'), 0, wx.ALL | wx.EXPAND, GAP)
        custom_sizer.Add(options_sizer, 0, wx.EXPAND)
        custom_sizer.Add(SectionSeparator(self.custom, 'Variables'), 0, wx.ALL | wx.EXPAND, GAP)
        custom_sizer.Add(variables_sizer, 0, wx.EXPAND)

        # sizing custom ------------------------------------------------------------------------------------------------
        self.custom.SetSizer(custom_sizer)

        # buttons ------------------------------------------------------------------------------------------------------
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        import_button = wx.Button(self.panel, label='Import')
        import_button.Bind(wx.EVT_BUTTON, self.OnImportButton)

        cancel_button = wx.Button(self.panel, label='Cancel')
        cancel_button.Bind(wx.EVT_BUTTON, self.OnCancelButton)

        button_sizer.Add(import_button, 1, wx.RIGHT, GAP)
        button_sizer.Add(cancel_button, 1)

        # setting layout -----------------------------------------------------------------------------------------------
        sizer.Add(self.custom, 1, wx.ALL | wx.EXPAND, GAP)
        sizer.Add(button_sizer, 0, (wx.ALL & ~wx.TOP) | wx.ALIGN_RIGHT, GAP)
        self.panel.SetSizer(sizer)
        sizer.Fit(self)

    # events -----------------------------------------------------------------------------------------------------------
    def OnBrowseButton(self, event):

        path = GetFilePath(self, message='Import Profile...')
        if path is None:
            return
        else:
            self.path.SetValue(path)

    def OnCancelButton(self, event):
        self.Close(True)

    def OnImportButton(self, event):
        path = self.path.GetValue()
        if path == '':
            return

        sheet = self.sheet.GetValue()
        if sheet == '':
            return

        # append items to list -----------------------------------------------------------------------------------------
        items = []
        box = None

        try:

            items.append(('date', '', self.date.GetColumn()))

            if self.lift_uptime.IsChecked():
                items.append(('lift_gas_uptime', self.lift_uptime.GetUnit(), self.lift_uptime.GetColumn()))

            if self.lift_gas.IsChecked():
                items.append(('lift_gas_potential', self.lift_gas.GetUnit(), self.lift_gas.GetColumn()))

            if self.prod_uptime.IsChecked():
                items.append(('production_uptime', self.prod_uptime.GetUnit(), self.prod_uptime.GetColumn()))

            if self.oil.IsChecked():
                items.append(('oil_potential', self.oil.GetUnit(), self.oil.GetColumn()))

            if self.total_gas.IsChecked():
                items.append(('total_gas_potential', self.total_gas.GetUnit(), self.total_gas.GetColumn()))

            if self.water.IsChecked():
                items.append(('water_potential', self.water.GetUnit(), self.water.GetColumn()))

            if self.gas_inj_uptime.IsChecked():
                items.append(('gas_injection_uptime', self.gas_inj_uptime.GetUnit(), self.gas_inj_uptime.GetColumn()))

            if self.water_inj_uptime.IsChecked():
                items.append(('water_injection_uptime', self.water_inj_uptime.GetUnit(), self.water_inj_uptime.GetColumn()))

            if self.gas_inj.IsChecked():
                items.append(('gas_injection_potential', self.gas_inj.GetUnit(), self.gas_inj.GetColumn()))

            if self.water_inj.IsChecked():
                items.append(('water_injection_potential', self.water_inj.GetUnit(), self.water_inj.GetColumn()))

        except TypeError as e:

            box = wx.MessageDialog(self, message=str(e), caption='Type Error')

        except ValueError as e:

            box = wx.MessageDialog(self, message=str(e), caption='Value Error')

        if box is not None:
            box.ShowModal()
            box.Destroy()
            return

        # gather options -----------------------------------------------------------------------------------------------
        first_row = 1

        try:
            first_row = int(self.first_row.GetValue())

            if first_row < 1:

                box = wx.MessageDialog(self, message='First row must be greater than 0', caption='Value Error')

        except ValueError:

            box = wx.MessageDialog(self, message='First row must be an integer greater than 0', caption='Type Error')

        if box is not None:
            box.ShowModal()
            box.Destroy()
            return

        # import from excel --------------------------------------------------------------------------------------------
        profile = None

        try:
            profile = FromExcel(items, path, sheet, first_row=first_row)

        except FileNotFoundError:

            box = wx.MessageDialog(self, message='Unable to find file \'{}\''.format(path), caption='FileNotFound Error')

        except XLRDError:

            box = wx.MessageDialog(self, message='Unable to find sheet \'{}\''.format(sheet), caption='XLRD Error')

        if box is not None:
            box.ShowModal()
            box.Destroy()
            return

        if not self.includes_lift.IsChecked():
            profile.values[:, 1] += profile.values[:, 3]

        self._profile.replace(profile)

        self._path = path
        self._imported = True
        self.Close(True)

    def Default(self):
        self.date.SetDefault('1')
        self.lift_uptime.SetDefault('3', True, 0)
        self.lift_gas.SetDefault('9', True, 1)
        self.prod_uptime.SetDefault('2', True, 0)
        self.oil.SetDefault('6', True, 0)
        self.total_gas.SetDefault('7', True, 1)
        self.water.SetDefault('8', True, 0)
        self.gas_inj_uptime.SetDefault('4', False, 0)
        self.water_inj_uptime.SetDefault('5', False, 0)
        self.gas_inj.SetDefault('10', False, 1)
        self.water_inj.SetDefault('11', False, 0)

    def IsImported(self):
        return self._imported

    def GetPath(self):
        return self._path
