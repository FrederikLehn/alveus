import os
from datetime import datetime
import wx.adv
import wx.grid
import wx.lib.agw.aui as aui
import wx.lib.fancytext as fancy

from profile_ import Profile
from cultural import Outline, WellTrajectory
from frames.frame_utilities import GetFilePath
from frames.frame_design import SectionSeparator, PropertySizer, AlignedFlexSizer, Latex2HTML, GAP, INTER_GAP
from widgets.customized_tree_ctrl import CustomizedTreeCtrl
from widgets.customized_menu import CustomMenu, CustomMenuItem
from widgets.tab_art import AuiModifiedTabArt
from widgets.insert_controls import ButtonsInsertCtrl, ArrowButtonsInsertCtrl

from widgets.text_button_control import TextButtonCtrl, ID_RIGHT, ID_LEFT
from frames.import_frames import ProfileImportFrame

import variable_mgr as vm

from _errors import LimitError
from _ids import *
import _icons as ico

GREY = wx.Colour(230, 230, 230)


# ======================================================================================================================
# Customized Controls containing information from VariableManager
# ======================================================================================================================
class PropertyCtrl:
    def __init__(self, property_):

        self._property = property_
        self._align_row = True

    def AlignRow(self):
        return self._align_row

    def ChangeProperty(self, property_):
        self._property = property_

    def GetErrorLabel(self):
        return self._property.GetComboLabel()

    def GetFrameLabel(self, idx=None):
        return self._property.GetFrameLabel(idx)

    def GetLimits(self):
        return self._property.GetLimits()

    def GetUnit(self, idx=None):
        return self._property.GetUnit(idx)


class PropertyArrowButtonsInsertCtrl(ArrowButtonsInsertCtrl, PropertyCtrl):
    def __init__(self, parent, property_, entity_mgr, tree, type_=None, lock=False, hierarchical=False, btn_bitmaps=()):
        ArrowButtonsInsertCtrl.__init__(self, parent, btn_bitmaps=btn_bitmaps)
        PropertyCtrl.__init__(self, property_)

        self.custom_textctrl.SetToolTip(self._property.GetToolTip())

        self._entity_mgr = entity_mgr
        self._tree = tree
        self._type = type_
        self._lock = lock
        self._hierarchical = hierarchical

        self.Bind(wx.EVT_BUTTON, self.OnInsertItem, self.arrow)

    # events -----------------------------------------------------------------------------------------------------------
    def OnInsertItem(self, event):
        item = self._tree.GetSelection()
        if not item:
            return

        data = item.GetData()
        if not data.IsPointer():
            return

        entity = self._entity_mgr.GetEntity(*data.GetPointer())

        if (self._type is not None) and (not entity.IsType(self._type)):
            return

        self.Insert(entity.GetName(), entity.GetBitmap(), entity.GetPointer())
        self.Lock()

    # methods ----------------------------------------------------------------------------------------------------------
    def BindMethod(self, idx, method):
        self.Bind(wx.EVT_BUTTON, method, self._buttons[idx])

    def Default(self):
        self.Clear()

    def DisableButton(self, idx):
        self._buttons[idx].Disable()

    def GetProperty(self):
        return self._property.FromFrame(self.GetClientData())

    def Lock(self):
        if self._lock:
            self.arrow.Enable(False)
            self.custom_textctrl.Enable(False)

    def SetProperty(self, property_):
        pointer = self._property.ToFrame(property_)

        if pointer is not None:

            # crude method for distinguishing between pointer and other insert methods
            if len(pointer) == 2:

                try:
                    entity = self._entity_mgr.GetEntity(*pointer)
                    self.Insert(entity.GetName(), entity.GetBitmap(), entity.GetPointer())
                    self.Lock()

                except KeyError:

                    self.Clear()  # entity has been deleted

            else:  # property_ contains label, bitmap and data

                self.Insert(*pointer)

        elif self._hierarchical:  # clear text

            self.Clear()


class PropertyBitmapComboBox(wx.adv.BitmapComboBox, PropertyCtrl):
    def __init__(self, parent, property_):  # client_data=None
        wx.adv.BitmapComboBox.__init__(self, parent, value='', style=wx.CB_READONLY)
        PropertyCtrl.__init__(self, property_)

        self.SetToolTip(self._property.GetToolTip())

        self.Initialise()

    def ChangeProperty(self, property_):
        self._property = property_
        self.Clear()
        self.Initialise()

    def Default(self):
        self.SetProperty(None)

    def GetData(self):
        return [self.GetClientData(i) for i in range(0, self.GetCount())]

    def GetProperty(self):
        return self._property.FromFrame(self.GetSelection())

    def GetSelectionData(self):
        map = self._property.GetClientDataMap()

        try:
            return map[self.GetSelection()]
        except KeyError:
            raise

    def GetText(self):
        return self.GetString(self.GetSelection())

    def Initialise(self):
        for (label, bitmap) in zip(self._property.GetChoices(), self._property.GetChoiceBitmaps()):
            self.Append(label, bitmap, None)

    def SetData(self, client_data):
        for i in range(self.GetCount()):
            self.SetClientData(i, client_data[i])

    def SetProperty(self, property_):
        self.SetSelection(self._property.ToFrame(property_))  # method okay, using undetected overload


class PropertyButtonsInsertCtrl(ButtonsInsertCtrl, PropertyCtrl):
    def __init__(self, parent, property_, btn_bitmaps):
        ButtonsInsertCtrl.__init__(self, parent, btn_bitmaps=btn_bitmaps)
        PropertyCtrl.__init__(self, property_)

        self.custom_textctrl.SetToolTip(self._property.GetToolTip())

    def BindMethod(self, idx, method):
        self.Bind(wx.EVT_BUTTON, method, self._buttons[idx])

    def Default(self):
        self.SetProperty(None)

    def GetProperty(self):
        return self._property.FromFrame(self.GetClientData())

    def SetProperty(self, property_):
        label, bitmap, data = property_
        self.Insert(label, bitmap, data)


class PropertyCheckBox(wx.CheckBox, PropertyCtrl):
    def __init__(self, parent, property_):
        wx.CheckBox.__init__(self, parent, label=property_.GetLabel())
        PropertyCtrl.__init__(self, property_)

        self.SetToolTip(self._property.GetToolTip())

        self._align_row = False

    def Default(self):
        self.SetValue(False)

    def GetProperty(self):
        return self._property.FromFrame(self.IsChecked())

    def SetProperty(self, property_):
        self.SetValue(self._property.ToFrame(property_))


class PropertyChoice(wx.Choice, PropertyCtrl):
    def __init__(self, parent, property_):
        wx.Choice.__init__(self, parent)
        PropertyCtrl.__init__(self, property_)

        self.Initialise()

    def ChangeProperty(self, property_):
        self._property = property_
        self.Clear()
        self.Initialise()

    def Default(self):
        self.SetProperty(None)

    def GetProperty(self):
        return self._property.FromFrame(self.GetSelection())

    def GetData(self):
        return [self.GetClientData(i) for i in range(0, self.GetCount())]

    def Initialise(self):
        for label in self._property.GetChoices():
            self.Append(label)

    def SetProperty(self, property_):
        self.SetSelection(self._property.ToFrame(property_))


class PropertyDatePickerCtrl(wx.adv.DatePickerCtrl, PropertyCtrl):
    def __init__(self, parent, property_):
        wx.adv.DatePickerCtrl.__init__(self, parent, dt=wx.DateTime.Now(), style=wx.adv.DP_DROPDOWN)
        PropertyCtrl.__init__(self, property_)

        self.SetToolTip(self._property.GetToolTip())

    def Default(self):
        self.SetProperty(datetime.now())

    def GetProperty(self):
        return self._property.FromFrame(self.GetValue())

    def SetProperty(self, property_):
        self.SetValue(self._property.ToFrame(property_))


class PropertyColourPickerCtrl(wx.ColourPickerCtrl, PropertyCtrl):
    def __init__(self, parent, property_):
        wx.ColourPickerCtrl.__init__(self, parent)
        PropertyCtrl.__init__(self, property_)

        self.SetToolTip(self._property.GetToolTip())

    def Default(self):
        self.SetProperty(wx.Colour(0, 0, 0))

    def GetProperty(self):
        return self._property.FromFrame(self.GetColour())

    def SetProperty(self, property_):
        self.SetColour(self._property.ToFrame(property_))


class PropertyRadioBox(wx.RadioBox, PropertyCtrl):
    def __init__(self, parent, property_):
        wx.RadioBox.__init__(self, parent, label=property_.GetLabel(), choices=property_.GetChoices())
        PropertyCtrl.__init__(self, property_)

        self._align_row = False

    def Default(self):
        self.SetSelection(0)

    def GetProperty(self):
        return self._property.FromFrame(self.GetSelection())

    def SetProperty(self, property_):
        self.SetSelection(self._property.ToFrame(property_))


class PropertyTextButtonCtrl(TextButtonCtrl, PropertyCtrl):
    def __init__(self, parent, property_, side=ID_RIGHT):
        TextButtonCtrl.__init__(self, parent, bitmap=property_.GetBitmap(), side=side)
        PropertyCtrl.__init__(self, property_)

        self.text_ctrl.SetToolTip(self._property.GetToolTip())

    def Default(self):
        self.SetProperty(None)

    def GetProperty(self):
        return self._property.FromFrame(self.GetValue())

    def SetProperty(self, property_):
        self.SetValue(self._property.ToFrame(property_))


class PropertyTextCtrl(wx.TextCtrl, PropertyCtrl):
    def __init__(self, parent, property_):
        wx.TextCtrl.__init__(self, parent)
        PropertyCtrl.__init__(self, property_)

        tooltip = self._property.GetToolTip()
        if tooltip is not None:
            self.SetToolTip(tooltip)

    def Default(self):
        self.SetProperty(None)

    def GetProperty(self):
        return self._property.FromFrame(self.GetValue())

    def SetProperty(self, property_):
        self.SetValue(self._property.ToFrame(property_))


# ======================================================================================================================
# Generic panel classes and methods
# ======================================================================================================================
class PropertyPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

    def GetRequiredSize(self, texts):
        f = self.GetFont()
        dc = wx.WindowDC(self)
        dc.SetFont(f)

        w_max = 0
        h_max = 0

        for text in tuple(texts):
            if text is None:
                continue

            if not isinstance(text, str):  # text is a type Class Unit
                text = text.Get()

            w, h = dc.GetTextExtent(text)
            w_max = max(w, w_max)
            h_max = max(h, h_max)

        return w_max, h_max

    @staticmethod
    def ErrorCheckInput(ctrl):
        label = ctrl.GetErrorLabel()

        try:

            if isinstance(ctrl, PropertyTextCtrl):

                value = ctrl.GetValue()

                if isinstance(value, str):

                    if value:  # string not empty

                        value = float(value)

                        minimum, maximum = ctrl.GetLimits()

                        if minimum is not None and value < minimum:
                            raise LimitError('{} must be greater than {}.'.format(label, minimum))

                        if maximum is not None and value > maximum:
                            raise LimitError('{} must be less than {}.'.format(label, maximum))

        except ValueError:
            raise ValueError('{} must be a number.'.format(label))


class GridPanel(PropertyPanel):
    def __init__(self, parent, rows, cols):
        super().__init__(parent)

        self._ctrls = []
        self.ctrl_sizer = PropertySizer(rows, cols)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

    def AddCtrl(self, ctrl, label=None, unit=None):
        self._ctrls.append(ctrl)

        if ctrl.AlignRow():
            self.ctrl_sizer.AddCtrl(self, ctrl, label=label, unit=unit)
        else:  # RadioBox and CheckBox
            self.sizer.Add(ctrl, 1, wx.EXPAND | wx.ALL, GAP)

    def BindMethodToCtrls(self, wx_event, method, from_=None, to=None):
        for ctrl in self.GetCtrls(from_, to):
            self.Bind(wx_event, method, ctrl)

    def DefaultCtrls(self, from_=None, to=None):
        for ctrl in self.GetCtrls(from_, to):
            ctrl.Default()

    def EnableCtrls(self, state=True, from_=None, to=None):
        for ctrl in self.GetCtrls(from_, to):
            ctrl.Enable(state)

    def Get(self):
        values = []

        for ctrl in self._ctrls:

            box = None

            try:

                self.ErrorCheckInput(ctrl)
                values.append(ctrl.GetProperty())

            except ValueError as e:

                box = wx.MessageDialog(self, message=str(e), caption='Value Error')

            except LimitError as e:

                box = wx.MessageDialog(self, message=str(e), caption='Limit Error')

            if box is not None:
                box.ShowModal()
                box.Destroy()
                raise ValueError()

        return values

    def GetCtrls(self, from_=None, to=None):
        if from_ is None and to is None:
            ctrls = self._ctrls
        elif to is None:
            ctrls = self._ctrls[from_:]
        elif from_ is None:
            ctrls = self._ctrls[:to]
        else:
            ctrls = self._ctrls[from_:to]

        return ctrls

    def Realize(self, col=1):

        if col >= 0:
            self.ctrl_sizer.AddGrowableCol(col, 1)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def Set(self, *values):
        for ctrl, value in zip(self._ctrls, values):
            ctrl.SetProperty(value)


class DynamicPanel(GridPanel):
    def __init__(self, parent, property_, rows, cols):
        super().__init__(parent, rows+1, cols)

        self.selection = PropertyBitmapComboBox(self, property_)
        self._ctrls.append(self.selection)
        self.ctrl_sizer.AddCtrl(self, self.selection)

        self._labels = []
        self._units = []

        # used for special cases of external control enabling
        self._to = 0

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_COMBOBOX, self.OnComboBox, self.selection)

    # events -----------------------------------------------------------------------------------------------------------
    def OnComboBox(self, event):
        idx = event.GetInt()
        self.UpdateText(idx)

        # clearing every input but the selection
        for ctrl in self._ctrls[1:]:
            ctrl.Default()

    # external functions -----------------------------------------------------------------------------------------------
    def AddCtrl(self, ctrl, label=None, unit=None):
        w, h = self.GetRequiredSize(ctrl.GetFrameLabel())
        self._labels.append(wx.StaticText(self, label='', size=wx.Size(w, h)))

        w, h = self.GetRequiredSize(ctrl.GetUnit())
        self._units.append(wx.StaticText(self, label='', size=wx.Size(w, h)))

        self._ctrls.append(ctrl)
        self.ctrl_sizer.AddCtrl(self, ctrl, label=self._labels[-1], unit=self._units[-1])

    def ChangeProperties(self, *properties):
        for (ctrl, property_) in zip(self._ctrls, properties):
            ctrl.ChangeProperty(property_)

    def Clear(self):
        self.selection.SetSelection(-1)  # method okay, using undetected overload

        for (ctrl, label, unit) in zip(self._ctrls[1:], self._labels, self._units):
            ctrl.Default()
            label.SetLabel('')
            unit.SetLabel('')
            ctrl.Enable(False)

    def EnableAvailableCtrls(self, state):
        self.EnableCtrls(state, from_=0, to=self._to)

    def GetSelection(self):
        return self.selection.GetSelection()

    def UpdateText(self, idx):
        if idx == -1:
            self.Clear()
            return

        self._to = 1

        # self._ctrls[0] is self.selection. Added for input/output, but not dynamic
        for (ctrl, label, unit) in zip(self._ctrls[1:], self._labels, self._units):
            label_str = ctrl.GetFrameLabel(idx)
            unit_str = ctrl.GetUnit(idx)

            if label_str:
                label.SetLabel(ctrl.GetFrameLabel(idx))
            else:
                label.SetLabel('')

            if unit_str:
                unit.SetLabel(ctrl.GetUnit(idx))
            else:
                unit.SetLabel('')

            if label_str or unit_str:
                ctrl.Enable(True)
                self._to += 1

            else:
                ctrl.Enable(False)


class SectionPanel(GridPanel):
    def __init__(self, parent, rows, cols, label, bitmap=None):
        super().__init__(parent, rows, cols)

        self.sizer.Add(SectionSeparator(self, label=label, bitmap=bitmap), 0, wx.EXPAND | (wx.ALL & ~wx.TOP), GAP)
        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | (wx.ALL & ~wx.TOP), GAP)


class DynamicSectionPanel(DynamicPanel):
    def __init__(self, parent, property_, rows, cols, label, bitmap=None):
        super().__init__(parent, property_, rows, cols)

        self.sizer.Add(SectionSeparator(self, label=label, bitmap=bitmap), 0, wx.EXPAND | (wx.ALL & ~wx.TOP), GAP)
        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | (wx.ALL & ~wx.TOP), GAP)


class DerivedPanel(SectionPanel):
    def __init__(self, parent, rows, cols, label, bitmap, derived=False):
        super().__init__(parent, rows, cols, label, bitmap)


class HierarchicalPanel(wx.Panel):
    def __init__(self, parent, panel, *args, label=None, bitmap=None, has_parent=True):
        super().__init__(parent)

        self.use_self = SectionSeparator(self, label=label, bitmap=bitmap, checkbox=has_parent)
        self.ctrls = panel(self, *args)  # GridPanel or DynamicPanel

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.use_self, 0, wx.EXPAND | wx.ALL, GAP)
        self.ctrls.sizer.Add(self.ctrls.ctrl_sizer, 0, wx.EXPAND | (wx.ALL & ~wx.TOP), GAP)
        self.sizer.Add(self.ctrls, 0, wx.EXPAND | wx.ALL, GAP)

        # events -------------------------------------------------------------------------------------------------------
        if has_parent:
            self.Bind(wx.EVT_CHECKBOX, self.OnChecked, self.use_self.checkbox)
            self.use_self.SetValue(True)
            self.OnChecked(self.use_self)

    # events -----------------------------------------------------------------------------------------------------------
    def OnChecked(self, event):
        self.ctrls.EnableCtrls(event.IsChecked())

    # external functions -----------------------------------------------------------------------------------------------
    def AddCtrl(self, ctrl, label=None, unit=None):
        self.ctrls.AddCtrl(ctrl, label=label, unit=unit)

    def EnableCheckBox(self, state):
        self.use_self.EnableCheckBox(state)

    def EnableCtrls(self, state=True, from_=None, to=None):
        self.ctrls.EnableCtrls(state, from_=from_, to=to)

    def EnableAvailableCtrls(self, state):
        self.ctrls.EnableAvailableCtrls(state)

    def Get(self):
        return (self.use_self.IsChecked(), *self.ctrls.Get())

    def IsChecked(self):
        return self.use_self.IsChecked()

    def Realize(self):
        self.ctrls.Realize()
        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def Set(self, use_self, *values):
        self.use_self.SetValue(use_self)
        self.OnChecked(self.use_self)

        self.ctrls.Set(*values)

    def SetUseSelf(self, state):
        self.use_self.SetValue(state)

    def UseSelf(self):
        return self.use_self.IsChecked()


# ======================================================================================================================
# Generic AUI classes and methods
# ======================================================================================================================
class PropertiesAUIPanel(wx.Panel):
    def __init__(self, parent, min_size=(200, 200)):
        super().__init__(parent)

        # preparing aui-manager ----------------------------------------------------------------------------------------
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        self.SetMinSize(size=min_size)

        self.notebook = PropertiesNotebook(self)

    def AddPage(self, parent_panel, *panels, proportions=(), title='', bitmap=wx.NullBitmap):

        sizer = wx.BoxSizer(wx.VERTICAL)

        if not proportions:
            proportions = [0 for _ in panels]

        for panel, proportion in zip(panels[:-1], proportions[:-1]):
            sizer.Add(panel, proportion, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), INTER_GAP)

        sizer.Add(panels[-1], proportions[-1], wx.EXPAND | wx.ALL, INTER_GAP)

        parent_panel.SetSizer(sizer)
        sizer.Fit(parent_panel)

        # TODO: this causes a matplotlib wxAssertionError. which I believe to be a bug in matplotlib
        self.notebook.AddPage(parent_panel, title, bitmap=bitmap)

    def Realize(self):
        self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().Name('panel').CenterPane().PaneBorder(False))
        self._mgr.Update()


class PropertiesNotebook(aui.AuiNotebook):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetAGWWindowStyleFlag(aui.AUI_NB_TOP)
        self.ChangeTabArt()

    def ChangeTabArt(self):
        art = AuiModifiedTabArt()

        # colours ------------------------------------------------------------------------------------------------------
        colour = GREY
        art.SetBaseColour(colour)
        art._border_colour = wx.Colour(150, 150, 150)
        art._border_pen = wx.Pen(wx.Colour(150, 150, 150))

        art._background_top_colour = colour
        art._background_bottom_colour = colour

        art._tab_top_start_colour = colour
        art._tab_top_end_colour = colour
        art._tab_bottom_start_colour = colour
        art._tab_bottom_end_colour = colour

        art._tab_inactive_top_colour = colour
        art._tab_inactive_bottom_colour = colour

        art._tab_text_colour = lambda page: page.text_colour
        art._tab_disabled_text_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)

        self.SetArtProvider(art)


# ======================================================================================================================
# CustomTreeCtrl Panels
# ======================================================================================================================
class SelectionTree(wx.Panel):
    def __init__(self, parent, object_menu_page, expand_collapse=False):
        super().__init__(parent, style=wx.SIMPLE_BORDER)

        self.tree = CustomizedTreeCtrl(self, agw_style=wx.TR_HAS_BUTTONS | wx.TR_MULTIPLE)

        self._mirror_tree = object_menu_page.tree  # object_menu_page tree mirrored for population
        self.tree.SetImageList(self._mirror_tree.GetImageList())

        # workaround to not have ugly greyed out disabled pictures
        self.tree._grayedImageList = self.tree.GetImageList()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.SetMinSize(wx.Size(150, 0))

        # events -------------------------------------------------------------------------------------------------------
        if expand_collapse:
            self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRightClick, self.tree)

    # events -----------------------------------------------------------------------------------------------------------
    def OnRightClick(self, event):
        context_menu = CustomMenu(self)
        context_menu.AppendCollapseItem(self.OnCollapseAll)
        context_menu.AppendExpandItem(self.OnExpandAll)
        context_menu.CustomPopup()

    def OnCollapseAll(self, event):
        self.tree.CollapseAll()

    def OnExpandAll(self, event):
        self.tree.ExpandAll()

    # external methods -------------------------------------------------------------------------------------------------
    def Populate(self, mirror_items, types, entity=None, entity_mgr=None, root_title=None, ct_type=1, progress=False):
        self.tree.Freeze()

        # called in case tree reloaded
        self.tree.DeleteAllItems()

        if root_title is None:
            self.tree.SetAGWWindowStyleFlag(self.tree.GetAGWWindowStyleFlag() | wx.TR_HIDE_ROOT)
            root = self.tree.AddRoot('')
        else:
            root = self.tree.AddRoot(root_title)

        for mirror_item in mirror_items:
            item = self.tree.AppendItem(root, mirror_item.GetText(), data=mirror_item.GetData())
            self.tree.SetItemImage(item, mirror_item.GetImage(), wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(item, mirror_item.GetImage(), wx.TreeItemIcon_Expanded)

            self.AddChildren(item, mirror_item, types, entity=entity, entity_mgr=entity_mgr,
                             ct_type=ct_type, progress=progress)

        self.tree.ExpandAll()

        self.tree.Thaw()

    def AddChildren(self, parent, mirror_parent, types, entity=None, entity_mgr=None, ct_type=1, progress=False):
        """
        Add children to the mirrored item

        Parameters
        ----------
        parent : wx.lib.agw.GenericTreeItem
            Parent item in CustomTreeCtrl to add children to
        mirror_parent : wx.lib.agw.GenericTreeItem
            Parent from object_menu_page being mirror in the tree
        types : tuple
            Tuple of types to test against
        entity : Entity
            Class Entity
        entity_mgr : EntityManager
            Class EntityManager
        ct_type : int
            ct_type from CustomTreeCtrl
        progress : bool
            Whether to progress through the tree and show all items in a hierarchy after the first item with ct_type>0
        """

        child, cookie = self._mirror_tree.GetFirstChild(mirror_parent)

        while child:
            data = child.GetData()

            item = self.tree.AppendItem(parent, child.GetText(), ct_type=1, data=data)
            self.tree.SetItemImage(item, child.GetImage(), wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(item, child.GetImage(), wx.TreeItemIcon_Expanded)

            # if an entity and entity mgr is passed, ensure the entity itself is not populated, and potential child
            # entities which already have a parent of the entity type does not allow checking.
            # if the item is already a child of entity then check it
            disable = False

            if (entity is not None) and (not data.IsFolder()):
                item_entity = entity_mgr.GetEntity(*data.GetPointer())

                if item_entity is entity:
                    disable = True

                if data.GetType() in types:

                    if item_entity.HasParent(entity.GetType()):

                        if entity.IsParentOf(*data.GetPointer()):
                            self.tree.CheckItem2(item, True)

                        else:

                            if not item_entity.AllowMultipleParents(entity.GetType()):
                                disable = True

                    elif entity.HasParent(item_entity.GetType()):

                        if item_entity.IsParentOf(*entity.GetPointer()):

                            disable = True

            # change ct_type and progress
            if data.GetType() in types:

                self.tree.SetItemType(item, ct_type=ct_type)

                if disable:
                    self.tree.EnableItem(item, False, torefresh=True)

                if progress:
                    self.AddChildren(item, child, types, entity=entity, entity_mgr=entity_mgr,
                                     ct_type=ct_type, progress=progress)

            else:
                self.tree.SetItemType(item, ct_type=0)
                self.AddChildren(item, child, types, entity=entity, entity_mgr=entity_mgr,
                                 ct_type=ct_type, progress=progress)

            child, cookie = self._mirror_tree.GetNextChild(mirror_parent, cookie)

    def CheckItemsById(self, ids, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

            if (not isinstance(ids, tuple)) and (not isinstance(ids, list)):
                ids = (ids,)

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()
            if data.GetId() in ids:
                self.tree.CheckItem2(child, True)

            self.CheckItemsById(ids, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def GetPointers(self):
        return [d.GetPointer() for d in self.tree.GetData()]

    def GetItems(self):
        return self.tree.GetItems()

    # returns a list of all items in the tree that are checked (checkbox and radiobutton)
    def GetCheckedItems(self):
        return self.tree.GetCheckedItems()

    def SetImageList(self, il):
        self.tree.SetImageList(il)


class ProcessorFlowTree(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, style=wx.SIMPLE_BORDER)

        self.tree = CustomizedTreeCtrl(self, agw_style=wx.TR_HAS_BUTTONS | wx.TR_MULTIPLE)

        # Create an image list to add icons next to an item ------------------------------------------------------------
        il = wx.ImageList(16, 16)
        il.Add(ico.processor_16x16.GetBitmap())
        il.Add(ico.pipeline_16x16.GetBitmap())

        self.tree.SetImageList(il)

        # workaround to not have ugly greyed out disabled pictures
        self.tree._grayedImageList = self.tree.GetImageList()

        # sizing -------------------------------------------------------------------------------------------------------
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.SetMinSize(wx.Size(150, 0))

    def CheckItemById(self, id_, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            if child.GetData() == id_:
                self.tree.CheckItem2(child, True)

            self.CheckItemById(id_, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    # returns a list of all items in the tree that are checked (checkbox and radiobutton)
    def GetCheckedItems(self):
        return self.tree.GetCheckedItems()

    def Populate(self, entity, entity_mgr):
        # called in case tree reloaded
        self.tree.DeleteAllItems()

        root = self.tree.AddRoot('Primary down-stream node')

        parents = entity_mgr.GetEntities([p for p in entity.GetNetworkParents()])

        for parent in parents:

            image = 0 if entity.IsProcessor() else 1

            item = self.tree.AppendItem(root, parent.GetName(), ct_type=2, data=parent.GetId())
            self.tree.SetItemImage(item, image, wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(item, image, wx.TreeItemIcon_Expanded)

        self.tree.ExpandAll()


# ======================================================================================================================
# Free text input panels (requires overwritten Get & Set not checking for numbers)
# ======================================================================================================================
class NamePanel(GridPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2)

        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | wx.ALL, GAP)
        self.AddCtrl(PropertyTextCtrl(self, vm.Name()))

        self.Realize()

    def Get(self):
        return self._ctrls[0].GetProperty()

    def Set(self, name):
        self._ctrls[0].SetProperty(name)


class EvaluationPanel(GridPanel):
    def __init__(self, parent, property_):
        super().__init__(parent, 1, 2)

        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | wx.ALL, GAP)
        self.arrow = PropertyTextButtonCtrl(self, property_, side=ID_LEFT)
        self.AddCtrl(self.arrow)

        self.Realize()

    def Append(self, expression):
        self.Set(self.Get() + expression)

    def Get(self):
        return self._ctrls[0].GetProperty()

    def Set(self, evaluation):
        self._ctrls[0].SetProperty(evaluation)


class ScalerEvaluationPanel(EvaluationPanel):
    def __init__(self, parent):
        super().__init__(parent, vm.ScalerEvaluation())


class SummaryEvaluationPanel(EvaluationPanel):
    def __init__(self, parent):
        super().__init__(parent, vm.SummaryEvaluation())


# ======================================================================================================================
# Import panels (Either from ObjectMenu or from a ProfileImportFrame)
# ======================================================================================================================
class AnaloguePanel(GridPanel):
    def __init__(self, parent, entity_mgr, tree):
        super().__init__(parent, 1, 2)

        bitmaps = (ico.window_trend_chart_16x16.GetBitmap(),)
        self.analogue = PropertyArrowButtonsInsertCtrl(self, vm.Analogue(), entity_mgr, tree, type_=ID_ANALOGUE, lock=True, btn_bitmaps=bitmaps)
        self.AddCtrl(self.analogue)

        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | wx.ALL, GAP)
        self.Realize()

    def Insert(self, id_):
        self.analogue.SetProperty(id_)


class ScalingEvaluationPanel(HierarchicalPanel):
    def __init__(self, parent, entity_mgr, tree, has_parent=True):
        super().__init__(parent, GridPanel, 1, 2, label='Scaling evaluation', bitmap=ico.scaling_chart_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyArrowButtonsInsertCtrl(self.ctrls, vm.Scaling(), entity_mgr, tree,
                                                    type_=ID_SCALING, hierarchical=True))

        self.Realize()


class HistoryPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2, 'History', ico.history_match_16x16.GetBitmap())

        self.history = PropertyButtonsInsertCtrl(self, vm.History(), btn_bitmaps=(ico.project_open_16x16.GetBitmap(),))
        self.AddCtrl(self.history)

        self.Realize()

        # events -------------------------------------------------------------------------------------------------------
        self.history.BindMethod(0, self.OnBrowseButton)

    def OnBrowseButton(self, event):
        profile = Profile()
        frame = ProfileImportFrame(self, profile)
        frame.ShowModal()

        if frame.IsImported():
            self.Set(profile, frame.GetPath())

    def Get(self):
        data = self.history.GetClientData()
        if data is not None:
            profile, path = data
        else:
            profile, path = None, None

        return profile, path

    def Set(self, profile, path):
        if path is None:
            return

        label = os.path.basename(path)
        bitmap = ico.history_match_16x16.GetBitmap()
        self.history.Insert(label, bitmap, (profile, path))


class HistoryFitPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2, 'History and fitting', ico.history_match_16x16.GetBitmap())

        bitmaps = (ico.project_open_16x16.GetBitmap(), ico.window_fit_chart_16x16.GetBitmap(),)
        self.history = PropertyButtonsInsertCtrl(self, vm.HistoryFit(), btn_bitmaps=bitmaps)
        self.AddCtrl(self.history)

        self.Realize()

        # events -------------------------------------------------------------------------------------------------------
        self.history.BindMethod(0, self.OnBrowseButton)

    def OnBrowseButton(self, event):
        profile = Profile()
        frame = ProfileImportFrame(self, profile)
        frame.ShowModal()

        if frame.IsImported():
            self.Set(profile, frame.GetPath())

    def Get(self):
        data = self.history.GetClientData()
        if data is not None:
            profile, path = data
        else:
            profile, path = None, None

        return profile, path

    def Set(self, profile, path):
        if path is None:
            return

        label = os.path.basename(path)
        bitmap = ico.history_match_16x16.GetBitmap()
        self.history.Insert(label, bitmap, (profile, path))


class CulturalPanel(SectionPanel):
    def __init__(self, parent, bitmap):
        super().__init__(parent, 1, 2, 'Cultural', bitmap)

        self.cultural = PropertyButtonsInsertCtrl(self, vm.Cultural(), btn_bitmaps=(ico.project_open_16x16.GetBitmap(),))
        self.AddCtrl(self.cultural)

        self.Realize()

    def Get(self):
        data = self.cultural.GetClientData()
        if data is not None:
            cultural, path = data
        else:
            cultural, path = None, None

        return cultural, path

    def Set(self, cultural, path):
        if path is None:
            return

        label = os.path.basename(path)
        bitmap = ico.polygon_16x16.GetBitmap()
        self.cultural.Insert(label, bitmap, (cultural, path))


class CulturalTrajectoryPanel(CulturalPanel):
    def __init__(self, parent):
        super().__init__(parent, ico.polygon_16x16.GetBitmap())

        # events -------------------------------------------------------------------------------------------------------
        self.cultural.BindMethod(0, self.OnBrowseButton)

    def OnBrowseButton(self, event):
        filepath = GetFilePath(self)
        if filepath is None:
            return

        cultural = WellTrajectory()
        cultural.ReadDEV(filepath)
        self.Set(cultural, filepath)


class CulturalOutlinePanel(CulturalPanel):
    def __init__(self, parent):
        super().__init__(parent, ico.polygon_16x16.GetBitmap())

        # events -------------------------------------------------------------------------------------------------------
        self.cultural.BindMethod(0, self.OnBrowseButton)

    def OnBrowseButton(self, event):
        filepath = GetFilePath(self)
        if filepath is None:
            return

        cultural = Outline()
        cultural.ReadASCII(filepath)
        self.Set(cultural, filepath)


class CulturalPointPanel(CulturalPanel):
    def __init__(self, parent):
        super().__init__(parent, ico.polygon_16x16.GetBitmap())

        # events -------------------------------------------------------------------------------------------------------
        self.cultural.BindMethod(0, self.OnBrowseButton)

    def OnBrowseButton(self, event):
        pass
        # filepath = GetFilePath(self)
        # if filepath is None:
        #     return
        #
        # cultural = Outline()
        # cultural.ReadASCII(filepath)
        # self.Set(cultural, filepath)


class PredictionPanel(HierarchicalPanel):
    def __init__(self, parent, entity_mgr, tree, disable_dca=True, has_parent=True):
        super().__init__(parent, GridPanel, 3, 3, label='Prediction', bitmap=ico.analogue_16x16.GetBitmap(), has_parent=has_parent)

        # used for access to tree
        self._entity_mgr = entity_mgr
        self._tree = tree  # object_menu.<page>.tree for access to selection when clicking on ArrowInsertControl
        self._prediction = None

        bitmaps = (ico.project_open_16x16.GetBitmap(), ico.window_trend_chart_16x16.GetBitmap())

        self.prediction = PropertyBitmapComboBox(self.ctrls, vm.Prediction())
        self.typecurve = PropertyArrowButtonsInsertCtrl(self.ctrls, vm.Typecurve(), entity_mgr, tree, type_=ID_TYPECURVE, btn_bitmaps=bitmaps)
        self.occurrence = PropertyTextCtrl(self.ctrls, vm.ProbabilityOfOccurrence())

        self.ctrls.AddCtrl(self.prediction)
        self.ctrls.AddCtrl(self.typecurve)
        self.ctrls.AddCtrl(self.occurrence)

        if disable_dca:
            self.typecurve.DisableButton(1)

        self.Realize()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_COMBOBOX, self.OnComboBox, self.prediction)
        self.typecurve.BindMethod(0, self.OnBrowseButton)

    # events -----------------------------------------------------------------------------------------------------------
    def OnComboBox(self, event):
        self.SaveState()

        i = event.GetInt()
        self._prediction = self.prediction.GetClientData(i)

        self.LoadState()

    def OnBrowseButton(self, event):
        profile = Profile()
        frame = ProfileImportFrame(self, profile)
        frame.ShowModal()

        if frame.IsImported():
            self.InsertImport(profile, frame.GetPath())

    # external functions -----------------------------------------------------------------------------------------------
    def Get(self):
        self.SaveState()
        return (self.use_self.IsChecked(),  *self.prediction.GetData())

    def GetFunctions(self):
        return self._prediction.GetFunctions()

    def GetPrediction(self):
        pointer = None
        functions = self._prediction.GetFunctions()
        profile = None
        label = None

        typecurve = self.typecurve.GetClientData()

        if typecurve is not None:
            type_ = self._prediction.GetType()

            # work-around for loading typecurves that have been insert via arrow
            if isinstance(typecurve, tuple) and isinstance(typecurve[0], int):
                type_ = ID_PREDICTION_TYPECURVE

            # gather client data
            if type_ == ID_PREDICTION_TYPECURVE:
                pointer = typecurve

            elif type_ == type_ == ID_PREDICTION_FUNCTION:
                label = typecurve

            else:
                profile, label = typecurve
        else:
            type_ = None

        occurrence = self.occurrence.GetProperty()

        return type_, pointer, functions, profile, label, occurrence

    def LoadState(self):
        self.SetPrediction(*self._prediction.Get())

    def SaveState(self):
        self._prediction.Set(*self.GetPrediction())

    def Set(self, use_self, *values):
        for i, value in enumerate(values):
            self.prediction.SetClientData(i, value.Copy())

        self.use_self.SetValue(use_self)
        self.OnChecked(self.use_self)

        # initialize as Mid
        self.prediction.SetProperty(1)
        self._prediction = self.prediction.GetClientData(1)

        self.LoadState()

    def SetFunctions(self, functions):
        self._prediction.SetFunctions(functions)
        self.InsertFunctions()

    def SetPrediction(self, *values):
        type_, pointer, functions, profile, path, occurrence = values

        if type_ is not None:
            if type_ == ID_PREDICTION_TYPECURVE:
                self.InsertTypecurve(pointer)

            elif type_ == ID_PREDICTION_FUNCTION:
                self.InsertFunctions()

            else:
                self.InsertImport(profile, path)
        else:
            self.typecurve.Clear()

        self.occurrence.SetProperty(occurrence)

    def InsertFunctions(self):
        label = 'DCA ({})'.format(self.prediction.GetText())
        bitmap = ico.hyperbolic_dca_16x16.GetBitmap()
        self.typecurve.Insert(label, bitmap, ID_PREDICTION_FUNCTION)
        self._prediction.SetType(ID_PREDICTION_FUNCTION)

    def InsertImport(self, profile, path):
        if path is None:
            return

        label = os.path.basename(path)
        bitmap = ico.history_chart_16x16.GetBitmap()
        self.typecurve.Insert(label, bitmap, (profile, path))
        self._prediction.SetType(ID_PREDICTION_IMPORT)

    def InsertTypecurve(self, pointer):
        if pointer is not None:

            try:
                entity = self._entity_mgr.GetEntity(*pointer)
            except KeyError:
                return

            self.typecurve.Insert(entity.GetName(), entity.GetBitmap(), entity.GetPointer())
            self._prediction.SetType(ID_PREDICTION_TYPECURVE)


class ScenarioPanel(GridPanel):
    def __init__(self, parent, entity_mgr, tree):
        super().__init__(parent, 1, 2)

        self.AddCtrl(PropertyArrowButtonsInsertCtrl(self, vm.Scenario(), entity_mgr, tree, type_=ID_SCENARIO, lock=True))
        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | wx.ALL, GAP)

        self.Realize()

    def Insert(self, id_):
        self._ctrls[0].SetProperty(id_)


class HistorySimulationPanel(GridPanel):
    def __init__(self, parent, entity_mgr, tree):
        super().__init__(parent, 1, 2)

        self.AddCtrl(PropertyArrowButtonsInsertCtrl(self, vm.HistorySimulation(), entity_mgr, tree, type_=ID_HISTORY))
        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | wx.ALL, GAP)

        self.Realize()


# ======================================================================================================================
# Input panels in alphabetical order
# ======================================================================================================================
class AvailabilityPanel(HierarchicalPanel):
    def __init__(self, parent, has_parent=True):
        super().__init__(parent, GridPanel, 1, 3, label='Availability', bitmap=ico.uptime_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.Availability()))

        self.Realize()


class ConstrainedModelPanel(SectionPanel):
    def __init__(self, parent, has_parent=True):
        super().__init__(parent, 2, 3, 'Modelling', bitmap=ico.flow_constraint_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.Availability()))
        self.AddCtrl(PropertyCheckBox(self, vm.SimulateConstrainted()))

        self.Realize()


class FlowConstraintPanel(SectionPanel):
    def __init__(self, parent, unit_system):
        super().__init__(parent, 4, 3, 'Flow constraints', ico.flow_constraint_16x16.GetBitmap())

        self.oil = PropertyTextCtrl(self, vm.OilConstraint(unit_system))
        self.gas = PropertyTextCtrl(self, vm.GasConstraint(unit_system))
        self.water = PropertyTextCtrl(self, vm.WaterConstraint(unit_system))
        self.liquid = PropertyTextCtrl(self, vm.LiquidConstraint(unit_system))

        self.AddCtrl(self.oil)
        self.AddCtrl(self.gas)
        self.AddCtrl(self.water)
        self.AddCtrl(self.liquid)

        self.Realize()


class FlowSplitPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 6, 3, 'Flow split', ico.flow_constraint_16x16.GetBitmap())

        self.AddCtrl(PropertyBitmapComboBox(self, vm.SplitType()))
        self.AddCtrl(PropertyTextCtrl(self, vm.OilSplit()))
        self.AddCtrl(PropertyTextCtrl(self, vm.GasSplit()))
        self.AddCtrl(PropertyTextCtrl(self, vm.WaterSplit()))
        self.AddCtrl(PropertyTextCtrl(self, vm.InjectionGasSplit()))
        self.AddCtrl(PropertyTextCtrl(self, vm.InjectionWaterSplit()))

        self.Realize()


class LiftGasConstraintPanel(SectionPanel):
    def __init__(self, parent, unit_system):
        super().__init__(parent, 1, 3, 'Lift gas constraint', ico.lift_gas_constraint_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.LiftGasConstraint(unit_system)))

        self.Realize()


class GasLiftPanel(HierarchicalPanel):
    def __init__(self, parent, unit_system, has_parent=True):
        super().__init__(parent, GridPanel, 1, 3, label='Gas-lift', bitmap=ico.lift_gas_rate_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.TargetGasLiquidRatio(unit_system)))

        self.Realize()


class InflowingPhasePanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 5, 1, 'In-flowing phases', ico.fluids_16x16.GetBitmap())

        self.AddCtrl(PropertyCheckBox(self, vm.OilInflow()))
        self.AddCtrl(PropertyCheckBox(self, vm.GasInflow()))
        self.AddCtrl(PropertyCheckBox(self, vm.WaterInflow()))
        self.AddCtrl(PropertyCheckBox(self, vm.InjectionGasInflow()))
        self.AddCtrl(PropertyCheckBox(self, vm.InjectionWaterInflow()))

        self.Realize(col=-1)


class InjectionConstraintPanel(SectionPanel):
    def __init__(self, parent, unit_system):
        super().__init__(parent, 2, 3, 'Injection constraints', ico.injection_constraint_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.InjectionGasConstraint(unit_system)))
        self.AddCtrl(PropertyTextCtrl(self, vm.InjectionWaterConstraint(unit_system)))

        self.Realize()


class InjectionFluidPanel(HierarchicalPanel):
    def __init__(self, parent, unit_system, has_parent=True):
        super().__init__(parent, GridPanel, 2, 3, label='Injection fluids', bitmap=ico.fluids_injection_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.InjectionGasFVF(unit_system)))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.InjectionWaterFVF(unit_system)))

        self.Realize()


class InjectionPhasePanel(GridPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2)

        self.radio = PropertyRadioBox(self, vm.InjectionPhase())  # used for access in events
        self.AddCtrl(self.radio)

        self.Realize()

    def GetSelection(self):
        return self._ctrls[0].GetSelection()


class InjectionPotentialPanel(HierarchicalPanel):
    def __init__(self, parent, unit_system, has_parent=True):
        super().__init__(parent, GridPanel, 2, 3, label='Injection potentials', bitmap=ico.wag_injection_rate_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.GasInjectionPotentialConstant(unit_system)))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.WaterInjectionPotentialConstant(unit_system)))

        self.Realize()


class LicensePanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2, 'License', ico.event_16x16.GetBitmap())

        self.AddCtrl(PropertyDatePickerCtrl(self, vm.License()))

        self.Realize()


class ProductionPhasePanel(GridPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2)

        self.AddCtrl(PropertyRadioBox(self, vm.ProductionPhase()))

        self.Realize()

    def GetSelection(self):
        return self._ctrls[0].GetSelection()


class ReservoirFluidPanel(HierarchicalPanel):
    def __init__(self, parent, unit_system, has_parent=True):
        super().__init__(parent, GridPanel, 4, 3, label='Reservoir fluids', bitmap=ico.fluids_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.OilFVF(unit_system)))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.GasFVF(unit_system)))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.WaterFVF(unit_system)))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.SolutionGasOilRatio(unit_system)))

        self.Realize()


class RiskingPanel(DerivedPanel):
    def __init__(self, parent, derived=False):
        super().__init__(parent, 2, 3, 'Risking', ico.risking_16x16.GetBitmap(), derived=derived)

        self.AddCtrl(PropertyTextCtrl(self, vm.Maturity()))
        self.AddCtrl(PropertyTextCtrl(self, vm.ProbabilityOfSuccess()))

        self.Realize()
        self.EnableCtrls(not derived)


class VolumePanel(DerivedPanel):
    def __init__(self, parent, unit_system, derived=False):
        super().__init__(parent, 2, 3, 'Volumes', ico.stoiip_16x16.GetBitmap(), derived=derived)

        self.AddCtrl(PropertyTextCtrl(self, vm.STOIIP(unit_system)))

        self.Realize()
        self.EnableCtrls(not derived)


class WagPanel(HierarchicalPanel):
    def __init__(self, parent, has_parent=True):
        super().__init__(parent, GridPanel, 2, 3, label='WAG', bitmap=ico.injector_wag_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.WAGCycleDuration()))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.WAGCycles()))

        self.Realize()


class WellSpacingPanel(HierarchicalPanel):
    def __init__(self, parent, unit_system, has_parent=True):
        super().__init__(parent, GridPanel, 2, 3, label='Well spacing', bitmap=ico.well_spacing_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyBitmapComboBox(self.ctrls, vm.DevelopmentLayout()))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.WellSpacing(unit_system)))

        self.Realize()


# ======================================================================================================================
# Panels with buttons
# ======================================================================================================================
class VoidagePanel(SectionPanel):
    def __init__(self, parent, unit_system):
        super().__init__(parent, 1, 2, 'Voidage replacement', ico.wag_voidage_replacement_16x16.GetBitmap())

        self._proportions = {}

        self.ratio = PropertyTextButtonCtrl(self, vm.VoidageProportion(unit_system))
        self.AddCtrl(self.ratio)

        self.Realize()

    def GetProportions(self):
        return self._proportions

    def Get(self):
        try:
            self.ErrorCheckInput(self.ratio)
        except ValueError:
            raise

        return self.ratio.GetProperty(), self._proportions

    def Set(self, ratio, proportions):
        self.ratio.SetProperty(ratio)
        self._proportions = proportions


# ======================================================================================================================
# Uncertainty panels
# ======================================================================================================================
class UncertainParameter:
    """
    Used as client data to the BitmapComboBox in UncertainParameterPanel to keep track of input
    """
    def __init__(self):
        self._value = None
        self._distribution = None
        self._parameters = [None, None, None]

    def Set(self, value, distribution, parameters):
        self._value = value
        self._distribution = distribution
        self._parameters = parameters

    def GetValue(self):
        return self._value

    def SetValue(self, value):
        self._value = value

    def GetUncertainty(self):
        return (self._distribution, *self._parameters)

    def SetUncertainty(self, distribution, parameters):
        self._distribution = distribution
        self._parameters = parameters


class UncertaintyPanel(HierarchicalPanel):
    def __init__(self, parent, has_parent=True):
        super().__init__(parent, DynamicPanel, vm.Distribution(), 3, 3, label='Uncertainty',
                         bitmap=ico.uncertainty_16x16.GetBitmap(), has_parent=has_parent)

        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.DistributionParameter1()))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.DistributionParameter2()))
        self.AddCtrl(PropertyTextCtrl(self.ctrls, vm.DistributionParameter3()))


class UncertainParameterPanel(wx.Panel):
    def __init__(self, parent, has_parent=True):
        super().__init__(parent)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self._properties = None
        self._current_idx = None

        self.selection = wx.adv.BitmapComboBox(self, style=wx.CB_READONLY)
        self.value = HierarchicalPanel(self, GridPanel, 1, 3, label='Value', has_parent=has_parent)
        self.uncer = UncertaintyPanel(self, has_parent=has_parent)

        # used to control unit of value TextCtrl
        self.unit = None

        # sizing -------------------------------------------------------------------------------------------------------
        selection_sizer = AlignedFlexSizer([wx.StaticText(self, label='Parameter:')], [self.selection])
        self.sizer.Add(selection_sizer, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        self.sizer.Add(self.value, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)
        self.sizer.Add(self.uncer, 0, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), GAP)

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_COMBOBOX, self.OnComboBox, self.selection)

    # events -----------------------------------------------------------------------------------------------------------
    def OnComboBox(self, event):
        self.SaveState()

        idx = event.GetInt()

        # update the fancytext unit
        unit = self._properties.GetUnit(idx)
        if unit is not None:
            unit, _ = Latex2HTML(unit)
            self.unit.SetBitmap(wx.NullBitmap)  # avoid duplication of bitmap

            if unit:  # avoid little black dot if unit is an empty string (unitless variables)
                self.unit.SetBitmap(fancy.RenderToBitmap(unit))

        self.LoadState(idx)

        self.uncer.ctrls.UpdateText(self.uncer.ctrls.GetSelection())

        self._current_idx = idx

        # enable/disable value
        self.value.EnableCtrls(self.value.UseSelf())

        # disable all uncertainties after having loaded, in-case it is unchecked hierarchically
        self.uncer.EnableCtrls(False)

        # enable based on existing selections
        if self.uncer.UseSelf():
            if self.uncer.ctrls.GetSelection() > -1:
                self.uncer.EnableAvailableCtrls(True)
            else:
                self.uncer.EnableCtrls(True, to=1)

    # external functions -----------------------------------------------------------------------------------------------
    def EnableCtrls(self, state):
        # remainder of ctrls are disabled by default if self.selection cannot be accessed.
        self.selection.Enable(state)

    def GetUncertainties(self):
        self.SaveState()

        uncertainties = []
        for i, _ in enumerate(self._properties.GetVariables()):
            data = self.selection.GetClientData(i)
            uncertainties.append(data.GetUncertainty())

        return (self.uncer.IsChecked(), *uncertainties)

    def GetValues(self):
        self.SaveState()

        values = []
        for i, _ in enumerate(self._properties.GetVariables()):
            data = self.selection.GetClientData(i)
            values.append(data.GetValue())

        return (self.value.IsChecked(), *values)

    def Initialise(self, collection):
        for property_ in collection.GetVariables():
            label = property_.GetComboLabel()
            bitmap = property_.GetBitmap()

            self.selection.Append(label, bitmap, UncertainParameter())

        w, h = self.value.ctrls.GetRequiredSize(collection.GetUnit())
        self.unit = fancy.StaticFancyText(self.value.ctrls, wx.ID_ANY, ' ', size=wx.Size(w, h))
        self.value.AddCtrl(PropertyTextCtrl(self.value.ctrls, vm.UncertainValue()), unit=self.unit)
        self._properties = collection

    def LoadState(self, idx):
        data = self.selection.GetClientData(idx)

        # load values
        self.value.Set(self.value.UseSelf(), data.GetValue())

        # load uncertainty
        self.uncer.Set(self.uncer.UseSelf(), *data.GetUncertainty())

    def Realize(self):
        self.value.Realize()
        self.uncer.Realize()
        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def SaveState(self):
        idx = self._current_idx
        if idx is None:
            return

        data = self.selection.GetClientData(idx)

        # save values and uncertainty
        try:
            _, value = self.value.Get()
            uncer = self.uncer.Get()
        except ValueError:
            return

        data.SetValue(value)
        data.SetUncertainty(uncer[1], uncer[2:])  # 0 is use_self

    def SetUncertainties(self, use_self, *uncertainties):
        for i, uncer in enumerate(uncertainties):
            data = self.selection.GetClientData(i)
            data.SetUncertainty(*uncer)

        self.uncer.Set(use_self)
        self.uncer.EnableCtrls(False)

    def SetValues(self, use_self, *values):
        for i, value in enumerate(values):
            data = self.selection.GetClientData(i)
            data.SetValue(value)

        self.value.Set(use_self)
        self.value.EnableCtrls(False)


class ScalingPanel(UncertainParameterPanel):
    def __init__(self, parent, has_parent=True):
        super().__init__(parent, has_parent=has_parent)

        properties = vm.VariableCollection(vm.CumulativeScaler(),
                                           vm.RateScaler(),
                                           vm.FFWScaler(),
                                           vm.FFGScaler(),
                                           vm.OnsetScaler(),
                                           vm.InitialWCTScaler())

        self.Initialise(properties)
        self.Realize()


class StaticPanel(UncertainParameterPanel):
    def __init__(self, parent, unit_system, has_parent=True):
        super().__init__(parent, has_parent=has_parent)

        properties = vm.VariableCollection(vm.CompletedLength(unit_system),
                                           vm.HydrocarbonFeet(unit_system),
                                           vm.HydrocarbonPoreVolume(unit_system),
                                           vm.Permeability(unit_system),
                                           vm.OilDensity(unit_system))

        self.Initialise(properties)
        self.Realize()


# ======================================================================================================================
# Properties panel (generic for the most common entity frames)
# ======================================================================================================================
class PropertiesPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundColour(wx.WHITE)

        self.name = NamePanel(self)

        # sizing input -------------------------------------------------------------------------------------------------
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.name, 0, wx.EXPAND)
        self.SetSizer(self.sizer)

    def SaveName(self, entity):
        entity.SetName(self.name.Get())

    def Load(self, name):
        self.name.Set(name)


# ======================================================================================================================
# Analogue panels
# ======================================================================================================================
class ModelPanel(DynamicSectionPanel):
    def __init__(self, parent):
        super().__init__(parent, vm.PlaceholderMethod(), 4, 2, label='Model')

        self.AddCtrl(PropertyTextCtrl(self, vm.PlaceholderInput()))
        self.AddCtrl(PropertyTextCtrl(self, vm.PlaceholderParameter1()))
        self.AddCtrl(PropertyTextCtrl(self, vm.PlaceholderParameter2()))
        self.AddCtrl(PropertyTextCtrl(self, vm.PlaceholderParameter3()))

        self.Realize()


# ======================================================================================================================
# Typecurve panels
# ======================================================================================================================
class IncludeModelPanel(GridPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2)

        self.check = PropertyCheckBox(self, vm.IncludeModel())  # used for access in events
        self.AddCtrl(self.check)

        self.Realize()


class MergePanel(DynamicSectionPanel):
    def __init__(self, parent):
        super().__init__(parent, vm.MergeType(), 2, 2, label='Merge', bitmap=ico.merge_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.MergePoint()))
        self.AddCtrl(PropertyTextCtrl(self, vm.MergeRate()))

        self.Realize()


class ModifierPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 2, 2, 'Modify', ico.modify_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.Multiplier()))
        self.AddCtrl(PropertyTextCtrl(self, vm.Addition()))

        self.Realize()


class RunPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 8, label='Run', bitmap=ico.run_16x16.GetBitmap())

        self.point = PropertyBitmapComboBox(self, vm.RunFrom())
        self.axis = PropertyBitmapComboBox(self, vm.RunFromSpecific())
        self.value = PropertyTextCtrl(self, vm.RunFromValue())
        self.run_to = PropertyTextButtonCtrl(self, vm.RunTo())

        self.AddCtrl(self.point)
        self.AddCtrl(self.axis)
        self.AddCtrl(self.value)
        self.AddCtrl(self.run_to)

        self.Realize(col=7)


# ======================================================================================================================
# Scenario panels
# ======================================================================================================================
class DurationPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 2, 2, 'Duration', ico.duration_16x16.GetBitmap())

        self.AddCtrl(PropertyDatePickerCtrl(self, vm.StartDate()))
        self.AddCtrl(PropertyDatePickerCtrl(self, vm.EndDate()))

        self.Realize()


class EventPanel(DynamicSectionPanel):
    def __init__(self, parent):
        super().__init__(parent, vm.EventTrigger(), 2, 3, label='Event', bitmap=ico.event_16x16.GetBitmap())

        self.AddCtrl(PropertyDatePickerCtrl(self, vm.EventDate()))
        self.AddCtrl(PropertyTextCtrl(self, vm.OffsetYears()))

        self.Realize()


# ======================================================================================================================
# Simulation panels
# ======================================================================================================================
class PlateauPanel(SectionPanel):
    def __init__(self, parent, unit_system):
        super().__init__(parent, 2, 3, 'Plateaus', ico.plateau_chart_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.TargetOilPlateau(unit_system)))
        self.AddCtrl(PropertyTextCtrl(self, vm.TargetGasPlateau(unit_system)))

        self.Realize()


class TimelinePanel(DynamicSectionPanel):
    def __init__(self, parent):
        super().__init__(parent, vm.Frequency(), 2, 3, 'Timeline', ico.event_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.TimeDelta()))

        self.Realize()


class SamplingPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 2, 2, 'Sampling', ico.swanson_distribution_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.Samples()))
        self.AddCtrl(PropertyCheckBox(self, vm.SaveAllSamples()))

        self.Realize()


# ======================================================================================================================
# Scaling Panels
# ======================================================================================================================
class ScalerSelectionPanel(GridPanel):
    # designed to be sub-classed
    def __init__(self, parent):
        super().__init__(parent, 1, 2)

        self.selection = PropertyBitmapComboBox(self, vm.ScalerSelection())
        self.AddCtrl(self.selection)
        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | wx.ALL, GAP)

        self.Realize()


# ======================================================================================================================
# Re-sample Panels
# ======================================================================================================================
class ResamplePanel(HierarchicalPanel):
    def __init__(self, parent):
        super().__init__(parent, GridPanel, 4, 3, label='Re-sample', bitmap=ico.dates_16x16.GetBitmap())

        self.AddCtrl(PropertyDatePickerCtrl(self.ctrls, vm.StartDate()))
        self.AddCtrl(PropertyDatePickerCtrl(self.ctrls, vm.EndDate()))

        self.frequency = PropertyBitmapComboBox(self.ctrls, vm.Frequency())
        self.timestep = PropertyTextCtrl(self.ctrls, vm.TimeStep())
        self.AddCtrl(self.frequency)
        self.AddCtrl(self.timestep)

        self.ctrls.Enable(False)
        self.timestep.Enable(False)
        self.SetUseSelf(False)

        self.Realize()

        self.Bind(wx.EVT_COMBOBOX, self.OnComboBox, self.frequency)

    def OnChecked(self, event):
        """
        Overwritten usage of HierarchicalPanel. Workaround to enable ctrls without enabling self.timestep
        :param event: wx.EVT class
        :return:
        """
        self.ctrls.Enable(event.IsChecked())

    def OnComboBox(self, event):
        id_ = event.GetInt()

        if id_ == 3:
            self.timestep.Enable(True)
        else:
            self.timestep.Clear()
            self.timestep.Enable(False)


# ======================================================================================================================
# Variable Panels
# ======================================================================================================================
class LineOptionsPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 3, 2, 'Line Options', ico.event_16x16.GetBitmap())

        self.AddCtrl(PropertyBitmapComboBox(self, vm.VariableLinestyle()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.VariableDrawstyle()))
        self.AddCtrl(PropertyColourPickerCtrl(self, vm.VariableColour()))

        self.Realize()


class SummaryIconPanel(GridPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2)

        self.sizer.Add(self.ctrl_sizer, 1, wx.EXPAND | wx.ALL, GAP)
        self.selection = PropertyBitmapComboBox(self, vm.SummaryIcon())
        self.AddCtrl(self.selection)

        self.Realize()


class SummaryConversionPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 4, 3, 'Conversion', bitmap=ico.specific_point_16x16.GetBitmap())

        self.function = PropertyBitmapComboBox(self, vm.SummaryFunction())
        self.point = PropertyBitmapComboBox(self, vm.SummaryPoint())

        self.AddCtrl(self.function)
        self.AddCtrl(self.point)
        self.AddCtrl(PropertyDatePickerCtrl(self, vm.SummaryPointDate()))
        self.AddCtrl(PropertyTextCtrl(self, vm.SummaryPointTime()))

        self.EnableCtrls(False, from_=1)

        self.Realize()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_COMBOBOX, self.OnFunctionComboBox, self.function)
        self.Bind(wx.EVT_COMBOBOX, self.OnPointComboBox, self.point)

    # events -----------------------------------------------------------------------------------------------------------
    def OnFunctionComboBox(self, event, idx=None):
        if idx is None:
            if event is None:
                return

            idx = event.GetInt()

        if idx == 0:
            self.EnableCtrls(True, from_=1, to=2)

            point = self.point.GetSelection()
            if point != -1:
                self.OnPointComboBox(None, point)

        else:
            self.EnableCtrls(False, from_=1)

    def OnPointComboBox(self, event, idx=None):
        if idx is None:
            if event is None:
                return

            idx = event.GetInt()

        self.EnableCtrls(False, from_=2)

        if idx == 2:  # date
            self.EnableCtrls(True, from_=2, to=3)

        elif idx == 3:  # time
            self.EnableCtrls(True, from_=3)


# ======================================================================================================================
# Settings Panels
# ======================================================================================================================
class NormalSizeOptionsPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 5, 2, 'Normal mode', ico.window_16x16.GetBitmap())

        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsLinewidth()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsMarkerSize()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsTickLabelSize()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsLabelSize()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsLegendSize()))

        self.Realize()


class PresentSizeOptionsPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 5, 2, 'Presentation mode', ico.window_16x16.GetBitmap())

        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsLinewidth()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsMarkerSize()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsTickLabelSize()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsLabelSize()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsLegendSize()))

        self.Realize()


class UnitSystemPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 1, 2, 'Unit system', ico.settings_16x16.GetBitmap())

        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsUnitSystem()))
        self.EnableCtrls(False)

        self.Realize()


class EnsembleCasePanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 3, 2, 'Cases', ico.profiles_chart_16x16.GetBitmap())

        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsLowCase()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsMidCase()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsHighCase()))

        self.Realize()


class EnsembleShadingPanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 3, 2, 'Shading', ico.prediction_16x16.GetBitmap())

        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsShadingResolution()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsShadingLow()))
        self.AddCtrl(PropertyBitmapComboBox(self, vm.SettingsShadingHigh()))

        self.Realize()


# ======================================================================================================================
# Duplicate Panels
# ======================================================================================================================
class DuplicatePanel(SectionPanel):
    def __init__(self, parent):
        super().__init__(parent, 2, 2, 'Duplicate', ico.swanson_distribution_16x16.GetBitmap())

        self.AddCtrl(PropertyTextCtrl(self, vm.Duplicates()))
        self.AddCtrl(PropertyCheckBox(self, vm.DuplicateAsControlled()))

        self.Realize()
