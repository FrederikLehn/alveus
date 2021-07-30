import numpy as np
import numpy.random as random
from scipy.optimize import linprog  # TODO: REMOVE


from properties import SimulationResult
from timeline import sample_timeline, merge_datelines
from profile_ import Profile
from optimize import secant
from statistics import stnormal2stuniform, extract_realizations

from _ids import *
from _errors import AssembleError, ConvergenceError


# ======================================================================================================================
# Performance Table
# ======================================================================================================================
class PerformanceTable:
    def __init__(self, profile):

        self.index = 0                    # time-index
        self.potentials = profile.copy()  # unconstrained potentials
        self.instantaneous = profile      # instantaneous potentials

        # calculate here to avoid recalculation at each progression
        self.cumulatives = np.vstack((profile.oil_cumulative(),
                                      profile.gas_injection_cumulative(),
                                      profile.water_injection_cumulative())).T

        # trackers for the cumulative progress of produced/injected fluids
        # col index     0            1             2
        # values = [oil_cumulative, gas_injection_cumulative, water_injection_cumulative]
        # units          MMstb                Bscf                       Bscf
        self.tracker = np.zeros(3)

        # progression of the tracker can be optimized by storing the previously used index for the closest cumulative
        # in potentials. This avoids the need for binary search during interpolation.
        self.tracker_index = [0, 0, 0]

    def _progress(self, choke, dt, idt, idu, idp):
        """
        Progress the performance table according to the choke position found during the constrained optimization.

        Parameters
        ----------
        choke : float
            choke position in [0, 1]
        dt : float
            time-step size
        idt : int
            index of tracker, 0=production, 1=gas injection, 2=water injection
        idu : int/tuple
            indexes of uptimes, production=(0, 1), gas injection=2, water injection=3
        idp : int/tuple
            indexes of instantaneous potentials, production=(0, 1, 2, 3), gas injection=4, water injection=5
        """

        # progress the tracker
        idi = idp[0] if isinstance(idp, tuple) else idp
        self.tracker[idt] += self.instantaneous.values[self.index, idi] * dt * choke / 1e3

        # assign uptimes values to the sample profile based on the choke
        self.instantaneous.uptimes[self.index, idu] = choke
        self.index += 1

        # update the instantaneous potentials via interpolation
        try:
            self._progress_tracker_index(idt)

            t = self.tracker_index[idt]
            den = self.cumulatives[t + 1, idt] - self.cumulatives[t, idt]
            nom = self.potentials.values[t + 1, idp] - self.potentials.values[t, idp]
            a = nom / den
            b = self.potentials.values[t, idp]
            x = self.tracker[idt] - self.cumulatives[t, idt]

            self.instantaneous.values[self.index, idp] = b + a * x

        except IndexError:

            pass

    def progress_production(self, choke, dt):
        self._progress(choke, dt, 0, (0, 1), (0, 1, 2, 3))

    def progress_gas_injection(self, choke, dt):
        self._progress(choke, dt, 1, 2, 4)

    def progress_water_injection(self, choke, dt):
        self._progress(choke, dt, 2, 3, 5)

    def _progress_tracker_index(self, idt):
        # progress the tracker index

        found = False

        while not found:

            try:
                cum = self.cumulatives[self.tracker_index[idt] + 1, idt]
            except IndexError:
                raise  # last index reached

            if cum < self.tracker[idt]:
                self.tracker_index[idt] += 1
            else:
                found = True

    def production(self):
        values = self.instantaneous.values[self.index, :]
        return values[0], values[1] - values[3], values[2]

    def injection(self):
        return self.instantaneous.values[self.index, 4:]

    def oil(self):
        return self.instantaneous.values[self.index, 0]

    def total_gas(self):
        return self.instantaneous.values[self.index, 1]

    def water(self):
        return self.instantaneous.values[self.index, 2]

    def lift_gas(self):
        return self.instantaneous.values[self.index, 3]

    def gas_injection(self):
        return self.instantaneous.values[self.index, 4]

    def water_injection(self):
        return self.instantaneous.values[self.index, 5]


# ======================================================================================================================
# Simulation entity, overarching simulation entity class
# ======================================================================================================================
class SimulationEntity:
    """
    :class: SimulationEntity is a back-end version of the Entity class from the EntityManager.
    it contains only the information relevant for simulation and uses back-end naming convention of methods.
    It also only contains the information relevant to a single specific Scenario and Simulation.
    """
    def __init__(self):

        self.name = None
        self.events = None
        self.children = []

        self.profiles = []      # list of class Profile()
        self.summaries = []     # list of dictionaries {summary_id: float}
        self.simulation = None  # class SimulationProfile()

        # polygon_id, only relevant to producers and injectors
        self.polygon_id = None
        self.polygon_index = None

        # retained for later transfer back to the EntityManager
        self.attr = None
        self.type = None
        self.id = None

        # network mappings ---------------------------------------------------------------------------------------------
        # used during mapping
        self.children_nw = []  # list, [(id, attr),...]  TODO: Not used?
        self.parents_nw = []  # list, [(id, attr),...]

        # using when creating system matrix coefficient
        self.active_wells = []         # list, [well_id, ...] list of wells associated to the network
        self.active_constraints = []   # list, [ID_PHASE_NW, ...] list of network IDs for active constraints
        self.active_phases = []        # list, [ID_PHASE_NW, ...] list of network IDs for inflowing phases
        self.streams_nw = {}           # dict, {well_id: {ID_PHASE_NW: float}} of network streams for each phase

        # variables used during network modelling (not applicable to all entities)
        self.inflow = None
        self.flow_constraints = None
        self.inj_constraints = None
        self.gl_constraint = None
        self.constraints = {}          # dict, {ID_PHASE_NW: float} dict of constraints
        self.primary_node = None

    # front-end code for interaction with EntityManager ----------------------------------------------------------------
    def GetId(self):
        return self.id

    def GetPointer(self):
        return self.id, self.attr

    def GetSimulation(self):
        return self.simulation

    # back-end code ----------------------------------------------------------------------------------------------------
    def get_network_parents(self):
        return [p for p in self.parents_nw]

    def get_profile(self, id_=0):
        return self.profiles[id_]

    def assign_well(self, well_id):
        self.active_wells.append(well_id)

    def assign_streams(self, well_id, child):
        try:
            split_type, splits = child.split
        except AttributeError:
            split_type, splits = False, {}

        streams = {id_: 0. for id_ in self.active_phases}

        for id_ in streams:

            stream = 1.

            if split_type:

                stream = splits[id_]

                if child.primary_node == self.id:
                    stream = 1. - stream

            try:
                streams[id_] = child.streams_nw[well_id][id_] * stream
            except KeyError:
                pass  # stream is either not in processor or preceding equipment, TODO: raise error?

        self.streams_nw[well_id] = streams

    def assemble_constraints(self):

        if self.flow_constraints is not None:
            self.constraints.update(self.flow_constraints)

        if self.inj_constraints is not None:
            self.constraints.update(self.inj_constraints)

        if self.gl_constraint is not None:
            self.constraints.update(self.gl_constraint)

        self.active_constraints = [id_ for id_, value in self.constraints.items() if value is not None]

    def network_coefficient(self, phase_id, well):
        stream = 0.

        if phase_id == ID_OIL_NW:
            stream = well.performance.oil() * self.streams_nw[well.id][phase_id]

        elif phase_id == ID_GAS_NW:
            stream = well.performance.total_gas() * self.streams_nw[well.id][phase_id]

        elif phase_id == ID_WATER_NW:
            stream = well.performance.water() * self.streams_nw[well.id][phase_id]

        elif phase_id == ID_LIQUID_NW:
            oil = well.performance.oil() * self.streams_nw[well.id][ID_OIL_NW]
            water = well.performance.water() * self.streams_nw[well.id][ID_WATER_NW]
            stream = oil + water

        elif phase_id == ID_INJ_GAS_NW:
            stream = well.performance.gas_injection() * self.streams_nw[well.id][phase_id]

        elif phase_id == ID_INJ_WATER_NW:
            stream = well.performance.water_injection() * self.streams_nw[well.id][phase_id]

        elif phase_id == ID_LIFT_GAS_NW:
            stream = well.performance.lift_gas() * self.streams_nw[well.id][phase_id]

        return stream


class ProducerSimulation(SimulationEntity):
    def __init__(self, properties):
        super().__init__()

        # unpack properties --------------------------------------------------------------------------------------------
        self.history = properties.history.get()
        self.spacing = properties.well_spacing.get()
        self.fluids = properties.res_fluids.get()
        self.ttglr = properties.gas_lift.get()
        self.flow_constraints = properties.flow_constraints.get()
        self.gl_constraint = properties.gl_constraint.get()
        self.volumes = properties.volumes.get()
        self.risking = properties.risking.get()

        self.statics = properties.statics.get()
        self.statics_unc = properties.statics_unc.get()
        self.scalers = properties.scalers
        self.scalers_unc = properties.scalers_unc.get()

        self.predictions = properties.prediction

        # properties set in the EntityManager --------------------------------------------------------------------------
        # scaling evaluation function
        self.scaling = None

        # L/M/H functions and typecurve ids for later sampling
        self._functions = [None, None, None]   # list, [liquid_potential, oil_cut, gas_oil_ratio] functions with .eval(x) methods
        self._typecurves = [None, None, None]  # list, id from typecurves associated with L/M/H (None if not typecurve)
        self._occurrences = None               # list, [probability of low, probability of mid]

        # temporarily stored variables during constrained simulation ---------------------------------------------------
        self.performance = None

    # front-end code for interaction with EntityManager ----------------------------------------------------------------
    def AssignFunctions(self, typecurves):
        self._occurrences = self.predictions.get_occurrences()

        for j, p in enumerate(self.predictions.get()):

            try:

                type_, prediction = p.get()

            except AssembleError as e:

                raise AssembleError('Producer ({}) unable to assemble function: {}'.format(self.name, str(e)))

            if type_ is None:

                continue

            if type_ == ID_PREDICTION_TYPECURVE:

                try:

                    self._functions[j] = typecurves[prediction[0]].functions
                    self._typecurves[j] = prediction[0]

                except KeyError:

                    raise KeyError('Producer ({}) unable to find the assigned typecurve'.format(self.name))

            elif type_ in (ID_PREDICTION_FUNCTION, ID_PREDICTION_IMPORT):

                self._functions[j] = prediction

    def GetPropertyMap(self):
        return {'length':        self.statics[0],
                'hcft':          self.statics[1],
                 'hcpv':         self.statics[2],
                 'permeability': self.statics[3],
                 'oil_density':  self.statics[4],
                 'stoiip':       self.volumes,
                 'maturity':     self.risking[0],
                 'pos':          self.risking[1]}

    # back-end code ----------------------------------------------------------------------------------------------------
    def sample_functions(self, x, i):
        """
        Sample either low, mid or high function
        :param x: sampled probability
        :param i: sample idx
        :return:
        """
        j = self.polygon_index

        if x[i, j] < self._occurrences[0]:  # Low

            function = self._functions[0]
            typecurve = self._typecurves[0]

        elif x[i, j] < self._occurrences[1]:  # Mid

            function = self._functions[1]
            typecurve = self._typecurves[1]

        else:  # High

            function = self._functions[2]
            typecurve = self._typecurves[2]

        return function, typecurve

    def reservoir_volume(self):
        bo, bg, bw, rs = self.fluids
        oil, gas, water = self.performance.production()
        return oil * (bo + max(gas / oil - rs, 0.) * bg) + water * bw

    def prepare_network(self):
        self.active_wells = [self.id]

        self.streams_nw[self.id] = {ID_OIL_NW: 1., ID_GAS_NW: 1., ID_WATER_NW: 1., ID_LIFT_GAS_NW: 1.}

    def assign_performance(self, i):
        self.performance = PerformanceTable(self.profiles[i])

    def progress_performance(self, choke, dt):
        self.performance.progress_production(choke, dt)


class InjectorSimulation(SimulationEntity):
    def __init__(self, properties):
        super().__init__()

        # unpack properties --------------------------------------------------------------------------------------------
        self.history = properties.history.get()
        self.phase = properties.phase.get()
        self.fluids = properties.inj_fluids.get()
        self.inj_constraints = properties.inj_constraints.get()
        self.wag = properties.wag.get()
        self.voidage = properties.voidage
        self.inj_potentials = properties.inj_potentials.get()

        self.producer_map = {}  # dict, {producer_id: producer index in system matrix}

        # temporarily stored variables during constrained simulation ---------------------------------------------------
        self.performance = None

    def injection_volume(self):
        array = [() for _ in self.producer_map]

        bw_inj, bg_inj = self.fluids
        gas_inj, water_inj = self.performance.injection()
        q_inj = gas_inj * bg_inj + water_inj * bw_inj

        for i, (id_, index) in enumerate(self.producer_map.items()):

            ratio = self.voidage.get_ratio()

            coefficient = - q_inj * self.voidage.get_proportion(id_) / ratio
            array[i] = (coefficient, index)

        return array

    def assign_performance(self, i):
        self.performance = PerformanceTable(self.profiles[i])

    def prepare_network(self):
        self.active_wells = [self.id]

        self.streams_nw[self.id] = {ID_INJ_GAS_NW: 1.}
        self.streams_nw[self.id] = {ID_INJ_WATER_NW: 1.}

    def progress_performance(self, choke, dt):

        if self.phase == ID_GAS_INJ:

            self.performance.progress_gas_injection(choke, dt)

        elif self.phase == ID_WATER_INJ:

            self.performance.progress_water_injection(choke, dt)

        else:  # WAG

            pass


class ProcessorSimulation(SimulationEntity):
    def __init__(self, properties):
        super().__init__()

        # unpack properties --------------------------------------------------------------------------------------------
        self.inflow = properties.inflow.get()
        self.flow_constraints = properties.flow_constraints.get()
        self.inj_constraints = properties.inj_constraints.get()
        self.split = properties.split.get()
        self.primary_node = properties.primary_node.get()

    def assemble_phases(self):
        self.active_phases = [id_ for id_, value in self.inflow.items() if value]


class PipelineSimulation(SimulationEntity):
    def __init__(self, properties):
        super().__init__()

        # unpack properties --------------------------------------------------------------------------------------------
        self.flow_constraints = properties.flow_constraints.get()
        self.inj_constraints = properties.inj_constraints.get()

        self.active_phases = [ID_OIL_NW, ID_GAS_NW, ID_WATER_NW, ID_INJ_GAS_NW, ID_INJ_WATER_NW]


class TypecurveSimulation(SimulationEntity):
    def __init__(self, properties):
        super().__init__()

        # unpack properties --------------------------------------------------------------------------------------------
        self.spacing = properties.well_spacing.get()

        self.statics = properties.statics.get()
        self.statics_unc = properties.statics_unc.get()

        # functions: liquid_potential, oil_cut and gas_oil_ratio with .eval(x) methods
        self.functions = None


# ======================================================================================================================
# Simulation cases (history & prediction)
# ======================================================================================================================
class SimulationCase:
    def __init__(self, properties):

        self._start = np.array([], dtype='datetime64[D]')
        self._end = np.array([], dtype='datetime64[D]')
        self._timeline = np.empty(0)
        self._dateline = np.array([], dtype='datetime64[D]')

        # modelling
        self._constrained = False
        self._availability = 1.

        # number of samples
        self._samples = 1
        self._save_all = False

        # timeline
        self._frequency, self._delta = properties.timeline.get()

        # entities
        self._producers = {}    # only producers included in scenario
        self._injectors = {}    # only injectors included in scenario
        self._processors = {}   # only processors included in scenario
        self._pipelines = {}    # only pipelines included in scenario
        self._polygons = {}     # all polygons
        self._typecurves = {}   # all typecurves

        # mapping from well id to system matrix index
        self._well_map = {}  # dict, {well_id: system_index, ...}

    # front-end code for interaction with EntityManager ----------------------------------------------------------------
    def GetDateline(self):
        return self._dateline

    def GetSamples(self):
        return self._samples

    def GetEquipment(self):
        return self._get_equipment()

    def GetPolygons(self):
        return self._polygons

    def GetWells(self):
        return self._get_wells()

    def KeepAllProfiles(self):
        return self._save_all

    def PostProcess(self, summaries, settings):
        extraction = settings.GetExtraction()
        cases = settings.GetCases(False)
        self._post_process(summaries, extraction, cases)

    def SetDuration(self, start, end):
        self._start = np.array(start, dtype='datetime64[D]')
        self._end = np.array(end, dtype='datetime64[D]')

    def SetEntities(self, producers, injectors, processors=None, pipelines=None, polygons=None, typecurves=None):
        self._producers = producers
        self._injectors = injectors
        self._processors = processors if processors is not None else {}
        self._pipelines = pipelines if pipelines is not None else {}
        self._polygons = polygons if polygons is not None else {}
        self._typecurves = typecurves if typecurves is not None else {}

        for injector in injectors.values():
            self._set_producer_map(injector)

        self._set_polygon_indices()

    # back-end code for simulating -------------------------------------------------------------------------------------
    def _assemble_system_network(self):
        self._assemble_well_map()
        self._prepare_network()

        for well in self._get_wells():
            self._assign_network_coefficients(well.id, well)

    def _assign_network_coefficients(self, well_id, child):
        # propagate up the hierarchy
        parents = child.get_network_parents()

        for pointer in parents:

            try:
                parent = self._get_entity(*pointer)
            except KeyError:
                raise KeyError('Entity ({}) sends flow downstream to an entity '
                               'not included in the simulation.'.format(child.name))

            # wells
            parent.assign_well(well_id)

            # streams
            parent.assign_streams(well_id, child)

            self._assign_network_coefficients(well_id, parent)

    def _assemble_well_map(self):
        """
        Assembles the mapping from well id to system matrix index.
        """

        for i, well in enumerate(self._get_wells()):
            self._well_map[well.id] = i

    def _prepare_network(self):
        for well in self._get_wells():
            well.assemble_constraints()
            well.prepare_network()

        for processor in self._processors.values():
            processor.assemble_constraints()
            processor.assemble_phases()

        for pipeline in self._pipelines.values():
            pipeline.assemble_constraints()

    def _get_entity(self, id_, attr):
        return getattr(self, attr)[id_]

    def _get_producers(self, children):
        """
        Extracts producers from a list of children.

        Parameters
        ----------
        children : list
            List of tuples: (id, attr)

        Returns
        -------
        list
            List of SimulationEntity
        """

        return [self._producers[id_] for (id_, attr) in children if attr == '_producers' and id_ in self._producers]

    def _set_producer_map(self, injector):
        """
        Sets the producer mapping for an injector.

        Parameters
        ----------
        injector : InjectorSimulation
            Class InjectionSimulation
        """

        producers = self._get_producers(injector.children)
        injector.producer_map = {p.id: i for (i, p) in enumerate(self._producers.values()) if p in producers}

    def _set_polygon_indices(self):
        for i, id_ in enumerate(self._polygons):
            for producer in self._producers.values():
                if producer.polygon_id == id_:
                    producer.polygon_index = i

            for typecurve in self._typecurves.values():
                if typecurve.polygon_id == id_:
                    typecurve.polygon_index = i

    def _generate_timeline(self):
        self._timeline = sample_timeline(self._start, self._end, self._frequency, delta=self._delta)
        self._dateline = self._start + self._timeline.astype(np.uint64)

    def _get_wells(self):
        return list(self._producers.values()) + list(self._injectors.values())

    def _get_equipment(self):
        return list(self._processors.values()) + list(self._pipelines.values())

    def _get_network(self):
        return list({**self._producers, **self._injectors, **self._processors, **self._pipelines}.values())

    def _post_process(self, summaries, extraction, cases):
        """
        Post-processing of a simulation run. Extracting low, mid and high cases.

        Parameters
        ----------
        summaries: list
            List of class Summary(), used to calculate summary values from profiles/properties
        extraction : list
            List of strings, id's from summaries which are to be used for extraction of realizations
        cases : list
            List of integers, denoting the percentile for Low, Mid and High case respectively.
        """

        if not extraction:
            raise ValueError('No summary defined for extraction of L/M/H profiles')

        save_all = self._save_all
        weights = np.full(len(extraction), 1. / len(extraction))

        # calculate producer summaries
        for prod in self._producers.values():
            try:
                prod.summaries = [{s.GetId(): s.Calculate(prod.profiles[i], prod.GetPropertyMap()) for s in summaries}
                                  for i in range(self._samples)]

            except NameError:
                raise

        # pre-allocate injector summaries
        for inj in self._injectors.values():
            inj.summaries = [{s.GetId(): 0. for s in summaries} for _ in range(self._samples)]

        # extract representative realizations for each producer
        for prod in self._producers.values():

            lmh = extract_realizations(prod.summaries, extraction, weights, cases)

            prod.simulation = SimulationResult(lmh, prod.profiles, prod.summaries, shading=save_all, finalized=True)

        for inj in self._injectors.values():

            if self._constrained:
                inj.simulation = SimulationResult((0, 0, 0), inj.profiles, inj.summaries,
                                                  shading=save_all, finalized=True)

            else:
                # create LMH for injectors based on the extracted realizations in the supported producers
                producers = self._get_producers(inj.children)

                lmh_profiles = [self._simulate_injection_potential(inj, [p.simulation.get_lmh()[i] for p in producers])
                               for i in range(3)]

                inj.simulation = SimulationResult(profiles=inj.profiles, summaries=inj.summaries,
                                                 lmh_p=lmh_profiles, shading=save_all, finalized=True)

        # calculate phases going through the surface network -----------------------------------------------------------
        # pre-allocate profiles for all equipment
        for e in self._get_equipment():
            e.profiles = [Profile() for _ in range(self._samples)]
            for profile in e.profiles:
                profile.allocate(self._dateline)

        wells = {**self._producers, **self._injectors}
        phases = (ID_OIL_NW, ID_GAS_NW, ID_WATER_NW, ID_LIFT_GAS_NW, ID_INJ_GAS_NW, ID_INJ_WATER_NW)

        for e in self._get_equipment():

            active_wells = [wells[w] for w in e.active_wells]
            streams = [[e.streams_nw[well.id][id_] if id_ in e.streams_nw[well.id] else 0. for id_ in phases] for well in active_wells]

            # ensure lift-gas stream is equal to total gas stream
            for stream in streams:
                stream[3] = stream[1]

            for i in range(self._samples):
                e.profiles[i].sum([w.profiles[i] for w in active_wells], streams)

        # calculate summaries for all equipment and extract LMH
        for e in self._get_equipment():

            e.summaries = [{summary.GetId(): 0. for summary in summaries} for _ in range(self._samples)]

            for i in range(self._samples):
                for summary in summaries:
                    try:
                        e.summaries[i][summary.GetId()] = summary.Calculate(e.profiles[i], {})

                    except NameError:
                        pass

            lmh = extract_realizations(e.summaries, extraction, weights, cases)
            e.simulation = SimulationResult(lmh, e.profiles, e.summaries, shading=save_all, finalized=True)

    @staticmethod
    def _simulate_gas_lift_potential(profile, ttglr):
        if ttglr is not None:
            profile.values[:, 1] -= profile.values[:, 3]  # remove gas-lift from total gas
            profile.values[:, 3] = np.clip(ttglr * profile.liquid_potential() - profile.values[:, 1], 0., None)
            profile.values[:, 1] += profile.values[:, 3]

    def _equality_constraints(self):
        wells = self._get_wells()
        w = len(wells)
        p = len(self._producers)

        A_eq = np.zeros((p, w))

        for j, producer in enumerate(self._producers.values()):
            A_eq[j, j] = producer.reservoir_volume()

        for j, injector in enumerate(self._injectors.values()):
            volumes = injector.injection_volume()

            for volume, index in volumes:
                A_eq[index, p + j] = volume

        return A_eq, np.zeros((p, 1))

    def _inequality_constraints(self):
        n_con = np.sum([len(e.active_constraints) for e in self._get_network()])
        n_well = len(self._get_wells())

        A_iq = np.zeros((n_con, n_well))
        b_iq = np.zeros((n_con, 1))

        wells = {**self._producers, **self._injectors}

        count = 0
        for e in self._get_network():

            for con in e.active_constraints:

                for w in e.active_wells:

                    sys_idx = self._well_map[w]  # TODO: store smarter. Perhaps store in e.active_wells
                    well = wells[w]

                    A_iq[count, sys_idx] += e.network_coefficient(con, well)

                b_iq[count, 0] = e.constraints[con] * self._availability

                count += 1

        return A_iq, b_iq

    def _bounds(self):
        return [(0., self._availability) for _ in self._get_wells()]

    def _objective_function(self, i, t):
        # optimize the oil rates in each time_step (negative to convert from min to max)
        return [-w.profiles[i].values[t, 0] for w in self._get_wells()]

    def _progress_performance(self, chokes, dt):
        for j, well in enumerate(self._get_wells()):
            well.progress_performance(chokes[j], dt)

    def _assign_performance(self, i):
        for well in self._get_wells():
            well.assign_performance(i)

    def _simulate_rates(self):
        self._assemble_system_network()

        bounds = self._bounds()
        dt = self._timeline[1:] - self._timeline[:-1]

        for i in range(self._samples):

            self._assign_performance(i)

            for t, _ in enumerate(self._timeline):

                g = self._objective_function(i, t)

                A_eq, b_eq = self._equality_constraints()
                A_iq, b_iq = self._inequality_constraints()
                #print(A_eq)
                #print(A_iq)
                #print(b_iq)

                if b_eq.size or b_eq.size:
                    chokes = linprog(g, A_ub=A_iq, b_ub=b_iq,A_eq=A_eq, b_eq=b_eq, bounds=bounds)
                else:
                    chokes = np.repeat(self._availability, (len(self._get_wells()), 1))

                print(self._dateline[t], np.round(chokes.x, 4))

                try:
                    dt_ = dt[t]
                except IndexError:
                    dt_ = 0.  # last time-step, dt irrelevant.

                self._progress_performance(chokes.x, dt_)

    def _simulate_injection_potential(self, injector, samples=()):

        if injector.history is None:
            profile = Profile()
            profile.allocate(self._dateline)
        else:
            profile = injector.history.resample(self._dateline)

        # unpack variables and pre-allocate ----------------------------------------------------------------------------
        phase = injector.phase
        bg_inj, bw_inj = injector.fluids
        wag_cycle, wag_cycles = injector.wag
        gas_inj, water_inj = injector.inj_potentials

        # set provided injection ---------------------------------------------------------------------------------------
        gas = None
        if gas_inj is not None:
            gas = np.repeat(gas_inj, self._timeline.size)

        water = None
        if water_inj is not None:
            water = np.repeat(water_inj, self._timeline.size)

        # calculating injection rate based on phase --------------------------------------------------------------------
        if phase == ID_GAS_INJ:
            if gas is None:
                gas = self._calculate_voidage_replacement(injector, samples) / bg_inj

            profile.values[:, 4] = gas

        elif phase == ID_WATER_INJ:
            if water is None:
                water = self._calculate_voidage_replacement(injector, samples) / bw_inj

            profile.values[:, 5] = water

        else:  # WAG
            # prepare injection fluid
            voidage = None
            if (gas is None) or (water is None):
                voidage = self._calculate_voidage_replacement(injector, samples)

            fluid = [gas, water]
            if gas is None:
                fluid[0] = voidage / bg_inj

            if water is None:
                fluid[1] = voidage / bw_inj

            # WAG requires time-stepping due to the cycles
            t_c = 0.
            idx = 4
            cycle = 0.

            if wag_cycles:

                cycles = wag_cycles * 2

                for i, t in enumerate(self._timeline):
                    profile.values[i, idx] = fluid[int(cycle % 2)][i]

                    if t - t_c >= wag_cycle:
                        idx = (((idx - 4) + 1) % 2) + 4
                        cycle += 1
                        t_c = t

                        if cycle == cycles:
                            break

            # remaining injection is water injection
            profile.values[:, 5] = np.where(self._timeline < t_c, profile.values[:, 5], fluid[1])

        # apply linear correction where sum(proportions) * VR < 1 ------------------------------------------------------
        c = injector.voidage.get_cumulative_voidage()

        if 0. < c < 1.:
            profile.values[:, 4] /= c
            profile.values[:, 5] /= c

        return profile

    def _calculate_voidage_replacement(self, injector, samples):
        # Extract producers and which sample to use from them ----------------------------------------------------------
        voidage = np.zeros(self._timeline.size)

        producers = self._get_producers(injector.children)
        n = len(producers)

        # allow the use of different samples from different producers
        if isinstance(samples, tuple) or isinstance(samples, list):
            _samples = samples
        else:
            if samples is None:
                _samples = [0 for _ in range(n)]
            else:
                _samples = [samples for _ in range(n)]

        # calculating required voidage replacement for each producer ---------------------------------------------------
        for i, (producer, sample) in enumerate(zip(producers, _samples)):
            # unpacking required information for the supported producer
            bo, bg, bw, rs = producer.fluids
            oil = producer.get_profile(sample).oil_potential()
            gor = producer.get_profile(sample).gas_oil_ratio()
            water = producer.get_profile(sample).water_potential()
            ratio = injector.voidage.get_voidage_proportion(producer.id)

            voidage += ratio * (oil * (bo + np.clip(gor - rs, 0., None) * bg) + water * bw)

        return voidage


class HistoryCase(SimulationCase):
    def __init__(self, properties):
        super().__init__(properties)

    # front-end code ---------------------------------------------------------------------------------------------------
    def CalculateTotalProduction(self):
        return self._calculate_total_production()

    def Run(self):
        self._simulate()

    # back-end code ----------------------------------------------------------------------------------------------------
    def _simulate(self):
        # generate timeline --------------------------------------------------------------------------------------------
        self._generate_timeline()
        self._adjust_timeline()

        # simulate production potentials -------------------------------------------------------------------------------
        for prod in self._producers.values():
            profile = self._simulate_production_potential(prod)
            prod.profiles.append(profile)

        # simulate injection potentials --------------------------------------------------------------------------------
        for inj in self._injectors.values():
            profile = self._simulate_injection_potential(inj, samples=None)
            inj.profiles.append(profile)

    def _adjust_timeline(self):
        """
        adjusting timeline to include start and end dates of producer/injector history
        :return:
        """
        # gather all entities
        profiles = [p.history for p in self._producers.values() if p.history is not None]
        profiles += [i.history for i in self._injectors.values() if i.history is not None]

        if not profiles:
            return

        dates = [np.array([p.date()[0], p.date()[-1]], dtype='datetime64[D]') for p in profiles]
        self._dateline = merge_datelines([self._dateline] + dates)
        self._timeline = (self._dateline - self._dateline[0]).astype(np.float64)

    def _calculate_total_production(self):
        # calculate total production of history
        historical_production = Profile()
        historical_production.allocate(self._dateline)
        historical_production.sum([w.history for w in self._get_wells() if w.history is not None])

        # calculating total production of simulation
        simulated_production = Profile()
        simulated_production.allocate(self._dateline)
        simulated_production.sum([w.profiles[0] for w in self._get_wells()])

        return self._dateline, historical_production, simulated_production

    def _simulate_production_potential(self, producer):
        history = producer.history
        if history is None:
            history = Profile()

        profile = history.resample(self._dateline)

        # calculate lift-gas requirements ------------------------------------------------------------------------------
        self._simulate_gas_lift_potential(profile, producer.ttglr)

        return profile


class PredictionCase(SimulationCase):
    def __init__(self, properties):
        super().__init__(properties)

        # plateau
        self._plateau_oil, self._plateau_gas = properties.plateau.get()

        # modelling
        self._availability, self._constrained = properties.constrained.get()

        # sampling
        self._samples, self._save_all = properties.sampling.get()

    # front-end code ---------------------------------------------------------------------------------------------------
    def CalculateStability(self, variables):
        return self._stochastic_stability(variables)

    def Run(self, rho_v, rho_e):
        self._simulate_potentials(rho_v, rho_e)

        if self._constrained:
            self._simulate_rates()

    # external methods -------------------------------------------------------------------------------------------------
    # internal methods -------------------------------------------------------------------------------------------------
    @staticmethod
    def _evaluate_scalers(prod, statics, typecurve_statics):
        sample = [0. for _ in range(6)]

        for i in range(4):

            try:

                sample[i] = prod.scaling.eval(i, *statics) / prod.scaling.eval(i, *typecurve_statics)

            except TypeError:

                sample[i] = 1.

            except AttributeError:  # no associated scaling evaluation function

                sample[i] = 1.

            except NameError as e:

                raise NameError('Producer ({}) unable to evaluate parameter with the {}'.format(prod.name, str(e)))

            except SyntaxError as e:

                raise NameError('Producer ({}) unable to evaluate statement: {}'.format(prod.name, str(e)))

        return sample

    def _sample_function_uncertainty(self, rho_e):
        return stnormal2stuniform(np.random.multivariate_normal(np.zeros(len(rho_e)), rho_e, self._samples))

    @staticmethod
    def _sample_scalers(prod, sample, x, idx):

        scalers = prod.scalers.get()
        scalers_unc = prod.scalers_unc

        # sampled uncertainty parameters for the associated polygon
        x_scaler = x[prod.polygon_index, :len(scalers), idx]

        # extract assigned or defaulted scalers
        sample = prod.scalers.assign(sample)

        for i, scaler in enumerate(scalers):
            if scaler is not None:
                try:
                    sample[i] = scalers_unc[i].sample(x_scaler[i], scaler)  # sample[i]
                except ValueError as e:
                    raise ValueError('Producer ({}) unable to sample uncertainty: {}'.format(prod.name, str(e)))

        return sample

    @staticmethod
    def _sample_statics(entity, x, idx):
        """
        Sample static parameters of either producer or typecurve, taking into account uncertainty
        :param entity: ProducerSimulation or TypecurveSimulation
        :param x: sampled static uncertainty matrix
        :param idx: sample index
        :return:
        """
        # scalers and static parameters for the producer
        statics = entity.statics
        statics_unc = entity.statics_unc

        # sampled uncertainty parameters for the associated polygon
        if entity.polygon_id is not None:

            x_static = x[entity.polygon_index, 6:, idx]  # 6 is number of scalers

        else:  # typecurve is not associated to a polygon, thus unable to sample uncertainty

            return statics

        try:

            return [statics_unc[i].sample(x_static[i], statics[i]) for i in range(len(statics))]

        except ValueError as e:

            raise ValueError('Entity ({}) unable to sample uncertainty: {}'.format(entity.name, str(e)))

    def _sample_static_uncertainty(self, rho_v, rho_e):
        v = len(rho_v)
        e = len(rho_e)
        n = v * e
        rho_va = np.asarray(rho_v)
        rho = np.zeros((n, n))

        # assemble correlation matrix
        for i in range(0, e):
            for j in range(0, i + 1):
                rho[i*v:(i+1)*v, j*v:(j+1)*v] = rho_e[i][j] * rho_va

        rho += rho.T

        # sample standard normal random variables
        x = np.random.multivariate_normal(np.zeros(n), rho, self._samples)
        return np.reshape(x, (self._samples, v, e)).T

    def _simulate_potentials(self, rho_v, rho_e):
        # generate timeline --------------------------------------------------------------------------------------------
        self._generate_timeline()

        # sample uncertainty space -------------------------------------------------------------------------------------
        xf = self._sample_function_uncertainty(rho_e)
        xs = self._sample_static_uncertainty(rho_v, rho_e)

        for i in range(0, self._samples):

            # simulate production potentials
            for j, prod in enumerate(self._producers.values()):

                # sample function and potential typecurve id
                functions, id_ = prod.sample_functions(xf, i)

                # transform samples into scalers parameters
                if id_ is not None:
                    typecurve = self._typecurves[id_]
                else:
                    typecurve = None

                scalers = self._static_to_scalers(prod, typecurve, xs, i)
                scalers = self._sample_scalers(prod, scalers, xs, i)
                self._well_spacing_adjustment(prod, typecurve, scalers)

                profile = self._simulate_production_potential(prod, functions, scalers)

                # if producer has history, set cumulative offsets
                if prod.history is not None:
                    profile.set_offset(prod.history)

                prod.profiles.append(profile)

            # simulate injection potentials
            for inj in self._injectors.values():
                profile = self._simulate_injection_potential(inj, i)

                # if injector has history, set cumulative offsets
                if inj.history is not None:
                    profile.set_offset(inj.history)

                inj.profiles.append(profile)

    def _simulate_production_potential(self, producer, functions, scalers):
        profile = Profile()
        profile.allocate(self._dateline)

        # unpack variables and pre-allocate ----------------------------------------------------------------------------
        if functions is not None:
            liquid_potential, water_cut, gas_oil_ratio = functions
        else:
            return profile

        bo, bg, bw, rs = producer.fluids
        ttglr = producer.ttglr
        s_cum, s_rate, s_ffw, s_ffg, onset, wct_ini = scalers

        # calculate liquid potential vs time ---------------------------------------------------------------------------
        liquid = liquid_potential.eval(self._timeline) * s_rate

        # calculate GOR vs time ----------------------------------------------------------------------------------------
        gor = gas_oil_ratio.eval(self._timeline)

        # cut-cum scaling preparation ----------------------------------------------------------------------------------
        delta = np.zeros(self._dateline.size)
        if onset:
            delta = np.exp(-self._timeline / onset)

        if wct_ini:
            try:
                cum_ini = secant(lambda x: water_cut.eval(x) - wct_ini, 0., 1.)
            except ConvergenceError as e:
                raise ConvergenceError('{} failed to assign initial water-cut due to: {}'.format(producer.name, str(e)))
        else:
            cum_ini = 0.

        # time-step ----------------------------------------------------------------------------------------------------
        cum = 0.
        dt = self._timeline[1:] - self._timeline[:-1]

        for i, _ in enumerate(self._timeline):

            wct = water_cut.eval(cum / s_cum + cum_ini)

            # calculate flow at reservoir conditions
            oil = liquid[i] * (1. - wct)
            oil_res = bo * oil
            gas_res = bg * max(gor[i] - rs, 0.) * oil
            water_res = bw * liquid[i] * wct
            hydrocarbon = oil_res + gas_res
            reservoir = hydrocarbon + water_res

            # scaling the water-hydrocarbon ratio and free-gas oil ratio with the fractional flow scalers
            whcr = water_res / hydrocarbon * (s_ffw + (1. - s_ffw) * delta[i])
            fgor = gas_res / oil_res * (s_ffg + (1. - s_ffg) * delta[i])

            # calculating the fractional flows of water and gas respectively
            ffw = whcr / (1. + whcr)
            ffg = fgor / (1. + fgor)

            # calculating the scaled flows at surface
            profile.values[i, 2] = reservoir * ffw / bw
            profile.values[i, 0] = reservoir * (1. - ffw) * (1. - ffg) / bo
            profile.values[i, 1] = rs * profile.values[i, 0] + reservoir * (1. - ffw) * ffg / bg

            # update the cumulative oil using forward integration for the cut-cum calculation
            try:
                cum += profile.values[i, 0] * dt[i] / 1e3
            except IndexError:
                pass  # last time-step, cum not used going forward.

        # calculate lift-gas requirements ------------------------------------------------------------------------------
        self._simulate_gas_lift_potential(profile, ttglr)

        return profile

    def _static_to_scalers(self, prod, typecurve, x, i):
        scalers = [None for _ in range(6)]

        if typecurve is not None:
            statics = self._sample_statics(prod, x, i)
            tc_statics = self._sample_statics(typecurve, x, i)
            scalers = self._evaluate_scalers(prod, statics, tc_statics)

        return scalers

    def _stochastic_stability(self, variables):
        if self._samples < 2:
            return

        m = len(variables)
        s = 2

        # fill array with summed values from each realization
        _array = np.zeros((self._samples, m))

        for i in range(self._samples):
            profile = Profile()
            profile.allocate(self._dateline)
            profile.sum([p.profiles[i] for p in self._get_wells()])

            _array[i, 0] = np.sum(profile.Get(variables[0].GetId()))    # oil rate
            _array[i, 1] = profile.Get(variables[1].GetId())[-1]        # oil cum
            _array[i, 2] = np.mean(profile.Get(variables[2].GetId()))   # water-cut
            _array[i, 3] = np.mean(profile.Get(variables[3].GetId()))   # GOR

        # calculating statistical properties as a function of sample size for each variable
        stability = np.zeros((self._samples - 1, m, s))

        for i in range(self._samples - 1):
            for j, variable in enumerate(variables):
                stability[i, j, 0] = np.mean(_array[:(i+1), j])
                stability[i, j, 1] = np.std(_array[:(i + 1), j])

        return stability

    @staticmethod
    def _well_spacing_adjustment(producer, typecurve, scalers):

        if typecurve is None:
            return

        p_layout, p_spacing = producer.spacing
        t_layout, t_spacing = typecurve.spacing

        if p_layout != t_layout:
            return

        if (p_spacing is None) or (p_spacing == ID_EMPTY) or (t_spacing is None) or (t_spacing == ID_EMPTY):
            return

        ratio = p_spacing / t_spacing
        scalers[0] *= ratio
        scalers[1] *= 1. / ratio ** 0.75
