import os
import numpy as np
import wx

from timeline import sample_dateline, ExtractDates

from frames.frame_design import SectionSeparator, VGAP, HGAP, GAP

from frames.frame_utilities import GetDirPath
from export import ToExcel
from frames.property_panels import SelectionTree, PropertiesAUIPanel, ResamplePanel

from _ids import *
import _icons as ico


class ExportFrame(wx.Frame):
    def __init__(self, parent, entity_mgr, variable_mgr, object_menu, entities=()):
        super().__init__(parent=parent, title='Export Profiles...',
                         style=wx.CAPTION | wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR)

        self._entity_mgr = entity_mgr
        self._variable_mgr = variable_mgr
        self._object_menu = object_menu

        self._entities = entities  # saved for access in InitUI

        # custom panel -------------------------------------------------------------------------------------------------
        self.panel = wx.Panel(self)
        self.custom = wx.Panel(self.panel, style=wx.SIMPLE_BORDER)
        self.custom.SetBackgroundColour(wx.WHITE)
        self.splitter = wx.SplitterWindow(self.custom, wx.ID_ANY, style=wx.SP_THIN_SASH | wx.SP_LIVE_UPDATE)

        # aui tree selection -------------------------------------------------------------------------------------------
        self.aui_panel = PropertiesAUIPanel(self.splitter, min_size=(245, 385))
        entities_panel = wx.Panel(self.custom)
        self.entities = SelectionTree(entities_panel, object_menu.entities)

        self.aui_panel.AddPage(entities_panel, self.entities, proportions=(1,),
                               title='Entities', bitmap=ico.folder_closed_16x16.GetBitmap())

        projects_panel = wx.Panel(self.custom)
        self.projects = SelectionTree(projects_panel, object_menu.projects)

        self.aui_panel.AddPage(projects_panel, self.projects, proportions=(1,),
                               title='Projects', bitmap=ico.project_16x16.GetBitmap())

        variables_panel = wx.Panel(self.custom)
        self.variables = SelectionTree(variables_panel, object_menu.variables)

        self.aui_panel.AddPage(variables_panel, self.variables, proportions=(1,),
                               title='Variables', bitmap=ico.grid_properties_16x16.GetBitmap())

        # input --------------------------------------------------------------------------------------------------------
        self.input = wx.Panel(self.splitter)
        self.input.SetBackgroundColour(wx.WHITE)

        self.directory = wx.TextCtrl(self.input, value='')
        self.browse = wx.Button(self.input, label='Browse')

        self.single_file = wx.CheckBox(self.input, label='Export to single file (per simulation)')
        self.single_tab = wx.CheckBox(self.input, label='Append profiles vertically')
        self.export_children = wx.CheckBox(self.input, label='Export children of the selected entities')
        self.phaser = wx.CheckBox(self.input, label='Export variables in Phaser format')
        self.low = wx.CheckBox(self.input, label='Low case')
        self.mid = wx.CheckBox(self.input, label='Mid case')
        self.high = wx.CheckBox(self.input, label='High case')
        self.resample = ResamplePanel(self.input)

        self.InitUI()
        self.Default()

        self.SetSize(wx.Size(700, 600))
        self.SetMinSize(self.GetSize())
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.browse.Bind(wx.EVT_BUTTON, self.OnBrowseButton)

    def InitUI(self):
        self.SetIcon(ico.export_spreadsheet_16x16.GetIcon())

        # populate trees -----------------------------------------------------------------------------------------------
        items = (self._object_menu.entities.fields, self._object_menu.entities.blocks,
                 self._object_menu.entities.facilities, self._object_menu.entities.subsurface)

        types = (ID_FIELD, ID_BLOCK, ID_RESERVOIR, ID_THEME, ID_POLYGON, ID_PLATFORM, ID_PROCESSOR, ID_PIPELINE,
                 ID_PRODUCER, ID_INJECTOR)

        self.entities.Populate(items, types, progress=True)

        items = (self._object_menu.projects.projects,)
        types = (ID_HISTORY, ID_PREDICTION)
        self.projects.Populate(items, types, progress=True)

        items = (self._object_menu.variables.durations, self._object_menu.variables.potentials,
                 self._object_menu.variables.rates, self._object_menu.variables.cumulatives,
                 self._object_menu.variables.ratios)

        types = ('durations', 'potentials', 'rates', 'cumulatives', 'ratios')
        self.variables.Populate(items, types)

        # if items was passed, check it
        for entity in self._entities:
            if entity is not None:
                id_ = [entity.GetId()]

                if entity.IsHistory() or entity.IsPrediction():
                    self.projects.CheckItemsById(id_)

                else:
                    self.entities.CheckItemsById(id_)

        # user input ---------------------------------------------------------------------------------------------------
        path_sizer = wx.FlexGridSizer(1, 3, vgap=VGAP, hgap=HGAP)
        path_sizer.AddMany([(wx.StaticText(self.input, label='Path:'), 0, wx.ALIGN_CENTER_VERTICAL | (wx.ALL & ~wx.RIGHT), GAP),
                            (self.directory, 1, wx.EXPAND | wx.ALL, GAP),
                            (self.browse, 0, wx.EXPAND)])

        path_sizer.AddGrowableCol(1, 1)

        # sizing input -------------------------------------------------------------------------------------------------
        input_sizer = wx.BoxSizer(wx.VERTICAL)
        case_sizer = wx.BoxSizer(wx.HORIZONTAL)

        input_sizer.Add(SectionSeparator(self.input, 'Path'),    0, wx.ALL | wx.EXPAND, GAP)
        input_sizer.Add(path_sizer, 0, wx.EXPAND)
        input_sizer.Add(SectionSeparator(self.input, 'Options'), 0, wx.ALL | wx.EXPAND, GAP)
        input_sizer.Add(self.single_file, 0, wx.EXPAND | wx.ALL, GAP)
        input_sizer.Add(self.single_tab, 0, wx.EXPAND | wx.ALL, GAP)
        input_sizer.Add(self.export_children, 0, wx.EXPAND | wx.ALL, GAP)
        input_sizer.Add(self.phaser, 0, wx.EXPAND | wx.ALL, GAP)

        input_sizer.Add(SectionSeparator(self.input, 'Cases', bitmap=ico.profiles_chart_16x16.GetBitmap()), 0, wx.ALL | wx.EXPAND, GAP)

        case_sizer.Add(self.low, 0, wx.EXPAND, wx.ALL, GAP)
        case_sizer.Add(self.mid, 0, wx.EXPAND, wx.ALL, GAP)
        case_sizer.Add(self.high, 0, wx.EXPAND, wx.ALL, GAP)
        input_sizer.Add(case_sizer, 0, wx.EXPAND | wx.ALL, GAP)

        input_sizer.Add(self.resample, 0, wx.ALL | wx.EXPAND, GAP)

        self.input.SetSizer(input_sizer)

        # sizing custom ------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()
        self.splitter.SplitVertically(self.aui_panel, self.input, 200)

        custom_sizer = wx.BoxSizer(wx.VERTICAL)
        custom_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, GAP)
        self.custom.SetSizer(custom_sizer)

        # buttons ------------------------------------------------------------------------------------------------------
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        export_button = wx.Button(self.panel, label='Export')
        export_button.Bind(wx.EVT_BUTTON, self.OnExportButton)

        cancel_button = wx.Button(self.panel, label='Cancel')
        cancel_button.Bind(wx.EVT_BUTTON, self.OnCancelButton)

        button_sizer.Add(export_button, 1, wx.RIGHT, GAP)
        button_sizer.Add(cancel_button, 1)

        # setting layout -----------------------------------------------------------------------------------------------
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.custom, 1, wx.ALL | wx.EXPAND, GAP)
        sizer.Add(button_sizer, 0, (wx.ALL & ~wx.TOP) | wx.ALIGN_RIGHT, GAP)
        self.panel.SetSizer(sizer)
        sizer.Fit(self)

    def Default(self):
        self.single_file.SetValue(True)
        self.single_tab.SetValue(True)
        self.mid.SetValue(True)

    def OnBrowseButton(self, event):
        path = GetDirPath(self, message='Export...')
        if path is None:
            return
        else:
            self.directory.SetValue(path)

    def OnCancelButton(self, event):
        self.Close(True)

    def OnExportButton(self, event):
        directory = self.directory.GetValue()
        if directory == '':
            box = wx.MessageDialog(self, message='No path for exporting is provided.', caption='Missing path')
            box.ShowModal()
            box.Destroy()
            return

        # gather input -------------------------------------------------------------------------------------------------
        single_file = self.single_file.GetValue()
        single_tab = self.single_tab.GetValue()
        export_children = self.export_children.GetValue()
        phaser = self.phaser.IsChecked()

        # gather cases -------------------------------------------------------------------------------------------------
        cases = []
        if self.low.IsChecked():
            cases.append(0)

        if self.mid.IsChecked():
            cases.append(1)

        if self.high.IsChecked():
            cases.append(2)

        if not cases:
            box = wx.MessageDialog(self, message='No cases are selected.', caption='Missing selection')
            box.ShowModal()
            box.Destroy()
            return

        # gather selections --------------------------------------------------------------------------------------------
        box = None

        entities = self._entity_mgr.GetEntities(self.entities.GetPointers())
        simulations = self._entity_mgr.GetEntities(self.projects.GetPointers())
        variables = self._variable_mgr.GetVariables(self.variables.GetPointers())

        if not entities:

            box = wx.MessageDialog(self, message='No entities are selected.', caption='Missing selection')

        elif not simulations:

            box = wx.MessageDialog(self, message='No simulations are selected.', caption='Missing selection')

        elif (not variables) and not phaser:

            box = wx.MessageDialog(self, message='No variables are selected.', caption='Missing selection')

        if box is not None:
            box.ShowModal()
            box.Destroy()
            return

        # gather items -------------------------------------------------------------------------------------------------
        # items will contain {file_name: [entities]}
        if export_children:
            # TODO: ensure only children of SimulationHolders are exported (e.g. avoid analogues for polygons)
            items = {e.GetName(): self._entity_mgr.GetChildren(e) for e in entities}
        else:
            items = {e.GetName(): [e] for e in entities}

        # items will contain {file_name: {sheet_name: [entities]}}
        if single_file:
            if single_tab:
                items = {'profile_export': {'BTE': [e for es in items.values() for e in es]}}
            else:
                items = {'profile_export': {e.GetName(): [e] for es in items.values() for e in es}}
        else:
            if single_tab:
                items = {s.GetName(): {'BTE': [e for e in list(items.values())[i]]} for i, s in enumerate(entities)}
            else:
                items = {e.GetName(): {'BTE': [e]} for es in items.values() for e in es}

        # re-sampling options ------------------------------------------------------------------------------------------
        resample, start, end, frequency, delta = self.resample.Get()

        dateline = None
        if resample:
            if None in (start, end):
                start_p, end_p = ExtractDates([e.GetSimulationProfile(s) for e in entities for s in simulations])

                if start is None:
                    start = start_p

                if end is None:
                    end = end_p

            start = np.array(start, dtype='datetime64[D]')
            end = np.array(end, dtype='datetime64[D]')

            if frequency is None:
                frequency = 2

            dateline = sample_dateline(start, end, frequency, delta=delta)

        # if phaser format, overwrite variables by pre-determined variables
        if phaser:
            variables = self._variable_mgr.GetVariables(('date', 'oil_potential', 'total_gas_potential',
                                                         'water_potential', 'lift_gas_potential',
                                                         'gas_injection_potential', 'water_injection_potential'))

        # export -------------------------------------------------------------------------------------------------------
        ToExcel(cases, items, simulations, variables, directory, dateline=dateline, phaser=phaser)
        self.Close(True)
