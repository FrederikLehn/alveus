# generic imports ------------------------------------------------------------------------------------------------------
import os
import gc
import pickle
from pubsub import pub
import matplotlib.pyplot as plt


# wxPython imports -----------------------------------------------------------------------------------------------------
from wx.lib.agw.persist import PersistenceManager
from wx.lib.agw.customtreectrl import EVT_TREE_ITEM_CHECKED
from wx.lib.agw.ribbon import EVT_RIBBONBUTTONBAR_CLICKED, EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED
from wx.lib.agw.aui import EVT_AUINOTEBOOK_PAGE_CHANGING, EVT_AUINOTEBOOK_PAGE_CHANGED, EVT_AUINOTEBOOK_PAGE_CLOSE,\
    EVT_AUINOTEBOOK_PAGE_CLOSED


# Alveus imports -------------------------------------------------------------------------------------------------------
from _ids import *
import _icons as ico
from widgets.customized_menu import CustomMenu, CustomMenuItem
from settings import Settings
from entity_mgr import EntityManager
from variable_mgr import VariableManager
from chart_mgr import ChartManager, CartesianChart, StackedChart, BarChart, BubbleChart, HistogramChart, MapChart,\
    ThreeDChart, FitChart, AxesItem

from object_menu import ObjectMenu
from display import Display
from ribbon import Ribbon

from frames.frame_utilities import GetFilePath, DeleteSingleTreeItem, DeleteMultipleTreeItems, MoveFolderOntoFolder,\
    RelativeDragIndex
from frames.settings_frame import SettingsFrame
from frames.auxiliary_frames import DuplicateFrame
from frames.export_frame import ExportFrame
from frames.import_frames import ProfileImportFrame
from frames.scenario_frame import ScenarioFrame
from frames.entity_frames import HistoryFrame, PredictionFrame, ScalingFrame
from frames.correlation_frame import EntityCorrelationFrame, VariableCorrelationFrame
from frames.variable_frame import ProductionVariableFrame, SummaryVariableFrame
from frames.entity_frames import FieldFrame, BlockFrame, ReservoirFrame, ThemeFrame, PolygonFrame, \
                                      ProjectFrame, PlatformFrame, ProducerFrame, InjectorFrame, \
                                      ProcessorFrame, PipelineFrame, AnalogueFrame, TypecurveFrame


# ----------------------------------------------------------------------------------------------------------------------


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Alveus', style=wx.DEFAULT_FRAME_STYLE)

        # project, settings and managers
        self._enabled = False
        self._project_path = None
        self._settings = None
        self._entity_mgr = None
        self._variable_mgr = None
        self._chart_mgr = None
        self._persist_mgr = PersistenceManager.Get()

        # pre-allocate objects
        self.panel = wx.Panel(self)
        self.splitter = wx.SplitterWindow(self.panel, wx.ID_ANY, style=wx.SP_THIN_SASH | wx.SP_LIVE_UPDATE)

        # primary components displayed on interface
        self.ribbon = Ribbon(self.panel)
        self.object_menu = ObjectMenu(self.splitter)
        self.display = Display(self.splitter)
        self.status_bar = self.CreateStatusBar(1)

        # used for drag & drop
        self._drag_items = None

        # used for copy, cut and paste
        self._cut = False       # true if cut, false if copy
        self._copy_tree = None  # used to check if copy_tree is paste_tree
        self._copy_items = None

        # chart display modes
        self._present = False

        # locking of open frames to avoid the same frame being opened twice (object_menu items handled separately)
        self._corr_ent_locked = False
        self._corr_var_locked = False

        self.InitUI()

        self.Maximize()
        self.SetMinSize(self.GetSize())

        # ==============================================================================================================
        # Events
        # ==============================================================================================================
        # object menu events -------------------------------------------------------------------------------------------
        # checking events
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnTreeItemChecked,   self.object_menu.entities.tree)
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnTreeItemChecked,   self.object_menu.projects.tree)
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnTreeItemChecked,   self.object_menu.variables.tree)
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnWindowItemChecked, self.object_menu.windows.tree)

        # clicking events
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnEntityRightClick,    self.object_menu.entities.tree)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED,   self.OnEntityDoubleClick,   self.object_menu.entities.tree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnEntityRightClick,    self.object_menu.projects.tree)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED,   self.OnEntityDoubleClick,   self.object_menu.projects.tree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnVariableRightClick,  self.object_menu.variables.tree)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED,   self.OnVariableDoubleClick, self.object_menu.variables.tree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnWindowRightClick,    self.object_menu.windows.tree)

        # drag & drop events
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag, self.object_menu.entities.tree)
        self.Bind(wx.EVT_TREE_END_DRAG,   self.OnEndDrag,   self.object_menu.entities.tree)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag, self.object_menu.projects.tree)
        self.Bind(wx.EVT_TREE_END_DRAG,   self.OnEndDrag,   self.object_menu.projects.tree)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag, self.object_menu.windows.tree)
        self.Bind(wx.EVT_TREE_END_DRAG,   self.OnEndDrag,   self.object_menu.windows.tree)

        # edit label events
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEditLabel, self.object_menu.entities.tree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT,   self.OnEndEditLabel,   self.object_menu.entities.tree)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEditLabel, self.object_menu.projects.tree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT,   self.OnEndEditLabel,   self.object_menu.projects.tree)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEditLabel, self.object_menu.windows.tree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT,   self.OnEndEditLabel,   self.object_menu.windows.tree)

        # display events -----------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_COMBOBOX, self.OnOptionsBarChanged, self.display.options_bar.data)
        self.Bind(wx.EVT_COMBOBOX, self.OnOptionsBarChanged, self.display.options_bar.uncertainty)
        self.Bind(wx.EVT_COMBOBOX, self.OnOptionsBarChanged, self.display.options_bar.split)
        self.Bind(wx.EVT_COMBOBOX, self.OnOptionsBarChanged, self.display.options_bar.group)
        self.Bind(wx.EVT_COMBOBOX, self.OnOptionsBarChanged, self.display.options_bar.colour)

        self.Bind(EVT_AUINOTEBOOK_PAGE_CHANGING, self.OnPageChanging,  self.display.notebook, id=wx.NewId())
        self.Bind(EVT_AUINOTEBOOK_PAGE_CHANGED,  self.OnPageChanged,   self.display.notebook, id=wx.NewId())
        self.Bind(EVT_AUINOTEBOOK_PAGE_CLOSE,    self.OnPageClosing,   self.display.notebook, id=wx.NewId())
        self.Bind(EVT_AUINOTEBOOK_PAGE_CLOSED,   self.OnPageClosed,    self.display.notebook, id=wx.NewId())

        # ribbon bar events --------------------------------------------------------------------------------------------
        # file
        self.Bind(wx.EVT_MENU, self.OnSave,            self.ribbon.file_menu.save)
        self.Bind(wx.EVT_MENU, self.OnSaveAs,          self.ribbon.file_menu.save_as)
        self.Bind(wx.EVT_MENU, self.OnOpenProject,     self.ribbon.file_menu.open)
        self.Bind(wx.EVT_MENU, self.OnCloseProject,    self.ribbon.file_menu.close)
        self.Bind(wx.EVT_MENU, self.OnNewProject,      self.ribbon.file_menu.new)
        self.Bind(wx.EVT_MENU, self.OnProjectSettings, self.ribbon.file_menu.settings)

        # window
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnAddWindow, id=ID_WINDOW)
        self.Bind(EVT_RIBBONBUTTONBAR_DROPDOWN_CLICKED, self.OnWindowDropdown, id=ID_WINDOW)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnRefreshWindow, id=ID_WINDOW_REFRESH)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnPresentMode, id=ID_WINDOW_PRESENT)

        # add folder
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnAddFolder, id=ID_FOLDER)

        # add chart
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, lambda e: self.OnAddChart(e, CartesianChart()), id=ID_CHART_CARTESIAN)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, lambda e: self.OnAddChart(e, StackedChart()),   id=ID_CHART_STACKED)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, lambda e: self.OnAddChart(e, BarChart()),       id=ID_CHART_BAR)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, lambda e: self.OnAddChart(e, BubbleChart()),    id=ID_CHART_BUBBLE)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, lambda e: self.OnAddChart(e, HistogramChart()), id=ID_CHART_HISTOGRAM)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, lambda e: self.OnAddChart(e, MapChart()),       id=ID_CHART_MAP)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, lambda e: self.OnAddChart(e, ThreeDChart()),    id=ID_CHART_3D)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, lambda e: self.OnAddChart(e, FitChart()),       id=ID_CHART_FIT)
        # self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnAddChart, id=ID_CHART_TREND)
        # self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnAddChart, id=ID_CHART_INCREMENT)
        # self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnAddChart, id=ID_CHART_PROFILES)

        # import/export
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnExportMultiple, id=ID_EXPORT_EXCEL)

        # summary
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenVariableFrame, id=ID_SUMMARY)

        # add entity
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_FIELD)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_BLOCK)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_RESERVOIR)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_THEME)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_POLYGON)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_ANALOGUE)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_TYPECURVE)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_SCALING)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_PLATFORM)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_PROCESSOR)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_PIPELINE)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_PRODUCER)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_INJECTOR)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_PROJECT)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_HISTORY)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_SCENARIO)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityFrame, id=ID_PREDICTION)

        # correlation groups
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenEntityCorrelationFrame,   id=ID_CORRELATION_ENT)
        self.Bind(EVT_RIBBONBUTTONBAR_CLICKED, self.OnOpenVariableCorrelationFrame, id=ID_CORRELATION_VAR)

        # close application
        self.Bind(wx.EVT_CLOSE, self.OnCloseApplication)

        # ==============================================================================================================
        # PyPubSub
        # ==============================================================================================================
        pub.subscribe(self.ActivateChart, 'activate_chart')
        pub.subscribe(self.EntityCorrelationClosed, 'entity_correlation_closed')
        pub.subscribe(self.VariableCorrelationClosed, 'variable_correlation_closed')
        pub.subscribe(self.EntityAdded, 'entity_added')
        pub.subscribe(self.PointerUpdated, 'pointer_updated')
        pub.subscribe(self.SummaryAdded, 'summary_added')
        pub.subscribe(self.SettingsUpdated, 'settings_updated')

    def InitUI(self):
        self.splitter.SplitVertically(self.object_menu, self.display, 350)
        self.ribbon.EnableButtons(False)
        self.display.EnableOptionsBar(False)

        self.status_bar.SetStatusText('Made by Frederik Winkel Lehn, J0514243')

        # sizing and layout --------------------------------------------------------------------------------------------
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ribbon, 0, wx.EXPAND)
        sizer.Add(self.splitter, 1, wx.EXPAND)

        self.panel.SetSizer(sizer)
        self.Layout()
        self.Show()

    # ==================================================================================================================
    # Object Menu Functions
    # ==================================================================================================================
    # Check tree items functions ---------------------------------------------------------------------------------------
    def OnTreeItemChecked(self, event):
        ids = self.display.GetActiveIds()
        chart = self._chart_mgr.GetChart(*ids)

        # item = event.GetItem()
        # # if in radio-button mode, uncheck all other radiobuttons (independent of parent)
        # if item.GetType() == 2:
        #     tree = event.GetEventObject()
        #     tree.GetParent().UncheckOtherRadioButtons(item)
        #     tree.GetParent().EnableChildRadioButtons()

        # draw chart
        self.DisplayChart(chart)

    def OnWindowItemChecked(self, event):
        item = event.GetItem()
        state = item.IsChecked()
        data = item.GetData()

        if data.IsWindow():

            if state:
                window = self._chart_mgr.GetWindow(data.GetId())
                self.PageOpening(window)
            else:
                # close page in display
                index = self.display.GetWindowIndex(data.GetId())
                self.PageClosing(index)
                self.PageClosed()
                self.display.ClosePage(index)

        else:  # chart

            parent = item.GetParent()
            if not parent.IsChecked():
                return

            id_ = parent.GetData().GetId()

            index = self.display.GetWindowIndex(id_)
            self.display.SetSelection(index)

            if id_ is not None:
                self.OnRefreshWindow(None, True)

    # click tree items functions ---------------------------------------------------------------------------------------
    def OnEntityRightClick(self, event):

        if not self._enabled:
            return

        tree = event.GetEventObject()
        items = tree.GetSelections()

        if len(items) > 1:

            self.EntityRightClickMultiple(tree, items)

        elif len(items):

            self.EntityRightClickSingle(tree, items[0])

        else:
            return

    def EntityRightClickSingle(self, tree, item):

        data = item.GetData()

        context_menu = CustomMenu(self)

        if data is None:
            return

        page = tree.GetParent()

        if data.IsPointer():
            # add open option
            entity = self._entity_mgr.GetEntity(*data.GetPointer())

            context_menu.AppendOpenItem(lambda e: self.OnOpenEntityFrame(e, entity.GetType(), item=item))
            context_menu.AppendSeparator()
            # TODO: Add rename options, which initiates the EDIT_LABEL event

        else:
            entity = None

        # options for adding new children (maximum of 2 options). For some reason binding of events does not work
        # properly when looping over them, so hard-coding additions TODO: fix this
        child_types, texts, icons = GetPrimaryChildrenInput(data.GetType())

        if child_types:
            context_menu.AppendGenericItem('Add ' + texts[0],
                                           lambda e: self.OnOpenEntityFrame(e, child_types[0], item_parent=item),
                                           bitmap=icons[0])

            if len(child_types) == 2:
                context_menu.AppendGenericItem('Add ' + texts[1],
                                               lambda e: self.OnOpenEntityFrame(e, child_types[1], item_parent=item),
                                               bitmap=icons[1])

        # option for adding a folder
        if data.GetChildType() is not None:
            context_menu.AppendGenericItem('Add folder', lambda e: self.OnAddFolder(e, item=item, page=page),
                                           bitmap=ico.folder_closed_16x16.GetBitmap())

        if data.IsPointer():

            # duplicate options
            if not entity.IsControlled():

                context_menu.AppendGenericItem('Create duplicates', lambda e: self.OnDuplicateEntity(e, item, page))

            else:

                context_menu.AppendGenericItem('Sever control', lambda e: self.OnSeverEntityControl(e, item))

            # cut, copy and paste options
            context_menu.AppendSeparator()
            context_menu.AppendCutItem(lambda evt: self.OnCopyEntities(evt, tree, [item], cut=True))
            context_menu.AppendCopyItem(lambda evt: self.OnCopyEntities(evt, tree, [item]))
            paste = context_menu.AppendPasteItem(lambda evt: self.OnPasteEntities(evt, tree, item))

            if self._copy_items is None:
                paste.Enable(False)

            # export options
            if entity.IsSimulationHolder():

                context_menu.AppendSeparator()
                context_menu.AppendExportExcel(lambda evt: self.OnExportMultiple(evt, [entity]))

        # collapse and expand options
        context_menu.AppendSeparator()
        context_menu.AppendCollapseItem(page.OnCollapseAll)
        context_menu.AppendExpandItem(page.OnExpandAll)

        # delete option
        if data.IsPointer() or data.IsFolder():

            context_menu.AppendSeparator()
            context_menu.AppendDeleteItem(lambda e: self.OnDeleteEntity(e, item, page))

        context_menu.CustomPopup()

    def EntityRightClickMultiple(self, tree, items):
        entities = []
        can_sever = True    # all entities have to be controlled by another entity
        can_export = True   # all entities have to be SimulationHolders
        can_delete = True   # all entities have to have the same type

        rep_type = None

        # conduct various checks
        for i, item in enumerate(items):

            if item.IsSeparator():
                return

            data = item.GetData()
            if not data.IsPointer():
                return

            if i == 0:
                rep_type = data.GetType()

            if not data.IsType(rep_type):
                can_delete = False

            entity = self._entity_mgr.GetEntity(*data.GetPointer())

            if not entity.IsControlled():
                can_sever = False

            if entity.IsSimulationHolder():
                entities.append(entity)
            else:
                can_export = False

        context_menu = CustomMenu(self)

        context_menu.AppendCutItem(lambda evt: self.OnCopyEntities(evt, tree, items, cut=True))
        context_menu.AppendCopyItem(lambda evt: self.OnCopyEntities(evt, tree, items))
        paste = context_menu.AppendPasteItem(lambda evt: self.OnPasteEntities(evt, tree, items[-1]))

        if self._copy_items is None:
            paste.Enable(False)

        context_menu.AppendSeparator()

        if can_sever:
            context_menu.AppendGenericItem('Sever control', lambda e: self.OnSeverEntityControls(e, items))
            context_menu.AppendSeparator()

        if can_export:
            context_menu.AppendExportExcel(lambda evt: self.OnExportMultiple(evt, entities))
            context_menu.AppendSeparator()

        page = tree.GetParent()
        context_menu.AppendCollapseItem(page.OnCollapseAll)
        context_menu.AppendExpandItem(page.OnExpandAll)

        if can_delete:
            context_menu.AppendSeparator()
            context_menu.AppendDeleteItem(lambda e: self.OnDeleteEntities(e, items, page))

        context_menu.CustomPopup()

    def OnDeleteEntity(self, event, item, *args):
        DeleteSingleTreeItem(self, item, self.DeleteEntity, *args)

    def OnDeleteEntities(self, event, items, *args):
        DeleteMultipleTreeItems(self, items, self.DeleteEntity, *args)

    def DeleteEntity(self, event, item, page):
        self.DeletePrimaryChildEntities(item, page)

        data = item.GetData()
        if data.IsEntity():  # alternative is a folder
            entity = self._entity_mgr.GetEntity(*data.GetPointer())
            self._entity_mgr.DeleteEntity(entity)

            # send PyPubSub signal to open frames to check if the deleted item was open, then close the frame
            if data.IsLocked():
                pub.sendMessage('entity_deleted', id_=data.GetId())

        # update derived properties of the deleted items parent (now that it has lost child entities)
        parent_data = page.GetNonFolderParent(item).GetData()
        if parent_data.IsPointer():
            parent = self._entity_mgr.GetEntity(*parent_data.GetPointer())
            self._entity_mgr.UpdateDerivedProperties(parent)

        if data.IsEntity():
            checked = item.IsChecked()

            page.DeleteEntity(item)
            self.UpdateDependencies()

            if checked:
                self.SaveChartState()
                self.RedisplayChart()

        else:  # folder
            page.tree.Delete(item)

    def DeletePrimaryChildEntities(self, item, page):
        # recursively delete all children which has the item as a primary entity (child on the treectrl)
        # of the deleted item from the entity manager
        tree = page.tree
        child, cookie = tree.GetFirstChild(item)

        while child:
            data = child.GetData()

            if data.IsEntity():  # alternative is a folder
                entity = self._entity_mgr.GetEntity(*data.GetPointer())
                self._entity_mgr.DeleteEntity(entity)

                # send PyPubSub signal to open frames to check if the deleted item was open, then close the frame
                pub.sendMessage('entity_deleted', id_=data.GetId())

            self.DeletePrimaryChildEntities(child, page)
            child, cookie = self.object_menu.entities.tree.GetNextChild(item, cookie)

    def OnDuplicateEntity(self, event, item, page):
        DuplicateFrame(self, self._entity_mgr, page, item).Show()

    def OnSeverEntityControl(self, event, item):
        entity = self._entity_mgr.GetEntity(*item.GetData().GetPointer())
        self._entity_mgr.SeverControl(entity)

    def OnSeverEntityControls(self, event, items):
        for item in items:
            self.OnSeverEntityControl(None, item)

    def OnSetVariableAsAxis(self, event, item, axis_id):
        ids = self.display.GetActiveIds()
        self.object_menu.variables.SetItemAsAxis(item, *ids, axis_id)

        chart = self._chart_mgr.GetChart(*self.display.GetActiveIds())
        self.DisplayChart(chart)

    def OnVariableRightClick(self, event):
        if not self._enabled:
            return

        tree = event.GetEventObject()
        page = tree.GetParent()
        items = tree.GetSelections()

        if len(items) > 1:

            self.VariableRightClickMultiple(page, items)

        elif len(items):

            self.VariableRightClickSingle(page, items[0])

        else:
            return

    def VariableRightClickSingle(self, page, item):
        if not self._enabled:
            return

        data = item.GetData()

        if data is None:
            return

        context_menu = CustomMenu(self)

        if data.IsPointer():

            # open variable or summary
            type_id = data.GetTypeId()
            open_ = None

            if type_id in (ID_POTENTIAL, ID_RATE, ID_CUMULATIVE, ID_RATIO, ID_SUMMARY):
                context_menu.AppendOpenItem(lambda e: self.OnOpenVariableFrame(e, type_id=type_id, item=item))

            if type_id == ID_SUMMARY:
                context_menu.AppendSeparator()
                context_menu.AppendDeleteItem(lambda e: self.OnDeleteSummary(e, item))

            # allow assigning as variables as x, y, z, etc. if chart allows it
            ids = self.display.GetActiveIds()

            if ids is not None:
                chart = self._chart_mgr.GetChart(*ids)

                item_types = chart.GetAllowedAssign()

                if data.GetType() in item_types[1]:

                    if open_ is not None:
                        context_menu.AppendSeparator()

                    if chart.IncludesSort():
                        context_menu.AppendGenericItem('Set sort by',
                                                       lambda e: self.OnSetVariableAsAxis(e, item, ID_SORT))

                    if chart.IncludesX():
                        context_menu.AppendGenericItem('Set x-axis',
                                                       lambda e: self.OnSetVariableAsAxis(e, item, ID_X_AXIS),
                                                       bitmap=ico.x_16x16.GetBitmap())

                    if chart.IncludesY():
                        context_menu.AppendGenericItem('Set y-axis',
                                                       lambda e: self.OnSetVariableAsAxis(e, item, ID_Y_AXIS),
                                                       bitmap=ico.y_16x16.GetBitmap())

                    if chart.IncludesZ():
                        context_menu.AppendGenericItem('Set z-axis',
                                                       lambda e: self.OnSetVariableAsAxis(e, item, ID_Z_AXIS),
                                                       bitmap=ico.z_16x16.GetBitmap())

        else:

            # allow adding of a summary
            type_ = data.GetType()
            if type_ == 'summaries_':
                context_menu.AppendGenericItem('Add summary',
                                               lambda e: self.OnOpenVariableFrame(e, type_id=ID_SUMMARY),
                                               bitmap=ico.summary_16x16.GetBitmap())

        context_menu.AppendSeparator()
        context_menu.AppendCollapseItem(page.OnCollapseAll)
        context_menu.AppendExpandItem(page.OnExpandAll)

        context_menu.CustomPopup()

    def VariableRightClickMultiple(self, page, items):
        can_delete = True  # all items have to be summaries

        # conduct various checks
        for i, item in enumerate(items):

            if item.IsSeparator():
                return

            data = item.GetData()

            if not data.GetTypeId() == ID_SUMMARY:
                can_delete = False

        context_menu = CustomMenu(self)

        context_menu.AppendCollapseItem(page.OnCollapseAll)
        context_menu.AppendExpandItem(page.OnExpandAll)

        if can_delete:
            context_menu.AppendSeparator()
            context_menu.AppendDeleteItem(lambda e: self.OnDeleteSummaries(e, items))

        context_menu.CustomPopup()

    def OnDeleteSummary(self, event, item):
        DeleteSingleTreeItem(self, item, self.DeleteSummary)

    def OnDeleteSummaries(self, event, items):
        DeleteMultipleTreeItems(self, items, self.DeleteSummary)

    def DeleteSummary(self, event, item):
        data = item.GetData()
        id_ = data.GetId()
        self._entity_mgr.DeleteSummary(id_)
        self._settings.DeleteSummary(id_)
        self._variable_mgr.DeleteSummary(id_)

        checked = item.IsChecked()
        self.object_menu.variables.tree.Delete(item)

        if checked:
            self.SaveChartState()
            self.RedisplayChart()

    def OnImportProfile(self, event, entity):
        ProfileImportFrame(self, entity.GetProfile()).ShowModal()

    def OnWindowRightClick(self, event):
        if not self._enabled:
            return

        tree = event.GetEventObject()
        page = tree.GetParent()
        items = tree.GetSelections()

        if len(items) > 1:

            self.WindowRightClickMultiple(page, items)

        elif len(items):

            self.WindowRightClickSingle(page, items[0])

        else:
            return

    def WindowRightClickSingle(self, page, item):

        data = item.GetData()

        if data is None:
            return

        context_menu = CustomMenu(self)

        if data.IsPointer():
            if data.IsWindow():
                context_menu.AppendDeleteItem(lambda e: self.OnDeleteWindow(e, item))
            else:  # chart
                context_menu.AppendDeleteItem(lambda e: self.OnDeleteChart(e, item))

            context_menu.AppendSeparator()

        context_menu.AppendCollapseItem(page.OnCollapseAll)
        context_menu.AppendExpandItem(page.OnExpandAll)

        context_menu.CustomPopup()

    def WindowRightClickMultiple(self, page, items):
        can_delete = True  # either all windows or all charts

        is_window = None

        # conduct various checks
        for i, item in enumerate(items):

            if item.IsSeparator():
                return

            data = item.GetData()
            if not data.IsPointer():
                return

            if i == 0:
                is_window = data.IsWindow()

            if is_window != data.IsWindow():
                can_delete = False

        context_menu = CustomMenu(self)

        context_menu.AppendCollapseItem(page.OnCollapseAll)
        context_menu.AppendExpandItem(page.OnExpandAll)

        if can_delete:
            context_menu.AppendSeparator()

            if is_window:
                context_menu.AppendDeleteItem(lambda e: self.OnDeleteWindows(e, items))
            else:  # chart
                context_menu.AppendDeleteItem(lambda e: self.OnDeleteCharts(e, items))

        context_menu.CustomPopup()

    def OnDeleteWindow(self, event, item):
        DeleteSingleTreeItem(self, item, self.DeleteWindow)

    def OnDeleteWindows(self, event, items):
        DeleteMultipleTreeItems(self, items, self.DeleteWindow)

    def DeleteWindow(self, event, item):
        id_ = item.GetData().GetId()

        # close page in display
        index = self.display.GetWindowIndex(id_)

        if index is not None:
            self.PageClosing(index)
            self.PageClosed()
            self.display.ClosePage(index)

        # delete in chart manager
        window = self._chart_mgr.GetWindow(id_)
        self._chart_mgr.DeleteWindow(window)

        # delete in object_menu
        self.object_menu.DeleteWindow(item, id_)

    def OnDeleteChart(self, event, item):
        DeleteSingleTreeItem(self, item, self.DeleteChart)

    def OnDeleteCharts(self, event, items):
        DeleteMultipleTreeItems(self, items, self.DeleteChart)

    def DeleteChart(self, event, item):
        parent = item.GetParent()
        window_id = parent.GetData().GetId()
        chart_id = item.GetData().GetId()

        checked = item.IsChecked()

        # delete item in display (if not checked it has already been removed from the window)
        if checked:
            self.display.DeleteChart(window_id, chart_id)

        # delete item in chart_manager
        self._chart_mgr.DeleteChart(window_id, chart_id)

        # delete window in object_menu
        self.object_menu.DeleteChart(item, window_id, chart_id)

        # if the window is checked and the deleted item was checked, the charts have to be re-drawn on the window
        # change
        if parent.IsChecked() and checked:
            index = self.display.GetWindowIndex(window_id)
            self.display.SetSelection(index)

            self.OnRefreshWindow(None, True)

    def OnEntityDoubleClick(self, event):
        item = event.GetItem()
        data = item.GetData()

        if data is None or not data.IsPointer():
            return

        type_ = data.GetType()
        self.OnOpenEntityFrame(None, type_=type_, item=item)

    def OnVariableDoubleClick(self, event):
        # Do not allow multiple frames of the same entity
        item = event.GetItem()
        data = item.GetData()

        if data is None:
            return

        type_id = data.GetTypeId()

        self.OnOpenVariableFrame(None, type_id=type_id, item=item)

    def UpdateDependencies(self):
        self.ribbon.EnableButtons(True, self._entity_mgr)

    def RedisplayChart(self):
        ids = self.display.GetActiveIds()
        if ids is not None:
            chart = self._chart_mgr.GetChart(*ids)

            # ChangeState to get correct checkbox state of added item for shown chart
            self.object_menu.LoadState(*ids, chart)

            # re-draw chart with updated data
            self.DisplayChart(chart)

    # drag & drop events -----------------------------------------------------------------------------------------------
    def OnBeginDrag(self, event):
        tree = event.GetEventObject()
        selections = tree.GetSelections()

        if not self.BeginDragAndCopy(tree, selections):
            event.Veto()
            return

        self._drag_items = selections

        event.Allow()

    def BeginDragAndCopy(self, tree, selections):
        # check if any of the selections is a first child of the root or a separator
        root = tree.GetRootItem()
        for item in selections:
            if item.GetParent() == root or item.IsSeparator():
                return False

        return True

    def EndDragAndCopy(self, items, target):
        if items is None or not len(items):
            return None, None

        if target is None:
            return None, None

        target_data = target.GetData()
        if target_data is None:
            return None, None

        # loop to check all items are same entity family type and has the same parent, else return
        drag_type = items[0].GetData().GetFamilyType()
        drag_parent = items[0].GetParent()

        for item in items:
            if not item.GetData().IsFamilyType(drag_type) or not item.GetParent() == drag_parent:
                return None, None

        return self.GetDragTarget(target, items[0])

    def GetDragTarget(self, target, item):
        data_t = target.GetData()
        data_i = item.GetData()

        index = None
        drop_target = None

        # handle dragging to folders and entities separately
        if data_t.IsFolder():  # folder

            if target is item:
                # TODO: Should potentially be allowed for copying folders, just not dragging
                pass

            elif data_i.IsFolder() and (target is item.GetParent()):
                # moving a folder to a folder it is already inside
                index, drop_target = MoveFolderOntoFolder(self, target, item)

            elif data_i.IsFolder() and (target.GetParent() is item.GetParent()):
                # move a folder into a folder which has the same parent
                index, drop_target = MoveFolderOntoFolder(self, target, item)

            elif data_i.IsFolder() and data_i.IsFamilyType(data_t.GetFamilyType()):
                # moving a folder into/onto a folder which is of similar type
                index, drop_target = MoveFolderOntoFolder(self, target, item)

            elif target is item.GetParent():
                # moving an item to a folder it is already inside
                index = target.GetChildrenCount() - 1
                drop_target = target

            elif data_t.IsFamilyType(data_i.GetFamilyType()):
                # moving an item into a folder
                index = target.GetChildrenCount() - 1
                drop_target = target

        else:  # entity or window

            if data_i.IsFolder() and data_i.ParentIsType(data_t.GetType()):
                # moving a folder to a hierarchical parent
                index = target.GetChildrenCount() - 1
                drop_target = target

            if data_i.IsFolder() and data_t.IsFamilyType(data_i.GetFamilyType()):
                # moving a folder to an entity of similar type
                index = RelativeDragIndex(target, item)
                drop_target = target.GetParent()

            elif target is item.GetParent():
                # same parent
                index = target.GetChildrenCount() - 1
                drop_target = target

            elif data_i.ParentIsType(data_t.GetType()) and data_i.AllowParentTransfer():
                # different parent of similar type
                index = target.GetChildrenCount() - 1
                drop_target = target

            elif data_i.IsFamilyType(data_t.GetFamilyType()):
                # Same item type
                index = RelativeDragIndex(target, item)
                drop_target = target.GetParent()

        return index, drop_target

    def OnEndDrag(self, event):
        target = event.GetItem()
        index, drop_target = self.EndDragAndCopy(self._drag_items, target)

        if index is None or drop_target is None:
            return

        # get tree and object_menu page
        tree = event.GetEventObject()
        page = tree.GetParent()

        # move nodes and update managers and charts
        represent = self._drag_items[0].GetData()
        non_folder_parent = page.GetNonFolderParent(self._drag_items[0])
        data = non_folder_parent.GetData()

        if represent.IsEntity() or represent.IsFolder():
            self.MoveEntityNodes(drop_target, self._drag_items, index, tree)

            # update derived properties of the drag_parent (now that it has lost child entities)
            if data.IsPointer():
                entity = self._entity_mgr.GetEntity(*data.GetPointer())
                self._entity_mgr.UpdateDerivedProperties(entity)

        elif represent.IsWindow():

            self.MoveNodes(drop_target, self._drag_items, index, tree)

            # change window and refresh
            index = self.display.GetWindowIndex(data.GetId())
            self.display.SetSelection(index)
            self.OnRefreshWindow(None, replace_charts=True)

        target.Expand()

    def MoveNodes(self, target, sources, index, tree):
        tree.Freeze()

        counter = 0
        for idx in range(index + 1, index + 1 + len(sources)):
            source = sources[counter]

            item = tree.InsertItem(target, idx, source.GetText(), ct_type=1, image=source.GetImage(), data=source.GetData())
            item.SetType(source.GetType())
            tree.CheckItem2(item, source.IsChecked(), torefresh=False)

            self.AppendChildren(item, source, tree)
            counter += 1

        for source in sources:
            tree.Delete(source)

        tree.Thaw()

    def MoveEntityNodes(self, target, sources, index, tree, copy=False):
        tree.Freeze()

        page = tree.GetParent()

        # preparing entity for replacing parent entities in entity_mgr
        target_data = target.GetData()

        # if target is a folder, replace entity with the first entity parent
        if target_data.IsFolder():
            target_data = page.GetNonFolderParent(target).GetData()

        # get new entity parent if the target is an entity (alternative are top level items)
        new_parent = None
        if target_data.IsPointer():
            new_parent = self._entity_mgr.GetEntity(*target_data.GetPointer())

        counter = 0
        for idx in range(index + 1, index + 1 + len(sources)):
            source = sources[counter]
            data = source.GetData()

            if data.IsPointer():  # entity
                entity = self._entity_mgr.GetEntity(*data.GetPointer())
                if copy:
                    entity = self._entity_mgr.CreateDuplicate(entity, control=False)
                    entity.SetName('Copy of {}'.format(entity.GetName()))

                item = page.CopyEntity(target, entity, data, idx=idx)
                item.SetType(source.GetType())
                tree.CheckItem2(item, source.IsChecked(), torefresh=False)

            else:  # folder
                text = source.GetText()
                if copy:
                    text = 'Copy of {}'.format(text)

                item = tree.InsertItem(target, idx, text, ct_type=0, image=source.GetImage(), data=source.GetData())

            self.AppendEntityChildren(item, source, tree, copy=copy)
            counter += 1

            # updating the entity_mgr by replacing the old parent entity for the new parent entity
            if new_parent is not None:
                if data.IsFolder():
                    items = page.GetNonFolderChildren(item)
                else:
                    items = [item]

                for it in items:
                    self.UpdateEntityProperties(it, new_parent)

        # updating entity_mgr with derived changes (because movement can only happen from the same parent, only need
        # to call derived once)
        if new_parent is not None:
            self._entity_mgr.UpdateDerivedProperties(new_parent)

        if not copy:
            for source in sources:
                tree.Delete(source)

        tree.Thaw()

    def UpdateEntityProperties(self, item, new_parent_entity):
        data = item.GetData()
        entity = self._entity_mgr.GetEntity(*data.GetPointer())
        self._entity_mgr.ReplacePrimaryParent(entity, new_parent_entity)

        # updating entity_mgr with hierarchical changes
        self._entity_mgr.UpdateHierarchicalProperties(entity)

    def AppendChildren(self, item, source, tree):
        child, cookie = tree.GetFirstChild(source)

        while child:
            alias = tree.AppendItem(item, child.GetText(), ct_type=1, image=child.GetImage(), data=child.GetData())
            alias.SetType(child.GetType())
            tree.CheckItem2(alias, child.IsChecked(), torefresh=False)

            self.AppendChildren(alias, child, tree)
            child, cookie = tree.GetNextChild(source, cookie)

        tree.Expand(item)

    def AppendEntityChildren(self, item, source, tree, copy=False):
        page = tree.GetParent()
        child, cookie = tree.GetFirstChild(source)

        while child:

            data = child.GetData()

            if data.IsPointer():  # entity

                entity = self._entity_mgr.GetEntity(*data.GetPointer())
                if copy:
                    entity = self._entity_mgr.CreateDuplicate(entity, control=False)
                    entity.SetName('Copy of {}'.format(entity.GetName()))

                alias = page.CopyEntity(item, entity, data)

            else:  # folder
                text = child.GetText()
                if copy:
                    text = 'Copy of {}'.format(text)

                alias = tree.AppendItem(item, text, ct_type=0, image=child.GetImage(), data=child.GetData())

            #alias = tree.AppendItem(item, child.GetText(), ct_type=1, image=child.GetImage(), data=child.GetData())
            #alias.SetType(child.GetType())
            #tree.CheckItem2(alias, child.IsChecked(), torefresh=False)

            self.AppendEntityChildren(alias, child, tree, copy=copy)
            child, cookie = tree.GetNextChild(source, cookie)

        tree.Expand(item)

    # edit label events ------------------------------------------------------------------------------------------------
    def OnBeginEditLabel(self, event):

        textctrl = event.GetEventObject().GetEditControl()
        textctrl.SelectAll()

        event.Allow()

    def OnEndEditLabel(self, event):
        if not event.GetLabel():
            event.Veto()
            return

        item = event.GetItem()
        data = item.GetData()

        if data.IsEntity():
            entity = self._entity_mgr.GetEntity(*data.GetPointer())
            entity.SetName(event.GetLabel())

            if item.IsChecked():
                self.OnRefreshWindow(None)

        elif data.IsWindow():
            window = self._chart_mgr.GetWindow(data.GetPointer())
            window.SetLabel(event.GetLabel())
            self.display.SetPageText(window)

        elif data.IsChart():
            parent_data = item.GetParent().GetData()
            window = self._chart_mgr.GetChart(parent_data.GetPointer(), data.GetPointer())
            window.SetLabel(event.GetLabel())

    # ==================================================================================================================
    # Options Bar Functions
    # ==================================================================================================================
    def OnOptionsBarChanged(self, event):
        # draw chart
        ids = self.display.GetActiveIds()
        chart = self._chart_mgr.GetChart(*ids)
        self.DisplayChart(chart)

    # ==================================================================================================================
    # Ribbon Functions
    # ==================================================================================================================
    def OnAddFolder(self, event, item=None, page=None):
        # if added from ribbon the correct page and selected item has to be found
        if page is None:
            page = self.object_menu.GetActiveTab()

            if page is None:  # no active tab
                return

            item = page.tree.GetSelection()

        # primary_parent = data.GetParentType()
        # parents = page.GetItemsByType(primary_parent)
        #
        # print(primary_parent, parents)
        #
        # if parents:
        #     item_parent = parents[0]
        # else:
        #     return

        page.AddFolder(item)

    # Window functions -------------------------------------------------------------------------------------------------
    def OnWindowDropdown(self, event):
        menu = CustomMenu(self)
        window = CustomMenuItem(menu, wx.ID_ANY, 'Window', '')
        window.SetBitmap(ico.window_16x16.GetBitmap())
        menu.AppendItem(window)

        split = CustomMenuItem(menu, wx.ID_ANY, 'Split window', '')
        split.SetBitmap(ico.window_split_16x16.GetBitmap())
        menu.AppendItem(split)

        # events
        self.Bind(wx.EVT_MENU, self.OnAddWindow, window)
        self.Bind(wx.EVT_MENU, lambda e: self.OnAddWindow(e, True), split)

        menu.CustomPopup()

    def OnAddWindow(self, event, allow_split=False):
        window = self._chart_mgr.AddWindow(allow_split=allow_split)
        window.Init()
        self.AddWindow(window)

    def AddWindow(self, window):
        self.object_menu.AddWindow(window)
        self.display.AddWindow(window)

    def OnRefreshWindow(self, event, replace_charts=False):
        id_ = self.display.GetActiveWindowId()
        if id_ is None:
            return

        self.SaveChartState()

        window = self._chart_mgr.GetWindow(id_)
        charts = self.GetDrawableCharts(window)

        # used for OnWindowItemCheck and OnDeleteChart
        if replace_charts:
            window_panel = self.display.GetActiveWindow()
            window_panel.ReplaceCharts(charts)

        self.DrawCharts(window.GetId(), charts)

    def OnPresentMode(self, event):
        self._present = not self._present

        self.OnRefreshWindow(None)

    # Add chart functions  ---------------------------------------------------------------------------------------------
    def OnAddChart(self, event, chart):
        if not self.display.GetPageCount():
            self.OnAddWindow(None)

        else:
            if not self.display.GetActiveWindow().AllowSplit():
                self.OnAddWindow(None)

            else:
                # if window allows split, no change event will fire, so the current state is saved here
                self.SaveChartState()

        # adding chart to chart_manager
        id_ = self.display.GetActiveWindowId()
        self._chart_mgr.AddChart(id_, chart)
        window = self._chart_mgr.GetWindow(id_)

        # adding chart to display
        self.display.AddChart(window, chart)
        self.display.EnableOptionsBar(True, chart)

        # updating window item in object_menu
        self.object_menu.AddChart(window, chart)

        # draw newly added chart
        self.DisplayChart(chart)

    # Export functions -------------------------------------------------------------------------------------------------
    def OnExportMultiple(self, event, entities=()):
        ExportFrame(self, self._entity_mgr, self._variable_mgr, self.object_menu, entities=entities).Show()

    # open entity frame functions --------------------------------------------------------------------------------------
    def OnOpenEntityFrame(self, event, type_=None, item=None, item_parent=None):

        # Do not allow multiple frames of the same entity
        if item is not None:

            data = item.GetData()

            if data.IsLocked():
                return

            else:
                data.Lock()

        e_mgr = self._entity_mgr
        v_mgr = self._variable_mgr

        e_page = self.object_menu.entities
        p_page = self.object_menu.projects

        us = self._settings.GetUnitSystem()

        if type_ is None:
            type_ = event.GetId()

        if type_ == ID_FIELD:
            FieldFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_BLOCK:
            BlockFrame(self, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_PLATFORM:
            PlatformFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_PROCESSOR:
            ProcessorFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_PIPELINE:
            PipelineFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_PRODUCER:
            ProducerFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_INJECTOR:
            InjectorFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_RESERVOIR:
            ReservoirFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_THEME:
            ThemeFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_POLYGON:
            PolygonFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_ANALOGUE:
            AnalogueFrame(self, us, e_mgr, e_page, item=item).Show()

        elif type_ == ID_TYPECURVE:
            TypecurveFrame(self, us, e_mgr, e_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_SCALING:
            ScalingFrame(self, us, e_mgr, self.object_menu, item=item, item_parent=item_parent).Show()

        elif type_ == ID_PROJECT:
            ProjectFrame(self, e_mgr, p_page, item=item, item_parent=item_parent).Show()

        elif type_ == ID_HISTORY:
            HistoryFrame(self, self._settings, v_mgr, e_mgr, self.object_menu, item=item, item_parent=item_parent).Show()

        elif type_ == ID_SCENARIO:
            ScenarioFrame(self, e_mgr, self.object_menu, item=item, item_parent=item_parent).Show()

        elif type_ == ID_PREDICTION:
            PredictionFrame(self, self._settings, v_mgr, e_mgr, p_page, item=item, item_parent=item_parent).Show()

    # variables frames -------------------------------------------------------------------------------------------------
    def OnOpenVariableFrame(self, event, type_id=None, item=None):
        # Do not allow multiple frames of the same variable
        if item is not None:
            data = item.GetData()
            if data.IsLocked():
                return
            else:
                data.Lock()

        if type_id is None:
            type_id = event.GetId()

        if type_id in (ID_POTENTIAL, ID_RATE, ID_CUMULATIVE, ID_RATIO):
            ProductionVariableFrame(self, self._variable_mgr, item=item).Show()

        elif type_id == ID_SUMMARY:
            SummaryVariableFrame(self, self._variable_mgr, self.object_menu, item=item).Show()

    # open correlation frames ------------------------------------------------------------------------------------------
    def OnOpenEntityCorrelationFrame(self, event):
        if self._corr_ent_locked:
            return

        self._corr_ent_locked = True
        EntityCorrelationFrame(self, self._entity_mgr, self.object_menu.entities).Show()

    def OnOpenVariableCorrelationFrame(self, event):
        if self._corr_var_locked:
            return

        self._corr_var_locked = True
        VariableCorrelationFrame(self, self._variable_mgr, self.object_menu.variables).Show()

    # File functions ---------------------------------------------------------------------------------------------------
    def SetPersistenceFile(self):
        persistence_file = os.path.join(os.path.dirname(self._project_path), 'persist')
        self._persist_mgr.SetPersistenceFile(persistence_file)

    def OnSave(self, event):
        if self._project_path is None:
            self.OnSaveAs(None)
            return

        # save chart state prior to saving
        self.SaveChartState()

        # pickling
        fid2 = open(self._project_path, 'wb')
        gc.disable()

        pickler = pickle.Pickler(fid2, pickle.HIGHEST_PROTOCOL)
        pickler.fast = 1

        object_ = SaveObject()
        object_.Set(self._settings, self._variable_mgr, self._entity_mgr, self._chart_mgr, self.object_menu.Save(), None)
        pickler.dump(object_)

        fid2.close()
        gc.enable()

        # persisting
        self.SetPersistenceFile()  # TODO: should probably be done in SaveAs and Open only
        self._persist_mgr.Register(self.object_menu.notebook)
        self._persist_mgr.Register(self.display.notebook)
        self._persist_mgr.SaveAndUnregister(self.object_menu.notebook)
        self._persist_mgr.SaveAndUnregister(self.display.notebook)

    def OnSaveAs(self, event):
        # get file path
        path = GetFilePath(self)
        if path is None:
            return

        # ensure file has .alv extension
        path = os.path.splitext(path)[0] + '.alv'

        self._project_path = path
        self.OnSave(None)

    def OnOpenProject(self, event):
        # test for already open project
        if self.OnCloseProject(None):
            return

        filename = GetFilePath(self, wildcard='Alveus files (*.alv)|*.alv')
        if filename is None:
            return

        #filename = r'C:\Users\Frederik\Desktop\alveus_save\test.alv'
        #filename = r'\\main.glb.corp.local\EP-DK$\Home\COP\3\J0514243\Desktop\Alveus data\test.alv'

        # pickling
        fid2 = open(filename, 'rb')
        object_ = pickle.load(fid2)
        fid2.close()

        # load managers and gui
        self._project_path = filename
        settings, variable_mgr, entity_mgr, chart_mgr, object_menu, display = object_.Get()
        self._settings = settings
        self._variable_mgr = variable_mgr
        self._entity_mgr = entity_mgr
        self._chart_mgr = chart_mgr

        self.object_menu.Initialize()
        self.object_menu.Load(object_menu)
        self.ribbon.EnableButtons(True, self._entity_mgr)
        self.RestoreDisplay()
        self._enabled = True

        # persist
        self.SetPersistenceFile()
        self._persist_mgr.RegisterAndRestore(self.object_menu.notebook)
        self._persist_mgr.RegisterAndRestore(self.display.notebook)

    def OnCloseProject(self, event):

        # test whether or not user wants to save prior to closing
        if self._project_path is not None:
            warning = wx.MessageDialog(self, 'Would you like to save the current project prior to starting a new one?',
                                       caption='Save', style=wx.YES_NO | wx.CANCEL | wx.CENTER)

            answer = warning.ShowModal()

            if answer == wx.ID_YES:

                self.OnSave(None)

            elif answer == wx.ID_NO:

                pass

            elif answer == wx.ID_CANCEL:

                return True

        self.display.Clear()
        self.object_menu.Clear()
        self.ribbon.EnableButtons(False)

        self._enabled = False
        self._project_path = None
        self._settings = None
        self._variable_mgr = None
        self._entity_mgr = None
        self._chart_mgr = None

        return False

    def OnNewProject(self, event):
        # test for already open project
        if self.OnCloseProject(None):
            return

        filename = GetFilePath(self)
        if filename is None:
            return

        #filename = r'C:\Users\Frederik\Desktop\alveus_save\test.alv'
        #filename = r'\\main.glb.corp.local\EP-DK$\Home\COP\3\J0514243\Desktop\Alveus data\test.alv'
        self._project_path = filename
        self._enabled = True

        # initialise managers
        self._settings = Settings()
        self._variable_mgr = VariableManager(self._settings.GetUnitSystem())
        self._entity_mgr = EntityManager()
        self._chart_mgr = ChartManager()

        # initialise gui objects
        self.object_menu.Initialize()
        self.object_menu.Populate(self._variable_mgr)
        self.ribbon.EnableButtons(True, self._entity_mgr)

    def OnProjectSettings(self, event):
        SettingsFrame(self, self._settings, self.object_menu.variables).Show()

    # ==================================================================================================================
    # Display Functions
    # ==================================================================================================================
    # Change display page functions ------------------------------------------------------------------------------------
    def OnPageChanging(self, event):
        self.PageChanging(event.GetSelection())

    def PageChanging(self, idx):
        self.SaveChartState()
        self.display.SetActiveWindow(idx)

    def OnPageChanged(self, event):
        ids = self.display.GetActiveIds()
        if ids is not None:
            self.LoadChartState(*ids)

            # loop over all charts on window and refresh if required
            window = self._chart_mgr.GetWindow(ids[0])
            window_panel = self.display.GetActiveWindow()

            for chart, chart_panel in zip(window.GetCharts(), window_panel.GetCharts()):
                if chart.DoRefresh():
                    self.DisplayChart(chart, chart_panel)
                    chart.SetRefresh(False)

        else:  # window without chart
            self.object_menu.DefaultItemTypes()
            self.display.EnableOptionsBar(False)

    def OnPageClosing(self, event):
        self.PageClosing(event.GetSelection())

    def PageClosing(self, index):
        if index is not None:
            self.object_menu.windows.WindowClosed(self.display.GetWindowId(index))

        self.SaveChartState()

    def OnPageClosed(self, event):
        self.PageClosed()

    def PageClosed(self):
        count = self.display.notebook.GetPageCount() - 1

        if not count:
            self.object_menu.DefaultItemTypes()
            self.display.SetActiveWindow(None)
            self.display.EnableOptionsBar(False)

    def PageOpening(self, window):
        self.display.AddWindow(window)
        self.display.EnableOptionsBar(True)

        charts = self.GetDrawableCharts(window)

        # add charts to window
        for chart in charts:
            self.display.AddChart(window, chart)

        self.DrawCharts(window.GetId(), charts)

    def RestoreDisplay(self):
        items = self.object_menu.windows.GetCheckedItems()

        for item in items:
            data = item.GetData()
            if data.IsWindow():
                window = self._chart_mgr.GetWindow(data.GetId())
                self.PageOpening(window)

    def GetDrawableCharts(self, window):
        if window.AllowSplit():
            # get charts from object_menu to ensure correct ordering of charts and to only use enabled charts
            id_ = window.GetId()
            items = self.object_menu.windows.GetCheckedChartItems(id_)
            charts = [self._chart_mgr.GetChart(id_, i.GetData().GetId()) for i in items]
        else:
            # only contains one chart
            charts = window.GetCharts()

        return charts

    def DrawCharts(self, window_id, charts):
        for chart in charts:
            self.ActivateChart(window_id, chart.GetId(), save_state=False)

            # pre-drawing chart to ensure correct sizing
            self.DisplayChart()

            self.DisplayChart(chart)

    def SaveChartState(self):
        # save existing chart state
        ids = self.display.GetActiveIds()
        if ids is not None:
            self.object_menu.SaveState(*ids)

            chart = self._chart_mgr.GetChart(*ids)
            chart.SetState(*self.display.GetState())

    def LoadChartState(self, window_id, chart_id):
        # load new chart state
        chart = self._chart_mgr.GetChart(window_id, chart_id)

        self.object_menu.LoadState(window_id, chart_id, chart)
        self.display.SetState(chart)

        self.display.SetActiveChart(window_id, chart_id)

    def DisplayChart(self, chart=None, chart_panel=None):

        if chart_panel is None:
            chart_panel = self.display.GetActiveChart()

            if chart_panel is None:
                return

        if chart is not None:
            chart_type = chart.GetType()
        else:
            chart_type = None

        if self._present:
            size_options = self._settings.GetPresentSizeOptions()
        else:
            size_options = self._settings.GetNormalSizeOptions()

        settings = self._settings

        # 2D line charts
        if chart_type == ID_CHART_CARTESIAN:

            # gather input
            _, x, _, _ = self.object_menu.variables.GetAxis(*chart_panel.GetIds())
            if x is not None:
                x = self._variable_mgr.GetVariable(x.GetId())

            variables = self._variable_mgr.GetVariables(self.object_menu.variables.GetPointers())
            entities = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())
            simulations = self._entity_mgr.GetEntities(self.object_menu.projects.GetPointers())

            # gather options
            show_data = self.display.options_bar.GetShowData()
            show_uncertainty = self.display.options_bar.GetShowUncertainty()
            split_by = self.display.options_bar.GetSplitBy()
            group_by = self.display.options_bar.GetGroupBy()

            # generate axes item
            axes_item = AxesItem()
            axes_item.MergeLines(x, variables, entities, simulations, size_options, settings, show_data=show_data,
                                 show_uncertainty=show_uncertainty, split_by=split_by, group_by=group_by)

            chart_panel.Realize(axes_item, size_options)

        elif chart_type == ID_CHART_STACKED:

            # gather input
            _, x, _, _ = self.object_menu.variables.GetAxis(*chart_panel.GetIds())
            if x is not None:
                x = self._variable_mgr.GetVariable(x.GetId())

            variables = self._variable_mgr.GetVariables(self.object_menu.variables.GetPointers())
            entities = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())
            simulations = self._entity_mgr.GetEntities(self.object_menu.projects.GetPointers())

            # gather options
            split_by = self.display.options_bar.GetSplitBy()

            # generate axes item
            axes_item = AxesItem()
            axes_item.MergeStackedLines(x, variables, entities, simulations, size_options, split_by=split_by)

            chart_panel.Realize(axes_item, size_options)

        elif chart_type == ID_CHART_BAR:

            # gather input
            sort, _, _, _ = self.object_menu.variables.GetAxis(*chart_panel.GetIds())
            if sort is not None:
                sort = self._variable_mgr.GetVariable(sort.GetId())

            # gather input
            variables = self._variable_mgr.GetVariables(self.object_menu.variables.GetPointers())
            entities = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())
            simulations = self._entity_mgr.GetEntities(self.object_menu.projects.GetPointers())

            # gather options
            split_by = self.display.options_bar.GetSplitBy()
            group_by = self.display.options_bar.GetGroupBy()

            # generate axes item
            axes_item = AxesItem()
            axes_item.MergeBars(variables, entities, simulations, split_by=split_by, group_by=group_by, sort_by=sort)

            chart_panel.Realize(axes_item, size_options)

        elif chart_type == ID_CHART_BUBBLE:

            # gather input
            _, x, y, z = self.object_menu.variables.GetAxis(*chart_panel.GetIds())

            if x is not None:
                x = self._variable_mgr.GetVariable(x.GetId())

            if y is not None:
                y = self._variable_mgr.GetVariable(y.GetId())

            if z is not None:
                z = self._variable_mgr.GetVariable(z.GetId())

            entities = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())
            simulations = self._entity_mgr.GetEntities(self.object_menu.projects.GetPointers())

            # generate axes item
            axes_item = AxesItem()
            axes_item.MergeBubbles(x, y, z, entities, simulations)

            chart_panel.Realize(axes_item, size_options)

        elif chart_type == ID_CHART_HISTOGRAM:

            # gather input
            variables = self._variable_mgr.GetVariables(self.object_menu.variables.GetPointers())
            entities = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())
            simulations = self._entity_mgr.GetEntities(self.object_menu.projects.GetPointers())

            # generate axes item
            axes_item = AxesItem()
            axes_item.MergeHistograms(variables, entities, simulations, size_options)

            chart_panel.Realize(axes_item, size_options)

        elif chart_type == ID_CHART_MAP:

            # gather input
            variables = self._variable_mgr.GetVariables(self.object_menu.variables.GetPointers())
            entities = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())
            simulations = self._entity_mgr.GetEntities(self.object_menu.projects.GetPointers())

            # generate axes item
            axes_item = AxesItem()
            axes_item.MergeMaps(variables, entities)

            chart_panel.Realize(axes_item, size_options)

        elif chart_type == ID_CHART_3D:

            # gather input
            entities = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())

            # generate axes item
            axes_item = AxesItem()
            axes_item.Merge3D(entities)

            chart_panel.Realize(axes_item, size_options)

        elif chart_type == ID_CHART_FIT:

            entities = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())

            # get x and y variables from variable_mgr
            xs = self._variable_mgr.GetVariables(('date', 'oil_cumulative', 'date'))
            ys = self._variable_mgr.GetVariables(('liquid_potential', 'water_cut', 'gas_oil_ratio'))


            if entities:
                analogue = entities[0]
                profile = analogue.GetHistory()

                # get models from analogue Functions property
                functions = analogue.GetProperties().functions
                ms = [f.GetModels() if f is not None else () for f in functions.Get()]

            else:
                profile = None
                ms = ()

            # generate axes item
            axes_item = AxesItem()
            axes_item.MergeFits(profile, xs, ys, ms, size_options)

            chart_panel.Realize(axes_item, size_options)

        # elif chart_type == ID_CHART_PROFILES:
        #
        #     # gather input
        #     parent = self._entity_mgr.GetEntities(self.object_menu.entities.GetPointers())
        #
        #     if parent:
        #         entities = self._entity_mgr.GetChildren(parent[0])
        #     else:
        #         entities = []
        #
        #     # generate axes item
        #     axes_item = AxesItem()
        #     axes_item.MergeProfiles(entities)
        #
        #     chart_panel.Realize(axes_item)

        else:
            chart_panel.Realize(size_options=size_options)

    def OnCloseApplication(self, event):
        plt.close('all')  # due to import of mpl.use('WXAGG') in charts.py the MainLoop hangs without this code
        event.Skip()

    # ==================================================================================================================
    # PyPubSub receivers
    # ==================================================================================================================
    def ActivateChart(self, window_id, chart_id, save_state=True):
        if save_state:
            self.SaveChartState()

        self.LoadChartState(window_id, chart_id)

    def EntityAdded(self, id_, type_):
        # ensure added entity has ChangeState objects in object_menu pointer for each window and chart in chart_mgr
        item = self.ReverseEntityPointer(id_, type_)
        data = item.GetData()

        for window_id, chart_ids in self._chart_mgr.GetAllIds().items():
            data.AddWindowState(window_id)

            for chart_id in chart_ids:
                data.AddChartState(window_id, chart_id)

        # Activate chart to assign correct checkbox to item
        ids = self.display.GetActiveIds()
        if ids is not None:
            self.ActivateChart(*ids, save_state=True)

        self.UpdateDependencies()

    def SummaryAdded(self, id_):
        # ensure added summary has ChangeState objects in object_menu pointer for each window and chart in chart_mgr
        item = self.ReverseSummaryPointer(id_)
        data = item.GetData()

        for window_id, chart_ids in self._chart_mgr.GetAllIds().items():
            data.AddWindowState(window_id)

            for chart_id in chart_ids:
                data.AddChartState(window_id, chart_id)

        self._entity_mgr.AddSummary(id_)

    def PointerUpdated(self, checked, id_, type_=None):
        # refresh current window to display changes
        if checked:
            self.SaveChartState()
            self.RedisplayChart()

        # find item of updated entity/variable
        if type_ is not None:
            item = self.ReverseEntityPointer(id_, type_)
        else:
            item = self.ReverseVariablePointer(id_)

        # loop through all charts where the pointer is checked and set them to refresh next time their window is clicked
        ids = self.display.GetActiveIds()
        states = item.GetData().GetChartStates()
        for window_id in states:
            for chart_id in states[window_id]:
                state = states[window_id][chart_id]

                if state.IsChecked() and ((ids is None) or (window_id != ids[0])):
                    chart = self._chart_mgr.GetChart(window_id, chart_id)
                    chart.SetRefresh(True)

    def EntityCorrelationClosed(self):
        self._corr_ent_locked = False

    def VariableCorrelationClosed(self):
        self._corr_var_locked = False

    def SettingsUpdated(self):
        self.SaveChartState()
        self.RedisplayChart()

    # ==================================================================================================================
    # Auxiliary methods
    # ==================================================================================================================
    def ReverseEntityPointer(self, id_, type_):
        items = self.object_menu.entities.GetItemsByType(type_)
        items += self.object_menu.projects.GetItemsByType(type_)

        return {i.GetData().GetId(): i for i in items}[id_]

    def ReverseVariablePointer(self, id_):
        return self.object_menu.variables.GetItemsById(id_)[0]

    def ReverseSummaryPointer(self, id_):
        return self.object_menu.variables.GetItemsById(id_, parent=self.object_menu.variables.summaries)[0]

    # ==================================================================================================================
    # Copy, Cut and Paste methods
    # ==================================================================================================================
    def OnCopyEntities(self, event, tree, items, cut=False):
        self.CopyEntities(tree, items, cut=cut)

    def CopyEntities(self, tree, items, cut=False):

        if not self.BeginDragAndCopy(tree, items):
            return

        self._copy_tree = tree
        self._copy_items = items
        self._cut = cut

    def OnPasteEntities(self, event, tree, paste_target):
        self.PasteEntities(tree, paste_target)

    def PasteEntities(self, tree, paste_target):
        if self._copy_items is None:
            return

        # cut items have to have their image enabled even if cut event fails
        self._copy_tree.GetParent().EnableCutItems(self._copy_items)

        if tree is not self._copy_tree:
            return

        index, target = self.EndDragAndCopy(self._copy_items, paste_target)

        if (index is None) or (target is None):
            return

        self.MoveEntityNodes(target, self._copy_items, index, tree, copy=not self._cut)

        self._copy_tree = None
        self._copy_items = None
        self._cut = False


# ======================================================================================================================
# Save class
# ======================================================================================================================
class SaveObject:
    def __init__(self):
        self._settings = None
        self._variable_mgr = None
        self._entity_mgr = None
        self._chart_mgr = None
        self._object_menu = None    # not the actual object menu, but the state
        self._display = None        # not the actual display, but the state

    def Get(self):
        return self._settings, self._variable_mgr, self._entity_mgr, self._chart_mgr, self._object_menu, self._display

    def Set(self, settings, variable_mgr, entity_mgr, chart_mgr, object_menu, display):
        self._settings = settings
        self._variable_mgr = variable_mgr
        self._entity_mgr = entity_mgr
        self._chart_mgr = chart_mgr
        self._object_menu = object_menu
        self._display = display


# ======================================================================================================================
# Helper functions
# ======================================================================================================================
def GetPrimaryChildrenInput(type_):
    if type_ == ID_SIMULATIONS:
        child_types = (ID_PROJECT,)
        texts = ('project',)
        icons = (ico.project_16x16.GetBitmap(),)

    elif type_ == ID_PROJECT:
        child_types = (ID_HISTORY, ID_SCENARIO)
        texts = ('history', 'scenario')
        icons = (ico.history_match_16x16.GetBitmap(), ico.scenario_16x16.GetBitmap())

    elif type_ == ID_SCENARIO:
        child_types = (ID_PREDICTION,)
        texts = ('prediction',)
        icons = (ico.prediction_16x16.GetBitmap(),)

    elif type_ == ID_FIELDS:
        child_types = (ID_FIELD,)
        texts = ('field',)
        icons = (ico.field_16x16.GetBitmap(),)

    elif type_ == ID_BLOCKS:
        child_types = (ID_BLOCK,)
        texts = ('block',)
        icons = (ico.block_16x16.GetBitmap(),)

    elif type_ == ID_FACILITIES:
        child_types = (ID_PLATFORM, ID_PIPELINE)
        texts = ('platform', 'pipeline')
        icons = (ico.platforms_16x16.GetBitmap(), ico.pipeline_16x16.GetBitmap())

    elif type_ == ID_PLATFORM:
        child_types = (ID_PROCESSOR,)
        texts = ('processor',)
        icons = (ico.processor_16x16.GetBitmap(),)

    elif type_ == ID_SUBSURFACE:
        child_types = (ID_RESERVOIR,)
        texts = ('reservoir',)
        icons = (ico.reservoir_16x16.GetBitmap(),)

    elif type_ == ID_RESERVOIR:
        child_types = (ID_THEME,)
        texts = ('theme',)
        icons = (ico.theme_16x16.GetBitmap(),)

    elif type_ == ID_THEME:
        child_types = (ID_POLYGON,)
        texts = ('polygon',)
        icons = (ico.polygon_16x16.GetBitmap(),)

    elif type_ == ID_POLYGON:
        child_types = (ID_PRODUCER, ID_INJECTOR)
        texts = ('producer', 'injector')
        icons = (ico.producer_oil_gas_16x16.GetBitmap(), ico.injector_wag_16x16.GetBitmap())

    elif type_ == ID_PORTFOLIO:
        child_types = (ID_ANALOGUE, ID_SCALING)
        texts = ('analogue', 'scaling')
        icons = (ico.analogue_16x16.GetBitmap(), ico.scaling_chart_16x16.GetBitmap())

    elif type_ == ID_ANALOGUE:
        child_types = (ID_TYPECURVE,)
        texts = ('typecurve',)
        icons = (ico.trend_chart_16x16.GetBitmap(),)

    else:
        child_types = ()
        texts = ()
        icons = ()

    return child_types, texts, icons
