from datetime import datetime
import unittest

import pytz
from google.api_core.exceptions import ServiceUnavailable

from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.base.testcases import EryTestCase, create_test_stintdefinition
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.labs.factories import LabFactory
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import (
    ModuleVariableFactory,
    HandVariableFactory,
    TeamVariableFactory,
    VariableDefinitionFactory,
)
from ery_backend.stint_specifications.factories import StintSpecificationFactory

from ..entities import RunEntity, WriteEntity, TeamEntity, HandEntity
from ..ery_client import get_datastore_client
from ..factories import NO_SUCH_KEY, RunEntityFactory, WriteEntityFactory, TeamEntityFactory, HandEntityFactory


class TestDatastoreEntities(EryTestCase):
    """
    The DatastoreRunSaver correctly produces datastore entities.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.dsclient = get_datastore_client()

    def test_entity_key_generators(self):
        """
        Key generators must have correct parent keys
        """

        run = RunEntityFactory()
        self.assertEqual(run.kind, "Run")
        self.assertEqual(run.key.id_or_name, run.get("pk"))

        write = WriteEntityFactory(parent=run.key)
        self.assertEqual(write.kind, "Write")
        self.assertIsNot(write.key.id_or_name, None)
        self.assertEqual(write.key.parent, run.key)

        team = TeamEntityFactory(parent=write.key)
        self.assertEqual(team.kind, "Team")
        self.assertEqual(team.key.id_or_name, team.get("pk"))
        self.assertEqual(team.key.parent, write.key)

        hand = HandEntityFactory(parent=write.key)
        self.assertEqual(hand.kind, "Hand")
        self.assertEqual(hand.key.id_or_name, hand.get("pk"))
        self.assertEqual(hand.key.parent, write.key)

    def test_run_entity_from_django(self):
        """
        Produce a :class:`~ery_backend.datastore.RunEntity` from the :class:`~ery_backend.stints.models.Stint`
        """
        stint_definition = create_test_stintdefinition(Frontend.objects.get(name="Web"))
        spec = StintSpecificationFactory(stint_definition=stint_definition)
        stint = stint_definition.realize(stint_specification=spec)
        stint.started_by = UserFactory()
        stint.lab = LabFactory()

        stint.started = datetime.now(pytz.UTC)
        stint.ended = datetime.now(pytz.UTC)

        entity = RunEntity.from_django(stint)

        self.assertEqual(entity.key.id_or_name, stint.pk)
        self.assertEqual(entity["pk"], stint.pk)
        self.assertEqual(entity["stint_definition_id"], stint.stint_specification.stint_definition.pk)
        self.assertEqual(entity["stint_definition_name"], stint.stint_specification.stint_definition.name)
        self.assertEqual(entity["stint_specification_name"], stint.stint_specification.name)
        self.assertEqual(entity["stint_specification_id"], stint.stint_specification.pk)
        self.assertEqual(entity["started_by"], stint.started_by.username)
        self.assertEqual(entity["lab"], stint.lab.name)
        self.assertEqual(entity["started"], stint.started)
        self.assertEqual(entity["ended"], stint.ended)

    def test_run_entity_from_entity(self):
        """:class:`~ery_backend.datastore.RunEntity` can be recreated from the :class:`google.cloud.datastore.Entity`"""
        run = RunEntityFactory()
        try:
            self.dsclient.put(run)
            entity = self.dsclient.get(run.key)
        except ServiceUnavailable:  # Used to avoid pickling errors in multiprocessing
            raise Exception("Could not connect to datastore")
        self.assertEqual(dict(run), dict(RunEntity.from_entity(entity)))

    def test_write_entity_from_django(self):
        """Produce a :class:`~ery_backend.datastore.WriteEntity` from a :class:`~ery_backend.actions.models.ActionStep`"""
        hand = HandFactory()
        action = ActionFactory(module_definition=hand.current_module.module_definition)
        variable_definition = VariableDefinitionFactory(module_definition=action.module_definition)
        action_step = ActionStepFactory(action=action, variable_definition=variable_definition)
        entity = WriteEntity.from_django(action_step, [], hand, NO_SUCH_KEY())

        self.assertEqual(entity.key.id_or_name, entity["pk"].isoformat())
        self.assertIsInstance(entity["pk"], datetime)
        self.assertEqual(entity["action_name"], action_step.action.name)
        self.assertEqual(entity["action_step_id"], action_step.pk)
        self.assertEqual(entity["module_name"], action_step.variable_definition.module_definition.name)
        self.assertEqual(entity["module_id"], action_step.variable_definition.module_definition.pk)
        self.assertEqual(entity["current_module_index"], hand.get_current_index())
        self.assertEqual(entity["era_name"], action_step.era.name)
        self.assertEqual(entity["era_id"], action_step.era.pk)

    @unittest.skip("#XXX: Fix in issue #678")
    # pylint:disable=no-self-use
    def test_write_entity_from_django_stintdefinitionvariabledefinition(self):
        """
        Test that a :class:`~ery_backend.datastore.WriteEntity` is properly built when using variables with
        :class:`~ery_backend.stints.StintDefinitionVariableDefinition` connections
        """
        # vds = []

        # choices = [d[0] for d in VariableDefinition.DATA_TYPE_CHOICES]
        # data_type = random.choice(choices)
        # vds.append(VariableDefinitionFactory(data_type=data_type))
        # sdvd = StintDefinitionVariableDefinitionFactory(variable_definitions=vds)

        ModuleVariableFactory(with_stint_definition_variable_definition=True)
        TeamVariableFactory(with_stint_definition_variable_definition=True)
        HandVariableFactory(with_stint_definition_variable_definition=True)

    def test_write_entity_from_entity(self):
        """
        :class:`~ery_backend.datastore.WriteEntity` can be recreated from the google :class:`google.cloud.datastore.Entity`
        """
        write = WriteEntityFactory()
        try:
            self.dsclient.put(write)
            entity = self.dsclient.get(write.key)
        except ServiceUnavailable:
            raise Exception("Could not connect to datastore")
        self.assertEqual(write, WriteEntity.from_entity(entity))

    @unittest.skip("Fix in #682")
    def test_team_entity_from_django(self):
        """
        TeamEntity can be greated via from_django()
        """
        tv = TeamVariableFactory()
        team = tv.team
        entity = TeamEntity.from_django(team, {tv.variable_definition.name: tv.value})

        self.assertEqual(entity.key.id_or_name, team.pk)
        self.assertEqual(entity["pk"], team.pk)
        self.assertEqual(entity["era_id"], team.era.pk)
        self.assertEqual(entity["era_name"], team.era.name)
        self.assertEqual(entity["variables"][tv.variable_definition.name], tv.value)

    def test_team_entity_from_entity(self):
        """
        :class:`~ery_backend.datastore.TeamEntity` can be recreated from the google :class:`google.cloud.datastore.Entity`
        """
        team = TeamEntityFactory()
        try:
            self.dsclient.put(team)
            entity = self.dsclient.get(team.key)
        except ServiceUnavailable:
            raise Exception("Could not connect to datastore")
        self.assertEqual(team, TeamEntity.from_entity(entity))

    @unittest.skip("Fix in #682")
    def test_hand_entity_from_django(self):
        """
        HandEntity can be greated via from_django()
        """
        hv = HandVariableFactory()
        hand = hv.hand
        other_hvs = [HandVariableFactory(hand=hand) for _ in range(2)]
        hand.user = UserFactory()
        ## TODO: Handle the creation of dicts inside from_django
        hvs = {variable.variable_definition.name: variable.value for variable in [hv] + other_hvs}
        entity = HandEntity.from_django(hand, hvs)

        self.assertEqual(entity.key.id_or_name, hand.pk)
        self.assertEqual(entity["pk"], hand.pk)
        self.assertEqual(entity["variables"][hv.variable_definition.name], hv.value)

        self.assertEqual(entity["name"], hand.user.username)
        self.assertEqual(entity["era_id"], hand.era.pk)
        self.assertEqual(entity["era_name"], hand.era.name)

        self.assertEqual(getattr(entity, "current_team", None), hand.current_team)
        self.assertEqual(entity["stage"], hand.stage.stage_definition.name)
        self.assertEqual(entity["frontend"], hand.frontend.name)
        self.assertEqual(entity["language"], hand.language.name_en)

    def test_hand_entity_from_entity(self):
        """HandEntity can be recreated from the google entity"""
        hand = HandEntityFactory()
        try:
            self.dsclient.put(hand)
            entity = self.dsclient.get(hand.key)
        except ServiceUnavailable:
            raise Exception("Could not connect to datastore")

        self.assertEqual(hand, HandEntity.from_entity(entity))
