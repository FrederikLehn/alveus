import wx.adv
from wx.lib.agw.customtreectrl import EVT_TREE_ITEM_CHECKING, EVT_TREE_ITEM_CHECKED
from widgets.customized_menu import CustomMenu, CustomMenuItem

from curve_fit import HistoryModelFit, CurveModelFit, NonParametricModelFit, DCACumModelFit, DCATimeModelFit

import _icons as ico
from _errors import ConvergenceError
from utilities import ReturnProperty
from variable_mgr import Date, OilCumulative, LiquidPotential, WaterCut, GasOilRatio
from chart_mgr import *
from charts import SelectionChartPanel, GetVariableLabel
from widgets.customized_tree_ctrl import CustomizedTreeCtrl
from frames.frame_utilities import DeleteSingleTreeItem, DeleteMultipleTreeItems
from frames.frame_design import ObjectDialog, GAP, SMALL_GAP
from frames.property_panels import PropertiesAUIPanel, ModelPanel
import variable_mgr as vm


class Model:
    def __init__(self, id_, x_is_date=False):
        # data used for fitting (assigned on CurveFitFrame)
        self._x = None  # numpy array
        self._y = None  # numpy array

        # model used for function evaluation (assigned on CurveFitFrame)
        self._model_fit = None  # ModelFit class

        # included (assigned on FunctionFrame)
        self._include = False  # bool

        # merge parameters (assigned on FunctionFrame)
        self._merge_type = None   # id (int)
        self._merge_point = None  # float
        self._merge_rate = None   # float (for merge_type = smooth, else None)

        # modifiers (assigned on FunctionFrame)
        self._multiplier = None  # float
        self._addition = None    # float

        # gui options
        self._label = None
        self._type = None
        self._id = id_
        self._properties = None
        self._can_fit = True
        self._can_fit_best = False

        self._x_is_date = x_is_date
        self.Allocate()

    def Allocate(self):
        if self._x_is_date:
            self._x = np.array([], dtype='datetime64[D]')
        else:
            self._x = np.empty(0)

        self._y = np.empty(0)

    def AppendXY(self, x, y):
        self._x = np.append(self._x, x)
        self._y = np.append(self._y, y)

    def CanEditLabel(self):
        return True

    def CanFit(self):
        return self._can_fit

    def CanFitBest(self):
        return self._can_fit_best

    def ClearXY(self):
        self.Allocate()

    def ConvertValues(self):
        if self._x_is_date:
            self._model_fit.ConvertValues(self._x[0])

    def DefaultModel(self):
        # sub-class
        pass

    def GetFittingX(self):
        if self._x_is_date:
            return (self._x - self._x[0]).astype(np.float64)
        else:
            return self._x

    def GetId(self):
        return self._id

    def GetInput(self):
        return [self._model_fit.GetInput()] if self._model_fit.GetInput() is not None else []

    def GetLabel(self):
        return self._label

    def GetMerges(self):
        return self._merge_type, self._merge_point, self._merge_rate

    def GetMethod(self):
        return self._properties[0].GetChoices(self._model_fit.GetMethod())

    def GetModel(self):
        # used for transfer to the panel
        method = self._model_fit.GetMethod()

        if self._model_fit.GetFit() is not None:
            input_ = ReturnProperty(self._model_fit.GetInput(), default=None)
            parameters = copy.deepcopy(self._model_fit.GetParameters())

        else:
            input_ = None
            parameters = []

        while len(parameters) < 3:
            parameters.append(None)

        return (method, input_, *parameters)

    def GetModelFit(self):
        return self._model_fit

    def GetModifiers(self):
        return self._multiplier, self._addition

    def GetParameters(self):
        return [p for p in self._model_fit.GetParameters() if p is not None]

    def GetProperties(self):
        return self._properties

    def GetType(self):
        return self._type

    def GetValues(self):
        return self._model_fit.GetValues()

    def GetX(self):
        return self._x

    def GetXY(self):
        return self._x, self._y

    def GetY(self):
        return self._y

    def Include(self):
        return self._include

    def IsParametric(self):
        return self._model_fit.IsParametric()

    def RemoveXY(self, id_):
        self._x = np.delete(self._x, id_)
        self._y = np.delete(self._y, id_)

    def SetModel(self, method, input_, *parameters):
        # used specifically for transfer from the panel
        par = []
        for i, p in enumerate(parameters):
            if p is not None:
                par.append(p)
            elif self._model_fit.GetFit() is not None and i < self._model_fit.GetMinData():
                par.append(0.)

        self._model_fit.Set(method, input_, par)

    def SetInclude(self, include):
        self._include = include

    def SetLabel(self, label):
        self._label = label

    def SetMerges(self, merge_type, merge_point, merge_rate):
        self._merge_type = merge_type
        self._merge_point = merge_point
        self._merge_rate = merge_rate

    def SetModifiers(self, multiplier, addition):
        self._multiplier = multiplier
        self._addition = addition

    def SetX(self, x):
        self._x = x

    def SetY(self, y):
        self._y = y

    def Sort(self):
        p = np.argsort(self._x)
        self._x = self._x[p]
        self._y = self._y[p]

    def Update(self, model):
        self._include = model.Include()
        self._merge_type, self._merge_point, self._merge_rate = model.GetMerges()
        self._multiplier, self._addition = model.GetModifiers()

    def XIsDate(self):
        return self._x_is_date


class HistoryModel(Model):
    def __init__(self, id_, x_is_date=False):
        super().__init__(id_, x_is_date)
        self._label = 'History'
        self._type = 'history'

        self._properties = [vm.HistoryMethod(),
                            vm.HistoryInput(),
                            vm.HistoryParameter1(),
                            vm.HistoryParameter2(),
                            vm.HistoryParameter3()]

        self.DefaultModel()

    def DefaultModel(self):
        if not self._x.size:
            self._model_fit = HistoryModelFit(np.empty(0), np.empty(0))
            return

        self.Sort()
        self._model_fit = HistoryModelFit(self.GetFittingX(), self._y)

    def FindFit(self, method, input_=None):
        if not self._x.size:
            return

        self.DefaultModel()
        self._model_fit.find_fit(method, input_)
        self.ConvertValues()


class CurvefitModel(Model):
    def __init__(self, id_, x_is_date=False):
        super().__init__(id_, x_is_date)
        self._label = 'Curvefit'
        self._type = 'curvefit'

        self._properties = [vm.CurvefitMethod(),
                            vm.CurvefitInput(),
                            vm.CurvefitParameter1(),
                            vm.CurvefitParameter2(),
                            vm.CurvefitParameter3()]

        self._can_fit_best = True

        self.DefaultModel()

    def DefaultModel(self):
        if not self._x.size:
            self._model_fit = CurveModelFit(np.empty(0), np.empty(0))
            return

        self.Sort()
        self._model_fit = CurveModelFit(self.GetFittingX(), self._y)
        self.ConvertValues()

    def FindFit(self, method=None, input_=None):
        if not self._x.size:
            return

        self.DefaultModel()

        try:

            if method is not None:
                self._model_fit.find_fit(method)
            else:
                self._model_fit.find_best_fit()

            self.ConvertValues()

        except ConvergenceError as e:
            self.DefaultModel()

            box = wx.MessageDialog(None, message=str(e), caption='Convergence Error')
            box.ShowModal()
            box.Destroy()


class DCAModel(Model):
    def __init__(self, id_, x_is_date=False):
        super().__init__(id_, x_is_date)
        self._label = 'DCA'
        self._type = 'dca'

        self._properties = [vm.DCAMethod(),
                            vm.DCAInput(),
                            vm.DCAParameter1(),
                            vm.DCAParameter2(),
                            vm.DCAParameter3()]

        self.DefaultModel()

    def DefaultModel(self):
        if not self._x.size:

            if self._x_is_date:
                self._model_fit = DCATimeModelFit(np.empty(0), np.empty(0))
            else:
                self._model_fit = DCACumModelFit(np.empty(0), np.empty(0))

            return

        self.Sort()

        if self._x_is_date:
            self._model_fit = DCATimeModelFit(self.GetFittingX(), self._y)
        else:
            self._model_fit = DCACumModelFit(self.GetFittingX(), self._y)

        self.ConvertValues()

    def FindFit(self, method, input_=None):
        if not self._x.size:
            return

        self.DefaultModel()

        try:

            self._model_fit.find_fit(method, input_)
            self.ConvertValues()

        except ConvergenceError as e:

            self.DefaultModel()

            box = wx.MessageDialog(None, message=str(e), caption='Convergence Error')
            box.ShowModal()
            box.Destroy()


class NonParametricModel(Model):
    def __init__(self, id_,  x_is_date=False):
        super().__init__(id_, x_is_date)
        self._label = 'Non-parametric'
        self._type = 'non_parametric'

        self._properties = [vm.NonParametricMethod(),
                            vm.NonParametricInput(),
                            vm.NonParametricParameter1(),
                            vm.NonParametricParameter2(),
                            vm.NonParametricParameter3()]

        self._can_fit = False

        self.DefaultModel()

    def DefaultModel(self):
        self._model_fit = NonParametricModelFit(np.empty(0), np.empty(0))


class ModelTree(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, style=wx.SIMPLE_BORDER)
        self.tree = CustomizedTreeCtrl(self)
        self.tree.AddRoot('')

        # Create an image list to add icons next to an item
        il = wx.ImageList(16, 16)
        self._images = {'history':        il.Add(ico.history_fit_16x16.GetBitmap()),
                        'curvefit':       il.Add(ico.linear_fit_16x16.GetBitmap()),
                        'dca':            il.Add(ico.hyperbolic_dca_16x16.GetBitmap()),
                        'non_parametric': il.Add(ico.bow_wave_16x16.GetBitmap())}

        self.model_icon = il.Add(ico.fit_chart_16x16.GetBitmap())

        self.tree.SetImageList(il)
        self.tree._grayedImageList = self.tree.GetImageList()

        self.models = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.SetMinSize(wx.Size(100, 120))

        self.Populate()

    # external functions -----------------------------------------------------------------------------------------------
    def Get(self):
        return [item.GetData() for item in self.models.GetChildren()]

    def GetCheckedItems(self):
        return self.tree.GetCheckedItems()

    def GetItems(self):
        return self.models.GetChildren()

    def GetModelCount(self):
        return self.tree.GetChildrenCount(self.models)

    def GetUniqueId(self):
        ids = [data.GetId() for data in self.Get()]
        if ids:
            return max(ids) + 1
        else:
            return 0

    def Populate(self):
        root = self.tree.GetRootItem()

        self.models = self.tree.AppendItem(root, 'Models', data=None)
        self.tree.SetItemImage(self.models, self.model_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.models, self.model_icon, wx.TreeItemIcon_Expanded)

        self.tree.ExpandAll()

    def Set(self, models):
        for model in models:
            model = copy.deepcopy(model)
            child = self.tree.AppendItem(self.models, model.GetLabel(), ct_type=2, data=model)
            self.tree.SetItemImage(child, self._images[model.GetType()], wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(child, self._images[model.GetType()], wx.TreeItemIcon_Expanded)

        self.tree.ExpandAll()


class ConfigurableModelTree(ModelTree):
    def __init__(self, parent):
        super().__init__(parent)

        self.tree.SetAGWWindowStyleFlag(wx.TR_HAS_BUTTONS | wx.TR_MULTIPLE | wx.TR_HIDE_ROOT | wx.TR_EDIT_LABELS)

        self.drag_item = None

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEditLabel, self.tree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndEditLabel, self.tree)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag, self.tree)
        self.Bind(wx.EVT_TREE_END_DRAG, self.OnEndDrag, self.tree)

    # events -----------------------------------------------------------------------------------------------------------
    def OnBeginEditLabel(self, event):

        textctrl = event.GetEventObject().GetEditControl()
        textctrl.SelectAll()

        event.Allow()

    def OnEndEditLabel(self, event):
        item = event.GetItem()
        data = item.GetData()

        if event.GetLabel():
            data.SetLabel(event.GetLabel())
        else:
            event.Veto()

    def OnBeginDrag(self, event):
        selections = self.tree.GetSelections()

        # check if any of the selections is a first child of the root or a separator
        root = self.tree.GetRootItem()
        for item in selections:
            if item.GetParent() == root or item.IsSeparator() or item is self.models:
                event.Veto()
                return

        self.drag_item = selections
        event.Allow()

    def OnEndDrag(self, event):
        if self.drag_item is None or not len(self.drag_item):
            return

        drag_target = event.GetItem()
        if drag_target is None:
            return

        # check whether dragged to parent or to another function
        drag_parent = self.drag_item[0].GetParent()
        if drag_parent is drag_target:
            # dragged to parent
            index = -1
            target = drag_target

        else:
            # Same item type
            index = drag_target.GetParent().GetChildren().index(drag_target)
            target = drag_target.GetParent()

        self.MoveNodes(target, self.drag_item, index)
        drag_target.Expand()

    def MoveNodes(self, target, sources, index):
        tree = self.tree
        tree.Freeze()

        counter = 0
        for idx in range(index + 1, index + 1 + len(sources)):
            source = sources[counter]

            item = tree.InsertItem(target, idx, source.GetText(), ct_type=source.GetType(), image=source.GetImage(), data=source.GetData())
            tree.CheckItem2(item, source.IsChecked(), False)
            counter += 1

        for source in sources:
            tree.Delete(source)

        tree.Thaw()

    def AddModel(self, model):
        child = self.tree.AppendItem(self.models, model.GetLabel(), ct_type=2, data=model)
        self.tree.SetItemImage(child, self._images[model.GetType()], wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(child, self._images[model.GetType()], wx.TreeItemIcon_Expanded)

        self.tree.ExpandAll()

    def HandleDelete(self, tree):
        items = tree.GetSelections()

        if self.AllowDelete(items):
            self.GetParent().OnDeleteModels(None, items)

    def AllowDelete(self, items):
        for item in items:
            if item is self.models:
                return False

        return True


class CurveFitChartPanel(SelectionChartPanel):
    def __init__(self, parent):
        super().__init__(parent)

        self._model = None

        # events -------------------------------------------------------------------------------------------------------
        self.fig.canvas.mpl_connect('button_press_event', self.OnClicked)

    def Realize(self, axes_item=None, ax=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder()
            return

        # Create required axes' ----------------------------------------------------------------------------------------
        if ax is None:
            self.fig.clf()
            ax = self.fig.add_subplot(1, 1, 1)
            self.SetRectangleSelector(ax)
        else:
            ax.clear()

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

        if self._selection is not None:
            ax.plot(*self._selection.GetXY(), **self._selection.GetOptions())

        ax.legend(handles=axes_item.GetLegend())
        ax.minorticks_on()
        ax.grid(True)

        # draw chart on canvas
        self.canvas.draw()

        # required for being able to deselect when not triggering rectangle selector
        self._ax = ax

        # saved such that the chart can be redrawn with a highlighted selection
        self._axes_item = axes_item
        self._data = axes_item.GetLines()[0]

    # ==================================================================================================================
    # events
    # ==================================================================================================================
    def OnClicked(self, event):
        if self._rs is None:
            return

        if event.button == 1:

            self.ClearSelection()
            self._rs.set_active(True)

        if event.button == 2:

            self._rs.set_active(False)

        if event.button == 3:

            self._rs.set_active(False)
            self.OnRightClick(event)

    def OnRightClick(self, event):
        if self._model is None:
            return

        context_menu = CustomMenu(self)
        append = context_menu.Append(wx.ID_ANY, 'Append selection to data')
        remove = context_menu.Append(wx.ID_ANY, 'Remove selection from data')
        context_menu.AppendSeparator()
        clear = context_menu.Append(wx.ID_ANY, 'Clear data')

        self.Bind(wx.EVT_MENU, self.OnAppend, append)
        self.Bind(wx.EVT_MENU, self.OnRemove, remove)
        self.Bind(wx.EVT_MENU, self.OnClear,  clear)

        context_menu.CustomPopup()

    def OnAppend(self, event):

        for (x, y) in zip(*self._selection.GetXY()):

            add_x = self._model.GetX()

            if x not in add_x:
                self._model.AppendXY(x, y)

        self._selection.ClearXY()
        self.GetParent().DisplayChart(self._model)

    def OnRemove(self, event):
        id_ = []

        for i, (x, y) in enumerate(zip(*self._model.GetXY())):

            sel_x, sel_y = self._selection.GetXY()

            if (x in sel_x) and (y in sel_y):
                id_.append(i)

        if id_:
            self._model.RemoveXY(id_)

        self._selection.ClearXY()
        self.GetParent().DisplayChart(self._model)

    def OnClear(self, event):
        self._model.ClearXY()

        self._selection.ClearXY()
        self.GetParent().DisplayChart(self._model)

    # internal events --------------------------------------------------------------------------------------------------
    def GetTooltipParams(self, event):
        return self.GetLineTooltipParams(event)

    # external events --------------------------------------------------------------------------------------------------
    def ChangeModel(self, model):
        self._model = model


class CurveFitTab(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self._x_axis = None  # class from VariableManager
        self._y_axis = None  # class from VariableManager
        self._model = None
        self._has_data = False

        self._profile = None

        self.chart = CurveFitChartPanel(self)
        self.model_tree = ConfigurableModelTree(self)
        self.model = ModelPanel(self)
        self.model.Enable(False)

        self.find_fit = wx.Button(self, wx.ID_ANY, 'Find fit')
        self.find_best_fit = wx.Button(self, wx.ID_ANY, 'Find best fit')
        self.find_fit.Enable(False)
        self.find_best_fit.Enable(False)

        self.InitUI()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnTreeItemRightClicked, self.model_tree.tree)
        self.Bind(EVT_TREE_ITEM_CHECKING, self.OnTreeItemChecking, self.model_tree.tree)
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnTreeItemChecked, self.model_tree.tree)
        self.find_fit.Bind(wx.EVT_BUTTON, self.OnFindFit)
        self.find_best_fit.Bind(wx.EVT_BUTTON, lambda evt: self.OnFindFit(evt, True))

    def InitUI(self):
        self.SetBackgroundColour(wx.WHITE)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        button_sizer.Add(self.find_fit,      0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        button_sizer.Add(self.find_best_fit, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)

        # sizing & layout ----------------------------------------------------------------------------------------------
        input_sizer.Add(self.model_tree, 1, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        input_sizer.Add(self.model,      0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        input_sizer.Add(button_sizer,    0, wx.EXPAND | wx.ALL, GAP)

        sizer.Add(input_sizer, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        sizer.Add(wx.StaticLine(self, wx.ID_ANY, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx. ALL, GAP)
        sizer.Add(self.chart, 1, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)

        self.SetSizer(sizer)
        sizer.Fit(self)

    # events -----------------------------------------------------------------------------------------------------------
    def OnTreeItemRightClicked(self, event):
        tree = event.GetEventObject()
        page = tree.GetParent()
        items = tree.GetSelections()

        if len(items) > 1:

            self.TreeItemRightClickMultiple(page, items)

        elif len(items):

            self.TreeItemRightClickSingle(items[0])

        else:
            return

    def TreeItemRightClickSingle(self, item):

        context_menu = CustomMenu(self)

        if item == self.model_tree.models:

            history = CustomMenuItem(context_menu, wx.ID_ANY, 'Add history')
            history.SetBitmap(ico.history_fit_16x16.GetBitmap())
            context_menu.AppendItem(history)

            if not self._has_data:
                history.Enable(False)

            curvefit = CustomMenuItem(context_menu, wx.ID_ANY, 'Add curvefit')
            curvefit.SetBitmap(ico.linear_fit_16x16.GetBitmap())
            context_menu.AppendItem(curvefit)

            dca = CustomMenuItem(context_menu, wx.ID_ANY, 'Add DCA')
            dca.SetBitmap(ico.hyperbolic_dca_16x16.GetBitmap())
            context_menu.AppendItem(dca)

            non_parametric = CustomMenuItem(context_menu, wx.ID_ANY, 'Add non-parametric')
            non_parametric.SetBitmap(ico.bow_wave_16x16.GetBitmap())
            context_menu.AppendItem(non_parametric)

            # events
            x_is_date = isinstance(self._x_axis, Date)
            id_ = self.model_tree.GetUniqueId()
            self.Bind(wx.EVT_MENU, lambda e: self.OnAddFunction(e, HistoryModel(id_, x_is_date)), history)
            self.Bind(wx.EVT_MENU, lambda e: self.OnAddFunction(e, CurvefitModel(id_, x_is_date)), curvefit)
            self.Bind(wx.EVT_MENU, lambda e: self.OnAddFunction(e, DCAModel(id_, x_is_date)), dca)
            self.Bind(wx.EVT_MENU, lambda e: self.OnAddFunction(e, NonParametricModel(id_, x_is_date)), non_parametric)

        else:

            delete = CustomMenuItem(context_menu, wx.ID_ANY, 'Delete')
            delete.SetBitmap(ico.delete_16x16.GetBitmap())
            context_menu.AppendItem(delete)

            self.Bind(wx.EVT_MENU, lambda e: self.OnDeleteModel(e, item), delete)

        context_menu.CustomPopup()

    def TreeItemRightClickMultiple(self, page, items):
        can_delete = True

        for item in items:
            if item is page.models:
                can_delete = False

        context_menu = CustomMenu(self)

        if can_delete:
            delete = CustomMenuItem(context_menu, wx.ID_ANY, 'Delete')
            delete.SetBitmap(ico.delete_16x16.GetBitmap())
            context_menu.AppendItem(delete)

            self.Bind(wx.EVT_MENU, lambda e: self.OnDeleteModels(e, items), delete)

        context_menu.CustomPopup()

    # events -----------------------------------------------------------------------------------------------------------
    def OnAddFunction(self, event, model):
        self.model_tree.AddModel(model)

    def OnDeleteModel(self, event, item):
        DeleteSingleTreeItem(self, item, self.DeleteModel)

    def OnDeleteModels(self, event, items):
        DeleteMultipleTreeItems(self, items, self.DeleteModel)
        #for item in items:
        #    self.OnDeleteModel(event, item)

    def DeleteModel(self, event, item):
        model = item.GetData()
        if model is self._model:
            self.DisplayChart()
            self.model.Clear()
            self.model.Enable(False)
            self.find_fit.Enable(False)
            self.find_best_fit.Enable(False)

            self._model = None

        self.model_tree.tree.Delete(item)

    def OnTreeItemChecking(self, event):
        # save existing state
        saved = self.SaveState()

        if not saved:
            event.Veto()
        else:
            event.Skip()

    def OnTreeItemChecked(self, event):
        self.model.Enable(True)

        item = event.GetItem()
        model = item.GetData()

        self.chart.ChangeModel(model)

        # load parameters
        self.model.ChangeProperties(*model.GetProperties())
        self.LoadState(model)
        self.model.UpdateText(self.model.GetSelection())

        if self._has_data:
            self.find_fit.Enable(model.CanFit())
            self.find_best_fit.Enable(model.CanFitBest())

        self.DisplayChart(model)

        self._model = model

    def OnFindFit(self, event, best=False):
        if self._model is None:
            return

        if best:
            self._model.FindFit()
        else:
            model = self.model.Get()
            method = model[0]
            input_ = model[1]

            if method is None:
                return

            self._model.FindFit(method, input_)

        # writing results to the panel
        self.LoadState(self._model)
        self.model.UpdateText(self.model.GetSelection())

        # plotting results
        self.DisplayChart(self._model)

    # internal functions -----------------------------------------------------------------------------------------------
    def LoadState(self, model):
        if model is not None:
            self.model.Set(*model.GetModel())

    def SaveState(self):
        if self._model is not None:
            model = self.model.Get()

            if model:
                self._model.SetModel(*model)
            else:
                return False

        return True

    # external functions -----------------------------------------------------------------------------------------------
    def DisplayChart(self, model=()):
        if model:
            model = (model,)

        if self._profile is not None:
            axes_item = AxesItem()
            axes_item.MergeFits(self._profile, [self._x_axis], [self._y_axis], [model])
        else:
            axes_item = None

        self.chart.Realize(axes_item)

    def Get(self):
        saved = self.SaveState()
        return saved, self.model_tree.Get()

    def Set(self, function, profile=None):
        self.model_tree.Set(function.GetModels())

        if profile is not None:
            self._profile = profile
            self._has_data = True

        self.chart.Realize()  # required for initialization of the figure size
        self.DisplayChart()


class LiquidPotentialTab(CurveFitTab):
    def __init__(self, parent, unit_system):
        super().__init__(parent)
        self._x_axis = Date()
        self._y_axis = LiquidPotential(unit_system)


class WaterCutTab(CurveFitTab):
    def __init__(self, parent, unit_system):
        super().__init__(parent)
        self._x_axis = OilCumulative(unit_system)
        self._y_axis = WaterCut(unit_system)


class GasOilRatioTab(CurveFitTab):
    def __init__(self, parent, unit_system):
        super().__init__(parent)
        self._x_axis = Date()
        self._y_axis = GasOilRatio(unit_system)


class CurveFitFrame(ObjectDialog):
    def __init__(self, parent, unit_system, functions, profile=None):
        super().__init__(parent, title='Curve fit')

        self._functions = functions
        self._profile = profile
        self._saved = True

        self.aui_panel = PropertiesAUIPanel(self.custom, min_size=(730, 370))

        liquid_panel = wx.Panel(self.custom)
        self.liquid_potential = LiquidPotentialTab(liquid_panel, unit_system)

        water_cut_panel = wx.Panel(self.custom)
        self.water_cut = WaterCutTab(water_cut_panel, unit_system)

        gor_panel = wx.Panel(self.custom)
        self.gas_oil_ratio = GasOilRatioTab(gor_panel, unit_system)

        # add tabs to aui
        self.aui_panel.AddPage(liquid_panel, self.liquid_potential, proportions=(1,),
                               title='Liquid pot. vs. time', bitmap=ico.liquid_rate_16x16.GetBitmap())

        self.aui_panel.AddPage(water_cut_panel, self.water_cut, proportions=(1,),
                               title='Water-cut vs. cum. oil', bitmap=ico.water_cut_16x16.GetBitmap())

        self.aui_panel.AddPage(gor_panel, self.gas_oil_ratio, proportions=(1,),
                               title='GOR vs. time', bitmap=ico.gas_oil_ratio_16x16.GetBitmap())

        self.SetMinSize(wx.Size(800, 520))
        self.InitUI()
        self.Load()
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.ok_button.Bind(wx.EVT_BUTTON, self.OnOKButton)

    def InitUI(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(ico.fit_chart_16x16.GetIcon())

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
            else:
                self._functions.SetModels(liquid, water, gor)

        except TypeError:
            self._saved = False

    def IsSaved(self):
        return self._saved

    def GetFunctions(self):
        return self._functions
