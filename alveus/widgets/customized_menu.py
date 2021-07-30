import wx
from wx.lib.agw.flatmenu import FMRendererMgr, FMRenderer, FlatMenu, FlatMenuItem
from wx.lib.agw.flatmenu import FMRendererXP, FMRendererMSOffice2007, FMRendererVista
from wx.lib.agw.artmanager import ArtManager, DCSaver

import _icons as ico


class CustomFMRendererMgr(FMRendererMgr):
    def __init__(self):
        super().__init__()

        #if hasattr(self, '_alreadyInitialized'):
        #    return

        #self._alreadyInitialized = True

        #self._currentTheme = StyleDefault
        self._currentTheme = 0
        self._renderers = []
        self._renderers.append(CustomFMRenderer())
        #self._renderers.append(FMRendererXP())
        #self._renderers.append(FMRendererMSOffice2007())
        #self._renderers.append(FMRendererVista())


class CustomFMRenderer(FMRendererVista):
    def __init__(self):
        super().__init__()

        # self.menuBarFaceColour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DFACE)
        #
        # self.buttonBorderColour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVECAPTION)
        # self.buttonFaceColour = ArtManager.Get().LightColour(self.buttonBorderColour, 75)
        # self.buttonFocusBorderColour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVECAPTION)
        # self.buttonFocusFaceColour = ArtManager.Get().LightColour(self.buttonFocusBorderColour, 75)
        # self.buttonPressedBorderColour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVECAPTION)
        # self.buttonPressedFaceColour = ArtManager.Get().LightColour(self.buttonPressedBorderColour, 60)
        #
        # self.menuFocusBorderColour = wx.RED #wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVECAPTION)
        # self.menuFocusFaceColour = ArtManager.Get().LightColour(self.buttonFocusBorderColour, 75)
        # self.menuPressedBorderColour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVECAPTION)
        # self.menuPressedFaceColour = ArtManager.Get().LightColour(self.buttonPressedBorderColour, 60)
        #
        # self.menuBarFocusBorderColour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVECAPTION)
        # self.menuBarFocusFaceColour = ArtManager.Get().LightColour(self.buttonFocusBorderColour, 75)
        # self.menuBarPressedBorderColour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVECAPTION)
        # self.menuBarPressedFaceColour = ArtManager.Get().LightColour(self.buttonPressedBorderColour, 60)

    def DrawButtonColour(self, dc, rect, state, colour):
        """
        Draws a button using the Vista theme.
        :param `dc`: an instance of :class:`DC`;
        :param `rect`: the an instance of :class:`Rect`, representing the button client rectangle;
        :param integer `state`: the button state;
        :param `colour`: a valid :class:`Colour` instance.
        """

        artMgr = ArtManager.Get()

        # Keep old pen and brush
        dcsaver = DCSaver(dc)

        # same colours as used on ribbon
        outer = wx.Colour(242, 201, 88)
        inner = wx.WHITE
        top = wx.Colour(255, 227, 125)
        bottom = wx.Colour(253, 243, 204)

        bdrRect = wx.Rect(*rect)
        filRect = wx.Rect(*rect)
        filRect.Deflate(1, 1)

        r1, g1, b1 = int(top.Red()), int(top.Green()), int(top.Blue())
        r2, g2, b2 = int(bottom.Red()), int(bottom.Green()), int(bottom.Blue())
        dc.GradientFillLinear(filRect, top, bottom, wx.SOUTH)

        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(wx.Pen(outer))
        dc.DrawRoundedRectangle(bdrRect, 3)
        bdrRect.Deflate(1, 1)
        dc.SetPen(wx.Pen(inner))
        dc.DrawRoundedRectangle(bdrRect, 2)


class CustomMenu(FlatMenu):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._rendererMgr = CustomFMRendererMgr()

    def CustomPopup(self):
        if self.GetMenuItems():
            pos = wx.GetMousePosition()
            self.Popup(wx.Point(pos.x, pos.y), self.GetParent())

    # common item implementations for ease of use ----------------------------------------------------------------------
    def AppendCollapseItem(self, method, bind_to=None):
        return self.AppendGenericItem('Collapse all', method, bitmap=ico.collapse_16x16.GetBitmap(), bind_to=bind_to)

    def AppendCopyItem(self, method, bind_to=None):
        return self.AppendGenericItem('Copy', method, bitmap=ico.copy_16x16.GetBitmap(), bind_to=bind_to)

    def AppendCutItem(self, method, bind_to=None):
        return self.AppendGenericItem('Cut', method, bitmap=ico.cut_16x16.GetBitmap(), bind_to=bind_to)

    def AppendDeleteItem(self, method, bind_to=None):
        return self.AppendGenericItem('Delete', method, bitmap=ico.delete_16x16.GetBitmap(), bind_to=bind_to)

    def AppendExpandItem(self, method, bind_to=None):
        return self.AppendGenericItem('Expand all', method, bitmap=ico.expand_16x16.GetBitmap(), bind_to=bind_to)

    def AppendExportExcel(self, method, bind_to=None):
        return self.AppendGenericItem('Export to Excel', method, bitmap=ico.export_spreadsheet_16x16.GetBitmap(), bind_to=bind_to)

    def AppendGenericItem(self, text, method, bitmap=wx.NullBitmap, bind_to=None):
        if bind_to is None:
            bind_to = self.GetParent()

        item = CustomMenuItem(self, wx.ID_ANY, text, normalBmp=bitmap)
        self.AppendItem(item)
        bind_to.Bind(wx.EVT_MENU, method, item)

        return item

    def AppendOpenItem(self, method, bind_to=None):
        return self.AppendGenericItem('Open', method, bitmap=ico.settings_page_16x16.GetBitmap(), bind_to=bind_to)

    def AppendPasteItem(self, method, bind_to=None):
        return self.AppendGenericItem('Paste', method, bitmap=ico.paste_16x16.GetBitmap(), bind_to=bind_to)


class CustomMenuItem(FlatMenuItem):
    def __init__(self, parent, id=wx.ID_SEPARATOR, label="", helpString="", kind=wx.ITEM_NORMAL, subMenu=None,
                 normalBmp=wx.NullBitmap, disabledBmp=wx.NullBitmap, hotBmp=wx.NullBitmap):

        super().__init__(parent, id=id, label=label, helpString=helpString, kind=kind, subMenu=subMenu,
                         normalBmp=normalBmp, disabledBmp=disabledBmp, hotBmp=hotBmp)

    def SetBitmap(self, bmp):
        self._normalBmp = bmp
