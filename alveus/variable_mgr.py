from datetime import date
import numpy as np

from matplotlib.lines import Line2D

from _ids import *
import _icons as ico
from utilities import pydate2wxdate, wxdate2pydate, GetAttributes
from properties import SummaryProperty


class VariableManager:
    def __init__(self, unit_system):
        # simulation dependent -----------------------------------------------------------------------------------------
        # times
        self._time = Time()
        self._date = Date()

        # potentials
        self._oil_potential = OilPotential(unit_system)
        self._gas_potential = GasPotential(unit_system)
        self._water_potential = WaterPotential(unit_system)
        self._liquid_potential = LiquidPotential(unit_system)
        self._lift_gas_potential = LiftGasPotential(unit_system)
        self._gas_injection_potential = GasInjectionPotential(unit_system)
        self._water_injection_potential = WaterInjectionPotential(unit_system)
        self._total_gas_potential = TotalGasPotential(unit_system)

        # rates
        self._oil_rate = OilRate(unit_system)
        self._gas_rate = GasRate(unit_system)
        self._water_rate = WaterRate(unit_system)
        self._liquid_rate = LiquidRate(unit_system)
        self._lift_gas_rate = LiftGasRate(unit_system)
        self._gas_injection_rate = GasInjectionRate(unit_system)
        self._water_injection_rate = WaterInjectionRate(unit_system)
        self._total_gas_rate = TotalGasRate(unit_system)

        # cumulatives
        self._oil_cumulative = OilCumulative(unit_system)
        self._gas_cumulative = GasCumulative(unit_system)
        self._water_cumulative = WaterCumulative(unit_system)
        self._liquid_cumulative = LiquidCumulative(unit_system)
        self._lift_gas_cumulative = LiftGasCumulative(unit_system)
        self._gas_injection_cumulative = GasInjectionCumulative(unit_system)
        self._water_injection_cumulative = WaterInjectionCumulative(unit_system)
        self._total_gas_cumulative = TotalGasCumulative(unit_system)

        # ratios
        self._water_cut = WaterCut(unit_system)
        self._oil_cut = OilCut(unit_system)
        self._gas_oil_ratio = GasOilRatio(unit_system)
        self._water_oil_ratio = WaterOilRatio(unit_system)
        self._gas_liquid_ratio = GasLiquidRatio(unit_system)
        self._water_gas_ratio = WaterGasRatio(unit_system)
        self._oil_gas_ratio = OilGasRatio(unit_system)
        self._total_gas_liquid_ratio = TotalGasLiquidRatio(unit_system)
        self._production_uptime = ProductionUptime(unit_system)
        self._lift_gas_uptime = LiftGasUptime(unit_system)
        self._gas_injection_uptime = GasInjectionUptime(unit_system)
        self._water_injection_uptime = WaterInjectionUptime(unit_system)

        # user-defined summary variables
        self._summaries = {}

        # non-simulation dependent -------------------------------------------------------------------------------------
        # wells
        self._well_spacing = WellSpacing(unit_system)

        # reservoir fluids
        self._bo = OilFVF(unit_system)
        self._bg = GasFVF(unit_system)
        self._bw = WaterFVF(unit_system)
        self._rs = SolutionGasOilRatio(unit_system)

        # injection fluids
        self._bg_inj = InjectionGasFVF(unit_system)
        self._bw_inj = InjectionWaterFVF(unit_system)

        # facilities
        self._availability = Availability(unit_system)
        self._tglr = TargetGasLiquidRatio(unit_system)
        self._wag_cycle = WAGCycleDuration(unit_system)
        self._wag_cycles = WAGCycles(unit_system)
        self._voidage_ratio = TargetVoidageRatio(unit_system)

        # constraints
        self._oil_constraint = OilConstraint(unit_system)
        self._gas_constraint = GasConstraint(unit_system)
        self._water_constraint = WaterConstraint(unit_system)
        self._liquid_constraint = LiquidConstraint(unit_system)
        self._gas_inj_constraint = InjectionGasConstraint(unit_system)
        self._water_inj_constraint = InjectionWaterConstraint(unit_system)
        self._gas_lift_constraint = LiftGasConstraint(unit_system)

        # volumes
        self._stoiip = STOIIP(unit_system)

        # risking
        self._maturity = Maturity(unit_system)
        self._pos = ProbabilityOfSuccess(unit_system)

        # scalers
        self._s_cum = CumulativeScaler(unit_system)
        self._s_rate = RateScaler(unit_system)
        self._s_ffw = FFWScaler(unit_system)
        self._s_ffg = FFGScaler(unit_system)
        self._onset = OnsetScaler(unit_system)
        self._wct_ini = InitialWCTScaler(unit_system)

        # statics TODO: Change to a dictionary and let user fill with only useful parameters
        self._length = CompletedLength(unit_system)
        self._hcft = HydrocarbonFeet(unit_system)
        self._hcpv = HydrocarbonPoreVolume(unit_system)
        self._permeability = Permeability(unit_system)
        self._oil_density = OilDensity(unit_system)

        # correlation matrix for the scalers and static parameters -----------------------------------------------------
        self._correlation_labels = []
        self._correlation_matrix = []
        self.InitialiseCorrelationMatrix()

    def AddCorrelation(self, variable):
        if self._correlation_matrix:
            for row in self._correlation_matrix:
                row.append(0.)

        self._correlation_matrix.append([0.] * (len(self._correlation_matrix) + 1))
        self._correlation_matrix[-1][-1] = 1.

        self._correlation_labels.append(variable.GetMenuLabel())

    def AddSummary(self, summary):
        id_ = self.GetUniqueSummaryId()
        summary.SetId(id_)
        self._summaries[id_] = summary

    def DeleteSummary(self, id_):
        del self._summaries[id_]

    def Get(self, type_, id_=None):
        if id_ is None:
            return list(getattr(self, '_{}'.format(type_)).values())
        else:
            return getattr(self, '_{}'.format(type_))[id_]

    def GetAllVariables(self):
        return GetAttributes(self, exclude=('_correlation_labels', '_correlation_matrix'), sort=True)

    def GetCorrelationMatrix(self):
        return self._correlation_matrix, self._correlation_labels

    def GetSummaries(self):
        return self._summaries.values()

    def GetVariable(self, id_):
        attr = '_{}'.format(id_)
        if hasattr(self, attr):
            return getattr(self, attr)
        else:
            return self._summaries[id_]

    def GetVariables(self, ids):
        return [self.GetVariable(id_) for id_ in ids]

    def GetUniqueSummaryId(self):
        ids = self._summaries.keys()
        if not ids:
            return 0
        else:
            return max(ids) + 1

    def InitialiseCorrelationMatrix(self):
        attrs = GetAttributes(self, exclude=('_summaries', '_correlation_labels', '_correlation_matrix'), attr_only=True, sort=True)
        for attr in attrs:
            if attr.IsStatic() or attr.IsScaler():
                self.AddCorrelation(attr)

    def SetCorrelationMatrix(self, correlation_matrix):
        self._correlation_matrix = correlation_matrix


# ======================================================================================================================
# Generic Variables
# ======================================================================================================================
class Variable:
    def __init__(self):
        self._unit = None               # subclass of class Unit
        self._frame_label = None        # label shown on wx.Frames
        self._menu_label = None         # label shown in treectrls
        self._image = None              # PyEmbeddedImage shown in trees, etc.
        self._choices = None            # list of strings, which can be given as input to wx.Choice, etc.
        self._choice_images = None      # list of PyEmbeddedImage which can be passed to bitmapcombobox
        self._client_data_map = None    # dictionary of client_data for each index in bitmapcombobox
        self._limits = (None, None)     # limiting values for input and on plot axis'

        # plot options
        self._line_options = None       # class of LineOptions
        self._fitted_options = None     # class of FittedDataOptions
        self._legend = None             # string, used for bar and bubble charts

        # axis options (plotting)
        self._plot_label = None         # label shown in Matplotlib plots
        self._is_date = False           # required for plotting of dates

        # to and from Frame options
        self._round_off = None          # round-off used for wx.Frame displays of variables (if pytype is float)
        self._pytype = None             # python-type

        # tooltip
        self._tooltip = None            # str, tooltip to be displayed on hover

        # variable management
        self._type = None               # str
        self._id = None                 # str, allows access to variable_mgr via getattr(self, id_)
        self._type_id = None            # int, id to test against
        self._image_key = None

    def FromFrame(self, value):

        if self._pytype is not str and value == '':

            return None

        elif self._pytype is bool:

            return value

        elif self._pytype is float:

            return float(value)

        elif self._pytype is int:

            return int(value)

        elif self._pytype is date:

            return wxdate2pydate(value)

        elif self._pytype is str:

            return str(value)

        elif (self._pytype is list) or (self._pytype is tuple):

            if value == -1:  # default selection in a combobox/choice

                return None

            else:

                return value

        elif self._pytype is Pointer:

            return value

        elif self._pytype is Index:

            return value

        elif self._pytype is wx.Colour:

            return value

    def GetAttribute(self):
        return '_{}'.format(self._type)

    def GetBitmap(self):
        if self._image is not None:
            return self._image.GetBitmap()
        else:
            return wx.NullBitmap

    def GetImage(self):
        return self._image

    def GetChoices(self, idx=None):
        if idx is None:
            return [choice if choice is not None else '' for choice in self._choices]
        else:
            return self._choices[idx]

    def GetChoiceBitmaps(self):
        return [image.GetBitmap() if (image is not None) else wx.NullBitmap for image in self._choice_images]

    def GetClientDataMap(self):
        return self._client_data_map

    def GetComboLabel(self):
        return self._frame_label

    def GetFittedOptions(self):
        return self._fitted_options

    def GetFrameLabel(self, idx=None):
        if isinstance(self._frame_label, tuple) and idx is None:
            return ('{}:'.format(l) for l in self._frame_label)

        if idx is None:
            if self._frame_label is None:
                return None

            label = self._frame_label
        else:
            if self._frame_label[idx] is None:
                return None

            label = self._frame_label[idx]

        return '{}:'.format(label)

    def GetId(self):
        return self._id

    def GetImageKey(self):
        return self._image_key

    def GetLabel(self):
        return self._frame_label

    def GetLegend(self):
        return self._legend

    def GetLimits(self):
        return self._limits

    def GetLineOptions(self):
        return self._line_options

    def GetMenuLabel(self):
        return self._menu_label

    def GetPlotLabel(self):
        return self._line_options.GetLabel()

    def GetToolTip(self):
        return self._tooltip

    def GetType(self):
        return self._type

    def GetTypeId(self):
        return self._type_id

    def GetUnit(self, idx=None):
        if idx is None:
            unit = self._unit
        else:
            unit = self._unit[idx]

        if unit is None or isinstance(unit, str) or isinstance(unit, tuple):
            return unit
        else:
            return unit.Get()

    def GetUnitClass(self):
        return self._unit

    def GetXLabel(self):
        unit = self._unit.Get()
        if unit:
            if ('^' in unit) or ('_' in unit):
                return r'{} [${}$]'.format(self._plot_label, unit)
            else:
                return r'{} [{}]'.format(self._plot_label, unit)
        else:
            return r'{}'.format(self._plot_label)

    def GetYLabel(self, group_units=False):
        if group_units:
            label = self._unit.GetLabel()
        else:
            label = self._plot_label

        unit = self._unit.Get()
        if ('^' in unit) or ('_' in unit):
            unit_label = r'[${}$]'.format(unit)
        elif unit == '':
            unit_label = r'[-]'
        else:
            unit_label = r'[{}]'.format(unit)

        return r'{} {}'.format(label, unit_label)

    def IsDate(self):
        return self._is_date

    def IsScaler(self):
        return self.IsType('scalers')

    def IsStatic(self):
        return self.IsType('statics')

    def IsSummary(self):
        return self.IsType('summaries')

    def IsType(self, type_):
        return self._type == type_

    def SetBitmap(self, bitmap):
        self._bitmap = bitmap

    def SetImage(self, image_key=None):
        self._image_key = self._id

    def SetUnit(self, unit_system):
        pass

    def SetUnitClass(self, unit_class):
        self._unit = unit_class

    def ToFrame(self, value):

        if ((self._pytype is float) or (self._pytype is int)) and value is None:

            return ''

        elif self._pytype is bool:

            return value

        elif self._pytype is float:

            return str(round(value, self._round_off))

        elif self._pytype is int:

            return str(value)

        elif self._pytype is date:

            if value is None:  # occurs on first load

                return wx.DateTime.Now()

            else:

                return pydate2wxdate(value)

        elif self._pytype is str:

            if value is None:

                return ''

            else:

                return str(value)

        elif (self._pytype is list) or (self._pytype is tuple):

            if value is None:  # default selection in a combobox/choice

                return -1

            else:

                return value

        elif self._pytype is Pointer:

            return value

        elif self._pytype is Index:

            if value is None:  # default selection in a RadioBoxes

                return 0

            else:

                return value

        elif self._pytype is wx.Colour:

            return value


class VariableCollection:
    def __init__(self, *variables):
        self._variables = []

        self.AddVariables(*variables)

    def AddVariable(self, variable):
        self._variables.append(variable)

    def AddVariables(self, *variables):
        for variable in variables:
            self.AddVariable(variable)

    def GetChoiceBitmaps(self):
        return [v.GetBitmap() for v in self._variables]

    def GetChoices(self):
        return [v.GetComboLabel() for v in self._variables]

    def GetFrameLabel(self, idx=None):
        if idx is None:
            return [v.GetFrameLabel() for v in self._variables]
        else:
            return self._variables[idx].GetFrameLabel()

    def GetUnit(self, idx=None):
        if idx is None:
            return [v.GetUnit() for v in self._variables]
        else:
            return self._variables[idx].GetUnit()

    def GetVariables(self):
        return self._variables


class Summary(Variable):
    def __init__(self):
        super().__init__()

        self._image_key = None
        self._properties = SummaryProperty()  # similar to what Entities have

        self._type = 'summaries'
        self._type_id = ID_SUMMARY

    def Calculate(self, profile, *args):
        return self._properties.Calculate(profile, *args)

    def GetImageKey(self):
        return self._image_key

    def GetProperties(self):
        return self._properties

    def ReplaceInformation(self, variable, image):
        self._image = image
        self._unit = variable.GetUnitClass()
        self._properties = variable.GetProperties()
        self._menu_label = variable.GetMenuLabel()
        self._plot_label = variable.GetMenuLabel()
        self._legend = variable.GetMenuLabel()

    def SetId(self, id_):
        self._id = id_

    def SetImage(self, image_key=None):
        self._image_key = image_key
        self._image = image_key

    def SetLabels(self, label):
        self._menu_label = label
        self._plot_label = label
        self._legend = label


# ======================================================================================================================
# Types used to test against in ToFrame and FromFrame
# ======================================================================================================================
class Pointer:
    """
    Used for controls that allow insert via an arrow or other means
    """
    def __init__(self):
        pass


class Index:
    """
    Used for transfer to and from RadioBox (which requires 0 as default, unlike bitmapcombobox which requires -1)
    """
    def __init__(self):
        pass


# ======================================================================================================================
# Plotting options for plotable variables
# ======================================================================================================================
class LineOptions:
    def __init__(self, alpha=None, colour=None, drawstyle='default', fillstyle=None, label=None, linestyle='-',
                 linewidth=None, marker=None, markersize=None):

        self._alpha = alpha             # double, [0, 1]
        self._colour = colour           # (R, G, B)  normalized to [0, 1]
        self._drawstyle = drawstyle     # 'default', 'steps-{pre, mid, post}'
        self._fillstyle = fillstyle     # 'full', 'none' (additional options available)
        self._label = label             # string
        self._linestyle = linestyle     # '-', '--', '-.', ':'
        self._linewidth = linewidth     # int, primarily set through settings
        self._marker = marker           # see matplotlib documentation
        self._markersize = markersize   # int, primarily set through settings

        self._picker = 7                # sensitivity to click-events

    def Get(self):
        # returns all options as **kwargs input to a matplotlib axes.plot function
        return {'alpha':      self._alpha,
                'color':      self._colour,
                'drawstyle':  self._drawstyle,
                'fillstyle':  self._fillstyle,
                'label':      self._label,
                'linestyle':  self._linestyle,
                'linewidth':  self._linewidth,
                'marker':     self._marker,
                'markersize': self._markersize,
                'picker':     self._picker}

    def GetAlpha(self):
        return self._alpha

    def GetColour(self):
        return self._colour

    def GetDrawstyle(self):
        """
        Used for transfer to frame
        :return:
        """

        if self._drawstyle is None:
            return -1
        elif self._drawstyle == 'default':
            return 0
        elif self._drawstyle == 'steps-pre':
            return 1
        elif self._drawstyle == 'steps-mid':
            return 2
        elif self._drawstyle == 'steps-post':
            return 3

    def GetLabel(self):
        return self._label

    def GetLegend(self):
        return Line2D([], [], **self.Get())

    def GetLinestyle(self):
        """
        Used for transfer to frame
        :return:
        """

        if self._linestyle is None:
            return -1
        elif self._linestyle == '-':
            return 0
        elif self._linestyle == '--':
            return 1
        elif self._linestyle == '-.':
            return 2
        elif self._linestyle == ':':
            return 3

    def SetAlpha(self, alpha):
        self._alpha = alpha

    def SetColour(self, colour):
        self._colour = colour

    def SetDrawstyle(self, drawstyle):
        """
        Used for transfer from frame
        :param drawstyle: int, BitmapComboBox index
        :return:
        """
        if drawstyle == -1:
            self._drawstyle = None
        elif drawstyle == 0:
            self._drawstyle = 'default'
        elif drawstyle == 1:
            self._drawstyle = 'steps-pre'
        elif drawstyle == 2:
            self._drawstyle = 'steps-mid'
        elif drawstyle == 3:
            self._drawstyle = 'steps-post'

    def SetFillstyle(self, fillstyle):
        self._fillstyle = fillstyle

    def SetLabel(self, label):
        self._label = label

    def SetLinestyle(self, linestyle):
        """
        Used for transfer from frame
        :param drawstyle: int, BitmapComboBox index
        :return:
        """
        if linestyle == -1:
            self._linestyle = None
        elif linestyle == 0:
            self._linestyle = '-'
        elif linestyle == 1:
            self._linestyle = '--'
        elif linestyle == 2:
            self._linestyle = '-.'
        elif linestyle == 3:
            self._linestyle = ':'

    def SetLinewidth(self, linewidth):
        self._linewidth = linewidth

    def SetMarker(self, marker):
        self._marker = marker

    def SetMarkerSize(self, markersize):
        self._markersize = markersize

    def Highlight(self):
        if self._markersize > 0:
            self._markersize += 2
        else:
            self._linewidth += 2

    def UnHighlight(self):
        if self._markersize > 0:
            self._markersize -= 2
        else:
            self._linewidth -= 2


class FittedDataOptions(LineOptions):
    def __init__(self, colour=None):
        super().__init__()

        self._colour = colour
        self._label = 'Fitted data'
        self._fillstyle = 'none'
        self._linewidth = 0.
        self._marker = 'o'


# ======================================================================================================================
# Units
# ======================================================================================================================
class Unit:
    def __init__(self, unit_system=None):
        self._unit = None
        self._label = None  # used as label in plotting when units are grouped

    def Get(self):
        return self._unit

    def GetLabel(self):
        return self._label

    def Set(self, unit_system):
        # sub-class
        pass


class TimeUnit(Unit):
    def __init__(self, unit='days', unit_system=None):
        super().__init__()

        self._unit = unit


class DateUnit(Unit):
    def __init__(self, unit_system=None):
        super().__init__()

        self._unit = '-'


class LiquidFlowRateUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Liquid Flow Rate'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'Mstb/day'
        else:  # metric
            self._unit = 'm^{3}/day'


class GasFlowRateUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Gas Flow Rate'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'MMscf/day'
        else:  # metric
            self._unit = 'm^{3}/day'


class LiquidVolumeUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Liquid Volume'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'MMstb'
        else:  # metric
            self._unit = 'km^{3}'


class GasVolumeUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Gas Volume'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'Bscf'
        else:  # metric
            self._unit = 'km^{3}'


class GasLiquidRatioUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Gas-Liquid Ratio'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'Mscf/stb'
        else:  # metric
            self._unit = 'sm^{3}/sm^{3}'


class LiquidGasRatioUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Liquid-Gas Ratio'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'stb/Mscf'
        else:  # metric
            self._unit = 'sm^{3}/sm^{3}'


class LiquidLiquidRatioUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Liquid-Liquid Ratio'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'stb/stb'
        else:  # metric
            self._unit = 'sm^{3}/sm^{3}'


class LiquidVolumeRatio(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Liquid Volume Ratio'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'rb/stb'
        else:  # metric
            self._unit = 'rm^{3}/sm^{3}'


class GasVolumeRatio(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Gas Volume Ratio'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'rb/Mscf'
        else:  # metric
            self._unit = 'rm^{3}/sm^{3}'


class ReservoirVolumeRatio(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Reservoir Volume Ratio'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'rb/rb'
        else:  # metric
            self._unit = 'rm^{3}/rm^{3}'


class LengthUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Length'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'ft'
        else:  # metric
            self._unit = 'm'


class AreaUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Area'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'ft^{2}'
        else:  # metric
            self._unit = 'm^{2}'


class VolumeUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Volume'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = 'stb'
        else:  # metric
            self._unit = 'm^{3}'


class PermeabilityUnit(Unit):
    def __init__(self, unit_system=None):
        super().__init__()

        self._label = 'Permeability'
        self._unit = 'mD'


class DensityUnit(Unit):
    def __init__(self, unit_system):
        super().__init__()

        self._label = 'Density'
        self.Set(unit_system)

    def Set(self, unit_system):
        if unit_system == ID_UNIT_FIELD:
            self._unit = '^{o}API'
        else:  # metric
            self._unit = 'kg/m^{3}'


class FractionUnit(Unit):
    def __init__(self, unit_system=None):
        super().__init__()

        self._label = 'Fraction'
        self._unit = '-'


class PercentageUnit(Unit):
    def __init__(self, unit_system=None):
        super().__init__()

        self._label = 'Percentage'
        self._unit = '%'


class AmountUnit(Unit):
    def __init__(self, unit_system=None):
        super().__init__()

        self._label = 'Amount'
        self._unit = ''


class Unitless(Unit):
    def __init__(self, unit_system=None):
        super().__init__()

        self._label = 'Dimensionless'
        self._unit = ''


# ======================================================================================================================
# Time Variables
# ======================================================================================================================
class DurationVariable(Variable):
    def __init__(self):
        super().__init__()

        self._type = 'durations'


class Time(DurationVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = TimeUnit()
        self._menu_label = 'Time'
        self._plot_label = 'Time'
        self._image = ico.time_16x16
        self._limits = (0., None)

        self._id = 'time'


class Date(DurationVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = DateUnit()
        self._menu_label = 'Date'
        self._plot_label = 'Dates'
        self._image = ico.dates_16x16
        self._limits = (None, None)
        self._is_date = True

        self._id = 'date'


# ======================================================================================================================
# Production Potential Variables
# ======================================================================================================================
class PotentialVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)
        self._type = 'potentials'
        self._type_id = ID_POTENTIAL


class OilPotential(PotentialVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._menu_label = 'Oil production potential'
        self._image = ico.oil_rate_16x16

        self._line_options = LineOptions(label=r'Oil Pot.', colour=np.array([0., 176., 80.]) / 255., linestyle='--')
        self._plot_label = r'Oil Production Potential'

        self._id = 'oil_potential'


class GasPotential(PotentialVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._menu_label = 'Gas production potential'
        self._image = ico.gas_rate_16x16

        self._line_options = LineOptions(label=r'Gas Pot.', colour=np.array([255., 0., 0.]) / 255., linestyle='--')
        self._plot_label = r'Gas Production Potential'

        self._id = 'gas_potential'


class WaterPotential(PotentialVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._menu_label = 'Water production potential'
        self._image = ico.water_rate_16x16

        self._line_options = LineOptions(label=r'Water Pot.', colour=np.array([91., 155., 213.]) / 255., linestyle='--')
        self._plot_label = r'Water Production Potential'

        self._id = 'water_potential'


class LiquidPotential(PotentialVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._menu_label = 'Liquid production potential'
        self._image = ico.liquid_rate_16x16

        self._line_options = LineOptions(label=r'Liquid Pot.', colour=np.array([51., 102., 153.]) / 255., linestyle='--')
        self._fitted_options = FittedDataOptions(colour=np.array([255., 0., 0.]) / 255.)
        self._plot_label = r'Liquid Production Potential'

        self._id = 'liquid_potential'


class LiftGasPotential(PotentialVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._menu_label = 'Lift gas injection potential'
        self._image = ico.lift_gas_rate_16x16

        self._line_options = LineOptions(label=r'Lift Gas Pot.', colour=np.array([219., 34., 211.]) / 255., linestyle='--')
        self._plot_label = r'Lift Gas Injection Potential'

        self._id = 'lift_gas_potential'


class GasInjectionPotential(PotentialVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._menu_label = 'Gas injection potential'
        self._image = ico.gas_injection_rate_16x16

        self._line_options = LineOptions(label=r'Gas Inj. Pot.', colour=np.array([255., 0., 0.]) / 255., linestyle='--')
        self._plot_label = r'Gas Injection Potential'

        self._id = 'gas_injection_potential'


class WaterInjectionPotential(PotentialVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._menu_label = 'Water injection potential'
        self._image = ico.water_injection_rate_16x16

        self._line_options = LineOptions(label=r'Water Inj. Pot.', colour=np.array([91., 155., 213.]) / 255., linestyle='--')
        self._plot_label = r'Water Injection Potential'

        self._id = 'water_injection_potential'


class TotalGasPotential(PotentialVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._menu_label = 'Total gas production potential'
        self._image = ico.total_gas_rate_16x16

        self._line_options = LineOptions(label=r'Total Gas Pot.', colour=np.array([218., 119., 6.]) / 255., linestyle='--')
        self._plot_label = r'Total Gas Production Potential'

        self._id = 'total_gas_potential'


# ======================================================================================================================
# Production Rate Variables
# ======================================================================================================================
class RateVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)
        self._type = 'rates'
        self._type_id = ID_RATE


class OilRate(RateVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._menu_label = 'Oil production rate'
        self._image = ico.oil_rate_16x16

        self._line_options = LineOptions(label=r'Oil Rate', colour=np.array([0., 176., 80.]) / 255.)
        self._plot_label = r'Oil Production Rate'

        self._id = 'oil_rate'


class GasRate(RateVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._menu_label = 'Gas production rate'
        self._image = ico.gas_rate_16x16

        self._line_options = LineOptions(label=r'Gas Rate', colour=np.array([255., 0., 0.]) / 255.)
        self._plot_label = r'Gas Production Rate'

        self._id = 'gas_rate'


class WaterRate(RateVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._menu_label = 'Water production rate'
        self._image = ico.water_rate_16x16

        self._line_options = LineOptions(label=r'Water Rate', colour=np.array([91., 155., 213.]) / 255.)
        self._plot_label = r'Water Production Rate'

        self._id = 'water_rate'


class LiquidRate(RateVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._menu_label = 'Liquid production rate'
        self._image = ico.liquid_rate_16x16

        self._line_options = LineOptions(label=r'Liquid Rate', colour=np.array([51., 102., 153.]) / 255.)
        self._plot_label = r'Liquid Production Rate'

        self._id = 'liquid_rate'


class LiftGasRate(RateVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._menu_label = 'Lift gas injection rate'
        self._image = ico.lift_gas_rate_16x16

        self._line_options = LineOptions(label=r'Lift Gas Rate', colour=np.array([219., 34., 211.]) / 255.)
        self._plot_label = r'Lift Gas Injection Rate'

        self._id = 'lift_gas_rate'


class GasInjectionRate(RateVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._menu_label = 'Gas injection rate'
        self._image = ico.gas_injection_rate_16x16

        self._line_options = LineOptions(label=r'Gas Inj. Rate', colour=np.array([255., 0., 0.]) / 255.)
        self._plot_label = r'Gas Injection Rate'

        self._id = 'gas_injection_rate'


class WaterInjectionRate(RateVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._menu_label = 'Water injection rate'
        self._image = ico.water_injection_rate_16x16

        self._line_options = LineOptions(label=r'Water Inj. Rate', colour=np.array([91., 155., 213.]) / 255.)
        self._plot_label = r'Water Injection Rate'

        self._id = 'water_injection_rate'


class TotalGasRate(RateVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._menu_label = 'Total gas production rate'
        self._image = ico.total_gas_rate_16x16

        self._line_options = LineOptions(label=r'Total Gas Rate', colour=np.array([218., 119., 6.]) / 255.)
        self._plot_label = r'Total Gas Production Rate'

        self._id = 'total_gas_rate'


# ======================================================================================================================
# Cumulative Production Variables
# ======================================================================================================================
class CumulativeVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)
        self._type = 'cumulatives'
        self._type_id = ID_CUMULATIVE


class OilCumulative(CumulativeVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidVolumeUnit(unit_system)
        self._menu_label = 'Cumulative oil production'
        self._image = ico.oil_cum_16x16

        self._line_options = LineOptions(label=r'Oil Cum.', colour=np.array([0., 134., 61.]) / 255.)
        self._plot_label = r'Cumulative Oil Production'

        self._id = 'oil_cumulative'


class GasCumulative(CumulativeVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasVolumeUnit(unit_system)
        self._menu_label = 'Cumulative gas production'
        self._image = ico.gas_cum_16x16

        self._line_options = LineOptions(label=r'Gas Cum.', colour=np.array([192., 0., 0.]) / 255.)
        self._plot_label = r'Cumulative Gas Production'

        self._id = 'gas_cumulative'


class WaterCumulative(CumulativeVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidVolumeUnit(unit_system)
        self._menu_label = 'Cumulative water production'
        self._image = ico.water_cum_16x16

        self._line_options = LineOptions(label=r'Water Cum.', colour=np.array([51., 126., 195.]) / 255.)
        self._plot_label = r'Cumulative Water Production'

        self._id = 'water_cumulative'


class LiquidCumulative(CumulativeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = LiquidVolumeUnit(unit_system)
        self._menu_label = 'Cumulative liquid production'
        self._image = ico.liquid_cum_16x16

        self._line_options = LineOptions(label=r'Liquid Cum.', colour=np.array([51., 63., 79.]) / 255.)
        self._plot_label = r'Cumulative Liquid Production'

        self._id = 'liquid_cumulative'


class LiftGasCumulative(CumulativeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = GasVolumeUnit(unit_system)
        self._menu_label = 'Cumulative lift gas injection'
        self._image = ico.lift_gas_cum_16x16

        self._line_options = LineOptions(label=r'Lift Gas Cum.', colour=np.array([153., 0., 153.]) / 255.)
        self._plot_label = r'Cumulative Lift Gas Injection'

        self._id = 'lift_gas_cumulative'


class GasInjectionCumulative(CumulativeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = GasVolumeUnit(unit_system)
        self._menu_label = 'Cumulative gas injection'
        self._image = ico.gas_injection_cum_16x16

        self._line_options = LineOptions(label=r'Gas Inj. Cum.', colour=np.array([192., 0., 0.]) / 255.)
        self._plot_label = r'Cumulative Gas Injection'

        self._id = 'gas_injection_cumulative'


class WaterInjectionCumulative(CumulativeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = LiquidVolumeUnit(unit_system)
        self._menu_label = 'Cumulative Water injection'
        self._image = ico.water_injection_cum_16x16

        self._line_options = LineOptions(label=r'Water Inj. Cum.', colour=np.array([51., 126., 195.]) / 255.)
        self._plot_label = r'Cumulative Water Injection'

        self._id = 'water_injection_cumulative'


class TotalGasCumulative(CumulativeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = GasVolumeUnit(unit_system)
        self._menu_label = 'Cumulative total gas production'
        self._image = ico.total_gas_cum_16x16

        self._line_options = LineOptions(label=r'Total Gas Cum.', colour=np.array([218., 119., 6.]) / 255.)
        self._plot_label = r'Cumulative Total Gas Production'

        self._id = 'total_gas_cumulative'


# ======================================================================================================================
# Ratio Variables
# ======================================================================================================================
class FractionVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., 1.)
        self._type = 'ratios'
        self._type_id = ID_RATIO


class RatioVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)
        self._type = 'ratios'
        self._type_id = ID_RATIO


class WaterCut(FractionVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidLiquidRatioUnit(unit_system)
        self._menu_label = 'Water-cut'
        self._image = ico.water_cut_16x16

        self._line_options = LineOptions(label=r'Water-cut', colour=np.array([91., 155., 213.]) / 255.)
        self._fitted_options = FittedDataOptions(colour=np.array([217., 83., 25.]) / 255.)  # TODO: NOT USED
        self._plot_label = r'Water-cut'

        self._id = 'water_cut'


class OilCut(FractionVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidLiquidRatioUnit(unit_system)
        self._menu_label = 'Oil-cut'
        self._image = ico.oil_cut_16x16

        self._line_options = LineOptions(label=r'Oil-cut', colour=np.array([0., 176., 80.]) / 255.)
        self._fitted_options = FittedDataOptions(colour=np.array([255., 0., 0.]) / 255.)
        self._plot_label = r'Oil-cut'

        self._id = 'oil_cut'


class GasOilRatio(RatioVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasLiquidRatioUnit(unit_system)
        self._menu_label = 'Gas-oil ratio'
        self._image = ico.gas_oil_ratio_16x16

        self._line_options = LineOptions(label=r'GOR', colour=np.array([255., 0., 0.]) / 255.)
        self._fitted_options = FittedDataOptions(colour=np.array([122., 48., 160.]) / 255.)
        self._plot_label = r'Gas-Oil Ratio'

        self._id = 'gas_oil_ratio'


class WaterOilRatio(RatioVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidLiquidRatioUnit(unit_system)
        self._menu_label = 'Water-oil ratio'
        self._image = ico.water_oil_ratio_16x16

        self._line_options = LineOptions(label=r'WOR', colour=np.array([91., 155., 213.]) / 255.)
        self._plot_label = r'Water-Oil Ratio'

        self._id = 'water_oil_ratio'


class GasLiquidRatio(RatioVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasLiquidRatioUnit(unit_system)
        self._menu_label = 'Gas-liquid ratio'
        self._image = ico.gas_liquid_ratio_16x16

        self._line_options = LineOptions(label=r'GLR', colour=np.array([255., 0., 0.]) / 255.)
        self._plot_label = r'Gas-Liquid Ratio'

        self._id = 'gas_liquid_ratio'


class WaterGasRatio(RatioVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidGasRatioUnit(unit_system)
        self._menu_label = 'Water-gas ratio'
        self._image = ico.water_gas_ratio_16x16

        self._line_options = LineOptions(label=r'WGR', colour=np.array([91., 155., 213.]) / 255.)
        self._plot_label = r'Water-Gas Ratio'

        self._id = 'water_gas_ratio'


class OilGasRatio(RatioVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidGasRatioUnit(unit_system)
        self._menu_label = 'Oil-gas ratio'
        self._image = ico.oil_gas_ratio_16x16

        self._line_options = LineOptions(label=r'WGR', colour=np.array([0., 176., 80.]) / 255.)
        self._plot_label = r'Oil-Gas Ratio'

        self._id = 'oil_gas_ratio'


class TotalGasLiquidRatio(RatioVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasLiquidRatioUnit(unit_system)
        self._menu_label = 'Total gas-liquid ratio'
        self._image = ico.total_gas_liquid_ratio_16x16

        self._line_options = LineOptions(label=r'TGLR', colour=np.array([218., 119., 6.]) / 255.)
        self._plot_label = r'Total Gas-Liquid Ratio'

        self._id = 'total_gas_liquid_ratio'


# ======================================================================================================================
# Uptime Variables
# ======================================================================================================================
class UptimeVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., 1.)
        self._type = 'uptimes'
        self._type_id = ID_UPTIME


class ProductionUptime(UptimeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = FractionUnit()
        self._menu_label = 'Production uptime'
        self._image = ico.uptime_16x16

        self._line_options = LineOptions(label=r'Prod. uptime', colour=np.array([255., 217., 102.]) / 255.)
        self._plot_label = r'Production Uptime'

        self._id = 'production_uptime'


class LiftGasUptime(UptimeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = FractionUnit()
        self._menu_label = 'Lift gas uptime'
        self._image = ico.uptime_16x16

        self._line_options = LineOptions(label=r'Lift gas uptime', colour=np.array([255., 217., 102.]) / 255.)
        self._plot_label = r'Lift Gas Uptime'

        self._id = 'lift_gas_uptime'


class GasInjectionUptime(UptimeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = FractionUnit()
        self._menu_label = 'Gas inj. uptime'
        self._image = ico.uptime_16x16

        self._line_options = LineOptions(label=r'Gas inj. uptime', colour=np.array([255., 217., 102.]) / 255.)
        self._plot_label = r'Gas Injection Uptime'

        self._id = 'gas_injection_uptime'


class WaterInjectionUptime(UptimeVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = FractionUnit()
        self._menu_label = 'Water inj. uptime'
        self._image = ico.uptime_16x16

        self._line_options = LineOptions(label=r'Water inj. uptime', colour=np.array([255., 217., 102.]) / 255.)
        self._plot_label = r'Water Injection Uptime'

        self._id = 'water_injection_uptime'


# ======================================================================================================================
# Summary variables (for use on frames)
# ======================================================================================================================
class SummaryFunction(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Function'
        self._choices = ('Point', 'Sum', 'Average')
        self._choice_images = (ico.specific_point_16x16, ico.specific_point_16x16, ico.specific_point_16x16)

        self._pytype = tuple

        self._tooltip = 'Function that reduces a temporal production profile to a scalar.'


class SummaryPoint(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Point'
        self._choices = ('First', 'Last', 'Date', 'Time')
        self._choice_images = (ico.first_point_16x16, ico.last_point_16x16, ico.dates_16x16, ico.time_16x16)

        self._pytype = tuple

        self._tooltip = 'The specific summary point of the production profile.'


class SummaryPointDate(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Date'

        self._pytype = date

        self._tooltip = 'Date at which to extract summary point.'


class SummaryPointTime(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = 'years'
        self._frame_label = 'Time'

        self._pytype = float

        self._tooltip = 'Time at which to extract summary point.'


class SummaryIcon(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Icon'
        self._choices = ('Oil rate', 'Gas rate', 'Water rate', 'Liquid rate', 'Lift gas rate', 'Gas injection rate',
                         'Water injection rate', 'Total gas rate', 'Oil cumulative', 'Gas cumulative',
                         'Water cumulative', 'Liquid cumulative', 'Lift gas cumulative', 'Gas injection cumulative',
                         'Water injection cumulative', 'Total gas cumulative', 'Length', 'HCFT', 'HCPV', 'Permeability')

        self._choice_images = (ico.oil_rate_16x16, ico.gas_rate_16x16, ico.water_rate_16x16,
                               ico.liquid_rate_16x16, ico.lift_gas_rate_16x16, ico.gas_injection_rate_16x16,
                               ico.water_injection_rate_16x16, ico.total_gas_rate_16x16,
                               ico.oil_cum_16x16, ico.gas_cum_16x16, ico.water_cum_16x16,
                               ico.liquid_cum_16x16, ico.lift_gas_cum_16x16, ico.gas_injection_cum_16x16,
                               ico.water_injection_cum_16x16, ico.total_gas_cum_16x16,
                               ico.completion_16x16, ico.HCFT_16x16, ico.HCPV_16x16, ico.permeability_16x16)

        self._client_data_map = {i: bitmap for i, bitmap in enumerate(self._choice_images)}

        self._pytype = tuple


class HistogramFrequency(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = AmountUnit()
        self._plot_label = 'Frequency'
        self._legend = 'Frequency'
        self._limits = (0., None)


# ======================================================================================================================
# Concession Variables
# ======================================================================================================================
class License(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'License'

        self._pytype = date

        self._type = 'concessions'
        self._id = 'license'


# ======================================================================================================================
# Plateau Variables
# ======================================================================================================================
class PlateauVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)

        self._round_off = 1
        self._pytype = float

        self._type = 'plateaus'


class TargetOilPlateau(PlateauVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._frame_label = 'Target oil'
        self._menu_label = 'Target oil plateau'
        self._image = ico.well_spacing_16x16

        self._plot_label = r'Target Oil Plateau'
        self._legend = r'Oil Plateau'

        self._tooltip = 'Target oil plateau used as constraint in prediction.'

        self._id = 'target_oil_plateau'


class TargetGasPlateau(PlateauVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._frame_label = 'Target gas'
        self._menu_label = 'Target gas plateau'
        self._image = ico.well_spacing_16x16

        self._plot_label = r'Target Gas Plateau'
        self._legend = r'Gas Plateau'

        self._tooltip = 'Target gas plateau used as constraint in prediction.'

        self._id = 'target_gas_plateau'


# ======================================================================================================================
# Well Variables
# ======================================================================================================================
class ProductionPhase(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Primary phase'
        self._choices = ('Oil', 'Gas')

        self._pytype = Index


class InjectionPhase(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Injected phase'
        self._choices = ('Water', 'Gas', 'WAG')

        self._pytype = Index


class DevelopmentLayout(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Layout'
        self._image = ico.well_pair_2_16x16
        self._choices = (None, 'Line-drive', 'Radial', '5-spot')
        self._choice_images = (None, ico.well_pair_2_16x16, ico.radial_pattern_16x16, ico.five_spot_16x16)

        self._tooltip = 'Scaling of well spacing is only done on\n' \
                        'wells/analogues with similar development scheme.'

        self._pytype = tuple


class WellSpacing(Variable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LengthUnit(unit_system)
        self._frame_label = 'Spacing'
        self._menu_label = 'Well spacing'
        self._image = ico.well_spacing_16x16
        self._limits = (0., None)

        self._plot_label = r'Well Spacing'
        self._legend = r'Spacing'

        self._tooltip = 'Used to scale the rate and cumulative production\n' \
                        'based on the ratio between the spacing of the\n' \
                        'producer and an analogue.'

        self._pytype = int

        self._type = 'well_spacing'
        self._id = 'spacing'


class History(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Import'

        self._pytype = tuple

        self._tooltip = 'Profile of historical data:\n' \
                        '- Browse: Import profile from external file.'


class HistoryFit(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Import'

        self._pytype = tuple

        self._tooltip = 'Profile of historical data:\n' \
                        '- Browse: Import profile from external file\n' \
                        '- Window: Fit models to historical data for use in prediction.'


class Cultural(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Import'

        self._pytype = tuple

        self._tooltip = 'Cultural of the entity:\n' \
                        '- Field, Block, Reservoir, Theme, Polygon: 2D outline (x, y)\n' \
                        '- Pipeline: 2D trajectory (x, y)\n' \
                        '- Platform, Processor: Point (x, y)\n' \
                        '- Producer, Injector, Analogue: 3D trajectory (x, y, z)'


class Prediction(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Prediction'
        self._choices = ('Low', 'Mid', 'High')
        self._choice_images = (ico.low_chart_16x16, ico.mid_chart_16x16, ico.high_chart_16x16)

        self._pytype = tuple


class ProbabilityOfOccurrence(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = PercentageUnit()
        self._frame_label = 'Occurrence'
        self._limits = (0., 100.)

        self._round_off = 1
        self._pytype = float

        self._tooltip = 'Probability of the currently selected prediction\n' \
                        'to be sampled during uncertainty modelling'


# ======================================================================================================================
# Pointer Variables
# ======================================================================================================================
class Analogue(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Analogue'

        self._pytype = Pointer

        self._tooltip = 'Analogue from which to historical data:\n' \
                        '- Arrow: Insert Analogue from menu\n' \
                        '- Window: Create function based on models\n' \
                        '                    fitted to historical data.'


class Typecurve(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Typecurve'

        self._pytype = Pointer

        self._tooltip = 'Profile used for prediction:\n' \
                        '- Arrow: Insert Typecurve from menu\n' \
                        '- Browse: Import profile from external file\n' \
                        '- Window: Create function based on models\n' \
                        '                    fitted to historical data.'


class Scaling(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Scaling'

        self._pytype = Pointer

        self._tooltip = 'Scaling evaluation used for transforming\n' \
                        'static parameters to scalers:\n' \
                        '- Arrow: Insert Scaling from menu.'


class Scenario(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Scenario'

        self._pytype = Pointer

        self._tooltip = 'Scenario from which to gather entities, events and dates:\n' \
                        '- Arrow: Insert Scenario from menu.'


class HistorySimulation(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'History'

        self._pytype = Pointer

        self._tooltip = 'History simulation to carry into prediction:\n' \
                        '- Arrow: Insert History from menu.'


# ======================================================================================================================
# Fluid Variables
# ======================================================================================================================
class FluidVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)

        self._round_off = 2
        self._pytype = float


class ReservoirFluidVariable(FluidVariable):
    def __init__(self):
        super().__init__()

        self._type = 'res_fluids'


class InjectionFluidVariable(FluidVariable):
    def __init__(self):
        super().__init__()

        self._type = 'inj_fluids'


class OilFVF(ReservoirFluidVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidVolumeRatio(unit_system)
        self._frame_label = 'Bo'
        self._menu_label = 'Oil FVF'
        self._image = ico.Bo_16x16

        self._plot_label = r'Oil FVF, $b_o$'
        self._legend = r'$b_o$'

        self._tooltip = 'Oil formation volume factor.'

        self._id = 'bo'


class GasFVF(ReservoirFluidVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasVolumeRatio(unit_system)
        self._frame_label = 'Bg'
        self._menu_label = 'Gas FVF'
        self._image = ico.Bg_16x16

        self._plot_label = r'Gas FVF, $b_g$'
        self._legend = r'$b_g$'

        self._tooltip = 'Gas formation volume factor.'

        self._id = 'bg'


class WaterFVF(ReservoirFluidVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidVolumeRatio(unit_system)
        self._frame_label = 'Bw'
        self._menu_label = 'Water FVF'
        self._image = ico.Bw_16x16

        self._plot_label = r'Water FVF, $b_w$'
        self._legend = r'$b_w$'

        self._tooltip = 'Water formation volume factor.'

        self._id = 'bw'


class SolutionGasOilRatio(ReservoirFluidVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasLiquidRatioUnit(unit_system)
        self._frame_label = 'Rs'
        self._menu_label = 'Solution GOR'
        self._image = ico.Rs_16x16

        self._plot_label = r'Solution Gas-Oil Ratio, $R_s$'
        self._legend = r'$R_s$'

        self._tooltip = 'Solution gas-oil-ratio.'

        self._id = 'rs'


class InjectionGasFVF(InjectionFluidVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasVolumeRatio(unit_system)
        self._frame_label = 'Bg inj.'
        self._menu_label = 'Gas inj. FVF'
        self._image = ico.Bg_inj_16x16

        self._plot_label = r'Injection Gas FVF, $b_{g,inj}$'
        self._legend = r'$b_{g,inj}$'

        self._tooltip = 'Injection gas formation volume factor.'

        self._id = 'bg_inj'


class InjectionWaterFVF(InjectionFluidVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidVolumeRatio(unit_system)
        self._frame_label = 'Bw inj.'
        self._menu_label = 'Water inj. FVF'
        self._image = ico.Bw_inj_16x16

        self._plot_label = r'Injection Water FVF, $b_{w,inj}$'
        self._legend = r'$b_{w,inj}$'

        self._tooltip = 'Injection water formation volume factor.'

        self._id = 'bw_inj'


# ======================================================================================================================
# Stakes Variables
# ======================================================================================================================
class Maturity(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Maturity'
        self._menu_label = 'Maturity'
        self._image = ico.oil_cum_16x16  # TODO: Draw icon
        self._limits = (.5, 1.5)

        self._plot_label = r'Maturity'
        self._legend = r'Maturity'

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Maturity index between 0.5 to 1.5,\n' \
                        'low values indicate low maturity and vice versa.'

        self._type = 'risking'
        self._id = 'maturity'


class ProbabilityOfSuccess(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = PercentageUnit()
        self._frame_label = 'PoS'
        self._menu_label = 'Probability of success'
        self._image = ico.binary_distribution_16x16
        self._limits = (0., 100.)

        self._plot_label = r'Probability of Success, PoS'
        self._legend = r'PoS'

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Probability of Success is used to include or\n' \
                        'exclude a well during uncertainty modelling.\n' \
                        'Weighted average shown for subsurface items.'

        self._type = 'risking'
        self._id = 'pos'


class STOIIP(Variable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidVolumeUnit(unit_system)
        self._frame_label = 'STOIIP'
        self._menu_label = 'STOIIP'
        self._image = ico.stoiip_16x16
        self._limits = (0., None)

        self._plot_label = r'STOIIP'
        self._legend = r'STOIIP'

        self._pytype = int

        self._tooltip = 'Stock tank oil initially in place.'

        self._type = 'volumes'
        self._id = 'stoiip'


# ======================================================================================================================
# Constraint Variables
# ======================================================================================================================
class ConstraintVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)

        self._round_off = 2
        self._pytype = float

        self._type = 'constraints'


class OilConstraint(ConstraintVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._frame_label = 'Oil flow'
        self._menu_label = 'Oil flow con.'
        self._image = ico.oil_flow_constraint_16x16

        self._plot_label = r'Oil Flow Constraint, $Q_{o,max}$'
        self._legend = r'Oil Con.'

        self._tooltip = 'Oil flow constraint.'

        self._id = 'oil_constraint'


class GasConstraint(ConstraintVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._frame_label = 'Gas flow'
        self._menu_label = 'Gas flow con.'
        self._image = ico.gas_flow_constraint_16x16

        self._plot_label = r'Gas Flow Constraint, $Q_{g,max}$'
        self._legend = r'Gas Con.'

        self._tooltip = 'Gas flow constraint.'

        self._id = 'gas_constraint'


class WaterConstraint(ConstraintVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._frame_label = 'Water flow'
        self._menu_label = 'Water flow con.'
        self._image = ico.water_flow_constraint_16x16

        self._plot_label = r'Water Flow Constraint, $Q_{w,max}$'
        self._legend = r'Water Con.'

        self._tooltip = 'Water flow constraint.'

        self._id = 'water_constraint'


class LiquidConstraint(ConstraintVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._frame_label = 'Liquid flow'
        self._menu_label = 'liquid flow con.'
        self._image = ico.liquid_flow_constraint_16x16

        self._plot_label = r'Liquid Flow Constraint, $Q_{l,max}$'
        self._legend = r'Liquid Con.'

        self._tooltip = 'Liquid flow constraint.'

        self._id = 'liquid_constraint'


class InjectionGasConstraint(ConstraintVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._frame_label = 'Gas-inj. rate'
        self._menu_label = 'Gas-inj. con.'
        self._image = ico.gas_injection_constraint_16x16

        self._plot_label = r'Gas-Injection Constraint, $Q_{g,inj,max}$'
        self._legend = r'Gas-Inj. Con.'

        self._tooltip = 'Injection gas constraint.'

        self._id = 'gas_inj_constraint'


class InjectionWaterConstraint(ConstraintVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._frame_label = 'Water-inj. rate'
        self._menu_label = 'Water-inj. con.'
        self._image = ico.water_injection_constraint_16x16

        self._plot_label = r'Water-Injection Constraint, $Q_{w,inj,max}$'
        self._legend = r'Water-Inj. Con.'

        self._tooltip = 'Injection water constraint.'

        self._id = 'water_inj_constraint'


class LiftGasConstraint(ConstraintVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._frame_label = 'Gas-lift rate'
        self._menu_label = 'Gas-lift con.'
        self._image = ico.lift_gas_constraint_16x16

        self._plot_label = r'Gas-Lift Constraint, $Q_{g,lift,max}$'
        self._legend = r'Gas-Lift Con.'

        self._tooltip = 'Lift-gas constraint.'

        self._id = 'lift_gas_constraint'


# ======================================================================================================================
# Out-flowing Phase Variables
# ======================================================================================================================
class OilInflow(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Oil'

        self._pytype = bool

        self._tooltip = 'Oil is fed in from the previous node.'


class GasInflow(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Gas'

        self._pytype = bool

        self._tooltip = 'Gas is fed in from the previous node.\n' \
                        'This is the total gas, i.e. gas from\n' \
                        'the reservoir and lift-gas.'


class WaterInflow(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Water'

        self._pytype = bool

        self._tooltip = 'Water is fed in from the previous node.'


class InjectionGasInflow(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Injection Gas'

        self._pytype = bool

        self._tooltip = 'Injection gas is fed in from the previous node.'


class InjectionWaterInflow(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Injection Water'

        self._pytype = bool

        self._tooltip = 'Injection water is fed in from the previous node.'


# ======================================================================================================================
# Flow Split Variables
# ======================================================================================================================
class SplitType(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Split type'
        self._choices = ('', 'Fixed', 'Multiphasic spill-over', 'Monophasic spill-over', 'Production to injection')
        self._choice_images = (None, ico.oil_cum_16x16, ico.fluids_16x16, ico.liquid_cum_16x16, ico.fluids_injection_16x16)

        self._tooltip = 'Defines the split-type used in determining\n' \
                        'how the phases are split.\n' \
                        '- Fixed: Sends phases to the two nodes based on the fractions given below.\n' \
                        '- Multiphasic:...'

        self._pytype = tuple


class OilSplit(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Oil split'
        self._limits = (0., 1.)

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Oil split. Fraction goes to step-parent,\n' \
                        '1-fraction goes to parent.'


class GasSplit(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Gas split'
        self._limits = (0., 1.)

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Gas split. Fraction goes to step-parent,\n' \
                        '1-fraction goes to parent.'


class WaterSplit(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Water split'
        self._limits = (0., 1.)

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Water split. Fraction goes to step-parent,\n' \
                        '1-fraction goes to parent.'


class LiftGasSplit(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Lift-gas split'
        self._limits = (0., 1.)

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Lift-gas split. Fraction goes to step-parent,\n' \
                        '1-fraction goes to parent.'


class InjectionGasSplit(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Injection gas split'
        self._limits = (0., 1.)

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Injection gas split. Fraction goes to step-parent,\n' \
                        '1-fraction goes to parent.'


class InjectionWaterSplit(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Injection water split'
        self._limits = (0., 1.)

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Injection water split. Fraction goes to step-parent,\n' \
                        '1-fraction goes to parent.'


# ======================================================================================================================
# Surface Variables
# ======================================================================================================================
class FacilityVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)
        self._type = 'facilities'


class TargetGasLiquidRatio(FacilityVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = GasLiquidRatioUnit(unit_system)
        self._frame_label = 'Target TGLR'
        self._menu_label = 'Target gas-liquid ratio'
        self._image = ico.total_gas_liquid_ratio_16x16

        self._plot_label = r'Target Gas-Liquid Rate'
        self._legend = r'Target TGLR.'

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Target total gas-liquid-ration used for\n' \
                        'calculating lift-gas requirements.'

        self._id = 'tglr'


class Availability(FacilityVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = FractionUnit()
        self._frame_label = 'Availability'
        self._menu_label = 'Availability'
        self._image = ico.average_uptime_16x16

        self._plot_label = r'Availability'
        self._legend = r'Availability'

        self._round_off = 3
        self._pytype = float

        self._tooltip = 'Availability applied to production rates and constraints.\n' \
                        'Individual entity availability not used in simulation, but\n' \
                        'kept for export to Phaser. Availability listed in History and Prediction is used\n' \
                        'as an over-all system availability.'

        self._id = 'availability'


class WAGCycleDuration(FacilityVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = TimeUnit('days')
        self._frame_label = 'Cycle dur.'
        self._menu_label = 'WAG cycle duration'
        self._image = ico.wag_cycle_duration_16x16

        self._plot_label = r'WAG Cycle Duration'
        self._legend = r'WAG Cycle'

        self._pytype = int

        self._tooltip = 'Duration between each change-over from\n' \
                        'gas to water injection'

        self._id = 'wag_cycle'


class WAGCycles(FacilityVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = AmountUnit()
        self._frame_label = '# of cycles'
        self._menu_label = 'WAG cycles'
        self._image = ico.wag_cycles_16x16

        self._plot_label = r'Number of WAG Cycles'
        self._legend = r'WAG Cycles'

        self._pytype = int

        self._tooltip = 'Maximum number of change-overs from\n' \
                        'gas to water injection. Starting with\n' \
                        'gas and ending with water'

        self._id = 'wag_cycles'


class TargetVoidageRatio(FacilityVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = ReservoirVolumeRatio(unit_system)
        self._frame_label = 'Target ratio'
        self._menu_label = 'Target voidage ratio'
        self._image = ico.wag_voidage_replacement_16x16

        self._plot_label = r'Target Voidage Replacement Ratio'
        self._legend = r'Target Voidage Ratio'

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Target voidage replacement ratio:\n' \
                        '- Spreadsheet: Assign proportion of injection\n' \
                        '               going to each supported producer'

        self._id = 'voidage'


class VoidageProportion(FacilityVariable):
    # used exclusively on the VoidagePanel in PropertyPanels. TargetVoidageRatio handles menu and plotting
    def __init__(self, unit_system):
        super().__init__()
        self._unit = ReservoirVolumeRatio(unit_system)
        self._frame_label = 'Target ratio'
        self._image = ico.spreadsheet_16x16

        self._round_off = 2
        self._pytype = float


class GasInjectionPotentialConstant(FacilityVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = GasFlowRateUnit(unit_system)
        self._frame_label = 'Gas inj.'
        self._menu_label = 'Constant gas inj.'
        self._image = ico.gas_injection_rate_16x16
        self._limits = (0., None)

        self._plot_label = r'Constant gas injection'
        self._legend = r'Con. gas inj.'

        self._tooltip = 'Set to provide a constant gas injection potential\n' \
                        'for the well. If this is not set, the required\n' \
                        'potential will be calculated based on voidage replacement.'

        self._pytype = float
        self._round_of = 1

        self._id = 'constant_gas_inj'


class WaterInjectionPotentialConstant(FacilityVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = LiquidFlowRateUnit(unit_system)
        self._frame_label = 'Water inj.'
        self._menu_label = 'Constant water inj.'
        self._image = ico.water_injection_rate_16x16
        self._limits = (0., None)

        self._plot_label = r'Constant water injection'
        self._legend = r'Con. water inj.'

        self._tooltip = 'Set to provide a constant water injection potential\n' \
                        'for the well. If this is not set, the required\n' \
                        'potential will be calculated based on voidage replacement.'

        self._pytype = float
        self._round_of = 1

        self._id = 'constant_water_inj'


# ======================================================================================================================
# Auxiliary Variables
# ======================================================================================================================
class Name(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Name'

        self._pytype = str

        self._id = 'name'


class ScalerEvaluation(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Evaluation'
        self._image = ico.right_arrow_16x16

        self._pytype = str

        self._tooltip = 'Mathematical expression used to transform\n' \
                        'static parameters into scaling parameters.'


class SummaryEvaluation(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Multiplier'
        self._image = ico.right_arrow_16x16

        self._pytype = str

        self._tooltip = 'Mathematical expression used to calculate\n' \
                        'multiplier to the production profile.'


class IncludeModel(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Include model'

        self._pytype = bool


class MergeType(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Merge type'
        self._choices = ('', 'Smooth', 'Conditional')
        self._choice_images = (None, ico.merge_16x16, ico.merge_16x16)

        self._pytype = tuple


class MergePoint(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None)
        self._frame_label = (None, 'Merge at (x-axis)', 'Merge at (y-axis)')

        self._round_off = 2
        self._pytype = float


class MergeRate(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None)
        self._frame_label = (None, 'Merge rate', None)

        self._round_off = 5
        self._pytype = float


class Multiplier(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Multiplier'

        self._round_off = 1
        self._pytype = float


class Addition(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Addition'

        self._round_off = 1
        self._pytype = float


class RunFrom(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Run from'
        self._choices = (None, 'First point', 'Last point', 'Specific')
        self._choice_images = (None, ico.first_point_16x16, ico.last_point_16x16, ico.specific_point_16x16)

        self._pytype = tuple


class RunFromSpecific(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Axis'
        self._choices = (None, 'x-axis', 'y-axis')
        self._choice_images = (None, ico.x_axis_16x16, ico.y_axis_16x16)

        self._pytype = tuple


class RunFromValue(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Value'
        self._limits = (0., None)

        self._round_off = 2
        self._pytype = float


class RunTo(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Run to (x-axis)'
        self._image = ico.run_16x16

        self._round_off = 1
        self._pytype = float


class Frequency(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Frequency'
        self._choices = ('Yearly', 'Quarterly', 'Monthly', 'Delta')
        self._choice_images = (ico.dates_year_16x16, ico.dates_quarter_16x16, ico.dates_16x16, ico.timestep_16x16)

        self._pytype = tuple


class TimeDelta(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None, TimeUnit('days'))
        self._frame_label = (None, None, None, 'Delta')

        self._round_off = 1
        self._pytype = float

        self._tooltip = 'Number of days for each time-step.'


class TimeStep(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = TimeUnit('days')
        self._frame_label = 'Time-step'

        self._round_off = 1
        self._pytype = float

        self._tooltip = 'Number of days for each time-step.'


class SaveAllSamples(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Save all samples'

        self._pytype = bool

        self._tooltip = 'Save all the sampled runs. This allows for\n' \
                        '- Display distribution shading in Cartesian charts\n' \
                        '- Display Histograms of summary variables\n' \
                        'Saved file size is substantially larger.'


class SimulateConstrainted(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Simulate with constraints'

        self._pytype = bool

        self._tooltip = 'Simulate using voidage replacement\n' \
                        'assumptions and surface network constraints.\n' \
                        'Rates will be based on the choke position and\n' \
                        'potentials will become instantaneous potentials.'


class Samples(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = AmountUnit()
        self._frame_label = '# of samples'
        self._plot_label = 'Samples'
        self._limits = (0., None)

        self._pytype = int

        self._tooltip = 'Number of stochastic samples to run.'



# ======================================================================================================================
# Scenario and Event Variables
# ======================================================================================================================
class StartDate(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Start'

        self._pytype = date

        self._tooltip = 'Start date of prediction'


class EndDate(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'End'

        self._pytype = date

        self._tooltip = 'End date of prediction'



class EventTrigger(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Trigger'
        self._choices = ('Scenario', 'Date')
        self._choice_images = (ico.scenario_16x16, ico.event_16x16)

        self._pytype = tuple


class EventDate(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None)
        self._frame_label = (None, 'Date')

        self._pytype = date


class OffsetYears(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (TimeUnit('years'), None)
        self._frame_label = ('Offset', None)

        self._round_off = 2
        self._pytype = float


# ======================================================================================================================
# Uncertainty Variables
# ======================================================================================================================
class UncertainValue(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Value'

        self._round_off = 2
        self._pytype = float

        self._tooltip = 'Deterministic value used for sampling.'


class Distribution(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Distribution'
        self._choices = ['', 'Swanson', 'Uniform', 'Triangular', 'Normal', 'Lognormal']
        self._choice_images = (None, ico.swanson_distribution_16x16, ico.uniform_distribution_16x16,
                               ico.triangular_distribution_16x16, ico.normal_distribution_16x16,
                               ico.lognormal_distribution_16x16)

        self._pytype = tuple

        self._tooltip = 'Probability distribution used for sampling\n' \
                        'of the properties uncertainty space.'


class DistributionParameter1(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, '+/-%', '+/-%', '+/-%', '+/-%', '+/-%')
        self._frame_label = (None, 'Min', 'Min', 'Min', 'Mean', 'Mean')
        self._limits = (-100., None)

        self._pytype = int

        self._tooltip = 'Distribution parameters is calculated\n' \
                        'as +/- percentage of Value.'


class DistributionParameter2(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, '+/-%', '+/-%', '+/-%', '+% of mean', '+% of mean')
        self._frame_label = (None, 'Mode', 'Max', 'Mode', 'St. dev.', 'St. dev.')
        self._limits = (-100., None)

        self._pytype = int

        self._tooltip = 'Distribution parameters is calculated\n' \
                        'as +/- percentage of Value.'


class DistributionParameter3(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, '+/-%', None, '+/-%', None, None)
        self._frame_label = (None, 'Max', None, 'Max', None, None)
        self._limits = (-100., None)

        self._pytype = int

        self._tooltip = 'Distribution parameters is calculated\n' \
                        'as +/- percentage of Value.'


# ======================================================================================================================
# Analogue Function Variables
# ======================================================================================================================
class PlaceholderMethod(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Method'
        self._choices = ('' * 5)
        self._choice_images = (None,)

        self._pytype = tuple


class PlaceholderInput(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None,)
        self._frame_label = ('' * 5)

        self._pytype = int


class PlaceholderParameter1(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None,)
        self._frame_label = ('' * 5)

        self._pytype = int


class PlaceholderParameter2(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None,)
        self._frame_label = ('' * 5)

        self._pytype = int


class PlaceholderParameter3(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None,)
        self._frame_label = ('' * 5)

        self._pytype = int


class HistoryMethod(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Method'
        self._choices = ('History', 'Moving average')
        self._choice_images = (ico.history_fit_16x16, ico.moving_average_fit_16x16)

        self._pytype = tuple


class HistoryInput(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None)
        self._frame_label = (None, 'n')

        self._pytype = int


class HistoryParameter1(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None)
        self._frame_label = (None, None)

        self._pytype = int


class HistoryParameter2(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None)
        self._frame_label = (None, None)

        self._pytype = int


class HistoryParameter3(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None)
        self._frame_label = (None, None)

        self._pytype = int


class CurvefitMethod(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Method'
        self._choices = ('Constant', 'Linear', 'Exponential', 'Power', 'Logarithmic')
        self._choice_images = (ico.constant_fit_16x16, ico.linear_fit_16x16, ico.exponential_fit_16x16, ico.power_fit_16x16, ico.logarithmic_fit_16x16)

        self._pytype = tuple


class CurvefitInput(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None, None, None)
        self._frame_label = (None, None, None, None, None)

        self._pytype = int


class CurvefitParameter1(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None, None, None)
        self._frame_label = ('con.', 'a', 'a', 'a', 'a')

        self._round_off = 3
        self._pytype = float


class CurvefitParameter2(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None, None, None)
        self._frame_label = (None, 'b', 'b', 'b', 'b')

        self._round_off = 2
        self._pytype = float


class CurvefitParameter3(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None, None, None)
        self._frame_label = (None, None, 'c', 'c', None)

        self._round_off = 2
        self._pytype = float


class NonParametricMethod(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Method'
        self._choices = ('Bow-wave',)
        self._choice_images = (ico.bow_wave_16x16,)

        self._pytype = tuple


class NonParametricInput(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None,)
        self._frame_label = ('Mid',)

        self._round_off = 2
        self._pytype = float


class NonParametricParameter1(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None,)
        self._frame_label = (None,)

        self._pytype = int


class NonParametricParameter2(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None,)
        self._frame_label = (None,)

        self._pytype = int


class NonParametricParameter3(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None,)
        self._frame_label = (None,)

        self._pytype = int


class DCAMethod(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Method'
        self._choices = ('Exponential', 'Hyperbolic', 'Harmonic')
        self._choice_images = (ico.exponential_dca_16x16, ico.hyperbolic_dca_16x16, ico.harmonic_dca_16x16)

        self._pytype = tuple


class DCAInput(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None)
        self._frame_label = (None, 'b', None)

        self._round_off = 2
        self._pytype = float


class DCAParameter1(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None)
        self._frame_label = ('q', 'q', 'q')

        self._round_off = 2
        self._pytype = float


class DCAParameter2(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None)
        self._frame_label = ('D', 'D', 'D')

        self._round_off = 5
        self._pytype = float


class DCAParameter3(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = (None, None, None)
        self._frame_label = (None, None, None)

        self._pytype = int


# ======================================================================================================================
# Scaling Variables
# ======================================================================================================================
class ScalerVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)

        self._round_off = 2
        self._pytype = float

        self._type = 'scalers'


class CumulativeScaler(ScalerVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Cum'
        self._menu_label = 'Cumulative'
        self._image = ico.cum_scaler_16x16

        self._plot_label = r'Cumulative Scaler, $S_{cum}$'
        self._legend = r'$S_{cum}$'

        self._id = 's_cum'


class RateScaler(ScalerVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'Rate'
        self._menu_label = 'Rate'
        self._image = ico.rate_scaler_16x16

        self._plot_label = r'Rate Scaler, $S_{rate}$'
        self._legend = r'$S_{rate}$'

        self._id = 's_rate'


class FFWScaler(ScalerVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'FFW'
        self._menu_label = 'FFW'
        self._image = ico.ffw_scaler_16x16

        self._plot_label = r'Fractional Flow of Water Scaler, $S_{ffw}$'
        self._legend = r'$S_{ffw}$'

        self._id = 's_ffw'


class FFGScaler(ScalerVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = Unitless()
        self._frame_label = 'FFG'
        self._menu_label = 'FFG'
        self._image = ico.ffg_scaler_16x16

        self._plot_label = r'Fractional Flow of Gas Scaler, $S_{ffg}$'
        self._legend = r'$S_{ffg}$'

        self._id = 's_ffg'


class OnsetScaler(ScalerVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = TimeUnit('years')
        self._frame_label = 'Onset'
        self._menu_label = 'Onset'
        self._image = ico.time_16x16  # TODO: Draw icon

        self._plot_label = r'Fractional Flow Onset, $\Delta$'
        self._legend = r'Onset'

        self._id = 'onset'


class InitialWCTScaler(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = PercentageUnit()
        self._frame_label = 'Ini. WCT'
        self._menu_label = 'Initial WCT'
        self._image = ico.wct_ini_scaler_16x16
        self._limits = (0., 100.)

        self._plot_label = r'Initial Water-cut'
        self._legend = r'Ini. WCT'

        self._pytype = int

        self._type = 'scalers'
        self._id = 'wct_ini'


class ScalerSelection(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Scaler'
        self._choices = ('Cumulative', 'Rate', 'FFW', 'FFG')
        self._choice_images = (ico.cum_scaler_16x16, ico.rate_scaler_16x16, ico.ffw_scaler_16x16, ico.ffg_scaler_16x16)

        self._pytype = tuple


# ======================================================================================================================
# Selection of possible static parameters used as input to scaling laws
# ======================================================================================================================
class StaticVariable(Variable):
    def __init__(self):
        super().__init__()

        self._limits = (0., None)

        self._round_off = 1
        self._pytype = float

        self._type = 'statics'


class CompletedLength(StaticVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = LengthUnit(unit_system)
        self._frame_label = 'Well length'
        self._menu_label = 'Well length'
        self._image = ico.completion_16x16

        self._plot_label = r'Well Length'
        self._legend = r'Well length'

        self._id = 'length'


class HydrocarbonFeet(StaticVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = AreaUnit(unit_system)
        self._frame_label = 'HCFT'
        self._menu_label = 'HCFT'
        self._image = ico.HCFT_16x16

        self._plot_label = r'HCFT'
        self._legend = r'HCFT'

        self._id = 'hcft'


class HydrocarbonPoreVolume(StaticVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = VolumeUnit(unit_system)
        self._frame_label = 'HCPV'
        self._menu_label = 'HCPV'
        self._image = ico.HCPV_16x16

        self._plot_label = r'HCPV'
        self._legend = r'HCPV'

        self._id = 'hcpv'


class Permeability(StaticVariable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = PermeabilityUnit()
        self._frame_label = 'Permeability'
        self._menu_label = 'Permeability'
        self._image = ico.permeability_16x16

        self._plot_label = r'Permeability'
        self._legend = r'Permeability'

        self._id = 'permeability'


class OilDensity(StaticVariable):
    def __init__(self, unit_system):
        super().__init__()
        self._unit = DensityUnit(unit_system)
        self._frame_label = 'Oil density'
        self._menu_label = 'Oil density'
        self._image = ico.stoiip_16x16

        self._plot_label = r'Oil density, $\rho_o$'
        self._legend = r'$\rho_o$'

        self._id = 'oil_density'


# ======================================================================================================================
# Plot Option Variables
# ======================================================================================================================
class ShowData(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Show data'
        self._choices = ('No', 'Yes')
        self._choice_images = (None, ico.history_match_16x16)

        self._pytype = tuple


class ShowUncertainty(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Show uncertainty'
        self._choices = ('No', 'Yes')
        self._choice_images = (ico.mid_chart_16x16, ico.prediction_16x16)

        self._pytype = tuple


class SplitBy(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Split by'
        self._choices = ('None', 'Entity', 'Simulation', 'Variable')
        self._choice_images = (None, ico.folder_closed_16x16, ico.project_16x16, ico.grid_properties_16x16)

        self._pytype = tuple


class GroupBy(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Group by'
        self._choices = ('None', 'Unit')
        self._choice_images = (None, None)

        self._pytype = tuple


class ColourBy(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Colour by'
        self._choices = ('None', 'Entity type')  # TODO: Not yet correct
        self._choice_images = (None, None)

        self._pytype = tuple


# ======================================================================================================================
# Variable plotting option variables (used on frames)
# ======================================================================================================================
class VariableColour(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Colour'

        self._tooltip = 'Select colour of line to display in cartesian charts.'

        self._pytype = wx.Colour


class VariableDrawstyle(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Drawstyle'
        self._choices = ('Default', 'Steps (pre)', 'Steps (mid)', 'Steps (post)')
        self._choice_images = (None, None, None, None)

        self._pytype = tuple


class VariableLinestyle(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Linestyle'
        self._choices = ('Solid', 'Dashed', 'Dash-dot', 'Dotted')
        self._choice_images = (None, None, None, None)

        self._pytype = tuple


# ======================================================================================================================
# Settings variables
# ======================================================================================================================
class SettingsUnitSystem(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Unit system'
        self._choices = ('Field', 'Metric')
        self._choice_images = (None, None)

        self._pytype = tuple


LINE_SIZES = ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10')
TEXT_SIZES = ('6', '8', '10', '12', '14', '16', '18', '20', '22', '24')
TEXT_BITMAPS = (None, None, None, None, None, None, None, None, None, None)


class SettingsLinewidth(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Linewidth'
        self._choices = LINE_SIZES
        self._choice_images = (ico.linewidth_1_16x16, ico.linewidth_2_16x16, ico.linewidth_3_16x16,
                               ico.linewidth_4_16x16, ico.linewidth_5_16x16, ico.linewidth_6_16x16,
                               ico.linewidth_7_16x16, ico.linewidth_8_16x16, ico.linewidth_9_16x16,
                               ico.linewidth_10_16x16)

        self._pytype = tuple


class SettingsMarkerSize(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Marker size'
        self._choices = LINE_SIZES
        self._choice_images = (ico.markersize_1_16x16, ico.markersize_2_16x16, ico.markersize_3_16x16,
                               ico.markersize_4_16x16, ico.markersize_5_16x16, ico.markersize_6_16x16,
                               ico.markersize_7_16x16, ico.markersize_8_16x16, ico.markersize_9_16x16,
                               ico.markersize_10_16x16)

        self._pytype = tuple


class SettingsTickLabelSize(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Tick-label size'
        self._choices = TEXT_SIZES
        self._choice_images = TEXT_BITMAPS

        self._pytype = tuple


class SettingsLabelSize(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Label size'
        self._choices = TEXT_SIZES
        self._choice_images = TEXT_BITMAPS

        self._pytype = tuple


class SettingsLegendSize(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Legend size'
        self._choices = TEXT_SIZES
        self._choice_images = TEXT_BITMAPS

        self._pytype = tuple


PERCENTILE_OPTIONS = ('P05', 'P10', 'P20', 'P25', 'P30', 'P40', 'P50', 'P60', 'P70', 'P75', 'P80', 'P90', 'P95')
PERCENTILE_BITMAPS = (None, None, None, None, None, None, None, None, None, None, None, None, None)


class SettingsLowCase(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Low case'
        self._choices = PERCENTILE_OPTIONS
        self._choice_images = PERCENTILE_BITMAPS

        self._pytype = tuple


class SettingsMidCase(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Mid case'
        self._choices = PERCENTILE_OPTIONS
        self._choice_images = PERCENTILE_BITMAPS

        self._pytype = tuple


class SettingsHighCase(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'High case'
        self._choices = PERCENTILE_OPTIONS
        self._choice_images = PERCENTILE_BITMAPS

        self._pytype = tuple


class SettingsShadingResolution(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Resolution'
        self._choices = ('2', '4', '6', '8', '10')
        self._choice_images = (None, None, None, None, None)

        self._pytype = tuple


class SettingsShadingLow(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Low bound'
        self._choices = PERCENTILE_OPTIONS
        self._choice_images = PERCENTILE_BITMAPS

        self._pytype = tuple


class SettingsShadingHigh(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'High bound'
        self._choices = PERCENTILE_OPTIONS
        self._choice_images = PERCENTILE_BITMAPS

        self._pytype = tuple


# ======================================================================================================================
# Duplicate variables
# ======================================================================================================================
class Duplicates(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._unit = AmountUnit()
        self._frame_label = '# of duplicates'

        self._pytype = int

        self._tooltip = 'Number of duplicates to create.'


class DuplicateAsControlled(Variable):
    def __init__(self, unit_system=None):
        super().__init__()
        self._frame_label = 'Duplicate as controlled'

        self._pytype = bool

        self._tooltip = 'Duplicated entities will only allow minor\n' \
                        'configuration. All properties will be determined\n' \
                        'by the controlling entity (the one duplicated).'
