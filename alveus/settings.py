from _ids import ID_UNIT_FIELD

ID_LINE_SIZE_1 = 0
ID_LINE_SIZE_2 = 1
ID_LINE_SIZE_3 = 2
ID_LINE_SIZE_4 = 3
ID_LINE_SIZE_5 = 4
ID_LINE_SIZE_6 = 5
ID_LINE_SIZE_7 = 6
ID_LINE_SIZE_8 = 7
ID_LINE_SIZE_9 = 8
ID_LINE_SIZE_10 = 9

ID_TEXT_SIZE_6 = 0
ID_TEXT_SIZE_8 = 1
ID_TEXT_SIZE_10 = 2
ID_TEXT_SIZE_12 = 3
ID_TEXT_SIZE_14 = 4
ID_TEXT_SIZE_16 = 5
ID_TEXT_SIZE_18 = 6
ID_TEXT_SIZE_20 = 7
ID_TEXT_SIZE_22 = 8
ID_TEXT_SIZE_24 = 9

TEXT_ID_TO_SIZE = {0: 6, 1: 8, 2: 10, 3: 12, 4: 14, 5: 16, 6: 18, 7: 20, 8: 22, 9: 24}

ID_P5 = 0
ID_P10 = 1
ID_20 = 2
ID_P25 = 3
ID_P30 = 4
ID_P40 = 5
ID_P50 = 6
ID_P60 = 7
ID_P70 = 8
ID_P75 = 9
ID_P80 = 10
ID_P90 = 11
ID_P95 = 12

PERCENTILE_ID_TO_VALUE = {0: 5, 1: 10, 2: 20, 3: 25, 4: 30, 5: 40, 6: 50, 7: 60, 8: 70, 9: 75, 10: 80, 11: 90, 12: 95}

ID_RESOLUTION_2 = 0
ID_RESOLUTION_4 = 1
ID_RESOLUTION_6 = 2
ID_RESOLUTION_8 = 3
ID_RESOLUTION_10 = 4

RESOLUTION_ID_TO_VALUE = {0: 2, 1: 4, 2: 6, 3: 8, 4: 10}


class Settings:
    def __init__(self):
        # general
        self._unit_system = ID_UNIT_FIELD  # options: 'field', 'metric'

        # windows
        self._normal_options = NormalChartSizeOptions()
        self._present_options = PresentChartSizeOptions()

        # ensemble
        self._low_case = None       # low case percentile
        self._mid_case = None       # mid case percentile
        self._high_case = None      # high case percentile
        self._resolution = None     # number of shading steps
        self._low_shading = None    # lower bound of shading percentile
        self._high_shading = None   # upper bound of shading percentile
        self._extraction = []       # summary ids used to calculate extraction objectives

        self.DefaultNormalSizeOptions()
        self.DefaultPresentSizeOptions()
        self.DefaultEnsemble()

    def DefaultNormalSizeOptions(self):
        self._normal_options.Default()

    def DefaultPresentSizeOptions(self):
        self._present_options.Default()

    def DefaultEnsemble(self):
        self._low_case = ID_P10
        self._mid_case = ID_P50
        self._high_case = ID_P90

        self._resolution = ID_RESOLUTION_10
        self._low_shading = ID_P10
        self._high_shading = ID_P90

    def DeleteSummary(self, id_):
        if id_ in self._extraction: self._extraction.remove(id_)

    def GetCases(self, id_=True):
        if id_:
            return self._low_case, self._mid_case, self._high_case
        else:
            low = PERCENTILE_ID_TO_VALUE[self._low_case]
            mid = PERCENTILE_ID_TO_VALUE[self._mid_case]
            high = PERCENTILE_ID_TO_VALUE[self._high_case]
            return low, mid, high

    def GetExtraction(self):
        return self._extraction

    def GetShading(self, id_=True):
        if id_:
            return self._resolution, self._low_shading, self._high_shading
        else:
            resolution = RESOLUTION_ID_TO_VALUE[self._resolution]
            low_shading = PERCENTILE_ID_TO_VALUE[self._low_shading]
            high_shading = PERCENTILE_ID_TO_VALUE[self._high_shading]
            return resolution, low_shading, high_shading

    def GetNormalSizeOptions(self):
        return self._normal_options

    def GetPresentSizeOptions(self):
        return self._present_options

    def SetCases(self, low_case, mid_case, high_case):
        self._low_case = low_case
        self._mid_case = mid_case
        self._high_case = high_case

    def SetExtraction(self, extraction):
        self._extraction = extraction

    def SetShading(self, resolution, low_shading, high_shading):
        self._resolution = resolution
        self._low_shading = low_shading
        self._high_shading = high_shading

    def SetNormalSizeOptions(self, *args):
        self._normal_options.Set(*args)

    def SetPresentSizeOptions(self, *args):
        self._present_options.Set(*args)

    def GetUnitSystem(self):
        return self._unit_system


class ChartSizeOptions:
    def __init__(self):

        self._linewidth = None
        self._markersize = None
        self._tick_label_size = None
        self._label_size = None
        self._legend_size = None

    def Get(self):
        return self._linewidth, self._markersize, self._tick_label_size, self._label_size, self._legend_size

    def GetLabelSizes(self):
        tick_label_size = TEXT_ID_TO_SIZE[self._tick_label_size]
        label_size = TEXT_ID_TO_SIZE[self._label_size]
        return tick_label_size, label_size

    def GetLegendSize(self):
        return TEXT_ID_TO_SIZE[self._legend_size]

    def GetLinewidth(self):
        return self._linewidth

    def GetMarkerSize(self):
        return self._markersize

    def Set(self, linewidth, markersize, tick_label_size, label_size, legend_size):
        self._linewidth = linewidth
        self._markersize = markersize
        self._tick_label_size = tick_label_size
        self._label_size = label_size
        self._legend_size = legend_size


class NormalChartSizeOptions(ChartSizeOptions):
    def __init__(self):
        super().__init__()

    def Default(self):
        self._linewidth = ID_LINE_SIZE_3
        self._markersize = ID_LINE_SIZE_5
        self._tick_label_size = ID_TEXT_SIZE_8
        self._label_size = ID_TEXT_SIZE_8
        self._legend_size = ID_TEXT_SIZE_8


class PresentChartSizeOptions(ChartSizeOptions):
    def __init__(self):
        super().__init__()

    def Default(self):
        self._linewidth = ID_LINE_SIZE_4
        self._markersize = ID_LINE_SIZE_7
        self._tick_label_size = ID_TEXT_SIZE_16
        self._label_size = ID_TEXT_SIZE_16
        self._legend_size = ID_TEXT_SIZE_16
