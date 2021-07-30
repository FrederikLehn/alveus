import copy
from datetime import datetime
import wx.adv
from wx.lib.agw.customtreectrl import EVT_TREE_ITEM_CHECKED

from properties import EventList
from widgets.customized_tree_ctrl import CustomizedTreeCtrl
from frames.frame_design import ObjectFrame, GAP
from frames.entity_frames import EntitySelectionFrame
from entity_mgr import Scenario
from frames.property_panels import DurationPanel, EventPanel

from _ids import *
import _icons as ico


class Event:
    def __init__(self):
        self._name = None
        self._type = None
        self._trigger = None
        self._date = datetime.now()
        self._offset = None

    def Get(self):
        return self._trigger, self._date, self._offset

    def GetName(self):
        return self._name

    def GetType(self):
        return self._type

    def Set(self, trigger, date, offset):
        self._trigger = trigger
        self._date = date
        self._offset = offset


class OnStreamEvent(Event):
    def __init__(self):
        super().__init__()
        self._name = 'On-stream'
        self._type = 'on_stream'


class DecommissionEvent(Event):
    def __init__(self):
        super().__init__()
        self._name = 'Decommission'
        self._type = 'decommission'


class ShutInEvent(Event):
    def __init__(self):
        super().__init__()
        self._name = 'Shut-in'
        self._type = 'shut_in'


class ReOpenEvent(Event):
    def __init__(self):
        super().__init__()
        self._name = 'Re-open'
        self._type = 're_open'


class EventSelectionPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, style=wx.SIMPLE_BORDER)
        self.tree = CustomizedTreeCtrl(self)
        self.tree.AddRoot('')

        # Create an image list to add icons next to an item
        il = wx.ImageList(16, 16)
        self._images = {'on_stream':    il.Add(ico.on_stream_16x16.GetBitmap()),
                        'shut_in':      il.Add(ico.shut_in_16x16.GetBitmap()),
                        're_open':      il.Add(ico.shut_in_16x16.GetBitmap()),
                        'decommission': il.Add(ico.decommission_16x16.GetBitmap())}

        self.event_icons = il.Add(ico.event_16x16.GetBitmap())

        self.tree.SetImageList(il)
        self.tree._grayedImageList = self.tree.GetImageList()

        self.events = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.SetMinSize(wx.Size(100, 220))

    # external functions -----------------------------------------------------------------------------------------------
    # returns a list of all items in the tree that are checked (checkbox and radiobutton)
    def GetCheckedItems(self):
        return self.tree.GetCheckedItems()

    def GetCount(self):
        return self.tree.GetChildrenCount(self.events)

    def AddEvent(self, event, entity_event):
        idx = self.GetCount() - 1
        child = self.tree.InsertItemByIndex(self.events, idx, entity_event.GetName(), ct_type=2, data=entity_event)
        self.tree.SetItemImage(child, self._images[entity_event.GetType()], wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(child, self._images[entity_event.GetType()], wx.TreeItemIcon_Expanded)

        self.tree.ExpandAll()

    def Populate(self):
        root = self.tree.GetRootItem()

        self.events = self.tree.AppendItem(root, 'Events', data=None)
        self.tree.SetItemImage(self.events, self.event_icons, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.events, self.event_icons, wx.TreeItemIcon_Expanded)

        self.tree.ExpandAll()

    def Default(self):
        # default with an on-stream and decommission event
        os_event = OnStreamEvent()
        on_stream = self.tree.AppendItem(self.events, os_event.GetName(), ct_type=2, data=os_event)
        self.tree.SetItemImage(on_stream, self._images[os_event.GetType()], wx.TreeItemIcon_Normal)

        dc_event = DecommissionEvent()
        decommission = self.tree.AppendItem(self.events, dc_event.GetName(), ct_type=2, data=dc_event)
        self.tree.SetItemImage(decommission, self._images[dc_event.GetType()], wx.TreeItemIcon_Normal)

    def Load(self, events):
        if events:
            for event in events:
                event = copy.deepcopy(event)
                child = self.tree.AppendItem(self.events, event.GetName(), ct_type=2, data=event)
                self.tree.SetItemImage(child, self._images[event.GetType()], wx.TreeItemIcon_Normal)
        else:
            self.Default()

        self.tree.ExpandAll()

    def Save(self):
        return [item.GetData() for item in self.events.GetChildren()]


class EventFrame(ObjectFrame):
    def __init__(self, parent, event_list, entity):
        super().__init__(parent, '')

        self._event_list = event_list
        self._entity = entity
        self._current_id = None

        self.SetIcon(ico.event_16x16.GetIcon())
        self.SetTitle('Events - {}'.format(self._entity.GetName()))

        splitter = wx.SplitterWindow(self.custom, wx.ID_ANY, style=wx.SP_THIN_SASH | wx.SP_LIVE_UPDATE)
        self.event_tree = EventSelectionPanel(splitter)
        self.input = wx.Panel(splitter)
        splitter.SplitVertically(self.event_tree, self.input, 200)

        self.input.SetBackgroundColour(wx.WHITE)

        self.event = EventPanel(self.input)
        self.event.Enable(False)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.event, 0, wx.EXPAND | wx.ALL, GAP)

        self.input.SetSizer(sizer)
        sizer.Fit(self.input)

        # sizing custom ------------------------------------------------------------------------------------------------
        custom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        custom_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, GAP)
        self.custom.SetSizer(custom_sizer)

        self.InitUI()
        self.Load()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnTreeItemRightClicked, self.event_tree.tree)
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnTreeItemChecked, self.event_tree.tree)
        self.apply_button.Bind(wx.EVT_BUTTON, self.OnApplyButton)
        self.ok_button.Bind(wx.EVT_BUTTON, self.OnOKButton)

    def InitUI(self):
        self.event_tree.Populate()

    def OnTreeItemRightClicked(self, event):
        item = event.GetItem()
        context_menu = wx.Menu()

        if item == self.event_tree.events:
            shut_in = wx.MenuItem(context_menu, wx.ID_ANY, 'Add shut-in')
            shut_in.SetBitmap(ico.shut_in_16x16.GetBitmap())
            context_menu.Append(shut_in)

            re_open = wx.MenuItem(context_menu, wx.ID_ANY, 'Add re-open')
            re_open.SetBitmap(ico.shut_in_16x16.GetBitmap())
            context_menu.Append(re_open)

            self.Bind(wx.EVT_MENU, lambda e: self.OnAddEvent(e, ShutInEvent()), shut_in)
            self.Bind(wx.EVT_MENU, lambda e: self.OnAddEvent(e, ReOpenEvent()), re_open)

        elif item.GetData().GetType() not in ('on_stream', 'decommission'):

            delete = wx.MenuItem(context_menu, wx.ID_ANY, 'Delete')
            delete.SetBitmap(ico.delete_16x16.GetBitmap())
            context_menu.Append(delete)

            self.Bind(wx.EVT_MENU, lambda e: self.OnDeleteFunction(e, item), delete)

        self.PopupMenu(context_menu)
        context_menu.Destroy()

    def OnAddEvent(self, event, entity_event):
        self.SaveState()
        self.event_tree.AddEvent(None, entity_event)

    def OnDeleteFunction(self, event, item):
        self.event_tree.tree.Delete(item)

    def OnTreeItemChecked(self, event):
        if self._current_id is None:
            self.event.Enable(True)

        self.SaveState()

        item = event.GetItem()
        data = item.GetData()

        # updating start
        self.event.Set(*data.Get())
        self.event.UpdateText(self.event.GetSelection())

        # get index of the selected item
        self._current_id = item.GetParent().GetChildren().index(item)

    def SaveState(self):
        if self._current_id is not None:
            data = self.event_tree.events.GetChildren()[self._current_id].GetData()
            data.Set(*self.event.Get())

    def Load(self):
        events = self._event_list.GetEvents()
        self.event_tree.Load(events)

    def OnApplyButton(self, event):
        self.SaveState()
        events = [child.GetData() for child in self.event_tree.events.GetChildren()]
        self._event_list.SetEvents(events)

    def OnOKButton(self, event):
        self.OnApplyButton(None)
        self.Close(True)


class ScenarioFrame(EntitySelectionFrame):
    def __init__(self, parent, entity_mgr, object_menu, item=None, item_parent=None):
        super().__init__(parent, Scenario(), entity_mgr, object_menu.projects, item, item_parent)

        self._object_menu = object_menu

        # used for propagating event_lists to the entity manager
        self._selection_items = (self._object_menu.entities.facilities, self._object_menu.entities.subsurface)
        self._selection_types = (ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR)
        self._event_lists = {type_: {} for type_ in self._selection_types}

        if item is not None:
            self._scenario_id = item.GetData().GetId()
        else:
            self._scenario_id = None

        self.duration = DurationPanel(self.properties)

        self.InitUI()
        self.Load()
        self.Center()
        self.SetSize(400, 400)
        self.SetMinSize(self.GetSize())

        # events -------------------------------------------------------------------------------------------------------
        #self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemDoubleClick, self.selection.tree)

    def InitUI(self):
        self.properties.sizer.Add(self.duration, 0, wx.EXPAND | wx.ALL, GAP)

        # selection tree -----------------------------------------------------------------------------------------------
        self.selection.SetImageList(self._object_menu.entities.tree.GetImageList())

        self.InitTitleBar()
        self.Realize()

    def InitTitleBar(self):
        # set title & icon ---------------------------------------------------------------------------------------------
        self.SetIcon(self._entity.GetIcon())

        if self._item is not None:
            self.SetTitle('Scenario - {}'.format(self._entity.GetName()))
        else:
            self.SetTitle('Add scenario')

    # events -----------------------------------------------------------------------------------------------------------
    def OnTreeItemDoubleClick(self, event):
        item = event.GetItem()
        data = item.GetData()

        if not data.IsPointer() or not item.IsChecked():
            return

        entity = self._entity_mgr.GetEntity(*data.GetPointer())
        event_list = self._event_lists[data.GetType()][data.GetId()]
        EventFrame(self, event_list, entity).Show()

    def SaveCustom(self, entity):

        #self._entity_mgr.PreallocateEventLists(self._scenario_id)

        for item in self.selection.GetCheckedItems():
            data = item.GetData()
            event_list = self._event_lists[data.GetType()][data.GetId()]
            self._entity_mgr.UpdateEventList(data.GetPointer(), event_list, self._scenario_id)

        return True

    def LoadCustom(self):
        # adding place-holder event_lists to the dictionary ------------------------------------------------------------
        for item in self.selection.GetItems():
            data = item.GetData()

            if data.GetType() not in self._selection_types:
                continue

            if self._scenario_id:
                event_list = self._entity_mgr.GetEntity(*data.GetPointer()).GetEventList(self._scenario_id)
            else:
                event_list = EventList()

            self._event_lists[data.GetType()][data.GetId()] = event_list

        self.Realize()
