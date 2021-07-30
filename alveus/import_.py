import datetime
import numpy as np
import xlrd

from profile_ import Profile


def FromExcel(items, path, sheet_name, first_row=1):

    workbook = xlrd.open_workbook(path)
    sheet = workbook.sheet_by_name(sheet_name)

    variables = {id_: [] for (id_, _, _) in items}

    for row in range(first_row - 1, sheet.nrows):
        # first item is dates

        cell = sheet.cell(row, items[0][2])
        variables[items[0][0]].append(datetime.datetime(*xlrd.xldate_as_tuple(cell.value, workbook.datemode)))

        # remaining items are numbers
        for id_, unit, column in items[1:]:
            cell = sheet.cell(row, column).value
            if cell == '':
                cell = 0.0

            value = ConvertUnit(float(cell), unit)
            variables[id_].append(value)

    return GetProfile(variables)


def GetProfile(variables):
    dates = np.array(variables['date'], dtype='datetime64[D]')
    times = np.concatenate((np.array([0.], dtype=np.float64), np.cumsum(dates[1:] - dates[:-1]).astype(np.float64)))

    uptimes = np.ones((times.size, 4))

    try:
        uptimes[:, 0] = np.array(variables['production_uptime'], dtype=np.float64)
        for i in range(0, times.size):
            uptimes[i, 0] /= variables['date'][i].day
    except KeyError:
        pass

    try:
        uptimes[:, 1] = np.array(variables['lift_gas_uptime'], dtype=np.float64)
        for i in range(0, times.size):
            uptimes[i, 1] /= variables['date'][i].day
    except KeyError:
        pass

    try:
        uptimes[:, 2] = np.array(variables['gas_injection_uptime'], dtype=np.float64)
        for i in range(0, times.size):
            uptimes[i, 2] /= variables['date'][i].day
    except KeyError:
        pass

    try:
        uptimes[:, 3] = np.array(variables['water_injection_uptime'], dtype=np.float64)
        for i in range(0, times.size):
            uptimes[i, 3] /= variables['date'][i].day
    except KeyError:
        pass

    values = np.zeros((dates.size, 6))

    try:
        values[:, 0] = np.array(variables['oil_potential'], dtype=np.float64)
    except KeyError:
        pass

    try:
        values[:, 1] = np.array(variables['total_gas_potential'], dtype=np.float64)
    except KeyError:
        pass

    try:
        values[:, 2] = np.array(variables['water_potential'], dtype=np.float64)
    except KeyError:
        pass

    try:
        values[:, 3] = np.array(variables['lift_gas_potential'], dtype=np.float64)
    except KeyError:
        pass

    try:
        values[:, 4] = np.array(variables['gas_injection_potential'], dtype=np.float64)
    except KeyError:
        pass

    try:
        values[:, 5] = np.array(variables['water_injection_potential'], dtype=np.float64)
    except KeyError:
        pass

    profile = Profile()
    profile.dates = dates
    profile.times = times
    profile.uptimes = uptimes
    profile.values = values

    return profile


def ConvertUnit(value, unit):
    if unit == 'stb/day':
        return value / 1e3
    elif unit == 'Mstb/day':
        return value
    elif unit == 'Mscf/day':
        return value / 1e3
    elif unit == 'MMscf/day':
        return value
    elif unit == '%':
        return value / 100.
    else:
        return value


class SimulationResults:
    def __init__(self, RSM_KW):
        # Initialize the class with a dictionary of Eclipse SUMMARY keywords
        self.time = []
        self.keywords = {kw: list([]) for kw in RSM_KW}

    def add_time(self, t):
        self.time.append(float(t))

    def add_value(self, kw, value):
        # Append value to the relevant keyword
        self.keywords[kw].append(float(value))


def read_rsm(RSM_KW, file_name):

    runsum = SimulationResults(RSM_KW)

    # Open the file in read-only mode
    f = open(file_name, 'r')

    # Loop through all the lines in the file
    kws = []
    cols = []
    load_time = True
    for i, line in enumerate(f):

        # '1' without a prefixed space is the delimiter splitting tables, reset keywords reading
        if line.startswith('1'):
            kws = []
            cols = []
            if i > 0:
                load_time = False

            continue

        # skip header rows
        if line.startswith(' -') or line.startswith(' SUMMARY'):
            continue

        # Indicates a line containing keywords, check if any are relevant and save column indices
        if line.startswith(' TIME'):
            # Split the line using blank space as delimiter
            split_line = line.split()

            for j, kw in enumerate(split_line):
                if kw in RSM_KW:
                    kws.append(kw)
                    cols.append(j)

            continue

        # skip header rows
        if line.startswith(' DAYS') or line.startswith(12*' '):
            continue

        # Read the columns which were identified as relevant keywords previously
        if not kws:
            continue
        else:
            # Split the line using blank space as delimiter
            split_line = line.split()
            count = 0
            for j, value in enumerate(split_line):
                if j == 0 and load_time:
                    runsum.add_time(value)

                if j in cols:
                    runsum.add_value(kws[count], value)
                    count += 1

    f.close()
    return runsum
