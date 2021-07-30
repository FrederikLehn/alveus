import wx

# ======================================================================================================================
# Ribbon IDs
# ======================================================================================================================
ID_WINDOW = wx.ID_HIGHEST + 1
ID_WINDOW_SPLIT = ID_WINDOW + 1
ID_WINDOW_REFRESH = ID_WINDOW_SPLIT + 1
ID_WINDOW_PRESENT = ID_WINDOW_REFRESH + 1

ID_CHART_CARTESIAN = ID_WINDOW_PRESENT + 1
ID_CHART_STACKED = ID_CHART_CARTESIAN + 1
ID_CHART_BAR = ID_CHART_STACKED + 1
ID_CHART_BUBBLE = ID_CHART_BAR + 1
ID_CHART_HISTOGRAM = ID_CHART_BUBBLE + 1
ID_CHART_MAP = ID_CHART_HISTOGRAM + 1
ID_CHART_3D = ID_CHART_MAP + 1
ID_CHART_FIT = ID_CHART_3D + 1
ID_CHART_TREND = ID_CHART_FIT + 1
ID_CHART_INCREMENT = ID_CHART_TREND + 1
ID_CHART_PROFILES = ID_CHART_INCREMENT + 1

ID_EXPORT_EXCEL = ID_CHART_PROFILES + 1

ID_FOLDER = ID_EXPORT_EXCEL + 1
ID_FIELD = ID_FOLDER + 1
ID_BLOCK = ID_FIELD + 1
ID_RESERVOIR = ID_BLOCK + 1
ID_THEME = ID_RESERVOIR + 1
ID_POLYGON = ID_THEME + 1
ID_PRODUCER = ID_POLYGON + 1
ID_INJECTOR = ID_PRODUCER + 1
ID_SCALING = ID_INJECTOR + 1
ID_ANALOGUE = ID_SCALING + 1
ID_TYPECURVE = ID_ANALOGUE + 1
ID_PLATFORM = ID_TYPECURVE + 1
ID_PROCESSOR = ID_PLATFORM + 1
ID_PIPELINE = ID_PROCESSOR + 1
ID_PROJECT = ID_PIPELINE + 1
ID_HISTORY = ID_PROJECT + 1
ID_SCENARIO = ID_HISTORY + 1
ID_PREDICTION = ID_SCENARIO + 1

ID_CORRELATION_ENT = ID_PREDICTION + 1
ID_CORRELATION_VAR = ID_CORRELATION_ENT + 1

ID_SUMMARY = ID_CORRELATION_VAR + 1

# ======================================================================================================================
# Entity/Window family types
# ======================================================================================================================
ID_WELL_FAMILY = ID_SUMMARY + 1
ID_NETWORK_FAMILY = ID_WELL_FAMILY + 1
ID_CASE_FAMILY = ID_NETWORK_FAMILY + 1
ID_PORTFOLIO_FAMILY = ID_CASE_FAMILY + 1

ID_WINDOW_FAMILY = ID_PORTFOLIO_FAMILY + 1
ID_CHART_FAMILY = ID_WINDOW_FAMILY + 1

# ======================================================================================================================
# IDs for item deletion dialogs
# ======================================================================================================================
ID_PROMPT_YESTOALL = 0
ID_PROMPT_YES = 1
ID_PROMPT_NO = 2
ID_PROMPT_CANCEL = 3

# ======================================================================================================================
# IDs for ItemData of pre-defined items
# ======================================================================================================================
ID_FIELDS = 0
ID_BLOCKS = 1
ID_FACILITIES = 2
ID_SUBSURFACE = 3
ID_PORTFOLIO = 4
ID_SIMULATIONS = 5

# ======================================================================================================================
# Function IDs
# ======================================================================================================================
ID_HIS = 0
ID_MAV = 1

ID_CON = 0
ID_LIN = 1
ID_EXP = 2
ID_POW = 3
ID_LOG = 4

ID_EXP_DCA = 0
ID_HYP_DCA = 1
ID_HAR_DCA = 2

ID_BOW = 0

ID_SMOOTH = 1
ID_COND = 2


# ======================================================================================================================
# Variable IDs
# ======================================================================================================================
ID_POTENTIAL = 0
ID_RATE = 1
ID_CUMULATIVE = 2
ID_RATIO = 3
ID_UPTIME = 4

# ======================================================================================================================
# Generic IDs (account for BitmapComboBox and RadioBox indices)
# ======================================================================================================================
ID_EMPTY = 0

ID_SORT = 0
ID_X_AXIS = 1
ID_Y_AXIS = 2
ID_Z_AXIS = 3

ID_FIRST = 1
ID_LAST = 2
ID_SPECIFIC = 3

ID_ON_X_AXIS = 1
ID_ON_Y_AXIS = 2

ID_DATA_NO = 0
ID_DATA_YES = 1

ID_UNCERTAINTY_NO = 0
ID_UNCERTAINTY_YES = 1

ID_SPLIT_NONE = 0
ID_SPLIT_ENTITY = 1
ID_SPLIT_SIMULATION = 2
ID_SPLIT_VARIABLE = 3

ID_GROUP_NONE = 0
ID_GROUP_UNIT = 1

ID_UNIT_FIELD = 0
ID_UNIT_METRIC = 1

ID_PREDICTION_TYPECURVE = 0
ID_PREDICTION_FUNCTION = 1
ID_PREDICTION_IMPORT = 2

ID_OIL = 0
ID_GAS = 1

ID_WATER_INJ = 0
ID_GAS_INJ = 1
ID_WAG_INJ = 2

ID_DIST_SWANSON = 1
ID_DIST_UNIFORM = 2
ID_DIST_TRIANGULAR = 3
ID_DIST_NORMAL = 4
ID_DIST_LOGNORMAL = 5

ID_YEARLY = 0
ID_QUARTERLY = 1
ID_MONTHLY = 2
ID_DELTA = 3

ID_POINT = 0
ID_SUM = 1
ID_AVERAGE = 2

ID_POINT_FIRST = 0
ID_POINT_LAST = 1
ID_POINT_DATE = 2
ID_POINT_TIME = 3


# ======================================================================================================================
# Surface Network Model IDs
# ======================================================================================================================
ID_OIL_NW = 0
ID_GAS_NW = 1
ID_WATER_NW = 2
ID_LIQUID_NW = 3
ID_INJ_GAS_NW = 4
ID_INJ_WATER_NW = 5
ID_LIFT_GAS_NW = 6
