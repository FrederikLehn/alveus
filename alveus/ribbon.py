# generic imports ------------------------------------------------------------------------------------------------------
import types

# wxPython imports -----------------------------------------------------------------------------------------------------
import wx.lib.agw.ribbon as rb
from wx.lib.agw.gradientbutton import GradientButton
from wx.lib.agw.ribbon.art import RIBBON_BAR_SHOW_PAGE_LABELS, RIBBON_BAR_SHOW_PAGE_ICONS

# Alveus imports -------------------------------------------------------------------------------------------------------
from _ids import *
import _icons as ico
from widgets.customized_menu import CustomMenuItem, CustomMenu


# ----------------------------------------------------------------------------------------------------------------------

class Ribbon(rb.RibbonBar):
    def __init__(self, parent):
        super().__init__(parent=parent, id=wx.ID_ANY, agwStyle=rb.RIBBON_BAR_DEFAULT_STYLE | rb.RIBBON_BAR_SHOW_PANEL_EXT_BUTTONS)

        # File tab------------------------------------------------------------------------------------------------------
        self.file_page = RibbonFileTab(self)
        self.file_menu = RibbonFileMenu()
        self.file_page.Bind(wx.EVT_BUTTON, self.OnFileTabMenu)

        # Home tab------------------------------------------------------------------------------------------------------
        home = rb.RibbonPage(self, wx.ID_ANY, 'Home')

        window_panel = rb.RibbonPanel(home, wx.ID_ANY, 'Window')
        self.window = rb.RibbonButtonBar(window_panel)
        self.window.AddHybridButton(ID_WINDOW, 'Window', ico.window_32x32.GetBitmap(), 'Add new window')
        self.window.AddSimpleButton(ID_WINDOW_REFRESH, 'Refresh', ico.window_refresh_32x32.GetBitmap(), 'Refresh active window')
        self.window.AddToggleButton(ID_WINDOW_PRESENT, 'Present', ico.window_32x32.GetBitmap(), 'Change to presentation mode')

        generic_chart_panel = rb.RibbonPanel(home, wx.ID_ANY, 'Generic charts')
        self.generic_chart = rb.RibbonButtonBar(generic_chart_panel)
        self.generic_chart.AddSimpleButton(ID_CHART_CARTESIAN, 'Cartesian', ico.cartesian_chart_32x32.GetBitmap(), 'Add new cartesian chart')
        self.generic_chart.AddSimpleButton(ID_CHART_STACKED, 'Stacked', ico.stacked_chart_32x32.GetBitmap(), 'Add new stacked chart')
        self.generic_chart.AddSimpleButton(ID_CHART_BAR, 'Bar', ico.bar_chart_32x32.GetBitmap(), 'Add new bar chart')
        self.generic_chart.AddSimpleButton(ID_CHART_BUBBLE, 'Bubble', ico.bubble_chart_32x32.GetBitmap(), 'Add new bubble chart')
        self.generic_chart.AddSimpleButton(ID_CHART_HISTOGRAM, 'Histogram', ico.histogram_chart_32x32.GetBitmap(), 'Add new histogram')
        self.generic_chart.AddSimpleButton(ID_CHART_MAP, 'Map', ico.map_chart_32x32.GetBitmap(), 'Add new map')
        self.generic_chart.AddSimpleButton(ID_CHART_3D, '3D', ico.threeD_chart_32x32.GetBitmap(), 'Add 3D chart')

        custom_chart_panel = rb.RibbonPanel(home, wx.ID_ANY, 'Custom charts')
        self.custom_chart = rb.RibbonButtonBar(custom_chart_panel)
        self.custom_chart.AddSimpleButton(ID_CHART_FIT, 'Fits', ico.fit_chart_32x32.GetBitmap(), 'Add new fit chart')
        self.custom_chart.AddSimpleButton(ID_CHART_TREND, 'Trends', ico.trend_chart_32x32.GetBitmap(), 'Add new trend chart')
        self.custom_chart.AddSimpleButton(ID_CHART_INCREMENT, 'Increments', ico.increment_chart_32x32.GetBitmap(), 'Add new increment chart')
        self.custom_chart.AddSimpleButton(ID_CHART_PROFILES, 'Profiles', ico.profiles_chart_32x32.GetBitmap(), 'Add new profiles chart')

        export_panel = rb.RibbonPanel(home, wx.ID_ANY, 'Export')
        self.export = rb.RibbonButtonBar(export_panel)
        self.export.AddSimpleButton(ID_EXPORT_EXCEL, 'Export', ico.export_spreadsheet_32x32.GetBitmap(), 'Open profile export frame')

        correlation_panel = rb.RibbonPanel(home, wx.ID_ANY, 'Correlation')
        self.correlation = rb.RibbonButtonBar(correlation_panel)
        self.correlation.AddSimpleButton(ID_CORRELATION_ENT, 'Entity', ico.correlation_entity_32x32.GetBitmap(), 'Open entity correlation frame')
        self.correlation.AddSimpleButton(ID_CORRELATION_VAR, 'Variable', ico.correlation_variable_32x32.GetBitmap(), 'Open variable correlation frame')

        summary_panel = rb.RibbonPanel(home, wx.ID_ANY, 'Summary')
        self.summary = rb.RibbonButtonBar(summary_panel)
        self.summary.AddSimpleButton(ID_SUMMARY, 'Summary', ico.summary_32x32.GetBitmap(), 'Add new summary variable')

        # Entities tab -------------------------------------------------------------------------------------------------
        entities = rb.RibbonPage(self, wx.ID_ANY, 'Entities')

        folder_panel = rb.RibbonPanel(entities, wx.ID_ANY, 'Folders')
        self.folder = rb.RibbonButtonBar(folder_panel)
        self.folder.AddSimpleButton(ID_FOLDER, 'Folder', ico.folder_closed_32x32.GetBitmap(), 'Add new folder')

        portfolio_panel = rb.RibbonPanel(entities, wx.ID_ANY, 'Portfolio')
        self.portfolio = rb.RibbonButtonBar(portfolio_panel)
        self.portfolio.AddSimpleButton(ID_ANALOGUE, 'Analogue', ico.analogue_32x32.GetBitmap(), 'Add new analogue')
        self.portfolio.AddSimpleButton(ID_TYPECURVE, 'Typecurve', ico.trend_chart_32x32.GetBitmap(), 'Add new typecurve')
        self.portfolio.AddSimpleButton(ID_SCALING, 'Scaling', ico.scaling_chart_32x32.GetBitmap(), 'Add new scaling')

        subsurface_panel = rb.RibbonPanel(entities, wx.ID_ANY, 'Subsurface')
        self.subsurface = rb.RibbonButtonBar(subsurface_panel)
        self.subsurface.AddSimpleButton(ID_RESERVOIR, 'Reservoir', ico.reservoir_32x32.GetBitmap(), 'Add new reservoir')
        self.subsurface.AddSimpleButton(ID_THEME, 'Theme', ico.theme_32x32.GetBitmap(), 'Add new theme')
        self.subsurface.AddSimpleButton(ID_POLYGON, 'Polygon', ico.polygon_32x32.GetBitmap(), 'Add new polygon')
        self.subsurface.AddSimpleButton(ID_PRODUCER, 'Producer', ico.producer_oil_gas_32x32.GetBitmap(), 'Add new producer')
        self.subsurface.AddSimpleButton(ID_INJECTOR, 'Injector', ico.injector_wag_32x32.GetBitmap(), 'Add new injector')

        facility_panel = rb.RibbonPanel(entities, wx.ID_ANY, 'Facility')
        self.facility = rb.RibbonButtonBar(facility_panel)
        self.facility.AddSimpleButton(ID_PLATFORM, 'Platform', ico.platforms_32x32.GetBitmap(), 'Add new platform')
        self.facility.AddSimpleButton(ID_PROCESSOR, 'Processor', ico.processor_32x32.GetBitmap(), 'Add new processor')
        self.facility.AddSimpleButton(ID_PIPELINE, 'Pipeline', ico.pipeline_32x32.GetBitmap(), 'Add new pipeline')

        concession_panel = rb.RibbonPanel(entities, wx.ID_ANY, 'Concession')
        self.concession = rb.RibbonButtonBar(concession_panel)
        self.concession.AddSimpleButton(ID_FIELD, 'Field', ico.field_32x32.GetBitmap(), 'Add new field')
        self.concession.AddSimpleButton(ID_BLOCK, 'Block', ico.block_32x32.GetBitmap(), 'Add new block')

        simulation_panel = rb.RibbonPanel(entities, wx.ID_ANY, 'Simulation')
        self.simulation = rb.RibbonButtonBar(simulation_panel)
        self.simulation.AddSimpleButton(ID_PROJECT, 'Project', ico.project_32x32.GetBitmap(), 'Add new project')
        self.simulation.AddSimpleButton(ID_HISTORY, 'History', ico.history_match_32x32.GetBitmap(), 'Add new history')
        self.simulation.AddSimpleButton(ID_SCENARIO, 'Scenario', ico.scenario_32x32.GetBitmap(), 'Add new scenario')
        self.simulation.AddSimpleButton(ID_PREDICTION, 'Prediction', ico.prediction_32x32.GetBitmap(), 'Add new prediction')

        self.ChangeArtProvider()
        self.Realize()

    # ==================================================================================================================
    # Events
    # ==================================================================================================================
    # comes from: https://github.com/wxWidgets/wxPython/blob/master/demo/agw/FlatMenu.py (26-08-2019)
    # lines: 538-561
    def OnFileTabMenu(self, event):
        button = event.GetEventObject()
        button_size = button.GetSize()
        button_pos = button.GetPosition()
        button_pos = button.GetParent().ClientToScreen(button_pos)
        self.file_menu.SetOwnerHeight(button_size.y)
        self.file_menu.Popup(wx.Point(button_pos.x, button_pos.y), self)

    # ==================================================================================================================
    # External Methods
    # ==================================================================================================================
    def EnableButtons(self, state, entity_mgr=None):
        """
        Enables or disables ribbon buttons. If state is False, all buttons are disabled, if state is True, the enabling
        is based on certain criteria from the entity_mgr w.r.t. lower hierarchy entities not being enabled if no
        higher level entity is available.
        :param state: bool
        :param entity_mgr: class EntityManager
        :return:
        """
        # Enable file menu
        self.file_menu.save.Enable(state)
        self.file_menu.save_as.Enable(state)
        self.file_menu.close.Enable(state)
        self.file_menu.settings.Enable(state)

        # Enable ribbon
        self.folder.EnableButton(ID_FOLDER, state)

        self.window.EnableButton(ID_WINDOW, state)
        self.window.EnableButton(ID_WINDOW_REFRESH, state)
        self.window.EnableButton(ID_WINDOW_PRESENT, state)

        self.generic_chart.EnableButton(ID_CHART_CARTESIAN, state)
        self.generic_chart.EnableButton(ID_CHART_STACKED, state)
        self.generic_chart.EnableButton(ID_CHART_BAR, state)
        self.generic_chart.EnableButton(ID_CHART_BUBBLE, state)
        self.generic_chart.EnableButton(ID_CHART_HISTOGRAM, state)
        self.generic_chart.EnableButton(ID_CHART_MAP, state)
        self.generic_chart.EnableButton(ID_CHART_3D, state)

        # TODO: Once charts are created, replace false with state
        self.custom_chart.EnableButton(ID_CHART_FIT, state)
        self.custom_chart.EnableButton(ID_CHART_TREND, False)
        self.custom_chart.EnableButton(ID_CHART_INCREMENT, False)
        self.custom_chart.EnableButton(ID_CHART_PROFILES, False)

        self.export.EnableButton(ID_EXPORT_EXCEL, state)

        self.correlation.EnableButton(ID_CORRELATION_ENT, state)
        self.correlation.EnableButton(ID_CORRELATION_VAR, state)

        self.summary.EnableButton(ID_SUMMARY, state)

        # Entities tab -------------------------------------------------------------------------------------------------
        # analogues and typecurves
        self.portfolio.EnableButton(ID_ANALOGUE, state)
        self.portfolio.EnableButton(ID_SCALING, state)

        if state:
            if entity_mgr.GetAnalogues():
                self.portfolio.EnableButton(ID_TYPECURVE, state)

            else:
                self.portfolio.EnableButton(ID_TYPECURVE, False)

        else:
            self.portfolio.EnableButton(ID_TYPECURVE, state)

        # subsurface (reservoirs, themes, polygons, producers and injectors)
        self.subsurface.EnableButton(ID_RESERVOIR, state)

        if state:
            if entity_mgr.GetReservoirs():
                self.subsurface.EnableButton(ID_THEME, state)

                if entity_mgr.GetThemes():
                    self.subsurface.EnableButton(ID_POLYGON, state)

                    if entity_mgr.GetPolygons():
                        self.subsurface.EnableButton(ID_PRODUCER, state)
                        self.subsurface.EnableButton(ID_INJECTOR, state)

                    else:
                        self.subsurface.EnableButton(ID_PRODUCER, False)
                        self.subsurface.EnableButton(ID_INJECTOR, False)

                else:
                    self.subsurface.EnableButton(ID_POLYGON, False)

            else:
                self.subsurface.EnableButton(ID_THEME, False)

        else:
            self.subsurface.EnableButton(ID_THEME, state)
            self.subsurface.EnableButton(ID_POLYGON, state)
            self.subsurface.EnableButton(ID_PRODUCER, state)
            self.subsurface.EnableButton(ID_INJECTOR, state)

        # facilities (platforms, processors and pipelines)
        self.facility.EnableButton(ID_PLATFORM, state)
        self.facility.EnableButton(ID_PIPELINE, state)

        if state:
            if entity_mgr.GetPlatforms():
                self.facility.EnableButton(ID_PROCESSOR, state)

            else:
                self.facility.EnableButton(ID_PROCESSOR, False)

        else:
            self.facility.EnableButton(ID_PROCESSOR, state)

        # concessions (fields and blocks)
        self.concession.EnableButton(ID_FIELD, state)
        self.concession.EnableButton(ID_BLOCK, state)

        # projects (projects, histories, scenarios and predictions)
        self.simulation.EnableButton(ID_PROJECT, state)

        if state:
            if entity_mgr.GetProjects():
                self.simulation.EnableButton(ID_HISTORY, state)
                self.simulation.EnableButton(ID_SCENARIO, state)

                if entity_mgr.GetScenarios():
                    self.simulation.EnableButton(ID_PREDICTION, state)

                else:
                    self.simulation.EnableButton(ID_PREDICTION, False)

            else:
                self.simulation.EnableButton(ID_HISTORY, False)
                self.simulation.EnableButton(ID_SCENARIO, False)

        else:
            self.simulation.EnableButton(ID_HISTORY, state)
            self.simulation.EnableButton(ID_SCENARIO, state)
            self.simulation.EnableButton(ID_PREDICTION, state)

    # Based on: https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/ribbon/art_msw.py (16-07-2019)
    def ChangeArtProvider(self):
        art = self.GetArtProvider()

        # add changes to drawing methods
        art.DrawTab = types.MethodType(DrawTab, art)
        art.DrawPanelBackground = types.MethodType(DrawPanelBackground, art)
        art.DrawPanelBorder = types.MethodType(DrawPanelBorder, art)
        art.DrawPageBackground = types.MethodType(DrawPageBackground, art)

        # ==============================================================================================================
        # drawing distances
        # ==============================================================================================================
        art._cached_tab_separator_visibility = -10.0  # valid visibilities are in range [0, 1]
        art._tab_separation_size = 0
        art._page_border_left = 1
        art._page_border_top = 0
        art._page_border_right = 0
        art._page_border_bottom = 2
        art._panel_x_separation_size = -1
        art._panel_y_separation_size = 0
        art._cached_tab_separator = wx.NullBitmap

        # ==============================================================================================================
        # colours
        # ==============================================================================================================
        # Tabs ---------------------------------------------------------------------------------------------------------
        # sets the colour of tab labels (created by Andrea Gavana
        # art._tab_label_colour = wx.Colour(255, 255, 255)
        # Adjusted by Frederik Lehn to allow for different colour of active tab, hovered tab and passive tab
        art._tab_label_colour = wx.Colour(255, 255, 255)
        art._tab_active_label_colour = wx.Colour(0, 0, 0)
        art._tab_hover_label_colour = wx.Colour(255, 255, 255)

        # dont know
        # art._tab_separator_colour = wx.Colour(255, 0, 0)
        # art._tab_separator_gradient_colour = wx.Colour(200, 0, 0)

        # sets the colour of the active tab
        art._tab_active_background_colour = wx.Colour(255, 255, 255)
        art._tab_active_background_gradient_colour = wx.Colour(230, 230, 230)

        # sets colour of the hovered tab
        art._tab_hover_background_top_colour = wx.Colour(100, 100, 100)
        art._tab_hover_background_top_gradient_colour = wx.Colour(105, 105, 105)
        art._tab_hover_background_colour = wx.Colour(105, 105, 105)
        art._tab_hover_background_gradient_colour = wx.Colour(110, 110, 110)

        # Sets the colour behind the tabs
        art._tab_ctrl_background_brush = wx.Brush(wx.Colour(55, 55, 55))

        # sets the colour of the border around the active tabs
        art._tab_border_pen = wx.Pen(wx.Colour(55, 55, 55))

        # Panels -------------------------------------------------------------------------------------------------------
        # sets the colour of the label of the panel
        art._panel_label_colour = wx.Colour(0, 0, 0)
        art._panel_hover_label_colour = wx.Colour(0, 0, 0)
        art._panel_minimised_label_colour = wx.Colour(0, 0, 0)

        # don't know
        # art._panel_active_background_colour = wx.Colour(255, 0, 0)  # aux.COLOUR_DEFAULT
        # art._panel_active_background_gradient_colour = wx.Colour(255, 0, 0)  # aux.COLOUR_DEFAULT
        # art._panel_active_background_top_colour = wx.Colour(255, 0, 0)  # aux.COLOUR_DEFAULT
        # art._panel_active_background_top_gradient_colour = wx.Colour(255, 0, 0)  # aux.COLOUR_DEFAULT

        # sets the colour of the background of the panel label
        art._panel_label_background_brush = wx.Brush(wx.Colour(230, 230, 230))
        art._panel_hover_label_background_brush = wx.Brush(wx.Colour(230, 230, 230))

        # dont' know
        # art._panel_hover_button_background_brush = wx.Brush(wx.Colour(255, 0, 0))

        # sets the colour of the border around the panel
        art._panel_border_pen = wx.Pen(wx.Colour(143, 143, 143))
        art._panel_border_gradient_pen = wx.Pen(wx.Colour(143, 143, 143))

        # Pages --------------------------------------------------------------------------------------------------------
        # Sets the colour of the tab pages
        art._page_background_top_colour = wx.Colour(230, 230, 230)
        art._page_background_top_gradient_colour = wx.Colour(242, 242, 242)
        art._page_background_colour = wx.Colour(242, 242, 242)
        art._page_background_gradient_colour = wx.Colour(255, 255, 255)

        # sets the colour of the background of the panels when hovering on them (not the pages)
        art._page_hover_background_top_colour = art._page_background_top_colour
        art._page_hover_background_top_gradient_colour = art._page_background_top_gradient_colour
        art._page_hover_background_colour = art._page_background_colour
        art._page_hover_background_gradient_colour = art._page_background_gradient_colour

        # sets the colour of the border around the pages,
        art._page_border_pen = wx.Pen(wx.Colour(83, 83, 83))
        # introduced by Frederik Lehn to allow for a different coloured top border
        art._page_border_top_pen = wx.Pen(wx.Colour(244, 170, 0))

        # Buttons ------------------------------------------------------------------------------------------------------
        # Sets the colour of the label of a button
        art._button_bar_label_colour = wx.Colour(0, 0, 0)

        # Sets the colour when clicking on a button
        art._button_bar_active_background_top_colour = wx.Colour(255, 218, 109)
        art._button_bar_active_background_top_gradient_colour = wx.Colour(255, 218, 109)
        art._button_bar_active_background_colour = wx.Colour(255, 218, 109)
        art._button_bar_active_background_gradient_colour = wx.Colour(255, 218, 109)

        # Sets the colour when hovering on a button
        art._button_bar_hover_background_top_colour = wx.Colour(255, 227, 125)
        art._button_bar_hover_background_top_gradient_colour = wx.Colour(254, 233, 157)
        art._button_bar_hover_background_colour = wx.Colour(254, 233, 157)
        art._button_bar_hover_background_gradient_colour = wx.Colour(253, 243, 204)

        # Sets the colour of the border when clicking and hovering on a button
        art._button_bar_active_border_pen = wx.Pen(wx.Colour(194, 150, 61))
        art._button_bar_hover_border_pen = wx.Pen(wx.Colour(242, 201, 88))

        self.SetArtProvider(art)


class RibbonFileMenu(CustomMenu):
    def __init__(self):
        super().__init__()

        self.save = CustomMenuItem(self, id=wx.ID_ANY, label='Save project', helpString='', kind=wx.ITEM_NORMAL,
                                    normalBmp=ico.save_32x32.GetBitmap())

        self.save_as = CustomMenuItem(self, id=wx.ID_ANY, label='Save project as', helpString='', kind=wx.ITEM_NORMAL,
                                       normalBmp=ico.save_as_32x32.GetBitmap())

        self.open = CustomMenuItem(self, id=wx.ID_ANY, label='Open project', helpString='', kind=wx.ITEM_NORMAL,
                                    normalBmp=ico.project_open_32x32.GetBitmap())

        self.close = CustomMenuItem(self, id=wx.ID_ANY, label='Close project', helpString='', kind=wx.ITEM_NORMAL,
                                     normalBmp=ico.project_close_32x32.GetBitmap())

        self.new = CustomMenuItem(self, id=wx.ID_ANY, label='New project', helpString='', kind=wx.ITEM_NORMAL,
                                   normalBmp=wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_OTHER, wx.Size(32, 32)))

        self.settings = CustomMenuItem(self, id=wx.ID_ANY, label='Settings', helpString='', kind=wx.ITEM_NORMAL,
                                        normalBmp=ico.settings_32x32.GetBitmap())

        self.AppendItem(self.save)
        self.AppendItem(self.save_as)
        self.AppendSeparator()
        self.AppendItem(self.open)
        self.AppendItem(self.close)
        self.AppendItem(self.new)
        self.AppendSeparator()
        self.AppendItem(self.settings)


class RibbonFileTab(GradientButton):
    def __init__(self, parent):
        super().__init__(parent=parent, id=wx.ID_ANY, label='File', pos=(1, 2), size=(49, 24))
        self.GetPath = types.MethodType(GetPathGradientButton, self)

        self.SetTopStartColour(wx.Colour(236, 201, 10))
        self.SetTopEndColour(wx.Colour(250, 192, 0))
        self.SetBottomStartColour(wx.Colour(250, 192, 0))
        self.SetBottomEndColour(wx.Colour(244, 170, 0))

        self.SetPressedTopColour(wx.Colour(244, 170, 0))
        self.SetPressedBottomColour(wx.Colour(244, 170, 0))

        self.SetForegroundColour(wx.Colour(0, 0, 0))


# ======================================================================================================================
# Functions used to change the ArtProvider of the ribbon
# ======================================================================================================================
# Taken from https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/ribbon/art_msw.py (17-07-2019)
# Changes are made to lines (in the link): 993-1007 in order to remove the curved edges at the bottom of the tabs
# Changes are made to lines (in the link): 982-991 in order to remove the curved edges at the top of the tabs
# Changes are made to lines (in the link): 1023 to have black colour for active tab and white for inactive
def DrawTab(self, dc, wnd, tab):
    if tab.rect.height <= 2:
        return

    if tab.active or tab.hovered:
        if tab.active:
            background = wx.Rect(*tab.rect)
            background.SetX(background.GetX() + 2)
            background.SetY(background.GetY() + 2)
            background.SetWidth(background.GetWidth() - 4)
            background.SetHeight(background.GetHeight() - 2)

            dc.GradientFillLinear(background, self._tab_active_background_colour,
                                  self._tab_active_background_gradient_colour, wx.SOUTH)

            # TODO: active and hovered

        elif tab.hovered:
            background = wx.Rect(*tab.rect)
            background.SetX(background.GetX() + 2)
            background.SetY(background.GetY() + 2)
            background.SetWidth(background.GetWidth() - 4)
            background.SetHeight(background.GetHeight() - 3)
            h = background.GetHeight()
            background.SetHeight(background.GetHeight() / 2)
            dc.GradientFillLinear(background, self._tab_hover_background_top_colour,
                                  self._tab_hover_background_top_gradient_colour, wx.SOUTH)

            background.SetY(background.GetY() + background.GetHeight())
            background.SetHeight(h - background.GetHeight())
            dc.GradientFillLinear(background, self._tab_hover_background_colour,
                                  self._tab_hover_background_gradient_colour, wx.SOUTH)

        # Draw the outline of the tab
        dc.SetPen(self._tab_border_pen)
        dc.DrawLine(wx.Point(1, 1), wx.Point(3, 1))
        dc.DrawLine(wx.Point(3, 1), wx.Point(3, 3))
        dc.DrawLine(wx.Point(3, 3), wx.Point(1, 3))
        dc.DrawLine(wx.Point(1, 3), wx.Point(1, 1))

    if self._flags & RIBBON_BAR_SHOW_PAGE_ICONS:
        icon = tab.page.GetIcon()

        if icon.IsOk():
            x = tab.rect.x + 4
            if self._flags & RIBBON_BAR_SHOW_PAGE_LABELS == 0:
                x = tab.rect.x + (tab.rect.width - icon.GetWidth()) / 2

            dc.DrawBitmap(icon, x, tab.rect.y + 1 + (tab.rect.height - 1 - icon.GetHeight()) / 2, True)

    if self._flags & RIBBON_BAR_SHOW_PAGE_LABELS:
        label = tab.page.GetLabel()
        if label.strip():
            dc.SetFont(self._tab_label_font)

            if tab.active:
                dc.SetTextForeground(self._tab_active_label_colour)
            elif tab.hovered:
                dc.SetTextForeground(self._tab_hover_label_colour)
            else:
                dc.SetTextForeground(self._tab_label_colour)

            dc.SetBackgroundMode(wx.TRANSPARENT)

            text_width, text_height = dc.GetTextExtent(label)
            width = tab.rect.width - 5
            x = tab.rect.x + 3

            if self._flags & RIBBON_BAR_SHOW_PAGE_ICONS:
                x += 3 + tab.page.GetIcon().GetWidth()
                width -= 3 + tab.page.GetIcon().GetWidth()

            y = tab.rect.y + (tab.rect.height - text_height) / 2

            if width <= text_width:
                dc.SetClippingRegion(x, tab.rect.y, width, tab.rect.height)
                dc.DrawText(label, x, y)
            else:
                dc.DrawText(label, x + (width - text_width) / 2 + 1, y)


# Taken from https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/ribbon/art_msw.py (16-07-2019)
# Changes are made to lines (in the link): 1691-1719 in order to remove wrap-around border of the panels
def DrawPanelBorder(self, dc, rect, primary_colour, secondary_colour):
    dc.SetPen(primary_colour)

    # draw the separating borders
    #dc.DrawLine(wx.Point(1, 2), wx.Point(1, rect.height - 1))
    dc.DrawLine(wx.Point(rect.width, 2), wx.Point(rect.width, rect.height - 1))

    # draw the top border in the page top border colour
    dc.SetPen(self._page_border_top_pen)
    dc.DrawLine(wx.Point(0, 0), wx.Point(rect.width + 1, 0))


# Taken from https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/ribbon/art_msw.py (18-07-2019)
# Changes are made to lines (in the link): 1450-1451 in order to extend panel colouring slightly to allow for a single border
# Changes are made to lines (in the link): 1480 due to an error with dc.DrawRectangleRect (changed to dc.DrawRectangle)
# notice this solution results in a slight flickering when moving the mouse between panels
def DrawPanelBackground(self, dc, wnd, rect):
    self.DrawPartialPageBackground(dc, wnd, rect, False)

    true_rect = wx.Rect(*rect)
    true_rect = self.RemovePanelPadding(true_rect)

    dc.SetFont(self._panel_label_font)
    dc.SetPen(wx.TRANSPARENT_PEN)

    has_ext_button = wnd.HasExtButton()

    if wnd.IsHovered():
        dc.SetBrush(self._panel_hover_label_background_brush)
        dc.SetTextForeground(self._panel_hover_label_colour)
    else:
        dc.SetBrush(self._panel_label_background_brush)
        dc.SetTextForeground(self._panel_label_colour)

    label_rect = wx.Rect(*true_rect)
    label = wnd.GetLabel().strip()
    clip_label = False
    label_size = wx.Size(*dc.GetTextExtent(label))

    label_rect.SetX(label_rect.GetX())  # + 1
    label_rect.SetWidth(label_rect.GetWidth())  # - 2
    label_rect.SetHeight(label_size.GetHeight() + 2)
    label_rect.SetY(true_rect.GetBottom() - label_rect.GetHeight())
    label_height = label_rect.GetHeight()

    label_bg_rect = wx.Rect(*label_rect)

    if has_ext_button:
        label_rect.SetWidth(label_rect.GetWidth() - 13)

    if label_size.GetWidth() > label_rect.GetWidth():
        # Test if there is enough length for 3 letters and ...
        new_label = label[0:3] + "..."
        label_size = wx.Size(*dc.GetTextExtent(new_label))

        if label_size.GetWidth() > label_rect.GetWidth():
            # Not enough room for three characters and ...
            # Display the entire label and just crop it
            clip_label = True
        else:
            # Room for some characters and ...
            # Display as many characters as possible and append ...
            for l in range(len(label) - 1, 3, -1):
                new_label = label[0:l] + "..."
                label_size = wx.Size(*dc.GetTextExtent(new_label))
                if label_size.GetWidth() <= label_rect.GetWidth():
                    label = new_label
                    break

    dc.DrawRectangle(label_rect)

    if clip_label:
        clip = wx.DCClipper(dc, label_rect)
        dc.DrawText(label, label_rect.GetX(), label_rect.GetY() + (label_rect.GetHeight() - label_size.GetHeight()) / 2)
    else:
        dc.DrawText(label, label_rect.GetX() + (label_rect.GetWidth() - label_size.GetWidth()) / 2,
                    label_rect.GetY() + (label_rect.GetHeight() - label_size.GetHeight()) / 2)

    if has_ext_button:
        if wnd.IsExtButtonHovered():
            dc.SetPen(self._panel_hover_button_border_pen)
            dc.SetBrush(self._panel_hover_button_background_brush)
            dc.DrawRoundedRectangle(label_rect.GetRight(), label_rect.GetBottom() - 13, 13, 13, 1)
            dc.DrawBitmap(self._panel_extension_bitmap[1], label_rect.GetRight() + 3, label_rect.GetBottom() - 10, True)
        else:
            dc.DrawBitmap(self._panel_extension_bitmap[0], label_rect.GetRight() + 3, label_rect.GetBottom() - 10, True)

    if wnd.IsHovered():
        client_rect = wx.Rect(*true_rect)
        client_rect.SetX(client_rect.GetX() + 1)
        client_rect.SetWidth(client_rect.GetWidth() - 2)
        client_rect.SetY(client_rect.GetY() + 1)
        client_rect.SetHeight( - 2 + label_height)
        self.DrawPartialPageBackground(dc, wnd, client_rect, True)

    self.DrawPanelBorder(dc, true_rect, self._panel_border_pen, self._panel_border_gradient_pen)


# Taken from https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/ribbon/art_msw.py (17-07-2019)
# Changes are made to lines (in the link): 1229-1240 in order to remove rounded pages and allow for a coloured top line
def DrawPageBackground(self, dc, wnd, rect):
    dc.SetPen(wx.TRANSPARENT_PEN)
    dc.SetBrush(self._tab_ctrl_background_brush)

    edge = wx.Rect(*rect)

    edge.SetWidth(2)
    dc.DrawRectangle(edge.GetX(), edge.GetY(), edge.GetWidth(), edge.GetHeight())

    edge.SetX(edge.GetX() + rect.GetWidth() - 2)
    dc.DrawRectangle(edge.GetX(), edge.GetY(), edge.GetWidth(), edge.GetHeight())

    edge = wx.Rect(*rect)
    edge.SetHeight(2)
    edge.SetY(edge.GetY() + rect.GetHeight() - edge.GetHeight())
    dc.DrawRectangle(edge.GetX(), edge.GetY(), edge.GetWidth(), edge.GetHeight())

    background = wx.Rect(*rect)
    background.SetX(background.GetX() + 2)
    background.SetWidth(background.GetWidth() - 4)
    background.SetHeight(background.GetHeight() - 2)

    background.SetHeight(background.GetHeight() / 5)
    dc.GradientFillLinear(background, self._page_background_top_colour,
                          self._page_background_top_gradient_colour, wx.SOUTH)

    background.SetY(background.GetY() + background.GetHeight())
    background.SetHeight(rect.GetHeight() - 2 - background.GetHeight())
    dc.GradientFillLinear(background, self._page_background_colour,
                          self._page_background_gradient_colour, wx.SOUTH)

    # draw bottom and the sides
    dc.SetPen(self._page_border_pen)
    border_points = [wx.Point() for i in range(4)]
    border_points[0] = wx.Point(0, 0)  # upper left
    border_points[1] = wx.Point(0, rect.height - 1)  # lower left
    border_points[2] = wx.Point(rect.width + 1, rect.height - 1)  # lower right
    border_points[3] = wx.Point(rect.width + 1, 0)  # upper right corner
    dc.DrawLines(border_points, rect.x, rect.y)

    # draw top line
    dc.SetPen(self._page_border_top_pen)
    dc.DrawLine(border_points[0], border_points[3])


# Taken from https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/gradientbutton.py (17-07-2019)
# Changes are made to line (in the link): 476-489 in order to remove the rounding of the button (added zero radius)
def GetPathGradientButton(self, gc, rc, r):
    x, y, w, h = rc
    r = 0
    path = gc.CreatePath()
    path.AddRoundedRectangle(x, y, w, h, r)
    path.CloseSubpath()
    return path
