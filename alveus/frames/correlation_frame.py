import copy
from pubsub import pub
import wx
import wx.grid
from wx.lib.agw.customtreectrl import EVT_TREE_ITEM_CHECKED

from _ids import ID_POLYGON
import _icons as ico
from frames.frame_design import ObjectFrame, GAP
from frames.property_panels import SelectionTree


class CorrelationSelectionTree(SelectionTree):
    def __init__(self, parent, object_menu_page):
        super().__init__(parent, object_menu_page)

    def GetIndices(self):
        items = self.GetCheckedItems()
        indices = []
        for i, item in enumerate(items):
            if item.IsChecked() and not item.HasChildren():
                indices.append(i)

        return indices

    def CheckAllItems(self, parent=None):
        if parent is None:
            parent = self.tree.GetRootItem()

        child, cookie = self.tree.GetFirstChild(parent)

        while child:
            self.tree.CheckItem2(child, checked=True, torefresh=True)

            self.CheckAllItems(child)
            child, cookie = self.tree.GetNextChild(parent, cookie)


class CorrelationFrame(ObjectFrame):
    def __init__(self, parent, title, mgr, object_menu_page, items, types):
        super().__init__(parent=parent, title=title)

        self._items = items
        self._types = types

        self._mgr = mgr
        self._object_menu_page = object_menu_page
        self._correlation, self._labels = mgr.GetCorrelationMatrix()

        self.splitter = wx.SplitterWindow(self.custom, wx.ID_ANY, style=wx.SP_THIN_SASH | wx.SP_LIVE_UPDATE)
        self.selection = CorrelationSelectionTree(self.splitter, self._object_menu_page)
        self.properties = wx.Panel(self.splitter)
        self.splitter.SplitVertically(self.selection, self.properties, 200)
        self.grid = wx.grid.Grid(self.properties)

        self.custom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.InitUI()
        self.Load()
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_TREE_ITEM_CHECKED, self.OnTreeItemChecked, self.selection.tree)
        self.apply_button.Bind(wx.EVT_BUTTON, self.OnApplyButton)
        self.ok_button.Bind(wx.EVT_BUTTON, self.OnOKButton)

    def InitUI(self):
        self.SetIcon(ico.correlation_16x16.GetIcon())

        # selection tree -----------------------------------------------------------------------------------------------
        self.selection.Populate(self._items, self._types)
        self.selection.CheckAllItems()

        n = len(self._correlation)
        self.grid.CreateGrid(n, n)
        self.grid.SetColLabelTextOrientation(wx.VERTICAL)

        # disable lower half of the correlation matrix (including diagonal)
        n = len(self._correlation)
        for j in range(0, n):
            for i in range(j, n):
                self.grid.SetReadOnly(i, j, True)
                self.grid.SetCellBackgroundColour(i, j, wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))

        # change row and column options
        for i in range(0, n):
            # labels
            self.grid.SetColLabelValue(i, self._labels[i])
            self.grid.SetRowLabelValue(i, self._labels[i])

            # sizes
            self.grid.SetColSize(i, 30)
            self.grid.SetRowSize(i, 30)

        self.grid.SetColLabelSize(wx.grid.GRID_AUTOSIZE)

        # sizing -------------------------------------------------------------------------------------------------------
        self.custom_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, GAP)
        self.custom.SetSizer(self.custom_sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.grid, 1, wx.EXPAND)
        self.properties.SetSizer(sizer)
        self.custom_sizer.Fit(self.custom)

        self.Realize()

    def OnClose(self, event):
        pass

    def OnTreeItemChecked(self, event):
        indices = self.selection.GetIndices()
        n = len(self._correlation)
        for i in range(0, n):
            if i in indices:
                self.grid.ShowCol(i)
                self.grid.ShowRow(i)
            else:
                self.grid.HideCol(i)
                self.grid.HideRow(i)

    def OnApplyButton(self, event):
        return self.Save()

    def OnOKButton(self, event):
        saved = self.OnApplyButton(None)
        if saved:
            self.Close(True)

    def Load(self):
        # load upper half of the correlation matrix
        n = len(self._correlation)
        for j in range(0, n):
            for i in range(0, j):
                self.grid.SetCellValue(i, j, str(self._correlation[i][j]))

                # set alignment
                self.grid.SetCellAlignment(i, j, wx.ALIGN_CENTER, wx.ALIGN_CENTER)

            # Fill diagonal with ones
            self.grid.SetCellValue(j, j, str(1))
            self.grid.SetCellAlignment(j, j, wx.ALIGN_CENTER, wx.ALIGN_CENTER)

    def Save(self):
        # Save upper half of the grid to the upper and lower half of the correlation matrix
        correlation = copy.deepcopy(self._correlation)
        n = len(correlation)
        for j in range(1, n):
            for i in range(0, j):
                try:
                    value = float(self.grid.GetCellValue(i, j))
                    if -1. <= value <= 1.:
                        correlation[i][j] = value
                        correlation[j][i] = value
                    else:
                        msg = 'coefficient ({},{}) must be in the range -1 to 1'.format(i, j)
                        box = wx.MessageDialog(self, msg, caption='Value Error')
                        box.ShowModal()
                        box.Destroy()
                        return False

                except ValueError:
                    msg = 'coefficient ({},{}) must be a number'.format(i, j)
                    box = wx.MessageDialog(self, msg, caption='Type Error')
                    box.ShowModal()
                    box.Destroy()
                    return False

        self._mgr.SetCorrelationMatrix(correlation)
        return True


class EntityCorrelationFrame(CorrelationFrame):
    def __init__(self, parent, mgr, object_menu_page):

        items = (object_menu_page.subsurface,)
        types = (ID_POLYGON,)

        super().__init__(parent, 'Correlated polygons', mgr, object_menu_page, items, types)

    def OnClose(self, event):
        pub.sendMessage('entity_correlation_closed')

        event.Skip()


class VariableCorrelationFrame(CorrelationFrame):
    def __init__(self, parent, mgr, object_menu_page):

        items = (object_menu_page.statics, object_menu_page.scalers)
        types = ('scalers', 'statics')

        super().__init__(parent, 'Correlated variables', mgr, object_menu_page, items, types)

    def OnClose(self, event):
        pub.sendMessage('variable_correlation_closed')

        event.Skip()
