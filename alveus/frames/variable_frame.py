import copy
import wx
import numpy as np
from pubsub import pub

from variable_mgr import Summary
from frames.frame_design import ObjectFrame, GAP, INTER_GAP
from frames.property_panels import PropertiesAUIPanel, SelectionTree, LineOptionsPanel, NamePanel,\
    SummaryConversionPanel, SummaryEvaluationPanel, SummaryIconPanel

import _icons as ico


class VariableFrame(ObjectFrame):
    def __init__(self, parent, variable_mgr, item=None):
        super().__init__(parent, '')

        # used for access to object_menu tree, to add/modify entities
        self._variable_mgr = variable_mgr
        self._variable_id = None
        self._variable = None
        self._item = item

        if item is not None:  # can be none for SummaryVariables
            id_ = item.GetData().GetId()
            self._variable = variable_mgr.GetVariable(id_)
            self._variable_id = id_

        self.custom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # events -------------------------------------------------------------------------------------------------------
        self.apply_button.Bind(wx.EVT_BUTTON, self.OnApplyButton)
        self.ok_button.Bind(wx.EVT_BUTTON, self.OnOKButton)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnApplyButton(self, event):
        saved = self.Save(self._variable)

        if saved:
            pub.sendMessage('pointer_updated', checked=self._item.IsChecked(), id_=self._variable.GetId())

        return saved

    def OnOKButton(self, event):
        saved = self.OnApplyButton(None)

        if saved:
            self.Close(True)

    def OnClose(self, event):
        if self._item is not None:
            # unlock variable pointer
            self._item.GetData().Lock(False)

        event.Skip()

    def Save(self, variable):
        return True


class ProductionVariableFrame(VariableFrame):
    def __init__(self, parent, variable_mgr, item=None):
        super().__init__(parent, variable_mgr, item=item)

        self.options = LineOptionsPanel(self.custom)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._variable.GetImage().GetIcon())
        self.SetTitle(self._variable.GetMenuLabel())

        # sizing -------------------------------------------------------------------------------------------------------
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.options, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)

        self.custom_sizer.Add(sizer, 1, wx.EXPAND)
        self.custom.SetSizer(self.custom_sizer)
        self.Realize()

    def Load(self):
        lo = self._variable.GetLineOptions()

        r, g, b = lo.GetColour() * 255.
        alpha = lo.GetAlpha() * 255. if lo.GetAlpha() is not None else 255
        colour = wx.Colour(int(r), int(g), int(b), int(alpha))

        self.options.Set(lo.GetLinestyle(), lo.GetDrawstyle(), colour)

    def Save(self, variable):
        lo = variable.GetLineOptions()
        linestyle, drawstyle, colour = self.options.Get()

        lo.SetLinestyle(linestyle)
        lo.SetDrawstyle(drawstyle)

        r, g, b, alpha = colour.Get()
        lo.SetColour(np.array([r, g, b], dtype=np.float64) / 255.)
        lo.SetAlpha(float(alpha) / 255.)

        return True


class SummaryVariableFrame(VariableFrame):
    def __init__(self, parent, variable_mgr, object_menu, item=None):
        super().__init__(parent, variable_mgr, item=item)

        self._object_menu = object_menu

        if item is None:
            self._variable = Summary()

        splitter = wx.SplitterWindow(self.custom, wx.ID_ANY, style=wx.SP_THIN_SASH | wx.SP_LIVE_UPDATE)
        self.aui_panel = PropertiesAUIPanel(splitter, min_size=(270, 255))
        self.input = wx.Panel(splitter)
        splitter.SplitVertically(self.aui_panel, self.input, 200)

        self.name = NamePanel(self.input)
        self.icon = SummaryIconPanel(self.input)
        self.evaluation = SummaryEvaluationPanel(self.input)
        self.conversion = SummaryConversionPanel(self.input)

        # production ---------------------------------------------------------------------------------------------------
        production_panel = wx.Panel(self.custom)
        self.production = SelectionTree(production_panel, self._object_menu.variables)

        self.aui_panel.AddPage(production_panel, self.production, proportions=(1,),
                               title='Production', bitmap=ico.cumulatives_16x16.GetBitmap())

        # variables ----------------------------------------------------------------------------------------------------
        variables_panel = wx.Panel(self.custom)
        self.variables = SelectionTree(variables_panel, object_menu.variables)

        self.aui_panel.AddPage(variables_panel, self.variables, proportions=(1,),
                               title='Variables', bitmap=ico.grid_properties_16x16.GetBitmap())

        # updating aui -------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()

        # sizing custom ------------------------------------------------------------------------------------------------
        self.custom_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, GAP)
        self.custom.SetSizer(self.custom_sizer)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_BUTTON, self.OnInsert, self.evaluation.arrow.button)

    def InitUI(self):
        self.input.SetBackgroundColour(wx.WHITE)

        # set title & icon ---------------------------------------------------------------------------------------------
        if self._item is not None:
            self.SetIcon(self._variable.GetImage().GetIcon())
            self.SetTitle(self._variable.GetMenuLabel())
        else:
            self.SetIcon(ico.summary_16x16.GetIcon())
            self.SetTitle('Add summary')

        # trees --------------------------------------------------------------------------------------------------------
        items = (self._object_menu.variables.potentials, self._object_menu.variables.rates,
                 self._object_menu.variables.cumulatives, self._object_menu.variables.ratios)

        self.production.Populate(items, ('potentials', 'rates', 'cumulatives', 'ratios'), ct_type=2)

        items = (self._object_menu.variables.statics, self._object_menu.variables.volumes,
                 self._object_menu.variables.risking)

        self.variables.Populate(items, ('statics', 'volumes', 'risking'), ct_type=0)

        # sizing -------------------------------------------------------------------------------------------------------
        input_sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer.Add(self.name, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        input_sizer.Add(self.icon, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        input_sizer.Add(self.evaluation, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        input_sizer.Add(self.conversion, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)

        self.input.SetSizer(input_sizer)
        input_sizer.Fit(self.input)

        self.Realize()

    # events -----------------------------------------------------------------------------------------------------------
    def OnApplyButton(self, event):
        if self._item is not None:
            # Wrapped in copy.deepcopy to ensure properties are not changed in case of Save error + Cancel
            variable = copy.deepcopy(self._variable_mgr.GetVariable(self._item.GetData().GetId()))

        else:
            variable = self._variable

        saved = self.Save(variable)

        if saved:
            image_id = self.GetImageId()

            if self._item is None:

                self._variable_mgr.AddSummary(variable)

                item_parent = getattr(self._object_menu.variables, variable.GetType())
                self._item = self._object_menu.variables.AddVariable(item_parent, variable, image_id=image_id)
                pub.sendMessage('summary_added', id_=variable.GetId())

            else:
                self._object_menu.variables.UpdateVariable(self._item, variable, image_id=image_id)
                self._variable.ReplaceInformation(variable, image_id)

        return saved

    def OnInsert(self, event):
        item = self.variables.tree.GetSelection()
        if not item:
            return

        data = item.GetData()
        if data.IsPointer():
            self.evaluation.Append(data.GetId())

    # external methods -------------------------------------------------------------------------------------------------
    def GetImageId(self):
        try:
            return self.icon.selection.GetSelectionData()
        except KeyError:
            return None

    def Load(self):
        self.name.Set(self._variable.GetMenuLabel())

        properties = self._variable.GetProperties()
        production, icon, eval_, function, point, date, time = properties.Get()

        self.production.CheckItemsById(production)

        self.icon.Set(icon)
        self.evaluation.Set(eval_)
        self.conversion.Set(function, point, date, time)

        # enable appropriate controls
        self.conversion.OnFunctionComboBox(None, function)
        self.conversion.OnPointComboBox(None, point)

    def Save(self, variable):

        variable.SetLabels(self.name.Get())

        production = self.production.GetCheckedItems()
        if production:
            production = production[0].GetData().GetId()
        else:
            return False

        # settings the unit of the summary to the unit of the production variable
        variable.SetUnitClass(self._variable_mgr.GetVariable(production).GetUnitClass())

        properties = variable.GetProperties()

        icon = self.icon.Get()
        if icon[0] is None:
            return False

        try:
            properties.Set(production,  *icon, self.evaluation.Get(), *self.conversion.Get())

        except ValueError:
            return False

        return True

