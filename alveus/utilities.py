import inspect
import math
import datetime
import wx

# -------------------------------------------------------------------------------------------------------------------- #

def ArgSort(seq):
    return sorted(range(len(seq)), key=seq.__getitem__)


# -------------------------------------------------------------------------------------------------------------------- #

def pydate2wxdate(date):
    """
    Transforms a `datetime.date` object into a `wx.DateTime` one.

    :param date: a `datetime.date` object.
    """

    tt = date.timetuple()
    dmy = (tt[2], tt[1]-1, tt[0])
    return wx.DateTime.FromDMY(*dmy)


# -------------------------------------------------------------------------------------------------------------------- #

def wxdate2pydate(date):
    """
   Transforms a `wx.DateTime` object into a `datetime.date` one.

    :param date: a `wx.DateTime` object.
    """

    if date.IsValid():
        ymd = map(int, date.FormatISODate().split('-'))
        return datetime.date(*ymd)
    else:
        return None


# -------------------------------------------------------------------------------------------------------------------- #

def GetAttributes(class_, exclude=(), name_only=False, attr_only=False, sort=False):
    if sort:
        # TODO: Potentially this can be the only method, removing inspect.getmembers
        attr = zip(list(class_.__dict__.keys()), list(class_.__dict__.values()))
    else:
        # getmembers returns a generator of tuples ((attribute_name, attribute_value), ...)
        attr = inspect.getmembers(class_, lambda a: not (inspect.isroutine(a)))

    decl = (a for a in attr if not (a[0].startswith('__') and a[0].endswith('__')) and not (a[0] in exclude))

    if name_only:
        return (a[0] for a in decl)
    elif attr_only:
        return (a[1] for a in decl)
    else:
        return decl


# -------------------------------------------------------------------------------------------------------------------- #

def Latex2HTML(text):
    # returns text and False if no changes made, True if changes made
    sup = text.find('^{')
    sub = text.find('_{')
    greek = text.find(r'\\')
    if sup == -1 and sub == -1 and greek == -1:
        return text, False

    while True:

        sup = text.find('^{'); sup = sup if sup > -1 else math.inf
        sub = text.find('_{'); sub = sub if sub > -1 else math.inf
        greek = text.find(r'\\'); greek = greek if greek > -1 else math.inf

        # use first occurrence
        used = min(sup, sub, greek)

        if used == math.inf:
            break

        if used == sup:
            text = text.replace('^{', '<sup>', 1)
            text = text.replace('}', '</sup>', 1)

        elif used == sub:
            text = text.replace('_{', '<sub>', 1)
            text = text.replace('}', '</sub>', 1)

        else:
            text = text.replace(r'\\', '<', 1)
            end = text.find(' ', used)
            text = text[:end] + '/>' + text[(end+2):]

    return text, True


# -------------------------------------------------------------------------------------------------------------------- #

def return_property(property_, default=None):
    return property_ if property_ is not None else default


def ReturnProperty(property_, default=None):
    # front-end wrapper for return_property
    return return_property(property_, default=default)


def return_properties(properties, defaults=()):
    return [return_property(property_, default) for property_, default in zip(properties, defaults)]


def ReturnProperties(properties, defaults=()):
    # front-end wrapper for return_properties
    return return_properties(properties, defaults=defaults)
