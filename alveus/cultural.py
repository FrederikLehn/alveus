import math
import numpy as np

ft_to_m = 0.3048


class Outline:
    def __init__(self):

        self.x = []
        self.y = []
        self.z = []  # used to translate plane in 3D windows

    def read_ascii(self, filepath):

        # Open the file in read-only mode
        f = open(filepath, 'r')

        for line in f:
            non_numeric = False
            split_line = line.split()

            # ensure all values on the line are digits
            for split in split_line:
                try:
                    float(split)
                except ValueError:
                    non_numeric = True

            if non_numeric:
                continue

            self.x.append(float(split_line[0]))
            self.y.append(float(split_line[1]))

            if len(split_line) == 3:
                self.z.append(float(split_line[2]))
            else:
                self.z.append(0.)

    def GetX(self):
        return np.array(self.x)

    def GetY(self):
        return np.array(self.y)
                
    def ReadASCII(self, filepath):
        # front-end wrapper to read_ascii
        self.read_ascii(filepath)


class WellPosition:
    def __init__(self):

        self.x = 0
        self.y = 0
        self.datum = 0

    def set_x(self, x):
        self.x = float(x)

    def set_y(self, y):
        self.y = float(y)

    def set_datum(self, datum):
        self.datum = float(datum)


class WellTrajectory(object):
    def __init__(self):

        self.name = ''

        # Initialize well position
        self.position = WellPosition()

        # Initialize string of generic information
        self.info = []

        # Initialize deviation survey
        self.MD = []
        self.x = []
        self.y = []
        self.z = []
        self.TVD = []
        self.dx = []
        self.dy = []
        self.azim_TN = []
        self.incl = []
        self.DLS = []
        self.azim_GN = []

    def GetX(self):
        return self.x

    def GetY(self):
        return self.y

    def GetZ(self):
        return self.z

    def add_info(self, info):
        self.info.append(info)

    def add_MD(self, MD):
        self.MD.append(float(MD))

    def add_x(self, x):
        self.x.append(float(x))

    def add_y(self, y):
        self.y.append(float(y))

    def add_z(self, z):
        self.z.append(float(z))

    def add_TVD(self, TVD):
        self.TVD.append(float(TVD))

    def add_dx(self, dx):
        self.dx.append(float(dx))

    def add_dy(self, dy):
        self.dy.append(float(dy))

    def add_azim_TN(self, azim_TN):
        self.azim_TN.append(float(azim_TN))

    def add_incl(self, incl):
        self.incl.append(float(incl))

    def add_DLS(self, DLS):
        self.DLS.append(float(DLS))

    def add_azim_GN(self, azim_GN):
        self.azim_GN.append(float(azim_GN))

    # ------------------------------------------------------------------------------------------------------------------
    # Methods for interpolating trajectories from existing wells
    # ------------------------------------------------------------------------------------------------------------------
    def infill_trajectory_x(self, x):
        self.x = x

    def infill_trajectory_xy(self, dev1, dev2, alpha):

        self.add_y(dev1.y[0])

        for i in range(1, len(dev1.x)):
            y1 = dev1.y[i]
            y2 = interpolate_trajectory_2d(dev2.x, dev2.y, dev1.x[i], dev1.y[i])
            y = y1 + alpha * (y2 - y1)

            self.add_y(y)

    def infill_trajectory_xz(self, dev1, dev2, alpha):

        self.add_z(dev1.z[0])

        for i in range(1, len(dev1.x)):
            z1 = dev1.z[i]
            z2 = interpolate_trajectory_2d(dev2.x, dev2.z, dev1.x[i], dev1.z[i])
            z = z1 + alpha * (z2 - z1)

            self.add_z(z)

    def calculate_MD(self):
        self.add_MD(0)
        for i in range(1, len(self.x)):
            self.add_MD(self.MD[i-1] + MD_increment([self.x[i-1], self.y[i-1], self.z[i-1]], [self.x[i], self.y[i], self.z[i]]))

    def extend_total_depth(self, TD_x, n=10):
        x_ext = linspace(self.x[-1], TD_x, n + 1)

        trajectory = (self.y[-1] - self.y[-2]) / (self.x[-1] - self.x[-2])

        x = self.x[-1]
        y = self.y[-1]

        for i in range(1, n+1):
            self.add_x(x_ext[i])
            self.add_y(y + trajectory * (x_ext[i] - x))
            self.add_z(self.z[-1])

            x = self.x[-1]
            y = self.y[-1]

    def adjacent_trajectory_y(self, dev, ws, MD):
        # ws given in ft assumed
        # linearly increase the spacing until a certain MD is reached
        ind = 0
        for i in range(0, len(dev.x)):
            if dev.MD[i] >= MD:
                ind = i
                break

        ws_int = 0
        if ind > 0:
            ws_int = linspace(0, ws, ind)

        for i in range(0, ind):
            self.add_x(dev.x[i])
            self.add_y(dev.y[i] + ws_int[i] * ft_to_m)
            self.add_z(dev.z[i])

        for i in range(ind+1, len(dev.x)):
            self.add_x(dev.x[i])
            self.add_y(dev.y[i] + ws * ft_to_m)
            self.add_z(dev.z[i])

    def read_dev(self, filepath):

        # Open the file in read-only mode
        f = open(filepath, 'r')

        for i, line in enumerate(f):
            # set well name
            if line.startswith('# WELL NAME:'):
                # Split the line using blank space as delimiter
                split_line = line.split()
                self.name = split_line[3]
                continue

            # set well position x
            if line.startswith('# WELL HEAD X-COORDINATE:'):
                # Split the line using blank space as delimiter
                split_line = line.split()
                for val in split_line:
                    try:
                        self.position.set_x(val)
                    except ValueError:
                        continue

                continue

            # set well position y
            if line.startswith('# WELL HEAD Y-COORDINATE:'):
                # Split the line using blank space as delimiter
                split_line = line.split()
                for val in split_line:
                    try:
                        self.position.set_y(val)
                    except ValueError:
                        continue

                continue

            # add well position datum
            if line.startswith('# WELL DATUM'):
                # Split the line using blank space as delimiter
                split_line = line.split()
                for val in split_line:
                    try:
                        self.position.set_datum(val)
                    except ValueError:
                        continue

                continue

            # skip redundant information
            if line.startswith('# WELL TYPE:') or line.startswith('#=') or 'MD' in line:
                continue

            # if line contains other information
            if line.startswith('#'):
                self.add_info(line)
                continue

            # Set values
            split_line = line.split()
            self.add_MD(split_line[0])
            self.add_x(split_line[1])
            self.add_y(split_line[2])
            self.add_z(split_line[3])
            self.add_TVD(split_line[4])
            self.add_dx(split_line[5])
            self.add_dy(split_line[6])
            self.add_azim_TN(split_line[7])
            self.add_incl(split_line[8])
            self.add_DLS(split_line[9])
            self.add_azim_GN(split_line[10])

        f.close()

    def ReadDEV(self, filepath):
        # Front-end wrapper to read_dev
        self.read_dev(filepath)


def pad_zeros(num):
    s = str(num)
    for i in range(0, 12-len(s)):
        s += '0'

    return s


def write_dev(dev, filename):
    f = open(filename, 'w')

    # Initial information
    print >> f, '# WELL TRACE INTERPOLATED BETWEEN EXISTING WELL TRAJECTORIES'
    print >> f, '# WELL NAME:               ' + str(dev.name)
    print >> f, '# WELL HEAD X-COORDINATE:  ' + str(dev.position.x)
    print >> f, '# WELL HEAD Y-COORDINATE:  ' + str(dev.position.y)
    print >> f, '# WELL DATUM:              ' + str(dev.position.datum)
    print >> f, '# WELL TYPE:'
    for info in dev.info:
        print >> f, info,
    print >> f, '#==============================================================================================================================================='
    print >> f, '      MD            X            Y            Z           TVD           DX          DY        AZIM_TN        INCL         DLS        AZIM_GN    '
    print >> f, '#==============================================================================================================================================='

    line = ' '
    for i, _ in enumerate(dev.MD):
        # pad float with arbitrarily many zeros
        line += pad_zeros(dev.MD[i]) + ' '
        line += pad_zeros(dev.x[i]) + ' '
        line += pad_zeros(dev.y[i]) + ' '
        line += pad_zeros(dev.z[i]) + ' '
        line += pad_zeros(dev.TVD[i]) + ' '
        line += pad_zeros(dev.dx[i]) + ' '
        line += pad_zeros(dev.dy[i]) + ' '
        line += pad_zeros(dev.azim_TN[i]) + ' '
        line += pad_zeros(dev.incl[i]) + ' '
        line += pad_zeros(dev.DLS[i]) + ' '
        line += pad_zeros(dev.azim_GN[i])
        print >> f, line
        line = ' '

    f.close()


def write_xyz(dev, filename):
    f = open(filename, 'w')

    # Initial information
    print >> f, '# WELL TRACE INTERPOLATED BETWEEN EXISTING WELL TRAJECTORIES'
    print >> f, '# WELL NAME:               ' + str(dev.name)
    print >> f, '# WELL HEAD X-COORDINATE:  ' + str(dev.position.x)
    print >> f, '# WELL HEAD Y-COORDINATE:  ' + str(dev.position.y)
    print >> f, '# WELL DATUM:              ' + str(dev.position.datum)
    print >> f, '# WELL TYPE:'
    for info in dev.info:
        print >> f, info,
    print >> f, '#===================================================='
    print >> f, '      ??            X            Y            Z      '
    print >> f, '#===================================================='

    line = ' '
    for i, _ in enumerate(dev.x):
        # pad float with arbitrarily many zeros
        line += pad_zeros(0.0) + ' '
        line += pad_zeros(dev.x[i]) + ' '
        line += pad_zeros(dev.y[i]) + ' '
        line += pad_zeros(dev.z[i]) + ' '
        print >> f, line
        line = ' '

    f.close()


def linspace(x1, x2, n):
    x = []
    slope = (x2 - x1) / (float(n) - 1)
    for i in range(0, n):
        x.append(x1 + slope * float(i))

    return x


def interpolate_trajectory_2d(X, vec, x, v_ex):
    converged = False
    for i, val in enumerate(X):
        if val > x:
            x1 = X[i-1]
            v1 = vec[i-1]
            x2 = X[i]
            v2 = vec[i]
            converged = True
            break

    if converged:
        if x1 != x2:
            v = v1 + (x-x1)*(v2-v1)/(x2-x1)
        else:
            v = v_ex
    else:
        trajectory = (vec[-1] - vec[-2]) / (X[-1] - X[-2])
        v = vec[-1] + (x - X[-1]) * trajectory

    return v


def MD_increment(vec1, vec2):
    # vec1=[x1, y1, z1] and vec2=[x2, y2, z2]
    return math.sqrt((vec2[0] - vec1[0]) ** 2 + (vec2[1] - vec1[1]) ** 2 + (vec2[2] - vec1[2]) ** 2)
