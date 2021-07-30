import copy

from _ids import *
import _icons as ico
from _errors import AssembleError
from utilities import GetAttributes
from timeline import ExtractDates
import properties as pro
import simulate as sim


# ======================================================================================================================
# EntityManager Implementation.
# ======================================================================================================================
class EntityManager:
    def __init__(self):
        # concessions
        self._fields = {}
        self._blocks = {}

        # facilities
        self._platforms = {}
        self._processors = {}
        self._pipelines = {}

        # subsurface
        self._reservoirs = {}
        self._themes = {}
        self._polygons = {}
        self._producers = {}
        self._injectors = {}

        # analogues
        self._analogues = {}
        self._typecurves = {}
        self._scalings = {}

        # projects, scenarios & simulations
        self._projects = {}
        self._histories = {}
        self._scenarios = {}
        self._predictions = {}

        # correlation matrix amongst polygons {id: {id: float}}
        self._correlation_matrix = {}

        # entity management
        self._id = 0

    def AddCorrelation(self, id_):
        if self._correlation_matrix:
            for row in self._correlation_matrix.values():
                row[id_] = 0.

        self._correlation_matrix[id_] = {id_: 0. for id_ in self._polygons}
        self._correlation_matrix[id_][id_] = 1.

    def AddEntity(self, entity):
        """
        Add an entity to the EntityManager

        Parameters
        ----------
        entity : Entity
            Class Entity

        Returns
        -------
        Entity
            Class Entity
        """

        entity.SetId(self.GetNextId())

        # if the entity is a simulation holder, empty event lists and simulation results are added
        if entity.IsSimulationHolder():
            for id_ in self._scenarios:
                entity.SetEventList(id_, pro.EventList())

            for id_ in self._histories:
                entity.SetHistoryResult(id_, pro.SimulationResult())

            for id_ in self._predictions:
                entity.SetPredictionResult(id_, pro.SimulationResult())

        # if the entity is a scenario, empty event lists have to be allocated to all simulation holders
        if entity.IsScenario():
            self.PreallocateEventLists(entity.GetId())

        # if the entity is a history, empty simulation results have to be allocated to all simulation holders
        if entity.IsHistory():
            self.PreallocateHistoryResults(entity.GetId())

        # if the entity is a prediction, empty simulation results have to be allocated to all simulation holders
        if entity.IsPrediction():
            self.PreallocatePredictionResults(entity.GetId())

        # if the entity is a polygon, additional space will have to be added to the correlation matrix
        if entity.IsPolygon():
            self.AddCorrelation(entity.GetId())

        getattr(self, entity.GetAttribute())[entity.GetId()] = entity

        return entity

    def AddSummary(self, id_):
        """
        Add a new summary with a given id_ to all simulation holders

        Parameters
        ----------
        id_ : int
            Key to a dict on a SimulationResult
        """

        for entities in self.GetSimulationHolders():
            for entity in entities:
                entity.AddSummary(id_)

    def AsHistoryEntity(self, entity):
        """
        Convert a front-end Entity into a back-end entity used in history simulations

        Parameters
        ----------
        entity : Entity
            Class Entity

        Returns
        -------
        ProducerEntity or InjectorEntity or TypecurveEntity or SimulationEntity
            Class ProducerEntity or InjectorEntity or TypecurveEntity or SimulationEntity
        """

        return self.AsSimulationEntity(entity)

    def AsPredictionEntity(self, entity,  scenario_id):
        """
        Convert a front-end Entity into a back-end entity used in prediction simulations

        Parameters
        ----------
        entity : Entity
            Class Entity
        scenario_id : int
            Id of class Scenario of which a prediction is run

        Returns
        -------
        ProducerEntity or InjectorEntity or TypecurveEntity or SimulationEntity
            Class ProducerEntity or InjectorEntity or TypecurveEntity or SimulationEntity
        """

        se = self.AsSimulationEntity(entity)

        if not entity.IsTypecurve():

            se.events = entity.GetEventList(scenario_id)

            if entity.IsProducer():
                pointer = entity.GetProperties().scaling_eval.get()

                if pointer is not None:
                    scaling = self.GetEntity(*pointer)
                    se.scaling = scaling.GetProperties().evaluations

        else:
            # assemble functions:
            try:
                se.functions = [f.Assemble() for f in entity.GetProperties().functions.Get()]

            except AssembleError as e:
                raise AssembleError('Typecurve {} unable to assemble functions: {}'.format(entity.GetName(), str(e)))

            except TypeError as e:
                raise AssembleError('Typecurve {} unable to assemble functions: {}'.format(entity.GetName(), str(e)))

            # find polygon id for uncertainty modelling of typecurve
            analogue = self.GetParentByType(entity, ID_ANALOGUE)
            polygon = self.GetParentByType(analogue, ID_POLYGON)

            if polygon is not None:
                se.polygon_id = polygon.GetId()

        return se

    def AsSimulationEntity(self, entity):
        """
        Convert a front-end Entity into a back-end entity used in simulations

        Parameters
        ----------
        entity : Entity
            Class Entity

        Returns
        -------
        ProducerEntity or InjectorEntity or TypecurveEntity or SimulationEntity
            Class ProducerEntity or InjectorEntity or TypecurveEntity or SimulationEntity
        """

        if entity.IsProducer():

            se = sim.ProducerSimulation(entity.GetProperties())

        elif entity.IsInjector():

            se = sim.InjectorSimulation(entity.GetProperties())

        elif entity.IsProcessor():

            se = sim.ProcessorSimulation(entity.GetProperties())

        elif entity.IsPipeline():

            se = sim.PipelineSimulation(entity.GetProperties())

        elif entity.IsTypecurve():

            se = sim.TypecurveSimulation(entity.GetProperties())

        else:

            se = sim.SimulationEntity()

        se.name = entity.GetName()
        se.children = entity.GetChildren()
        se.attr = entity.GetAttribute()
        se.type = entity.GetType()
        se.id = entity.GetId()
        se.children_nw = entity.GetNetworkChildren()
        se.parents_nw = entity.GetNetworkParents()

        # add polygon id to wells
        if entity.IsProducer() or entity.IsInjector():
            polygon = self.GetParentByType(entity, ID_POLYGON)
            se.polygon_id = polygon.GetId()

        return se

    def CreateDuplicate(self, entity, control):
        """
        Create a duplicate of an existing entity and add it to the EntityManager.

        Parameters
        ----------
        entity : Entity
            Class Entity
        control : bool
            Is the duplicate controlled by the entity

        Returns
        -------
        Entity
            Class Entity
        """

        duplicate = self.AddEntity(entity.Duplicate())

        duplicate.ClearChildren()
        duplicate.ClearParents()
        duplicate.ClearDuplicates()
        duplicate.RemoveController()

        try:

            parent = self.GetPrimaryParent(entity)
            parent.AddChild(duplicate)

        except KeyError:

            pass  # top level hierarchical entity such as Reservoir and Field

        if control:
            entity.AddDuplicate(duplicate)

        return duplicate

    def DefaultHierarchicalProperties(self, entity, parent_type):
        """
        Default the hierarchical properties from a given entity parent type for an entity.
        Used if entity loses a parent.

        Parameters
        ----------
        entity : Entity
            Class Entity
        parent_type : int
            Entity type ID
        """

        types = entity.GetProperties().GetHierarchicalTypes()

        for type_ in types:

            property_ = entity.GetProperties().Get(type_)

            if property_.UseHierarchy():

                hierarchy_type = property_.GetHierarchyType()

                if hierarchy_type == parent_type:
                    property_.__init__(hierarchy_type, False)  # TODO: __init__ may be an issue, other way to default?

    def DeleteEntity(self, entity):
        """
        Delete an entity from the EntityManager

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        # update all existing children's hierarchical properties (now that they may have lost a parent)
        for child in self.GetChildren(entity):
            self.DefaultHierarchicalProperties(child, entity.GetType())

        # removing all pointers to the entity in other entities
        self.RemoveAsParent(entity)
        self.RemoveAsChild(entity)
        self.RemoveAsController(entity)
        self.RemoveAsDuplicate(entity)

        attr = entity.GetAttribute()
        id_ = entity.GetId()

        # if deleted entity is a polygon, the row & col will be removed from the correlation matrix
        if entity.IsPolygon():
            self.RemoveCorrelation(id_)

        # if deleted entity is a scenario the associated event_list has to be deleted from all entities
        if entity.IsScenario():
            self.RemoveEventLists(id_)

        # if deleted entity is a History the associated simulations has to be deleted from all entities
        if entity.IsHistory():
            self.RemoveHistoryResults(id_)

        # if deleted entity is a Prediction the associated simulations has to be deleted from all entities
        if entity.IsPrediction():
            self.RemovePredictionResults(id_)

        # delete entity
        del getattr(self, attr)[id_]

    def DeleteSummary(self, id_):
        """
        Used when a summary has been deleted in the VariableManager. Deletes references to it on all SimulationResults
        of all simulation holders.

        Parameters
        ----------
        id_ : int
            Key to a dictionary on a class SimulationResult
        """

        for entities in self.GetSimulationHolders():
            for entity in entities:
                entity.DeleteSummary(id_)

    def GetAnalogues(self):
        """
        Get all Analogues.

        Returns
        -------
        list
            List of class Analogues
        """

        return self._analogues.values()

    def GetChildren(self, entity, type_=None):
        """
        Get children of a given entity.

        Parameters
        ----------
        entity : Entity
            Class Entity
        type_ : int
            Key to the dictionary of children in the entity

        Returns
        -------
        list
            List of class Entity
        """

        return self.GetEntities(entity.GetChildren(type_))

    def GetCorrelationMatrix(self):
        """
        Get the correlation matrix and polygon names to be used as labels on a grid.

        Returns
        -------
        tuple
            2D list of correlations and a list of strings
        """

        matrix = [[self._correlation_matrix[id1][id2] for id2 in self._polygons] for id1 in self._polygons]
        return matrix, [p.GetName() for p in self._polygons.values()]

    def GetDuplicates(self, entity):
        """
        Get duplicates of a given entity.

        Parameters
        ----------
        entity : Entity
            Class Entity

        Returns
        -------
        list
            List of class Entity
        """

        return self.GetEntities(entity.GetDuplicates())

    def GetEntity(self, id_, attr):
        """
        Get an entity associated with the provided pointer.

        Parameters
        ----------
        id_ : int
            Key to the dict getattr(self, attr)[id]
        attr : str
            String used to access getattr(self, attr)

        Returns
        -------
        Entity
            Class Entity
        """

        return getattr(self, attr)[id_]

    def GetEntities(self, pointers):
        """
        Get multiple entities associated with the provided pointers

        Parameters
        ----------
        pointers : list
            list of tuples [(id, attr), ...]

        Returns
        -------
        list
            List of class Entity
        """

        return [self.GetEntity(*pointer) for pointer in pointers]

    def GetEntitiesByScenario(self, type_, scenario_id):
        """
        Get entities of a specific type pertaining to a specific scenario

        Parameters
        ----------
        type_ : int
            Entity type
        scenario_id : int
            Id of a scenario

        Returns
        -------
        list
            List of class Entity
        """

        return self.GetEntities(self._scenarios[scenario_id].GetChildren(type_))

    def GetFirstChild(self, parent):
        """
        Get the first child in the flattened list of the children dictionary of the parent entity

        Parameters
        ----------
        parent : Entity
            Class Entity

        Returns
        -------
        Entity
            Class Entity
        """

        cookie = 0
        return self.GetNextChild(parent, cookie)

    def GetFirstParent(self, child):
        """
        Get the first parent in the flattened list of the parent dictionary of the child entity
        Parameters
        ----------
        child : Entity
            Class Entity

        Returns
        -------
        Entity
            Class Entity
        """
        cookie = 0
        return self.GetNextParent(child, cookie)

    def GetHierarchicalProperties(self, entity, type_, properties=None):
        """
        Get the properties of a specific type for an entity by recursively going through the entity hierarchy

        Parameters
        ----------
        entity : Entity
            Class Entity
        type_ : str
            str used to access getattr(self, str) on a class Property
        properties : PropertyGroup
            Class PropertyGroup

        Returns
        -------
        Property
            Class PropertyGroup

        TODO: method probably does not have to be recursive as properties are stored in all hierarchical entities
        """

        if entity is None:
            return properties

        properties = entity.GetProperties().Get(type_)
        if properties.UseHierarchy():
            hierarchy = self.GetParentByType(entity, properties.GetHierarchyType())
            properties = self.GetHierarchicalProperties(hierarchy, type_, properties)

        return properties

    def GetHistoryCase(self, history):
        """
        Extracts everything relevant for a simulation and packages it in a back-end class which is used for
        simulating history

        Parameters
        ----------
        history : History
            Class History

        Returns
        -------
        HistoryCase:
            Class HistoryCase
        """

        # extracting simulation properties
        properties = history.GetProperties()

        case = sim.HistoryCase(properties)

        producers = {e.GetId(): self.AsHistoryEntity(e) for e in self.GetChildren(history, ID_PRODUCER)}
        injectors = {e.GetId(): self.AsHistoryEntity(e) for e in self.GetChildren(history, ID_INJECTOR)}
        polygons = {e.GetId(): self.AsHistoryEntity(e) for e in self._polygons.values()}
        case.SetEntities(producers, injectors, polygons=polygons)

        # find start and end dates
        prod = [p.history for p in producers.values() if p.history is not None]
        inj = [i.history for i in injectors.values() if i.history is not None]
        start, end = ExtractDates(prod + inj)
        case.SetDuration(start, end)
        properties.duration.Set(start, end)  # saved for access in Prediction

        return case

    def GetNextChild(self, parent, cookie):
        """
        Get the next child in the flattened list of the children dictionary of the parent entity

        Parameters
        ----------
        parent : Entity
            Class Entity
        cookie : int
            Increment keeping track of how the list has been progressed

        Returns
        -------
        Entity
            Class Entity
        """

        children = self.GetChildren(parent)
        if cookie < len(children):
            return children[cookie], cookie + 1
        else:
            return None, cookie

    def GetNextParent(self, child, cookie):
        """
        Get the next parent in the flattened list of the parent dictionary of the child entity

        Parameters
        ----------
        child : Entity
            Class Entity
        cookie : int
            Increment keeping track of how the list has been progressed

        Returns
        -------
        Entity
            Class Entity
        """

        parents = self.GetParents(child)

        if cookie < len(parents):
            return parents[cookie], cookie + 1
        else:
            return None, 0

    def GetNextId(self):
        """
        Get an id that is guaranteed to be unique in the dictionary

        Returns
        -------
        int
            Key guaranteed to be unique in the dictionary
        """

        id_ = self._id
        self._id += 1

        return id_

    def GetParents(self, entity):
        """
        Get parents of a given entity

        Parameters
        ----------
        entity : Entity
            Class Entity

        Returns
        -------
        list
            List of class Entity
        """
        return self.GetEntities(entity.GetParents())

    def GetParentByType(self, entity, type_):
        """
        Get parent of a given type for a given entity

        Parameters
        ----------
        entity : Entity
            Class Entity
        type_ : int
            Key to the dictionary of parents in the entity

        Returns
        -------
        Entity
            Class Entity
        """

        pointer = entity.GetParents(type_)

        if pointer is not None:

            return self.GetEntity(*pointer)

    def GetPlatforms(self):
        """
        Get all Platforms

        Returns
        -------
        list
            List of Platform
        """

        return self._platforms

    def GetPolygons(self):
        """
        Get all Polygons

        Returns
        -------
        list
            List of Polygon
        """

        return self._polygons

    def GetPredictionCase(self, prediction):
        """
        Extracts everything relevant for a simulation and packages it in a back-end class which is used for
        simulating prediction

        Parameters
        ----------
        prediction : Prediction
            Class Prediction

        Returns
        -------
        PredictionCase
            Class PredictionCase
        """

        # extracting simulation properties
        properties = prediction.GetProperties()

        case = sim.PredictionCase(properties)

        scenario = self.GetParentByType(prediction, ID_SCENARIO)
        s_id = scenario.GetId()

        # gather entities
        producers = {e.GetId(): self.AsPredictionEntity(e, s_id) for e in self.GetEntitiesByScenario(ID_PRODUCER, s_id)}
        injectors = {e.GetId(): self.AsPredictionEntity(e, s_id) for e in self.GetEntitiesByScenario(ID_INJECTOR, s_id)}
        processors = {e.GetId(): self.AsPredictionEntity(e, s_id) for e in self.GetEntitiesByScenario(ID_PROCESSOR, s_id)}
        pipelines = {e.GetId(): self.AsPredictionEntity(e, s_id) for e in self.GetEntitiesByScenario(ID_PIPELINE, s_id)}
        polygons = {e.GetId(): self.AsPredictionEntity(e, s_id) for e in self._polygons.values()}
        typecurves = {e.GetId(): self.AsPredictionEntity(e, s_id) for e in self._typecurves.values()}
        case.SetEntities(producers, injectors, processors, pipelines, polygons, typecurves)

        # assigning functions to producers
        for p in producers.values():
            p.AssignFunctions(typecurves)

        # assign start/end for prediction
        start, end = scenario.GetProperties().duration.get()

        if start >= end:
            raise ValueError('End of prediction must be greater than start of prediction')

        # if a history is associated with the prediction, start prediction at end of history
        pointer = properties.history.Get()[0]
        if pointer is not None:
            history = self.GetEntity(*pointer)
            _, history_end = history.GetProperties().duration.Get()

            if history_end is not None:
                start = history_end

        case.SetDuration(start, end)

        return case

    def GetPrimaryParent(self, entity):
        """
        Get the primary parent of an entity

        Parameters
        ----------
        entity : Entity
            Class Entity

        Returns
        -------
        Entity
            Class Entity
        """

        return self.GetParentByType(entity, entity.GetPrimaryParent())

    def GetProjects(self):
        """
        Get all Projects

        Returns
        -------
        list
            List of Project
        """

        return self._projects

    def GetReservoirs(self):
        """
        Get all Reservoirs

        Returns
        -------
        list
            List of Reservoir
        """

        return self._reservoirs

    def GetScenarios(self):
        """
        Get all Scenarios

        Returns
        -------
        list
            List of Scenario
        """

        return self._scenarios

    def GetSimulationHolders(self):
        """
        Get all entities which are simulation holders

        Returns
        -------
        list
            List of lists of entities
        """

        exclude = ('_projects', '_histories', '_scenarios', '_predictions', '_analogues', '_typecurves',
                   '_scalings', '_correlation_matrix', '_id')

        return (a.values() for a in GetAttributes(self, exclude=exclude, attr_only=True))

    def GetThemes(self):
        """
        Get all Themes

        Returns
        -------
        list
            List of Themes
        """

        return self._themes

    def MergeDerivedProperties(self, entity, type_):
        """
        Propagates through the entity hierarchy starting at a given entity. Merges all derived properties of the
        hierarchical parents of the entity

        Parameters
        ----------
        entity : Entity
            Class Entity
        type_ : str
            String used to access getattr(self, str) on a Property
        """

        parent, cookie = self.GetFirstParent(entity)

        while parent:

            if parent.HasProperty(type_):
                property_ = parent.GetProperties().Get(type_)

                if property_.UseDerived():

                    children = [c for c in self.GetChildren(parent) if c.HasProperty(type_)]
                    property_.Merge(children)
                    self.MergeDerivedProperties(parent, type_)

            parent, cookie = self.GetNextParent(parent, cookie)

    def PreallocateEventLists(self, id_):
        """
        Preallocate event lists on all simulation holders for a scenario with the given id

        Parameters
        ----------
        id_ : int
            Scenario id
        """

        for entities in self.GetSimulationHolders():  # all event_list holders are also simulation holders
            for entity in entities:
                entity.SetEventList(id_, pro.EventList())

    def PreallocateHistoryResults(self, id_):
        """
        Preallocate simulation results on all simulation holders for a history with the given id

        Parameters
        ----------
        id_ : int
            History id
        """

        for entities in self.GetSimulationHolders():
            for entity in entities:
                entity.SetHistoryResult(id_, pro.SimulationResult())

    def PreallocatePredictionResults(self, id_):
        """
        Preallocate simulation results on all simulation holders for a prediction with the given id

        Parameters
        ----------
        id_ : int
            Prediction id
        """

        for entities in self.GetSimulationHolders():
            for entity in entities:
                entity.SetPredictionResult(id_, pro.SimulationResult())

    def PropagateHierarchicalProperty(self, entity, type_):
        """
        Propagate down through the hierarchy, assigning hierarchical properties to all entities which have requested it.

        Parameters
        ----------
        entity : Entity
            Class Entity
        type_ : int
            Entity type-id
        """

        properties = entity.GetProperties().Get(type_)
        child, cookie = self.GetFirstChild(entity)

        while child:
            if child.HasProperty(type_):
                c_prop = child.GetProperties().Get(type_)
                if c_prop.UseHierarchy() and c_prop.FromHierarchyType(entity.GetType()):
                    c_prop.CopyFrom(properties)

                self.PropagateHierarchicalProperty(child, type_)

            child, cookie = self.GetNextChild(entity, cookie)

    def PropagateSimulationHierarchy(self, entity, simulation, case, summaries, settings, children_types=()):
        """
        Transfer a simulation case (history or prediction) and propagate the result through the entity hierarchy.

        Parameters
        ----------
        entity : Entity
            The entity for which to calculate a simulation profile.
        simulation : History() or Prediction()
            The simulation entity from the entity_mgr.
        case : HistoryCase or PredictionCase
            Simulation case with backend entities.
        summaries: list
            List of class Summary
        settings: Settings
            The project settings
        children_types : tuple
            Tuple of entity ids for which to merge profiles and summaries from. Empty for all types.
        """

        entity_result = entity.GetSimulationResult(simulation)
        entity_result.InitializeSamples(case.GetSamples(), case.GetDateline(), summaries)

        child, cookie = self.GetFirstChild(entity)

        while child:
            result = child.GetSimulationResult(simulation)
            profiles = result.GetProfiles()
            summaries_ = result.GetSummaries()

            # first level of hierarchy with samples reached
            if not result.IsFinalized():
                profiles, summaries_ = self.PropagateSimulationHierarchy(child, simulation, case, summaries, settings,
                                                                         children_types=children_types)

            # merge profiles if child type is in the list of approved children types
            if (not children_types) or (child.GetType() in children_types):
                entity_result.MergeProfile(profiles)
                entity_result.MergeSummary(summaries_)

            child, cookie = self.GetNextChild(entity, cookie)

        entity_result.FinalizeSamples(case.KeepAllProfiles(), settings)

        return entity_result.GetProfiles(), entity_result.GetSummaries()

    def RemoveAsChild(self, entity):
        """
        Remove entity as a child from all parents

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        for parent in self.GetParents(entity):
            parent.RemoveChild(entity)

    def RemoveAsController(self, entity):
        """
        Remove entity as a controller from all duplicates

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        for duplicate in self.GetDuplicates(entity):
            duplicate.RemoveController()

    def RemoveAsDuplicate(self, entity):
        """
        Remove entity as a duplicate from its controller

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        pointer = entity.GetController()

        if pointer is not None:
            controller = self.GetEntity(*entity.GetController())
            controller.RemoveDuplicate(entity)

    def RemoveAsParent(self, entity):
        """
        Remove entity as a parent from all children

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        for child in self.GetChildren(entity):
            child.RemoveParent(entity)

    def RemoveCorrelation(self, id_):
        """
        Delete the part of the correlation matrix associated with the provided id

        Parameters
        ----------
        id_ : int
            Polygon id
        """

        for row in self._correlation_matrix.values():
            del row[id_]

        del self._correlation_matrix[id_]

    def RemoveEventLists(self, id_):
        """
        Remove an event list from all simulation holders

        Parameters
        ----------
        id_ : int
            Scenario id
        """

        for entities in self.GetSimulationHolders():
            for entity in entities:
                entity.RemoveEventList(id_)

    def RemoveHistoryResults(self, id_):
        """
        Remove a history simulation result from all simulation holders

        Parameters
        ----------
        id_ : int
            History id
        """

        for entities in self.GetSimulationHolders():
            for entity in entities:
                entity.RemoveHistoryResult(id_)

    def RemovePredictionResults(self, id_):
        """
        Remove a prediction simulation result from all simulation holders

        Parameters
        ----------
        id_ : int
            Prediction id
        """

        for entities in self.GetSimulationHolders():
            for entity in entities:
                entity.RemovePredictionResult(id_)

    def ReplaceChildren(self, entity, children):
        """
        Replace the current children pointers of the entity with new pointers

        Parameters
        ----------
        entity : Entity
            Class Entity
        children : list
            List of Entities
        """

        # update all existing children's hierarchical properties (now that they may have lost a parent)
        for child in self.GetChildren(entity):
            self.DefaultHierarchicalProperties(child, entity.GetType())

        self.RemoveAsParent(entity)

        # adding the new children
        entity.ClearChildren()
        for child in children:
            entity.AddChild(child)

    def ReplacePrimaryParent(self, entity, parent):
        """
        Replace the primary parent of the entity with a new parent.

        Parameters
        ----------
        entity : Entity
            Class Entity
        parent : Entity
            Class Entity replacing the previous parent
        """

        # removing the existing link between the entity and the primary parent
        old_parent = self.GetPrimaryParent(entity)
        old_parent.RemoveChild(entity)
        entity.RemoveParent(old_parent)

        # add the entity as a child to the new parent
        parent.AddChild(entity)

    def SeverControl(self, entity):
        """
        Sever the control between a duplicated entity and its controller.

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        self.RemoveAsDuplicate(entity)
        entity.RemoveController()

    def SetCorrelationMatrix(self, matrix):
        """
        Set correlation matrix

        Parameters
        ----------
        matrix : list
            2D list of correlation coefficients between polygons
        """

        for i, id1 in enumerate(self._polygons):
            for j, id2 in enumerate(self._polygons):
                self._correlation_matrix[id1][id2] = matrix[i][j]

    def TransferSimulationCase(self, simulation, case, summaries, settings):
        """
        Transfer a simulation case (history or prediction) and propagate the result through the entity hierarchy.

        Parameters
        ----------
        simulation : Entity
            Class History or Prediction
        case : HistoryCase or PredictionCase
            Simulation case with backend entities.
        summaries: list
            List of class Summary
        settings: Settings
            The project settings
        """

        # prior to transferring simulation case, all previously held SimulationResults from the simulation with this
        # id has to be overwritten by pre-allocation
        if simulation.IsHistory():
            self.PreallocateHistoryResults(simulation.GetId())

        elif simulation.IsPrediction():
            self.PreallocatePredictionResults(simulation.GetId())

        # producers and injectors are handled during simulation, so transfer directly
        for well in case.GetWells():
            self.UpdateSimulationResult(well, simulation)

        # processors and pipelines are handled during simulation, so transfer directly
        for equipment in case.GetEquipment():
            self.UpdateSimulationResult(equipment, simulation)

        # transfer to remaining entities
        # platform can be handled as stand-alone (only dependent on wells)
        for platform in self._platforms.values():
            self.PropagateSimulationHierarchy(platform, simulation, case, summaries, settings,
                                              children_types=(ID_PRODUCER, ID_INJECTOR))

        # reservoirs have to be run prior to field and block which require polygons
        for reservoir in self._reservoirs.values():
            self.PropagateSimulationHierarchy(reservoir, simulation, case, summaries, settings)

        for field in self._fields.values():
            self.PropagateSimulationHierarchy(field, simulation, case, summaries, settings)

        for block in self._blocks.values():
            self.PropagateSimulationHierarchy(block, simulation, case, summaries, settings)

        # clean up samples from simulation profiles to reduce memory requirements
        for entities in self.GetSimulationHolders():
            for entity in entities:
                result = entity.GetSimulationResult(simulation)
                result.ClearSamples()

    def UpdateControlledProperties(self, entity):
        """
        Updates the properties of the entity by replacing them with the controlling entities properties

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        pointer = entity.GetController()

        if pointer is not None:
            controller = self.GetEntity(*entity.GetController())
            entity.GetProperties().DuplicateFrom(controller.GetProperties())

    def UpdateDerivedProperties(self, entity):
        """
        Updates the derived properties of an entity and propagates it through the hierarchy.

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        types = entity.GetProperties().GetDerivedTypes()
        for type_ in types:
            # merging the derived properties of the entity itself
            property_ = entity.GetProperties().Get(type_)
            if property_.UseDerived():
                children = [c for c in self.GetChildren(entity) if c.HasProperty(type_)]
                property_.Merge(children)

            # propagating up the hierarchy
            self.MergeDerivedProperties(entity, type_)

    def UpdateDuplicatedProperties(self, entity):
        """
        Updates the properties in all duplicates controlled by the entity.

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        for duplicate in self.GetDuplicates(entity):
            duplicate.GetProperties().DuplicateFrom(entity.GetProperties())
            self.UpdateHierarchicalProperties(duplicate)

    def UpdateEventList(self, pointer, event_list, id_=None):
        """
        Updates an entity with a given event list for a scenario of the provided id.

        Parameters
        ----------
        pointer : tuple
            Pointer to an entity (id, attr)
        event_list : EventList
            Class EventList
        id_ : int
            Scenario id
        """

        entity = self.GetEntity(*pointer)
        entity.SetEventList(id_, event_list)

    def UpdateHierarchicalProperties(self, entity):
        """
        Updates the hierarchical properties of an entity and propagates it down through the hierarchy.

        Parameters
        ----------
        entity : Entity
            Class Entity
        """

        types = entity.GetProperties().GetHierarchicalTypes()

        for type_ in types:
            # if use hierarchical, go up the hierarchy to find the property
            if entity.GetProperties().Get(type_).UseHierarchy():
                # update properties with the hierarchical properties
                properties = self.GetHierarchicalProperties(entity, type_)
                entity.GetProperties().Get(type_).CopyFrom(properties)

            # propagate the property down the hierarchy
            self.PropagateHierarchicalProperty(entity, type_)

    def UpdateSimulationResult(self, simulation_entity, simulation):
        """
        Updates the simulation result of an entity.

        Parameters
        ----------
        simulation_entity : SimulationEntity
            Back-end class SimulationEntity
        simulation : Entity
            Class History or Prediction
        """

        entity = self.GetEntity(*simulation_entity.GetPointer())
        entity.SetSimulationResult(simulation, simulation_entity.GetSimulation())


# ======================================================================================================================
# Entity Implementation.
# ======================================================================================================================
class Entity:
    def __init__(self, name=None):
        #  information
        self._name = name        # non-unique name shown in labels
        self._properties = None  # class <Entity>Properties, collection of all properties
        self._event_lists = {}   # dict, {scenario_id: EventList}, 1 per scenario in the EntityManager
        self._histories = {}     # dict, {history_id: SimulationResult}, 1 per history in EntityManager
        self._predictions = {}   # dict, {prediction_id: SimulationResult}, 1 per prediction in EntityManager
        self._cultural = None    # class Cultural, holds coordinates used in map chart

        # entity management
        self._id = None                 # int, unique index in entity dict in EntityManager
        self._attr = None               # str, input to getattr(EntityManager, '_<entity type name>')
        self._type = None               # int, used to test against
        self._family_type = None        # int, used to test against
        self._children = {}             # dict, {type: [(id, attr), ...]} references to EntityManager
        self._parents = {}              # dict, {type: [(id, attr), ...], ...} references to EntityManager
        self._controller = None         # tuple, (id, attr) reference to EntityManager, attr = self._attr
        self._duplicates = []           # list, [(id, attr), ...] references to EntityManager, attr=self._attr
        self._multiple_parents = {}     # dict, {type: bool/int} True/False or number of allowed parents of type
        self._primary_parent = None     # int, id of the entity that self will be a child of in the object_menu
        self._primary_child = None      # int, id of the family_type of entities that are children in the object_menu
        self._parent_transfer = True    # bool, allow parent transfer in drag & drop and copy
        self._allow_control = True      # bool, allow an entity to be controlled after duplication
        self._simulation_holder = True  # bool, test for whether entity is a simulation holder

        # visual
        self._image_key = None          # used for dictionary look up in tree ctrl image lists
        self._image = None              # PyEmbeddedImage

    def AddChild(self, child):
        """
        Add a pointer to another entity in the EntityManager to the list of children

        Parameters
        ----------
        child : Entity
            class Entity used to extract pointer from.
        """

        child.AddParent(self)
        self._children[child.GetType()].append(child.GetPointer())

    def AddController(self, controller):
        """
        Add a pointer to another entity in the EntityManager as the controller

        Parameters
        ----------
        controller : Entity
            class Entity used to extract pointer from.
        """

        self._controller = (controller.GetId(), self._attr)

    def AddDuplicate(self, duplicate):
        """
        Add a pointer to another entity in the EntityManager to the list of duplicates

        Parameters
        ----------
        duplicate : Entity
            class Entity used to extract pointer from.
        """

        duplicate.AddController(self)
        self._duplicates.append((duplicate.GetId(), self._attr))

    def AddParent(self, parent):
        """
        Add a pointer to another entity in the EntityManager to the list of parents.

        Parameters
        ----------
        parent : Entity
            class Entity used to extract pointer from.
        """

        self._parents[parent.GetType()].append(parent.GetPointer())

    def AddSummary(self, id_):
        """
        Add summary to all SimulationResults.

        Parameters
        ----------
        id_ : int
            Id of the summary
        """

        for history in self._histories.values():
            history.AddSummary(id_)

        for prediction in self._predictions.values():
            prediction.AddSummary(id_)

    def AllowControl(self):
        """
        Test whether the entity allows to be controlled after duplication.

        Returns
        -------
        bool
        """

        return self._allow_control

    def AllowMultipleParents(self, type_):
        """
        Test whether the entity allows multiple parents of the provided type.

        Parameters
        ----------
        type_ : int
            Entity id

        Returns
        -------
        bool
        """

        return self._multiple_parents[type_]

    def AllowParentTransfer(self):
        """
        Test whether the entity allows parent transfer

        Returns
        -------
        bool
            bool
        """

        return self._parent_transfer

    def ClearChildren(self):
        """
        Clear the children of the entity
        """

        for type_ in self._children:
            self._children[type_] = []

    def ClearDuplicates(self):
        """
        Clear the duplicates of the entity
        """

        self._duplicates = []

    def ClearParents(self):
        """
        Clear the parents of the entity
        """

        for type_ in self._parents:
            self._parents[type_] = []

    def Copy(self):
        """
        Create a deep copy of the entity

        Returns
        -------
        Entity
            A copy of the entity
        """

        return copy.deepcopy(self)

    def DeleteSummary(self, id_):
        """
        Called when a summary in the VariableManager is deleted. This removes the summary from all SimulationResults.

        Parameters
        ----------
        id_ : int
            Index to a summary dictionary in a SimulationResult
        """

        for history in self._histories.values():
            history.DeleteSummary(id_)

        for prediction in self._predictions.values():
            prediction.DeleteSummary(id_)

    def Duplicate(self):
        duplicate = self.Copy()

        # ensure properties which should not be duplicated are defaulted
        duplicate.GetProperties().InitialDuplication()

        return duplicate

    def GetAttribute(self):
        """
        Get the attribute of the entity

        Returns
        -------
        attr : str
            Str used to access attribute in EntityManager via getattr(self, attr)
        """

        return self._attr

    def GetBitmap(self):
        """
        Get the entity bitmap

        Returns
        -------
        wx.Bitmap
            Bitmap displayed on various wxPython widgets
        """

        return self._image.GetBitmap()

    def GetChildren(self, type_=None):
        """
        Return a list of children pointers associated to the entity

        Parameters
        ----------
        type_ : int
            Key to the dictionary self._children

        Returns
        -------
        list
            List of children pointers
        """

        if type_ is not None:

            try:
                return self._children[type_]

            except KeyError:
                raise KeyError('{} does not allow that type of children'.format(self._attr[1:]))

        else:
            # flatten dict and return all children as tuples
            return [c for lc in self._children.values() for c in lc]

    def GetController(self):
        """
        Get a pointer to the entity's controlling entity

        Returns
        -------
        tuple
            (id, attr) pointer to the controlling entity
        """

        return self._controller

    def GetCultural(self):
        """
        Get cultural

        Returns
        -------
        Cultural
            Class Cultural
        """

        return self._properties.cultural.GetCultural()

    def GetDuplicates(self):
        """
        Get a list of pointers to the entity's duplicates

        Returns
        -------
        list
            List of [(id, attr), ...] pointers to the duplicates of the entity
        """

        return self._duplicates

    def GetEventList(self, id_):
        """
        Get an EventList

        Parameters
        ----------
        id_ : int
            Key to the dict self._event_lists

        Returns
        -------
        EventList
            EventList used in simulations
        """

        return self._event_lists[id_]

    def GetEventLists(self):
        """
        Get all event lists.

        Returns
        -------
        list
            List of all event lists
        """

        return self._event_lists.values()

    def GetFamilyType(self):
        """
        Get family type.

        Returns
        -------
        int
            Family type id
        """

        return self._family_type

    def GetHistory(self, variable=None):
        """
        Get the historical production/injection data associated to this entity

        Parameters
        ----------
        variable : str
            Str used to access getattr(self, str) in a Profile class

        Returns
        -------
        array_like or Profile
            Returns a Profile or an array if variable is not None
        """

        return self._properties.history.GetProfile(variable)

    def GetHistoryResult(self, id_):
        """
        Get the SimulationResult associated to a given History

        Parameters
        ----------
        id_ : int
            Key to dict self._histories

        Returns
        -------
        SimulationResult
            SimulationResult of the history with the passed id
        """

        return self._histories[id_]

    def GetHistoryResults(self):
        """
        Get all history results

        Returns
        -------
        list
            List of class SimulationResult
        """

        return self._histories.values()

    def GetIcon(self):
        """
        Get the entity bitmap

        Returns
        -------
        wx.Icon
            Icon displayed on wxPython frames
        """

        return self._image.GetIcon()

    def GetId(self):
        """
        Get id

        Returns
        -------
        int
            Id of the entity
        """

        return self._id

    def GetImage(self):
        """
        Get the PyEmbeddedImage object

        Returns
        -------
        str
            String which can be used as input to a wx.Bitmap(path)
        """

        return self._image

    def GetImageKey(self):
        """
        Get image key

        Returns
        -------
        str
            Key in a dict on the object_menu page containing indices to a wxPython ImageList
        """

        return self._image_key

    def GetName(self):
        """
        Get name

        Returns
        -------
        str
            Name of the entity displayed on GUI
        """

        return self._name

    def GetNetworkChildren(self):
        """
        Get the children related to the surface-network of the entity

        Returns
        -------
        list
            List of pointer (id, attr)
        """

        return [(id_, attr) for key, list_ in self._children.items() for id_, attr in list_
                if key in (ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR)]

    def GetNetworkParents(self):
        """
        Get the parents related to the surface-network of the entity

        Returns
        -------
        list
            List of pointer (id, attr)
        """

        return [(id_, attr) for key, list_ in self._parents.items() for id_, attr in list_
                if key in (ID_PROCESSOR, ID_PIPELINE, ID_PRODUCER, ID_INJECTOR)]

    def GetParents(self, type_=None):
        """
        Get the parents of a specific type associated to the entity

        Parameters
        ----------
        type_ : int
            Entity type

        Returns
        -------
        tuple
            Pointer (id, attr)
        """

        if type_ is not None:

            try:

                parents = self._parents[type_]

                if self._multiple_parents[type_]:

                    return parents

                else:

                    if parents:

                        return parents[0]

                    else:

                        return None

            except KeyError:

                raise KeyError('{} does not allow that type of parents'.format(self._attr[1:]))

        else:

            return [p for lp in self._parents.values() for p in lp]

    def GetPointer(self):
        """
        Get pointer to the entity which can be used in EntityManager

        Returns
        -------
        tuple
            Tuple with (id, attr) which can access the entity via getattr(self, attr)[id_] in the EntityManager
        """

        return self._id, self._attr

    def GetPrimaryParent(self):
        """
        Get primary parent type

        Returns
        -------
        int
            Type of the primary parent
        """

        return self._primary_parent

    def GetPrimaryChild(self):
        """
        Get primary child family type

        Returns
        -------
        int
            Family type of the primary child
        """

        return self._primary_child

    def GetProperties(self):
        """
        Get properties

        Returns
        -------
        Properties
            Class Properties unique to a specific type of entity
        """

        return self._properties

    def GetPredictionResult(self, id_):
        """
        Get the SimulationResult associated to a given prediction

        Parameters
        ----------
        id_ : int
            Key to dict self._predictions

        Returns
        -------
        SimulationResult
            SimulationResult of the prediction with the passed id
        """

        return self._predictions[id_]

    def GetPredictionResults(self):
        """
        Get all prediction results

        Returns
        -------
        list
            List of class SimulationResult
        """

        return self._predictions.values()

    def GetSimulationProfile(self, simulation, variable):
        """
        Get a specific profile from a class Profile on a SimulationResult.

        Parameters
        ----------
        simulation : Entity
            Class History or Prediction
        variable : str
            Str used as input to Profile.Get(str)

        Returns
        -------
        array_like
            Numpy array of simulated production/injection profile
        """

        return self.GetSimulationResult(simulation).GetProfile(variable)

    def GetSimulationResult(self, simulation):
        """
        Get simulation result

        Parameters
        ----------
        simulation : Entity
            Class History or Prediction

        Returns
        -------
        SimulationResult
            SimulationResult from a history or prediction simulation
        """

        if simulation.IsHistory():
            return self.GetHistoryResult(simulation.GetId())
        else:  # Prediction
            return self.GetPredictionResult(simulation.GetId())

    def GetSimulationSummary(self, simulation, variable):
        """
        Get a specific summary from a dict of summaries on a SimulationResult.

        Parameters
        ----------
        simulation : Entity
            Class History or Prediction
        variable : str
            Str used as input to Profile.Get(str)

        Returns
        -------
        float
            Summary value
        """

        return self.GetSimulationResult(simulation).GetSummary(variable)

    def GetType(self):
        """
        Get type

        Returns
        -------
        int
            Id of the entity type
        """

        return self._type

    def HasParent(self, type_):
        """
        Test if the entity has a parent of a given type

        Parameters
        ----------
        type_ : int
            Type of the parent

        Returns
        -------
        bool
            bool
        """

        try:

            if self._parents[type_]:

                return True

        except KeyError:

            return False

        return False

    def HasProperty(self, type_):
        """
        Test if the entity's properties contain a specific type of properties

        Parameters
        ----------
        type_ : str
            Str used to test a class Properties for whether it has a given attribute

        Returns
        -------
        bool
            bool
        """

        return self._properties.HasProperty(type_)

    def IsAnalogue(self):
        """
        Test if entity is an Analogue

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_ANALOGUE)

    def IsBlock(self):
        """
        Test if entity is a Block

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_BLOCK)

    def IsChildOf(self, parent_id, parent_attr):
        """
        Test if an entity with the provided id and attribute is a parent of self

        Parameters
        ----------
        parent_id : int
            Entity id
        parent_attr : str
            Entity attribute

        Returns
        -------
        bool
            bool
        """

        for (id_, attr) in self.GetParents():
            if (id_ == parent_id) and (attr == parent_attr):
                return True

        return False

    def IsControlling(self):
        """
        Test if the entity is controlling other entities

        Returns
        -------
        bool
            bool
        """

        return len(self._duplicates)

    def IsControlled(self):
        """
        Test if the entity is controlled by another entity

        Returns
        -------
        bool
            bool
        """

        return self._controller is not None

    def IsFamilyType(self, type_):
        """
        Test if the entity is of a provided family type

        Parameters
        ----------
        type_ : int
            Entity family type id to test against

        Returns
        -------
        bool
            bool
        """

        return self._family_type == type_

    def IsField(self):
        """
        Test if entity is a Field

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_FIELD)

    def IsHistory(self):
        """
        Test if entity is a History

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_HISTORY)

    def IsInjector(self):
        """
        Test if entity is an Injector

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_INJECTOR)

    def IsParentOf(self, child_id, child_attr):
        """
        Test if an entity with the provided id and attribute is a child of self

        Parameters
        ----------
        child_id : int
            Entity id
        child_attr : str
            Entity attribute

        Returns
        -------
        bool
            bool
        """

        for (id_, attr) in self.GetChildren():
            if (id_ == child_id) and (attr == child_attr):
                return True

        return False

    def IsPipeline(self):
        """
        Test if entity is a pipeline

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_PIPELINE)

    def IsPolygon(self):
        """
        Test if entity is a Polygon

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_POLYGON)

    def IsPrediction(self):
        """
        Test if entity is a Polygon

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_PREDICTION)

    def IsProcessor(self):
        """
        Test if entity is a processor

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_PROCESSOR)

    def IsProducer(self):
        """
        Test if entity is a Producer

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_PRODUCER)

    def IsProject(self):
        """
        Test if entity is a Project

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_PROJECT)

    def IsReservoir(self):
        """
        Test if entity is a Reservoir

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_RESERVOIR)

    def IsScenario(self):
        """
        Test if entity is a Scenario

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_SCENARIO)

    def IsSimulationHolder(self):
        """
        Test if the entity holds simulation, both histories and predictions

        Returns
        -------
        bool
            bool
        """

        return self._simulation_holder

    def IsTheme(self):
        """
        Test if entity is a Theme

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_THEME)

    def IsType(self, type_):
        """
        Test if the entity is of a provided type

        Parameters
        ----------
        type_ : int
            Entity type id to test against

        Returns
        -------
        bool
            bool
        """

        return self._type == type_

    def IsTypecurve(self):
        """
        Test if entity is a Typecurve

        Returns
        -------
        bool
            bool
        """

        return self.IsType(ID_TYPECURVE)

    def RemoveChild(self, child):
        """
        Remove a given child from the dict of children

        Parameters
        ----------
        child : Entity
            Class Entity
        """

        type_ = child.GetType()

        for i, (id_, _) in enumerate(self._children[type_]):
            if id_ == child.GetId():
                del self._children[type_][i]
                break

    def RemoveController(self):
        """
        Remove the controller
        """

        self._controller = None

    def RemoveDuplicate(self, duplicate):
        """
        Remove a given duplicate from the dict of duplicates

        Parameters
        ----------
        duplicate : Entity
            A class Entity
        """

        for i, (id_, _) in enumerate(self._duplicates):
            if id_ == duplicate.GetId():
                del self._duplicates[i]
                break

    def RemoveParent(self, parent):
        """
        Remove a given parent from the dict of parents

        Parameters
        ----------
        parent : Entity
            A class Entity
        """

        type_ = parent.GetType()

        for i, (id_, _) in enumerate(self._parents[type_]):
            if id_ == parent.GetId():
                del self._parents[type_][i]
                break

    def RemoveEventList(self, id_):
        """
        Remove an event list from the dict of event lists

        Parameters
        ----------
        id_ : int
            Key to the dict self._event_lists
        """

        del self._event_lists[id_]

    def RemoveHistoryResult(self, id_):
        """
        Remove a result from the dict of history result

        Parameters
        ----------
        id_ : int
            Key to the dict self._histories
        """

        del self._histories[id_]

    def RemovePredictionResult(self, id_):
        """
        Remove a result from the dict of prediction result

        Parameters
        ----------
        id_ : int
            Key to the dict self._predictions
        """

        del self._predictions[id_]

    def ReplaceInformation(self, entity):
        """
        Used when updating information of an entity from an EntityFrame

        Parameters
        ----------
        entity : Entity
            Temporarily created entity holding properties set on the EntityFrame
        """

        self._name = copy.deepcopy(entity.GetName())
        self._properties = copy.deepcopy(entity.GetProperties())

    def SetEventList(self, id_, event_list):
        """
        Set an event list

        Parameters
        ----------
        id_ : int
            Id of a Scenario
        event_list : EventList
            Class EventList containing events used in simulations
        """

        self._event_lists[id_] = event_list

    def SetHistoryResult(self, id_, result):
        """
        Set a history result.

        Parameters
        ----------
        id_ : int
            Id of a History or a Prediction
        result : SimulationResult
            Class SimulationResult
        """

        self._histories[id_] = result

    def SetSimulationResult(self, simulation, result):
        """
        Set a simulation result.

        Parameters
        ----------
        simulation : Entity
            Class History or Prediction
        result : SimulationResult
            Class SimulationResult
        """

        if simulation.IsHistory():
            return self.SetHistoryResult(simulation.GetId(), result)
        else:  # Prediction
            return self.SetPredictionResult(simulation.GetId(), result)

    def SetPredictionResult(self, id_, result):
        """
        Set prediction result.

        Parameters
        ----------
        id_ : int
            Key to self._predictions
        result : SimulationResult
            Class SimulationResult
        """

        self._predictions[id_] = result

    def SetId(self, id_):
        """
        Set id

        Parameters
        ----------
        id_ : int
            Entity id
        """

        self._id = id_

    def SetImage(self, id_=None):
        """
        Set image_key and bitmap_str (in subclassed versions).

        Parameters
        ----------
        id_ : int
            Id to test against in subclassed versions
        """

        self._image_key = self._type

    def SetName(self, name):
        """
        Set name

        Parameters
        ----------
        name : str
            Name of the entity
        """

        self._name = name

    def SetProperties(self, properties):
        """
        Set properties

        Parameters
        ----------
        properties : Properties
            Class of specific EntityProperties
        """

        self._properties = properties


# ======================================================================================================================
# Specific sub-classes of Entity
# ======================================================================================================================
class Project(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.ProjectProperties()

        # children: scenarios
        self._attr = '_projects'
        self._type = ID_PROJECT
        self._family_type = self._type
        self._children = {ID_HISTORY: [], ID_SCENARIO: []}
        self._primary_parent = ID_SIMULATIONS
        self._primary_child = ID_CASE_FAMILY
        self._allow_control = False
        self._simulation_holder = False

        self._image = ico.project_16x16


class History(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.HistoryProperties()

        # children: themes
        self._attr = '_histories'
        self._type = ID_HISTORY
        self._family_type = ID_CASE_FAMILY
        self._children = {ID_PRODUCER: [], ID_INJECTOR: []}
        self._parents = {ID_PROJECT: []}
        self._multiple_parents = {ID_PROJECT: False}
        self._primary_parent = ID_PROJECT
        self._allow_control = False
        self._simulation_holder = False

        self._image = ico.history_match_16x16


class Scenario(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.ScenarioProperties()

        self._attr = '_scenarios'
        self._type = ID_SCENARIO
        self._family_type = ID_CASE_FAMILY
        self._children = {ID_PREDICTION: [], ID_PROCESSOR: [], ID_PIPELINE: [], ID_PRODUCER: [], ID_INJECTOR: []}
        self._parents = {ID_PROJECT: []}
        self._multiple_parents = {ID_PROJECT: False}
        self._primary_parent = ID_PROJECT
        self._primary_child = ID_PREDICTION
        self._allow_control = False
        self._simulation_holder = False

        self._image = ico.scenario_16x16


class Prediction(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.PredictionProperties()

        # children: themes
        self._attr = '_predictions'
        self._type = ID_PREDICTION
        self._family_type = self._type
        self._children = {ID_PREDICTION: []}
        self._parents = {ID_SCENARIO: [], ID_PREDICTION: []}
        self._multiple_parents = {ID_SCENARIO: False, ID_PREDICTION: True}
        self._primary_parent = ID_SCENARIO
        self._parent_transfer = False
        self._allow_control = False
        self._simulation_holder = False

        self._image = ico.prediction_16x16


class Field(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.FieldProperties()

        # children: reservoirs (CHANGE?)
        self._attr = '_fields'
        self._type = ID_FIELD
        self._family_type = self._type
        self._children = {ID_RESERVOIR: []}
        self._primary_parent = ID_FIELDS

        self._image = ico.field_16x16


class Block(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.BlockProperties()

        # children: polygons (CHANGE?)
        self._attr = '_blocks'
        self._type = ID_BLOCK
        self._family_type = self._type
        self._children = {ID_POLYGON: []}
        self._primary_parent = ID_BLOCKS

        self._image = ico.block_16x16


class Platform(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.PlatformProperties()

        # children: producers, injectors, processors, pipelines
        self._attr = '_platforms'
        self._type = ID_PLATFORM
        self._family_type = ID_NETWORK_FAMILY
        self._children = {ID_PROCESSOR: [], ID_PRODUCER: [], ID_INJECTOR: []}
        self._primary_parent = ID_FACILITIES
        self._primary_child = ID_PROCESSOR

        self._image = ico.platforms_16x16


class Processor(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.ProcessorProperties()

        self._attr = '_processors'
        self._type = ID_PROCESSOR
        self._family_type = self._type
        self._children = {ID_PROCESSOR: [], ID_PIPELINE: [], ID_PRODUCER: [], ID_INJECTOR: []}
        self._parents = {ID_PLATFORM: [], ID_PROCESSOR: [], ID_PIPELINE: [], ID_SCENARIO: []}

        self._multiple_parents = {ID_PLATFORM: False, ID_PROCESSOR: True, ID_PIPELINE: False, ID_SCENARIO: True}

        self._primary_parent = ID_PLATFORM

        self._image = ico.processor_16x16


class Pipeline(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.PipelineProperties()

        self._attr = '_pipelines'
        self._type = ID_PIPELINE
        self._family_type = ID_NETWORK_FAMILY
        self._children = {ID_PROCESSOR: [], ID_PIPELINE: [], ID_PRODUCER: [], ID_INJECTOR: []}
        self._parents = {ID_PROCESSOR: [], ID_PIPELINE: [], ID_SCENARIO: []}

        self._multiple_parents = {ID_PROCESSOR: False, ID_PIPELINE: False, ID_SCENARIO: True}

        self._primary_parent = ID_FACILITIES

        self._image = ico.pipeline_16x16


class Reservoir(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.ReservoirProperties()

        # children: themes
        self._attr = '_reservoirs'
        self._type = ID_RESERVOIR
        self._family_type = self._type
        self._parents = {ID_FIELD: []}
        self._children = {ID_THEME: []}
        self._multiple_parents = {ID_FIELD: False}
        self._primary_parent = ID_SUBSURFACE
        self._primary_child = ID_THEME

        self._image = ico.reservoir_16x16


class Theme(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.ThemeProperties()

        # children: polygons
        self._attr = '_themes'
        self._type = ID_THEME
        self._family_type = self._type
        self._children = {ID_POLYGON: []}
        self._parents = {ID_RESERVOIR: []}
        self._multiple_parents = {ID_RESERVOIR: False}
        self._primary_parent = ID_RESERVOIR
        self._primary_child = ID_POLYGON

        self._image = ico.theme_16x16


class Polygon(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.PolygonProperties()

        # children: producers, injectors
        self._attr = '_polygons'
        self._type = ID_POLYGON
        self._family_type = self._type
        self._children = {ID_PRODUCER: [], ID_INJECTOR: [], ID_ANALOGUE: []}
        self._parents = {ID_THEME: [], ID_BLOCK: []}
        self._multiple_parents = {ID_THEME: False, ID_BLOCK: False}
        self._primary_parent = ID_THEME
        self._primary_child = ID_WELL_FAMILY

        self._image = ico.polygon_16x16


class Producer(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.ProducerProperties()

        self._attr = '_producers'
        self._type = ID_PRODUCER
        self._family_type = ID_WELL_FAMILY

        self._parents = {ID_POLYGON: [], ID_PLATFORM: [], ID_PROCESSOR: [], ID_PIPELINE: [],
                         ID_INJECTOR: [], ID_SCALING: [], ID_HISTORY: [], ID_SCENARIO: []}

        self._multiple_parents = {ID_POLYGON: False, ID_PLATFORM: False, ID_PROCESSOR: False, ID_PIPELINE: False,
                                  ID_INJECTOR: True, ID_SCALING: True, ID_HISTORY: True, ID_SCENARIO: True}

        self._primary_parent = ID_POLYGON

        self._image = ico.producer_oil_gas_16x16

    def GetNetworkParents(self):
        """
        Get the parents related to the surface-network of the entity

        Returns
        -------
        list
            List of pointer (id, attr)
        """

        return [(id_, attr) for key, list_ in self._parents.items() for id_, attr in list_
                if key in (ID_PROCESSOR, ID_PIPELINE)]

    def SetImage(self, id_=None):
        if id_ == ID_OIL:

            self._image_key = '{}_{}'.format(self._type, 'oil')
            self._image = ico.producer_oil_16x16

        elif id_ == ID_GAS:

            self._image_key = '{}_{}'.format(self._type, 'gas')
            self._image = ico.producer_gas_16x16

        return self._image


class Injector(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.InjectorProperties()

        self._attr = '_injectors'
        self._type = ID_INJECTOR
        self._family_type = ID_WELL_FAMILY
        self._children = {ID_PRODUCER: []}
        self._parents = {ID_POLYGON: [], ID_PLATFORM: [], ID_PROCESSOR: [],
                         ID_PIPELINE: [], ID_HISTORY: [], ID_SCENARIO: []}

        self._multiple_parents = {ID_POLYGON: False, ID_PLATFORM: False, ID_PROCESSOR: False,
                                  ID_PIPELINE: False, ID_HISTORY: True, ID_SCENARIO: True}

        self._primary_parent = ID_POLYGON

        self._image = ico.injector_wag_16x16

    def SetImage(self, id_=None):

        if id_ == ID_WATER_INJ:

            self._image_key = '{}_{}'.format(self._type, 'water')
            self._image = ico.injector_water_16x16

        elif id_ == ID_GAS_INJ:

            self._image_key = '{}_{}'.format(self._type, 'gas')
            self._image = ico.injector_gas_16x16

        elif id_ == ID_WAG_INJ:

            self._image_key = '{}_{}'.format(self._type, 'wag')
            self._image = ico.injector_wag_16x16

        return self._image


class Analogue(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.AnalogueProperties()

        # children: typecurves
        self._attr = '_analogues'
        self._type = ID_ANALOGUE
        self._family_type = ID_PORTFOLIO_FAMILY
        self._children = {ID_TYPECURVE: []}
        self._parents = {ID_POLYGON: [], ID_SCALING: []}
        self._multiple_parents = {ID_POLYGON: False, ID_SCALING: True}
        self._primary_parent = ID_PORTFOLIO
        self._allow_control = False
        self._simulation_holder = False

        self._image = ico.analogue_16x16


class Scaling(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.ScalingProperties()

        self._attr = '_scalings'
        self._type = ID_SCALING
        self._family_type = ID_PORTFOLIO_FAMILY
        self._children = {ID_PRODUCER: [], ID_ANALOGUE: []}
        self._primary_parent = ID_PORTFOLIO
        self._allow_control = False
        self._simulation_holder = False

        self._image = ico.scaling_chart_16x16


class Typecurve(Entity):
    def __init__(self, name=None):
        super().__init__(name)

        self._properties = pro.TypecurveProperties()

        self._attr = '_typecurves'
        self._type = ID_TYPECURVE
        self._family_type = self._type
        self._parents = {ID_ANALOGUE: []}
        self._multiple_parents = {ID_ANALOGUE: False}
        self._primary_parent = ID_ANALOGUE
        self._parent_transfer = False
        self._allow_control = False
        self._simulation_holder = False

        self._image = ico.trend_chart_16x16
