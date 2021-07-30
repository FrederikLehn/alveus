import numpy as np


def _calculate_along(n, x=None, dx=1.):
    if x is None:
        x = np.arange(0., n * dx, dx)

    return x


def forward_integration(y, x=None, dx=1., initial=0.):
    x = _calculate_along(y.size, x, dx)
    return np.cumsum(np.insert(y[:-1] * (x[1:] - x[:-1]), 0, initial))


def backward_integration(y, x=None, dx=1., final=0.):
    x = _calculate_along(y.size, x, dx)
    return np.cumsum(np.insert(y[1:] * (x[1:] - x[:-1]), y.size - 1, final))


def trapezoidal_integration(y, x=None, dx=1., initial=0.):
    x = _calculate_along(y.size, x, dx)
    return np.cumsum(np.insert((y[:-1] + y[1:]) / 2. * (x[1:] - x[:-1]), 0, initial))


def forward_difference(y, x=None, dx=1.):
    """
    1st order forward differencing scheme, using backwards differencing at the boundary value.
    Parameters
    ----------
    y : array_like
        Array of function values to differentiate.
    x : array_like
        Array of x-values for which to differentiate w.r.t.
    dx : float
        Step used to create `x` if not provided
    """
    x = _calculate_along(y.size, x, dx)
    return np.insert((y[1:] - y[:-1]) / (x[1:] - y[:-1]), 0, (y[1] - y[0]) / (x[1] - x[0]))


def backward_difference(y, x=None, dx=1.):
    """
    1st order back differencing scheme, using forward differencing at the boundary value.
    Parameters
    ----------
    y : array_like
        Array of function values to differentiate.
    x : array_like
        Array of x-values for which to differentiate w.r.t.
    dx : float
        Step used to create `x` if not provided
    """
    x = _calculate_along(y.size, x, dx)
    return np.insert((y[:-1] - y[1:]) / (x[:-1] - x[1:]), y.size - 1, (y[-1] - y[-2]) / (x[-1] - x[-2]))


def central_difference(y, x=None, dx=1.):
    """
    1st order central differencing scheme, using forward/backwards differencing at the boundary values.
    Parameters
    ----------
    y : array_like
        Array of function values to differentiate.
    x : array_like
        Array of x-values for which to differentiate w.r.t.
    dx : float
        Step used to create `x` if not provided
    """
    x = _calculate_along(y.size, x, dx)
    return np.insert(np.insert((y[1:-1] - y[:-2]) / (x[1:-1] - y[:-2]), 0, (y[1] - y[0]) / (x[1] - x[0])),
                     y.size - 1, (y[-1] - y[-2]) / (x[-1] - x[-2]))


def central_difference_2nd(y, x=None, dx=1.):
    """
    2nd order central differencing scheme, using 1st order forward/backwards differencing at the boundary values.
    Parameters
    ----------
    y : array_like
        Array of function values to differentiate.
    x : array_like
        Array of x-values for which to differentiate w.r.t.
    dx : float
        Step used to create `x` if not provided
    """
    x = _calculate_along(y.size, x, dx)
    hd = x[2:] - x[1:-1]
    hs = x[1:-1] - x[:-2]
    hd2 = hd ** 2.
    hs2 = hs ** 2.
    yd = y[2:]
    ys = y[:-2]

    dy = (hs2 * yd + (hd2 - hs2) * y[1:-1] - hd2 * ys) / (hs * hd * (hd + hs))

    return np.insert(np.insert(dy, 0, (y[1] - y[0]) / (x[1] - x[0])), y.size - 1, (y[-1] - y[-2]) / (x[-1] - x[-2]))