import math
import copy
import numpy as np
import matplotlib
from matplotlib.patches import Patch, Polygon, Circle
from matplotlib.lines import Line2D
from matplotlib.collections import PatchCollection

from _ids import *
import _icons as ico
from variable_mgr import LineOptions, HistogramFrequency

GENERIC_COLOURS = [np.array([0.,   114., 189.]) / 255.,
                   np.array([217., 83.,   25.]) / 255.,
                   np.array([237., 177.,  32.]) / 255.,
                   np.array([126., 47.,  142.]) / 255.,
                   np.array([119., 172.,  48.]) / 255.,
                   np.array([77.,  190., 238.]) / 255.,
                   np.array([162., 20.,   47.]) / 255.,
                   '#1f77b4',
                   '#ff7f0e',
                   '#2ca02c',
                   '#d62728',
                   '#9467bd',
                   '#8c564b',
                   '#e377c2',
                   '#7f7f7f',
                   '#bcbd22',
                   '#17becf']


class ChartManager:
    def __init__(self):

        self._windows = {}
        self._id = -1  # unique key to the windows dictionary

    def AddChart(self, id_, chart):
        window = self._windows[id_]
        window.AddChart(chart)

        if not window.AllowSplit():
            self._windows[id_].SetLabel('{} ({})'.format(self._windows[id_].GetLabel(), len(self._windows)))

    def AddWindow(self, allow_split=False):
        id_ = self.NextId()
        self._windows[id_] = Window(id_, allow_split)
        return self._windows[id_]

    def DeleteChart(self, window_id, chart_id):
        self._windows[window_id].DeleteChart(chart_id)

    def DeleteWindow(self, window):
        del self._windows[window.GetId()]

    def GetAllIds(self):
        return {id_: [chart.GetId() for chart in window.GetCharts()] for id_, window in self._windows.items()}

    def GetChart(self, window_id, chart_id):
        return self._windows[window_id].GetChart(chart_id)

    def GetWindow(self, id_):
        return self._windows[id_]

    def NextId(self):
        self._id += 1
        return self._id


class Window:
    def __init__(self, id_, allow_split=False):
        # information
        self._label = None
        self._charts = {}
        self._allow_split = allow_split
        self._row = 1
        self._col = 1

        # chart management
        self._id = id_
        self._chart_id = -1
        self._type = None
        self._family_type = ID_WINDOW_FAMILY
        self._image_key = None

        # visual
        self._image = None  # PyEmbeddedImage

    def AddChart(self, chart):
        id_ = self.NextId()
        chart.SetId(id_)
        self._charts[id_] = chart

        if not self._allow_split:
            self._label = chart.GetLabel()
            self._image = chart.GetWindowImage()
            self._image_key = '{}_{}'.format(self.GetType(), chart.GetType())

    def AllowSplit(self):
        return self._allow_split

    def DeleteChart(self, chart_id):
        del self._charts[chart_id]

    def GetBitmap(self):
        return self._image.GetBitmap()

    def GetChart(self, id_):
        return self._charts[id_]

    def GetCharts(self):
        return self._charts.values()

    def GetFamilyType(self):
        return self._family_type

    def GetId(self):
        return self._id

    def GetImage(self):
        return self._image

    def GetImageKey(self):
        return self._image_key

    def GetLabel(self):
        return self._label

    @staticmethod
    def GetParentType():
        return 'windows_'

    def GetType(self):
        return self._type

    def Init(self):
        if self._allow_split:
            self._label = 'Split window'
            self._type = ID_WINDOW_SPLIT
            self._image = ico.window_split_16x16

        else:
            self._label = 'Window'
            self._type = ID_WINDOW
            self._image = ico.window_16x16

        self._image_key = self._type

    def NextId(self):
        self._chart_id += 1
        return self._chart_id

    def SetLabel(self, label):
        self._label = label


class Chart:
    def __init__(self):
        # information
        self._label = None

        # object_menu checkbox options
        self._entities = (0, [])   # list of 1x2 tuple with (ct_type, [<ID1>, <ID2>,...])
        self._projects = (0, [])   # list of 1x2 tuple with (ct_type, [<ID1>, <ID2>,...])
        self._variables = (0, [])  # list of 1x2 tuple with (ct_type, ['<type1>', '<type2>',...])
        self._allow_assign = []    # additional variables types that can be assigned to by right-click

        # object_menu right-click options
        self._inc_x = False     # chart needs x-axis variable as input
        self._inc_y = False     # chart needs y-axis variable as input
        self._inc_z = False     # chart needs z variable as input (size/color, etc.)
        self._inc_sort = False  # chart can sort by a variable

        # display options bar includes and states
        self._inc_data = False
        self._inc_uncertainty = False
        self._inc_split = False
        self._inc_group = False
        self._inc_colour = False

        self._data = 0          # id (int)
        self._uncertainty = 0   # id (int)
        self._split = 0         # id (int)
        self._group = 0         # id (int)
        self._colour = 0        # id (int)

        # gui management
        self._id = None    # int
        self._type = None  # id (int)
        self._family_type = ID_CHART_FAMILY

        # visual
        self._image = None
        self._window_image = None

        # auxiliary
        self._refresh = False  # if true, the chart will refresh next time its parent window is switched to

    def DoRefresh(self):
        return self._refresh

    def GetAllowedAssign(self):
        return self._variables[0], self._variables[1] + self._allow_assign

    def GetBitmap(self):
        return self._image.GetBitmap()

    def GetEntities(self):
        return self._entities

    def GetFamilyType(self):
        return self._family_type

    def GetId(self):
        return self._id

    def GetImage(self):
        return self._image

    def GetLabel(self):
        return self._label

    @staticmethod
    def GetParentType():
        return ID_WINDOW_SPLIT

    def GetProjects(self):
        return self._projects

    def GetState(self):
        return self._data, self._uncertainty, self._split, self._group, self._colour

    def GetType(self):
        return self._type

    def GetVariables(self):
        return self._variables

    def GetWindowBitmap(self):
        return self._window_image.GetBitmap()

    def GetWindowImage(self):
        return self._window_image

    def IncludesColour(self):
        return self._inc_colour

    def IncludesData(self):
        return self._inc_data

    def IncludesUncertainty(self):
        return self._inc_uncertainty

    def IncludesGroup(self):
        return self._inc_group

    def IncludesSort(self):
        return self._inc_sort

    def IncludesSplit(self):
        return self._inc_split

    def IncludesX(self):
        return self._inc_x

    def IncludesY(self):
        return self._inc_y

    def IncludesZ(self):
        return self._inc_z

    def SetId(self, id_):
        self._id = id_

    def SetLabel(self, label):
        self._label = label

    def SetRefresh(self, refresh):
        self._refresh = refresh

    def SetState(self, data, uncertainty, split, group, colour):
        self._data = data
        self._uncertainty = uncertainty
        self._split = split
        self._group = group
        self._colour = colour


class CartesianChart(Chart):
    def __init__(self):
        super().__init__()

        self._label = 'Cartesian chart'

        self._entities = (1, [ID_FIELD, ID_BLOCK, ID_RESERVOIR, ID_THEME, ID_POLYGON, ID_PLATFORM,
                              ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR])

        self._projects = (1, [ID_HISTORY, ID_PREDICTION])
        self._variables = (1, ['potentials', 'rates', 'cumulatives', 'ratios', 'uptimes'])
        self._allow_assign = ['durations']

        self._inc_x = True

        self._inc_data = True
        self._inc_uncertainty = True
        self._inc_split = True
        self._inc_group = True

        self._type = ID_CHART_CARTESIAN

        self._image = ico.cartesian_chart_16x16
        self._window_image = ico.window_cartesian_chart_16x16


class StackedChart(Chart):
    def __init__(self):
        super().__init__()

        self._label = 'Stacked chart'

        self._entities = (1, [ID_FIELD, ID_BLOCK, ID_RESERVOIR, ID_THEME, ID_POLYGON, ID_PLATFORM,
                              ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR])

        self._projects = (1, [ID_HISTORY, ID_PREDICTION])
        self._variables = (1, ['potentials', 'rates', 'cumulatives'])
        self._allow_assign = ['durations']

        self._inc_x = True

        self._inc_split = True

        self._type = ID_CHART_STACKED

        self._image = ico.stacked_chart_16x16
        self._window_image = ico.window_stacked_chart_16x16


class BarChart(Chart):
    def __init__(self):
        super().__init__()

        self._label = 'Bar chart'

        self._entities = (1, [ID_FIELD, ID_BLOCK, ID_RESERVOIR, ID_THEME, ID_POLYGON, ID_PLATFORM,
                              ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR])

        self._projects = (1, [ID_HISTORY, ID_PREDICTION])
        self._variables = (1, ['wells', 'res_fluids', 'inj_fluids', 'facilities', 'constraints', 'volumes', 'risking', 'scalers', 'statics', 'summaries'])

        self._inc_sort = True

        self._inc_uncertainty = True
        self._inc_split = True
        self._inc_group = True

        self._type = ID_CHART_BAR

        self._image = ico.bar_chart_16x16
        self._window_image = ico.window_bar_chart_16x16


class BubbleChart(Chart):
    def __init__(self):
        super().__init__()

        self._label = 'Bubble chart'

        self._entities = (1, [ID_FIELD, ID_BLOCK, ID_RESERVOIR, ID_THEME, ID_POLYGON, ID_PLATFORM,
                              ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR])

        self._projects = (1, [ID_HISTORY, ID_PREDICTION])
        self._variables = (0, ['wells', 'res_fluids', 'inj_fluids', 'facilities', 'constraints', 'volumes', 'risking', 'scalers', 'statics', 'summaries'])

        self._inc_x = True
        self._inc_y = True
        self._inc_z = True

        self._type = ID_CHART_BUBBLE

        self._image = ico.bubble_chart_16x16
        self._window_image = ico.window_bubble_chart_16x16


class HistogramChart(Chart):
    def __init__(self):
        super().__init__()

        self._label = 'Histogram chart'

        self._entities = (1, [ID_FIELD, ID_BLOCK, ID_RESERVOIR, ID_THEME, ID_POLYGON, ID_PLATFORM,
                              ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR])

        self._projects = (1, [ID_HISTORY, ID_PREDICTION])
        self._variables = (1, ['summaries'])

        self._type = ID_CHART_HISTOGRAM

        self._image = ico.histogram_chart_16x16
        self._window_image = ico.window_bar_chart_16x16


class MapChart(Chart):
    def __init__(self):
        super().__init__()

        self._label = 'Map chart'

        self._entities = (1, [ID_FIELD, ID_BLOCK, ID_RESERVOIR, ID_THEME, ID_POLYGON, ID_PLATFORM,
                              ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR, ID_ANALOGUE])

        self._projects = (1, [ID_HISTORY, ID_PREDICTION])
        self._variables = (1, ['wells', 'res_fluids', 'inj_fluids', 'facilities', 'constraints', 'volumes', 'risking',
                               'scalers', 'statics', 'summaries'])

        self._type = ID_CHART_MAP

        self._image = ico.map_chart_16x16
        self._window_image = ico.window_map_chart_16x16


class ThreeDChart(Chart):
    def __init__(self):
        super().__init__()

        self._label = '3D chart'

        self._entities = (1, [ID_PRODUCER, ID_INJECTOR, ID_ANALOGUE])

        self._projects = (1, [])
        self._variables = (1, [])

        self._type = ID_CHART_3D

        self._image = ico.threeD_chart_16x16
        self._window_image = ico.window_threeD_chart_16x16


class FitChart(Chart):
    def __init__(self):
        super().__init__()

        self._label = 'Fit chart'

        self._entities = (1, [ID_ANALOGUE])

        self._type = ID_CHART_FIT

        self._image = ico.fit_chart_16x16
        self._window_image = ico.window_fit_chart_16x16


# ======================================================================================================================
# AxesItem (used as input to charts)
# ======================================================================================================================
class AxesItem:
    def __init__(self):
        # plot layout
        self._axes = 0              # number of main axes' (the subplots axes')
        self._sub_axes = 0          # number of twin axes' per main axes
        self._split = False         # True/False for whether axes' are split
        self._uncertainty = False   # True/False for whether uncertainty is included
        self._layout = (1, 1)       # Layout of split axes'

        self._xoptions = []         # list of dictionaries containing x-axis options
        self._yoptions = []         # list of dictionaries containing y-axis options
        self._legendoptions = []    #

        # primary plot items
        self._lines = []
        self._stackedlines = []
        self._bars = []
        self._bubbles = []
        self._histograms = []

        # mapping items
        self._outlines = []
        self._polygons = []
        self._trajectories = []

        # secondary plot items
        self._low = []      # similar to self._lines (used to display selected low)
        self._high = []     # similar to self._lines (used to display selected high)
        self._shading = []  # list of shading classes (used for displaying shaded cone of uncertainty)

    def MergeLines(self, x, variables, entities, simulations, size_options, settings, show_data=ID_DATA_NO,
                   show_uncertainty=ID_UNCERTAINTY_NO, split_by=ID_SPLIT_NONE, group_by=ID_GROUP_NONE):

        if (x is None) or (not variables) or (not entities) or (not simulations and not show_data):
            return

        units = {}

        s = len(simulations)
        e = len(entities)
        v = len(variables)
        se = s * e

        self._xoptions.append(LineXOptions(x))

        # loop variables -----------------------------------------------------------------------------------------------
        for i, variable in enumerate(variables):
            # allocate variables to grouped axis'
            unit = variable.GetUnit()
            if group_by:
                if unit in units.keys():
                    axis = units[unit][0]
                    self._yoptions[axis].UpdateLim(variable, entities, simulations, show_data=show_data,
                                                   show_uncertainty=show_uncertainty)
                else:
                    axis = len(units)
                    units[unit] = [axis, 0]
                    self._yoptions.append(AxesYOptions(variable, entities, simulations, show_data=show_data,
                                                       show_uncertainty=show_uncertainty, group_units=True))

            else:
                axis = i
                units[unit] = [axis, 0]
                self._yoptions.append(AxesYOptions(variable, entities, simulations, show_data=show_data,
                                                   show_uncertainty=show_uncertainty))

            # loop entities --------------------------------------------------------------------------------------------
            for j, entity in enumerate(entities):

                # add data ---------------------------------------------------------------------------------------------
                if show_data:

                    history = entity.GetHistory()

                    if history is None:
                        self._lines.append(None)
                        self._low.append(None)
                        self._high.append(None)
                        self._shading.append(None)

                    else:
                        xd = history.Get(x.GetId())
                        yd = history.Get(variable.GetId())

                        line = LineItem(xd, yd)
                        line.SetAxes(axis)

                        option = copy.deepcopy(variable.GetLineOptions())
                        option.SetMarker('o')
                        option.SetMarkerSize(size_options.GetMarkerSize())
                        option.SetLinewidth(0)

                        # merge data colours ---------------------------------------------------------------------------
                        if s > 0:  # simulation with or without data
                            if (se > 1) and (v > 1) and (split_by == ID_SPLIT_VARIABLE):
                                option.SetColour(GetGenericColour(units[unit][1]))

                            elif (se > 1) and (split_by in (ID_SPLIT_NONE, ID_SPLIT_VARIABLE)):
                                option.SetColour(GetGenericColour(s * (j + i * e)))

                            elif (se > 1) and (e != 1) and (split_by == ID_SPLIT_SIMULATION):
                                option.SetColour(GetGenericColour((j + i * e)))

                            elif (v > 1) and (split_by != ID_SPLIT_VARIABLE):
                                pass  # keep variable colour

                            elif (v > 1) and (split_by == ID_SPLIT_VARIABLE) and (group_by == ID_GROUP_UNIT):
                                pass  # keep variable colour

                            else:
                                pass  # keep variable colour

                        else:  # data only
                            if (e > 1) and (split_by in (ID_SPLIT_NONE, ID_SPLIT_SIMULATION)):
                                option.SetColour(GetGenericColour(j + i * e))

                            elif (e > 1) and (split_by == ID_SPLIT_VARIABLE):
                                option.SetColour(GetGenericColour(units[unit][1]))
                                units[unit][1] += 1

                        # merge data labels ----------------------------------------------------------------------------
                        option.SetLabel(MergeLabels(option.GetLabel(), entity.GetName(), 'Data', v,
                                                    split_by=split_by, group_by=group_by))

                        line.SetOptions(option)
                        self._lines.append(line)
                        self._low.append(None)
                        self._high.append(None)
                        self._shading.append(None)

                # loop simulations -------------------------------------------------------------------------------------
                for k, simulation in enumerate(simulations):

                    # define line item
                    xd = entity.GetSimulationProfile(simulation, x.GetId())
                    yd = entity.GetSimulationResult(simulation)

                    if yd is None:
                        self._lines.append(None)
                        self._low.append(None)
                        self._high.append(None)
                        self._shading.append(None)
                        continue

                    line = LineItem(xd, yd.GetProfile(variable.GetId()))
                    line.SetAxes(axis)

                    option = copy.deepcopy(variable.GetLineOptions())

                    # merge prediction colours -------------------------------------------------------------------------
                    if (se > 1) and (split_by == ID_SPLIT_NONE):
                        option.SetColour(GetGenericColour(k + s * (j + i * e)))

                    elif (se > 1) and (s != 1) and (split_by == ID_SPLIT_ENTITY):
                        option.SetColour(GetGenericColour(k + i * s))

                    elif (se > 1) and (e != 1) and (split_by == ID_SPLIT_SIMULATION):
                        option.SetColour(GetGenericColour(j + i * e))

                    elif (se > 1) and (split_by == ID_SPLIT_VARIABLE):
                        option.SetColour(GetGenericColour(units[unit][1]))
                        units[unit][1] += 1

                    # merge prediction labels --------------------------------------------------------------------------
                    option.SetLabel(MergeLabels(option.GetLabel(), entity.GetName(), simulation.GetName(), v,
                                                split_by=split_by, group_by=group_by))

                    option.SetLinewidth(size_options.GetLinewidth())
                    line.SetOptions(option)
                    self._lines.append(line)

                    # define uncertainty item
                    if show_uncertainty and simulation.IsPrediction():
                        self._low.append(yd.GetLowProfile(variable.GetId()))
                        self._high.append(yd.GetHighProfile(variable.GetId()))

                        shading = yd.GetShading(*settings.GetShading(False), variable.GetId())

                        if shading is not None:
                            self._shading.append(ShadingItem(shading, option.GetColour()))
                        else:
                            self._shading.append(None)

                    else:
                        self._low.append(None)
                        self._high.append(None)
                        self._shading.append(None)

        # Configure subplot
        if show_data:
            s += 1

        if group_by:
            v = len(units)

        self._uncertainty = show_uncertainty

        self.ConfigureSubplot(self._lines, v, e, s, split_by)
        self.SetLegendOptions(variables, entities, simulations, size_options, show_data=show_data, split_by=split_by, group_by=group_by)

    def MergeStackedLines(self, x, variables, entities, simulations, size_options, split_by=ID_SPLIT_VARIABLE):
        if (x is None) or (not variables) or (not entities) or (not simulations):
            return

        s = len(simulations)
        e = len(entities)
        v = len(variables)

        # sort entities according to time and the first variable of the first simulation
        entities = SortEntities(entities, simulations[0], x, variable=variables[0])

        self._xoptions.append(LineXOptions(x))

        for i, variable in enumerate(variables):

            self._yoptions.append(AxesYOptions(variable))

            for j, simulation in enumerate(simulations):

                options = StackedLineOptions()
                stackedline = StackedLineItem()
                stackedline.SetBaselineDuration(x, entities, simulations)

                for entity in entities:
                    options.Append(entity.GetName())

                    xd = entity.GetSimulationProfile(simulation, x.GetId())
                    yd = entity.GetSimulationProfile(simulation, variable.GetId())

                    if xd is not None:
                        stackedline.AppendY(xd, yd)

                stackedline.SetOptions(options)
                stackedline.AdjustStart()
                stackedline.SetAxes(i)
                self._stackedlines.append(stackedline)

        self._xoptions[0].SetLim(*GetLimits(x, entities, simulations, relaxed=False))

        # Configure subplot
        self.ConfigureSubplot(self._stackedlines, v, 1, s, split_by=split_by)
        self.SetLegendOptions(variables, entities, simulations, size_options, split_by=split_by, group_by=False)

    def MergeBars(self, variables, entities, simulations, split_by=None, group_by=False, sort_by=None):
        if (not variables) or (not entities):
            return

        v = len(variables)
        e = len(entities)
        s = len(simulations)

        # prepare axis grouping scheme
        units = {}  # dictionary of lists {unit: [axis, count of variables on axis]}
        axis = []
        count = {}

        sort_idx = 0

        # allocate variables to grouped axis' and determine variables per unit -----------------------------------------
        idx = 0
        for variable in variables:

            if sort_by == variable.GetId():
                sort_idx = idx

            # if variable is a summary, each associated simulation becomes an independent variable
            if variable.IsSummary():
                for _ in simulations:
                    self.GroupBars(variable, entities, simulations, units, axis, count, group_by, idx)
                    idx += 1
                    v += 1

                v -= 1  # accounts for the double count of 1 variable already being counted

            else:
                self.GroupBars(variable, entities, simulations, units, axis, count, group_by, idx)
                idx += 1

        # generate bars now all variables per axes is known and consequently width/position ----------------------------
        idx = 0
        for variable in variables:
            if variable.IsSummary():
                for simulation in simulations:
                    width, delta = self.BarPosition(variable, units, count, split_by, group_by, idx, v)
                    self.AssignBars(variable, entities, width, delta, axis, idx, simulation=simulation)
                    idx += 1

            else:
                width, delta = self.BarPosition(variable, units, count, split_by, group_by, idx, v)
                self.AssignBars(variable, entities, width, delta, axis, idx)
                idx += 1

        # children names
        self._xoptions.append(BarXOptions([entity.GetName() for entity in entities]))

        # configure subplot
        if group_by:
            v = len(units)

        self.ConfigureSubplot(self._bars, v, e, s, split_by=split_by)

        # sorting
        if sort_by is not None:
            # TODO: use ArgSort instead?
            p = self._bars[sort_idx].Sort()
            for bar in self._bars:
                bar.Sort(p)

    def AssignBars(self, variable, entities, width, delta, axis, idx, simulation=None):
        options = BarOptions()

        label = variable.GetLegend()
        if simulation is not None:
            label += ' - ' + simulation.GetName()

        options.SetLabel(label)

        options.SetWidth(width)
        options.SetColour(GetGenericColour(idx))

        bar = BarItem(options=options)
        bar.SetAxes(axis[idx])

        for j, entity in enumerate(entities):

            if simulation is None:

                try:
                    property_ = entity.GetProperties().Get(variable.GetType(), variable.GetId())
                except AttributeError:
                    property_ = None

            else:
                property_ = entity.GetSimulationSummary(simulation, variable.GetId())

            if property_ is not None:
                bar.Append(j + delta, property_)

        self._bars.append(bar)

    def BarPosition(self, variable, units, count, split_by, group_by, i, v):
        space = 1.
        entity_padding = 0.05

        if split_by != ID_SPLIT_VARIABLE:
            width = (space - 2. * entity_padding) / v
            delta = (i - (v - 1.) / 2.) * width
        else:
            if group_by:
                v_g = units[variable.GetUnit()][1]
                width = (space - 2. * entity_padding) / v_g
                idx = count[variable.GetUnit()]
                delta = (idx - (v_g - 1) / 2.) * width
                count[variable.GetUnit()] += 1
            else:
                width = (space - 2. * entity_padding)
                delta = 0.

        return width, delta

    def GroupBars(self, variable, entities, simulations, units, axis, count, group_by, idx):
        #         count = {variable.GetUnit(): 0 for variable in variables}

        if group_by:
            if variable.GetUnit() in units.keys():
                axis.append(units[variable.GetUnit()][0])
                units[variable.GetUnit()][1] += 1
                #self._yoptions[axis[-1]].UpdateLim(variable, entities, simulations)
            else:
                axis.append(len(units))
                units[variable.GetUnit()] = [axis[-1], 1]
                count[variable.GetUnit()] = 0
                self._yoptions.append(AxesYOptions(variable, group_units=group_by))

        else:
            axis.append(idx)
            units[variable.GetUnit()] = [axis, 1]
            count[variable.GetUnit()] = 0
            self._yoptions.append(AxesYOptions(variable))

    def MergeBubbles(self, x, y, z, entities, simulations):
        if (x is None) or (y is None) or (z is None) or not entities:
            return

        self._xoptions.append(LineXOptions(x))
        self._yoptions.append(AxesYOptions(y))

        options = BubbleOptions()
        options.SetLabel(z.GetMenuLabel())
        options.SetColour(GetGenericColour(0))

        bubble = BubbleItem(options=options)

        # if one or more variables are summaries, sizes of array have to be adjusted
        includes_summary = False
        if x.IsSummary() or y.IsSummary() or z.IsSummary():
            includes_summary = True

        # allocating x-properties
        _xs = self.AllocateBubbles(x, entities, simulations, includes_summary)
        _ys = self.AllocateBubbles(y, entities, simulations, includes_summary)
        _zs = self.AllocateBubbles(z, entities, simulations, includes_summary)

        for (_x, _y, _z) in zip(_xs, _ys, _zs):
            if (_x is not None) and (_y is not None) and (_z is not None):
                bubble.AppendXYS(_x, _y, _z)

        for entity in entities:
            for _ in range(len(simulations) if includes_summary else 1):
                bubble.AppendLabel(entity.GetName())

        self._bubbles.append(bubble)

        self.ConfigureSubplot(self._bubbles, 1, 1, 1)

    def AllocateBubbles(self, variable, entities, simulations, includes_summary):
        array = []

        if variable.IsSummary():
            for entity in entities:
                for simulation in simulations:
                    array.append(entity.GetSimulationSummary(simulation, variable.GetId()))

        else:
            if includes_summary:
                for entity in entities:
                    for _ in simulations:
                        array.append(entity.GetProperties().Get(variable.GetType(), variable.GetId()))

            else:
                for entity in entities:
                    array.append(entity.GetProperties().Get(variable.GetType(), variable.GetId()))

        return array

    def MergeHistograms(self, variables, entities, simulations, size_options):
        if (not variables) or (not entities):
            return

        v = len(variables)
        e = len(entities)
        s = len(simulations)

        for i, variable in enumerate(variables):

            self._xoptions.append(HistogramXOptions(variable=variable))
            self._yoptions.append(AxesYOptions(HistogramFrequency()))

            for j, entity in enumerate(entities):

                for k, simulation in enumerate(simulations):

                    result = entity.GetSimulationResult(simulation)

                    summaries = result.GetSummaries()
                    x = np.asarray([s[variable.GetId()] for s in summaries])

                    option = HistogramOptions()

                    if result.HasShading():
                        option.SetBins(int(x.size / 10))
                    else:
                        option.SetBins(3)

                    option.SetColour(GetGenericColour(j + e * k))
                    option.SetLabel('{} - {}'.format(entity.GetName(), simulation.GetName()))

                    histogram = HistogramItem(x, option)
                    histogram.SetAxes(i)

                    if x.sum():
                        self._histograms.append(histogram)
                    else:
                        self._histograms.append(None)

        # Configure subplot
        self.ConfigureSubplot(self._histograms, v, e, s, split_by=ID_SPLIT_VARIABLE)
        self.SetLegendOptions(variables, entities, simulations, size_options, split_by=ID_SPLIT_VARIABLE)

    def MergeMaps(self, variables, entities):
        if not entities:
            return

        v = len(variables)
        e = len(entities)
        polygons = []
        polygon_values = {v.GetId(): [] for v in variables}

        self._xoptions.append(MapAxisOptions())  # will set both x and y

        for i, entity in enumerate(entities):

            cultural = entity.GetCultural()

            if cultural is None:
                continue

            # outlines ---------------------------------------------------------------------------------------------
            if entity.IsField() or entity.IsBlock():

                options = OutlineOptions()
                outline = OutlineItem(cultural.GetX(), cultural.GetY(), options)

                self._outlines.append(outline)

            # trajectories -----------------------------------------------------------------------------------------
            if entity.IsProducer() or entity.IsInjector() or entity.IsAnalogue():

                options = TrajectoryOptions()

                if entity.IsProducer():

                    options.SetColour(np.array([0., 176., 80.]) / 255.)

                elif entity.IsInjector():

                    options.SetColour(np.array([91., 155., 213.]) / 255.)

                elif entity.IsAnalogue():

                    options.SetColour(np.array([219., 34., 211.]) / 255.)

                trajectory = TrajectoryItem(cultural.GetX(), cultural.GetY(), options=options)

                self._trajectories.append(trajectory)

            # polygons coloured by variable ------------------------------------------------------------------------
            if entity.IsReservoir() or entity.IsTheme() or entity.IsPolygon():
                polygons.append(Polygon(np.vstack((cultural.GetX(), cultural.GetY())).T))

                for variable in variables:
                    id_ = variable.GetId()

                    try:
                        value = entity.GetProperties().Get(variable.GetType(), id_)
                        if value is not None:
                            polygon_values[id_].append(value)
                        else:
                            polygon_values[id_].append(0.)
                    except AttributeError:
                        polygon_values[id_].append(0.)

        if polygons:
            for variable in variables:
                collection = PatchCollection(polygons, cmap=matplotlib.cm.jet, alpha=0.5)
                collection.set_array(np.array(polygon_values[variable.GetId()]))
                self._polygons.append(collection)

        # Configure subplot
        self.ConfigureSubplot(self._outlines, max(v, 1), e, 1, split_by=ID_SPLIT_VARIABLE)

    def Merge3D(self, entities):
        if not entities:
            return

        e = len(entities)

        self._xoptions.append(ThreeDAxisOptions())  # will set both x and y

        for i, entity in enumerate(entities):

            cultural = entity.GetCultural()

            if cultural is None:
                continue

            # trajectories -----------------------------------------------------------------------------------------
            options = TrajectoryOptions()

            if entity.IsProducer():

                options.SetColour(np.array([0., 176., 80.]) / 255.)

            elif entity.IsInjector():

                options.SetColour(np.array([91., 155., 213.]) / 255.)

            elif entity.IsAnalogue():

                options.SetColour(np.array([219., 34., 211.]) / 255.)

            trajectory = TrajectoryItem(cultural.GetX(), cultural.GetY(), cultural.GetZ(), options=options)

            self._trajectories.append(trajectory)

        self.ConfigureSubplot(self._trajectories, 1, 1, 1, split_by=ID_SPLIT_NONE)

    # used both for displaying in Display and on CurvefitFrame / FunctionFrame
    def MergeFits(self, profile, xs, ys, ms=(), size_options=None):
        """
        Merge input for plotting a FitChart.

        Parameters
        ----------
        profile : Profile
            Class Profile
        xs : list
            A list of class Variable
        ys : list
            A list of class Variable
        ms : list
            A list of tuples of class Model

        Returns
        -------
        list
            List of class Entity
        """

        if not profile or not len(xs) or not len(ys):
            return

        if not ms:
            ms = [() for _ in xs]

        for i, (x, y, models) in enumerate(zip(xs, ys, ms)):
            self._xoptions.append(LineXOptions(x, relaxed=False))
            self._yoptions.append(AxesYOptions(y))

            # setting limits
            start = min(profile.Get(x.GetId()))
            end = max(profile.Get(x.GetId()))
            if x.GetId() == 'date':
                delta = (end - start) / 20.
                start -= delta
                end += delta
            else:
                start -= .5
                end += .5

            self._xoptions[-1].SetLim(start, end)

            # data
            option = copy.deepcopy(y.GetLineOptions())
            option.SetMarker('o')
            option.SetMarkerSize(3)
            option.SetLinewidth(0)
            option.SetLabel('Data')

            data = LineItem(profile.Get(x.GetId()), profile.Get(y.GetId()), option)
            data.SetAxes(i)
            self._lines.append(data)

            # fitted data ----------------------------------------------------------------------------------------------
            # all fitted data points are concatenated as one data set
            option = y.GetFittedOptions()
            line = LineItem(options=option, x_is_date=x.IsDate())
            x_ = []

            for model in models:
                temp = model.GetX()
                if not temp.size:
                    x_.append(None)
                    continue

                if x.GetId() in ('year', 'time'):
                    x_.append((((temp - temp[0]).astype('Float64')) + (temp[0] - profile.Get('date')[0]).astype('Float64')))
                else:
                    x_.append(temp)

                line.AppendXY(x_[-1], model.GetY())

            line.SetAxes(i)
            self._lines.append(line)

            # fitted functions -----------------------------------------------------------------------------------------
            for j, model in enumerate(models):
                if model.GetMethod() is None or not model.GetValues()[0].size:
                    continue

                # fitted line
                option = FittedLineOptions()
                option.SetColour(GetGenericColour(j))
                option.SetLabel(model)

                x_, y_ = model.GetValues()
                if x.GetId() in ('year', 'time'):
                    x_ = (((x_ - x_[0]).astype('Float64')) + (x_[0] - profile.Get('date')[0]).astype('Float64'))

                line = LineItem(x_, y_, option)
                line.SetAxes(i)
                self._lines.append(line)

        # Configure subplot
        self.ConfigureSubplot(self._lines, len(xs), 1, 1, ID_SPLIT_VARIABLE)

        if size_options:
            self.SetLegendOptions(ys, (), (), size_options, split_by=ID_SPLIT_VARIABLE)

    def MergeProfiles(self, entities):
        if not entities:
            return

        xs = ['year', 'year', 'year', 'oil_cum']
        ys = ['oil_rate', 'liquid_rate', 'oil_cum', 'water_cut']

        for i, (x, y) in enumerate(zip(xs, ys)):
            self._xoptions.append(LineXOptions(x))
            self._yoptions.append(AxesYOptions(y))

            self._xoptions[-1].SetLim(*GetLimits(entities, x))

            for j, entity in enumerate(entities):
                option = LineOptions()
                option.SetMarkerStyle(y, entity.IsDerived())
                option.SetColour(GetGenericColour(j))
                option.SetLabel(entity.GetName())

                line = LineItem(entity.GetProfile(x), entity.GetProfile(y), option)
                line.SetAxes(i)

                self._lines.append(line)

        # Configure subplot
        self.ConfigureSubplot(self._lines, 4, len(entities), 'variable')

    def MergeScaledHistory(self, xs, ys, entities):
        if (not xs) or (not ys) or (not entities) or (len(xs) != len(ys)):
            return

        s = 1
        e = len(entities)
        v = len(xs)
        se = s * e

        for i, (x, y) in enumerate(zip(xs, ys)):
            self._xoptions.append(LineXOptions(x))
            self._yoptions.append(AxesYOptions(y))

            # loop variables -------------------------------------------------------------------------------------------
            for j, entity in enumerate(entities):

                history = entity.GetHistory()
                xd = history.Get(x.GetId())
                yd = history.Get(y.GetId())

                line = LineItem(xd, yd)
                line.SetAxes(i)

                option = copy.deepcopy(y.GetLineOptions())
                option.SetLabel(entity.GetName())
                option.SetMarker('o')
                option.SetMarkerSize(3)
                option.SetLinewidth(0)
                option.SetColour(GetGenericColour(j))

                line.SetOptions(option)
                self._lines.append(line)

        self.ConfigureSubplot(self._lines, v, e, 1, split_by=ID_SPLIT_VARIABLE)
        self.SetLegendOptions(ys, entities, (), split_by=ID_SPLIT_VARIABLE)

    def MergeStability(self, x, variables, stability):
        samples, v, s = stability.shape
        labels = (r'$\mu$', r'$\sigma$')
        linestyles = (0, 1)  # linestyle ids

        self._xoptions.append(LineXOptions(x))
        xd = range(samples)

        for i, variable in enumerate(variables):

            self._yoptions.append(AxesYOptions(variable))
            min_val = min(stability[:, i, :].min(0))
            max_val = max(stability[:, i, :].max(0))
            self._yoptions[-1].SetLim(min_val * 0.95, max_val * 1.05)

            for j in range(s):

                line = LineItem(xd, stability[:, i, j])
                line.SetAxes(i)

                # set options --------------------------------------------------------------------------
                option = copy.deepcopy(variable.GetLineOptions())
                option.SetLabel(labels[j])
                option.SetLinestyle(linestyles[j])

                line.SetOptions(option)
                self._lines.append(line)

        self.ConfigureSubplot(self._lines, v, s, 1, split_by=ID_SPLIT_VARIABLE)
        self.SetLegendOptions(variables, (), (), split_by=ID_SPLIT_VARIABLE)

    def MergeTotalProduction(self, x, variables, dateline, historical, simulated):
        if (x is None) or (not variables):
            return

        s = 1
        e = 1
        v = len(variables)
        se = s * e

        self._xoptions.append(LineXOptions(x))

        # loop variables -----------------------------------------------------------------------------------------------
        for i, variable in enumerate(variables):

            self._yoptions.append(AxesYOptions(variable))

            # add historical
            line = LineItem(dateline, historical.Get(variable.GetId()))
            line.SetAxes(i)

            option = copy.deepcopy(variable.GetLineOptions())
            option.SetLabel('Data')
            option.SetMarker('o')
            option.SetMarkerSize(3)
            option.SetLinewidth(0)
            # option.SetColour('k')

            line.SetOptions(option)
            self._lines.append(line)

            # add simulated
            line = LineItem(dateline, simulated.Get(variable.GetId()))
            line.SetAxes(i)

            option = copy.deepcopy(variable.GetLineOptions())
            option.SetLabel('Simulated')
            option.SetLinestyle(1)  # '--'
            line.SetOptions(option)
            self._lines.append(line)

        self.ConfigureSubplot(self._lines, v, 1, 1, split_by=ID_SPLIT_VARIABLE)
        self.SetLegendOptions(variables, (), (), split_by=ID_SPLIT_VARIABLE)

    def ConfigureSubplot(self, items, v, e, s, split_by=ID_SPLIT_NONE):

        if split_by == ID_SPLIT_NONE:
            self._axes = 1
            self._sub_axes = v - 1
            return

        elif split_by == ID_SPLIT_VARIABLE:
            self._axes = v
            self._sub_axes = 0

        elif split_by == ID_SPLIT_ENTITY:
            self._axes = e
            self._sub_axes = v - 1

            if e > 1:
                j = 0
                k = 1
                for item in items:
                    if item is not None:
                        item.SetAxes(item.GetAxes() + j * v)

                    if k < s:
                        k += 1
                    elif (j > 0) and (not j % (e - 1)):
                        j = 0
                        k = 1
                    else:
                        j += 1
                        k = 1

        elif split_by == ID_SPLIT_SIMULATION:
            self._axes = s
            self._sub_axes = v - 1

            if s > 1:
                j = 0
                for item in items:
                    if item is not None:
                        item.SetAxes(item.GetAxes() + j * v)

                    if (j > 0) and (not j % (s - 1)):
                        j = 0
                    else:
                        j += 1

        # adjust axes
        if split_by in (ID_SPLIT_ENTITY, ID_SPLIT_SIMULATION):
            # if split by entity or simulation, additional yoptions are duplicated by the number of axes'
            # TODO: Possibly here an option for whether to share y-axis can be implemented
            for _ in range(1, self._axes):  # minimum changed from 0
                for opt in list(self._yoptions):
                    self._yoptions.append(opt)

        self.SetLayout()

        if self._axes > 1:
            self._split = True

    def SetLayout(self):
        n = float(self._axes)

        if not n:
            self._layout = (1, 1)
            return

        r = round(math.sqrt(n))
        c = math.ceil(n / r)

        self._layout = (r, c)

    def SetLegendOptions(self, variables, entities, simulations, size_options=None, show_data=ID_DATA_NO,
                         split_by=ID_SPLIT_NONE, group_by=ID_GROUP_NONE):

        s = len(simulations)
        e = len(entities)
        v = len(variables)

        if show_data:
            s += 1

        se = s * e

        if split_by == ID_SPLIT_NONE:

            self._legendoptions = [{} for _ in entities]

        elif split_by == ID_SPLIT_VARIABLE:

            if (group_by == ID_GROUP_UNIT) and v > 1:
                self._legendoptions = [{} for _ in variables]

            else:

                try:
                    self._legendoptions = [{'title': variable.GetPlotLabel()} for variable in variables]  # .GetLineOptions().GetLabel()

                except AttributeError:
                    self._legendoptions = [{'title': variable.GetLegend()} for variable in variables]

        elif split_by == ID_SPLIT_ENTITY:

            self._legendoptions = [{'title': entity.GetName()} for entity in entities]

        elif split_by == ID_SPLIT_SIMULATION:

            self._legendoptions = [{'title': simulation.GetName()} for simulation in simulations]

            if show_data:
                self._legendoptions = [{'title': 'Data'}] + self._legendoptions

        else:
            self._legendoptions = [{} for _ in range(0, se)]

        if size_options is not None:
            for option in self._legendoptions:
                option['fontsize'] = size_options.GetLegendSize()
                option['title_fontsize'] = size_options.GetLegendSize()

    def GetLegendOptions(self, i):
        return self._legendoptions[i]

    def GetLayout(self):
        return self._layout

    def GetLegend(self):
        legend = []
        for line in self._lines:
            legend.append(line.GetLegend())

        for line in self._stackedlines:
            legend.append(line.GetLegend())

        for bar in self._bars:
            legend.append(bar.GetLegend())

        for bubble in self._bubbles:
            legend.append(bubble.GetLegend())

        for histogram in self._histograms:
            legend.append(histogram.GetLegend())

        return legend

    def GetYOptions(self, i):
        return self._yoptions[i].Get()

    def GetXOptions(self, i=0):
        if i >= len(self._xoptions):
            i = 0
        return self._xoptions[i].Get()

    def GetNumberOfAxes(self):
        return self._axes * (1 + self._sub_axes)

    def GetAxes(self):
        return self._axes

    def GetSubAxes(self):
        return self._sub_axes

    def GetLines(self):
        return self._lines

    def GetStackedLines(self):
        return self._stackedlines

    def GetBars(self):
        return self._bars

    def GetBubbles(self):
        return self._bubbles

    def GetHistograms(self):
        return self._histograms

    def GetOutlines(self):
        return self._outlines

    def GetTrajectories(self):
        return self._trajectories

    def GetPolygons(self):
        return self._polygons

    def GetShading(self, i):
        """
        Follows the configuration of self._lines, so only sampled one at a time
        :param i: int, index
        :return: class UncertaintyItem()
        """
        if len(self._shading) < i:
            return None
        else:
            return self._shading[i]

    def GetHighY(self, i):
        return self._high[i]

    def GetLowY(self, i):
        return self._low[i]

    def IsSplit(self):
        return self._split

    def ShowUncertainty(self):
        return self._uncertainty

    def XIsDate(self, i=0):
        if i >= len(self._xoptions):
            i = 0
        return self._xoptions[i].IsDate()


class PlotItem:
    def __init__(self):
        self._options = None
        self._axes = 0

    def SetAxes(self, axes):
        self._axes = axes

    def GetAxes(self):
        return self._axes

    def SetOptions(self, options):
        self._options = options

    def GetOptions(self):
        return self._options.Get()

    def CopyOptions(self):
        return copy.deepcopy(self._options)

    def GetLegend(self):
        return self._options.GetLegend()

    def Highlight(self):
        self._options.Highlight()

    def UnHighlight(self):
        self._options.UnHighlight()


class LineItem(PlotItem):
    def __init__(self, x=None, y=None, options=None, x_is_date=False):
        super().__init__()

        if x is not None:
            self._x = x
        else:
            if x_is_date:
                self._x = np.array([], dtype='datetime64[D]')
            else:
                self._x = np.empty(0)

        self._y = y if y is not None else np.empty(0)

        self._options = options if options is not None else LineOptions()

    def AppendXY(self, x, y):
        self._x = np.append(self._x, x)
        self._y = np.append(self._y, y)

    def RemoveXY(self, idx):
        self._x = np.delete(self._x, idx)
        self._y = np.delete(self._y, idx)

    def GetX(self):
        return self._x

    def GetY(self):
        return self._y

    def GetXY(self):
        return self._x, self._y

    def ClearXY(self):
        self._x = np.empty(0)
        self._y = np.empty(0)


class StackedLineItem(PlotItem):
    def __init__(self, x=None, options=None):
        super().__init__()
        self._x = x
        self._ys = []
        self._options = options if options is not None else StackedLineOptions()
        self._start = None

    def AppendY(self, time, y):
        self._ys.append(self.AdjustToBaseline(time, y))

    def GetX(self):
        return self._x

    def GetYs(self):
        return self._ys

    def SetBaselineDuration(self, x, entities, simulations):
        start, end = GetLimits(x, entities, simulations, relaxed=False)
        self._start = start
        self._x = np.linspace(0., (end - start).astype(np.float64), 500)

    def AdjustToBaseline(self, x, y):
        return np.interp(self._x, (x - self._start).astype(np.float64), y, left=0.0, right=0.0)

    def AdjustStart(self):
        if type(self._start) == np.datetime64:
            self._x = self._start + self._x.astype(np.uint64)


class BarItem(PlotItem):
    def __init__(self, x=None, height=None, options=None):
        super().__init__()
        self._x = x if x is not None else np.empty(0)
        self._height = height if height is not None else np.empty(0)
        self._options = options if options is not None else BarOptions()

    def Append(self, x, height):
        self._x = np.append(self._x, x)
        self._height = np.append(self._height, height)

    def Get(self):
        return self._x, self._height

    def Sort(self, p=None):
        if p is None:
            p = np.argsort(self._height)

        self._height = self._height[p]

        return p


class BubbleItem(PlotItem):
    def __init__(self, x=np.empty(0), y=np.empty(0), s=np.empty(0), labels=None, options=None):
        super().__init__()
        self._x = x
        self._y = y
        self._s = s
        self._labels = labels if labels is not None else []
        self._options = options if options is not None else BubbleOptions()

    def AppendXYS(self, x, y, s):
        self._x = np.append(self._x, x)
        self._y = np.append(self._y, y)
        self._s = np.append(self._s, s)

    def GetAnnotations(self):
        return zip(self._labels, self._x * 1.025, self._y * 1.025)

    def GetXYS(self):
        if not self._s.size:
            return [], [], []

        max_ = self._s.max()

        if max_:
            s = self._s * (2000. / max_)
        else:
            s = self._s

        return self._x, self._y, s

    def AppendLabel(self, label):
        self._labels.append(label)


class HistogramItem(PlotItem):
    def __init__(self, x=np.empty(0), options=None):
        super().__init__()

        self._x = x
        self._options = options if options is not None else HistogramOptions()

    def GetX(self):
        return self._x


class OutlineItem(PlotItem):
    def __init__(self, x=np.empty(0), y=np.empty(0), options=None):
        super().__init__()

        self._x = x
        self._y = y
        self._options = options if options is not None else OutlineOptions()

    def GetXY(self):
        return self._x, self._y


class TrajectoryItem(PlotItem):
    def __init__(self, x=np.empty(0), y=np.empty(0), z=np.empty(0), options=None):
        super().__init__()

        self._x = x
        self._y = y
        self._z = z
        self._options = options if options is not None else TrajectoryOptions()

    def GetXY(self):
        return self._x, self._y

    def GetZ(self):
        return self._z


class ShadingItem:
    def __init__(self, shading, colour):
        self._resolution = shading.shape[1] - 1
        self._ys = shading
        self._options = []

        mid = int(self._resolution / 2.)
        for i in range(mid - 1, -1, -1):
            alpha = .7 - .5 * i / float(mid)
            self._options.append(ShadingOptions(alpha=alpha, colour=colour))

        for i in range(mid - 1, -1, -1):
            self._options.append(self._options[i])

    def GetOptions(self, i):
        return self._options[i - 1].Get()

    def GetResolution(self):
        return 1, self._resolution + 1

    def GetYs(self, i):
        return self._ys[:, i-1], self._ys[:, i]


# ======================================================================================================================
# Plot options
# ======================================================================================================================
class AxesOptions:
    def __init__(self, variable=None, entities=None, simulations=None, show_data=False, show_uncertainty=False, relaxed=True):
        self._label = None

        if variable is not None and entities is not None:
            self._lim = GetLimits(variable, entities, simulations, show_data=show_data, show_uncertainty=show_uncertainty, relaxed=relaxed)
        elif variable is not None:
            self._lim = variable.GetLimits()

    def Get(self):
        return {'xlabel': self._label,
                'xlim':   self._lim}

    def SetLabel(self, label):
        self._label = label

    def SetLim(self, minimum=None, maximum=None):
        lim = [self._lim[0], self._lim[1]]
        if minimum is not None:
            lim[0] = minimum

        if maximum is not None:
            lim[1] = maximum

        self._lim = lim


class LineXOptions(AxesOptions):
    def __init__(self, x=None, entities=None, relaxed=True):
        super().__init__(x, entities=entities, relaxed=relaxed)

        self._is_date = x.IsDate()

        if not self._is_date:
            self._label = x.GetXLabel()

    def Get(self):
        return {'xlabel': self._label,
                'xlim':   self._lim}

    def IsDate(self):
        return self._is_date


class BarXOptions(AxesOptions):
    def __init__(self, labels=None):
        super().__init__()
        self._lim = None
        self._ticks = None
        self._ticklabels = None

        if labels is not None:
            self._lim = (-0.5, len(labels) - 0.5)
            self._ticks = np.arange(0, len(labels))
            self._ticklabels = labels

    def Get(self):
        return {'lim':         self._lim,
                'xticks':      self._ticks,
                'xticklabels': self._ticklabels}


class HistogramXOptions(AxesOptions):
    def __init__(self, variable=None):
        super().__init__(variable=variable)

        if variable is not None:
            self._label = variable.GetXLabel()


class MapAxisOptions(AxesOptions):
    def __init__(self):
        super().__init__()

    def Get(self):
        return {'xlabel': 'X-direction [m]',
                'ylabel': 'Y-direction [m]'}


class ThreeDAxisOptions(AxesOptions):
    def __init__(self):
        super().__init__()

    def Get(self):
        return {'xlabel': 'X-direction [m]',
                'ylabel': 'Y-direction [m]',
                'zlabel': 'Z-direction [ft]'}


class AxesYOptions(AxesOptions):
    def __init__(self, variable=None, entities=None, simulations=None, show_data=False, show_uncertainty=False, group_units=False):
        super().__init__(variable, entities, simulations, show_data=show_data, show_uncertainty=show_uncertainty)

        self._label = variable.GetYLabel(group_units)

    def UpdateLim(self, variable, entities, simulations, show_data=False, show_uncertainty=False):
        self._lim = GetLimits(variable, entities, simulations, show_data=show_data, show_uncertainty=show_uncertainty, relaxed=True, existing_lim=self._lim)

    def Get(self):
        return {'ylabel': self._label,
                'ylim':   self._lim}


class StackedLineOptions:
    def __init__(self):
        self._alpha = 0.8       # double, [0, 1]
        self._colours = []      # list of (R, G, B) normalized to [0, 1]
        self._edgecolour = 'k'  # colour
        self._labels = []       # list of str

    def Append(self, label):
        self._labels.append(label)
        self._colours.append(GetGenericColour(len(self._colours)))

    def Get(self):
        return {'alpha':     self._alpha,
                'colors':    self._colours,
                'edgecolor': self._edgecolour,
                'labels':    self._labels}

    def GetLegend(self):
        return [Patch(color=colour, label=label, alpha=self._alpha) for colour, label in zip(self._colours, self._labels)]


class BarOptions:

    def __init__(self, colour=None, edgecolour='black', label=None, width=None):
        self._align = 'center'
        self._alpha = 0.8
        self._colour = colour
        self._edgecolour = edgecolour
        self._label = label
        self._width = width

    def Get(self):
        return {'align':     self._align,
                'alpha':     self._alpha,
                'color':     self._colour,
                'edgecolor': self._edgecolour,
                'width':     self._width}

    def SetColour(self, colour):
        self._colour = colour

    def SetLabel(self, label):
        self._label = label

    def SetWidth(self, width):
        self._width = width

    def GetLegend(self):
        return Patch(alpha=self._alpha, edgecolor=self._edgecolour, facecolor=self._colour, label=self._label)


class BubbleOptions:
    def __init__(self):
        self._alpha = 0.8
        self._colour = None
        self._edgecolour = np.array([0., 0., 0.])
        self._label = None

    def Get(self):
        return {'alpha': self._alpha,
                'c': self._colour,
                'edgecolors': self._edgecolour}

    def GetLegend(self):
        return Line2D([], [], color=self._colour, label=self._label)

    def SetColour(self, colour):
        self._colour = colour

    def SetLabel(self, label):
        self._label = label


class HistogramOptions:
    def __init__(self):
        self._alpha = 0.8
        self._bins = None
        self._colour = None
        self._edgecolour = np.array([0., 0., 0.])
        self._label = None

    def Get(self):
        return {'alpha':     self._alpha,
                'bins':      self._bins,
                'color':     self._colour,
                'edgecolor': self._edgecolour}

    def SetBins(self, bins):
        self._bins = bins

    def SetColour(self, colour):
        self._colour = colour

    def SetLabel(self, label):
        self._label = label

    def GetLegend(self):
        return Patch(alpha=self._alpha, edgecolor=self._edgecolour, facecolor=self._colour, label=self._label)


class OutlineOptions:
    def __init__(self):

        self._colour = np.array([0., 0., 0.])

    def Get(self):
        return {'color': self._colour}

    def SetColour(self, colour):
        self._colour = colour


class TrajectoryOptions:
    def __init__(self):

        self._colour = np.array([0., 0., 0.])

    def Get(self):
        return {'color': self._colour}

    def SetColour(self, colour):
        self._colour = colour


# class FittedDataOptions(LineOptions):
#     # TODO: DELETE
#     def __init__(self, variable=None):
#         super().__init__()
#         self._label = 'Fitted data'
#         self._fillstyle = 'none'
#         self._linewidth = 0.
#         self._marker = 'o'
#
#         self.SetColour(variable.GetFitColour())


class FittedLineOptions(LineOptions):
    def __init__(self, variable=None):
        super().__init__()

    def SetLabel(self, fun):
        self._label = fun.GetLabel()#FIT_LINE_LEGENDS[fun.GetMethod()]

        # adding parameters to legend
        #par_names = list(fun.GetAvailableParameters()[fun.GetMethod()])
        #if par_names:
        #    self._label += '('
        #
        #    for i, par in enumerate(fun.GetParameters()):
        #        self._label += '{}={}, '.format(par_names[i], round(par, 3))  # FIT_LINE_PARAMETERS
        #
        ## adding input to legend
        #inp_names = list(fun.GetAvailableInput()[fun.GetMethod()])
        #if inp_names and not par_names:
        #    self._label += '('
        #
        #if inp_names:
        #    input_ = fun.GetInput()
        #    for i in range(0, len(inp_names) - 1):
        #        self._label += '{}={}, '.format(inp_names[i], input_[i])  # FIT_LINE_PARAMETERS
        #
        #    i = len(inp_names) - 1
        #    self._label += '{}={})'.format(inp_names[i], input_[i])  # FIT_LINE_PARAMETERS
        #
        #if par_names and not inp_names:
        #    self._label = self._label[:-2] + ')'  # removing last appended comma and space


class ShadingOptions:
    def __init__(self, alpha=None, colour=None):
        self._alpha = alpha
        self._colour = colour
        self._linewidth = 0.

    def Get(self):
        return {'alpha': self._alpha,
                'color': self._colour,
                'linewidth': self._linewidth}


# ======================================================================================================================
# Generic functions
# ======================================================================================================================
def PrimarySort(profile, x):
    return profile.GetProfile(x.GetId())[0]


def SecondarySort(profile, variable):
    return -np.sum(profile.GetProfile(variable.GetId()))


def SortEntities(entities, simulation, x, variable=None):
    v = variable

    profiles = [e.GetSimulationResult(simulation) for e in entities]
    sequence = [(e, p) for e, p in zip(entities, profiles) if p.GetProfile() is not None]

    if variable is not None:
        sequence = [e for e, p in sorted(sequence, key=lambda s: (PrimarySort(s[1], x), SecondarySort(s[1], v)))]
    else:
        sequence = [e for e, p in sorted(sequence, key=lambda s: (PrimarySort(s[1], x)))]

    # adding entities which had None profiles at the end of the list
    for e in entities:
        if e not in sequence:
            sequence.append(e)

    return sequence


def GetGenericColour(i):
    return GENERIC_COLOURS[i % len(GENERIC_COLOURS)]

    # TODO: Use something along the lines of below code to make changes to colours, using the generic colours as base
    #self.col = (self.col + 3) % 241
    #return wx.Colour(0, self.col * 10 % 255, self.col % 255)


def GetLimits(variable, entities, simulations=None, show_data=False, show_uncertainty=False, relaxed=True, existing_lim=None):
    v = variable.GetId()
    start, end = variable.GetLimits()

    # allocating all profiles
    profiles = [e.GetSimulationProfile(s, v) for e in entities for s in simulations]

    # include data
    if show_data:
        profiles += [e.GetHistory(v) for e in entities if e.GetHistory() is not None]

    # include uncertainty cone
    if show_uncertainty:
        for s in simulations:
            if s.IsPrediction():
                for e in entities:
                    result = e.GetSimulationResult(s)
                    profiles += [result.GetLowProfile(v)]
                    profiles += [result.GetHighProfile(v)]

    if not profiles:
        return start, end

    if start is None:

        if simulations is None:

            start = min([min(e.GetHistory(v)) for e in entities])

        else:

            lowest = [min(p) for p in profiles if p is not None]

            if lowest:
                start = min(lowest)

            if relaxed and (start is not None):
                start *= 0.95

    if end is None:

        if simulations is None:

            end = max([max(e.GetHistory(v)) for e in entities])

        else:

            highest = [max(p) for p in profiles if p is not None]

            if highest:
                end = max(highest)

            if relaxed and (end is not None):
                end *= 1.05

    if existing_lim is not None:

        start = start if existing_lim[0] is None else min(start, existing_lim[0])
        end = end if existing_lim[1] is None else max(end, existing_lim[1])

    # ensure start < end
    if ((start is not None) and (end is not None)) and (start >= end):
        start, end = None, None

    return start, end


def MergeLabels(variable_label, entity_name, simulation_name, v, split_by=ID_SPLIT_NONE, group_by=ID_GROUP_NONE):
    """
    Returns a correctly merged label for
    :param variable_label: variable label (defined in Variable Manager)
    :param entity_name: str
    :param simulation_name: str
    :param v: int, number of variables passed to Merge function
    :param split_by: id
    :param group_by: id
    :return:
    """

    label = ''
    prev = False
    if not (split_by == ID_SPLIT_ENTITY):
        label += entity_name
        prev = True

    if not (split_by == ID_SPLIT_SIMULATION):
        if prev:
            label += ' - '

        label += simulation_name
        prev = True

    if not (split_by == ID_SPLIT_VARIABLE):
        if prev:
            label += ' - '

        label += variable_label

    elif (v > 1) and (split_by == ID_SPLIT_VARIABLE) and (group_by == ID_GROUP_UNIT):
        if prev:
            label += ' - '

        label += variable_label

    return label