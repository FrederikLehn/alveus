import copy
import numpy as np

from calculus import forward_integration, backward_difference
from utilities import return_property


class Profile:
    def __init__(self):
        # time
        self.dates = np.array([], dtype='datetime64[D]')
        self.times = np.empty(0)

        # all values are potentials. Multiplying by uptime gives rates, subsequent integration gives cums
        # col index     0            1             2            3                4                   5
        # values = [oil_rate, total_gas_rate, water_rate, lift_gas_rate, gas_injection_rate, water_injection_rate]
        # units     Mstb/day     MMscf/day     Mstb/day     MMscf/day         MMscf/day          Mstb/day
        self.values = np.empty((0, 6))

        # cumulative offset. Added when integrating rates to account for prediction of historic wells.
        # col index    0          1             2            3               4                 5
        # values = [oil_cum, total_gas_cum, water_cum, lift_gas_cum, gas_injection_cum, water_injection_cum]
        # units      MMstb       Bscf         MMstb        Bscf             Bscf               MMstb
        self.offset = np.empty(6)

        # Four separate uptimes are available, one for production (o, g, w), three for lift, water and gas injection
        # index               0                1                 2                    3
        # values = [production_uptime, lift_gas_uptime, gas_injection_uptime, water_injection_uptime]
        # units            -                 -                   -                    -
        self.uptimes = np.empty((0, 4))

    def pre_allocate(self, n):
        self.times = np.zeros(n)
        self.values = np.zeros((n, 6))
        self.offset = np.zeros(6)
        self.uptimes = np.ones((n, 4))

    def set_dates(self, start):
        self.dates = start + self.times.astype(np.uint64)

    def set_times(self):
        self.times = (self.dates - self.dates[0]).astype(np.float64)

    def set_offset(self, profile):
        self.offset = np.asarray([profile.oil_cumulative()[-1],
                                  profile.total_gas_cumulative()[-1],
                                  profile.water_cumulative()[-1],
                                  profile.lift_gas_cumulative()[-1],
                                  profile.gas_injection_cumulative()[-1],
                                  profile.water_injection_cumulative()[-1]])

    def truncate(self, date):
        idx = np.argmax(self.dates >= date)

        self.dates = self.dates[:idx]
        self.times = self.times[:idx]
        self.values = self.values[:idx, :]
        self.uptimes = self.uptimes[:idx, :]

    def _integrate_rate(self, rate):
        return forward_integration(rate / 1e3, self.time(), initial=0.)

    @staticmethod
    def _ratio(num, den):
        return np.where(den > 0., num / den, 0.)

    # get time / dates -------------------------------------------------------------------------------------------------
    def time(self):
        return self.times

    def year(self):
        return self.time() / 365.25  # TODO: Improve to be the actual time in years (leap-year)
        #return (self.dates - self.dates[0]).astype(np.uint64)

    def date(self):
        return self.dates

    # get uptimes ------------------------------------------------------------------------------------------------------
    def uptime(self, idx):
        """
        Used for looping in internal functions. Returns the uptime associated to the value index idx

        Parameters
        ----------
        idx : int
            index to self.value

        Returns
        -------
        array_like
        """

        if idx < 3:
            return self.production_uptime()
        elif idx == 3:
            return self.lift_gas_uptime()
        elif idx == 4:
            return self.gas_injection_uptime()
        elif idx == 5:
            return self.water_injection_uptime()

    def production_uptime(self):
        return self.uptimes[:, 0]

    def lift_gas_uptime(self):
        return self.uptimes[:, 1]

    def gas_injection_uptime(self):
        return self.uptimes[:, 2]

    def water_injection_uptime(self):
        return self.uptimes[:, 3]

    # get potentials ---------------------------------------------------------------------------------------------------
    def oil_potential(self):
        return self.values[:, 0]

    def total_gas_potential(self):
        return self.values[:, 1]

    def water_potential(self):
        return self.values[:, 2]

    def lift_gas_potential(self):
        return self.values[:, 3]

    def gas_injection_potential(self):
        return self.values[:, 4]

    def water_injection_potential(self):
        return self.values[:, 5]

    def liquid_potential(self):
        return self.oil_potential() + self.water_potential()

    def gas_potential(self):
        return self.total_gas_potential() - self.lift_gas_potential()

    # get rates --------------------------------------------------------------------------------------------------------
    def oil_rate(self):
        return self.oil_potential() * self.production_uptime()

    def total_gas_rate(self):
        return self.gas_rate() + self.lift_gas_rate()

    def water_rate(self):
        return self.water_potential() * self.production_uptime()

    def lift_gas_rate(self):
        return self.lift_gas_potential() * self.lift_gas_uptime()

    def gas_injection_rate(self):
        return self.gas_injection_potential() * self.gas_injection_uptime()

    def water_injection_rate(self):
        return self.water_injection_potential() * self.water_injection_uptime()

    def liquid_rate(self):
        return self.liquid_potential() * self.production_uptime()

    def gas_rate(self):
        return self.gas_potential() * self.production_uptime()

    # get cums ---------------------------------------------------------------------------------------------------------
    def oil_cumulative(self):
        return self._integrate_rate(self.oil_rate()) + self.offset[0]

    def total_gas_cumulative(self):
        return self._integrate_rate(self.total_gas_rate()) + self.offset[1]

    def water_cumulative(self):
        return self._integrate_rate(self.water_rate()) + self.offset[2]

    def lift_gas_cumulative(self):
        return self._integrate_rate(self.lift_gas_rate()) + self.offset[3]

    def gas_injection_cumulative(self):
        return self._integrate_rate(self.gas_injection_rate()) + self.offset[4]

    def water_injection_cumulative(self):
        return self._integrate_rate(self.water_injection_rate()) + self.offset[5]

    def liquid_cumulative(self):
        return self._integrate_rate(self.liquid_rate()) + (self.offset[0] + self.offset[1])

    def gas_cumulative(self):
        return self._integrate_rate(self.gas_rate()) + (self.offset[1] - self.offset[3])

    # get ratio's ------------------------------------------------------------------------------------------------------
    def water_cut(self):
        return self._ratio(self.water_potential(), self.liquid_potential())

    def oil_cut(self):
        return self._ratio(self.oil_potential(), self.liquid_potential())

    def gas_oil_ratio(self):
        return np.where(self.uptimes[:, 0] > 0., self._ratio(self.gas_potential(), self.oil_potential()), 0.)

    def water_oil_ratio(self):
        return np.where(self.uptimes[:, 0] > 0., self._ratio(self.water_potential(), self.oil_potential()), 0.)

    def gas_liquid_ratio(self):
        return np.where(self.uptimes[:, 0] > 0., self._ratio(self.gas_potential(), self.liquid_potential()), 0.)

    def water_gas_ratio(self):
        return np.where(self.uptimes[:, 0] > 0., self._ratio(self.water_potential(), self.liquid_potential()), 0.)

    def oil_gas_ratio(self):
        return np.where(self.uptimes[:, 0] > 0., self._ratio(self.oil_potential(), self.gas_potential()), 0.)

    def total_gas_liquid_ratio(self):
        return np.where(self.uptimes[:, 0] > 0., self._ratio(self.total_gas_rate(), self.liquid_rate()), 0.)  # rate because it uses different uptimes

    # scaling methods --------------------------------------------------------------------------------------------------
    def temporal_scale(self, scalers, fluids):
        """
        A time-intrusive scaling method similar to the method used in simulate.py. It is only used for visualization
        in the ScaleFrame w.r.t. deciding on scaling laws
        :param scalers: list, [s_cum, s_rate, s_ffw, s_ffg]
        :param fluids:  list, [bo, bg, bw, rs]
        :return:
        """

        s_cum, s_rate, s_ffw, s_ffg = scalers
        bo, bg, bw, rs = fluids

        # scale temporarily on cumulative and rate
        if s_cum is not None:

            self.times *= s_cum

        if s_rate is not None:

            self.times /= s_rate
            self.values *= s_rate

        # update dates to account for the new time
        self.set_dates(self.dates[0])

        # due to a mass balance error related to clipping gas values < 0, it is better to not scale if not required
        if (s_ffw is None) and (s_ffg is None):
            return

        s_ffw = return_property(s_ffw, default=1.)
        s_ffg = return_property(s_ffg, default=1.)

        # scale on fractional flow of water and gas
        oil = self.values[:, 0]
        oil_res = bo * oil
        gas = np.clip(self.values[:, 1] - self.values[:, 3], 0., None)
        gas_res = bg * np.clip(gas - rs * oil, 0, None)
        water = self.values[:, 2]
        water_res = bw * water
        liquid = oil + water

        hydrocarbon = oil_res + gas_res
        reservoir = hydrocarbon + water_res

        tglr = self.values[:, 1] / liquid

        whcr = water_res / hydrocarbon * s_ffw
        fgor = gas_res / oil_res * s_ffg

        # calculating the fractional flows of water and gas respectively
        ffw = whcr / (1. + whcr)
        ffg = fgor / (1. + fgor)

        # calculating the scaled flows at surface
        self.values[:, 2] = reservoir * ffw / bw
        self.values[:, 0] = reservoir * (1. - ffw) * (1. - ffg) / bo
        self.values[:, 1] = rs * self.values[:, 0] + reservoir * (1. - ffw) * ffg / bg

        if tglr is not None:
            self.values[:, 3] = np.clip(tglr * liquid - self.values[:, 1], 0., None)
            self.values[:, 1] += self.values[:, 3]

    # resample methods -------------------------------------------------------------------------------------------------
    def resample(self, dateline, inplace=False):
        # pre-allocate
        resampled = Profile()
        resampled.pre_allocate(dateline.size)

        # sample time based on frequency and number of points
        if self.times.size:
            # set time and dates
            resampled.dates = dateline
            resampled.set_times()

            # adjust for date offsets
            delta = (dateline[0] - self.dates[0]).astype(np.float64)
            resampled.times += delta

            # resample values
            resampled.sum((self,))

            # adjust back
            resampled.times -= delta

        if inplace:
            self.replace(resampled)
        else:
            return resampled

    # merge methods ----------------------------------------------------------------------------------------------------
    def add(self, profile, fractions=1.):

        if isinstance(fractions, float):
            _fractions = np.repeat(fractions, 6)
        else:
            _fractions = fractions

        # re-sampling based on cum
        for i, fraction in zip(range(6), _fractions):
            self.values[:, i] += self.interpolate_rate(profile.time(), profile.values[:, i], uptime=1.) * fraction

        self.offset += profile.offset  # TODO: need * _fractions as well?

    def sum(self, profiles, fractions=1.):

        if isinstance(fractions, float):
            _fractions = np.tile(fractions, (len(profiles), 6))
        else:
            _fractions = fractions

        rates = np.zeros((self.times.size, 6))

        for p, fraction in zip(profiles, _fractions):
            # re-sampling based on cum
            self.add(p, fractions=fraction)

            # calculate rates for later calculation of uptimes
            for i in range(6):
                rates[:, i] += self.interpolate_rate(p.time(), p.values[:, i], p.uptime(i)) * fraction[i]

        self.calculate_uptime(self.values, rates)

    def interpolate_rate(self, time, value, uptime):
        cum = np.interp(self.time(), time, forward_integration(value * uptime, time, initial=0.), left=0.)
        return backward_difference(cum, self.time())

    def calculate_uptime(self, potentials, rates):
        # calculate production uptime
        self.uptimes[:, 0] = np.where(potentials[:, 0] > 0., rates[:, 0] / potentials[:, 0],
                                np.where(potentials[:, 1] > 0., rates[:, 1] / potentials[:, 1],
                                    np.where(potentials[:, 2] > 0., rates[:, 2] / potentials[:, 2],
                                        0.)))

        # calculate lift-gas uptime
        self.uptimes[:, 1] = self._ratio(rates[:, 3], potentials[:, 3])

        # calculate gas injection uptime
        self.uptimes[:, 2] = self._ratio(rates[:, 4], potentials[:, 4])

        # calculate water injection uptime
        self.uptimes[:, 3] = self._ratio(rates[:, 5], potentials[:, 5])

    def replace(self, profile):
        self.dates = profile.dates
        self.times = profile.times
        self.values = profile.values
        self.offset = profile.offset
        self.uptimes = profile.uptimes

    def stack(self, profile):
        self.dates = np.hstack((self.dates, profile.dates))
        self.times = np.hstack((self.times, profile.times))
        self.uptimes = np.vstack((self.uptimes, profile.uptimes))
        self.values = np.vstack((self.values, profile.values))

    def prepend(self, profile):
        # TODO: Set self.offset = profile.offset?
        self.times = np.hstack((profile.times, self.times + profile.times[-1]))
        self.uptimes = np.vstack((profile.uptimes, self.uptimes))
        self.values = np.vstack((profile.values, self.values))

        self.set_dates(profile.dates[0])

    def append(self, profile, inplace=False):
        merged = Profile()
        merged.times = np.hstack((self.times, profile.times + self.times[-1]))
        merged.uptimes = np.vstack((self.uptimes, profile.uptimes))
        merged.values = np.vstack((self.values, profile.values))

        merged.set_dates(self.dates[0])

        if inplace:
            self.replace(merged)
        else:
            return merged

    # auxiliary (back-end) ---------------------------------------------------------------------------------------------
    def allocate(self, dateline):
        self.pre_allocate(dateline.size)
        self.dates = dateline
        self.set_times()

    def copy(self):
        return copy.deepcopy(self)

    # auxiliary (front-end) --------------------------------------------------------------------------------------------
    def Allocate(self, dateline):
        self.allocate(dateline)

    def Get(self, id_):
        return getattr(self, id_)()

    def Add(self, profile):
        """
        Front-end wrapper to add
        """
        self.add(profile)

    def Sum(self, profiles):
        """
        Front-end wrapper to sum
        """
        self.sum(profiles)
