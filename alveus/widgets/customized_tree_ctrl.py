import wx
from wx.lib.agw.customtreectrl import CustomTreeCtrl

# used for editing the source code
from wx.lib.agw.customtreectrl import TreeEvent, TreeTextCtrl, wxEVT_TREE_BEGIN_LABEL_EDIT, wxEVT_TREE_KEY_DOWN,\
    EventFlagsToSelType, wxEVT_TREE_ITEM_MENU, wxEVT_TREE_ITEM_ACTIVATED, TR_HIDE_ROOT, TreeFindTimer, _DELAY


class CustomizedTreeCtrl(CustomTreeCtrl):
    def __init__(self, parent, agw_style=None):
        super().__init__(parent, wx.ID_ANY, agwStyle=wx.TR_HAS_BUTTONS | wx.TR_MULTIPLE | wx.TR_HIDE_ROOT)

        self.SetBackgroundColour(wx.Colour(255, 255, 255))

        if agw_style is not None:
            self.SetAGWWindowStyleFlag(agw_style)

    # external functions -----------------------------------------------------------------------------------------------
    def CollapseAll(self, parent=None):
        if parent is None:
            parent = self.GetRootItem()

        child, cookie = self.GetFirstChild(parent)

        while child:
            self.Collapse(child)
            self.CollapseAll(child)
            child, cookie = self.GetNextChild(parent, cookie)

    def GetItems(self, parent=None, items=None):
        if parent is None:
            parent = self.GetRootItem()

        if items is None:
            items = []

        child, cookie = self.GetFirstChild(parent)

        while child:
            items.append(child)

            items = self.GetItems(child, items)
            child, cookie = self.GetNextChild(parent, cookie)

        return items

    # returns a list of all items in the tree that are checked (checkbox and radiobutton), excluding root
    def GetCheckedItems(self, parent=None, checked_items=None):
        if parent is None:
            parent = self.GetRootItem()

        if checked_items is None:
            checked_items = []

        child, cookie = self.GetFirstChild(parent)

        while child:
            if self.IsItemChecked(child):
                checked_items.append(child)

            checked_items = self.GetCheckedItems(child, checked_items)
            child, cookie = self.GetNextChild(parent, cookie)

        return checked_items

    def GetData(self, items=None):
        if items is None:
            items = self.GetCheckedItems()

        data = []
        for item in items:
            data.append(item.GetData())

        return data

    # ==================================================================================================================
    # CHANGES TO ORIGINAL CODE
    # ==================================================================================================================
    # Taken from https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/customtreectrl.py (12-12-2019)
    # Changes are made to lines (in the link): 7537-7541 moving the further up, to allow for TreeEventItem.SelectAll()
    # in the wxEVT_TREE_BEGIN_LABEL_EDIT event
    def Edit(self, item):
        """
        Internal function. Starts the editing of an item label, sending a
        ``EVT_TREE_BEGIN_LABEL_EDIT`` event.
        :param item: an instance of :class:`GenericTreeItem`.
        .. warning:: Separator-type items can not be edited.
        """

        if item.IsSeparator():
            return

        data = item.GetData()  # added by me

        if data is None:  # added by me
            return

        if not data.CanEditLabel():  # added by me
            return

        # 4 lines below are moved from bottom of code to here, to allow .SelectAll(). Added the CHAR_HOOK event
        if self._editCtrl is not None and item != self._editCtrl.item():
            self._editCtrl.StopEditing()

        self._editCtrl = TreeTextCtrl(self, item=item)
        self._editCtrl.Bind(wx.EVT_CHAR_HOOK, self._editCtrl.OnChar)
        self._editCtrl.SetFocus()

        te = TreeEvent(wxEVT_TREE_BEGIN_LABEL_EDIT, self.GetId())
        te._item = item
        te.SetEventObject(self)
        if self.GetEventHandler().ProcessEvent(te) and not te.IsAllowed():
            # vetoed by user
            return

        # We have to call this here because the label in
        # question might just have been added and no screen
        # update taken place.
        if self._dirty:
            if wx.Platform in ["__WXMSW__", "__WXMAC__"]:
                self.Update()
            else:
                wx.YieldIfNeeded()

    # ------------------------------------------------------------------------------------------------------------------
    # Taken from https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/customtreectrl.py (12-12-2019)
    # Changes are made to lines (in the link): 7178 removing wx.WXK_SPACE from the list, to reuse another place.
    # Also commented out lines 7190-7197, as it is no longer applicable. Could be moved down to my code potentially
    # Code is then added at line (in this file): 210-223
    def OnKeyDown(self, event):
        """
        Handles the ``wx.EVT_KEY_DOWN`` event for :class:`CustomTreeCtrl`, sending a
        ``EVT_TREE_KEY_DOWN`` event.
        :param `event`: a :class:`KeyEvent` event to be processed.
        """

        te = TreeEvent(wxEVT_TREE_KEY_DOWN, self.GetId())
        te._evtKey = event
        te.SetEventObject(self)

        if self.GetEventHandler().ProcessEvent(te):
            # intercepted by the user code
            return

        if self._current is None or self._key_current is None:
            self._current = self._key_current = self.GetFirstVisibleItem()

        # how should the selection work for this event?
        is_multiple, extended_select, unselect_others = EventFlagsToSelType(self.GetAGWWindowStyleFlag(),
                                                                            event.ShiftDown(), event.CmdDown())

        # + : Expand
        # - : Collaspe
        # * : Expand all/Collapse all
        # ' ' | return : activate
        # up    : go up (not last children!)
        # down  : go down
        # left  : go to parent
        # right : open if parent and go next
        # home  : go to root
        # end   : go to last item without opening parents
        # alnum : start or continue searching for the item with this prefix

        keyCode = event.GetKeyCode()

        if keyCode in [ord("+"), wx.WXK_ADD]:  # "+"
            if self._current.HasPlus() and not self.IsExpanded(self._current) and self.IsItemEnabled(self._current):
                self.Expand(self._current)

        elif keyCode in [ord("*"), wx.WXK_MULTIPLY]:  # "*"
            if not self.IsExpanded(self._current) and self.IsItemEnabled(self._current):
                # expand all
                self.ExpandAll()  # self._current removed by me

        elif keyCode in [ord("-"), wx.WXK_SUBTRACT]:  # "-"
            if self.IsExpanded(self._current):
                self.Collapse(self._current)

        elif keyCode == wx.WXK_MENU:
            # Use the item's bounding rectangle to determine position for the event
            itemRect = self.GetBoundingRect(self._current, True)
            event = TreeEvent(wxEVT_TREE_ITEM_MENU, self.GetId())
            event._item = self._current
            # Use the left edge, vertical middle
            event._pointDrag = wx.Point(itemRect.GetX(), itemRect.GetY() + itemRect.GetHeight() / 2)
            event.SetEventObject(self)
            self.GetEventHandler().ProcessEvent(event)

        elif keyCode in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:

            if not self.IsItemEnabled(self._current):
                event.Skip()
                return

            if not event.HasModifiers():
                event = TreeEvent(wxEVT_TREE_ITEM_ACTIVATED, self.GetId())
                event._item = self._current
                event.SetEventObject(self)
                self.GetEventHandler().ProcessEvent(event)

                #if keyCode == wx.WXK_SPACE and self.GetItemType(self._current) > 0:
                #    if self.IsItem3State(self._current):
                #        checked = self.GetItem3StateValue(self._current)
                #        checked = (checked + 1) % 3
                #    else:
                #        checked = not self.IsItemChecked(self._current)
                #
                #    self.CheckItem(self._current, checked)

                if self.IsItemHyperText(self._current):
                    self.HandleHyperLink(self._current)

            # in any case, also generate the normal key event for this key,
            # even if we generated the ACTIVATED event above: this is what
            # wxMSW does and it makes sense because you might not want to
            # process ACTIVATED event at all and handle Space and Return
            # directly (and differently) which would be impossible otherwise
            event.Skip()

        elif keyCode in [wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE]:
            # check selected items
            sel = self.GetSelections()
            # do not send tree-item checked event until last item in selection
            for i in range(0, len(sel) - 1):
                self.CheckItem2(sel[i], checked=not sel[i].IsChecked(), torefresh=True)

            if sel:
                self.CheckItem(sel[-1], checked=not sel[-1].IsChecked())

        elif keyCode == wx.WXK_F2:
            sel = self.GetSelections()
            if self.HasAGWFlag(wx.TR_EDIT_LABELS) and len(sel) == 1:
                self.Edit(sel[0])

        # up goes to the previous sibling or to the last
        # of its children if it's expanded
        elif keyCode == wx.WXK_UP:
            prev = self.GetPrevSibling(self._key_current)
            if not prev:
                prev = self.GetItemParent(self._key_current)
                if prev == self.GetRootItem() and self.HasAGWFlag(TR_HIDE_ROOT):
                    return

                if prev:
                    current = self._key_current
                    # TODO: Huh?  If we get here, we'd better be the first child of our parent.  How else could it be?
                    if current == self.GetFirstChild(prev)[0] and self.IsItemEnabled(prev):
                        # otherwise we return to where we came from
                        self.DoSelectItem(prev, unselect_others, extended_select, from_key=True)
                        self._key_current = prev

            else:
                current = self._key_current

                # We are going to another parent node
                while self.IsExpanded(prev) and self.HasChildren(prev):
                    child = self.GetLastChild(prev)
                    if child:
                        prev = child
                        current = prev

                # Try to get the previous siblings and see if they are active
                while prev and not self.IsItemEnabled(prev):
                    prev = self.GetPrevSibling(prev)

                if not prev:
                    # No previous siblings active: go to the parent and up
                    prev = self.GetItemParent(current)
                    while prev and not self.IsItemEnabled(prev):
                        prev = self.GetItemParent(prev)

                if prev:
                    self.DoSelectItem(prev, unselect_others, extended_select, from_key=True)
                    self._key_current = prev

        # left arrow goes to the parent
        elif keyCode == wx.WXK_LEFT:

            prev = self.GetItemParent(self._current)
            if prev == self.GetRootItem() and self.HasAGWFlag(TR_HIDE_ROOT):
                # don't go to root if it is hidden
                prev = self.GetPrevSibling(self._current)

            if self.IsExpanded(self._current):
                self.Collapse(self._current)
            else:
                if prev and self.IsItemEnabled(prev):
                    self.DoSelectItem(prev, unselect_others, extended_select, from_key=True)

        elif keyCode == wx.WXK_RIGHT:
            # this works the same as the down arrow except that we
            # also expand the item if it wasn't expanded yet
            if self.IsExpanded(self._current) and self.HasChildren(self._current):
                child, cookie = self.GetFirstChild(self._key_current)
                if self.IsItemEnabled(child):
                    self.DoSelectItem(child, unselect_others, extended_select, from_key=True)
                    self._key_current = child
            else:
                self.Expand(self._current)
            # fall through

        elif keyCode == wx.WXK_DOWN:
            if self.IsExpanded(self._key_current) and self.HasChildren(self._key_current):

                child = self.GetNextActiveItem(self._key_current)

                if child:
                    self.DoSelectItem(child, unselect_others, extended_select, from_key=True)
                    self._key_current = child

            else:

                next = self.GetNextSibling(self._key_current)

                if not next:
                    current = self._key_current
                    while current and not next:
                        current = self.GetItemParent(current)
                        if current:
                            next = self.GetNextSibling(current)
                            if not next or not self.IsItemEnabled(next):
                                next = None

                else:
                    while next and not self.IsItemEnabled(next):
                        next = self.GetNext(next)

                if next:
                    self.DoSelectItem(next, unselect_others, extended_select, from_key=True)
                    self._key_current = next


        # <End> selects the last visible tree item
        elif keyCode == wx.WXK_END:

            last = self.GetRootItem()

            while last and self.IsExpanded(last):

                lastChild = self.GetLastChild(last)

                # it may happen if the item was expanded but then all of
                # its children have been deleted - so IsExpanded() returned
                # true, but GetLastChild() returned invalid item
                if not lastChild:
                    break

                last = lastChild

            if last and self.IsItemEnabled(last):
                self.DoSelectItem(last, unselect_others, extended_select, from_key=True)

        # <Home> selects the root item
        elif keyCode == wx.WXK_HOME:

            prev = self.GetRootItem()

            if not prev:
                return

            if self.HasAGWFlag(TR_HIDE_ROOT):
                prev, cookie = self.GetFirstChild(prev)
                if not prev:
                    return

            if self.IsItemEnabled(prev):
                self.DoSelectItem(prev, unselect_others, extended_select, from_key=True)

        # MADE BY ME: Delete item
        elif keyCode == wx.WXK_DELETE:

            parent = self.GetParent()

            if hasattr(parent, 'HandleDelete'):
                # raise deletion event to parent which then redistributes it or handles it itself
                parent.HandleDelete(self)

        # MADE BY ME: Copy item
        elif keyCode in (ord('c'), ord('C')) and event.CmdDown():

            parent = self.GetParent()

            if hasattr(parent, 'HandleCopy'):
                # raise copy event to parent which then redistributes it or handles it itself
                parent.HandleCopy(self)

        # MADE BY ME: Cut item
        elif keyCode in (ord('x'), ord('X')) and event.CmdDown():

            parent = self.GetParent()

            if hasattr(parent, 'HandleCopy'):
                # raise cut event to parent which then redistributes it or handles it itself
                parent.HandleCopy(self, cut=True)

        # MADE BY ME: Paste item
        elif keyCode in (ord('v'), ord('V')) and event.CmdDown():

            parent = self.GetParent()

            if hasattr(parent, 'HandlePaste'):
                # raise paste event to parent which then redistributes it or handles it itself
                parent.HandlePaste(self)

        else:

            if not event.HasModifiers() and ((keyCode >= ord('0') and keyCode <= ord('9')) or
                                             (keyCode >= ord('a') and keyCode <= ord('z')) or
                                             (keyCode >= ord('A') and keyCode <= ord('Z'))):

                # find the next item starting with the given prefix
                ch = chr(keyCode)
                id = self.FindItem(self._current, self._findPrefix + ch)

                if not id:
                    # no such item
                    return

                if self.IsItemEnabled(id):
                    self.SelectItem(id)
                self._findPrefix += ch

                # also start the timer to reset the current prefix if the user
                # doesn't press any more alnum keys soon -- we wouldn't want
                # to use this prefix for a new item search
                if not self._findTimer:
                    self._findTimer = TreeFindTimer(self)

                self._findTimer.Start(_DELAY, wx.TIMER_ONE_SHOT)

            else:

                event.Skip()
