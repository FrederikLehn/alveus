import copy
import numpy as np

from _errors import ConvergenceError
from _ids import *
from utilities import return_property
from optimize import nl_lsq, secant


# ======================================================================================================================
# Available functions and Jacobians
# ======================================================================================================================
# History functions ----------------------------------------------------------------------------------------------------
def history(x, x_d, y_d):
    return np.interp(x, x_d, y_d)


def mav_fun(x, x_d, y_d):
    return np.interp(x, x_d, y_d)


def moving_average(y, n=1):
    n = int(n)
    ma = np.convolve(y, np.ones((n,))/n, mode='valid')
    return np.append(y[:(n-1)], ma)


# Standard curve-fit functions -----------------------------------------------------------------------------------------
def con_fun(x, c):
    return np.repeat(c, x.size)


def exp_fun2(x, a, b):
    return b * np.exp(-a * x)


def exp_fun3(x, a, b, c):
    return b * np.exp(-a * x) + c


def exp_fun2_jacobian(x, a, b):
    return np.array([-b * x * np.exp(-a * x), np.exp(-a * x)]).T


def exp_fun3_jacobian(x, a, b, c):
    return np.array([-b * x * np.exp(-a * x), np.exp(-a * x), np.repeat(1., x.size)]).T


def lin_fun(x, a, b):
    return a * x + b


def lin_fun_jacobian(x, a, b):
    return np.array([x, np.repeat(1., x.size)]).T


def log_fun(x, a, b):
    return np.where(x > 0.0, a * np.log(x) + b, b)


def log_fun_jacobian(x, a, b):
    return np.array([np.where(x > 0.0, np.log(x), 0.), np.repeat(1., x.size)]).T


def pow_fun2(x, a, b):
    return np.where(x > 0.0, b * x ** a, 0.)


def pow_fun3(x, a, b, c):
    return np.where(x > 0.0, b * x ** a + c, c)


def pow_fun2_jacobian(x, a, b):
    return np.array([np.where(x > 0.0, b * x ** a * np.log(x), 0.0), np.where(x > 0.0, x ** a, 0.0)]).T


def pow_fun3_jacobian(x, a, b, c):
    return np.array([np.where(x > 0.0, b * x ** a * np.log(x), 0.0), np.where(x > 0.0, x ** a, 0.0), np.repeat(1., x.size)]).T


# Decline Curve Analysis functions -------------------------------------------------------------------------------------
# based on: http://www.fekete.com/SAN/WebHelp/FeketeHarmony/Harmony_WebHelp/Content/HTML_Files/Reference_Material/Analysis_Method_Theory/Traditional_Decline_Theory.htm
def exp_decline_rate_cum(q, q_i, d_i):
    # exponential decline for rate vs cum. Note: 1. - to transform from water-cut to oil-cut
    return 1. - (q_i - q * d_i)


def exp_decline_rate_cum_jacobian(q, q_i, d_i):
    # Note: - to transform from water-cut to oil-cut
    return - np.array([np.repeat(1., q.size), -q]).T


def exp_decline_rate_time(t, q_i, d_i):
    # exponential decline for rate vs cum. Note: 1. - to transform from water-cut to oil-cut
    return q_i * np.exp(-d_i * t)


def exp_decline_rate_time_jacobian(t, q_i, d_i):
    return np.array([np.exp(-d_i * t), - q_i * t * np.exp(-d_i * t)]).T


def har_decline_rate_cum(q, q_i, d_i):
    # harmonic decline for rate vs cum. Note: 1. - to transform from water-cut to oil-cut
    return 1. - (q_i * np.exp(-q * d_i / q_i))


def har_decline_rate_cum_jacobian(q, q_i, d_i):
    # Note: - to transform from water-cut to oil-cut
    return - np.array([np.exp(-q * d_i / q_i) + q * d_i * np.exp(-q * d_i / q_i) / q_i, -q * np.exp(-q * d_i / q_i)]).T


def har_decline_rate_time(t, q_i, d_i):
    # harmonic decline for rate vs cum
    return q_i / (1. + d_i * t)


def har_decline_rate_time_jacobian(t, q_i, d_i):
    return np.array([1. / (1. + d_i * t), -q_i * t / (1. + d_i * t) ** 2.]).T


def hyp_decline_rate_cum(q, q_i, d_i, b):
    # hyperbolic decline for rate vs cum. Note: 1. - to transform from water-cut to oil-cut
    # due to the formulation of the hyperbolic function, it is actually a rebounding curve. This is not allowed.
    q_1_b = q_i ** (1. - b) - (q * d_i * (1. - b)) / (q_i ** b)
    return 1. - np.where(q_1_b > 0., q_1_b ** (1. / (1. - b)), 0.)


def hyp_decline_rate_cum_jacobian(q, q_i, d_i, b):
    # Note: - to transform from water-cut to oil-cut
    return - np.array([((1. - b) * b * d_i * q * q_i ** (-b - 1.) + (1. - b) * q_i ** (-b)) * (q_i ** (1. - b) - (1. - b) * d_i * q * q_i ** (-b)) ** (1. / (1. - b) - 1.) / (1. - b),
                     q * (-q_i ** (-b)) * (q_i ** (1. - b) - (1. - b) * d_i * q * q_i ** (-b)) ** (1. / (1. - b) - 1.)]).T


def hyp_decline_rate_time(t, q_i, d_i, b):
    # hyperbolic decline for rate vs cum
    return q_i / (1. + b * d_i * t) ** (1. / b)


def hyp_decline_rate_time_jacobian(t, q_i, d_i, b):
    # hyperbolic decline for rate vs cum
    return np.array([1. / (1. + b * d_i * t) ** (1. / b), -q_i * t * (1. + b * d_i * t) ** ((-1. - b) / b)]).T


# Non-parametric functions ---------------------------------------------------------------------------------------------
def bow_wave(x, x0, xm, y0, d_y0):
    """
    The bow wave function uses the "exit velocity" of the previous function and creates a rebounding curve, a so called
    bow wave.
    # Parameters
    :param x:
    :param x0:
    :param xm:
    :param y0:
    :param d_y0:
    :return:
    """
    return y0 + d_y0 * (1. - (x - x0) / (xm - x0)) * (x - x0)


# ======================================================================================================================
# Available functions (classes)
# ======================================================================================================================
class Fit:
    # designed to be subclassed
    def __init__(self, input_=None):
        self.input = input_    # input (provided parameters)
        self.parameters = []   # classical parameters (fitted)
        self.args = []         # hidden parameters (such as when x and y data are required)

        self.min_data = 0      # minimum number of required data points for optimization

    def error_check(self, x):
        if x.size < self.min_data:
            raise ValueError('Number of selected data points ({}) is less than the minimum '
                             'number of required data points ({})'.format(x.size, self.min_data))

    def optimize(self, x, y):
        self.error_check(x)
        parameters = self.solve(x, y)
        self.parameters = list(parameters)

    def solve(self, x, y):
        # sub-class
        return []


# History functions ----------------------------------------------------------------------------------------------------
class HistoryFit(Fit):
    def __init__(self):
        super().__init__()

    def eval(self, x):
        return history(x, *self.args)

    def optimize(self, x, y):
        self.args = (x, y)


class MovingAverageFit(Fit):
    def __init__(self, input_):
        super().__init__(input_)

    def eval(self, x):
        return mav_fun(x, *self.args)

    def optimize(self, x, y):
        self.input = return_property(self.input, default=1)
        self.args = (x, moving_average(y, self.input))


# Standard curve-fit functions -----------------------------------------------------------------------------------------
class ConstantFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 1

    def eval(self, x):
        return con_fun(x, *self.parameters)

    def solve(self, x, y):
        return [np.mean(y)]


class ExponentialFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 2

    def eval(self, x):
        return exp_fun3(x, *self.parameters)

    def solve(self, x, y):
        if x.size == 2:
            p0 = np.array([.01, y[0]])
            p = nl_lsq(exp_fun2, x, y, p0, jac=exp_fun2_jacobian)
            p = np.append(p, 0.)

        else:
            p0 = np.array([.01, y[0], 0.1])
            p = nl_lsq(exp_fun3, x, y, p0, jac=exp_fun3_jacobian)

        return p


class LinearFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 2

    def eval(self, x):
        return lin_fun(x, *self.parameters)

    def solve(self, x, y):
        p0 = np.array([(y[-1] - y[0]) / (x[-1] - x[0]), y[0]])
        return nl_lsq(lin_fun, x, y, p0, jac=lin_fun_jacobian)


class LogarithmicFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 2

    def eval(self, x):
        return log_fun(x, *self.parameters)

    def solve(self, x, y):
        return nl_lsq(log_fun, x, y, np.array([.0, y[0]]), jac=log_fun_jacobian)


class PowerFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 2

    def eval(self, x):
        return pow_fun3(x, *self.parameters)

    def solve(self, x, y):
        if x.size == 2:
            p0 = np.array([.1, y[-1]])
            p = nl_lsq(pow_fun2, x, y, p0, jac=pow_fun2_jacobian)
            p = np.append(p, 0.)

        else:
            p0 = np.array([.1, y[-1], 0.])
            p = nl_lsq(pow_fun3, x, y, p0, jac=pow_fun3_jacobian)

        return p


# Decline Curve Analysis functions -------------------------------------------------------------------------------------
class ExponentialDeclineCumFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 2

    def eval(self, x):
        return exp_decline_rate_cum(x, *self.parameters)

    def solve(self, x, y):
        return nl_lsq(exp_decline_rate_cum, x, y, np.array([1. - y[0], 0.01]), jac=exp_decline_rate_cum_jacobian)


class HarmonicDeclineCumFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 2

    def eval(self, x):
        return har_decline_rate_cum(x, *self.parameters)

    def solve(self, x, y):
        return nl_lsq(har_decline_rate_cum, x, y, np.array([1. - y[0], 0.01]), jac=har_decline_rate_cum_jacobian)


class HyperbolicDeclineCumFit(Fit):
    def __init__(self, input_):
        super().__init__(input_)

        self.min_data = 2

    def eval(self, x):
        return hyp_decline_rate_cum(x, *self.parameters, self.input)

    def solve(self, x, y):
        self.input = return_property(self.input, default=0.5)
        return nl_lsq(hyp_decline_rate_cum, x, y, np.array([1. - y[0], 0.01]), jac=hyp_decline_rate_cum_jacobian, args=(self.input,))


class ExponentialDeclineTimeFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 2

    def eval(self, x):
        return exp_decline_rate_time(x, *self.parameters)

    def solve(self, x, y):
        return nl_lsq(exp_decline_rate_time, x, y, np.array([y[0], 0.001]), jac=exp_decline_rate_time_jacobian)


class HarmonicDeclineTimeFit(Fit):
    def __init__(self):
        super().__init__()

        self.min_data = 2

    def eval(self, x):
        return har_decline_rate_time(x, *self.parameters)

    def solve(self, x, y):
        return nl_lsq(har_decline_rate_time, x, y, np.array([y[0], 0.001]), jac=har_decline_rate_time_jacobian)


class HyperbolicDeclineTimeFit(Fit):
    def __init__(self, input_):
        super().__init__(input_)

        self.min_data = 2

    def eval(self, x):
        return hyp_decline_rate_time(x, *self.parameters, self.input)

    def solve(self, x, y):
        self.input = return_property(self.input, default=0.5)
        return nl_lsq(hyp_decline_rate_time, x, y, np.array([y[0], 0.001]), jac=hyp_decline_rate_time_jacobian, args=(self.input,))


# Non-parametric functions ---------------------------------------------------------------------------------------------
class BowWaveFit(Fit):
    def __init__(self, input_):
        super().__init__(input_)

    def eval(self, x):
        return bow_wave(x, *self.args)

    def initialize(self, f, x0, xn):
        """
        :param f: The function from which to calculate "exit velocity"
        :param x0: The point at which the previous merge merge happened happen
        :param xn: The point at which the bow wave function merges with the next function
        :return:
        """
        xm = (1. - self.input) * x0 + self.input * xn
        y0 = f(x0)
        d_y0 = (y0 - f(x0 * 0.99)) / (0.01 * x0)
        self.args = (x0, xm, y0, d_y0)


# ======================================================================================================================
# Function groups
# ======================================================================================================================
class ModelFit:
    def __init__(self, x, y):
        self._x = x
        self._y = y

        self.method = None
        self.fit = None
        self._values = [np.empty(0), np.empty(0)]

        self.is_parametric = True

    # front-end methods ------------------------------------------------------------------------------------------------
    def ConvertValues(self, start_date):
        self._values[0] = start_date + self._values[0].astype(np.uint64)

    def GetFit(self):
        return self.fit

    def GetInput(self):
        return self.fit.input

    def GetMethod(self):
        return self.method

    def GetMinData(self):
        return self.fit.min_data

    def GetParameters(self):
        return self.fit.parameters

    def GetValues(self):
        return self._values

    def IsParametric(self):
        return self.is_parametric

    def Set(self, method, input_, parameters):
        if method is None:
            return

        # in case of a provided model, not a fitted one
        self.method = method

        if self.fit is None:
            self.fit = self.allocate_fit(method, input_)

        self.fit.input = input_
        self.fit.parameters = list(parameters)

    # back-end methods -------------------------------------------------------------------------------------------------
    @staticmethod
    def allocate_fit(method, input_=None):
        # sub-class
        return None

    def calculate_values(self):

        if self._x.size > 1:
            x = np.linspace(self._x[0], self._x[-1], 100)

        elif self._x.size == 1:
            x = self._x

        else:
            return

        self._values = [x, self.eval(x)]

    def eval(self, x):
        try:
            return self.fit.eval(x)
        except TypeError:
            raise


class HistoryModelFit(ModelFit):
    def __init__(self, x, y):
        super().__init__(x, y)

    @staticmethod
    def allocate_fit(method, input_=None):
        if method == ID_HIS:
            fit = HistoryFit()

        elif method == ID_MAV:
            fit = MovingAverageFit(input_)

        else:
            fit = None

        return fit

    def find_fit(self, method, input_=None):
        self.method = method
        self.fit = self.allocate_fit(method, input_)
        self.fit.optimize(self._x, self._y)
        self.calculate_values()


class CurveModelFit(ModelFit):
    def __init__(self, x, y):
        super().__init__(x, y)

    @staticmethod
    def allocate_fit(method, input_=None):
        if method == ID_CON:
            fit = ConstantFit()

        elif method == ID_LIN:
            fit = LinearFit()

        elif method == ID_EXP:
            fit = ExponentialFit()

        elif method == ID_POW:
            fit = PowerFit()

        elif method == ID_LOG:
            fit = LogarithmicFit()

        else:
            fit = None

        return fit

    def find_best_fit(self):
        rms = [np.Inf, 0.]

        for method in range(0, ID_LOG):
            try:
                fit = self._find_fit(method)
            except ConvergenceError:
                continue

            rms[1] = self._calculate_rms(fit)

            if rms[1] < rms[0]:
                self.method = method
                self.fit = fit

            rms[0] = rms[1]

        self.calculate_values()

    def find_fit(self, method):
        self.method = method
        self.fit = self._find_fit(method)
        self.calculate_values()

    def _calculate_rms(self, fit):
        return np.sqrt(np.mean((self._y - fit.eval(self._x)) ** 2.))

    def _find_fit(self, method):
        fit = self.allocate_fit(method)
        fit.optimize(self._x, self._y)
        return fit


class DCACumModelFit(ModelFit):
    def __init__(self, x, y):
        super().__init__(x, y)

    @staticmethod
    def allocate_fit(method, input_=None):
        if method == ID_EXP_DCA:
            fit = ExponentialDeclineCumFit()

        elif method == ID_HAR_DCA:
            fit = HarmonicDeclineCumFit()

        elif method == ID_HYP_DCA:
            fit = HyperbolicDeclineCumFit(input_)

        else:
            fit = None

        return fit

    def find_fit(self, method, input_=None):
        self.method = method
        self.fit = self.allocate_fit(method, input_)
        self.fit.optimize(self._x, self._y)
        self.calculate_values()


class DCATimeModelFit(ModelFit):
    def __init__(self, x, y):
        super().__init__(x, y)

    @staticmethod
    def allocate_fit(method, input_=None):
        if method == ID_EXP_DCA:
            fit = ExponentialDeclineTimeFit()

        elif method == ID_HAR_DCA:
            fit = HarmonicDeclineTimeFit()

        elif method == ID_HYP_DCA:
            fit = HyperbolicDeclineTimeFit(input_)

        else:
            fit = None

        return fit

    def find_fit(self, method, input_=None):
        self.method = method
        self.fit = self.allocate_fit(method, input_)
        self.fit.optimize(self._x, self._y)
        self.calculate_values()


class NonParametricModelFit(ModelFit):
    def __init__(self, x, y):
        super().__init__(x, y)

        self.is_parametric = False

    @staticmethod
    def allocate_fit(method, input_=None):
        if method == ID_BOW:
            fit = BowWaveFit(input_)

        else:
            fit = None

        return fit


# ======================================================================================================================
# Merge functions
# ======================================================================================================================
class AssemblyFunction:
    def __init__(self):
        self._function = None
        self._offset = 0.

    # front-end functions (external) -----------------------------------------------------------------------------------
    def Add(self, model, merge_type, point, rate, multiplier, addition, args=()):
        if model.is_parametric:
            f = self._generate_function(model, multiplier, addition)
        else:
            f = self._generate_non_parametric_function(model, args)

        if merge_type == ID_SMOOTH:
            self._function = self._merge_function(f, point, rate)

        elif merge_type == ID_COND:
            # find x0 at which existing function reaches point (on y)
            try:
                x0 = secant(lambda x: self._function(x) - point, 0., 1.)
            except ConvergenceError:
                raise ConvergenceError('Unable to find conditional point equivalent on x-axis')
            except TypeError:
                raise  # missing parameters

            self._function = self._conditional_function(f, x0, point)

    def GetOffset(self):
        return self._offset

    def SetInitial(self, model, multiplier, addition):
        self._function = self._generate_function(model, multiplier, addition)

    def SetLimits(self, limits):
        # final function to be called
        f_exi = copy.deepcopy(self._function)
        self._function = lambda x: np.clip(f_exi(x), *limits)

    def SetOffset(self, offset):
        self._offset = offset

    # back-end functions (external) ------------------------------------------------------------------------------------
    def eval(self, x):
        return self._function(self._offset + x)

    # back-end functions (internal) ------------------------------------------------------------------------------------
    @staticmethod
    def _generate_function(model, multiplier, addition):
        return lambda x: model.eval(x) * multiplier + addition

    def _generate_non_parametric_function(self, model, args):
        if model.method == ID_BOW:
            fun = copy.deepcopy(self._function)
            model.fit.initialize(fun, *args)

        return lambda x: model.eval(x)

    # idea from: https://math.stackexchange.com/questions/45321/smooth-transition-between-two-lines-2d
    # (answer by Lubos Motl)
    # can become unstable if fun1 becomes too large at high x-values
    def _merge_function(self, f, p, k):
        f_exi = copy.deepcopy(self._function)
        return lambda x: f_exi(x) + (1. + np.tanh(k * (x - p))) / 2. * (f(x) - f_exi(x))

    def _conditional_function(self, f, x0, cond):
        f_exi = copy.deepcopy(self._function)
        return lambda x: np.where(f_exi(x) < cond, f_exi(x), f(x) + (f_exi(x0) - f(x0)))
