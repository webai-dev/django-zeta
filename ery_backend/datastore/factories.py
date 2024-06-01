from datetime import datetime
import random
import pytz

import factory
import factory.fuzzy

from .entities import RunEntity, WriteEntity, TeamEntity, HandEntity
from .ery_client import get_datastore_client


NO_SUCH_KEY = lambda: get_datastore_client().key("no such key, factory generated", 1)
ERA_NAMES = ["triassic", "jurassic", "cretaceous"]


def testable_entity_set(stint_pk=None):
    """
    Produce a complete set of Entities, as can be used in testing

    Args:
    stint_pk: optional integer to be used for the RunEntity pk field.  Data will not be made to match Django.
    """

    if stint_pk is None:
        run = RunEntityFactory()
    else:
        run = RunEntityFactory(pk=stint_pk)

    entities = [run]

    write = WriteEntityFactory(parent=run.key)
    entities.append(write)

    team = TeamEntityFactory(parent=write.key)
    entities.append(team)
    entities.extend([HandEntityFactory(parent=write.key) for i in range(random.randint(1, 5))])

    return entities


class RunEntityFactory(factory.Factory):
    class Meta:
        model = RunEntity

    pk = factory.Sequence(id)
    stint_definition_id = factory.fuzzy.FuzzyInteger(1, 100)

    @factory.lazy_attribute
    def stint_definition_name(self):
        return f"stint_definition-{self.stint_definition_id}"

    stint_specification_id = factory.fuzzy.FuzzyInteger(1, 100)

    @factory.lazy_attribute
    def stint_specification_name(self):
        return f"stint_specification-{self.stint_specification_id}"

    started_by = factory.Faker('name')

    @factory.lazy_attribute
    def lab(self):
        return f"lab_for_stint-{self.pk}"

    started = factory.fuzzy.FuzzyDateTime(datetime(2018, 1, 1, tzinfo=pytz.UTC), datetime(2018, 6, 1, tzinfo=pytz.UTC))
    ended = factory.fuzzy.FuzzyDateTime(datetime(2018, 1, 1, tzinfo=pytz.UTC), datetime.now(pytz.UTC))


class WriteEntityFactory(factory.Factory):
    class Meta:
        model = WriteEntity

    parent = factory.LazyFunction(NO_SUCH_KEY)
    action_name = factory.fuzzy.FuzzyText()
    action_step_id = factory.fuzzy.FuzzyInteger(1, 100)
    module_name = factory.fuzzy.FuzzyText()
    module_id = factory.fuzzy.FuzzyInteger(1, 100)
    era_name = factory.fuzzy.FuzzyText()
    era_id = factory.fuzzy.FuzzyInteger(1, 100)

    current_module_index = factory.fuzzy.FuzzyInteger(0, 8)

    @factory.lazy_attribute
    def variables(self):
        return {f"write-{self.action_name}": random.randint(1, 500)}


class TeamEntityFactory(factory.Factory):
    class Meta:
        model = TeamEntity

    pk = factory.fuzzy.FuzzyInteger(1, 100)
    parent = factory.LazyFunction(NO_SUCH_KEY)

    name = factory.fuzzy.FuzzyText()
    era_name = factory.fuzzy.FuzzyChoice(ERA_NAMES)

    @factory.lazy_attribute
    def era_id(self):
        return ERA_NAMES.index(self.era_name) + 1

    @factory.lazy_attribute
    def variables(self):
        return {f"team-{self.name}": random.randint(1, 500)}


class HandEntityFactory(factory.Factory):
    class Meta:
        model = HandEntity

    pk = factory.fuzzy.FuzzyInteger(1, 100)
    parent = factory.LazyFunction(NO_SUCH_KEY)

    name = factory.fuzzy.FuzzyText()
    era_name = factory.fuzzy.FuzzyChoice(ERA_NAMES)

    @factory.lazy_attribute
    def era_id(self):
        return ERA_NAMES.index(self.era_name) + 1

    current_team = factory.fuzzy.FuzzyText()
    stage = factory.fuzzy.FuzzyText()

    @factory.lazy_attribute
    def variables(self):
        return {f"hand-{self.name}": random.randint(1, 500)}
