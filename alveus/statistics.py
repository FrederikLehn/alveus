import math
import numpy as np


# ======================================================================================================================
# Cumulative Inverse Tranforms
# ======================================================================================================================
def stnormal2swanson(x, a, c, b):
    # a = min, c = mode, b = max
    u = stnormal2stuniform(x)
    return np.where(u < 0.3, a, np.where(0.3 <= u < 0.7, c, b))


def stnormal2triangular(x, a, c, b):
    # a = min, c = mode, b = max
    u = stnormal2stuniform(x)
    f = np.where(b > a, (c - a) / (b - a), 0.)
    return np.where(u < f, a + np.sqrt(u * (b - a) * (c - a)), b - np.sqrt((1. - u) * (b - a) * (b - c)))


def stnormal2lognormal(x, m, v):
    # m = mean, v = variance
    m2 = m ** 2.
    mu = math.log(m2 / (math.sqrt(v + m2)))
    sigma = math.sqrt(math.log(1. + v / m2))
    return np.exp(stnormal2normal(x, mu, sigma))


def stnormal2uniform(x, a, b):
    # a = min, b = max
    return a + (b - a) * stnormal2stuniform(x)


def stnormal2normal(x, mu, sigma):
    return mu + x * sigma


def stnormal2stuniform(x):
    # standard normal distribution to standard uniform in (0, 1)
    return .5 * (1. + erf(x / math.sqrt(2.)))


# from https://stackoverflow.com/questions/457408/is-there-an-easily-available-implementation-of-erf-for-python
# answer by John D. Cook
def erf(x):
    # save the sign of x
    sign = np.where(x >= 0., 1., -1.)
    x_ = abs(x)

    # constants
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    # A&S formula 7.1.26
    t = 1.0 / (1.0 + p * x_)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * np.exp(-x_ ** 2.)
    return sign * y


# ======================================================================================================================
# Ensemble/Realization statical functions
# ======================================================================================================================
def percentileofscore(a, score, kind='rank'):
    """
    DISCLAIMER: Taken directly from the Scipy implementation of the similarly named function:
    https://github.com/scipy/scipy/blob/master/scipy/stats/stats.py#L1832 (line 1832), on 09-04-2020

    Compute the percentile rank of a score relative to a list of scores.
    A `percentileofscore` of, for example, 80% means that 80% of the
    scores in `a` are below the given score. In the case of gaps or
    ties, the exact definition depends on the optional keyword, `kind`.
    Parameters
    ----------
    a : array_like
        Array of scores to which `score` is compared.
    score : int or float
        Score that is compared to the elements in `a`.
    kind : {'rank', 'weak', 'strict', 'mean'}, optional
        Specifies the interpretation of the resulting score.
        The following options are available (default is 'rank'):
          * 'rank': Average percentage ranking of score.  In case of multiple
            matches, average the percentage rankings of all matching scores.
          * 'weak': This kind corresponds to the definition of a cumulative
            distribution function.  A percentileofscore of 80% means that 80%
            of values are less than or equal to the provided score.
          * 'strict': Similar to "weak", except that only values that are
            strictly less than the given score are counted.
          * 'mean': The average of the "weak" and "strict" scores, often used
            in testing.  See https://en.wikipedia.org/wiki/Percentile_rank
    Returns
    -------
    pcos : float
        Percentile-position of score (0-100) relative to `a`.
    See Also
    --------
    numpy.percentile
    Examples
    --------
    Three-quarters of the given values lie below a given score:
    >>> from scipy import stats
    >>> percentileofscore([1, 2, 3, 4], 3)
    75.0
    With multiple matches, note how the scores of the two matches, 0.6
    and 0.8 respectively, are averaged:
    >>> percentileofscore([1, 2, 3, 3, 4], 3)
    70.0
    Only 2/5 values are strictly less than 3:
    >>> percentileofscore([1, 2, 3, 3, 4], 3, kind='strict')
    40.0
    But 4/5 values are less than or equal to 3:
    >>> percentileofscore([1, 2, 3, 3, 4], 3, kind='weak')
    80.0
    The average between the weak and the strict scores is:
    >>> percentileofscore([1, 2, 3, 3, 4], 3, kind='mean')
    60.0
    """
    if np.isnan(score):
        return np.nan
    a = np.asarray(a)
    n = len(a)
    if n == 0:
        return 100.0

    if kind == 'rank':
        left = np.count_nonzero(a < score)
        right = np.count_nonzero(a <= score)
        pct = (right + left + (1 if right > left else 0)) * 50.0 / n
        return pct
    elif kind == 'strict':
        return np.count_nonzero(a < score) / n * 100
    elif kind == 'weak':
        return np.count_nonzero(a <= score) / n * 100
    elif kind == 'mean':
        pct = (np.count_nonzero(a < score) + np.count_nonzero(a <= score)) / n * 50
        return pct
    else:
        raise ValueError("kind can only be 'rank', 'strict', 'weak' or 'mean'")


# -------------------------------------------------------------------------------------------------------------------- #

def extract_realizations(ensemble, ids, weights, percentiles):
    """
    Extracts statistically representative profiles from an ensemble production profiles based on pre-calculated
    summary values
    Parameters
    ----------
    ensemble: list
        List of dictionary containing summary values [{id_: value} for id_ in ensemble]
    ids: list
        List of keys to the ensemble, for which to base the extraction on
    weights: array_like
        List of weights used to prioritize certain values
    percentiles : list
        List of percentile values, such as 10.0 for P10, 50.0 for P50, etc.
    """

    # preparation
    n = len(ensemble)
    m = len(ids)

    # calculate all values of the various variables based on the functions
    values = np.zeros((n, m))

    for i, realization in enumerate(ensemble):
        for j, id_ in enumerate(ids):
            values[i, j] = realization[id_]

    # calculate the percentile score of each profile
    scores = np.zeros((n, m))

    for i in range(n):
        scores[i, :] = np.asarray([percentileofscore(values[:, j], values[i, j]) for j in range(m)], dtype=np.float64)

    # find the index of the best suited representative profile of each percentile
    return [min(range(n), key=lambda i: sum((scores[i, :] - p) ** 2. * weights)) for p in percentiles]


def ExtractRealizations(ensemble, ids, weights, percentiles):
    # Front-end wrapper to extract_realizations
    return extract_realizations(ensemble, ids, weights, percentiles)


# -------------------------------------------------------------------------------------------------------------------- #

def ensemble_distribution(ensemble, variable, percentiles):
    """
    Calculates the ensemble percentiles for a given ensemble at each time-step
    Parameters
    ----------
    ensemble : list
        List of class Profile()
    variable : str
        Variable id passed to each realization in the ensemble
    percentiles: list
         List of percentiles values, such as 10.0 for P10, 50.0 for P50, etc.
    """
    dateline = ensemble[0].dates
    n = len(dateline)
    m = len(ensemble)
    p = len(percentiles)

    array = np.zeros((n, m))
    for i, realization in enumerate(ensemble):
        array[:, i] = realization.Get(variable)

    distribution = np.zeros((n, p))
    for i in range(n):
        distribution[i, :] = np.percentile(array[i, :], percentiles, overwrite_input=True)

    return distribution


def EnsembleDistribution(ensemble, variable, percentiles):
    # Front-end wrapper to ensemble_distribution
    return ensemble_distribution(ensemble, variable, percentiles)


# ======================================================================================================================
# Experimental Designs
# ======================================================================================================================
