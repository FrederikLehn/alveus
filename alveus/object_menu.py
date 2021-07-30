import wx.lib.agw.aui as aui

from _ids import *
import _icons as ico
from widgets.customized_tree_ctrl import CustomizedTreeCtrl
from widgets.tab_art import AuiModifiedTabArt


# ======================================================================================================================
# Classes used for saving and loading object_menu upon open/close of application
# ======================================================================================================================
class ObjectMenuSave:
    def __init__(self, entities, projects, variables, windows):
        self._entities = entities
        self._projects = projects
        self._variables = variables
        self._windows = windows

    def GetEntities(self):
        return self._entities

    def GetProjects(self):
        return self._projects

    def GetVariables(self):
        return self._variables

    def GetWindows(self):
        return self._windows


class PageSave:
    def __init__(self):

        self._root = None

    @staticmethod
    def GetChildren(item):
        return item.GetChildren()

    def GetFirstChild(self, parent):
        cookie = 0
        return self.GetNextChild(parent, cookie)

    def GetNextChild(self, parent, cookie):
        children = self.GetChildren(parent)
        if cookie < len(children):
            return children[cookie], cookie + 1
        else:
            return None, cookie

    def GetRootItem(self):
        return self._root

    def IsRoot(self, item):
        return self._root is item

    def SetRootItem(self, root):
        self._root = root


class ItemSave:
    def __init__(self, item):

        self._text = item.GetText()
        self._data = item.GetData()
        self._is_expanded = item.IsExpanded()

        self._ct_type = 0         # used for windows
        self._is_checked = False  # used for windows

        if isinstance(self._data, WindowPointer):
            self._ct_type = 1
            self._is_checked = item.IsChecked()

        self._children = []

    def AppendChild(self, child):
        self._children.append(child)

    def GetBitmap(self):
        return self._data.GetBitmap()

    def GetChecked(self):
        return self._is_checked

    def GetChildren(self):
        return self._children

    def GetCtType(self):
        return self._ct_type

    def GetData(self):
        return self._data

    def GetImageKey(self):
        return self._data.GetImageKey()

    def GetText(self):
        return self._text

    def GetType(self):
        return self._data.GetType()

    def IsFolder(self):
        return self._data.IsFolder()

    def IsPointer(self):
        return self._data.IsPointer()

    def IsExpanded(self):
        return self._is_expanded

    def UnlockItem(self):
        self._data.Lock(False)


# ======================================================================================================================
# GenericTreeItem data object
# ======================================================================================================================
class ChartState:
    def __init__(self, checked=False):
        self._checked = checked
        self._sort = False
        self._x = False
        self._y = False
        self._z = False

    def IsChecked(self):
        return self._checked

    def IsSort(self):
        return self._sort

    def IsX(self):
        return self._x

    def IsY(self):
        return self._y

    def IsZ(self):
        return self._z

    def SetChecked(self, checked):
        self._checked = checked

    def SetSort(self, sort):
        self._sort = sort

    def SetX(self, x):
        self._x = x

    def SetY(self, y):
        self._y = y

    def SetZ(self, z):
        self._z = z


class ItemData:
    def __init__(self, id_=None, attr=None, type_=None, family_type=None, parent_type=None, child_type=None,
                 parent_transfer=False, image=None, image_key=None, edit_label=False):

        self._is_pointer = False                 # used to test against in various functions
        self._id = id_                           # id of the entity, variable, window or chart
        self._attr = attr                        # str, used to access on managers via getattr(self, attr)
        self._type = type_                       # type of the entity, variable, window or chart
        self._family_type = family_type          # family type, used to test against in drag & drop
        self._parent_type = parent_type          # test against in drag & drop and copy
        self._child_type = child_type            # used when creating folders
        self._image = image                      # PyEmbeddedImage, used to load trees when opening project
        self._image_key = image_key              # key to correct bitmap in tree image list
        self._edit_label = edit_label            # test against in edit label events
        self._parent_transfer = parent_transfer  # test against in drag & drop and copy
        self._chart_state = {}                   # dict with state{window_id}{chart_id} = ChartState()

        self._locked = False                     # lock/unlock when opening/closing frame of the item

    def AddChartState(self, window_id, chart_id):
        self._chart_state[window_id][chart_id] = ChartState(False)

    def AddWindowState(self, window_id):
        self._chart_state[window_id] = {}

    def AllowParentTransfer(self):
        return self._parent_transfer

    def CanEditLabel(self):
        return self._edit_label

    def ChildIsType(self, type_):
        return self._child_type == type_

    def DeleteChartState(self, window_id, chart_id):
        del self._chart_state[window_id][chart_id]

    def DeleteWindowState(self, window_id):
        del self._chart_state[window_id]

    def GetAttribute(self):
        return self._attr

    def GetBitmap(self):
        return self._image.GetBitmap()

    def GetChartStates(self):
        return self._chart_state

    def GetChildType(self):
        return self._child_type

    def GetFamilyType(self):
        return self._family_type

    def GetId(self):
        return self._id

    def SetId(self, id_):
        self._id = id_

    def GetImageKey(self):
        return self._image_key

    def GetImage(self):
        return self._image

    def GetParentType(self):
        return self._parent_type

    def GetState(self, window_id, chart_id):
        return self._chart_state[window_id][chart_id]

    def GetType(self):
        return self._type

    def GetTypeId(self):
        return None

    def HasId(self, ids):
        if self._id is None:
            return False

        if isinstance(ids, tuple) or isinstance(ids, list):
            return self._id in ids
        else:
            return self._id == ids

    @staticmethod
    def IsChart():
        return False

    @staticmethod
    def IsEntity():
        return False

    def IsFamilyType(self, type_):
        return self._family_type == type_

    def IsFolder(self):
        return self.IsType(ID_FOLDER)

    def IsLocked(self):
        return self._locked

    def IsPointer(self):
        return self._is_pointer

    def IsType(self, types):
        if self._type is None:
            return False

        if isinstance(types, tuple) or isinstance(types, list):
            return self._type in types
        else:
            return self._type == types

    @staticmethod
    def IsVariable():
        return False

    @staticmethod
    def IsWindow():
        return False

    def Lock(self, state=True):
        self._locked = state

    def ParentIsType(self, type_):
        return self._parent_type == type_

    def SetChartStates(self, chart_state):
        self._chart_state = chart_state

    def SetImageKey(self, image_key):
        self._image_key = image_key

    def SetImage(self, image):
        self._image = image

    def SetState(self, window_id, chart_id, state):
        self._chart_state[window_id][chart_id].SetChecked(state)


class EntityPointer(ItemData):
    def __init__(self, id_=None, attr=None, type_=None, family_type=None, parent_type=None, child_type=None,
                 parent_transfer=True, image=None, image_key=None):

        super().__init__(id_=id_, attr=attr, type_=type_, family_type=family_type, parent_type=parent_type,
                         child_type=child_type, parent_transfer=parent_transfer, image=image, image_key=image_key)

        self._is_pointer = True
        self._edit_label = True

    def GetPointer(self):
        return self._id, self._attr

    @staticmethod
    def IsEntity():
        return True

    def SetType(self, type_):
        self._type = type_


class VariablePointer(ItemData):
    def __init__(self, id_=None, type_=None, type_id=None, image=None, image_key=None):
        super().__init__(id_=id_, type_=type_, image=image, image_key=image_key, family_type=type_)

        self._is_pointer = True
        self._type_id = type_id

    def GetPointer(self):
        return self._id

    def GetTypeId(self):
        return self._type_id

    @staticmethod
    def IsVariable():
        return True


class WindowPointer(ItemData):
    def __init__(self, id_=None, type_=None, family_type=None, parent_type=None, is_window=True, image=None, image_key=None):
        super().__init__(type_, parent_type, image=image, image_key=image_key, family_type=family_type)

        self._is_pointer = True
        self._id = id_
        self._is_window = is_window  # alternative is chart
        self._edit_label = True

    def GetPointer(self):
        return self._id

    def IsWindow(self):
        return self._is_window

    def IsChart(self):
        return not self._is_window


# ======================================================================================================================
# CustomTreeCtrl pages on the AUI notebook
# ======================================================================================================================
class Page(wx.Panel):
    # designed to be subclassed
    def __init__(self, parent):
        super().__init__(parent)
        self.tree = CustomizedTreeCtrl(self, wx.TR_HAS_BUTTONS | wx.TR_MULTIPLE | wx.TR_HIDE_ROOT | wx.TR_EDIT_LABELS)

        self._images = {}

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)

    # events -----------------------------------------------------------------------------------------------------------
    def OnCollapseAll(self, event):
        self.tree.CollapseAll()

    def OnExpandAll(self, event):
        self.tree.ExpandAll()

    # external functions -----------------------------------------------------------------------------------------------
    def AddChartState(self, window_id, chart_id, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if (data is not None) and data.IsPointer():
                data.AddChartState(window_id, chart_id)

            self.AddChartState(window_id, chart_id, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def AddFolder(self, item_parent):
        image_key = ID_FOLDER
        image = ico.folder_closed_16x16

        item_data = item_parent.GetData()

        if item_data.IsFolder():
            parent_type = item_data.GetParentType()
        else:
            parent_type = item_data.GetType()

        data = ItemData(type_=ID_FOLDER, family_type=item_data.GetChildType(), parent_type=parent_type,
                        child_type=item_data.GetChildType(), parent_transfer=True,
                        image=image, image_key=image_key, edit_label=True)

        return self.AddItem(item_parent, 'New folder', data, image_key, image.GetBitmap())

    def AddItem(self, item_parent, text, data, image_key, bitmap=wx.NullBitmap, ct_type=0, checked=False, idx=None):
        # items are created with ct_type=1 due to an error that occurs if type is changed after having been initialized
        # as ct_type=0

        if idx is None:
            idx = len(item_parent.GetChildren())

        item = self.tree.InsertItem(item_parent, idx, text, ct_type=1, data=data)
        #item = self.tree.AppendItem(item_parent, text, ct_type=1, data=data)
        self.tree.SetItemType(item, ct_type)

        if ct_type > 0 and checked:
            self.tree.CheckItem2(item, checked)

        self.SetImage(item, image_key, bitmap)
        self.tree.Expand(item_parent)

        return item

    def AddWindowState(self, id_, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if (data is not None) and data.IsPointer():
                data.AddWindowState(id_)

            self.AddWindowState(id_, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    # changes all items which have one of the provided data_types to the ct_type (normal/checkbox/radiobutton)
    def DefaultItemTypes(self, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            self.tree.CheckItem2(child, checked=False, torefresh=False)
            self.tree.SetItemType(child, 0)

            self.DefaultItemTypes(child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def DeleteChartState(self, window_id, chart_id, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if (data is not None) and data.IsPointer():
                data.DeleteChartState(window_id, chart_id)

            self.DeleteChartState(window_id, chart_id, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def DeleteEntity(self, item):
        #self.UpdatePointerIds(item.GetData())
        self.tree.Delete(item)

    def DeleteWindowState(self, id_, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if (data is not None) and data.IsPointer():
                data.DeleteWindowState(id_)

            self.DeleteWindowState(id_, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def EnableChildRadioButtons(self, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            # enable the children of radiobutton items with children
            if (child.GetType() == 2) and (not child.IsChecked()):
                self.tree.EnableItem(child)
                # child.Enable()

            self.EnableChildRadioButtons(child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    # returns a list of all items in the tree that are checked (checkbox and radiobutton)
    def GetCheckedItems(self):
        return self.tree.GetCheckedItems()

    def GetData(self):
        return self.tree.GetData()

    # returns the first parent of an item which is not a folder
    def GetNonFolderParent(self, item):
        parent = item.GetParent()

        if parent.GetData().IsFolder():
            parent = self.GetNonFolderParent(parent)

        return parent

    # returns the set of children that ar first reached which are not folders (may be at different levels)
    def GetNonFolderChildren(self, item, children=None):
        if children is None:
            children = []

        child, cookie = self.tree.GetFirstChild(item)

        while child:
            if child.GetData().IsFolder():
                children = self.GetNonFolderChildren(child, children)
            else:
                children.append(child)

            child, cookie = self.tree.GetNextChild(item, cookie)

        return children

    # returns a list of all items in the tree with a given id
    def GetItemsById(self, ids, parent=None, items=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        if items is None:
            items = []

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            if not child.IsSeparator():
                data = child.GetData()
                if data.HasId(ids):
                    items.append(child)

            items = self.GetItemsById(ids, child, items)
            child, cookie = self.tree.GetNextChild(parent, cookie)

        return items

    # returns a list of all items in the tree with a given type
    def GetItemsByType(self, types, parent=None, items=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        if items is None:
            items = []

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            if not child.IsSeparator():
                data = child.GetData()
                if data.IsType(types):
                    items.append(child)

            items = self.GetItemsByType(types, child, items)
            child, cookie = self.tree.GetNextChild(parent, cookie)

        return items

    def GetMainFrame(self):
        """
        Returns the MainFrame which is the main event loop frame with access to all managers

        Returns
        -------
        MainFrame
        """

        #           notebook    object_menu  splitter   panel       mainframe
        return self.GetParent().GetParent().GetParent().GetParent().GetParent()

    def GetPointers(self):
        all_data = self.GetData()
        return (data.GetPointer() for data in all_data)

    def Load(self, page_l):
        self.LoadItem(page_l)

    def LoadItem(self, page_l, item_l=None, item=None, parent=None):

        if item_l is None:  # root
            item = self.tree.GetRootItem()
            item_l = page_l.GetRootItem()

        elif item_l.IsFolder():
            item = self.AddItem(parent, item_l.GetText(), item_l.GetData(), item_l.GetImageKey(),
                                bitmap=item_l.GetBitmap())

        elif not item_l.IsPointer():  # pre-defined item
            item.SetData(item_l.GetData())

        else:
            item_l.UnlockItem()
            item = self.AddItem(parent, item_l.GetText(), item_l.GetData(), item_l.GetImageKey(),
                                bitmap=item_l.GetBitmap(), ct_type=item_l.GetCtType(), checked=item_l.GetChecked())

        child, cookie = self.tree.GetFirstChild(item)
        child_l, cookie_l = page_l.GetFirstChild(item_l)

        while child_l:
            if child is None or not child.IsSeparator():
                self.LoadItem(page_l, child_l, child, item)
                child_l, cookie_l = page_l.GetNextChild(item_l, cookie_l)

            child, cookie = self.tree.GetNextChild(item, cookie)

        if page_l.IsRoot(item_l):
            return

        if item_l.IsExpanded():
            self.tree.Expand(item)
        else:
            self.tree.Collapse(item)

    # receives a chart id and chart configurations, saves existing state, and sets new state (adds a state if required)
    def LoadState(self, window_id, chart_id, item_types, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if data is not None and data.IsPointer():

                # remove left-most image to reset axis'
                self.tree.SetItemLeftImage(child, -1)  # no image

                # load new state
                try:  # existing state
                    state = data.GetState(window_id, chart_id)
                    checked = state.IsChecked()
                    is_sort, is_x, is_y, is_z = state.IsSort(), state.IsX(), state.IsY(), state.IsZ()  # Variables only

                except KeyError:  # newly added chart
                    checked = False
                    is_sort = is_x = is_y = is_z = False  # only relevant for Variables

                ct_type = 0
                if data.GetType() in item_types[1]:
                    ct_type = item_types[0]

                data.SetState(window_id, chart_id, checked)
                self.tree.SetItemType(child, ct_type)

                if ct_type > 0:
                    self.tree.CheckItem2(child, checked=checked, torefresh=True)

                    # disable the children of unchecked radiobuttons (if the child is not a radiobutton)
                    if (child.GetType() == 2) and (not checked):
                        grandchild = child.GetChildren()
                        if (grandchild is not None) and grandchild:
                            if grandchild[0].GetType() != 2:
                                self.tree.EnableChildren(child, enable=False)

                else:
                    child.SetType(1)  # used to ensure CheckItem2 goes through
                    self.tree.CheckItem2(child, checked=False, torefresh=False)
                    child.SetType(0)

                # assign left-image for axis' on VariablePage
                if is_sort:
                    self.tree.SetItemLeftImage(child, ID_SORT)
                elif is_x:
                    self.tree.SetItemLeftImage(child, ID_X_AXIS)
                elif is_y:
                    self.tree.SetItemLeftImage(child, ID_Y_AXIS)
                elif is_z:
                    self.tree.SetItemLeftImage(child, ID_Z_AXIS)

            self.LoadState(window_id, chart_id, item_types, parent=child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def Save(self):
        page_s = PageSave()

        root = self.tree.GetRootItem()
        root_s = self.SaveItem(root)
        page_s.SetRootItem(root_s)

        return page_s

    def SaveItem(self, item):
        item_s = ItemSave(item)

        child, cookie = self.tree.GetFirstChild(item)

        while child:
            if not child.IsSeparator():
                child_s = self.SaveItem(child)
                item_s.AppendChild(child_s)

            child, cookie = self.tree.GetNextChild(item, cookie)

        return item_s

    def SaveState(self, window_id, chart_id, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if data is not None and data.IsPointer():

                if None not in (window_id, chart_id):
                    data.SetState(window_id, chart_id, child.IsChecked())

            self.SaveState(window_id, chart_id, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def SetImage(self, item, image_key, bitmap=wx.NullBitmap):
        """
        Sets everything related to the image shown for an item on the object_menu

        Parameters
        ----------
        item : GenericTreeItem
            Class GenericTreeItem from CustomTreeCtrl
        image_key : int or str
            Key to a dictionary
        bitmap : wx.Bitmap
            Class wx.Bitmap
        """

        # update the tree's image list
        if image_key in self._images:

            image = self._images[image_key]

        else:

            il = self.tree.GetImageList()

            # add normal image
            image = il.Add(bitmap)
            self._images[image_key] = image

            # add disabled version
            img = bitmap.ConvertToImage()
            dimage = il.Add(wx.Bitmap(img.ConvertToDisabled()))
            self._images['{}_disabled'.format(image_key)] = dimage

        # set image on tree
        self.tree.SetItemImage(item, image, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(item, image, wx.TreeItemIcon_Expanded)

    def UpdateEntity(self, item, entity, image_id=None):
        entity.SetImage(image_id)

        # update image_key and image in item data
        data = item.GetData()
        data.SetImageKey(entity.GetImageKey())
        data.SetImage(entity.GetImage())

        # update entity item in object_menu
        self.UpdateItem(item, entity.GetName(), entity.GetImageKey(), bitmap=entity.GetBitmap())

    def UpdatePointerIds(self, pointer):
        # upon deletion of an item, all entity pointers has to be updated
        items = self.GetItemsByType(pointer.GetType())
        for item in items:
            p = item.GetData()
            if p.GetId() > pointer.GetId():
                p.SetId(p.GetId() - 1)

    def UpdateItem(self, item, text, image_key, bitmap=wx.NullBitmap):
        self.tree.SetItemText(item, text)
        self.SetImage(item, image_key, bitmap=bitmap)

    # Unchecks all items in the tree (checkbox and radiobuttons)
    def UncheckAllItems(self, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            if child.GetType() == 2:
                # to avoid locking children - change to checkbox, enable children, then check false
                self.tree.SetItemType(child, 1)
                self.tree.EnableChildren(child, enable=True)

            # for some reason self.tree.CheckItem does not check radiobuttons
            self.tree.CheckItem2(child, checked=False, torefresh=True)

            self.UncheckAllItems(child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    # Unchecks all other radiobuttons in the tree than the provided item
    def UncheckOtherRadioButtons(self, item=None, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            if (child.GetType() == 2) and (child is not item):
                self.tree.CheckItem2(child, checked=False, torefresh=True)

            self.UncheckOtherRadioButtons(item, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)


class EntityMgrPage(Page):
    def __init__(self, parent):
        super().__init__(parent)

    def AddEntity(self, item_parent, entity, image_id=None, idx=None):
        entity.SetImage(image_id)

        text = entity.GetName()
        image_key = entity.GetImageKey()
        image = entity.GetImage()

        data = EntityPointer(entity.GetId(), entity.GetAttribute(), entity.GetType(), entity.GetFamilyType(),
                             entity.GetPrimaryParent(), entity.GetPrimaryChild(), entity.AllowParentTransfer(),
                             image=image, image_key=image_key)

        bitmap = entity.GetBitmap()

        return self.AddItem(item_parent, text, data, image_key, bitmap, idx=idx)

    def CopyEntity(self, item_parent, entity, data, idx=None):
        item = self.AddEntity(item_parent, entity, idx=idx)
        copy_data = item.GetData()
        copy_data.SetChartStates(data.GetChartStates())
        copy_data.Lock(False)
        return item

    def EnableCutItems(self, items):
        for item in items:
            image_key = item.GetData().GetImageKey()
            self.tree.SetItemImage(item, self._images[image_key], wx.TreeItemIcon_Normal)
            self.tree.SetItemImage(item, self._images[image_key], wx.TreeItemIcon_Expanded)

    def HandleCopy(self, tree, cut=False):
        items = tree.GetSelections()

        if self.AllowHandling(items):
            # send copy event to MainFrame
            self.GetMainFrame().CopyEntities(tree, items, cut=cut)

            if cut:
                for item in items:
                    image_key = '{}_disabled'.format(item.GetData().GetImageKey())
                    self.tree.SetItemImage(item, self._images[image_key], wx.TreeItemIcon_Normal)
                    self.tree.SetItemImage(item, self._images[image_key], wx.TreeItemIcon_Expanded)

    def HandleDelete(self, tree):
        items = tree.GetSelections()

        if self.AllowHandling(items):
            # send deletion event to MainFrame
            self.GetMainFrame().OnDeleteEntities(None, items, self)

    def HandlePaste(self, tree):
        items = tree.GetSelection()

        # send paste event to MainFrame
        self.GetMainFrame().PasteEntities(tree, items)

    def AllowHandling(self, items):
        rep_type = None

        # conduct various checks
        for i, item in enumerate(items):

            if item.IsSeparator():
                return

            data = item.GetData()
            if (not data.IsPointer()) and (not data.IsFolder()):
                return

            if i == 0:
                rep_type = data.GetFamilyType()

            if not data.IsFamilyType(rep_type):
                return

        return True


class EntitiesPage(EntityMgrPage):
    def __init__(self, parent):
        super().__init__(parent)

        self.fields = None
        self.blocks = None
        self.facilities = None
        self.subsurface = None
        self.portfolio = None

        # Create an image list to add icons next to an item
        il = wx.ImageList(16, 16)

        self._fields_icon = il.Add(ico.field_16x16.GetBitmap())
        self._blocks_icon = il.Add(ico.block_16x16.GetBitmap())
        self._facilities_icon = il.Add(ico.platforms_16x16.GetBitmap())
        self._subsurface_icon = il.Add(ico.reservoirs_16x16.GetBitmap())
        self._analogues_icon = il.Add(ico.analogues_16x16.GetBitmap())

        self.tree.SetImageList(il)

        # workaround to not have ugly greyed out disabled pictures
        self.tree._grayedImageList = self.tree.GetImageList()

    def Initialize(self):
        root = self.tree.AddRoot('Entities')

        self.tree.AppendSeparator(root)

        self.fields = self.tree.AppendItem(root, 'Fields', data=ItemData(type_=ID_FIELDS, family_type=ID_FIELDS, child_type=ID_FIELD))
        self.tree.SetItemImage(self.fields, self._fields_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.fields, self._fields_icon, wx.TreeItemIcon_Expanded)

        self.blocks = self.tree.AppendItem(root, 'Blocks', data=ItemData(type_=ID_BLOCKS, family_type=ID_BLOCKS, child_type=ID_BLOCK))
        self.tree.SetItemImage(self.blocks, self._blocks_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.blocks, self._blocks_icon, wx.TreeItemIcon_Expanded)

        self.tree.AppendSeparator(root)

        self.facilities = self.tree.AppendItem(root, 'Facilities', data=ItemData(type_=ID_FACILITIES, family_type=ID_FACILITIES, child_type=ID_NETWORK_FAMILY))
        self.tree.SetItemImage(self.facilities, self._facilities_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.facilities, self._facilities_icon, wx.TreeItemIcon_Expanded)

        self.tree.AppendSeparator(root)

        self.subsurface = self.tree.AppendItem(root, 'Subsurface', data=ItemData(type_=ID_SUBSURFACE, family_type=ID_SUBSURFACE, child_type=ID_RESERVOIR))
        self.tree.SetItemImage(self.subsurface, self._subsurface_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.subsurface, self._subsurface_icon, wx.TreeItemIcon_Expanded)

        self.tree.AppendSeparator(root)

        self.portfolio = self.tree.AppendItem(root, 'Portfolio', data=ItemData(type_=ID_PORTFOLIO, family_type=ID_PORTFOLIO, child_type=ID_PORTFOLIO_FAMILY))
        self.tree.SetItemImage(self.portfolio, self._analogues_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.portfolio, self._analogues_icon, wx.TreeItemIcon_Expanded)


class ProjectsPage(EntityMgrPage):
    def __init__(self, parent):
        super().__init__(parent)

        self.simulations = None

        # Create an image list to add icons next to an item
        il = wx.ImageList(16, 16)
        self.projects_icon = il.Add(ico.project_16x16.GetBitmap())
        self.tree.SetImageList(il)

        # workaround to not have ugly greyed out disabled pictures
        self.tree._grayedImageList = self.tree.GetImageList()

    def Initialize(self):
        root = self.tree.AddRoot('Projects')

        self.simulations = self.tree.AppendItem(root, 'Simulations', data=ItemData(type_=ID_SIMULATIONS, family_type=ID_SIMULATIONS, child_type=ID_PROJECT))
        self.tree.SetItemImage(self.simulations, self.projects_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.simulations, self.projects_icon, wx.TreeItemIcon_Expanded)


class VariablesPage(Page):
    def __init__(self, parent):
        super().__init__(parent)

        self.durations = None
        self.potentials = None
        self.rates = None
        self.cumulatives = None
        self.ratios = None
        self.uptimes = None
        self.summaries = None
        self.statics = None
        self.scalers = None
        self.volumes = None
        self.risking = None
        self.well_spacing = None
        self.res_fluids = None
        self.inj_fluids = None
        self.facilities = None
        self.constraints = None
        self.plateaus = None

        # Create an image list to add icons next to an item ------------------------------------------------------------
        il = wx.ImageList(16, 16)
        self._duration_icon = il.Add(ico.duration_16x16.GetBitmap())
        self._potential_icon = il.Add(ico.rates_16x16.GetBitmap())
        self._rate_icon = il.Add(ico.rates_16x16.GetBitmap())
        self._cumulative_icon = il.Add(ico.cumulatives_16x16.GetBitmap())
        self._ratio_icon = il.Add(ico.ratios_16x16.GetBitmap())
        self._uptime_icon = il.Add(ico.uptime_16x16.GetBitmap())
        self._summary_icon = il.Add(ico.summary_16x16.GetBitmap())
        self._static_icon = il.Add(ico.grid_properties_16x16.GetBitmap())
        self._scaling_icon = il.Add(ico.profiles_chart_16x16.GetBitmap())
        self._volume_icon = il.Add(ico.stoiip_16x16.GetBitmap())
        self._risking_icon = il.Add(ico.risking_16x16.GetBitmap())
        self._wells_icon = il.Add(ico.well_16x16.GetBitmap())
        self._res_fluid_icon = il.Add(ico.fluids_16x16.GetBitmap())
        self._inj_fluid_icon = il.Add(ico.fluids_injection_16x16.GetBitmap())
        self._facility_icon = il.Add(ico.platforms_16x16.GetBitmap())
        self._constraint_icon = il.Add(ico.flow_constraint_16x16.GetBitmap())

        self.tree.SetImageList(il)

        # Create an left image list to add icons next to an item -------------------------------------------------------
        lil = wx.ImageList(16, 16)
        lil.Add(ico.x_16x16.GetBitmap())  # TODO: sort
        lil.Add(ico.x_16x16.GetBitmap())
        lil.Add(ico.y_16x16.GetBitmap())
        lil.Add(ico.z_16x16.GetBitmap())

        self.tree.SetLeftImageList(lil)

    def Initialize(self):
        root = self.tree.AddRoot('Variables')

        self.durations = self.tree.AppendItem(root, 'Durations', data=ItemData(type_='durations_'))
        self.tree.SetItemImage(self.durations, self._duration_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.durations, self._duration_icon, wx.TreeItemIcon_Expanded)

        self.potentials = self.tree.AppendItem(root, 'Potentials', data=ItemData(type_='potentials_'))
        self.tree.SetItemImage(self.potentials, self._potential_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.potentials, self._potential_icon, wx.TreeItemIcon_Expanded)

        self.rates = self.tree.AppendItem(root, 'Rates', data=ItemData('rates_'))
        self.tree.SetItemImage(self.rates, self._rate_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.rates, self._rate_icon, wx.TreeItemIcon_Expanded)

        self.cumulatives = self.tree.AppendItem(root, 'Cumulatives', data=ItemData(type_='cumulatives_'))
        self.tree.SetItemImage(self.cumulatives, self._cumulative_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.cumulatives, self._cumulative_icon, wx.TreeItemIcon_Expanded)

        self.ratios = self.tree.AppendItem(root, 'Ratios', data=ItemData(type_='ratios_'))
        self.tree.SetItemImage(self.ratios, self._ratio_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.ratios, self._ratio_icon, wx.TreeItemIcon_Expanded)

        self.uptimes = self.tree.AppendItem(root, 'Uptimes', data=ItemData(type_='uptimes_'))
        self.tree.SetItemImage(self.uptimes, self._uptime_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.uptimes, self._uptime_icon, wx.TreeItemIcon_Expanded)

        self.tree.AppendSeparator(root)

        self.summaries = self.tree.AppendItem(root, 'Summaries', data=ItemData(type_='summaries_'))
        self.tree.SetItemImage(self.summaries, self._summary_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.summaries, self._summary_icon, wx.TreeItemIcon_Expanded)

        self.tree.AppendSeparator(root)

        self.scalers = self.tree.AppendItem(root, 'Scalers', data=ItemData(type_='scalers_'))
        self.tree.SetItemImage(self.scalers, self._scaling_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.scalers, self._scaling_icon, wx.TreeItemIcon_Expanded)

        self.statics = self.tree.AppendItem(root, 'Static', data=ItemData(type_='statics_'))
        self.tree.SetItemImage(self.statics, self._static_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.statics, self._static_icon, wx.TreeItemIcon_Expanded)

        self.tree.AppendSeparator(root)

        self.volumes = self.tree.AppendItem(root, 'Volumes', data=ItemData(type_='volumes_'))
        self.tree.SetItemImage(self.volumes, self._volume_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.volumes, self._volume_icon, wx.TreeItemIcon_Expanded)

        self.risking = self.tree.AppendItem(root, 'Risking', data=ItemData(type_='risking_'))
        self.tree.SetItemImage(self.risking, self._risking_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.risking, self._risking_icon, wx.TreeItemIcon_Expanded)

        self.tree.AppendSeparator(root)

        self.well_spacing = self.tree.AppendItem(root, 'Well Spacing', data=ItemData(type_='well_spacing_'))
        self.tree.SetItemImage(self.well_spacing, self._wells_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.well_spacing, self._wells_icon, wx.TreeItemIcon_Expanded)

        self.res_fluids = self.tree.AppendItem(root, 'Reservoir Fluids', data=ItemData(type_='res_fluids_'))
        self.tree.SetItemImage(self.res_fluids, self._res_fluid_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.res_fluids, self._res_fluid_icon, wx.TreeItemIcon_Expanded)

        self.inj_fluids = self.tree.AppendItem(root, 'Injection Fluids', data=ItemData(type_='inj_fluids_'))
        self.tree.SetItemImage(self.inj_fluids, self._inj_fluid_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.inj_fluids, self._inj_fluid_icon, wx.TreeItemIcon_Expanded)

        self.tree.AppendSeparator(root)

        self.facilities = self.tree.AppendItem(root, 'Facilities', data=ItemData(type_='facilities_'))
        self.tree.SetItemImage(self.facilities, self._facility_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.facilities, self._facility_icon, wx.TreeItemIcon_Expanded)

        self.constraints = self.tree.AppendItem(root, 'Constraints', data=ItemData(type_='constraints_'))
        self.tree.SetItemImage(self.constraints, self._constraint_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.constraints, self._constraint_icon, wx.TreeItemIcon_Expanded)

        self.tree.ExpandAll()

    def Populate(self, variable_mgr):
        variables = variable_mgr.GetAllVariables()

        for id_, variable in variables:
            attr = id_[1:]

            if attr == 'summaries':
                pass
            else:
                item_parent = getattr(self, variable.GetType())
                self.AddVariable(item_parent, variable)

        self.tree.ExpandAll()

    def AddVariable(self, item_parent, variable, image_id=None):
        variable.SetImage(image_id)

        text = variable.GetMenuLabel()
        image_key = variable.GetImageKey()
        image = variable.GetImage()
        data = VariablePointer(id_=variable.GetId(), type_=variable.GetType(), type_id=variable.GetTypeId(),
                               image=image, image_key=image_key)

        bitmap = variable.GetBitmap()

        return self.AddItem(item_parent, text, data, image_key, bitmap)

    def SetItemAsAxis(self, item, window_id, chart_id, axis_id):
        # clear existing
        self.ClearAxisState(window_id, chart_id, axis_id, item)

        # assign new variable as x, y or z
        data = item.GetData()
        state = data.GetState(window_id, chart_id)

        if axis_id == ID_SORT:
            state.SetSort(True)

        elif axis_id == ID_X_AXIS:
            state.SetX(True)

        elif axis_id == ID_Y_AXIS:
            state.SetY(True)

        elif axis_id == ID_Z_AXIS:
            state.SetZ(True)

        self.tree.SetItemLeftImage(item, axis_id)

    def ClearAxisState(self, window_id, chart_id, axis_id, item=None, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            is_assigned = False
            data = child.GetData()

            if data is not None and data.IsPointer():
                state = data.GetState(window_id, chart_id)

                if item is not None and item is child:
                    state.SetSort(False)
                    state.SetX(False)
                    state.SetY(False)
                    state.SetZ(False)
                    is_assigned = True

                else:
                    if axis_id == ID_SORT and state.IsSort():
                        state.SetSort(False)
                        is_assigned = True

                    elif axis_id == ID_X_AXIS and state.IsX():
                        state.SetX(False)
                        is_assigned = True

                    elif axis_id == ID_Y_AXIS and state.IsY():
                        state.SetY(False)
                        is_assigned = True

                    elif axis_id == ID_Z_AXIS and state.IsZ():
                        state.SetZ(False)
                        is_assigned = True

                if is_assigned:
                    self.tree.SetItemLeftImage(child, -1)  # no image

            self.ClearAxisState(window_id, chart_id, axis_id, item, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def DefaultAxisStates(self, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if data is not None and data.IsPointer():
                self.tree.SetItemLeftImage(child, -1)  # no image

            self.DefaultAxisStates(child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

    def GetAxis(self, window_id, chart_id, sort=None, x=None, y=None, z=None, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if data is not None and data.IsPointer():
                state = data.GetState(window_id, chart_id)

                if state.IsSort():
                    sort = data

                elif state.IsX():
                    x = data

                elif state.IsY():
                    y = data

                elif state.IsZ():
                    z = data

            sort, x, y, z = self.GetAxis(window_id, chart_id, sort, x, y, z, child)
            child, cookie = self.tree.GetNextChild(parent, cookie)

        return sort, x, y, z

    def UpdateVariable(self, item, variable, image_id=None):
        variable.SetImage(image_id)
        self.UpdateItem(item, variable.GetMenuLabel(), variable.GetImageKey(), bitmap=variable.GetBitmap())

    def HandleDelete(self, tree):
        items = tree.GetSelections()

        if self.AllowHandling(items):
            # send deletion event to MainFrame
            self.GetMainFrame().OnDeleteSummaries(None, items)

    def AllowHandling(self, items):
        # conduct various checks
        for i, item in enumerate(items):

            if item.IsSeparator():
                return

            data = item.GetData()

            if not data.GetTypeId() == ID_SUMMARY:
                return

        return True


class WindowsPage(Page):
    def __init__(self, parent):
        super().__init__(parent)

        self.windows = None

        # Create an image list to add icons next to an item
        il = wx.ImageList(16, 16)
        self._windows_icon = il.Add(ico.windows_16x16.GetBitmap())
        self.tree.SetImageList(il)

        # workaround to not have ugly greyed out disabled pictures
        self.tree._grayedImageList = self.tree.GetImageList()

    def Initialize(self):
        root = self.tree.AddRoot('Windows')

        self.windows = self.tree.AppendItem(root, 'Windows', data=ItemData('windows_'))
        self.tree.SetItemImage(self.windows, self._windows_icon, wx.TreeItemIcon_Normal)
        self.tree.SetItemImage(self.windows, self._windows_icon, wx.TreeItemIcon_Expanded)

        self.tree.ExpandAll()

    def AddChart(self, window, chart):
        window_item = self.GetWindowItem(window.GetId())

        image_key = chart.GetType()
        image = chart.GetImage()

        data = WindowPointer(chart.GetId(), chart.GetType(), chart.GetFamilyType(), chart.GetParentType(),
                             is_window=False, image=image, image_key=image_key)

        label = chart.GetLabel()
        bitmap = chart.GetBitmap()

        return self.AddItem(window_item, label, data, image_key, bitmap, ct_type=1, checked=True)

    def AddWindow(self, window):
        image_key = window.GetImageKey()
        image = window.GetImage()
        data = WindowPointer(window.GetId(), window.GetType(), window.GetFamilyType(), window.GetParentType(),
                             image=image, image_key=image_key)

        label = window.GetLabel()
        bitmap = window.GetBitmap()

        return self.AddItem(self.windows, label, data, image_key, bitmap, ct_type=1, checked=True)

    def GetCheckedChartItems(self, window_id):
        window = self.GetWindowItem(window_id)
        child, cookie = self.tree.GetFirstChild(window)

        charts = []
        while child:
            if child.IsChecked():
                charts.append(child)

            child, cookie = self.tree.GetNextChild(window, cookie)

        return charts

    def GetWindowItem(self, id_, parent=None):
        # reverse pointer method
        item = None
        if parent is None:
            parent = self.windows

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            data = child.GetData()

            if data is not None and data.GetId() == id_:
                return child
            else:
                item = self.GetWindowItem(id_, child)
                child, cookie = self.tree.GetNextChild(parent, cookie)

        return item

    def UpdateWindow(self, window, item=None):
        if item is None:
            item = self.GetWindowItem(window.GetId())

        data = item.GetData()
        data.SetImageKey(window.GetImageKey())
        data.SetImage(window.GetImage())
        self.UpdateItem(item, window.GetLabel(), window.GetImageKey(), bitmap=window.GetBitmap())

    def WindowClosed(self, id_):
        item = self.GetWindowItem(id_)
        self.tree.CheckItem2(item, False, torefresh=True)

    def HandleDelete(self, tree):
        items = tree.GetSelections()

        allow, is_window = self.AllowHandling(items)

        if allow:
            # send deletion event to MainFrame
            mf = self.GetMainFrame()

            if is_window:
                mf.OnDeleteWindows(None, items)
            else:
                mf.OnDeleteCharts(None, items)

    def AllowHandling(self, items):
        is_window = None

        # conduct various checks
        for i, item in enumerate(items):

            if item.IsSeparator():
                return False, None

            data = item.GetData()
            if not data.IsPointer():
                return False, None

            if i == 0:
                is_window = data.IsWindow()

            if is_window != data.IsWindow():
                return False, None

        return True, is_window


class ObjectMenuNotebook(aui.AuiNotebook):
    def __init__(self, parent):
        super().__init__(parent=parent)
        # set style
        self.SetAGWWindowStyleFlag(aui.AUI_NB_BOTTOM | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_DRAW_DND_TAB | aui.AUI_NB_TAB_MOVE)

        self.ChangeTabArt()

    def ChangeTabArt(self):
        art = AuiModifiedTabArt()

        # colours ------------------------------------------------------------------------------------------------------
        colour = wx.Colour(230, 230, 230)

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


class ObjectMenu(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        self.SetMinSize(wx.Size(150, 0))

        self.notebook = ObjectMenuNotebook(self)
        self.notebook.SetName('object_menu_notebook')

        # Set entities tab ---------------------------------------------------------------------------------------------
        self.entities = EntitiesPage(self.notebook)
        self.notebook.AddPage(self.entities, 'Entities')
        self.notebook.SetPageBitmap(self.notebook.GetPageIndex(self.entities), ico.folder_closed_16x16.GetBitmap())

        # Set simulations tab ------------------------------------------------------------------------------------------
        self.projects = ProjectsPage(self.notebook)
        self.notebook.AddPage(self.projects, 'Simulations')
        self.notebook.SetPageBitmap(self.notebook.GetPageIndex(self.projects), ico.project_16x16.GetBitmap())

        # Set variables tab --------------------------------------------------------------------------------------------
        self.variables = VariablesPage(self.notebook)
        self.notebook.AddPage(self.variables, 'Variables')
        self.notebook.SetPageBitmap(self.notebook.GetPageIndex(self.variables), ico.grid_properties_16x16.GetBitmap())

        # Set windows tab --------------------------------------------------------------------------------------------
        self.windows = WindowsPage(self.notebook)
        self.notebook.AddPage(self.windows, 'Windows')
        self.notebook.SetPageBitmap(self.notebook.GetPageIndex(self.windows), ico.windows_16x16.GetBitmap())

        # set aui manager ----------------------------------------------------------------------------------------------
        self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().Name('object_menu').CenterPane().PaneBorder(False))
        self._mgr.Update()

    def AddChart(self, window, chart):
        ids = (window.GetId(), chart.GetId())

        self.entities.AddChartState(*ids)
        self.projects.AddChartState(*ids)
        self.variables.AddChartState(*ids)

        # ensures correct check-boxes
        self.LoadState(*ids, chart)

        # if window is split, add a chart item to the window item, otherwise update window item bitmap
        if window.AllowSplit():
            self.windows.AddChart(window, chart)
        else:
            self.windows.UpdateWindow(window)

    def AddWindow(self, window):
        id_ = window.GetId()

        self.entities.AddWindowState(id_)
        self.projects.AddWindowState(id_)
        self.variables.AddWindowState(id_)

        self.windows.AddWindow(window)

    def Clear(self):

        self.FreezeTrees()

        self.entities.tree.DeleteAllItems()
        self.projects.tree.DeleteAllItems()
        self.variables.tree.DeleteAllItems()
        self.windows.tree.DeleteAllItems()

        self.ThawTrees()

    def DefaultItemTypes(self):

        self.FreezeTrees()

        self.entities.DefaultItemTypes()
        self.projects.DefaultItemTypes()
        self.variables.DefaultItemTypes()
        self.variables.DefaultAxisStates()

        self.ThawTrees()

    def DeleteChart(self, item, window_id, chart_id):

        self.entities.DeleteChartState(window_id, chart_id)
        self.projects.DeleteChartState(window_id, chart_id)
        self.variables.DeleteChartState(window_id, chart_id)

        self.windows.tree.Delete(item)

    def DeleteWindow(self, item, id_):

        self.entities.DeleteWindowState(id_)
        self.projects.DeleteWindowState(id_)
        self.variables.DeleteWindowState(id_)

        self.windows.tree.Delete(item)

    def FreezeTrees(self):

        self.entities.tree.Freeze()
        self.projects.tree.Freeze()
        self.variables.tree.Freeze()

    def GetActiveTab(self):
        idx = self.notebook.GetSelection()

        if idx > -1:
            return self.notebook.GetPage(idx)
        else:
            return None

    def Initialize(self):

        self.FreezeTrees()

        self.entities.Initialize()
        self.projects.Initialize()
        self.variables.Initialize()
        self.windows.Initialize()

        self.ThawTrees()

    def Load(self, object_):

        self.FreezeTrees()

        self.entities.Load(object_.GetEntities())
        self.projects.Load(object_.GetProjects())
        self.variables.Load(object_.GetVariables())
        self.windows.Load(object_.GetWindows())

        self.ThawTrees()

    def LoadState(self, window_id, chart_id, chart):

        self.FreezeTrees()

        self.entities.LoadState(window_id, chart_id, chart.GetEntities())
        self.projects.LoadState(window_id, chart_id, chart.GetProjects())
        self.variables.LoadState(window_id, chart_id, chart.GetVariables())

        self.ThawTrees()

    def Populate(self, variable_mgr):

        self.FreezeTrees()
        self.variables.Populate(variable_mgr)
        self.ThawTrees()

    def Save(self):

        return ObjectMenuSave(self.entities.Save(), self.projects.Save(), self.variables.Save(), self.windows.Save())

    def SaveState(self, window_id, chart_id):

        self.entities.SaveState(window_id, chart_id)
        self.projects.SaveState(window_id, chart_id)
        self.variables.SaveState(window_id, chart_id)

    def ThawTrees(self):

        self.entities.tree.Thaw()
        self.projects.tree.Thaw()
        self.variables.tree.Thaw()

    def UncheckAllItems(self):

        self.FreezeTrees()

        self.entities.UncheckAllItems()
        self.projects.UncheckAllItems()
        self.variables.UncheckAllItems()

        self.ThawTrees()
