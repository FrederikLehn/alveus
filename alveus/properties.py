import copy

from _ids import *
from _errors import AssembleError, ConvergenceError
from utilities import GetAttributes, ReturnProperty, ReturnProperties

from profile_ import Profile
from optimize import secant
from curve_fit import AssemblyFunction
from statistics import *
from timeline import MergeDatelines


# ======================================================================================================================
# Classes to be sub-classed
# ======================================================================================================================
class PropertyGroup:
    def __init__(self):

        self._is_hierarchical = False
        self._is_derived = False

    def Copy(self):
        return copy.deepcopy(self)

    def CopyFrom(self, properties):
        attr = GetAttributes(self, exclude=('_use_self', '_hierarchy_type', '_is_derived', '_is_hierarchical', '_derived'))

        for a in attr:
            setattr(self, a[0], copy.deepcopy(getattr(properties, a[0])))

    def DuplicateFrom(self, properties):
        for a in GetAttributes(self, name_only=True):
            setattr(self, a, copy.deepcopy(getattr(properties, a)))

    @staticmethod
    def ExtractProperties(children, properties, variable):
        properties = [c.GetProperties().Get(properties, variable) for c in children]
        return np.array([p for p in properties if p is not None])

    def InitialDuplication(self):
        pass

    def IsHierarchical(self):
        return self._is_hierarchical

    def IsDerived(self):
        return self._is_derived


class HierarchicalProperty(PropertyGroup):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__()

        self._is_hierarchical = True
        self._hierarchy_type = hierarchy_type
        self._use_self = use_self

    def GetHierarchyType(self):
        return self._hierarchy_type

    def SetHierarchyType(self, hierarchy):
        self._hierarchy_type = hierarchy

    def SetUseSelf(self, state):
        self._use_self = state

    def UseHierarchy(self):
        return not self._use_self

    def FromHierarchyType(self, type_):
        return self._hierarchy_type == type_


class DerivedProperty(PropertyGroup):
    def __init__(self, derived=False):
        super().__init__()

        self._is_derived = True
        self._derived = derived

    def SetDerived(self, state):
        self._derived = state

    def UseDerived(self):
        return self._derived


# ======================================================================================================================
# Variable holder classes. They have both front-end and a back-end methods.
# ======================================================================================================================
class ConstrainedModelProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._availability = None
        self._constrained = False

    def get(self):
        return ReturnProperty(self._availability, default=1.), self._constrained

    def Get(self):
        return self._availability, self._constrained

    def Set(self, availability, constrained):
        self._availability = availability
        self._constrained = constrained


class CulturalProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._cultural = None
        self._path = None

    def Get(self):
        return self._cultural, self._path

    def GetCultural(self):
        return self._cultural

    def Set(self, cultural, path):
        self._cultural = cultural
        self._path = path


class DurationProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._start = None
        self._end = None

    def get(self):
        return self._start, self._end

    def Get(self):
        return self._start, self._end

    def Set(self, start, end):
        self._start = start
        self._end = end


class EvaluationProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._cum_eval = None   # string that can be read by python eval(x)
        self._rate_eval = None  # string that can be read by python eval(x)
        self._ffw_eval = None   # string that can be read by python eval(x)
        self._ffg_eval = None   # string that can be read by python eval(x)

    def eval(self, id_, length, hcft, hcpv, permeability, oil_density):

        if id_ == 0:
            expression = self._cum_eval
        elif id_ == 1:
            expression = self._rate_eval
        elif id_ == 2:
            expression = self._ffw_eval
        elif id_ == 3:
            expression = self._ffg_eval
        else:
            expression = ''

        if not expression or (expression is None):
            return

        try:

            scaler = eval(expression)

        except NameError:
            raise

        except SyntaxError:
            raise SyntaxError('\'{}\''.format(expression))

        except ZeroDivisionError:
            return

        if scaler == 0.:
            return

        return scaler

    def Get(self):
        return self._cum_eval, self._rate_eval, self._ffw_eval, self._ffg_eval

    def Set(self, cum_eval, rate_eval, ffw_eval, ffg_eval):
        self._cum_eval = cum_eval
        self._rate_eval = rate_eval
        self._ffw_eval = ffw_eval
        self._ffg_eval = ffg_eval


class FlowConstraintProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._oil_constraint = None
        self._gas_constraint = None
        self._water_constraint = None
        self._liquid_constraint = None

    def get(self):
        return {ID_OIL_NW: self._oil_constraint,
                ID_GAS_NW: self._gas_constraint,
                ID_WATER_NW: self._water_constraint,
                ID_LIQUID_NW: self._liquid_constraint}

    def Get(self):
        return self._oil_constraint, self._gas_constraint, self._water_constraint, self._liquid_constraint

    def Set(self, oil_constraint, gas_constraint, water_constraint, liquid_constraint):
        self._oil_constraint = oil_constraint
        self._gas_constraint = gas_constraint
        self._water_constraint = water_constraint
        self._liquid_constraint = liquid_constraint


class FlowSplitProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._split = None
        self._oil_split = None
        self._gas_split = None
        self._water_split = None
        self._inj_gas_split = None
        self._inj_water_split = None

    def get(self):
        oil = ReturnProperty(self._oil_split, default=0.)
        gas = ReturnProperty(self._gas_split, default=0.)
        water = ReturnProperty(self._water_split, default=0.)
        inj_gas = ReturnProperty(self._inj_gas_split, default=0.)
        inj_water = ReturnProperty(self._inj_water_split, default=0.)

        return self._split, {ID_OIL_NW: oil,
                             ID_GAS_NW: gas,
                             ID_WATER_NW: water,
                             ID_INJ_GAS_NW: inj_gas,
                             ID_INJ_WATER_NW: inj_water}

    def Get(self):
        return self._split, self._oil_split, self._gas_split, self._water_split,\
               self._inj_gas_split, self._inj_water_split

    def Set(self, split, oil_split, gas_split, water_split, inj_gas_split, inj_water_split):
        self._split = split
        self._oil_split = oil_split
        self._gas_split = gas_split
        self._water_split = water_split
        self._inj_gas_split = inj_gas_split
        self._inj_water_split = inj_water_split


class FunctionProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        # models (assigned on CurveFitFrame)
        self._models = []    # list of class Model

        # run start-point (assigned on FunctionFrame)
        self._point = None   # id (int)
        self._axis = None    # id (int)
        self._value = None   # float
        self._run_to = None  # float, only used when displaying on FunctionPanel, not for simulations

        # offset (calculated from the point, axis and value during save procedure)
        self._offset = 0.    # float

        # limit
        self._limits = (0., None)

    def Assemble(self):
        f = AssemblyFunction()

        # get all included models
        models = [model for model in self._models if model.Include()]
        if not models:
            raise AssembleError('No models are included.')

        # set initial model
        model = models[0]
        if not model.IsParametric():
            raise AssembleError('First model is non-parametric')

        model_fit = model.GetModelFit()
        multiplier, addition = ReturnProperties(model.GetModifiers(), defaults=(1., 0.))

        f.SetInitial(model_fit, multiplier, addition)

        # set all other models
        for i, model in enumerate(models[1:]):
            previous_model = models[i]

            model_fit = model.GetModelFit()
            type_, point, rate = ReturnProperties(previous_model.GetMerges(), defaults=(None, None, 1.))

            if None in (type_, point):
                continue

            if not model.IsParametric():
                _, next_point, _ = model.GetMerges()
                args = (point, next_point)

                # if the next model is not included, throw assemble error
                if i >= len(models) - 2:
                    raise AssembleError('Last model is non-parametric')

            else:
                args = ()

            multiplier, addition = ReturnProperties(model.GetModifiers(), defaults=(1., 0.))

            try:

                f.Add(model_fit, type_, point, rate, multiplier, addition, args=args)

                # testing models ability to evaluate
                f.eval(np.zeros(1))

            except ConvergenceError as e:

                raise ConvergenceError('Unable to evaluate model ({}) due to: {}'.format(model.GetLabel(), str(e)))

            except TypeError as e:

                raise TypeError('Unable to evaluate model ({}) due to: {}'.format(model.GetLabel(), str(e)))

            except AttributeError:

                raise AttributeError('Unable to evaluate model ({}) due to missing a method.'.format(model.GetLabel()))

        f.SetLimits(self._limits)
        f.SetOffset(self._offset)

        return f

    def CalculateOffset(self, x, y, profile=None):
        # viable profile input
        x_var = []
        available = False

        if profile is not None:
            x_var = profile.Get(x)
            if x_var.size:
                available = True

        # calculate offset
        offset = 0.
        if self._point == ID_FIRST and available:

            offset = x_var[0]

        elif self._point == ID_LAST and available:

            offset = x_var[-1]

        elif self._point == ID_SPECIFIC:

            if self._value is not None:

                if self._axis == ID_ON_X_AXIS:

                    offset = self._value

                elif self._axis == ID_ON_Y_AXIS and available:

                    try:
                        fun = self.Assemble()
                        offset = max(0., secant(lambda x_: fun.eval(x_) - self._value, x_var[0], x_var[-1]))
                    except AssembleError:
                        pass

        self._offset = offset

    def GetModels(self):
        return self._models

    def GetRun(self):
        return self._point, self._axis, self._value, self._run_to

    def Initialize(self):
        self._models = [copy.deepcopy(model) for model in self._models]

    def SetLimits(self, limits):
        self._limits = limits

    def SetModels(self, models):
        self._models = models

    def SetRun(self, point, axis, value, run_to):
        self._point = point
        self._axis = axis
        self._value = value
        self._run_to = run_to

    def UpdateModels(self, models):
        old_models = list(self._models)

        self._models = copy.deepcopy(models)
        for i, model in enumerate(self._models):
            for old_model in old_models:
                if model.GetId() == old_model.GetId():
                    model.Update(old_model)
                    break


class FunctionsProperty(HierarchicalProperty):
    """
    Shared between Analogues and Typecurves. Analogues supply the functions and Typecurves supply the rest.
    Has a unique hierarchical CopyFrom method to handle changes in the order of or number of functions.
    Similarly used for the DCA on producers.
    """
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._liquid_potential = FunctionProperty()
        self._water_cut = FunctionProperty()
        self._gas_oil_ratio = FunctionProperty()

    def Assemble(self):
        return self._liquid_potential.Assemble(), self._water_cut.Assemble(), self._gas_oil_ratio.Assemble()

    def CopyFrom(self, properties):
        self.UpdateModels(*properties.GetModels())

    def Get(self):
        return self._liquid_potential, self._water_cut, self._gas_oil_ratio

    def GetModels(self):
        return self._liquid_potential.GetModels(), self._water_cut.GetModels(), self._gas_oil_ratio.GetModels()

    def GetVariable(self, id_):
        return getattr(self, id_)

    def Initialize(self):
        self._liquid_potential.Initialize()
        self._water_cut.Initialize()
        self._gas_oil_ratio.Initialize()

    def Set(self, liquid_potential, water_cut, gas_oil_ratio):
        self._liquid_potential = liquid_potential
        self._water_cut = water_cut
        self._gas_oil_ratio = gas_oil_ratio

    def SetModels(self, liquid_potential, water_cut, gas_oil_ratio):
        self._liquid_potential.SetModels(liquid_potential)
        self._water_cut.SetModels(water_cut)
        self._gas_oil_ratio.SetModels(gas_oil_ratio)

    def UpdateModels(self, liquid_potential, water_cut, gas_oil_ratio):
        self._liquid_potential.UpdateModels(liquid_potential)
        self._water_cut.UpdateModels(water_cut)
        self._gas_oil_ratio.UpdateModels(gas_oil_ratio)


class GasLiftConstraintProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._gas_lift_constraint = None

    def get(self):
        return {ID_LIFT_GAS_NW: self._gas_lift_constraint}

    def Get(self):
        return (self._gas_lift_constraint,)

    def Set(self, gas_lift_constraint):
        self._gas_lift_constraint = gas_lift_constraint


class GasLiftProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._tglr = None

    def get(self):
        return ReturnProperty(self._tglr, default=0.)

    def Get(self):
        return self._use_self, self._tglr

    def Set(self, use_self, tglr):
        self._use_self = use_self
        self._tglr = tglr


class HierarchicalPointerProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._pointer = None  # (id, attribute)

    def get(self):
        return self._pointer

    def Get(self):
        return self._use_self, self._pointer,

    def Set(self, use_self, pointer):
        self._use_self = use_self
        self._pointer = pointer


class HistoryProperty(DerivedProperty):
    def __init__(self, derived=False):
        super().__init__(derived)

        self._profile = None
        self._path = None

    def get(self):
        return self._profile

    def Get(self):
        return self._profile, self._path

    def GetProfile(self, variable=None):
        if variable is None:
            return self._profile
        else:
            return getattr(self._profile, variable)()

    def Merge(self, children):
        profiles = [c.GetHistory() for c in children if c.GetHistory() is not None]
        if not profiles:
            return

        dateline = MergeDatelines([p.date() for p in profiles])
        self._profile = Profile()
        self._profile.Allocate(dateline)
        self._profile.Sum(profiles)

    def Set(self, profile, path=None):
        self._profile = profile
        self._path = path


class InflowProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._oil = False
        self._gas = False
        self._water = False
        self._inj_gas = False
        self._inj_water = False

    def get(self):
        return {ID_OIL_NW: self._oil,
                ID_GAS_NW: self._gas,
                ID_WATER_NW: self._water,
                ID_INJ_GAS_NW: self._inj_gas,
                ID_INJ_WATER_NW: self._inj_water}

    def Get(self):
        return self._oil, self._gas, self._water, self._inj_gas, self._inj_water

    def Set(self, oil, gas, water, inj_gas, inj_water):
        self._oil = oil
        self._gas = gas
        self._water = water
        self._inj_gas = inj_gas
        self._inj_water = inj_water


class InjectionConstraintProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._gas_inj_constraint = None
        self._water_inj_constraint = None

    def get(self):
        return {ID_INJ_GAS_NW: self._gas_inj_constraint,
                ID_INJ_WATER_NW: self._water_inj_constraint}

    def Get(self):
        return self._gas_inj_constraint, self._water_inj_constraint

    def Set(self, gas_inj_constraint, water_inj_constraint):
        self._gas_inj_constraint = gas_inj_constraint
        self._water_inj_constraint = water_inj_constraint


class InjectionFluidProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._bg_inj = None
        self._bw_inj = None

    def get(self):
        return ReturnProperty(self._bg_inj, default=1.),\
               ReturnProperty(self._bw_inj, default=1.),

    def Get(self):
        return self._use_self, self._bg_inj, self._bw_inj

    def Set(self, use_self, bg_inj, bw_inj):
        self._use_self = use_self
        self._bg_inj = bg_inj
        self._bw_inj = bw_inj


class InjectionPotentialProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._gas_inj = None
        self._water_inj = None

    def get(self):
        return self._gas_inj, self._water_inj

    def Get(self):
        return self._use_self, self._gas_inj, self._water_inj

    def Set(self, use_self, gas_inj, water_inj):
        self._use_self = use_self
        self._gas_inj = gas_inj
        self._water_inj = water_inj


class LicenseProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._license = None

    def Get(self):
        return (self._license,)

    def Set(self, license_):
        self._license = license_


class PhaseProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._phase = None

    def get(self):
        return self._phase

    def Get(self):
        return (self._phase,)

    def Set(self, phase):
        self._phase = phase


class PlateauProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._plateau_oil = None
        self._plateau_gas = None

    def get(self):
        return self._plateau_oil, self._plateau_gas

    def Get(self):
        return self._plateau_oil, self._plateau_gas

    def Set(self, plateau_oil, plateau_gas):
        self._plateau_oil = plateau_oil
        self._plateau_gas = plateau_gas


class PointerProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._pointer = None  # (id, attribute)

    def get(self):
        return self._pointer

    def Get(self):
        return (self._pointer,)

    def Set(self, pointer):
        self._pointer = pointer


class PredictionProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._type = None                      # id (int)
        self._pointer = None                   # (id, type) pointer to EntityManager
        self._functions = FunctionsProperty()  # typecurve defined on the producer
        self._profile = None                   # class Profile of imported data
        self._path = None                      # import file path (only used for style)
        self._occurrence = None                # probability of occurrence

    def get(self):
        if self._type == ID_PREDICTION_TYPECURVE:

            prediction = self._pointer

        elif self._type == ID_PREDICTION_FUNCTION:

            prediction = self._functions.Assemble()

        else:  # ID_PREDICTION_IMPORT

            prediction = (ProfileFunctionProperty(self._profile, 'time', 'liquid_potential'),
                          ProfileFunctionProperty(self._profile, 'oil_cumulative', 'oil_cut'),
                          ProfileFunctionProperty(self._profile, 'time', 'gas_oil_ratio'))

        return self._type, prediction

    def Get(self):
        return self._type, self._pointer, self._functions, self._profile, self._path, self._occurrence

    def GetFunctions(self):
        return self._functions

    def GetOccurrence(self):
        return self._occurrence

    def GetType(self):
        return self._type

    def Set(self, type_, pointer, functions, profile, path, occurrence):
        self._type = type_
        self._pointer = pointer
        self._functions = functions
        self._profile = profile
        self._path = path
        self._occurrence = occurrence

    def SetFunctions(self, functions):
        self._functions = functions

    def SetOccurrence(self, occurrence):
        self._occurrence = occurrence

    def SetType(self, type_):
        self._type = type_

    def UpdateModels(self, liquid_potential, oil_cut, gas_oil_ratio):
        self._functions.UpdateModels(liquid_potential, oil_cut, gas_oil_ratio)


class ProfileFunctionProperty(PropertyGroup):
    def __init__(self, profile, x, y):
        super().__init__()

        self._profile = profile
        self._x = x
        self._y = y

    def eval(self, x):
        return np.interp(x, self._profile.Get(self._x)(), self._profile.Get(self._y)(), left=0., right=0.)


class ReservoirFluidProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._bo = None
        self._bg = None
        self._bw = None
        self._rs = None

    def get(self):
        return ReturnProperty(self._bo, default=1.),\
               ReturnProperty(self._bg, default=1.),\
               ReturnProperty(self._bw, default=1.),\
               ReturnProperty(self._rs, default=0.),

    def Get(self):
        return self._use_self, self._bo, self._bg, self._bw, self._rs

    def Set(self, use_self, bo, bg, bw, rs):
        self._use_self = use_self

        if use_self:
            self._bo = bo
            self._bg = bg
            self._bw = bw
            self._rs = rs


class RiskingProperty(DerivedProperty):
    def __init__(self, derived=False):
        super().__init__(derived)

        self._maturity = None
        self._pos = None

    def get(self):
        return ReturnProperties((self._maturity, self._pos), defaults=(1., 1.))

    def Get(self):
        return self._maturity, self._pos

    def Merge(self, children, weight=False):
        if weight:
            w = np.array([c.Summary('bte') for c in children])
            sumw = Sum(w)
        else:
            w = None
            sumw = None

        self._maturity = Average(self.ExtractProperties(children, 'risking',  'maturity'), w, sumw)
        self._pos = Average(self.ExtractProperties(children, 'risking', 'pos'), w, sumw)

    def Set(self, maturity, pos):
        self._maturity = maturity
        self._pos = pos


class SamplingProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._samples = None
        self._save_all = False

    def get(self):
        return ReturnProperty(self._samples, default=1), self._save_all

    def Get(self):
        return self._samples, self._save_all

    def Set(self, samples, save_all):
        self._samples = samples
        self._save_all = save_all


class ScalingProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._s_cum = None
        self._s_rate = None
        self._s_ffw = None
        self._s_ffg = None
        self._onset = None
        self._wct_ini = None

    @staticmethod
    def assign(scalers):
        scalers[0] = ReturnProperty(scalers[0], default=1.)           # s_cum
        scalers[1] = ReturnProperty(scalers[1], default=1.)           # s_rate
        scalers[2] = ReturnProperty(scalers[2], default=1.)           # s_ffw
        scalers[3] = ReturnProperty(scalers[3], default=1.)           # s_ffg
        scalers[4] = ReturnProperty(scalers[4], default=0.) * 365.25  # onset
        scalers[5] = ReturnProperty(scalers[5], default=0.) / 100.    # wct_ini

        return scalers

    def get(self):
        onset = self._onset * 365.25 if self._onset is not None else None
        wct_ini = self._wct_ini / 100. if self._wct_ini is not None else None

        return self._s_cum, self._s_rate, self._s_ffw, self._s_ffg, onset, wct_ini

    def Get(self):
        return self._use_self, self._s_cum, self._s_rate, self._s_ffw, self._s_ffg, self._onset, self._wct_ini

    def Set(self, use_self, s_cum, s_rate, s_ffw, s_ffg, onset, wct_ini):
        self._use_self = use_self

        if use_self:
            self._s_cum = s_cum
            self._s_rate = s_rate
            self._s_ffw = s_ffw
            self._s_ffg = s_ffg
            self._onset = onset
            self._wct_ini = wct_ini


class ScalingUncertaintyProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._cum = UncertaintyProperty()
        self._rate = UncertaintyProperty()
        self._ffw = UncertaintyProperty()
        self._ffg = UncertaintyProperty()
        self._onset = UncertaintyProperty()
        self._wct_ini = UncertaintyProperty()

    def get(self):
        return self._cum, self._rate, self._ffw, self._ffg, self._onset, self._wct_ini

    def Get(self):
        return self._use_self, self._cum.Get(), self._rate.Get(), self._ffw.Get(), self._ffg.Get(), self._onset.Get(), self._wct_ini.Get()

    def Set(self, use_self, cum, rate, ffw, ffg, onset, wct_ini):
        self._use_self = use_self

        if use_self:
            self._cum.Set(*cum)
            self._rate.Set(*rate)
            self._ffw.Set(*ffw)
            self._ffg.Set(*ffg)
            self._onset.Set(*onset)
            self._wct_ini.Set(*wct_ini)


class StabilityProperty(PropertyGroup):
    def __init__(self):
        super().__init__()
        self._stability = None  # (4, 3, samples) array of P10, P50, P90 for 4 variables as function of samples

    def Get(self):
        return self._stability

    def Set(self, stability):
        self._stability = stability


class StaticProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._length = None
        self._hcft = None
        self._hcpv = None
        self._permeability = None
        self._oil_density = None

    def get(self):
        length = ReturnProperty(self._length, default=0.)
        hcft = ReturnProperty(self._hcft, default=0.)
        hcpv = ReturnProperty(self._hcpv, default=0.)
        permeability = ReturnProperty(self._permeability, default=0.)
        oil_density = ReturnProperty(self._oil_density, default=0.)

        return length, hcft, hcpv, permeability, oil_density

    def Get(self):
        return self._use_self, self._length, self._hcft, self._hcpv, self._permeability, self._oil_density

    def Set(self, use_self, length, hcft, hcpv, permeability, oil_density):
        self._use_self = use_self

        if use_self:
            self._length = length
            self._hcft = hcft
            self._hcpv = hcpv
            self._permeability = permeability
            self._oil_density = oil_density


class StaticUncertaintyProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._length = UncertaintyProperty()
        self._hcft = UncertaintyProperty()
        self._hcpv = UncertaintyProperty()
        self._permeability = UncertaintyProperty()
        self._oil_density = UncertaintyProperty()

    def get(self):
        return self._length, self._hcft, self._hcpv, self._permeability, self._oil_density

    def Get(self):
        return self._use_self, self._length.Get(), self._hcft.Get(), self._hcpv.Get(), self._permeability.Get(), self._oil_density.Get()

    def Set(self, use_self, length, hcft, hcpv, permeability, oil_density):
        self._use_self = use_self

        if use_self:
            self._length.Set(*length)
            self._hcft.Set(*hcft)
            self._hcpv.Set(*hcpv)
            self._permeability.Set(*permeability)
            self._oil_density.Set(*oil_density)


class TimelineProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._frequency = None  # False
        self._delta = None

    def get(self):
        return self._frequency, self._delta

    def Get(self):
        return self._frequency, self._delta

    def Set(self, frequency, delta):
        self._frequency = frequency
        self._delta = delta


class TotalProductionProperty(PropertyGroup):
    def __init__(self):
        super().__init__()
        self._dateline = None
        self._history = None
        self._simulated = None

    def Get(self):
        return self._dateline, self._history, self._simulated

    def Set(self, dateline, history, simulated):
        self._dateline = dateline
        self._history = history
        self._simulated = simulated


class UncertainPredictionProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._low = PredictionProperty()
        self._mid = PredictionProperty()
        self._high = PredictionProperty()

    def get(self):
        return self._low, self._mid, self._high

    def get_occurrences(self):
        types = (self._low.GetType(), self._mid.GetType(), self._high.GetType())
        occurrences = (ReturnProperty(self._low.GetOccurrence(), default=0.) / 100.,
                       ReturnProperty(self._mid.GetOccurrence(), default=0.) / 100.,
                       ReturnProperty(self._high.GetOccurrence(), default=0.) / 100.)

        count_type = 0
        count_occu = 0
        cum = 0.
        for (type_, occurrence) in zip(types, occurrences):
            if type_ is not None:
                cum += occurrence
                count_type += 1

                if occurrence:
                    count_occu += 1

        count = count_type - count_occu

        if (types[0] is not None) and (self._low.GetOccurrence() is None):
            low = (1. - cum) / count
        else:
            low = occurrences[0]

        if (types[1] is not None) and (self._mid.GetOccurrence() is None):
            mid = (1. - cum) / count
        else:
            mid = occurrences[1]

        return low, low + mid

    def AdjustOccurrence(self):
        low = ReturnProperty(self._low.GetOccurrence(), default=0.)
        mid = ReturnProperty(self._mid.GetOccurrence(), default=0.)
        high = ReturnProperty(self._high.GetOccurrence(), default=0.)

        cum = low + mid + high
        if cum > 0.:
            low *= 100. / cum
            mid *= 100. / cum
            high *= 100. / cum
        else:
            low = 33.3
            mid = 33.4
            high = 33.3

        if self._low.GetOccurrence() is not None:
            self._low.SetOccurrence(low)

        if self._mid.GetOccurrence() is not None:
            self._mid.SetOccurrence(mid)

        if self._high.GetOccurrence() is not None:
            self._high.SetOccurrence(high)

    def Get(self):
        return self._use_self, self._low, self._mid, self._high

    def Set(self, use_self, low, mid, high):
        self._use_self = use_self

        if use_self:
            self._low.Set(*low.Get())
            self._mid.Set(*mid.Get())
            self._high.Set(*high.Get())

            self.AdjustOccurrence()


class UncertaintyProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._distribution = None
        self._parameters = []  # list of [float]

    def Get(self):
        return self._distribution, self._parameters

    def Set(self, distribution, *parameters):
        self._distribution = distribution
        self._parameters = parameters

    def sample(self, x, value):

        if self._parameters and any(self._parameters):
            par1, par2, par3 = ReturnProperties(self._parameters, defaults=(0., 0., 0.))
        else:
            return value

        if self._distribution == ID_DIST_SWANSON:

            a = 1. + par1 / 100.
            c = 1. + par2 / 100.
            b = 1. + par3 / 100.

            if not a <= c <= b:
                raise ValueError('Swanson\'s distribution requires min ({}) <= mode ({}) <= max ({})'.format(a, c, b))

            u = stnormal2swanson(x, a, c, b)

        elif self._distribution == ID_DIST_UNIFORM:

            a = 1. + par1 / 100.
            b = 1. + par2 / 100.

            if not a <= b:
                raise ValueError('Uniform distribution requires min ({}) <= max ({})'.format(a, b))

            u = stnormal2uniform(x, a, b)

        elif self._distribution == ID_DIST_TRIANGULAR:

            a = 1. + par1 / 100.
            c = 1. + par2 / 100.
            b = 1. + par3 / 100.

            if not a <= c <= b:
                raise ValueError('Triangular distribution requires min ({}) <= mode ({}) <= max ({})'.format(a, c, b))

            u = stnormal2triangular(x, a, c, b)

        elif self._distribution == ID_DIST_NORMAL:

            mu = 1 + par1 / 100.
            sigma = mu * par2 / 100.
            u = np.clip(stnormal2normal(x, mu, sigma), 0., None)  # TODO: temporary solution, requires truncated normal

        elif self._distribution == ID_DIST_LOGNORMAL:

            m = 1 + par1 / 100.
            v = (m * par2 / 100.) ** 2.
            u = stnormal2lognormal(x, m, v)

        else:

            u = 1.

        return value * u


class AvailabilityProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._availability = None

    def get(self):
        return ReturnProperty(self._availability, default=1.)

    def Get(self):
        return self._use_self, self._availability

    def Set(self, use_self, availability):
        self._use_self = use_self
        self._availability = availability


class VoidageProperty(PropertyGroup):
    def __init__(self):
        super().__init__()

        self._voidage_ratio = None
        self._proportions = {}  # dictionary of {id: [producer_name, proportion, is_edited]}

    def get(self):
        return ReturnProperty(self._voidage_ratio, default=1.),\
               self._proportions

    def get_ratio(self):
        return self._voidage_ratio

    def get_proportion(self, id_):
        return self._proportions[id_][1]

    def get_voidage_proportion(self, id_):
        ratio = ReturnProperty(self._voidage_ratio, default=1.)
        return ratio * self._proportions[id_][1]

    def get_cumulative_voidage(self):
        return np.sum([p[1] for p in self._proportions.values()]) * ReturnProperty(self._voidage_ratio, default=1.0)

    def DuplicateFrom(self, properties):
        proportions = copy.deepcopy(self._proportions)
        self.CopyFrom(properties)
        self._proportions = proportions

    def InitialDuplication(self):
        self._proportions = {}

    def Get(self):
        return self._voidage_ratio, self._proportions

    def Set(self, voidage_ratio, proportions):
        self._voidage_ratio = voidage_ratio
        self._proportions = proportions


class VolumeProperty(DerivedProperty):
    def __init__(self, derived=False):
        super().__init__(derived)

        self._stoiip = None

    def get(self):
        return ReturnProperty(self._stoiip, default=0.)

    def Get(self):
        return (self._stoiip,)

    def Merge(self, children):
        # inplace volumes
        self._stoiip = Sum(self.ExtractProperties(children, 'volumes', 'stoiip'))

    def Set(self, stoiip):
        self._stoiip = stoiip


class WagProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._wag_cycle = None
        self._wag_cycles = None

    def get(self):
        return ReturnProperty(self._wag_cycle, default=0.),\
               ReturnProperty(self._wag_cycles, default=0)

    def Get(self):
        return self._use_self, self._wag_cycle, self._wag_cycles

    def Set(self, use_self, wag_cycle, wag_cycles):
        self._use_self = use_self

        if use_self:
            self._wag_cycle = wag_cycle
            self._wag_cycles = wag_cycles


class WellSpacingProperty(HierarchicalProperty):
    def __init__(self, hierarchy_type=None, use_self=True):
        super().__init__(hierarchy_type, use_self)

        self._layout = None
        self._spacing = None

    def get(self):
        return self._layout, self._spacing

    def Get(self):
        return self._use_self, self._layout, self._spacing

    def Set(self, use_self, layout, spacing):
        self._use_self = use_self

        if use_self:
            self._layout = layout
            self._spacing = spacing


# ======================================================================================================================
# Special classes used for scenario, analogue, typecurve and simulation entities
# ======================================================================================================================
class EventList:
    def __init__(self):
        self._events = []  # list of Class Event()

    def GetEvents(self):
        return self._events

    def SetEvents(self, events):
        self._events = events


class SimulationResult:
    def __init__(self, lmh=(), profiles=(), summaries=(), lmh_p=(), shading=False, finalized=False):

        self._lmh = lmh      # int, index of representatively sampled L (0), M (1) & H (2)
        self._lmh_p = lmh_p  # alternative option for injectors which are commingled from different producer samples

        # shading parameter
        self._shading = shading      # bool, check for whether shading is included in the simulation

        self._finalized = finalized  # bool, check for whether hierarchical propagation is finalized
        self._profiles = profiles    # list, containing classes [Profile(), ...]
        self._summaries = summaries  # list, dictionaries with [{summary_id: float}, ...]
        self._rates = []             # list, numpy arrays with sums of rates, used for calculating uptimes

    # back-end code ----------------------------------------------------------------------------------------------------
    def get_lmh(self):
        return self._lmh

    # front-end code ---------------------------------------------------------------------------------------------------
    def AddSummary(self, id_):
        """
        Add a newly added summary to the summaries, initialized with a 0 value.

        Parameters
        ----------
        id_ : int
            Id index to add to dictionary
        """

        for summary in self._summaries:
            summary[id_] = 0.

    def ClearSamples(self):
        if (not self._shading) and self._lmh:
            self._profiles = [self._profiles[i] for i in self._lmh]
            self._summaries = [self._summaries[i] for i in self._lmh]
            self._lmh = [0, 1, 2]

        self._rates = []

    def DeleteSummary(self, id_):
        for summary in self._summaries:
            del summary[id_]

    def FinalizeSamples(self, shading, settings):
        extraction = settings.GetExtraction()

        if not extraction:
            raise ValueError('No summary defined for extraction of L/M/H profiles')

        weights = np.full(len(extraction), 1. / len(extraction))
        cases = settings.GetCases(False)

        for i, sample in enumerate(self._profiles):
            sample.calculate_uptime(sample.values, self._rates[i])

        self._lmh = ExtractRealizations(self._summaries, extraction, weights, cases)

        self._finalized = True
        self._shading = shading

    def GetHighProfile(self, variable=None):
        if variable is None:
            if self._lmh:
                return self._profiles[self._lmh[2]]
            elif self._lmh_p:
                return self._lmh_p[2]
        else:
            if self._lmh:
                return self._profiles[self._lmh[2]].Get(variable)
            elif self._lmh_p:
                return self._lmh_p[2].Get(variable)

    def GetLowProfile(self, variable=None):
        if variable is None:
            if self._lmh:
                return self._profiles[self._lmh[0]]
            elif self._lmh_p:
                return self._lmh_p[0]
        else:
            if self._lmh:
                return self._profiles[self._lmh[0]].Get(variable)
            elif self._lmh_p:
                return self._lmh_p[0].Get(variable)

    def GetProfile(self, variable=None, idx=1):
        if variable is None:
            if self._lmh:
                return self._profiles[self._lmh[idx]]
            elif self._lmh_p:
                return self._lmh_p[idx]
        else:
            if self._lmh:
                return self._profiles[self._lmh[idx]].Get(variable)
            elif self._lmh_p:
                return self._lmh_p[idx].Get(variable)

    def GetProfiles(self):
        return self._profiles

    def GetSummary(self, variable=None):
        # TODO: Temporary for injectors
        if not self._lmh:
            return None

        if variable is None:
            return self._summaries[self._lmh[1]]
        else:
            return self._summaries[self._lmh[1]][variable]

    def GetSummaries(self):
        return self._summaries

    def GetShading(self, resolution, low, high, variable=None):
        shade = np.linspace(low, high, resolution + 1)

        if self._shading:
            return EnsembleDistribution(self._profiles, variable, shade)

    def HasShading(self):
        return self._shading

    def InitializeSamples(self, n, dateline, summaries):
        self._profiles = [Profile() for _ in range(n)]
        for p in self._profiles:
            p.Allocate(dateline)

        self._rates = [np.zeros((dateline.size, 6)) for _ in range(n)]
        self._summaries = [{summary.GetId(): 0. for summary in summaries} for _ in range(n)]

    def IsFinalized(self):
        return self._finalized

    def MergeProfile(self, profiles):
        for i, profile in enumerate(profiles):
            self._profiles[i].Add(profile)

            for j in range(6):
                self._rates[i][:, j] += self._profiles[i].interpolate_rate(profile.time(), profile.values[:, j], profile.uptime(j))

    def MergeSummary(self, summaries):
        for i, summary in enumerate(summaries):
            for id_, value in summary.items():
                self._summaries[i][id_] += value


# ======================================================================================================================
# Special class used for Summary Variable (only one not sitting on an Entity, but a Variable)
# ======================================================================================================================
class SummaryProperty:
    def __init__(self):

        self._production = None
        self._icon = None
        self._eval = None
        self._function = None
        self._point = None
        self._date = None
        self._time = None

    def Calculate(self, profile, property_map):
        # calculate multiplier
        mult = 1.

        if self._eval and (self._eval is not None):
            try:
                mult = eval(self._eval, {}, property_map)

            except NameError:
                raise

            except SyntaxError:
                raise SyntaxError('Error in statement: \'{}\''.format(self._eval))

            except ZeroDivisionError:
                return 0.

        # get production profile
        production = profile.Get(self._production)

        # calculate scalar from production profile
        scalar = 0.
        function = ReturnProperty(self._function, default=ID_POINT)
        point = ReturnProperty(self._point, default=ID_POINT_LAST)

        if function == ID_POINT:

            if point == ID_POINT_FIRST:

                scalar = production[0]

            elif point == ID_POINT_LAST:

                scalar = production[-1]

            elif point == ID_POINT_DATE:

                date = profile.date()
                if self._date > date[-1]:
                    idx = -1
                else:
                    idx = np.argmax(date >= self._date)

                scalar = production[idx]

            elif point == ID_POINT_TIME:

                days = self._time * 365.25
                time = profile.time()

                if days >= time[-1]:
                    idx = -1
                else:
                    idx = np.argmax(time >= days)

                scalar = production[idx]

        elif function == ID_SUM:

            scalar = np.sum(production)

        elif function == ID_AVERAGE:

            scalar = np.mean(production)

        return scalar * mult

    def Get(self):
        return self._production, self._icon, self._eval, self._function, self._point, self._date, self._time

    def Set(self, production, icon, eval_, function, point, date, time):
        self._production = production
        self._icon = icon
        self._eval = eval_
        self._function = function
        self._point = point
        self._date = date
        self._time = time


# ======================================================================================================================
# Grouping properties as they will be supplied to Entities. They have both front-end and a back-end methods.
# ======================================================================================================================
class BaseProperties:
    def __init__(self):
        pass

    def Copy(self):
        return copy.deepcopy(self)

    def DuplicateFrom(self, properties):
        for a, attr in GetAttributes(self):
            attr.DuplicateFrom(getattr(properties, a))

    def Get(self, type_, variable=None):
        if variable is not None:
            return getattr(getattr(self, type_), '_{}'.format(variable))
        else:
            return getattr(self, type_)

    def GetHierarchicalAttributes(self):
        return (a[0] for a in GetAttributes(self) if a[1].IsHierarchical())

    def GetHierarchicalTypes(self):
        return [a for a in self.GetHierarchicalAttributes()]

    def GetDerivedAttributes(self):
        return (a[0] for a in GetAttributes(self) if a[1].IsDerived())

    def GetDerivedTypes(self):
        return (a for a in self.GetDerivedAttributes())

    def HasProperty(self, type_):
        return hasattr(self, type_)

    def InitialDuplication(self):
        for attr in GetAttributes(self, attr_only=True):
            attr.InitialDuplication()


class ProjectProperties(BaseProperties):
    def __init__(self):
        super().__init__()


class HistoryProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.constrained = ConstrainedModelProperty()
        self.timeline = TimelineProperty()

        # hidden properties
        self.total_production = TotalProductionProperty()  # output graph data from simulation
        self.duration = DurationProperty()  # accessed from Prediction


class ScenarioProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.duration = DurationProperty()


class PredictionProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.parent = PointerProperty()   # pointer to Scenario
        self.history = PointerProperty()  # pointer to History
        self.plateau = PlateauProperty()
        self.constrained = ConstrainedModelProperty()
        self.sampling = SamplingProperty()
        self.timeline = TimelineProperty()

        # hidden properties
        self.stability = StabilityProperty()  # output graph data from simulation


class FieldProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty(derived=True)
        self.license = LicenseProperty()
        self.plateau = PlateauProperty()


class BlockProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty(derived=True)
        self.license = LicenseProperty()


class ReservoirProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty(derived=True)
        self.prediction = UncertainPredictionProperty()
        self.scaling_eval = HierarchicalPointerProperty()  # pointer to scaling
        self.well_spacing = WellSpacingProperty()
        self.res_fluids = ReservoirFluidProperty()
        self.inj_fluids = InjectionFluidProperty()
        self.volumes = VolumeProperty(derived=True)
        self.risking = RiskingProperty(derived=True)
        self.statics = StaticProperty()
        self.statics_unc = StaticUncertaintyProperty()
        self.scalers = ScalingProperty()
        self.scalers_unc = ScalingUncertaintyProperty()


class ThemeProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty(derived=True)
        self.prediction = UncertainPredictionProperty(hierarchy_type=ID_RESERVOIR)
        self.scaling_eval = HierarchicalPointerProperty(hierarchy_type=ID_RESERVOIR)  # pointer to scaling
        self.well_spacing = WellSpacingProperty(hierarchy_type=ID_RESERVOIR)
        self.res_fluids = ReservoirFluidProperty(hierarchy_type=ID_RESERVOIR)
        self.inj_fluids = InjectionFluidProperty(hierarchy_type=ID_RESERVOIR)
        self.volumes = VolumeProperty(derived=True)
        self.risking = RiskingProperty(derived=True)
        self.statics = StaticProperty(hierarchy_type=ID_RESERVOIR)
        self.statics_unc = StaticUncertaintyProperty(hierarchy_type=ID_RESERVOIR)
        self.scalers = ScalingProperty(hierarchy_type=ID_RESERVOIR)
        self.scalers_unc = ScalingUncertaintyProperty(hierarchy_type=ID_RESERVOIR)


class PolygonProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty(derived=True)
        self.prediction = UncertainPredictionProperty(hierarchy_type=ID_THEME)
        self.scaling_eval = HierarchicalPointerProperty(hierarchy_type=ID_THEME)  # pointer to scaling
        self.well_spacing = WellSpacingProperty(hierarchy_type=ID_THEME)
        self.res_fluids = ReservoirFluidProperty(hierarchy_type=ID_THEME)
        self.inj_fluids = InjectionFluidProperty(hierarchy_type=ID_THEME)
        self.volumes = VolumeProperty()
        self.risking = RiskingProperty()
        self.statics = StaticProperty(hierarchy_type=ID_THEME)
        self.statics_unc = StaticUncertaintyProperty(hierarchy_type=ID_THEME)
        self.scalers = ScalingProperty(hierarchy_type=ID_THEME)
        self.scalers_unc = ScalingUncertaintyProperty(hierarchy_type=ID_THEME)


class PlatformProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty(derived=True)
        self.availability = AvailabilityProperty()
        self.gas_lift = GasLiftProperty()
        self.wag = WagProperty()
        self.inj_potentials = InjectionPotentialProperty()


class ProcessorProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty(derived=True)
        self.availability = AvailabilityProperty(hierarchy_type=ID_PLATFORM)
        self.inflow = InflowProperty()
        self.flow_constraints = FlowConstraintProperty()
        self.inj_constraints = InjectionConstraintProperty()
        self.split = FlowSplitProperty()
        self.primary_node = PointerProperty()  # pointer to another entity


class PipelineProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty(derived=True)
        self.availability = AvailabilityProperty(hierarchy_type=ID_PLATFORM)
        self.flow_constraints = FlowConstraintProperty()
        self.inj_constraints = InjectionConstraintProperty()


class AnalogueProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.cultural = CulturalProperty()
        self.history = HistoryProperty()
        self.well_spacing = WellSpacingProperty()
        self.statics = StaticProperty()
        self.statics_unc = StaticUncertaintyProperty()
        self.functions = FunctionsProperty()

        # hidden properties
        self.res_fluids = ReservoirFluidProperty(hierarchy_type=ID_POLYGON, use_self=False)


class TypecurveProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.parent = PointerProperty()  # pointer to Analogue
        self.functions = FunctionsProperty(hierarchy_type=ID_ANALOGUE, use_self=False)

        # hidden properties
        self.res_fluids = ReservoirFluidProperty(hierarchy_type=ID_ANALOGUE, use_self=False)
        self.well_spacing = WellSpacingProperty(hierarchy_type=ID_ANALOGUE, use_self=False)
        self.statics = StaticProperty(hierarchy_type=ID_ANALOGUE, use_self=False)
        self.statics_unc = StaticUncertaintyProperty(hierarchy_type=ID_ANALOGUE, use_self=False)


class ScalingProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.evaluations = EvaluationProperty()


class ProducerProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.phase = PhaseProperty()
        self.cultural = CulturalProperty()
        self.history = HistoryProperty()
        self.functions = FunctionsProperty()
        self.prediction = UncertainPredictionProperty(hierarchy_type=ID_POLYGON)
        self.scaling_eval = HierarchicalPointerProperty(hierarchy_type=ID_POLYGON)  # pointer to scaling
        self.well_spacing = WellSpacingProperty(hierarchy_type=ID_POLYGON)
        self.volumes = VolumeProperty()
        self.risking = RiskingProperty()
        self.availability = AvailabilityProperty(hierarchy_type=ID_PLATFORM)
        self.flow_constraints = FlowConstraintProperty()
        self.gl_constraint = GasLiftConstraintProperty()
        self.gas_lift = GasLiftProperty(hierarchy_type=ID_PLATFORM)
        self.statics = StaticProperty(hierarchy_type=ID_POLYGON)
        self.statics_unc = StaticUncertaintyProperty(hierarchy_type=ID_POLYGON)
        self.scalers = ScalingProperty(hierarchy_type=ID_POLYGON)
        self.scalers_unc = ScalingUncertaintyProperty(hierarchy_type=ID_POLYGON)

        # hidden properties
        self.res_fluids = ReservoirFluidProperty(hierarchy_type=ID_POLYGON, use_self=False)


class InjectorProperties(BaseProperties):
    def __init__(self):
        super().__init__()

        self.phase = PhaseProperty()
        self.cultural = CulturalProperty()
        self.history = HistoryProperty()
        self.availability = AvailabilityProperty(hierarchy_type=ID_PLATFORM)
        self.inj_constraints = InjectionConstraintProperty()
        self.wag = WagProperty()
        self.voidage = VoidageProperty()
        self.inj_potentials = InjectionPotentialProperty(hierarchy_type=ID_PLATFORM)

        # hidden properties
        self.inj_fluids = InjectionFluidProperty(hierarchy_type=ID_POLYGON, use_self=False)


def Sum(x):
    if not x.size:
        return None

    return np.sum(x)


def Average(x, w=None, sumw=None):
    if not x.size:
        return None

    if w is None:
        return np.sum(x) / x.size
    else:
        return WeightedAverage(x, w, sumw)


def WeightedAverage(x, w, sumw=None):
    return np.sum(x * w) / (sumw if sumw is not None else np.sum(w))



