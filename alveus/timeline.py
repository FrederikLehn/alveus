import math
import numpy as np

from _ids import ID_YEARLY, ID_QUARTERLY, ID_MONTHLY, ID_DELTA

_DAYS_IN_MONTH = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
_MONTHS_IN_QUARTER = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}


def sample_dateline(start, end, frequency, delta=30.):
    return start + sample_timeline(start, end, frequency, delta=delta).astype(np.uint64)


def sample_timeline(start, end, frequency, delta=30.):

    if frequency == ID_DELTA:
        return np.cumsum(np.insert(_sample_delta(start, end, delta), 0, 0.))

    # if sampling is date dependent (monthly, quarterly, yearly), ensure dates returned at the first of the month.
    # handle situations where start > 01-xx-xxxx.
    days = _days_from_date(start).astype(np.float64)
    d_start = _days_in_month(_year_from_date(start), _month_from_date(start)) - days + 1.
    _start = start + np.timedelta64(int(d_start), 'D')

    # sample timeline
    if frequency == ID_YEARLY:

        time = _sample_yearly(_start, end)

    elif frequency == ID_QUARTERLY:

        time = _sample_quarterly(_start, end)

    elif frequency == ID_MONTHLY:

        time = _sample_monthly(_start, end)

    else:

        return

    # insert zero into timeline to start at provided start date:
    time = np.insert(time, 0, 0.)

    # if start != _start, insert difference between them:
    if start != _start:
        time = np.insert(time, 1, d_start)

    # if cum_time[-1] != (end - start), insert difference between them:
    cum_time = np.cumsum(time)
    duration = np.array(end - start, dtype=np.float64)

    if cum_time[-1] < duration:
        cum_time = np.insert(cum_time, cum_time.size, duration)

    return cum_time


def _sample_delta(start, end, delta):
    days = (end - start) / np.timedelta64(1, 'D')
    return np.arange(delta, days, delta)


def _sample_monthly(start, end):
    year_end = _year_from_date(end)
    month_end = _month_from_date(end)

    time = []
    year = _year_from_date(start)
    month = _month_from_date(start)

    while year < year_end or month < month_end:
        time.append(_days_in_month(year, month))

        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

    return np.array(time, dtype=np.float32)


def _sample_quarterly(start, end):
    year_end = _year_from_date(end)
    quarter_end = _quarter_from_date(end)

    time = []
    year = _year_from_date(start)
    quarter = _quarter_from_date(start)

    while year < year_end or quarter < quarter_end:
        time.append(_days_in_quarter(year, quarter))

        if quarter == 4:
            quarter = 1
            year += 1
        else:
            quarter += 1

    return np.array(time, dtype=np.float32)


def _sample_yearly(start, end):
    year_end = _year_from_date(end)

    time = []
    year = start.astype('datetime64[Y]').astype(int) + 1970

    while year < year_end:
        time.append(_days_in_year(year))
        year += 1

    return np.array(time, dtype=np.float32)


def _year_from_date(date):
    return date.astype('datetime64[Y]').astype(int) + 1970


def _quarter_from_date(date):
    return int(math.ceil((date.astype('datetime64[M]').astype(float) % 12 + 1) / 4.))


def _month_from_date(date):
    return date.astype('datetime64[M]').astype(int) % 12 + 1


def _days_from_date(date):
    return date - date.astype('datetime64[M]') + 1


def _is_leap_year(year):
    return ((not year % 4) and (year % 100)) or (not year % 400)


def _days_in_month(year, month):
    days = float(_DAYS_IN_MONTH[month])
    if month == 2 and _is_leap_year(year):
        days += 1

    return days


def _days_in_quarter(year, quarter):
    days = 0.
    for month in _MONTHS_IN_QUARTER[quarter]:
        days += _days_in_month(year, month)

    return days


def _days_in_year(year):
    return 365. + (1. if _is_leap_year(year) else 0.)


# ======================================================================================================================
# Auxiliary methods
# ======================================================================================================================
def extract_dates(profiles):
    start = np.datetime64(np.iinfo(np.int64).max, 'D')
    end = np.datetime64(np.iinfo(np.int64).min + 1, 'D')

    for p in profiles:
        if p.dates[0] < start:
            start = p.dates[0]

        if p.dates[-1] > end:
            end = p.dates[-1]

    return start, end


def ExtractDates(profiles):
    """
    Front-end wrapper to extract_dates
    :param profiles:
    :return:
    """
    return extract_dates(profiles)


def merge_datelines(datelines):
    dateline = np.array([], dtype='datetime64[D]')
    for dl in datelines:
        dateline = np.unique(np.concatenate((dateline, dl), 0))

    dateline.sort()
    return dateline


def MergeDatelines(datelines):
    """
    Front-end wrapper to merge_datelines
    :param datelines:
    :return:
    """
    return merge_datelines(datelines)

