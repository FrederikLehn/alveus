# generic imports ------------------------------------------------------------------------------------------------------
import numpy as np
from pubsub import pub

# wxPython imports -----------------------------------------------------------------------------------------------------
import wx.adv
import wx.grid
from wx.grid import EVT_GRID_CELL_CHANGED
from wx.lib.agw.customtreectrl import EVT_TREE_ITEM_CHECKED

# Alveus imports -------------------------------------------------------------------------------------------------------
from _ids import *
import _icons as ico
from _errors import *
from utilities import GetAttributes
from properties import EvaluationProperty
from frames.frame_design import ObjectFrame, SectionSeparator, GAP, SMALL_GAP, INTER_GAP
from frames.curve_fit_frame import CurveFitFrame
from frames.function_frame import FunctionFrame
from chart_mgr import AxesItem
from charts import CartesianChartPanel
import entity_mgr as em
import variable_mgr as vm
import frames.property_panels as pp

# ----------------------------------------------------------------------------------------------------------------------


class EntityFrame(ObjectFrame):
    def __init__(self, parent, entity, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, '')

        # used for access to object_menu tree, to add/modify entities
        self._entity_mgr = entity_mgr
        self._object_menu_page = object_menu_page
        self._item = item
        self._item_parent = item_parent

        # used for EntitySelectionFrames
        self._selection_items = ()  # items on the tree of the associated object_menu_page
        self._selection_types = ()  # Entity types which can be selected from selection
        self.selection = None

        # used for entities that require access to property FunctionsProperty
        self._functions = None

        # used for entities that require a parent to be locked on insert into ArrowInsertCtrl
        self.parent = None

        if item is not None:
            self._entity = entity_mgr.GetEntity(*item.GetData().GetPointer())
        else:
            self._entity = entity

        self.custom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_BUTTON, self.OnApplyButton, self.apply_button)
        self.Bind(wx.EVT_BUTTON, self.OnOKButton, self.ok_button)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # PyPubSub receivers -------------------------------------------------------------------------------------------
        pub.subscribe(self.EntityDeleted, 'entity_deleted')

    # events -----------------------------------------------------------------------------------------------------------
    def OnApplyButton(self, event):
        if self._item is not None:
            # entity is reloaded here in case hierarchical changes has been made to another entity since the frame
            # was opened. Using copy to ensure properties are not changed in case of Save error + Cancel
            entity = self._entity_mgr.GetEntity(*self._item.GetData().GetPointer()).Copy()

        else:
            # using initially allocated entity of relevant type
            entity = self._entity

        self.SaveName(entity)
        saved = self.Save(entity)

        if saved:
            added = False

            # producers & injectors have variable icons based on their fluid phase
            image_id = self.GetImageId()

            if self._item is None:  # new entity
                try:
                    self.DefineItemParent(entity)
                except IndexError:
                    return False

                # create entity and add as child to parent entity
                self._entity = self._entity_mgr.AddEntity(entity)
                data = self._item_parent.GetData()

                if data.IsPointer():
                    parent = self._entity_mgr.GetEntity(*data.GetPointer())
                    parent.AddChild(entity)

                self._item = self._object_menu_page.AddEntity(self._item_parent, entity, image_id=image_id)
                added = True

            else:  # existing entity

                self._entity.ReplaceInformation(entity)

                # if the entity is controlled, saving will have overwritten the controlling parameters, in case
                # the controlling entity has been updated since the frame was opened. Saving is required to
                # save the few parameters that can be changed on a controlled entity, but the remainder are
                # regathered from the the controlling entity here
                if self._entity.IsControlled():
                    self._entity_mgr.UpdateControlledProperties(self._entity)

                self._object_menu_page.UpdateEntity(self._item, self._entity, image_id=image_id)

            # if a selection frame, replace children to the selected ones
            self.SaveSelection(self._entity)

            # updating hierarchical properties
            self._entity_mgr.UpdateHierarchicalProperties(self._entity)

            # updating derived properties of parents
            self._entity_mgr.UpdateDerivedProperties(self._entity)

            # updating duplicated properties
            self._entity_mgr.UpdateDuplicatedProperties(self._entity)

            # loading to update derived, hierarchical and duplicated properties
            self.Load()

            # init title bar to update icons and names
            self.InitTitleBar()

            # send PyPubSub message to MainFrame, initiating various updates of other windows
            if added:
                pub.sendMessage('entity_added', id_=self._entity.GetId(), type_=self._entity.GetType())
            else:
                pub.sendMessage('pointer_updated', checked=self._item.IsChecked(),
                                id_=self._entity.GetId(), type_=self._entity.GetType())

        return saved

    def OnOKButton(self, event):
        saved = self.OnApplyButton(None)

        if saved:
            self.Close(True)

    def OnClose(self, event):
        if self._item is not None:
            # unlock entity pointer
            self._item.GetData().Lock(False)

        event.Skip()

    # PyPubSub receivers -----------------------------------------------------------------------------------------------
    def EntityDeleted(self, id_):
        if self._entity.GetId() == id_:
            self.OnCancelButton(None)

    # internal methods -------------------------------------------------------------------------------------------------
    def DefineItemParent(self, entity):
        # if item_parent is already defined, do nothing
        if self._item_parent is None:

            primary_parent = entity.GetPrimaryParent()

            # if a selection is made in the tree that has appropriate PrimaryParent, use that
            selection = self._object_menu_page.tree.GetSelection()

            if selection is not None:

                data = selection.GetData()

                if data is not None and data.IsPointer():

                    if data.IsType(primary_parent):

                        self._item_parent = selection
                        self.SaveAndLockParent()
                        return

            # otherwise choose the last item of primary parent type in the object_menu
            items = self._object_menu_page.GetItemsByType(primary_parent)
            if items:
                self._item_parent = items[-1]
                self.SaveAndLockParent()
                return

            # in case all primary parents are removed while the frame is open
            box = wx.MessageDialog(self, message='No available parent to attach to.', caption='Index Error')
            box.ShowModal()
            box.Destroy()

            raise IndexError()

    def DisableControlled(self):

        properties = self._entity.GetProperties()
        attributes = GetAttributes(properties, name_only=True)

        for attr in attributes:

            try:
                panel = getattr(self, attr)
                panel.EnableCtrls(False)

                # testing if the panel is hierarchical
                if hasattr(panel, 'use_self'):
                    panel.EnableCheckBox(False)

            except AttributeError:
                # errors related to hidden properties not shown on the frame.
                continue

    def GetImageId(self):
        return None

    def InitTitleBar(self):
        # sub-classed
        pass

    def Load(self):
        # locking parents for entities that require it
        if (self.parent is not None) and (self._item_parent is not None):
            self.LockParent()

        # loading selection tree if available
        if self.selection is not None:
            self.selection.Populate(self._selection_items, self._selection_types,
                                    entity=self._entity, entity_mgr=self._entity_mgr)

        self.LoadName()

        properties = self._entity.GetProperties()
        attributes = GetAttributes(properties, name_only=True)

        for attr in attributes:

            try:
                panel = getattr(self, attr)
                property_ = getattr(properties, attr)
                panel.Set(*property_.Get())

            except AttributeError:
                # errors related to hidden properties not shown on the frame.
                continue

        self.LoadCustom()

        if self._entity.IsControlled():
            self.DisableControlled()

    def LoadCustom(self):
        # sub-classed
        pass

    def LoadName(self):
        # sub-classed
        pass

    def LockParent(self):
        """
        Certain entities, such as Typecurve and Prediction require that parents are locked on insert. If such an entity
        is added by right-click the item is automatically locked.
        :return:
        """
        self.parent.Insert(self._item_parent.GetData().GetPointer())

    def Save(self, entity):
        properties = entity.GetProperties()
        attributes = GetAttributes(properties, name_only=True)

        for attr in attributes:
            try:
                panel = getattr(self, attr)

                property_ = getattr(properties, attr)
                property_.Set(*panel.Get())

            except AttributeError:
                # errors related to hidden properties not shown on the frame
                continue

            except ValueError:
                return False

        saved = self.SaveCustom(entity)

        return saved

    def SaveAndLockParent(self):
        """
        Certain entities, such as Typecurve and Prediction require that parents are locked on insert, as it uses
        some of their data. If such an entity is inserted via Ribbon, the parent is saved once the item_parent is found
        :return:
        """
        if self.parent is not None:
            properties = self._entity.GetProperties()
            properties.parent.Set(self._item_parent.GetData().GetPointer())

    def SaveCustom(self, entity):
        # sub-classed
        return True

    def SaveName(self, entity):
        # sub-classed
        pass

    def SaveSelection(self, entity):
        if self.selection is None:
            return

        items = self.selection.GetCheckedItems()
        children = [self._entity_mgr.GetEntity(*i.GetData().GetPointer()) for i in items]

        # retaining children of types that are not in selection types
        children += [e for e in self._entity_mgr.GetChildren(entity) if e.GetType() not in self._selection_types]

        self._entity_mgr.ReplaceChildren(entity, children)


class EntityPropertiesFrame(EntityFrame):
    def __init__(self, parent, entity, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, entity, entity_mgr, object_menu_page, item, item_parent)

        self.properties = pp.PropertiesPanel(self.custom)

        # sizing input -------------------------------------------------------------------------------------------------
        self.custom_sizer.Add(self.properties, 1, wx.EXPAND)
        self.custom.SetSizer(self.custom_sizer)

    def LoadName(self):
        self.properties.Load(self._entity.GetName())

    def SaveName(self, entity):
        self.properties.SaveName(entity)


class EntitySelectionFrame(EntityFrame):
    def __init__(self, parent, entity, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, entity, entity_mgr, object_menu_page, item, item_parent)

        self._selection_types = ()

        splitter = wx.SplitterWindow(self.custom, wx.ID_ANY, style=wx.SP_THIN_SASH | wx.SP_LIVE_UPDATE)
        self.selection = pp.SelectionTree(splitter, self._object_menu_page, expand_collapse=True)
        self.properties = pp.PropertiesPanel(splitter)
        splitter.SplitVertically(self.selection, self.properties, 200)

        # sizing custom ------------------------------------------------------------------------------------------------
        self.custom_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, GAP)
        self.custom.SetSizer(self.custom_sizer)

    def LoadName(self):
        self.properties.Load(self._entity.GetName())

    def SaveName(self, entity):
        self.properties.SaveName(entity)


# ======================================================================================================================
# Specific frames
# ======================================================================================================================
class AnalogueFrame(EntityPropertiesFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Analogue(), entity_mgr, object_menu_page, item, item_parent)

        self._unit_system = unit_system
        self._functions = None

        # preparing aui-manager ----------------------------------------------------------------------------------------
        self.aui_panel = pp.PropertiesAUIPanel(self.properties, min_size=(350, 380))

        # Profile ------------------------------------------------------------------------------------------------------
        general_panel = wx.Panel(self.properties)
        self.history = pp.HistoryFitPanel(general_panel)
        self.cultural = pp.CulturalTrajectoryPanel(general_panel)
        self.well_spacing = pp.WellSpacingPanel(general_panel, unit_system, has_parent=False)

        self.aui_panel.AddPage(general_panel, self.history, self.cultural, self.well_spacing,
                               title='General', bitmap=ico.analogue_16x16.GetBitmap())

        # Static -------------------------------------------------------------------------------------------------------
        static_panel = wx.Panel(self.properties)
        self.static = pp.StaticPanel(static_panel, unit_system, has_parent=False)

        self.aui_panel.AddPage(static_panel, self.static,
                               title='Static', bitmap=ico.grid_properties_16x16.GetBitmap())

        # sizing aui ---------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()

        self.properties.sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

        # events -------------------------------------------------------------------------------------------------------
        self.history.history.BindMethod(1, self.OnOpenFitFrame)

    def InitUI(self):
        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Analogue - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add analogue')

    # events -----------------------------------------------------------------------------------------------------------
    def OnOpenFitFrame(self, event):
        profile, _ = self.history.Get()
        frame = CurveFitFrame(self, self._unit_system, self._functions.Copy(), profile)
        frame.ShowModal()

        if frame.IsSaved():
            self._functions = frame.GetFunctions()

    # external events --------------------------------------------------------------------------------------------------
    def LoadCustom(self):
        properties = self._entity.GetProperties()
        self._functions = properties.functions.Copy()

        self.static.SetValues(*properties.statics.Get())
        self.static.SetUncertainties(*properties.statics_unc.Get())

    def SaveCustom(self, entity):
        properties = entity.GetProperties()

        try:
            properties.statics.Set(*self.static.GetValues())
            properties.statics_unc.Set(*self.static.GetUncertainties())
            properties.functions.Set(*self._functions.Get())

        except ValueError:
            return False

        return True


class TypecurveFrame(EntityPropertiesFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Typecurve(), entity_mgr, object_menu_page, item, item_parent)

        # used for access to object_menu tree, to add/modify entities
        self._unit_system = unit_system
        self._functions = None

        self.parent = pp.AnaloguePanel(self.properties, entity_mgr, object_menu_page.tree)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

        # events -------------------------------------------------------------------------------------------------------
        self.parent.analogue.BindMethod(0, self.OnOpenFunctionsButton)

    def InitUI(self):
        self.InitTitleBar()

        # sizing -------------------------------------------------------------------------------------------------------
        self.properties.sizer.Add(self.parent, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)

        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Typecurve - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add typecurve')

    def OnOpenFunctionsButton(self, event):
        # gather profile
        pointer = self.parent.Get()[0]
        if pointer is not None:
            analogue = self._entity_mgr.GetEntity(*pointer)
            profile = analogue.GetHistory()
        else:
            profile = None

        frame = FunctionFrame(self, self._unit_system, self._functions.Copy(), profile)
        frame.ShowModal()

        if frame.IsSaved():
            self._functions = frame.GetFunctions()

    def LoadCustom(self):
        properties = self._entity.GetProperties()
        self._functions = properties.functions.Copy()

        # only done on creation of the Typecurve
        if (self._item is None) and (self._item_parent is not None):
            analogue = self._entity_mgr.GetEntity(*self._item_parent.GetData().GetPointer())
            properties = analogue.GetProperties()
            self._functions.SetModels(*properties.functions.GetModels())
            self._functions.Initialize()

    def SaveCustom(self, entity):
        properties = entity.GetProperties()
        properties.functions.Set(*self._functions.Get())

        return True


class ScalingFrame(EntityFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu, item=None, item_parent=None):
        super().__init__(parent, em.Scaling(), entity_mgr, object_menu.entities, item, item_parent)

        self._object_menu = object_menu

        self._selection_items = (self._object_menu.entities.subsurface, self._object_menu.entities.portfolio)
        self._selection_types = (ID_PRODUCER, ID_ANALOGUE)

        self._current_idx = None

        # objects used for plotting
        self._x_axis = (vm.Time(unit_system), vm.Time(unit_system), vm.OilCumulative(unit_system), vm.Time(unit_system))
        self._y_axis = (vm.LiquidPotential(unit_system), vm.OilPotential(unit_system),
                        vm.WaterCut(unit_system), vm.GasOilRatio(unit_system))

        self.name = pp.NamePanel(self.custom)
        self.scaler = pp.ScalerSelectionPanel(self.custom)
        self.normalize = wx.Button(self.custom, label='Normalize')

        self.evaluation = pp.ScalerEvaluationPanel(self.custom)
        self.chart = CartesianChartPanel(self.custom, None, None)

        self.evaluation.EnableCtrls(False)

        # preparing aui-manager ----------------------------------------------------------------------------------------
        self.aui_panel = pp.PropertiesAUIPanel(self.custom, min_size=(270, 255))

        # production data ----------------------------------------------------------------------------------------------
        selection_panel = wx.Panel(self.custom)
        self.selection = pp.SelectionTree(selection_panel, self._object_menu.entities, expand_collapse=True)

        self.aui_panel.AddPage(selection_panel, self.selection, proportions=(1,),
                               title='Production data', bitmap=ico.analogue_16x16.GetBitmap())

        # static data --------------------------------------------------------------------------------------------------
        static_panel = wx.Panel(self.custom)
        self.static = pp.SelectionTree(static_panel, object_menu.variables, expand_collapse=True)

        self.aui_panel.AddPage(static_panel, self.static, proportions=(1,),
                               title='Static data', bitmap=ico.grid_properties_16x16.GetBitmap())

        # updating aui -------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()

        self.SetMinSize(wx.Size(900, 555))
        self.InitUI()
        self.Center()

        self.chart.Realize()  # required for initialization of the figure size
        self.Load()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_COMBOBOX, self.OnComboBox, self.scaler.selection)
        self.Bind(wx.EVT_BUTTON, self.OnInsert, self.evaluation.arrow.button)
        self.Bind(wx.EVT_BUTTON, self.OnNormalize, self.normalize)

    def InitUI(self):
        self.InitTitleBar()

        # trees --------------------------------------------------------------------------------------------------------
        items = (self._object_menu.variables.statics,)
        self.static.Populate(items, ('statics',), ct_type=0)

        # sizing -------------------------------------------------------------------------------------------------------
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_sizer.Add(self.name, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        left_sizer.Add(self.scaler, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        left_sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)
        left_sizer.Add(SectionSeparator(self.custom, label='Normalize', bitmap=ico.scaling_chart_16x16.GetBitmap()), 0, wx.EXPAND | wx.ALL, GAP)
        left_sizer.Add(self.normalize, 0, wx.EXPAND | wx.ALL, GAP)

        right_sizer = wx.BoxSizer(wx.VERTICAL)
        right_sizer.Add(self.evaluation, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        right_sizer.Add(self.chart, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)

        self.custom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.custom_sizer.Add(left_sizer, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM & ~wx.TOP), GAP)
        self.custom_sizer.Add(wx.StaticLine(self.custom, wx.ID_ANY, style=wx.LI_VERTICAL), 0, wx.ALL | wx.EXPAND, GAP)
        self.custom_sizer.Add(right_sizer, 1, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)

        self.custom.SetSizer(self.custom_sizer)
        self.custom_sizer.Fit(self.custom)

        self.Realize()

    def InitTitleBar(self):
        # title & icon -------------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Scaling - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add Scaling')

    # events -----------------------------------------------------------------------------------------------------------
    def OnComboBox(self, event):
        self.evaluation.EnableCtrls(True)
        idx = event.GetInt()

        self.SaveState()

        # load state
        self.evaluation.Set(self.scaler.selection.GetClientData(idx))
        self._current_idx = idx

    def OnInsert(self, event):
        item = self.static.tree.GetSelection()
        if not item:
            return

        data = item.GetData()
        if data.IsPointer():
            self.evaluation.Append(data.GetId())

    def OnNormalize(self, event):
        self.SaveState()

        items = self.selection.GetCheckedItems()
        entities = self._entity_mgr.GetEntities([i.GetData().GetPointer() for i in items])
        entities = [e.Copy() for e in entities if e.GetHistory() is not None]

        # save the current settings into an evaluator
        evaluator = EvaluationProperty()
        evaluator.Set(*self.scaler.selection.GetData())

        # calculate scalers and temporally scale the histories of all the entities
        for entity in entities:
            properties = entity.GetProperties()
            statics = properties.statics.get()
            fluids = properties.res_fluids.get()
            history = properties.history.get()

            scalers = [None for _ in range(4)]
            box = None

            for i in range(4):

                try:

                    scalers[i] = evaluator.eval(i, *statics)

                except NameError as e:

                    box = wx.MessageDialog(self, message='Parameter with the {} does not exist.'.format(str(e)),
                                           caption='Name Error')

                except SyntaxError as e:

                    box = wx.MessageDialog(self, message='Syntax error in statement: {}'.format(str(e)),
                                           caption='Syntax Error')

                if scalers[i] is not None:
                    scalers[i] **= -1.

            if box is not None:
                box.ShowModal()
                box.Destroy()
                return

            history.temporal_scale(scalers, fluids)

        self.DisplayChart(entities)

    # internal methods -------------------------------------------------------------------------------------------------
    def SaveState(self):
        # save state
        if self._current_idx is not None:
            self.scaler.selection.SetClientData(self._current_idx, self.evaluation.Get())

    def DisplayChart(self, entities):

        axes_item = AxesItem()
        axes_item.MergeScaledHistory(self._x_axis, self._y_axis, entities)
        self.chart.Realize(axes_item)

    # external methods -------------------------------------------------------------------------------------------------
    def LoadCustom(self):
        properties = self._entity.GetProperties()
        self.scaler.selection.SetData(properties.evaluations.Get())

    def LoadName(self):
        self.name.Set(self._entity.GetName())

    def SaveCustom(self, entity):
        self.SaveState()
        properties = entity.GetProperties()
        properties.evaluations.Set(*self.scaler.selection.GetData())

        return True

    def SaveName(self, entity):
        entity.SetName(self.name.Get())


class FieldFrame(EntitySelectionFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Field(), entity_mgr, object_menu_page, item, item_parent)

        self._selection_items = (self._object_menu_page.subsurface,)
        self._selection_types = (ID_RESERVOIR,)

        self.cultural = pp.CulturalOutlinePanel(self.properties)
        self.license = pp.LicensePanel(self.properties)
        self.plateau = pp.PlateauPanel(self.properties, unit_system)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        self.InitTitleBar()

        # sizing -------------------------------------------------------------------------------------------------------
        self.properties.sizer.Add(self.cultural, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.license,  0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.plateau,  0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)

        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Field - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add field')


class BlockFrame(EntitySelectionFrame):
    def __init__(self, parent, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Block(), entity_mgr, object_menu_page, item, item_parent)

        self._selection_items = (self._object_menu_page.subsurface,)
        self._selection_types = (ID_POLYGON,)

        self.cultural = pp.CulturalOutlinePanel(self.properties)
        self.license = pp.LicensePanel(self.properties)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        self.InitTitleBar()

        # sizing -------------------------------------------------------------------------------------------------------
        self.properties.sizer.Add(self.cultural, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.license,  0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)

        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._entity is not None:
            self.SetTitle('Block - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add block')


class PlatformFrame(EntitySelectionFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Platform(), entity_mgr, object_menu_page, item, item_parent)

        self._selection_items = (self._object_menu_page.subsurface,)
        self._selection_types = (ID_PRODUCER, ID_INJECTOR)

        self.cultural = pp.CulturalPointPanel(self.properties)
        self.availability = pp.AvailabilityPanel(self.properties, has_parent=False)
        self.gas_lift = pp.GasLiftPanel(self.properties, unit_system, has_parent=False)
        self.wag = pp.WagPanel(self.properties, has_parent=False)
        self.inj_potentials = pp.InjectionPotentialPanel(self.properties, unit_system, has_parent=False)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetSize(self.GetSize()[0] + 50, self.GetSize()[1])
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        self.InitTitleBar()

        # sizing -------------------------------------------------------------------------------------------------------
        self.properties.sizer.Add(self.cultural,       0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.availability,   0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.gas_lift,       0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.wag,            0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.inj_potentials, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)

        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Platform - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add platform')


class ProcessorFrame(EntitySelectionFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Processor(), entity_mgr, object_menu_page, item, item_parent)

        self._selection_items = (self._object_menu_page.facilities, self._object_menu_page.subsurface)
        self._selection_types = (ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR)

        # preparing aui-manager ----------------------------------------------------------------------------------------
        self.aui_panel = pp.PropertiesAUIPanel(self.properties, min_size=(350, 500))

        # general ------------------------------------------------------------------------------------------------------
        general_panel = wx.Panel(self.properties)
        self.cultural = pp.CulturalPointPanel(general_panel)
        self.availability = pp.AvailabilityPanel(general_panel)
        self.inflow = pp.InflowingPhasePanel(general_panel)

        self.aui_panel.AddPage(general_panel, self.cultural, self.availability, self.inflow,
                               title='General', bitmap=ico.well_16x16.GetBitmap())

        # constraints --------------------------------------------------------------------------------------------------
        constraint_panel = wx.Panel(self.properties)
        self.flow_constraints = pp.FlowConstraintPanel(constraint_panel, unit_system)
        self.inj_constraints = pp.InjectionConstraintPanel(constraint_panel, unit_system)

        self.aui_panel.AddPage(constraint_panel, self.flow_constraints, self.inj_constraints,
                               title='Constraints', bitmap=ico.flow_constraint_16x16.GetBitmap())

        # splits -------------------------------------------------------------------------------------------------------
        split_panel = wx.Panel(self.properties)
        self.split = pp.FlowSplitPanel(split_panel)
        self.flow_tree = pp.ProcessorFlowTree(split_panel)

        self.aui_panel.AddPage(split_panel, self.split, self.flow_tree, proportions=(0, 1.),
                               title='Splits', bitmap=ico.flow_constraint_16x16.GetBitmap())

        # sizing aui ---------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()
        self.properties.sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

        # events -------------------------------------------------------------------------------------------------------
        self.inflow.BindMethodToCtrls(wx.EVT_CHECKBOX, self.OnChecked)
        self.split.BindMethodToCtrls(wx.EVT_COMBOBOX, self.OnChoice, to=1)

    def InitUI(self):
        self.InitTitleBar()

        self.flow_constraints.EnableCtrls(False)
        self.inj_constraints.EnableCtrls(False)
        self.split.EnableCtrls(False, from_=1)

        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Processing equipment - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add processing equipment')

    def OnChecked(self, event):
        oil, gas, water, gas_inj, water_inj = self.inflow.Get()
        splits = self.split.Get()
        split = splits[0]

        # oil
        self.flow_constraints.EnableCtrls(oil, from_=0, to=1)
        if split:
            self.split.EnableCtrls(oil, from_=1, to=2)

        # gas
        self.flow_constraints.EnableCtrls(gas, from_=1, to=2)
        if split:
            self.split.EnableCtrls(gas, from_=2, to=3)

        # water
        self.flow_constraints.EnableCtrls(water, from_=2, to=3)
        if split:
            self.split.EnableCtrls(water, from_=3, to=4)

        # gas inj
        self.inj_constraints.EnableCtrls(gas_inj, from_=0, to=1)
        if split:
            self.split.EnableCtrls(gas_inj, from_=4, to=5)

        # water inj
        self.inj_constraints.EnableCtrls(water_inj, from_=1)
        if split:
            self.split.EnableCtrls(water_inj, from_=5, to=6)

        # liquid
        self.flow_constraints.EnableCtrls(oil and water, from_=3)

    def OnChoice(self, event):
        splits = self.split.Get()

        if splits[0]:
            self.OnChecked(None)
        else:
            self.split.EnableCtrls(False, from_=1)

    def LoadCustom(self):
        properties = self._entity.GetProperties()
        self.flow_tree.Populate(self._entity, self._entity_mgr)

        primary_node = properties.primary_node.Get()[0]

        if primary_node is not None:
            self.flow_tree.CheckItemById(primary_node)

        self.OnChecked(None)

    def SaveCustom(self, entity):
        properties = entity.GetProperties()

        primary_node = self.flow_tree.GetCheckedItems()
        if primary_node:
            primary_node = primary_node[0].GetData()
        else:
            primary_node = None

        properties.primary_node.Set(primary_node)

        return True


class PipelineFrame(EntitySelectionFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Pipeline(), entity_mgr, object_menu_page, item, item_parent)

        self._selection_items = (self._object_menu_page.facilities, self._object_menu_page.subsurface)
        self._selection_types = (ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR)

        self.cultural = pp.CulturalOutlinePanel(self.properties)
        self.availability = pp.AvailabilityPanel(self.properties)
        self.flow_constraints = pp.FlowConstraintPanel(self.properties, unit_system)
        self.inj_constraints = pp.InjectionConstraintPanel(self.properties, unit_system)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetSize(self.GetSize()[0] + 50, self.GetSize()[1])
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        self.InitTitleBar()

        # sizing -------------------------------------------------------------------------------------------------------
        self.properties.sizer.Add(self.cultural,         0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.availability,     0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.flow_constraints, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)
        self.properties.sizer.Add(self.inj_constraints,  0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)

        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Pipeline - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add pipeline')


class ProducerFrame(EntityPropertiesFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Producer(), entity_mgr, object_menu_page, item, item_parent)

        self._unit_system = unit_system
        self._functions = None

        # preparing aui-manager ----------------------------------------------------------------------------------------
        self.aui_panel = pp.PropertiesAUIPanel(self.properties, min_size=(370, 570))

        # general ------------------------------------------------------------------------------------------------------
        general_panel = wx.Panel(self.properties)
        self.phase = pp.ProductionPhasePanel(general_panel)
        self.cultural = pp.CulturalTrajectoryPanel(general_panel)
        self.history = pp.HistoryFitPanel(general_panel)
        self.prediction = pp.PredictionPanel(general_panel, entity_mgr, object_menu_page.tree, disable_dca=False)
        self.scaling_eval = pp.ScalingEvaluationPanel(general_panel, entity_mgr, object_menu_page.tree)
        self.well_spacing = pp.WellSpacingPanel(general_panel, unit_system)

        self.aui_panel.AddPage(general_panel, self.phase, self.cultural, self.history, self.prediction,
                               self.scaling_eval, self.well_spacing, title='General', bitmap=ico.well_16x16.GetBitmap())

        # Facility -----------------------------------------------------------------------------------------------------
        facility_panel = wx.Panel(self.properties)
        self.availability = pp.AvailabilityPanel(facility_panel)
        self.gas_lift = pp.GasLiftPanel(facility_panel, unit_system)
        self.flow_constraints = pp.FlowConstraintPanel(facility_panel, unit_system)
        self.gl_constraint = pp.LiftGasConstraintPanel(facility_panel, unit_system)

        self.aui_panel.AddPage(facility_panel, self.availability, self.gas_lift, self.flow_constraints, self.gl_constraint,
                               title='Facility', bitmap=ico.platforms_16x16.GetBitmap())

        # Stakes -------------------------------------------------------------------------------------------------------
        stakes_panel = wx.Panel(self.properties)
        self.risking = pp.RiskingPanel(stakes_panel)
        self.volumes = pp.VolumePanel(stakes_panel, unit_system)

        self.aui_panel.AddPage(stakes_panel, self.risking, self.volumes,
                               title='Stakes', bitmap=ico.risking_16x16.GetBitmap())

        # Static -------------------------------------------------------------------------------------------------------
        static_panel = wx.Panel(self.properties)
        self.static = pp.StaticPanel(static_panel, unit_system)

        self.aui_panel.AddPage(static_panel, self.static, title='Static', bitmap=ico.grid_properties_16x16.GetBitmap())

        # Scaling ------------------------------------------------------------------------------------------------------
        scaling_panel = wx.Panel(self.properties)
        self.scaling = pp.ScalingPanel(scaling_panel)

        self.aui_panel.AddPage(scaling_panel, self.scaling, title='Scaling', bitmap=ico.profiles_chart_16x16.GetBitmap())

        # sizing aui ---------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()
        self.properties.sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

        # events -------------------------------------------------------------------------------------------------------
        self.history.history.BindMethod(1, self.OnOpenFitFrame)
        self.prediction.typecurve.BindMethod(1, self.OnOpenFunctionsFrame)

    def InitUI(self):
        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Producer - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add producer')

    # events -----------------------------------------------------------------------------------------------------------
    def OnOpenFitFrame(self, event):
        profile, _ = self.history.Get()
        frame = CurveFitFrame(self, self._unit_system, self._functions.Copy(), profile)
        frame.ShowModal()

        if frame.IsSaved():
            self._functions = frame.GetFunctions()

            for prediction in self.prediction.prediction.GetData():
                prediction.UpdateModels(*self._functions.GetModels())

    def OnOpenFunctionsFrame(self, event):
        profile, _ = self.history.Get()
        functions = self.prediction.GetFunctions().Copy()
        frame = FunctionFrame(self, self._unit_system, functions, profile)
        frame.ShowModal()

        if frame.IsSaved():
            self.prediction.SetFunctions(frame.GetFunctions())

    def GetImageId(self):
        return self.phase.GetSelection()

    def LoadCustom(self):
        properties = self._entity.GetProperties()
        self._functions = properties.functions.Copy()
        self.prediction.Set(*properties.prediction.Get())

        self.static.SetValues(*properties.statics.Get())
        self.static.SetUncertainties(*properties.statics_unc.Get())

        self.scaling.SetValues(*properties.scalers.Get())
        self.scaling.SetUncertainties(*properties.scalers_unc.Get())

        if self._entity.IsControlled():
            self.static.EnableCtrls(False)
            self.scaling.EnableCtrls(False)

    def SaveCustom(self, entity):
        properties = entity.GetProperties()

        try:

            properties.statics.Set(*self.static.GetValues())
            properties.statics_unc.Set(*self.static.GetUncertainties())

            properties.scalers.Set(*self.scaling.GetValues())
            properties.scalers_unc.Set(*self.scaling.GetUncertainties())

            properties.functions.Set(*self._functions.Get())

        except ValueError:
            return False

        return True


class InjectorFrame(EntitySelectionFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Injector(), entity_mgr, object_menu_page, item, item_parent)

        self._selection_items = (self._object_menu_page.subsurface,)
        self._selection_types = (ID_PRODUCER,)

        # preparing aui-manager ----------------------------------------------------------------------------------------
        self.aui_panel = pp.PropertiesAUIPanel(self.properties, min_size=(300, 400))

        # general ------------------------------------------------------------------------------------------------------
        general_panel = wx.Panel(self.properties)
        self.phase = pp.InjectionPhasePanel(general_panel)
        self.cultural = pp.CulturalTrajectoryPanel(general_panel)
        self.history = pp.HistoryPanel(general_panel)
        self.voidage = pp.VoidagePanel(general_panel, unit_system)
        self.inj_potentials = pp.InjectionPotentialPanel(general_panel, unit_system)

        self.aui_panel.AddPage(general_panel, self.phase, self.cultural, self.history, self.voidage,
                               self.inj_potentials, title='General', bitmap=ico.well_16x16.GetBitmap())

        # Facility -----------------------------------------------------------------------------------------------------
        facility_panel = wx.Panel(self.properties)
        self.availability = pp.AvailabilityPanel(facility_panel)
        self.inj_constraints = pp.InjectionConstraintPanel(facility_panel, unit_system)
        self.wag = pp.WagPanel(facility_panel)

        self.aui_panel.AddPage(facility_panel, self.availability, self.inj_constraints, self.wag,
                               title='Facility', bitmap=ico.platforms_16x16.GetBitmap())

        # sizing aui ---------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()
        self.properties.sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)

        self.InitUI()
        self.Load()

        self.OnPhaseChecked(None, *self.phase.Get())

        self.Center()
        self.SetSize(self.GetSize()[0] + 50, self.GetSize()[1])
        self.SetMinSize(self.GetSize())

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_RADIOBOX, self.OnPhaseChecked, self.phase.radio)
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnTreeItemChecked, self.selection.tree)
        self.Bind(wx.EVT_BUTTON, self.OnButtonClicked, self.voidage.ratio.button)

    def InitUI(self):
        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Injector - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add injector')

    def OnPhaseChecked(self, event, phase=None):
        if phase is None:
            phase = event.GetInt()

        self.wag.Enable(False)

        if (phase == 2) and self.wag.UseSelf():   # WAG
            self.wag.Enable(True)

    def OnTreeItemChecked(self, event):
        # update proportions to hold the producers that are checked
        proportions = self.voidage.GetProportions()

        item = event.GetItem()
        data = item.GetData()
        id_ = data.GetId()

        if not item.IsChecked():
            # remove producer that is no longer in the list
            del proportions[id_]
            self.RecalculateProportions(proportions)

        else:
            # add new producer to list.
            proportion = self.RecalculateProportions(proportions, additional=1)
            proportions[id_] = [item.GetText(), proportion, False]

    @staticmethod
    def RecalculateProportions(proportions, additional=0):
        # Proportions are filled by equally distributing proportions of producers
        # which have not manually had their proportion set to a fixed number.
        spare = 1. - np.sum([p[1] for p in proportions.values() if p[2]])

        # find ids of unedited wells
        keys = [key for key, (_, _, is_edited) in proportions.items() if not is_edited]
        count = len(keys) + additional

        if not count:
            return

        proportion = round(spare / float(count), 2)

        for key in keys:
            proportions[key][1] = proportion

        return proportion

    def OnButtonClicked(self, event):
        # update proportions to hold the producers that are checked
        proportion = self.voidage.GetProportions()

        # cleaning up proportions by removing producers that have been deleted since last open
        for key in list(proportion):
            try:
                _ = self._entity_mgr.GetEntity(key, '_producers')
            except KeyError:
                del proportion[key]

        VoidageProportionFrame(self, proportion).Show()

    def GetImageId(self):
        return self.phase.GetSelection()


class VoidageProportionFrame(ObjectFrame):
    def __init__(self, parent, proportion):
        super().__init__(parent=parent, title='Producer Voidage Proportion')

        self._proportion = proportion  # {id_: [name, proportion, is_edited]}
        self._is_edited = [is_edited for (_, _, is_edited) in self._proportion.values()]

        self.grid = wx.grid.Grid(self.custom)

        self.InitUI()

        # events -------------------------------------------------------------------------------------------------------
        self.apply_button.Bind(wx.EVT_BUTTON, self.OnApplyButton)
        self.ok_button.Bind(wx.EVT_BUTTON, self.OnOKButton)
        self.Bind(EVT_GRID_CELL_CHANGED, self.OnGridCellChanged, self.grid)

    def InitUI(self):
        self.SetIcon(ico.wag_voidage_replacement_16x16.GetIcon())

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.grid.CreateGrid(len(self._proportion), 1)
        self.grid.SetColLabelValue(0, 'Proportion')

        for i, (producer, fraction, is_edited) in enumerate(self._proportion.values()):
            self.grid.SetRowLabelValue(i, producer)
            self.grid.SetCellValue(i, 0, str(fraction))

            if is_edited:
                self.grid.SetCellTextColour(i, 0, wx.Colour(47, 117, 181))

        sizer.Add(self.grid, 1, wx.EXPAND)
        self.custom.SetSizer(sizer)
        sizer.Fit(self.custom)

    def OnApplyButton(self, event):
        proportions = []

        for i, (_, proportion, _) in enumerate(self._proportion.values()):
            try:
                value = float(self.grid.GetCellValue(i, 0))
                if 0. <= value <= 1.:
                    proportions.append(value)
                else:
                    box = wx.MessageDialog(self, 'All proportions must be in the range 0 to 1', caption='Value Error')
                    box.ShowModal()
                    box.Destroy()
                    return False

            except ValueError:
                box = wx.MessageDialog(self, 'All proportions must be numbers', caption='Type Error')
                box.ShowModal()
                box.Destroy()
                return False

        if np.sum(proportions) > 1.:
            box = wx.MessageDialog(self, 'The sum of proportions must less than equal to 1.0', caption='Value Error')
            box.ShowModal()
            box.Destroy()
            return False

        # transferring properties to saved dictionary, now that all values are cleared
        for i, key, in enumerate(self._proportion):
            self._proportion[key][1] = proportions[i]
            self._proportion[key][2] = self._is_edited[i]

        return True

    def OnOKButton(self, event):
        saved = self.OnApplyButton(None)

        if saved:
            self.Close(True)

    def OnGridCellChanged(self, event):
        row = event.GetRow()
        self._is_edited[row] = True

        # colour the cell text blue
        self.grid.SetCellTextColour(row, 0, wx.Colour(47, 117, 181))


class SubsurfaceFrame(EntityPropertiesFrame):
    # Frame used for Reservoir, Theme
    def __init__(self, parent, unit_system, entity, entity_mgr, object_menu_page, item=None, item_parent=None, has_parent=False, derived=True):
        super().__init__(parent, entity, entity_mgr, object_menu_page, item, item_parent)

        self._tree = object_menu_page.tree  # access to selection when clicking on ArrowButtonInsertControl

        # preparing aui-manager ----------------------------------------------------------------------------------------
        self.aui_panel = pp.PropertiesAUIPanel(self.properties, min_size=(370, 450))

        # analogue -----------------------------------------------------------------------------------------------------
        analogue_panel = wx.Panel(self.properties)
        self.cultural = pp.CulturalOutlinePanel(analogue_panel)
        self.prediction = pp.PredictionPanel(analogue_panel, entity_mgr, self._tree, has_parent=has_parent)
        self.scaling_eval = pp.ScalingEvaluationPanel(analogue_panel, entity_mgr, self._tree, has_parent=has_parent)
        self.well_spacing = pp.WellSpacingPanel(analogue_panel, unit_system, has_parent=has_parent)

        self.aui_panel.AddPage(analogue_panel, self.cultural, self.prediction, self.scaling_eval, self.well_spacing,
                               title='Analogue', bitmap=ico.analogue_16x16.GetBitmap())

        # fluids -------------------------------------------------------------------------------------------------------
        fluids_panel = wx.Panel(self.properties)
        self.res_fluids = pp.ReservoirFluidPanel(fluids_panel, unit_system, has_parent=has_parent)
        self.inj_fluids = pp.InjectionFluidPanel(fluids_panel, unit_system, has_parent=has_parent)

        self.aui_panel.AddPage(fluids_panel, self.res_fluids, self.inj_fluids,
                               title='Fluids', bitmap=ico.fluids_16x16.GetBitmap())

        # stakes -------------------------------------------------------------------------------------------------------
        stakes_panel = wx.Panel(self.properties)
        self.risking = pp.RiskingPanel(stakes_panel, derived=derived)
        self.volumes = pp.VolumePanel(stakes_panel, unit_system, derived=derived)

        self.aui_panel.AddPage(stakes_panel, self.risking, self.volumes,
                               title='Stakes', bitmap=ico.risking_16x16.GetBitmap())

        # static -------------------------------------------------------------------------------------------------------
        static_panel = wx.Panel(self.properties)
        self.static = pp.StaticPanel(static_panel, unit_system, has_parent=has_parent)

        self.aui_panel.AddPage(static_panel, self.static, title='Static', bitmap=ico.grid_properties_16x16.GetBitmap())

        # scaling ------------------------------------------------------------------------------------------------------
        scaling_panel = wx.Panel(self.properties)
        self.scaling = pp.ScalingPanel(scaling_panel, has_parent=has_parent)

        self.aui_panel.AddPage(scaling_panel, self.scaling, title='Scaling', bitmap=ico.profiles_chart_16x16.GetBitmap())

        # sizing aui ---------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()
        self.properties.sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)

        self.SetMinSize(size=(370, 450))

    def LoadCustom(self):
        properties = self._entity.GetProperties()
        self.prediction.Set(*properties.prediction.Get())

        self.static.SetValues(*properties.statics.Get())
        self.static.SetUncertainties(*properties.statics_unc.Get())

        self.scaling.SetValues(*properties.scalers.Get())
        self.scaling.SetUncertainties(*properties.scalers_unc.Get())

        if self._entity.IsControlled():
            self.static.EnableCtrls(False)
            self.scaling.EnableCtrls(False)

    def SaveCustom(self, entity):
        properties = entity.GetProperties()

        try:

            properties.statics.Set(*self.static.GetValues())
            properties.statics_unc.Set(*self.static.GetUncertainties())

            properties.scalers.Set(*self.scaling.GetValues())
            properties.scalers_unc.Set(*self.scaling.GetUncertainties())

        except ValueError:
            return False

        return True


class ReservoirFrame(SubsurfaceFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, unit_system, em.Reservoir(), entity_mgr, object_menu_page, item, item_parent)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Reservoir - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add reservoir')


class ThemeFrame(SubsurfaceFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, unit_system, em.Theme(), entity_mgr, object_menu_page, item, item_parent, has_parent=True)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Theme - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add theme')


class PolygonFrame(SubsurfaceFrame):
    def __init__(self, parent, unit_system, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, unit_system, em.Polygon(), entity_mgr, object_menu_page, item, item_parent, has_parent=True, derived=False)

        self._selection_items = (self._object_menu_page.portfolio,)
        self._selection_types = (ID_ANALOGUE,)

        # change from EntityPropertiesFrame to EntitySelectionFrame
        splitter = wx.SplitterWindow(self.custom, wx.ID_ANY, style=wx.SP_THIN_SASH | wx.SP_LIVE_UPDATE)
        self.selection = pp.SelectionTree(splitter, self._object_menu_page)
        self.properties.Reparent(splitter)
        splitter.SplitVertically(self.selection, self.properties, 200)

        self.custom_sizer.Clear(delete_windows=False)
        self.custom_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, GAP)
        self.custom.SetSizer(self.custom_sizer)

        self.aui_panel.SetMinSize(size=(420, 450))

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Polygon - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add polygon')


class ProjectFrame(EntityPropertiesFrame):
    def __init__(self, parent, entity_mgr, object_menu, item=None, item_parent=None):
        super().__init__(parent, em.Project(), entity_mgr, object_menu, item, item_parent)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetMinSize(self.GetSize())

    def InitUI(self):
        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Project - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add project')


class HistoryFrame(EntityFrame):
    def __init__(self, parent, settings, variable_mgr, entity_mgr, object_menu, item=None, item_parent=None):
        super().__init__(parent, em.History(), entity_mgr, object_menu.projects, item, item_parent)

        self._settings = settings
        self._variable_mgr = variable_mgr
        self._object_menu = object_menu

        self._selection_items = (self._object_menu.entities.subsurface,)
        self._selection_types = (ID_PRODUCER, ID_INJECTOR)

        # objects related to plotting
        unit_system = settings.GetUnitSystem()
        self._dateline = None
        self._historical = None  # total historical production
        self._simulated = None   # total simulated production
        self._x_axis = vm.Date()
        self._production_variables = [vm.LiftGasCumulative(unit_system), vm.TotalGasCumulative(unit_system),
                                      vm.WaterInjectionCumulative(unit_system), vm.GasInjectionCumulative(unit_system)]

        self._case = None

        self.name = pp.NamePanel(self.custom)
        self.selection = pp.SelectionTree(self.custom, object_menu.entities, expand_collapse=True)
        self.timeline = pp.TimelinePanel(self.custom)

        self.run = wx.Button(self.custom, label='Run')
        self.chart = CartesianChartPanel(self.custom, None, None)

        self.run.Enable(False)

        self.SetMinSize(wx.Size(900, 600))
        self.InitUI()
        self.Center()

        self.chart.Realize()  # required for initialization of the figure size
        self.Load()

        # events -------------------------------------------------------------------------------------------------------
        self.run.Bind(wx.EVT_BUTTON, self.OnRun)

    def InitUI(self):
        # sizing & layout ----------------------------------------------------------------------------------------------
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_sizer = wx.BoxSizer(wx.VERTICAL)

        input_sizer.Add(self.name, 0, wx.EXPAND | wx.ALL, GAP)
        input_sizer.Add(self.selection, 1, wx.EXPAND | wx.ALL, GAP)
        input_sizer.Add(self.timeline, 0, wx.EXPAND | wx.ALL, GAP)
        input_sizer.Add(SectionSeparator(self.custom, label='Run', bitmap=ico.run_16x16.GetBitmap()), 0, wx.EXPAND | wx.ALL, GAP)
        input_sizer.Add(self.run, 0, wx.EXPAND | wx.ALL, GAP)

        sizer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, GAP)
        sizer.Add(wx.StaticLine(self.custom, wx.ID_ANY, style=wx.LI_VERTICAL), 0, wx.ALL | wx.EXPAND, GAP)
        sizer.Add(self.chart, 1, wx.EXPAND | wx.ALL, GAP)

        self.custom.SetSizer(sizer)
        sizer.Fit(self.custom)

        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # title & icon -------------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('History - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add History')

    # events -------------------------------------------------------------------------------------------------------
    def OnRun(self, event):
        # saving prior to running to get updated parameters
        if not self.Save(self._entity):
            return

        box = None
        history = None

        try:

            history = self._entity_mgr.GetHistoryCase(self._entity)
            history.Run()
            history.PostProcess(self._variable_mgr.GetSummaries(), self._settings)

        except ValueError as e:

            box = wx.MessageDialog(self, message=str(e), caption='Value Error')

        except NameError as e:

            box = wx.MessageDialog(self, message=str(e), caption='Name Error')

        except SyntaxError as e:

            box = wx.MessageDialog(self, message=str(e), caption='Syntax Error')

        if box is not None:
            box.ShowModal()
            box.Destroy()
            return

        self.CalculateTotalProduction(history)
        self._case = history

    def CalculateTotalProduction(self, history):
        self._dateline, self._historical, self._simulated = history.CalculateTotalProduction()
        self.DisplayChart()

    def DisplayChart(self):
        axes_item = AxesItem()
        axes_item.MergeTotalProduction(self._x_axis, self._production_variables, self._dateline, self._historical, self._simulated)
        self.chart.Realize(axes_item)

    def LoadCustom(self):

        properties = self._entity.GetProperties()

        frequency, delta = properties.timeline.Get()
        if (frequency is None) or (frequency != 3):
            self.timeline.EnableCtrls(False, from_=1, to=2)

        # can only be run if the entity exists in entity_mgr
        if self._item is not None:
            self.run.Enable(True)

        # draw charts
        self._dateline, self._historical, self._simulated = properties.total_production.Get()
        if self._dateline is not None:
            self.DisplayChart()

    def LoadName(self):
        self.name.Set(self._entity.GetName())

    def SaveCustom(self, entity):
        properties = entity.GetProperties()
        properties.total_production.Set(self._dateline, self._historical, self._simulated)

        # if self._item is None:
        #     self._entity_mgr.PreallocateHistoryResults()
        # else:
        #     if self._case is not None:
        #         self._entity_mgr.PreallocateHistoryResults(self._entity.GetId())

        if self._case is not None:
            self._entity_mgr.TransferSimulationCase(self._entity, self._case, self._variable_mgr.GetSummaries(), self._settings)

        return True

    def SaveName(self, entity):
        entity.SetName(self.name.Get())


class PredictionFrame(EntityFrame):
    def __init__(self, parent, settings, variable_mgr, entity_mgr, object_menu_page, item=None, item_parent=None):
        super().__init__(parent, em.Prediction(), entity_mgr, object_menu_page, item, item_parent)

        self._variable_mgr = variable_mgr
        self._settings = settings

        self._selection_items = (self._object_menu_page.simulations,)
        self._selection_types = (ID_PREDICTION,)

        # used for plotting stochastic stability of simulation
        unit_system = settings.GetUnitSystem()
        self._stability = None
        self._stability_variables = (vm.LiquidRate(unit_system), vm.OilCumulative(unit_system),
                                     vm.WaterCut(unit_system), vm.GasOilRatio(unit_system))

        self._case = None

        self.name = pp.NamePanel(self.custom)
        self.run = wx.Button(self.custom, label='Run')
        self.chart = CartesianChartPanel(self.custom, None, None)

        self.run.Enable(False)

        # preparing aui-manager ----------------------------------------------------------------------------------------
        self.aui_panel = pp.PropertiesAUIPanel(self.custom, min_size=(270, 255))

        # Deck ---------------------------------------------------------------------------------------------------------
        setup_panel = wx.Panel(self.custom)
        self.parent = pp.ScenarioPanel(setup_panel, entity_mgr, object_menu_page.tree)
        self.history = pp.HistorySimulationPanel(setup_panel, entity_mgr, object_menu_page.tree)
        self.selection = pp.SelectionTree(setup_panel, object_menu_page, expand_collapse=True)

        self.aui_panel.AddPage(setup_panel, self.parent, self.history, self.selection, proportions=(0, 0, 1),
                               title='Setup', bitmap=ico.well_16x16.GetBitmap())

        # Options ------------------------------------------------------------------------------------------------------
        parameter_panel = wx.Panel(self.custom)
        self.plateau = pp.PlateauPanel(parameter_panel, unit_system)
        self.constrained = pp.ConstrainedModelPanel(parameter_panel)
        self.sampling = pp.SamplingPanel(parameter_panel)
        self.timeline = pp.TimelinePanel(parameter_panel)

        self.aui_panel.AddPage(parameter_panel, self.plateau, self.constrained, self.sampling, self.timeline,
                               title='Parameters', bitmap=ico.settings_16x16.GetBitmap())

        # updating aui -------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()

        # sizing -------------------------------------------------------------------------------------------------------
        input_sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer.Add(self.name, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        input_sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)
        input_sizer.Add(SectionSeparator(self.custom, label='Run', bitmap=ico.run_16x16.GetBitmap()), 0, wx.EXPAND | wx.ALL, GAP)
        input_sizer.Add(self.run, 0, wx.EXPAND | wx.ALL, GAP)

        self.custom_sizer.Add(input_sizer, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM & ~wx.TOP), GAP)
        self.custom_sizer.Add(wx.StaticLine(self.custom, wx.ID_ANY, style=wx.LI_VERTICAL), 0, wx.ALL | wx.EXPAND, GAP)
        self.custom_sizer.Add(self.chart, 1, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)

        self.custom.SetSizer(self.custom_sizer)
        self.custom_sizer.Fit(self.custom)

        self.SetMinSize(wx.Size(900, 620))
        self.InitUI()
        self.Center()

        self.chart.Realize()  # required for initialization of the figure size
        self.Load()

        # events -------------------------------------------------------------------------------------------------------
        self.run.Bind(wx.EVT_BUTTON, self.OnRun)

    def InitUI(self):
        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # title & icon -------------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Prediction - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add Prediction')

    # events -------------------------------------------------------------------------------------------------------
    def OnRun(self, event):
        # saving prior to running to get updated parameters
        if not self.Save(self._entity):
            return

        # get correlation matrices and scaling laws
        rho_v, _ = self._variable_mgr.GetCorrelationMatrix()
        rho_e, _ = self._entity_mgr.GetCorrelationMatrix()

        box = None
        prediction = None

        # try:

        prediction = self._entity_mgr.GetPredictionCase(self._entity)
        prediction.Run(rho_v, rho_e)
        prediction.PostProcess(self._variable_mgr.GetSummaries(), self._settings)

        # except ValueError as e:
        #
        #     box = wx.MessageDialog(self, message=str(e), caption='Value Error')
        #
        # except AssembleError as e:
        #
        #     box = wx.MessageDialog(self, message=str(e), caption='Assemble Error')
        #
        # except AttributeError as e:
        #
        #     box = wx.MessageDialog(self, message=str(e), caption='Attribute Error')
        #
        # except ConvergenceError as e:
        #
        #     box = wx.MessageDialog(self, message=str(e), caption='Convergence Error')
        #
        # except KeyError as e:
        #
        #     box = wx.MessageDialog(self, message=str(e), caption='Key Error')
        #
        # except NameError as e:
        #
        #     box = wx.MessageDialog(self, message=str(e), caption='Name Error')
        #
        # except SyntaxError as e:
        #
        #     box = wx.MessageDialog(self, message=str(e), caption='Syntax Error')

        if box is not None:
            box.ShowModal()
            box.Destroy()
            return

        self.CalculateStability(prediction)
        self._case = prediction

    # internal methods -------------------------------------------------------------------------------------------------
    def CalculateStability(self, prediction):
        self._stability = prediction.CalculateStability(self._stability_variables)

        self.DisplayChart()

    def DisplayChart(self):
        if self._stability is not None:
            axes_item = AxesItem()
            axes_item.MergeStability(vm.Samples(), self._stability_variables, self._stability)
            self.chart.Realize(axes_item)
        else:
            self.chart.Realize()

    # external methods -------------------------------------------------------------------------------------------------
    def LoadCustom(self):

        properties = self._entity.GetProperties()

        frequency, delta = properties.timeline.Get()
        if (frequency is None) or (frequency != 3):
            self.timeline.EnableCtrls(False, from_=1, to=2)

        # can only be run if the entity exists in entity_mgr
        if self._item is not None:
            self.run.Enable(True)

        # draw charts
        self._stability = properties.stability.Get()
        if self._stability is not None:
            self.DisplayChart()

    def LoadName(self):
        self.name.Set(self._entity.GetName())

    def SaveCustom(self, entity):
        properties = entity.GetProperties()
        properties.stability.Set(self._stability)

        # if self._item is None:
        #     self._entity_mgr.PreallocatePredictionResults()
        # else:
        #     if self._case is not None:
        #         self._entity_mgr.PreallocatePredictionResults(self._entity.GetId())

        if self._case is not None:
            self._entity_mgr.TransferSimulationCase(self._entity, self._case, self._variable_mgr.GetSummaries(), self._settings)

        return True

    def SaveName(self, entity):
        entity.SetName(self.name.Get())