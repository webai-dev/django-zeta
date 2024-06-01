from django.core.exceptions import ValidationError

from ery_backend.base.testcases import EryTestCase
from ery_backend.hands.factories import HandFactory
from ery_backend.logs.models import Log
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.syncs.factories import EraFactory
from ery_backend.stints.factories import StintFactory
from ery_backend.users.factories import UserFactory

from ..factories import TeamFactory, TeamNetworkDefinitionFactory, TeamNetworkFactory
from ..models import TeamHand


class TestTeam(EryTestCase):
    def setUp(self):
        self.era = EraFactory()
        self.stint = StintFactory()
        self.team_network_definition = TeamNetworkDefinitionFactory(generation_method=None)
        self.user = UserFactory()
        self.team = TeamFactory(era=self.era, stint=self.stint, team_network_definition=self.team_network_definition)
        self.hand = HandFactory(user=self.user)
        self.team_hand_relationship = TeamHand(team=self.team, hand=self.hand)
        self.team_hand_relationship.save()

    def test_exists(self):
        self.assertIsNotNone(self.team)

    def test_expected_attributes(self):
        self.assertIn(self.hand, self.team.hands.all())
        self.assertEqual(self.team.era, self.era)
        self.assertEqual(self.team.stint, self.stint)
        self.assertEqual(self.team.team_network_definition, self.team_network_definition)

    def test_log(self):
        # Verify creation of a non-system log
        message = 'This is a test log'
        log_type = Log.LOG_TYPE_CHOICES.warning
        self.team.log(message=message, log_type=Log.LOG_TYPE_CHOICES.warning, system_only=False)
        self.assertTrue(Log.objects.filter(message=message, log_type=log_type, stint=self.stint, team=self.team).exists())

        # Verify system log is not created as Log object
        message = 'This is a system test log'
        self.team.log(message=message, log_type=Log.LOG_TYPE_CHOICES.warning, system_only=True)
        self.assertFalse(Log.objects.filter(message=message, log_type=log_type, stint=self.stint, team=self.team).exists())


class TestTeamNetworkDefinition(EryTestCase):
    def setUp(self):
        self.comment = "Hello. I'm a small test in a big world"
        self.parameters = {'Parameter 1': "Some definition for said parameter"}
        self.module_definition = ModuleDefinitionFactory()
        self.team_network_definition = TeamNetworkDefinitionFactory(
            name='test-network',
            comment=self.comment,
            module_definition=self.module_definition,
            static_network='graphQL',
            parameters=self.parameters,
            generation_method=None,
        )
        # can't have static network and generation method
        self.parameters_2 = {'k': 1, 'p': 2.3}
        self.team_network_definition_2 = TeamNetworkDefinitionFactory(
            static_network=None, generation_method='connected_newman_watts_strogatz_graph', parameters=self.parameters_2
        )

    def test_exists(self):
        self.assertIsNotNone(self.team_network_definition)

    def test_expected_attributes(self):
        self.assertEqual(self.team_network_definition.name, 'test-network')
        self.assertEqual(self.team_network_definition.comment, self.comment)
        self.assertEqual(self.team_network_definition.module_definition, self.module_definition)
        self.assertEqual(self.team_network_definition.static_network, 'graphQL')
        self.assertEqual(self.team_network_definition_2.generation_method, 'connected_newman_watts_strogatz_graph')
        self.assertEqual(self.team_network_definition.parameters, self.parameters)
        self.assertEqual(self.team_network_definition_2.parameters, self.parameters_2)

    def test_validation_errors(self):
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(static_network=None, generation_method=None)
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(static_network="graphQL", generation_method="boiler plate 1")
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None, generation_method='connected_newman_watts_strogatz_graph', parameters=None
            )

        # k not present
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None, generation_method='connected_newman_watts_strogatz_graph', parameters={'p': 0.34}
            )

        # k is None
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None,
                generation_method='connected_newman_watts_strogatz_graph',
                parameters={'k': None, 'p': 0.34},
            )

        # k is incorrect value

        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None,
                generation_method='connected_newman_watts_strogatz_graph',
                parameters={'p': 0.34, 'k': 'orange'},
            )
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None,
                generation_method='connected_newman_watts_strogatz_graph',
                parameters={'p': 0.34, 'k': 2.3},
            )
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None,
                generation_method='connected_newman_watts_strogatz_graph',
                parameters={'p': 0.34, 'k': '2'},
            )

        # p not present
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None, generation_method='connected_newman_watts_strogatz_graph', parameters={'k': 1}
            )

        # p is None
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None, generation_method='connected_newman_watts_strogatz_graph', parameters={'k': 1, 'p': None}
            )

        # p is incorrect value
        with self.assertRaises(ValidationError):
            TeamNetworkDefinitionFactory(
                static_network=None, generation_method='connected_newman_watts_strogatz_graph', parameters={'p': '.34', 'k': 2}
            )


class TestTeamNetwork(EryTestCase):
    def setUp(self):
        self.stint = StintFactory()
        self.team_network_instance = TeamNetworkFactory(stint=self.stint, network='graphQL',)

    def test_exists(self):
        self.assertIsNotNone(self.team_network_instance)

    def test_expected_attributes(self):
        self.assertEqual(self.team_network_instance.stint, self.stint)
        self.assertEqual(self.team_network_instance.network, 'graphQL')
