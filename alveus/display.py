# generic imports ------------------------------------------------------------------------------------------------------
import math
from pubsub import pub

# AUI design imports ---------------------------------------------------------------------------------------------------
import wx.lib.agw.aui as aui
from wx.lib.agw.aui.aui_constants import *
from wx.lib.agw.aui.aui_utilities import BitmapFromBits, StepColour, IndentPressedBitmap, ChopText
from wx.lib.agw.aui.aui_utilities import GetBaseColour, TakeScreenShot
from wx.lib.agw.aui.aui_utilities import CopyAttributes
from wx.lib.agw.aui.tabart import AuiCommandCapture

# Alveus imports -------------------------------------------------------------------------------------------------------
from _ids import *
from frames.frame_design import PropertySizer
from frames.property_panels import PropertyBitmapComboBox
from variable_mgr import ShowData, ShowUncertainty, SplitBy, GroupBy, ColourBy
from charts import CartesianChartPanel, StackedChartPanel, BarChartPanel, BubbleChartPanel, HistogramChartPanel, MapChartPanel, ThreeDChartPanel


# ======================================================================================================================
# Option bar used to control additional input to the charts
# ======================================================================================================================
class OptionsBar(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.data = PropertyBitmapComboBox(self, ShowData())
        self.uncertainty = PropertyBitmapComboBox(self, ShowUncertainty())
        self.split = PropertyBitmapComboBox(self, SplitBy())
        self.group = PropertyBitmapComboBox(self, GroupBy())
        self.colour = PropertyBitmapComboBox(self, ColourBy())

        data_sizer = PropertySizer(1, 2)
        uncertainty_sizer = PropertySizer(1, 2)
        split_sizer = PropertySizer(1, 2)
        group_sizer = PropertySizer(1, 2)
        colour_sizer = PropertySizer(1, 2)
        data_sizer.AddCtrl(self, self.data)
        uncertainty_sizer.AddCtrl(self, self.uncertainty)
        split_sizer.AddCtrl(self, self.split)
        group_sizer.AddCtrl(self, self.group)
        colour_sizer.AddCtrl(self, self.colour)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(data_sizer,        0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 10)
        h_sizer.Add(uncertainty_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 10)
        h_sizer.Add(split_sizer,       0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 10)
        h_sizer.Add(group_sizer,       0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 10)
        h_sizer.Add(colour_sizer,      0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 10)

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        v_sizer.Add(h_sizer, 0, wx.ALL, 5)

        self.SetSizer(v_sizer)

    def DisableCtrls(self):
        self.EnableCtrls(False)
        self.Set(-1, -1, -1, -1, -1)

    def EnableCtrls(self, state):
        self.data.Enable(state)
        self.uncertainty.Enable(state)
        self.split.Enable(state)
        self.group.Enable(state)
        self.colour.Enable(state)

    def Get(self):
        return self.data.GetProperty(), \
               self.uncertainty.GetProperty(), \
               self.split.GetProperty(), \
               self.group.GetProperty(), \
               self.colour.GetProperty()

    def GetColourBy(self):
        return self.colour.GetProperty()

    def GetGroupBy(self):
        return self.group.GetProperty()

    def GetShowData(self):
        return self.data.GetProperty()

    def GetShowUncertainty(self):
        return self.uncertainty.GetProperty()

    def GetSplitBy(self):
        return self.split.GetProperty()

    def Set(self, show_data, show_uncertainty, split_by, group_by, colour_by):
        self.data.SetProperty(show_data)
        self.uncertainty.SetProperty(show_uncertainty)
        self.split.SetProperty(split_by)
        self.group.SetProperty(group_by)
        self.colour.SetProperty(colour_by)

    def SetState(self, chart):
        self.data.Enable(chart.IncludesData())
        self.uncertainty.Enable(chart.IncludesUncertainty())
        self.split.Enable(chart.IncludesSplit())
        self.group.Enable(chart.IncludesGroup())
        self.colour.Enable(chart.IncludesColour())
        self.Set(*chart.GetState())


# ======================================================================================================================
# Display control
# ======================================================================================================================
class Display(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self._active_window = None  # index (used for self.GetPage(index))

        # Set up AUI manager and notebook ------------------------------------------------------------------------------
        aui_panel = wx.Panel(self)
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(aui_panel)
        aui_panel.SetMinSize(wx.Size(500, 0))

        self.notebook = DisplayNotebook(aui_panel)
        self.notebook.SetName('display_notebook')  # used for persistence
        self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().Name('display').CenterPane().PaneBorder(False))
        self._mgr.Update()

        # set options bar ----------------------------------------------------------------------------------------------
        self.options_bar = OptionsBar(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(aui_panel, 1, wx.EXPAND)
        sizer.Add(self.options_bar, 0, wx.EXPAND)

        self.SetSizer(sizer)
        self.SetMinSize(wx.Size(450, 0))

        # events -------------------------------------------------------------------------------------------------------

        # PyPubSub -----------------------------------------------------------------------------------------------------
        pub.subscribe(self.PageClicked, 'template_clicked')

    # ==================================================================================================================
    # External functions
    # ==================================================================================================================
    def AddChart(self, window, chart):
        self.GetActiveWindow().AddChart(chart)

        if not window.AllowSplit():
            self.notebook.SetPageText(self._active_window, window.GetLabel())
            self.notebook.SetPageBitmap(self._active_window, window.GetBitmap())

        self._mgr.Update()

    def AddWindow(self, window):
        count = self.GetPageCount()

        self.notebook.AddPage(DisplayWindow(self.notebook, window), window.GetLabel(), bitmap=window.GetBitmap())
        self.notebook.SetSelection(count)

        self._active_window = count

    def Clear(self):
        for i in range(self.GetPageCount()):
            self.notebook.DeletePage(i)

    def ClosePage(self, idx):
        self.notebook.DeletePage(idx)

    def DeleteChart(self, window_id, chart_id):
        window = self.GetWindow(self.GetWindowIndex(window_id))
        if window is not None:
            window.DeleteChart(chart_id)

    def EnableOptionsBar(self, state, chart=None):
        if not state:
            self.options_bar.DisableCtrls()
            return

        if chart is not None:
            self.SetState(chart)

    def GetActiveChart(self):
        window = self.GetActiveWindow()
        if window is not None:
            return window.GetActiveChart()
        else:
            return None

    def GetActiveIds(self):
        window = self.GetActiveWindow()
        if window is not None:
            return window.GetActiveIds()

    def GetActiveWindow(self):
        return self.GetWindow(self._active_window)

    def GetActiveWindowId(self):
        return self.GetWindowId(self._active_window)

    def GetActiveWindowIndex(self):
        return self._active_window

    def GetPageCount(self):
        return self.notebook.GetPageCount()

    def GetState(self):
        return self.options_bar.Get()

    def GetWindow(self, idx):
        if (idx is not None) and (idx < self.GetPageCount()):
            return self.notebook.GetPage(idx)

    def GetWindowId(self, idx):
        window = self.GetWindow(idx)
        if window is not None:
            return window.GetWindowId()

    def GetWindowIndex(self, id_):
        for i in range(self.GetPageCount()):
            page = self.notebook.GetPage(i)

            if page.GetWindowId() == id_:
                return i

    def SetActiveChart(self, window_id, chart_id):
        self._active_window = self.GetWindowIndex(window_id)
        self.GetActiveWindow().SetActiveChart(chart_id)

    def SetActiveWindow(self, idx):
        self._active_window = idx

    def SetPageText(self, window):
        index = self.GetWindowIndex(window.GetId())
        if index is not None:
            self.notebook.SetPageText(index, window.GetLabel())

    def SetSelection(self, idx):
        self.notebook.SetSelection(idx)

    def SetState(self, chart):
        self.options_bar.SetState(chart)

    # PyPubSub receivers -----------------------------------------------------------------------------------------------
    def PageClicked(self, template_id):
        self.notebook.SetSelection(template_id)


class DisplayWindow(wx.Panel):
    def __init__(self, parent, window):
        super().__init__(parent)

        self._charts = {}

        # ids related to unique charts and keeping track of active chart
        self._id = window.GetId()
        self._active_chart = None

        # layout
        self._allow_split = window.AllowSplit()
        self._row = 1
        self._col = 1

        # sizing
        self.panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.chart_sizer = wx.GridSizer(self._row, self._col, 1)

        self.panel_sizer.Add(self.chart_sizer, 1, wx.EXPAND | wx.ALL, 1)
        self.SetSizer(self.panel_sizer)

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_LEFT_UP, self.OnClick)

    # events -----------------------------------------------------------------------------------------------------------
    def OnClick(self, event):
        pub.sendMessage('template_clicked', template_id=self._id)

    # external methods -------------------------------------------------------------------------------------------------
    def AddChart(self, chart):
        self.AppendChart(chart)
        self.AdjustLayout()
        self.SetBackgroundColour(wx.WHITE)

    def AllowSplit(self):
        return self._allow_split or not len(self._charts)

    def DeleteChart(self, id_):
        self._charts[id_].Destroy()
        del self._charts[id_]

    def GetActiveChart(self):
        return self.GetChart(self._active_chart)

    def GetActiveIds(self):
        chart = self.GetActiveChart()
        if chart is not None:
            return chart.GetIds()

    def GetChart(self, chart_id):
        try:
            return self._charts[chart_id]
        except KeyError:
            return None

    def GetCharts(self):
        return self._charts.values()

    def GetWindowId(self):
        return self._id

    def ReplaceCharts(self, charts):
        self._charts = {}
        for chart in charts:
            self.AppendChart(chart)

        self.AdjustLayout(delete_windows=True)

    def SetActiveChart(self, id_):
        self._active_chart = id_

    # internal methods -------------------------------------------------------------------------------------------------
    def AppendChart(self, chart):
        id_ = chart.GetId()
        chart_type = chart.GetType()
        ids = (self._id, id_)

        if chart_type == ID_CHART_CARTESIAN:

            chart_panel = CartesianChartPanel(self, *ids)

        elif chart_type == ID_CHART_STACKED:

            chart_panel = StackedChartPanel(self, *ids)

        elif chart_type == ID_CHART_BAR:

            chart_panel = BarChartPanel(self, *ids)

        elif chart_type == ID_CHART_BUBBLE:

            chart_panel = BubbleChartPanel(self, *ids)

        elif chart_type == ID_CHART_HISTOGRAM:

            chart_panel = HistogramChartPanel(self, *ids)

        elif chart_type == ID_CHART_MAP:

            chart_panel = MapChartPanel(self, *ids)

        elif chart_type == ID_CHART_3D:

            chart_panel = ThreeDChartPanel(self, *ids)

        elif chart_type == ID_CHART_FIT:

             chart_panel = CartesianChartPanel(self, *ids)

        # elif chart_type == ID_CHART_TREND:

        #    self.AppendChart(TrendChart(self, *self.GetChartID()))

        #elif chart_type == ID_CHART_INCREMENT:

        #    self.AppendChart(IncrementTrendChart(self, *self.GetChartID()))

        #elif chart_type == ID_CHART_PROFILES:

        #    self.AppendChart(ProfilesChart(self, *self.GetChartID()))

        else:

            chart_panel = None


        self._charts[id_] = chart_panel
        self._active_chart = id_

    def SetWindowLayout(self):
        n = float(len(self._charts))

        if not n:  # no charts on the window
            self._row = 1
            self._col = 1
            return

        self._row = round(math.sqrt(n))
        self._col = math.ceil(n / self._row)

    def AdjustLayout(self, delete_windows=False):
        self.SetWindowLayout()

        # redefine sizer
        self.chart_sizer.Clear(delete_windows=delete_windows)
        self.chart_sizer.SetRows(self._row)
        self.chart_sizer.SetCols(self._col)

        for chart in self._charts.values():
            self.chart_sizer.Add(chart, 0, wx.EXPAND)

        self.Layout()


class DisplayNotebook(aui.AuiNotebook):
    def __init__(self, parent):
        super().__init__(parent=parent)
        # set style
        self.SetAGWWindowStyleFlag(aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT | #aui.AUI_NB_TAB_MOVE |
                                   aui.AUI_NB_DRAW_DND_TAB | aui.AUI_NB_CLOSE_ON_ALL_TABS |
                                   aui.AUI_NB_WINDOWLIST_BUTTON | aui.AUI_NB_USE_IMAGES_DROPDOWN)

        self.ChangeTabArt()
        self.ChangeDockArt()

    def ChangeTabArt(self):
        art = DisplayTabArt()

        # colours ------------------------------------------------------------------------------------------------------
        art.SetBaseColour(wx.Colour(230, 230, 230))
        art._border_colour = wx.Colour(83, 83, 83)
        art._border_pen = wx.Pen(wx.Colour(83, 83, 83))
        art._base_colour_brush = wx.Brush(wx.Colour(239, 164, 35))

        art._background_top_colour = wx.Colour(83, 83, 83)
        art._background_bottom_colour = wx.Colour(83, 83, 83)

        art._tab_top_start_colour = wx.Colour(246, 205, 25)
        art._tab_top_end_colour = wx.Colour(242, 185, 36)
        art._tab_bottom_start_colour = wx.Colour(242, 185, 36)
        art._tab_bottom_end_colour = wx.Colour(239, 164, 35)

        art._tab_inactive_top_colour = art._base_colour
        art._tab_inactive_bottom_colour = art._base_colour

        art._tab_text_colour = lambda page: page.text_colour
        art._tab_disabled_text_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)

        self.SetArtProvider(art)

    def ChangeDockArt(self):
        art = self._mgr.GetArtProvider()

        # sets the colour of the sash(s)
        art._sash_brush = wx.Brush(aui.dockart.GetBaseColour())

        # sets the colour of the background (if all tabs are closed)
        art._background_brush = wx.Brush(wx.Colour(103, 103, 104))
        art._background_gradient_colour = wx.Colour(103, 103, 104)

        # sets the colour of the border around the notebook
        art._border_pen = wx.Pen(wx.Colour(83, 83, 83))

        # NOT USED - related to a caption bar at the top of the control
        #art._active_caption_colour = wx.Colour(255, 0, 0)
        #art._active_caption_gradient_colour = wx.Colour(255, 0, 0)
        #art._inactive_caption_colour = wx.Colour(255, 0, 0)
        #art._inactive_caption_gradient_colour = wx.Colour(255, 0, 0)
        #art._gripper_brush = wx.Brush(wx.Colour(255, 0, 0))
        #art._gripper_pen1 = wx.Pen(wx.Colour(255, 0, 0))
        #art._gripper_pen2 = wx.Pen(wx.Colour(255, 0, 0))
        #art._gripper_pen3 = wx.Pen(wx.Colour(255, 0, 0))

        # sets the colour of the dock hint rectangle
        art._hint_background_colour = aui.dockart.colourHintBackground

        # sets the size of the sash
        art._sash_size = 2

        # setting AGW flags
        # note that aui.AUI_MGR_LIVE_RESIZE causes flickering (on this computer at least)
        self._mgr.SetAGWFlags(aui.AUI_MGR_DEFAULT | aui.AUI_MGR_LIVE_RESIZE)

        self._mgr.SetArtProvider(art)


# ======================================================================================================================
# Creating an ArtProvider from scratch
# ======================================================================================================================
# based on DefaultArtProvider: https://github.com/wxWidgets/wxPython/blob/master/wx/lib/agw/aui/tabart.py
# changes made to: Line 121-124 (on the website) Removed WXMAC option
# changes made to: Line 141-151 (on the website) Removed WXMAC option
# changes made to: Line 577-578 (on the website) DrawFocusRectangle caused errors
# changes made to Line 361, 364, 573, 676 (on the website) third output "dummy" removed from received output
# changes made to Line 440-460 (on the website) Made the tab square
# changes made to Line 422-427 (on the website) Made the tab border square and removed lower line
# changes made to Line 188-190 (on the website) Made additional gradient options
class DisplayTabArt(object):
    """
    Tab art provider code - a tab provider provides all drawing functionality to the :class:`~lib.agw.aui.auibook.AuiNotebook`.
    This allows the :class:`~lib.agw.aui.auibook.AuiNotebook` to have a plugable look-and-feel.
    By default, a :class:`~lib.agw.aui.auibook.AuiNotebook` uses an instance of this class called
    :class:`AuiDefaultTabArt` which provides bitmap art and a colour scheme that is adapted to the major platforms'
    look. You can either derive from that class to alter its behaviour or write a
    completely new tab art class. Call :meth:`AuiNotebook.SetArtProvider() <lib.agw.aui.auibook.AuiNotebook.SetArtProvider>` to make use this
    new tab art.
    """

    def __init__(self):
        """ Default class constructor. """

        self._normal_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self._selected_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self._selected_font.SetWeight(wx.FONTWEIGHT_NORMAL) #wx.BOLD
        self._measuring_font = self._selected_font

        self._fixed_tab_width = 100
        self._tab_ctrl_height = 0
        self._buttonRect = wx.Rect()

        self.SetDefaultColours()

        self._active_close_bmp = BitmapFromBits(nb_close_bits, 16, 16, wx.BLACK)
        self._disabled_close_bmp = BitmapFromBits(nb_close_bits, 16, 16, wx.Colour(128, 128, 128))

        self._hover_close_bmp = self._active_close_bmp
        self._pressed_close_bmp = self._active_close_bmp

        self._active_left_bmp = BitmapFromBits(nb_left_bits, 16, 16, wx.BLACK)
        self._disabled_left_bmp = BitmapFromBits(nb_left_bits, 16, 16, wx.Colour(128, 128, 128))

        self._active_right_bmp = BitmapFromBits(nb_right_bits, 16, 16, wx.BLACK)
        self._disabled_right_bmp = BitmapFromBits(nb_right_bits, 16, 16, wx.Colour(128, 128, 128))

        self._active_windowlist_bmp = BitmapFromBits(nb_list_bits, 16, 16, wx.BLACK)
        self._disabled_windowlist_bmp = BitmapFromBits(nb_list_bits, 16, 16, wx.Colour(128, 128, 128))

        self._focusPen = wx.Pen(wx.BLACK, 1, wx.USER_DASH)
        self._focusPen.SetDashes([1, 1])
        self._focusPen.SetCap(wx.CAP_BUTT)

    def SetBaseColour(self, base_colour):
        """
        Sets a new base colour.
        :param `base_colour`: an instance of :class:`Colour`.
        """

        self._base_colour = base_colour
        self._base_colour_pen = wx.Pen(self._base_colour)
        self._base_colour_brush = wx.Brush(self._base_colour)

    def SetDefaultColours(self, base_colour=None):
        """
        Sets the default colours, which are calculated from the given base colour.
        :param `base_colour`: an instance of :class:`Colour`. If defaulted to ``None``, a colour
         is generated accordingly to the platform and theme.
        """

        if base_colour is None:
            base_colour = GetBaseColour()

        self.SetBaseColour(base_colour)
        self._border_colour = StepColour(base_colour, 75)
        self._border_pen = wx.Pen(self._border_colour)

        self._background_top_colour = StepColour(self._base_colour, 90)
        self._background_bottom_colour = StepColour(self._base_colour, 170)

        self._tab_top_start_colour = self._base_colour
        self._tab_top_end_colour = self._base_colour
        self._tab_bottom_start_colour = self._base_colour
        self._tab_bottom_end_colour = self._base_colour

        self._tab_inactive_top_colour = self._base_colour
        self._tab_inactive_bottom_colour = StepColour(self._tab_inactive_top_colour, 160)

        self._tab_text_colour = lambda page: page.text_colour
        self._tab_disabled_text_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)

    def Clone(self):
        """ Clones the art object. """

        art = type(self)()
        art.SetNormalFont(self.GetNormalFont())
        art.SetSelectedFont(self.GetSelectedFont())
        art.SetMeasuringFont(self.GetMeasuringFont())

        art = CopyAttributes(art, self)
        return art

    def SetAGWFlags(self, agwFlags):
        """
        Sets the tab art flags.
        :param integer `agwFlags`: a combination of the following values:
         ==================================== ==================================
         Flag name                            Description
         ==================================== ==================================
         ``AUI_NB_TOP``                       With this style, tabs are drawn along the top of the notebook
         ``AUI_NB_LEFT``                      With this style, tabs are drawn along the left of the notebook. Not implemented yet.
         ``AUI_NB_RIGHT``                     With this style, tabs are drawn along the right of the notebook. Not implemented yet.
         ``AUI_NB_BOTTOM``                    With this style, tabs are drawn along the bottom of the notebook
         ``AUI_NB_TAB_SPLIT``                 Allows the tab control to be split by dragging a tab
         ``AUI_NB_TAB_MOVE``                  Allows a tab to be moved horizontally by dragging
         ``AUI_NB_TAB_EXTERNAL_MOVE``         Allows a tab to be moved to another tab control
         ``AUI_NB_TAB_FIXED_WIDTH``           With this style, all tabs have the same width
         ``AUI_NB_SCROLL_BUTTONS``            With this style, left and right scroll buttons are displayed
         ``AUI_NB_WINDOWLIST_BUTTON``         With this style, a drop-down list of windows is available
         ``AUI_NB_CLOSE_BUTTON``              With this style, a close button is available on the tab bar
         ``AUI_NB_CLOSE_ON_ACTIVE_TAB``       With this style, a close button is available on the active tab
         ``AUI_NB_CLOSE_ON_ALL_TABS``         With this style, a close button is available on all tabs
         ``AUI_NB_MIDDLE_CLICK_CLOSE``        Allows to close :class:`~lib.agw.aui.auibook.AuiNotebook` tabs by mouse middle button click
         ``AUI_NB_SUB_NOTEBOOK``              This style is used by :class:`~lib.agw.aui.framemanager.AuiManager` to create automatic AuiNotebooks
         ``AUI_NB_HIDE_ON_SINGLE_TAB``        Hides the tab window if only one tab is present
         ``AUI_NB_SMART_TABS``                Use Smart Tabbing, like ``Alt`` + ``Tab`` on Windows
         ``AUI_NB_USE_IMAGES_DROPDOWN``       Uses images on dropdown window list menu instead of check items
         ``AUI_NB_CLOSE_ON_TAB_LEFT``         Draws the tab close button on the left instead of on the right (a la Camino browser)
         ``AUI_NB_TAB_FLOAT``                 Allows the floating of single tabs. Known limitation: when the notebook is more or less
                                              full screen, tabs cannot be dragged far enough outside of the notebook to become floating pages
         ``AUI_NB_DRAW_DND_TAB``              Draws an image representation of a tab while dragging (on by default)
         ``AUI_NB_ORDER_BY_ACCESS``           Tab navigation order by last access time for the tabs
         ``AUI_NB_NO_TAB_FOCUS``              Don't draw tab focus rectangle
         ==================================== ==================================

        """

        self._agwFlags = agwFlags

    def GetAGWFlags(self):
        """
        Returns the tab art flags.
        :see: :meth:`~AuiDefaultTabArt.SetAGWFlags` for a list of possible return values.
        """

        return self._agwFlags

    def SetSizingInfo(self, tab_ctrl_size, tab_count, minMaxTabWidth):
        """
        Sets the tab sizing information.

        :param Size `tab_ctrl_size`: the size of the tab control area;
        :param integer `tab_count`: the number of tabs;
        :param tuple `minMaxTabWidth`: a tuple containing the minimum and maximum tab widths
         to be used when the ``AUI_NB_TAB_FIXED_WIDTH`` style is active.
        """

        self._fixed_tab_width = 100
        minTabWidth, maxTabWidth = minMaxTabWidth

        tot_width = tab_ctrl_size.x - self.GetIndentSize() - 4
        agwFlags = self.GetAGWFlags()

        if agwFlags & AUI_NB_CLOSE_BUTTON:
            tot_width -= self._active_close_bmp.GetWidth()
        if agwFlags & AUI_NB_WINDOWLIST_BUTTON:
            tot_width -= self._active_windowlist_bmp.GetWidth()

        if tab_count > 0:
            self._fixed_tab_width = tot_width / tab_count

        if self._fixed_tab_width < 100:
            self._fixed_tab_width = 100

        if self._fixed_tab_width > tot_width / 2:
            self._fixed_tab_width = tot_width / 2

        if self._fixed_tab_width > 220:
            self._fixed_tab_width = 220

        if minTabWidth > -1:
            self._fixed_tab_width = max(self._fixed_tab_width, minTabWidth)
        if maxTabWidth > -1:
            self._fixed_tab_width = min(self._fixed_tab_width, maxTabWidth)

        self._tab_ctrl_height = tab_ctrl_size.y

    def DrawBackground(self, dc, wnd, rect):
        """
        Draws the tab area background.
        :param `dc`: a :class:`DC` device context;
        :param `wnd`: a :class:`Window` instance object;
        :param Rect `rect`: the tab control rectangle.
        """

        self._buttonRect = wx.Rect()

        # draw background
        agwFlags = self.GetAGWFlags()
        if agwFlags & AUI_NB_BOTTOM:
            r = wx.Rect(rect.x, rect.y, rect.width + 2, rect.height)

        # TODO: else if (agwFlags & AUI_NB_LEFT)
        # TODO: else if (agwFlags & AUI_NB_RIGHT)
        else:  # for AUI_NB_TOP
            r = wx.Rect(rect.x, rect.y, rect.width + 2, rect.height - 3)

        dc.GradientFillLinear(r, self._background_top_colour, self._background_bottom_colour, wx.SOUTH)

        # draw base lines

        dc.SetPen(self._border_pen)
        y = rect.GetHeight()
        w = rect.GetWidth()

        if agwFlags & AUI_NB_BOTTOM:
            dc.SetBrush(wx.Brush(self._background_bottom_colour))
            dc.DrawRectangle(-1, 0, w + 2, 4)

        # TODO: else if (agwFlags & AUI_NB_LEFT)
        # TODO: else if (agwFlags & AUI_NB_RIGHT)

        else:  # for AUI_NB_TOP
            dc.SetBrush(self._base_colour_brush)
            dc.DrawRectangle(-1, y - 4, w + 2, 4)

    def DrawTab(self, dc, wnd, page, in_rect, close_button_state, paint_control=False):
        """
        Draws a single tab.
        :param `dc`: a :class:`DC` device context;
        :param `wnd`: a :class:`Window` instance object;
        :param `page`: the tab control page associated with the tab;
        :param Rect `in_rect`: rectangle the tab should be confined to;
        :param integer `close_button_state`: the state of the close button on the tab;
        :param bool `paint_control`: whether to draw the control inside a tab (if any) on a :class:`MemoryDC`.
        """

        # if the caption is empty, measure some temporary text
        caption = page.caption
        if not caption:
            caption = "Xj"

        dc.SetFont(self._selected_font)
        selected_textx, selected_texty = dc.GetMultiLineTextExtent(caption)  # dummy (removed as 3rd output)

        dc.SetFont(self._normal_font)
        normal_textx, normal_texty = dc.GetMultiLineTextExtent(caption)  # dummy (removed as 3rd output)

        control = page.control

        # figure out the size of the tab
        tab_size, x_extent = self.GetTabSize(dc, wnd, page.caption, page.bitmap,
                                             page.active, close_button_state, control)

        tab_height = self._tab_ctrl_height - 3
        tab_width = tab_size[0]
        tab_x = in_rect.x
        tab_y = in_rect.y + in_rect.height - tab_height

        caption = page.caption

        # select pen, brush and font for the tab to be drawn

        if page.active:
            dc.SetFont(self._selected_font)
            textx, texty = selected_textx, selected_texty

        else:

            dc.SetFont(self._normal_font)
            textx, texty = normal_textx, normal_texty

        if not page.enabled:
            dc.SetTextForeground(self._tab_disabled_text_colour)
            pagebitmap = page.dis_bitmap
        else:
            dc.SetTextForeground(self._tab_text_colour(page))
            pagebitmap = page.bitmap

        # create points that will make the tab outline

        clip_width = tab_width
        if tab_x + clip_width > in_rect.x + in_rect.width:
            clip_width = in_rect.x + in_rect.width - tab_x

        # since the above code above doesn't play well with WXDFB or WXCOCOA,
        # we'll just use a rectangle for the clipping region for now --
        dc.SetClippingRegion(tab_x, tab_y, clip_width + 1, tab_height - 3)

        border_points = [wx.Point() for i in range(6)]
        agwFlags = self.GetAGWFlags()

        if agwFlags & AUI_NB_BOTTOM:

            border_points[0] = wx.Point(tab_x, tab_y)
            border_points[1] = wx.Point(tab_x, tab_y + tab_height - 4)
            border_points[2] = wx.Point(tab_x, tab_y + tab_height - 4)
            border_points[3] = wx.Point(tab_x + tab_width, tab_y + tab_height - 4)
            border_points[4] = wx.Point(tab_x + tab_width, tab_y + tab_height - 4)
            border_points[5] = wx.Point(tab_x + tab_width, tab_y)

        else:  # if (agwFlags & AUI_NB_TOP)

            border_points[0] = wx.Point(tab_x, tab_y + tab_height - 3)
            border_points[1] = wx.Point(tab_x, tab_y + 1)
            border_points[2] = wx.Point(tab_x, tab_y)
            border_points[3] = wx.Point(tab_x + tab_width, tab_y)
            border_points[4] = wx.Point(tab_x + tab_width, tab_y + 1)
            border_points[5] = wx.Point(tab_x + tab_width, tab_y + tab_height - 3)

        # TODO: else if (agwFlags & AUI_NB_LEFT)
        # TODO: else if (agwFlags & AUI_NB_RIGHT)

        drawn_tab_yoff = border_points[1].y
        drawn_tab_height = border_points[0].y - border_points[1].y

        if page.active:

            # draw active tab

            # draw base background colour
            r = wx.Rect(tab_x, tab_y + 1, tab_width, tab_height - 3)

            r.x += 2
            r.y += 0
            r.width -= 2
            r.height /= 2
            r.height -= 0

            dc.SetPen(self._base_colour_pen)
            dc.SetBrush(self._base_colour_brush)
            dc.DrawRectangle(r.x, r.y, r.width, r.height)

            ## this white helps fill out the gradient at the top of the tab
            #dc.SetPen(wx.Pen(self._tab_gradient_highlight_colour))
            #dc.SetBrush(wx.Brush(self._tab_gradient_highlight_colour))
            #dc.DrawRectangle(r.x, r.y, r.width, r.height)

            #r.height /= 2

            top_colour = self._tab_top_start_colour
            bottom_colour = self._tab_top_end_colour
            dc.GradientFillLinear(r, bottom_colour, top_colour, wx.NORTH)

            # set rectangle down a bit for gradient drawing
            r.y += r.height
            r.y -= 1

            # draw gradient background
            top_colour = self._tab_bottom_start_colour
            bottom_colour = self._tab_bottom_end_colour
            dc.GradientFillLinear(r, bottom_colour, top_colour, wx.NORTH)

        else:

            # draw inactive tab

            r = wx.Rect(tab_x, tab_y + 1, tab_width, tab_height - 3)

            # start the gradent up a bit and leave the inside border inset
            # by a pixel for a 3D look.  Only the top half of the inactive
            # tab will have a slight gradient
            r.x += 2
            r.y += 0
            r.width -= 2
            r.height /= 2
            r.height -= 0

            # -- draw top gradient fill for glossy look
            top_colour = self._tab_inactive_top_colour
            bottom_colour = self._tab_inactive_bottom_colour
            dc.GradientFillLinear(r, bottom_colour, top_colour, wx.NORTH)

            r.y += r.height
            r.y -= 1

            # -- draw bottom fill for glossy look
            top_colour = self._tab_inactive_bottom_colour
            bottom_colour = self._tab_inactive_bottom_colour
            dc.GradientFillLinear(r, top_colour, bottom_colour, wx.SOUTH)

        # draw tab outline
        dc.SetPen(self._border_pen)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawPolygon(border_points)

        # there are two horizontal grey lines at the bottom of the tab control,
        # this gets rid of the top one of those lines in the tab control
        if page.active:

            if agwFlags & AUI_NB_BOTTOM:
                dc.SetPen(wx.Pen(self._background_bottom_colour))

            # TODO: else if (agwFlags & AUI_NB_LEFT)
            # TODO: else if (agwFlags & AUI_NB_RIGHT)
            else:  # for AUI_NB_TOP
                dc.SetPen(self._base_colour_pen)

            dc.DrawLine(border_points[0].x + 1,
                        border_points[0].y,
                        border_points[5].x,
                        border_points[5].y)

        text_offset = tab_x + 8
        close_button_width = 0

        if close_button_state != AUI_BUTTON_STATE_HIDDEN:
            close_button_width = self._active_close_bmp.GetWidth()

            if agwFlags & AUI_NB_CLOSE_ON_TAB_LEFT:
                text_offset += close_button_width - 5

        bitmap_offset = 0

        if pagebitmap.IsOk():

            bitmap_offset = tab_x + 8
            if agwFlags & AUI_NB_CLOSE_ON_TAB_LEFT and close_button_width:
                bitmap_offset += close_button_width - 5

            # draw bitmap
            dc.DrawBitmap(pagebitmap,
                          bitmap_offset,
                          drawn_tab_yoff + (drawn_tab_height / 2) - (pagebitmap.GetHeight() / 2),
                          True)

            text_offset = bitmap_offset + pagebitmap.GetWidth()
            text_offset += 3  # bitmap padding

        else:

            if agwFlags & AUI_NB_CLOSE_ON_TAB_LEFT == 0 or not close_button_width:
                text_offset = tab_x + 8

        draw_text = ChopText(dc, caption, tab_width - (text_offset - tab_x) - close_button_width)

        ypos = drawn_tab_yoff + (drawn_tab_height) / 2 - (texty / 2) - 1

        offset_focus = text_offset

        if control is not None:
            try:
                if control.GetPosition() != wx.Point(text_offset + 1, ypos):
                    control.SetPosition(wx.Point(text_offset + 1, ypos))

                if not control.IsShown():
                    control.Show()

                if paint_control:
                    bmp = TakeScreenShot(control.GetScreenRect())
                    dc.DrawBitmap(bmp, text_offset + 1, ypos, True)

                controlW, controlH = control.GetSize()
                text_offset += controlW + 4
                textx += controlW + 4
            except wx.PyDeadObjectError:
                pass

        # draw tab text
        rectx, recty = dc.GetMultiLineTextExtent(draw_text)  # dummy (removed as 3rd output)
        dc.DrawLabel(draw_text, wx.Rect(text_offset, ypos, rectx, recty))

        # draw focus rectangle
        #if (agwFlags & AUI_NB_NO_TAB_FOCUS) == 0:
        #    self.DrawFocusRectangle(dc, page, wnd, draw_text, offset_focus, bitmap_offset, drawn_tab_yoff,
        #                            drawn_tab_height, rectx, recty)

        out_button_rect = wx.Rect()

        # draw close button if necessary
        if close_button_state != AUI_BUTTON_STATE_HIDDEN:

            bmp = self._disabled_close_bmp

            if close_button_state == AUI_BUTTON_STATE_HOVER:
                bmp = self._hover_close_bmp
            elif close_button_state == AUI_BUTTON_STATE_PRESSED:
                bmp = self._pressed_close_bmp

            shift = (agwFlags & AUI_NB_BOTTOM and [1] or [0])[0]

            if agwFlags & AUI_NB_CLOSE_ON_TAB_LEFT:
                rect = wx.Rect(tab_x + 4, tab_y + (tab_height - bmp.GetHeight()) / 2 - shift,
                               close_button_width, tab_height)
            else:
                rect = wx.Rect(tab_x + tab_width - close_button_width - 1,
                               tab_y + (tab_height - bmp.GetHeight()) / 2 - shift,
                               close_button_width, tab_height)

            rect = IndentPressedBitmap(rect, close_button_state)
            dc.DrawBitmap(bmp, rect.x, rect.y, True)

            out_button_rect = rect

        out_tab_rect = wx.Rect(tab_x, tab_y, tab_width, tab_height)

        dc.DestroyClippingRegion()

        return out_tab_rect, out_button_rect, x_extent

    def SetCustomButton(self, bitmap_id, button_state, bmp):
        """
        Sets a custom bitmap for the close, left, right and window list buttons.

        :param integer `bitmap_id`: the button identifier;
        :param integer `button_state`: the button state;
        :param Bitmap `bmp`: the custom bitmap to use for the button.
        """

        if bitmap_id == AUI_BUTTON_CLOSE:
            if button_state == AUI_BUTTON_STATE_NORMAL:
                self._active_close_bmp = bmp
                self._hover_close_bmp = self._active_close_bmp
                self._pressed_close_bmp = self._active_close_bmp
                self._disabled_close_bmp = self._active_close_bmp

            elif button_state == AUI_BUTTON_STATE_HOVER:
                self._hover_close_bmp = bmp
            elif button_state == AUI_BUTTON_STATE_PRESSED:
                self._pressed_close_bmp = bmp
            else:
                self._disabled_close_bmp = bmp

        elif bitmap_id == AUI_BUTTON_LEFT:
            if button_state & AUI_BUTTON_STATE_DISABLED:
                self._disabled_left_bmp = bmp
            else:
                self._active_left_bmp = bmp

        elif bitmap_id == AUI_BUTTON_RIGHT:
            if button_state & AUI_BUTTON_STATE_DISABLED:
                self._disabled_right_bmp = bmp
            else:
                self._active_right_bmp = bmp

        elif bitmap_id == AUI_BUTTON_WINDOWLIST:
            if button_state & AUI_BUTTON_STATE_DISABLED:
                self._disabled_windowlist_bmp = bmp
            else:
                self._active_windowlist_bmp = bmp

    def GetIndentSize(self):
        """ Returns the tabs indent size. """

        return 5

    def GetTabSize(self, dc, wnd, caption, bitmap, active, close_button_state, control=None):
        """
        Returns the tab size for the given caption, bitmap and button state.
        :param `dc`: a :class:`DC` device context;
        :param `wnd`: a :class:`Window` instance object;
        :param string `caption`: the tab text caption;
        :param Bitmap `bitmap`: the bitmap displayed on the tab;
        :param bool `active`: whether the tab is selected or not;
        :param integer `close_button_state`: the state of the close button on the tab;
        :param Window `control`: a :class:`Window` instance inside a tab (or ``None``).
        """

        dc.SetFont(self._measuring_font)
        measured_textx, measured_texty = dc.GetMultiLineTextExtent(caption)  # dummy (removed as 3rd output)

        # add padding around the text
        tab_width = measured_textx
        tab_height = measured_texty

        # if the close button is showing, add space for it
        if close_button_state != AUI_BUTTON_STATE_HIDDEN:
            tab_width += self._active_close_bmp.GetWidth() + 3

        # if there's a bitmap, add space for it
        if bitmap.IsOk():
            tab_width += bitmap.GetWidth()
            tab_width += 3  # right side bitmap padding
            tab_height = max(tab_height, bitmap.GetHeight())

        # add padding
        tab_width += 16
        tab_height += 10

        agwFlags = self.GetAGWFlags()
        if agwFlags & AUI_NB_TAB_FIXED_WIDTH:
            tab_width = self._fixed_tab_width

        if control is not None:
            try:
                tab_width += control.GetSize().GetWidth() + 4
            except wx.PyDeadObjectError:
                pass

        x_extent = tab_width

        return (tab_width, tab_height), x_extent

    def DrawButton(self, dc, wnd, in_rect, button, orientation):
        """
        Draws a button on the tab or on the tab area, depending on the button identifier.
        :param `dc`: a :class:`DC` device context;
        :param `wnd`: a :class:`Window` instance object;
        :param Rect `in_rect`: rectangle the tab should be confined to;
        :param `button`: an instance of the button class;
        :param integer `orientation`: the tab orientation.
        """

        bitmap_id, button_state = button.id, button.cur_state

        if bitmap_id == AUI_BUTTON_CLOSE:
            if button_state & AUI_BUTTON_STATE_DISABLED:
                bmp = self._disabled_close_bmp
            elif button_state & AUI_BUTTON_STATE_HOVER:
                bmp = self._hover_close_bmp
            elif button_state & AUI_BUTTON_STATE_PRESSED:
                bmp = self._pressed_close_bmp
            else:
                bmp = self._active_close_bmp

        elif bitmap_id == AUI_BUTTON_LEFT:
            if button_state & AUI_BUTTON_STATE_DISABLED:
                bmp = self._disabled_left_bmp
            else:
                bmp = self._active_left_bmp

        elif bitmap_id == AUI_BUTTON_RIGHT:
            if button_state & AUI_BUTTON_STATE_DISABLED:
                bmp = self._disabled_right_bmp
            else:
                bmp = self._active_right_bmp

        elif bitmap_id == AUI_BUTTON_WINDOWLIST:
            if button_state & AUI_BUTTON_STATE_DISABLED:
                bmp = self._disabled_windowlist_bmp
            else:
                bmp = self._active_windowlist_bmp

        else:
            if button_state & AUI_BUTTON_STATE_DISABLED:
                bmp = button.dis_bitmap
            else:
                bmp = button.bitmap

        if not bmp.IsOk():
            return

        rect = wx.Rect(*in_rect)

        if orientation == wx.LEFT:

            rect.SetX(in_rect.x)
            rect.SetY(((in_rect.y + in_rect.height) / 2) - (bmp.GetHeight() / 2))
            rect.SetWidth(bmp.GetWidth())
            rect.SetHeight(bmp.GetHeight())

        else:

            rect = wx.Rect(in_rect.x + in_rect.width - bmp.GetWidth(),
                           ((in_rect.y + in_rect.height) / 2) - (bmp.GetHeight() / 2),
                           bmp.GetWidth(), bmp.GetHeight())

        rect = IndentPressedBitmap(rect, button_state)
        dc.DrawBitmap(bmp, rect.x, rect.y, True)

        out_rect = rect

        if bitmap_id == AUI_BUTTON_RIGHT:
            self._buttonRect = wx.Rect(rect.x, rect.y, 30, rect.height)

        return out_rect

    def DrawFocusRectangle(self, dc, page, wnd, draw_text, text_offset, bitmap_offset, drawn_tab_yoff, drawn_tab_height,
                           textx, texty):
        """
        Draws the focus rectangle on a tab.
        :param `dc`: a :class:`DC` device context;
        :param `page`: the page associated with the tab;
        :param `wnd`: a :class:`Window` instance object;
        :param string `draw_text`: the text that has been drawn on the tab;
        :param integer `text_offset`: the text offset on the tab;
        :param integer `bitmap_offset`: the bitmap offset on the tab;
        :param integer `drawn_tab_yoff`: the y offset of the tab text;
        :param integer `drawn_tab_height`: the height of the tab;
        :param integer `textx`: the x text extent;
        :param integer `texty`: the y text extent.
        """

        if self.GetAGWFlags() & AUI_NB_NO_TAB_FOCUS:
            return

        if page.active and wx.Window.FindFocus() == wnd:

            focusRectText = wx.Rect(text_offset, (drawn_tab_yoff + (drawn_tab_height) / 2 - (texty / 2)),
                                    textx, texty)

            if page.bitmap.IsOk():
                focusRectBitmap = wx.Rect(bitmap_offset,
                                          drawn_tab_yoff + (drawn_tab_height / 2) - (page.bitmap.GetHeight() / 2),
                                          page.bitmap.GetWidth(), page.bitmap.GetHeight())

            if page.bitmap.IsOk() and draw_text == "":
                focusRect = wx.Rect(*focusRectBitmap)
            elif not page.bitmap.IsOk() and draw_text != "":
                focusRect = wx.Rect(*focusRectText)
            elif page.bitmap.IsOk() and draw_text != "":
                focusRect = focusRectText.Union(focusRectBitmap)

            focusRect.Inflate(2, 2)

            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(self._focusPen)
            dc.DrawRoundedRectangleRect(focusRect, 2)

    def GetBestTabCtrlSize(self, wnd, pages, required_bmp_size):
        """
        Returns the best tab control size.
        :param `wnd`: a :class:`Window` instance object;
        :param list `pages`: the pages associated with the tabs;
        :param Size `required_bmp_size`: the size of the bitmap on the tabs.
        """

        dc = wx.ClientDC(wnd)
        dc.SetFont(self._measuring_font)

        # sometimes a standard bitmap size needs to be enforced, especially
        # if some tabs have bitmaps and others don't.  This is important because
        # it prevents the tab control from resizing when tabs are added.

        measure_bmp = wx.NullBitmap

        if required_bmp_size.IsFullySpecified():
            measure_bmp = wx.EmptyBitmap(required_bmp_size.x,
                                         required_bmp_size.y)

        max_y = 0

        for page in pages:

            if measure_bmp.IsOk():
                bmp = measure_bmp
            else:
                bmp = page.bitmap

            # we don't use the caption text because we don't
            # want tab heights to be different in the case
            # of a very short piece of text on one tab and a very
            # tall piece of text on another tab
            s, x_ext = self.GetTabSize(dc, wnd, page.caption, bmp, True, AUI_BUTTON_STATE_HIDDEN, None)
            max_y = max(max_y, s[1])

            if page.control:
                controlW, controlH = page.control.GetSize()
                max_y = max(max_y, controlH + 4)

        return max_y + 2

    def SetNormalFont(self, font):
        """
        Sets the normal font for drawing tab labels.
        :param Font `font`: the new font to use to draw tab labels in their normal, un-selected state.
        """

        self._normal_font = font

    def SetSelectedFont(self, font):
        """
        Sets the selected tab font for drawing tab labels.
        :param Font `font`: the new font to use to draw tab labels in their selected state.
        """

        self._selected_font = font

    def SetMeasuringFont(self, font):
        """
        Sets the font for calculating text measurements.
        :param Font `font`: the new font to use to measure tab labels text extents.
        """

        self._measuring_font = font

    def GetNormalFont(self):
        """ Returns the normal font for drawing tab labels. """

        return self._normal_font

    def GetSelectedFont(self):
        """ Returns the selected tab font for drawing tab labels. """

        return self._selected_font

    def GetMeasuringFont(self):
        """ Returns the font for calculating text measurements. """

        return self._measuring_font

    def ShowDropDown(self, wnd, pages, active_idx):
        """
        Shows the drop-down window menu on the tab area.
        :param `wnd`: a :class:`Window` derived window instance;
        :param list `pages`: the pages associated with the tabs;
        :param integer `active_idx`: the active tab index.
        """

        useImages = self.GetAGWFlags() & AUI_NB_USE_IMAGES_DROPDOWN
        menuPopup = wx.Menu()

        longest = 0
        for i, page in enumerate(pages):

            caption = page.caption

            # if there is no caption, make it a space.  This will prevent
            # an assert in the menu code.
            if caption == "":
                caption = " "

            # Save longest caption width for calculating menu width with
            width = wnd.GetTextExtent(caption)[0]
            if width > longest:
                longest = width

            if useImages:
                menuItem = wx.MenuItem(menuPopup, 1000 + i, caption)
                if page.bitmap:
                    menuItem.SetBitmap(page.bitmap)

                # menuPopup.AppendItem(menuItem)  # depreciated
                menuPopup.Append(menuItem)

            else:

                menuPopup.AppendCheckItem(1000 + i, caption)

            menuPopup.Enable(1000 + i, page.enabled)

        if active_idx != -1 and not useImages:
            menuPopup.Check(1000 + active_idx, True)

        # find out the screen coordinate at the bottom of the tab ctrl
        cli_rect = wnd.GetClientRect()

        # Calculate the approximate size of the popupmenu for setting the
        # position of the menu when its shown.
        # Account for extra padding on left/right of text on mac menus
        if wx.Platform in ['__WXMAC__', '__WXMSW__']:
            longest += 32

        # Bitmap/Checkmark width + padding
        longest += 20

        if self.GetAGWFlags() & AUI_NB_CLOSE_BUTTON:
            longest += 16

        pt = wx.Point(cli_rect.x + cli_rect.GetWidth() - longest,
                      cli_rect.y + cli_rect.height)

        cc = AuiCommandCapture()
        wnd.PushEventHandler(cc)
        wnd.PopupMenu(menuPopup, pt)
        command = cc.GetCommandId()
        wnd.PopEventHandler(True)

        if command >= 1000:
            return command - 1000

        return -1