import math
import numpy as np
from pubsub import pub
import wx
import wx.grid
import matplotlib as mpl
import matplotlib.figure
import matplotlib.dates as mdates
mpl.use('WXAGG')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d
from matplotlib.widgets import RectangleSelector
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

import _icons as ico
from chart_mgr import LineItem


font = {'size': 8}  # 16
mpl.rc('font', **font)


def GetVariableLabel(text):
    _text = text

    while ' - ' in _text:
        _text = _text[(_text.find(' - ') + 3):]

    return _text


class ChartPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        # create figure and canvas -------------------------------------------------------------------------------------
        self.fig = mpl.figure.Figure(figsize=(2, 2))
        self.fig.subplots_adjust(left=0., bottom=0., right=0.99, top=0.98, hspace=0., wspace=0.)

        self._bottom = None
        self._left = None
        self._date_adjust = None
        self._text_baseline = None
        self._adjust_text = None

        self.canvas = FigureCanvas(self, wx.ID_ANY, self.fig)
        self._renderer = self.fig.canvas.get_renderer()
        self._dpi = self.fig.get_dpi()

        # x, y annotation on chart -------------------------------------------------------------------------------------
        self._tooltip = None
        self._x = None
        self._y = None
        self._annotation_ax = None
        self._annotation = None
        self._annotation_timer = wx.Timer(self)

        # used for annotation & figure sizing --------------------------------------------------------------------------
        self._x_is_date = False
        self._x_is_text = False

        # sizing -------------------------------------------------------------------------------------------------------
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(box)
        self.Fit()

        # events -------------------------------------------------------------------------------------------------------
        self.fig.canvas.mpl_connect('motion_notify_event', self.OnHover)
        self.fig.canvas.mpl_connect('axes_leave_event', self.OnLeaveAxes)
        self.Bind(wx.EVT_TIMER, self.AnnotateChart)

    # ==================================================================================================================
    # Events
    # ==================================================================================================================
    # Annotation events ------------------------------------------------------------------------------------------------
    def OnHover(self, event):
        self._annotation_timer.Stop()

        # mouse is being dragged, not hovered
        if event.button is not None:
            return

        # check if hovering on an axes
        ax = event.inaxes
        if ax is None:
            return
        else:
            self._annotation_ax = ax

        # remove existing annotation
        annotations = [child for child in ax.get_children() if child == self._annotation]
        if annotations:
            annotations[0].remove()
            self.canvas.draw()

        # check if hovering on an item and extract appropriate parameters
        text, x, y, do_draw = self.GetTooltipParams(event)

        if not do_draw:
            return

        # adjust tooltip based on x-axis format ------------------------------------------------------------------------
        if isinstance(x, float):
            tooltip = text + ': ({}, {})'.format(round(x, 2), round(y, 2))
        elif self._x_is_date:
            tooltip = text + ': ({}, {})'.format(x.strftime('%d-%m-%Y'), round(y, 2))
            #tooltip += '({}, {})'.format(mdates.num2date(x).strftime('%d-%m-%Y'), round(y, 2))
        elif self._x_is_text:
            tooltip = '{}: {}'.format(x, round(y, 2))
        else:
            tooltip = text + ': ({}, {})'.format(round(x, 2), round(y, 2))

        self._tooltip = tooltip

        # x, y and annotation axes has to be the top most axes (when twinx) is used to display annotation
        self._x = event.xdata
        self._y = event.ydata

        if self._x is not None:
            # start timer
            if not self._annotation_timer.IsRunning():
                self._annotation_timer.Start(milliseconds=500)

    def AnnotateChart(self, event):
        self._annotation_timer.Stop()

        ax = self._annotation_ax
        x = self._x
        y = self._y

        # position label relative to the cursors position on the chart -------------------------------------------------
        tooltip_text = plt.text(0., 0., self._tooltip).get_window_extent(renderer=self._renderer)
        tooltip_width = tooltip_text.width
        tooltip_height = tooltip_text.height

        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        x_mid = (x_max + x_min) / 2.
        y_mid = (y_max + y_min) / 1.1

        x_offset = 5
        if x > x_mid:
            x_offset = -tooltip_width * 0.8

        y_offset = 5
        if y > y_mid:
            y_offset = -tooltip_height

        offset = (x_offset, y_offset)

        # annotate chart -----------------------------------------------------------------------------------------------
        self._annotation = ax.annotate(self._tooltip, xy=(x, y), xytext=offset, textcoords='offset points',
                                      bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.85), zorder=100)

        self._annotation.set_visible(True)
        self.canvas.draw()

    def OnLeaveAxes(self, event):
        if self._annotation_timer.IsRunning():
            self._annotation_timer.Stop()

        if self._annotation is not None:
            self._annotation.set_visible(False)
            event.canvas.draw()

    # ==================================================================================================================
    # Internal functions
    # ==================================================================================================================
    def GetTooltipParams(self, event):
        # sub-class
        return '', 0., 0., False

    def GetLineTooltipParams(self, event):
        # wrap in GetTooltipParams to use for multiple different subclasses of chart
        text = ''
        x = 0.
        y = 0.
        do_draw = False

        for ax in self.fig.get_axes():
            for line in ax.get_lines():
                cont, ind = line.contains(event)
                if cont:
                    x, y = line.get_data()
                    x = x[ind['ind'][0]].item()
                    y = y[ind['ind'][0]]
                    text = GetVariableLabel(line.get_label())
                    do_draw = True
                    break

        return text, x, y, do_draw

    # ==================================================================================================================
    # External functions
    # ==================================================================================================================
    def DrawPlaceholder(self, size_options=None):
        # Show an empty axes -------------------------------------------------------------------------------------------
        self.fig.clf()
        self.fig.subplots_adjust(left=0., bottom=0.)  # reset prior to allocating axes for setting figure space
        ax = self.fig.add_subplot(1, 1, 1, label=0)
        ax.minorticks_on()
        ax.yaxis.set_tick_params(labelrotation=90)
        ax.grid(True)

        self._x_is_date = False
        self._x_is_text = False

        self.AdjustFigureSpace(ax, size_options)
        self.canvas.draw()

    def SetSizeOptions(self, ax, size_options=None):

        if size_options is not None:
            tick_label_text_size, label_text_size = size_options.GetLabelSizes()
        else:  # default sizes for charts on Frames (CurveFitFrame, FunctionFrame, etc.)
            tick_label_text_size = 8
            label_text_size = 8

        ax.xaxis.set_tick_params(labelsize=tick_label_text_size)
        ax.yaxis.set_tick_params(labelsize=tick_label_text_size)
        ax.xaxis.label.set_size(label_text_size)
        ax.yaxis.label.set_size(label_text_size)

        return tick_label_text_size, label_text_size

    # taken from: https://matplotlib.org/3.1.1/gallery/text_labels_and_annotations/date.html
    def FormatXAxis(self, ax, is_date=False, is_text=False):

        if is_date:

            # year-base
            low, high = ax.xaxis.get_view_interval()
            major_base = int(max(1, round(((high - low) / 365.25) / 15.)))

            ax.xaxis.set_major_locator(mdates.YearLocator(base=major_base))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax.xaxis.set_minor_locator(mdates.YearLocator(base=1))

            # self.fig.autofmt_xdate does not work with subplots, so manually implementing same style
            ax.xaxis.set_tick_params(labelrotation=30)
            self.fig.subplots_adjust(bottom=self._bottom + self._date_adjust)

            # used for annotation & figure sizing
            self._x_is_date = True

        elif is_text:

            dpi = self._dpi
            ax_bbox = ax.get_window_extent()
            ax_height = (ax_bbox.y1 - ax_bbox.y0) / dpi

            row = ax.get_subplotspec().get_geometry()[0]
            self._adjust_text = ax.xaxis.get_ticklabel_extents(renderer=self._renderer)[0].height / row / dpi / ax_height

            self.fig.subplots_adjust(bottom=self._text_baseline + self._adjust_text)

            self._x_is_text = True

        else:

            self.fig.subplots_adjust(bottom=self._bottom)
            self._x_is_date = False
            self._x_is_text = False

            # set requirements for changing to scientific notation for x-axis
            ax.ticklabel_format(axis='x', style='scientific', scilimits=(-1, 5))
            # useMathText=True for 10^{-...} instead of 1e-...

    def FormatYAxis(self, ax):
        m = -1
        n = 5

        # set requirements for changing to scientific notation for y-axis
        ax.ticklabel_format(axis='y', style='scientific', scilimits=(m, n))
        # useMathText=True for 10^{-...} instead of 1e-...

        ylim = ax.get_ylim()
        if (ylim[1] < 10. ** m) or (ylim[1] >= 10. ** n):

            self.fig.subplots_adjust(top=0.96)
        else:
            self.fig.subplots_adjust(top=0.98)

    def AdjustFigureSpace(self, ax, chart_size):
        # set size parameters of texts ---------------------------------------------------------------------------------
        tick_label_text_size, label_text_size = self.SetSizeOptions(ax, chart_size)

        # get figure specific options ----------------------------------------------------------------------------------
        renderer = self._renderer
        dpi = self._dpi

        # get size parameters that will not change per axis ------------------------------------------------------------
        # get length of a single major tick
        tick_size = plt.rcParams['ytick.major.size'] / dpi

        # get padding between tick to tick labels (tick_pad) and tick labels to axis label (label_pad)
        tick_pad = ax.yaxis.get_tick_padding() / dpi
        label_pad = (ax.yaxis.labelpad * 2.) / dpi  # increasing the label padding by factor 2

        # find extent of axis for scaling with relative sizes
        ax_bbox = ax.get_window_extent()
        ax_width = (ax_bbox.x1 - ax_bbox.x0) / dpi
        ax_height = (ax_bbox.y1 - ax_bbox.y0) / dpi

        # get width of spine (required on the left side axis', because they are drawn from left -> right)
        spine_width = ax.spines['left'].get_linewidth() / dpi

        # if a tick label is not a string (as is the case) it defaults to '' and uses the tick locations.
        # To overcome this the width of the ticklabel is evaluated on a representative text object
        tick_label_width = plt.text(0., 0., '0.0', rotation=90, fontsize=tick_label_text_size).get_window_extent(renderer=renderer).width / dpi
        tick_label_height = tick_label_width

        # if x-axis is date or text, the ticklabels are rotated differently
        self._date_adjust = (plt.text(0., 0., '0000', rotation=30, fontsize=label_text_size).get_window_extent(renderer=renderer).height / dpi - tick_label_height) / ax_height

        # label width is evaluated on a representative text string
        label_width = plt.text(0., 0., r'N_p, [M/]', rotation=90, fontsize=label_text_size).get_window_extent(renderer=renderer).width / dpi
        label_height = plt.text(0., 0., r'N_p, [M/]').get_window_extent(renderer=renderer).height / dpi
        #label_height = mpl.text.TextPath((0., 0.), r'N_p, [M/]', size=label_text_size).get_extents().height / dpi

        # finding left
        left_pad = 0.005
        left = (label_width + label_pad + tick_label_width + tick_pad + tick_size + spine_width) / ax_width + left_pad

        # finding bottom
        bottom_pad = 0.005
        bottom = (label_height + label_pad + tick_label_height + tick_pad + tick_size + spine_width) / ax_height + bottom_pad

        # setting text baseline to be used when x-axis is text
        self._text_baseline = (tick_pad + tick_size + spine_width) / ax_height + bottom_pad

        self.fig.subplots_adjust(left=left, bottom=bottom)
        self._bottom = bottom
        self._left = left

    def AdjustSubplotSpace(self, row, col):
        if self._x_is_date:
            add = self._date_adjust
        elif self._x_is_text:
            add = self._text_baseline + self._adjust_text - self._bottom
        else:
            add = 0.

        # maybe the padding should be included?
        self.fig.subplots_adjust(wspace=col * (self._left + 5e-3), hspace=row * (self._bottom + add + 5e-3))


class DisplayChartPanel(ChartPanel):
    def __init__(self, parent, window_id, chart_id):
        super().__init__(parent)

        # id's related to activating charts ----------------------------------------------------------------------------
        self._window_id = window_id
        self._chart_id = chart_id
        self._axes_id = 0

        # picking ------------------------------------------------------------------------------------------------------
        self._picked = None
        self._pick_and_click = False

        # highlight clicked chart --------------------------------------------------------------------------------------
        self._highlight_timer = wx.Timer(self, id=wx.NewId())

        # events -------------------------------------------------------------------------------------------------------
        self.fig.canvas.mpl_connect('button_press_event', self.OnClick)
        self.fig.canvas.mpl_connect('pick_event', self.OnPick)
        self.Bind(wx.EVT_TIMER, self.HighlightChart, id=self._highlight_timer.GetId())

    # events -----------------------------------------------------------------------------------------------------------
    def UnHighlightPicked(self):
        # un-highlight existing highlighted lines
        if self._picked is not None:
            if self._picked.get_linewidth():
                self._picked.set_linewidth(self._picked.get_linewidth() - 2)

            elif self._picked.get_markersize():
                self._picked.set_markersize(self._picked.get_markersize() - 2)

    # Clicked events
    def OnClick(self, event):
        # avoids error when clicking on charts on separate frames (HistoryFrame, PredictionFrame, etc.)
        if (self._window_id is None) or (self._chart_id is None):
            return

        if event.button == 1:
            self.OnLeftClick(event)
        if event.button == 2:
            pass
        if event.button == 3:
            self.OnRightClick(event)

    def OnLeftClick(self, event):
        if not self._pick_and_click:
            self.UnHighlightPicked()
            self._picked = None

            # highlight clicked chart for a short duration
            self.fig.set_facecolor([0.95, 0.95, 0.95])
            self.canvas.draw()
            self._highlight_timer.Start(milliseconds=80)

            pub.sendMessage('activate_chart', window_id=self._window_id, chart_id=self._chart_id)

        self._pick_and_click = False

    def HighlightChart(self, event):
        self._highlight_timer.Stop()
        self.fig.set_facecolor([1., 1., 1.])
        self.canvas.draw()

    def OnRightClick(self, event):
        popupmenu = wx.Menu()

        spreadsheet = wx.MenuItem(popupmenu, wx.ID_ANY, 'Show xy-pair')
        spreadsheet.SetBitmap(ico.spreadsheet_16x16.GetBitmap())
        popupmenu.Append(spreadsheet)

        self.Bind(wx.EVT_MENU, self.OpenSpreadsheet, spreadsheet)

        self.PopupMenu(popupmenu)
        popupmenu.Destroy()

    def OpenSpreadsheet(self, event):
        if self._picked is not None:
            label = self._picked.get_label()
            x = self._picked.get_xdata()
            y = self._picked.get_ydata()

            if not self._x_is_date:
                x = np.round(x, 1) if x[-1] > 1. else np.round(x, 2)

            y = np.round(y, 1) if y[-1] > 1. else np.round(y, 2)

            SpreadsheetFrame(self, x, y, label).Show()

    # Picking events
    def OnPick(self, event):
        self.UnHighlightPicked()

        # highlight selected line
        self._picked = event.artist
        if self._picked.get_linewidth():
            self._picked.set_linewidth(self._picked.get_linewidth() + 2)

        elif self._picked.get_markersize():
            self._picked.set_markersize(self._picked.get_markersize() + 2)

        self._pick_and_click = True

    # internal methods -------------------------------------------------------------------------------------------------
    def GetAxesID(self):
        idx = '{}.{}.{}'.format(self._window_id, self._chart_id, self._axes_id)
        self._axes_id += 1
        return idx

    # external methods
    def GetIds(self):
        return self._window_id, self._chart_id

    def SetWindowId(self, id_):
        self._window_id = id_


class SpreadsheetFrame(wx.Frame):
    def __init__(self, parent, x, y, label):
        super().__init__(parent=parent, title=label,
                         style=wx.CAPTION | wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR)

        self.SetIcon(ico.spreadsheet_16x16.GetIcon())

        self._x = x
        self._y = y

        self.panel = None
        self.grid = None

        self.InitUI()
        self.SetSize(wx.Size(275, 600))

    def InitUI(self):
        self.panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.grid = wx.grid.Grid(self.panel)
        self.grid.CreateGrid(self._x.size, 2)

        for i, (x, y) in enumerate(zip(self._x, self._y)):
            self.grid.SetCellValue(i, 0, str(x))
            self.grid.SetCellValue(i, 1, str(y))

        sizer.Add(self.grid, 1, wx.EXPAND)
        self.panel.SetSizer(sizer)


class SelectionChartPanel(ChartPanel):
    def __init__(self, parent):
        super().__init__(parent)

        # data selection -----------------------------------------------------------------------------------------------
        self._axes_item = None
        self._data = None  # the first LineItem in AxesItem
        self._selection = LineItem()

        # required for rectangle selector
        self._ax = None
        self._rs = None

    def Realize(self, axes_item=None, ax=None):
        # designed to be subclassed
        pass

    def SetRectangleSelector(self, ax):
        # drawtype is 'box' or 'line' or 'none'
        rectprops = dict(facecolor=(0.8, 0.8, 0.8), edgecolor='black', alpha=0.3, fill=True)

        self._rs = RectangleSelector(ax, self.line_select_callback,
                                     rectprops=rectprops,
                                     drawtype='box', useblit=True,
                                     button=[1, 3],  # don't use middle button
                                     minspanx=5, minspany=5,
                                     spancoords='pixels',
                                     interactive=False)

    def line_select_callback(self, eclick, erelease):
        if self._axes_item is None:
            return

        # eclick and erelease are the press and release events
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        if self._x_is_date:
            x1 = np.datetime64(mdates.num2date(x1))
            x2 = np.datetime64(mdates.num2date(x2))

        self._selection = LineItem(options=self._data.CopyOptions(), x_is_date=self._x_is_date)
        self._selection.Highlight()

        for x, y in zip(*self._data.GetXY()):
            if ((x1 <= x <= x2) or (x2 <= x <= x1)) and ((y1 <= y <= y2) or (y2 <= y <= y1)):
                self._selection.AppendXY(x, y)

        self.Realize(self._axes_item)

    def GetSelection(self):
        return self._selection

    def ClearSelection(self):
        self._selection.ClearXY()
        self.Realize(self._axes_item, self._ax)


class MultiAxis:
    def __init__(self, fig):

        self.fig = fig

    def AllocateAxes(self, axes_item):
        axes = [None for _ in range(0, axes_item.GetNumberOfAxes())]

        # create main axes'
        for i in range(0, axes_item.GetAxes()):
            idx = i * (1 + axes_item.GetSubAxes())
            axes[idx] = self.fig.add_subplot(*axes_item.GetLayout(), i + 1)#, label=self.GetAxesID())

            # create sub axis'
            for j in range(1, axes_item.GetSubAxes() + 1):
                axes[idx + j] = axes[idx].twinx()

        return axes

    @staticmethod
    def PositionLegends(axes_item, items):
        legends = [[] for _ in range(0, axes_item.GetAxes())]

        for item in items:
            if item is None:
                continue

            idx = int(math.ceil((item.GetAxes() + 1) / (axes_item.GetSubAxes() + 1)) - 1)

            legend = item.GetLegend()
            if isinstance(legend, list):  # stacked line legend
                legends[idx] = legend
            else:
                legends[idx].append(legend)

        return legends

    # based on https://stackoverflow.com/questions/20356982/matplotlib-colour-multiple-twinx-axes (27-08-2019)
    def SetSpineLocations(self, axes_item, axes):
        # get figure specific options ----------------------------------------------------------------------------------
        renderer = self.fig.canvas.get_renderer()
        dpi = self.fig.get_dpi()

        # get size parameters that will not change per axis ------------------------------------------------------------
        # get length of a single major tick
        tick_size = plt.rcParams['ytick.major.size'] / dpi

        # get padding between tick to tick labels (tick_pad) and tick labels to axis label (label_pad)
        tick_pad = axes[0].yaxis.get_tick_padding() / dpi
        label_pad = (axes[0].yaxis.labelpad * 2.) / dpi  # increasing the label padding by factor 2

        # find extent of axis for scaling with relative sizes
        ax_bbox = axes[0].get_window_extent()
        ax_width = (ax_bbox.x1 - ax_bbox.x0) / dpi

        # get width of spine (required on the left side axis', because they are drawn from left -> right)
        spine_width = axes[0].spines['left'].get_linewidth() / dpi

        # if a tick label is not a string (as is the case) it defaults to '' and uses the tick locks.
        # To overcome this the width of the ticklabel is evaluated on a representative text object
        tick_label_width = plt.text(0., 0., '0.0', rotation=90).get_window_extent(renderer=renderer).width / dpi

        # calculate a delta to label position as it will be used multiple times
        delta_to_label = (tick_size + tick_pad + tick_label_width + label_pad) / ax_width

        # used to determine amount of padding
        _, col = axes_item.GetLayout()

        # loop through all primary axis' and all sub axis' -------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            ii = i * (1 + axes_item.GetSubAxes())
            custom_pad = 3. / dpi

            # rotate tick labels to reduce impact of decimal points, minuses, etc.
            axes[ii].yaxis.set_tick_params(labelrotation=90)

            # get initial width of labels on left side related to primary axis
            label_width = axes[ii].yaxis.label.get_window_extent(renderer=renderer).width / dpi

            # set deltas
            delta_left = delta_to_label + label_width / ax_width
            delta_right = 0.

            # to be consistent in axis alignment, move the primary axis label inwards
            axes[0].yaxis.set_label_coords(-delta_to_label, .5)

            for j in range(1, axes_item.GetSubAxes() + 1):
                ij = ii + j

                label_width = axes[ij].yaxis.label.get_window_extent(renderer=renderer).width / dpi

                delta = delta_to_label + label_width / ax_width

                if j % 2:

                    side = 'right'
                    is_left = False

                    box = axes[ij].get_position()
                    box.x1 -= delta / col
                    axes[ij].set_position(box)

                    padding = custom_pad / ax_width if j > 1 else 0.
                    spine_position = 1 + delta_right + padding
                    label_position = 1 + delta_right + delta_to_label + padding

                    delta_right += delta

                else:

                    side = 'left'
                    is_left = True

                    box = axes[ij].get_position()
                    box.x0 += delta / col
                    axes[ij].set_position(box)

                    # objects are drawn left -> right, so additional padding required when drawing on the left side
                    # adding label_width, tick_size and spine_width
                    spine_position = - (delta_left + (custom_pad + tick_size + spine_width) / ax_width)
                    label_position = - (delta_left + delta + (custom_pad + tick_size + spine_width) / ax_width)

                    delta_left += delta

                axes[ij].set_frame_on(True)
                axes[ij].patch.set_visible(False)

                plt.setp(axes[ij].spines.values(), visible=False)
                axes[ij].spines[side].set_position(('axes', spine_position))
                axes[ij].spines[side].set_visible(True)

                axes[ij].yaxis.label.set_color('k')
                axes[ij].spines[side].set_edgecolor('k')
                axes[ij].tick_params(axis='y', colors='k', direction='out',
                                     left=is_left, right=not is_left,
                                     labelleft=is_left, labelright=not is_left,
                                     labelrotation=90)

                axes[ij].yaxis.set_label_coords(label_position, .5)

                custom_pad += 5. / dpi


class CartesianChartPanel(DisplayChartPanel, MultiAxis):
    def __init__(self, parent, window_id, chart_id):
        DisplayChartPanel.__init__(self, parent, window_id, chart_id)
        MultiAxis.__init__(self, self.fig)

    def Realize(self, axes_item=None, size_options=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder(size_options=size_options)
            return

        self.fig.clf()
        # Create required axes' ----------------------------------------------------------------------------------------
        axes = self.AllocateAxes(axes_item)

        if size_options is not None:
            for ax in axes:
                self.SetSizeOptions(ax, size_options=size_options)

        # draw lines ---------------------------------------------------------------------------------------------------
        for l, line in enumerate(axes_item.GetLines()):
            if line is not None:
                i = line.GetAxes()
                axes[i].plot(*line.GetXY(), **line.GetOptions())

        # draw uncertainty ---------------------------------------------------------------------------------------------
        if axes_item.ShowUncertainty():
            for l, line in enumerate(axes_item.GetLines()):
                if line is not None:
                    i = line.GetAxes()

                    options = line.GetOptions()
                    label = options['label']

                    low = axes_item.GetLowY(l)
                    if low is not None:
                        options['label'] = label + ' (Low)'
                        axes[i].plot(line.GetX(), low, **options)

                    high = axes_item.GetHighY(l)
                    options['label'] = label + ' (High)'
                    if high is not None:
                        axes[i].plot(line.GetX(), high, **options)

                    shading = axes_item.GetShading(l)
                    if shading is not None:
                        for u in range(*shading.GetResolution()):
                            axes[i].fill_between(line.GetX(), *shading.GetYs(u), **shading.GetOptions(u))

        # configure x-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            ax = axes[i * (axes_item.GetSubAxes() + 1)]
            ax.set(**axes_item.GetXOptions(i))
            ax.minorticks_on()
            self.FormatXAxis(ax, axes_item.XIsDate(i))

        # configure y-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetNumberOfAxes()):
            axes[i].set(**axes_item.GetYOptions(i))
            self.FormatYAxis(axes[i])

        # configure subplot and spine locations ------------------------------------------------------------------------
        self.AdjustSubplotSpace(*axes_item.GetLayout())
        self.SetSpineLocations(axes_item, axes)

        # Gather legend at position at last chart of each axes ---------------------------------------------------------
        legends = self.PositionLegends(axes_item, axes_item.GetLines())
        for i in range(0, axes_item.GetAxes()):
            idx = (i + 1) * (axes_item.GetSubAxes() + 1) - 1
            axes[idx].legend(handles=legends[i], **axes_item.GetLegendOptions(i))

        # position grid at first chart of each axes --------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            idx = i * (axes_item.GetSubAxes() + 1)
            axes[idx].grid(True)

        # draw chart on canvas
        self.canvas.draw()

    def GetTooltipParams(self, event):
        return self.GetLineTooltipParams(event)


class StackedChartPanel(DisplayChartPanel, MultiAxis):
    def __init__(self, parent, window_id, chart_id):
        DisplayChartPanel.__init__(self, parent, window_id, chart_id)
        MultiAxis.__init__(self, self.fig)

        self._containers = []  # required for annotation

    def Realize(self, axes_item=None, size_options=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder(size_options=size_options)
            return

        self.fig.clf()

        # Create required axes' ----------------------------------------------------------------------------------------
        axes = self.AllocateAxes(axes_item)

        if size_options is not None:
            for ax in axes:
                self.SetSizeOptions(ax, size_options=size_options)

        # draw lines ---------------------------------------------------------------------------------------------------
        for line in axes_item.GetStackedLines():
            i = line.GetAxes()
            self._containers.append(axes[i].stackplot(line.GetX(), *line.GetYs(), **line.GetOptions()))

        # configure x-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            ax = axes[i * (axes_item.GetSubAxes() + 1)]
            ax.set(**axes_item.GetXOptions(i))
            ax.minorticks_on()
            self.FormatXAxis(ax, axes_item.XIsDate(i))

        # configure y-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetNumberOfAxes()):
            axes[i].set(**axes_item.GetYOptions(i))

        self.AdjustSubplotSpace(*axes_item.GetLayout())
        self.SetSpineLocations(axes_item, axes)

        # Gather legend at position at last chart of each axes ---------------------------------------------------------
        legends = self.PositionLegends(axes_item, axes_item.GetStackedLines())
        for i in range(0, axes_item.GetAxes()):
            idx = (i + 1) * (axes_item.GetSubAxes() + 1) - 1
            axes[idx].legend(handles=legends[i], **axes_item.GetLegendOptions(i))

        # position grid at first chart of each axes --------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            idx = i * (axes_item.GetSubAxes() + 1)
            axes[idx].grid(True)

        # draw chart on canvas
        self.canvas.draw()

    def GetTooltipParams(self, event):
        text = ''
        y = event.ydata
        do_draw = False

        if self._x_is_date:
            x = mdates.num2date(event.xdata)
        else:
            x = 0.

        for container in self._containers:
            for polygon in container:
                cont, _ = polygon.contains(event)
                if cont:
                    do_draw = True
                    text = polygon.get_label()
                    break

        return text, x, y, do_draw


class BarChartPanel(DisplayChartPanel, MultiAxis):
    def __init__(self, parent, window_id, chart_id):
        DisplayChartPanel.__init__(self, parent, window_id, chart_id)
        MultiAxis.__init__(self, self.fig)

        self._containers = []  # required for annotation

    def Realize(self, axes_item=None, size_options=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder(size_options=size_options)
            return

        self.fig.clf()
        # Create required axes' ----------------------------------------------------------------------------------------
        axes = self.AllocateAxes(axes_item)

        if size_options is not None:
            for ax in axes:
                self.SetSizeOptions(ax, size_options=size_options)

        # plot objectives ----------------------------------------------------------------------------------------------
        for i, bar in enumerate(axes_item.GetBars()):
            i = bar.GetAxes()
            self._containers.append(axes[i].bar(*bar.Get(), **bar.GetOptions()))

            # colour bars per a specific grouping
            #if self._colour_by is not None:
            #    for j, bar in enumerate(plots[i]):
            #        bar.set_color(df['colour'][j])
            #        bar.set_edgecolor(options.get_colour(i))
            #        bar.set_linewidth(2)

        # position names in the middle ---------------------------------------------------------------------------------
        ticks = axes_item.GetXOptions()
        for i in range(0, axes_item.GetAxes()):
            ax = axes[i * (axes_item.GetSubAxes() + 1)]
            ax.set_xlim(ticks['lim'])
            ax.set_xticks(ticks['xticks'])
            ax.set_xticklabels(ticks['xticklabels'], rotation=15)
            self.FormatXAxis(ax, is_date=False, is_text=True)

        # configure y-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetNumberOfAxes()):
            axes[i].set(**axes_item.GetYOptions(i))

        # set axis' ----------------------------------------------------------------------------------------------------
        self.AdjustSubplotSpace(*axes_item.GetLayout())
        self.SetSpineLocations(axes_item, axes)

        # Gather legend at position at last chart of each axes ---------------------------------------------------------
        legends = self.PositionLegends(axes_item, axes_item.GetBars())
        for i in range(0, axes_item.GetAxes()):
            idx = i + axes_item.GetSubAxes()
            axes[idx].legend(handles=legends[i], fontsize=size_options.GetLegendSize())

        # position grid at first chart of each axes --------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            idx = i * (axes_item.GetSubAxes() + 1)
            axes[idx].yaxis.grid(which='major')
            axes[idx].set_axisbelow(True)

        # draw chart on canvas -----------------------------------------------------------------------------------------
        self.canvas.draw()

    def GetTooltipParams(self, event):
        y = 0.
        do_draw = False

        for container in self._containers:
            for bar in container:
                cont, ind = bar.contains(event)
                if cont:
                    y = bar.get_height()
                    do_draw = True
                    break

        x = self.fig.get_axes()[0].xaxis.get_ticklabels()[int(round(event.xdata, 0))].get_text()

        return '', x, y, do_draw


class BubbleChartPanel(DisplayChartPanel):
    def __init__(self, parent, template_id, chart_id):
        super().__init__(parent, template_id, chart_id)

    def Realize(self, axes_item=None, size_options=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder(size_options=size_options)
            return

        # pre-allocate axes --------------------------------------------------------------------------------------------
        self.fig.clf()
        ax = self.fig.add_subplot(1, 1, 1, label=self.GetAxesID())
        self.SetSizeOptions(ax, size_options=size_options)
        ax.yaxis.set_tick_params(labelrotation=90)

        # plot bubbles and annotate with name --------------------------------------------------------------------------
        for bubble in axes_item.GetBubbles():
            ax.scatter(*bubble.GetXYS(), **bubble.GetOptions())
            for (s, x, y) in bubble.GetAnnotations():
                ax.annotate(s, (x, y))

        # configure axes options -----------------------------------------------------------------------------------
        if axes_item.GetNumberOfAxes():
            ax.set(**axes_item.GetXOptions(), **axes_item.GetYOptions(0))

        ax.legend(handles=axes_item.GetLegend())

        ax.minorticks_on()
        ax.grid(True)

        # draw chart on canvas
        self.canvas.draw()

        # Splitting chart into quadrants if relevant -------------------------------------------------------------------
        #if options.has_support(self.x) and options.has_support(self.y):
        #    self.ax.plot(options.get_average_limit(self.x), options.limit[self.y], 'k--')
        #    self.ax.plot(options.limit[self.x], options.get_average_limit(self.y), 'k--')


class HistogramChartPanel(DisplayChartPanel, MultiAxis):
    def __init__(self, parent, window_id, chart_id):
        DisplayChartPanel.__init__(self, parent, window_id, chart_id)
        MultiAxis.__init__(self, self.fig)

    def Realize(self, axes_item=None, size_options=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder(size_options=size_options)
            return

        self.fig.clf()
        # Create required axes' ----------------------------------------------------------------------------------------
        axes = self.AllocateAxes(axes_item)

        if size_options is not None:
            for ax in axes:
                self.SetSizeOptions(ax, size_options=size_options)

        # plot objectives ----------------------------------------------------------------------------------------------
        for i, histogram in enumerate(axes_item.GetHistograms()):
            if histogram is not None:
                i = histogram.GetAxes()
                axes[i].hist(histogram.GetX(), **histogram.GetOptions())

        # configure x-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            ax = axes[i * (axes_item.GetSubAxes() + 1)]
            ax.set(**axes_item.GetXOptions(i))

        # configure y-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetNumberOfAxes()):
            axes[i].set(**axes_item.GetYOptions(i))

        # set axis' ----------------------------------------------------------------------------------------------------
        self.AdjustSubplotSpace(*axes_item.GetLayout())
        self.SetSpineLocations(axes_item, axes)

        # Gather legend at position at last chart of each axes ---------------------------------------------------------
        legends = self.PositionLegends(axes_item, axes_item.GetHistograms())
        for i in range(0, axes_item.GetAxes()):
            idx = (i + 1) * (axes_item.GetSubAxes() + 1) - 1
            axes[idx].legend(handles=legends[i], **axes_item.GetLegendOptions(i))

        # position grid at first chart of each axes --------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            idx = i * (axes_item.GetSubAxes() + 1)
            axes[idx].grid(True)

        # draw chart on canvas -----------------------------------------------------------------------------------------
        self.canvas.draw()


class MapChartPanel(DisplayChartPanel, MultiAxis):
    def __init__(self, parent, window_id, chart_id):
        DisplayChartPanel.__init__(self, parent, window_id, chart_id)
        MultiAxis.__init__(self, self.fig)

    def Realize(self, axes_item=None, size_options=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder(size_options=size_options)
            return

        self.fig.clf()
        # Create required axes' ----------------------------------------------------------------------------------------
        axes = self.AllocateAxes(axes_item)

        if size_options is not None:
            for ax in axes:
                self.SetSizeOptions(ax, size_options=size_options)

        # plot polygons ------------------------------------------------------------------------------------------------
        polygons = axes_item.GetPolygons()
        if polygons:
            for i, polygon in enumerate(polygons):
                self.PlotItems(axes_item.GetOutlines(), axes[i])
                self.PlotItems(axes_item.GetTrajectories(), axes[i])
                axes[i].add_collection(polygon)
                self.fig.colorbar(polygon, ax=axes[i])

        else:
            self.PlotItems(axes_item.GetOutlines(), axes[0])
            self.PlotItems(axes_item.GetTrajectories(), axes[0])

        # configure x & y-axis options ---------------------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            ax = axes[i * (axes_item.GetSubAxes() + 1)]
            ax.set(**axes_item.GetXOptions(i))
            ax.axis('equal')

        # set axis' ----------------------------------------------------------------------------------------------------
        self.AdjustSubplotSpace(*axes_item.GetLayout())
        self.SetSpineLocations(axes_item, axes)

        # draw chart on canvas -----------------------------------------------------------------------------------------
        self.canvas.draw()

    @staticmethod
    def PlotItems(items, ax):
        for item in items:
            if item is not None:
                ax.plot(*item.GetXY(), **item.GetOptions())


class ThreeDChartPanel(DisplayChartPanel):
    def __init__(self, parent, template_id, chart_id):
        super().__init__(parent, template_id, chart_id)

    def Realize(self, axes_item=None, size_options=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder(size_options=size_options)
            return

        # pre-allocate axes --------------------------------------------------------------------------------------------
        self.fig.clf()
        ax = self.fig.add_subplot(1, 1, 1, label=self.GetAxesID(), projection='3d')
        self.SetSizeOptions(ax, size_options=size_options)

        # plot bubbles and annotate with name --------------------------------------------------------------------------
        for trajectory in axes_item.GetTrajectories():
            if trajectory is not None:
                ax.plot(*trajectory.GetXY(), trajectory.GetZ(), **trajectory.GetOptions())

        # configure axes options -----------------------------------------------------------------------------------
        if axes_item.GetNumberOfAxes():
            ax.set(**axes_item.GetXOptions())

        #ax.legend(handles=axes_item.GetLegend())

        #ax.minorticks_on()
        #ax.grid(True)

        # draw chart on canvas
        self.canvas.draw()


class FitChartPanel(DisplayChartPanel, MultiAxis):
    def __init__(self, parent, window_id, chart_id):
        DisplayChartPanel.__init__(self, parent, window_id, chart_id)
        MultiAxis.__init__(self, self.fig)

    def Realize(self, axes_item=None, size_options=None):
        if (axes_item is None) or (not axes_item.GetNumberOfAxes()):
            self.DrawPlaceholder(size_options=size_options)
            return

        self.fig.clf()
        # Create required axes' ----------------------------------------------------------------------------------------
        axes = self.AllocateAxes(axes_item)

        if size_options is not None:
            for ax in axes:
                self.SetSizeOptions(ax, size_options=size_options)

        # draw lines ---------------------------------------------------------------------------------------------------
        for l, line in enumerate(axes_item.GetLines()):
            if line is not None:
                i = line.GetAxes()
                axes[i].plot(*line.GetXY(), **line.GetOptions())

        # configure x-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            ax = axes[i * (axes_item.GetSubAxes() + 1)]
            ax.set(**axes_item.GetXOptions(i))
            ax.minorticks_on()
            self.FormatXAxis(ax, axes_item.XIsDate(i))

        # configure y-axis options -------------------------------------------------------------------------------------
        for i in range(0, axes_item.GetNumberOfAxes()):
            axes[i].set(**axes_item.GetYOptions(i))

        self.AdjustSubplotSpace(*axes_item.GetLayout())
        self.SetSpineLocations(axes_item, axes)

        # Gather legend at position at last chart of each axes ---------------------------------------------------------
        legends = self.PositionLegends(axes_item, axes_item.GetLines())
        for i in range(0, axes_item.GetAxes()):
            idx = (i + 1) * (axes_item.GetSubAxes() + 1) - 1
            axes[idx].legend(handles=legends[i], **axes_item.GetLegendOptions(i))

        # position grid at first chart of each axes --------------------------------------------------------------------
        for i in range(0, axes_item.GetAxes()):
            idx = i * (axes_item.GetSubAxes() + 1)
            axes[idx].grid(True)

        # draw chart on canvas
        self.canvas.draw()

    def GetTooltipParams(self, event):
        return self.GetLineTooltipParams(event)