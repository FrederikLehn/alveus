import numpy as np
import wx.adv
from wx.lib.agw.customtreectrl import EVT_TREE_ITEM_CHECKING, EVT_TREE_ITEM_CHECKED

from _ids import *
from _errors import AssembleError, ConvergenceError
from chart_mgr import AxesItem
from charts import ChartPanel
from variable_mgr import Time, OilCumulative, LiquidPotential, WaterCut, GasOilRatio
from frames.frame_design import ObjectDialog, GAP, SMALL_GAP

from frames.property_panels import PropertiesAUIPanel, IncludeModelPanel, MergePanel, ModifierPanel, RunPanel

from frames.curve_fit_frame import ModelTree

import _icons as ico


class FunctionChartPanel(ChartPanel):
    def __init__(self, parent):
        super().__init__(parent)

    def Realize(self, axes_item=None, fun=None, run_to=None, allow_push=True):
        if axes_item is None or not axes_item.GetNumberOfAxes():
            self.DrawPlaceholder()
            return

        self.fig.clf()
        # Create required axes -----------------------------------------------------------------------------------------
        ax = self.fig.add_subplot(1, 1, 1)

        # draw lines ---------------------------------------------------------------------------------------------------
        for line in axes_item.GetLines():
            ax.plot(*line.GetXY(), **line.GetOptions())

        # configure x-axis options -------------------------------------------------------------------------------------
        ax.set(**axes_item.GetXOptions(0))
        ax.minorticks_on()
        self.FormatXAxis(ax, axes_item.XIsDate(0))

        # configure y-axis options -------------------------------------------------------------------------------------
        ax.set(**axes_item.GetYOptions(0))
        ax.yaxis.set_tick_params(labelrotation=90)

        # draw typecurve -----------------------------------------------------------------------------------------------
        if fun is not None:
            data, fitted_data = axes_item.GetLines()[:2]

            offset = fun.GetOffset()
            if run_to is not None:
                x = np.linspace(offset, run_to, 100)
            else:
                x = data.GetX()[tuple(np.where(data.GetX() >= offset))]

            # if there is not pre-determined offset, push line on x-axis to match first "fitted data" point of the first
            # model or if no "fitted data" is available use the first producing data > 0
            push = 0.
            if (not offset) and allow_push:
                fitted_x = fitted_data.GetX()

                if fitted_x.size:
                    push = fitted_x[0]
                else:
                    push = data.GetX()[tuple(np.where(data.GetY() > 0.))][0]

            ax.plot(x + push, fun.eval(x - offset), 'k--', label='Typecurve')
            ax.set_xlim(0., x[-1])

        # Gather legend at position at last chart of each axes ---------------------------------------------------------
        ax.legend(handles=axes_item.GetLegend())
        ax.minorticks_on()
        ax.grid(True)

        # draw chart on canvas
        self.canvas.draw()

    def GetTooltipParams(self, event):
        return self.GetLineTooltipParams(event)


class TypecurveTab(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self._x_axis = None
        self._y_axis = None

        self._profile = None
        self._function = None
        self._model = None
        self._allow_push = True

        self.chart = FunctionChartPanel(self)
        self.model_tree = ModelTree(self)
        self.include = IncludeModelPanel(self)
        self.merges = MergePanel(self)
        self.modifiers = ModifierPanel(self)
        self.run = RunPanel(self)

        # disable all controls initially
        self.include.EnableCtrls(False)
        self.merges.EnableCtrls(False)
        self.modifiers.EnableCtrls(False)
        self.run.EnableCtrls(False, from_=1, to=3)

        self.InitUI()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(EVT_TREE_ITEM_CHECKING, self.OnTreeItemChecking, self.model_tree.tree)
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnTreeItemChecked, self.model_tree.tree)
        self.Bind(wx.EVT_CHECKBOX, self.OnChecked, self.include.check)
        self.Bind(wx.EVT_COMBOBOX, self.OnRunComboBox, self.run.point)
        self.Bind(wx.EVT_COMBOBOX, self.OnAxisComboBox, self.run.axis)
        self.Bind(wx.EVT_COMBOBOX, self.OnMergeComboBox, self.merges.selection)
        self.Bind(wx.EVT_BUTTON, self.OnRun, self.run.run_to.button)

    def InitUI(self):
        self.SetBackgroundColour(wx.WHITE)

        # sizing & layout ----------------------------------------------------------------------------------------------
        sizer = wx.BoxSizer(wx.VERTICAL)

        model_sizer = wx.BoxSizer(wx.VERTICAL)
        model_sizer.Add(self.model_tree, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        model_sizer.Add(self.include,    0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        model_sizer.Add(self.merges,     0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        model_sizer.Add(self.modifiers,  0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)

        display_sizer = wx.BoxSizer(wx.HORIZONTAL)
        display_sizer.Add(model_sizer, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        display_sizer.Add(wx.StaticLine(self, wx.ID_ANY, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.ALL, GAP)
        display_sizer.Add(self.chart, 1, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)

        sizer.Add(display_sizer, 1, wx.EXPAND)
        sizer.Add(self.run,      0, wx.EXPAND | (wx.LEFT | wx.RIGHT), GAP)

        self.SetSizer(sizer)
        sizer.Fit(self)

    # events -----------------------------------------------------------------------------------------------------------
    def OnChecked(self, event):
        self.EnableOptions(event.IsChecked())

    def OnMergeComboBox(self, event):
        idx = event.GetInt()
        if idx > -1:
            self.merges.EnableCtrls(True, from_=1, to=2)

    def OnTreeItemChecking(self, event):
        # save existing state
        saved = self.SaveState()

        if not saved:
            event.Veto()
        else:
            event.Skip()

    def OnTreeItemChecked(self, event):
        # load new state
        item = event.GetItem()
        model = item.GetData()

        include = model.Include()
        self.include.Set(include)
        self.include.EnableCtrls(True)
        self.EnableOptions(include)

        self.merges.Set(*model.GetMerges())
        self.merges.UpdateText(self.merges.GetSelection())

        self.modifiers.Set(*model.GetModifiers())

        self.DisplayChart()

        self._model = model

    def OnRunComboBox(self, event):
        self.EnableRun(event.GetInt())

    def OnAxisComboBox(self, event):
        self.EnableAxis(event.GetInt())

    def OnRun(self, event):
        saved = self.SaveState()
        if not saved:
            return

        saved, run_to = self.SaveRun()
        if not saved:
            return

        fun = None
        box = None
        try:

            fun = self._function.Assemble()

        except AssembleError as e:

            message = 'Unable to assemble function: {}'.format(e)
            box = wx.MessageDialog(None, message=message, caption='Assemble Error')

        except ConvergenceError as e:

            message = 'Unable to assemble function: {}'.format(e)
            box = wx.MessageDialog(None, message=message, caption='Convergence Error')

        except TypeError as e:

            box = wx.MessageDialog(None, message=str(e), caption='Type Error')

        except AttributeError as e:

            box = wx.MessageDialog(None, message=str(e), caption='Attribute Error')

        if box is not None:
            box.ShowModal()
            box.Destroy()
            return

        self.DisplayChart(fun=fun, run_to=run_to)

    # internal methods -------------------------------------------------------------------------------------------------
    def SaveRun(self):
        try:
            point, axis, value, run_to = self.run.Get()
        except TypeError:
            return False, None

        self._function.SetRun(point, axis, value, run_to)
        self._function.CalculateOffset(self._x_axis.GetId(), self._y_axis.GetId(), self._profile)

        return True, run_to

    def SaveState(self):
        # save existing state
        if self._model is not None:
            try:
                self._model.SetInclude(*self.include.Get())
                self._model.SetMerges(*self.merges.Get())
                self._model.SetModifiers(*self.modifiers.Get())
            except TypeError:
                return False

        # pushing updated models to self._function
        self._function.SetModels(self.model_tree.Get())
        return True

    def DisplayChart(self, fun=None, run_to=None):
        if self._profile is not None:
            axes_item = AxesItem()
            axes_item.MergeFits(self._profile, [self._x_axis], [self._y_axis], [self.model_tree.Get()])
        else:
            axes_item = None

        self.chart.Realize(axes_item, fun=fun, run_to=run_to, allow_push=self._allow_push)

    # internal methods -------------------------------------------------------------------------------------------------
    def EnableOptions(self, state):
        type_, _, _ = self.merges.Get()

        if state:
            if type_ is None:
                self.merges.EnableCtrls(state, to=1)
            else:
                self.merges.EnableCtrls(state)

        else:
            self.merges.EnableCtrls(state)

        self.modifiers.EnableCtrls(state)

    def EnableRun(self, idx):
        if idx == ID_SPECIFIC:
            self.run.EnableCtrls(True, from_=1, to=3)
        else:
            self.run.EnableCtrls(False, from_=1, to=3)
            self.run.DefaultCtrls(from_=1, to=3)

        _, axis, _, _ = self.run.Get()
        self.EnableAxis(axis)

    def EnableAxis(self, idx):
        if idx in (ID_ON_X_AXIS, ID_ON_Y_AXIS):
            self.run.EnableCtrls(True, from_=2, to=3)
        else:
            self.run.EnableCtrls(False, from_=2, to=3)
            self.run.DefaultCtrls(from_=2, to=3)

    # external methods -------------------------------------------------------------------------------------------------
    def Set(self, function, profile=None):
        self._profile = profile
        self.model_tree.Set(function.GetModels())

        self._function = function
        self._function.SetLimits(self._y_axis.GetLimits())

        point, axis, value, run_to = function.GetRun()
        self.run.Set(point, axis, value, run_to)
        self.EnableRun(point)

        self.chart.Realize()  # required for initialization of the figure size
        self.DisplayChart()

    def Get(self):
        saved_s = self.SaveState()
        saved_r, _ = self.SaveRun()
        return (saved_s and saved_r), self._function


class LiquidPotentialTab(TypecurveTab):
    def __init__(self, parent, unit_system):
        super().__init__(parent)
        self._x_axis = Time()
        self._y_axis = LiquidPotential(unit_system)


class WaterCutTab(TypecurveTab):
    def __init__(self, parent, unit_system):
        super().__init__(parent)

        self._x_axis = OilCumulative(unit_system)
        self._y_axis = WaterCut(unit_system)

        self._allow_push = False


class GasOilRatioTab(TypecurveTab):
    def __init__(self, parent, unit_system):
        super().__init__(parent)

        self._x_axis = Time()
        self._y_axis = GasOilRatio(unit_system)


class FunctionFrame(ObjectDialog):
    def __init__(self, parent, unit_system, functions, profile=None):
        super().__init__(parent, title='Function')

        self._functions = functions
        self._profile = profile
        self._saved = False

        self.aui_panel = PropertiesAUIPanel(self.custom, min_size=(820, 450))

        liquid_panel = wx.Panel(self.custom)
        self.liquid_potential = LiquidPotentialTab(liquid_panel, unit_system)

        water_cut_panel = wx.Panel(self.custom)
        self.water_cut = WaterCutTab(water_cut_panel, unit_system)

        gor_panel = wx.Panel(self.custom)
        self.gas_oil_ratio = GasOilRatioTab(gor_panel, unit_system)

        self.aui_panel.AddPage(liquid_panel, self.liquid_potential, proportions=(1,),
                               title='Liquid pot. vs. time', bitmap=ico.liquid_rate_16x16.GetBitmap())

        self.aui_panel.AddPage(water_cut_panel, self.water_cut, proportions=(1,),
                               title='Water-cut vs. cum. oil', bitmap=ico.water_cut_16x16.GetBitmap())

        self.aui_panel.AddPage(gor_panel, self.gas_oil_ratio, proportions=(1,),
                               title='GOR vs. time', bitmap=ico.gas_oil_ratio_16x16.GetBitmap())

        self.SetMinSize(wx.Size(920, 600))
        self.InitUI()
        self.Load()
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.ok_button.Bind(wx.EVT_BUTTON, self.OnOKButton)

    def InitUI(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(ico.trend_chart_16x16.GetIcon())

        # sizing aui ---------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)
        self.custom.SetSizer(sizer)

        self.Realize()

    def OnOKButton(self, event):
        self.Save()

        if self._saved:
            self.Close(True)

    def Load(self):
        liquid, water, gor = self._functions.Get()
        self.liquid_potential.Set(liquid, self._profile)
        self.water_cut.Set(water, self._profile)
        self.gas_oil_ratio.Set(gor, self._profile)

    def Save(self):
        try:
            saved_l, liquid = self.liquid_potential.Get()
            saved_w, water = self.water_cut.Get()
            saved_g, gor = self.gas_oil_ratio.Get()

            if False in (saved_l, saved_w, saved_g):
                self._saved = False
                return
            else:
                self._functions.Set(liquid, water, gor)

        except TypeError:
            self._saved = False
            return

        self._saved = True

    def IsSaved(self):
        return self._saved

    def GetFunctions(self):
        return self._functions
