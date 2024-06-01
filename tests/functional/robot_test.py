from collections import defaultdict
from time import sleep

from languages_plus.models import Language

from ery_backend.base.testcases import create_test_stintdefinition
from ery_backend.base.testcases import EryTestCase, EryTransactionTestCase
from ery_backend.frontends.models import Frontend
from ery_backend.hands.models import Hand
from ery_backend.hands.factories import HandFactory
from ery_backend.robots.factories import RobotFactory, RobotRuleFactory

from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.stint_specifications.factories import StintSpecificationRobotFactory
from ery_backend.users.factories import UserFactory


class TestStintSpecificationRealize(EryTransactionTestCase):
    def setUp(self):
        web = Frontend.objects.get(name='Web')
        self.stint_definition = create_test_stintdefinition(
            frontend=web, render_args=['procedure', 'module_definition_widget', 'variable']
        )  # Remove this for simplicity
        # Take number of modules and stages as args
        self.stint_definition.save()
        # create a stint_spec with number of robots
        self.stint_specification = StintSpecificationFactory(
            stint_definition=self.stint_definition, language=Language.objects.get(pk='en')
        )

        self.robots = {}
        self.robot_rules = defaultdict(list)
        for module_definition in self.stint_definition.module_definitions.all():
            self.robots[module_definition.id] = RobotFactory(module_definition=module_definition)

            for widget in module_definition.module_widgets.all():
                self.robot_rules[module_definition.id].append(RobotRuleFactory(widget=widget, rule_type='static'))

    def test_one_robot(self):
        stint = self.stint_specification.realize()
        for _ in range(2):
            HandFactory(stint=stint)
        StintSpecificationRobotFactory(stint_specification=self.stint_specification, number=1)
        stint.start(UserFactory())
        for _ in range(5):
            try:
                self.assertEqual(Hand.objects.filter(stint=stint, robot__isnull=False).count(), 1)
                break
            except AssertionError:
                sleep(5)
        self.assertEqual(Hand.objects.filter(stint=stint, robot__isnull=False).count(), 1)

    def test_two_robot(self):
        stint = self.stint_specification.realize()
        for _ in range(2):
            HandFactory(stint=stint)
        StintSpecificationRobotFactory(stint_specification=self.stint_specification, number=2)
        stint.start(UserFactory())
        for _ in range(5):
            try:
                self.assertEqual(Hand.objects.filter(stint=stint, robot__isnull=False).count(), 2)
                break
            except AssertionError:
                sleep(5)
        self.assertEqual(Hand.objects.filter(stint=stint, robot__isnull=False).count(), 2)

    def test_one_robots_per_human(self):
        stint = self.stint_specification.realize()
        for _ in range(2):
            HandFactory(stint=stint)

        StintSpecificationRobotFactory(stint_specification=self.stint_specification, robots_per_human=1)
        stint.start(UserFactory())
        for _ in range(5):
            try:
                self.assertEqual(Hand.objects.filter(stint=stint, robot__isnull=False).count(), 2)
                break
            except AssertionError:
                sleep(5)
        self.assertEqual(Hand.objects.filter(stint=stint, robot__isnull=False).count(), 2)

    def test_two_robots_per_human(self):
        stint = self.stint_specification.realize()
        for _ in range(2):
            HandFactory(stint=stint)

        StintSpecificationRobotFactory(stint_specification=self.stint_specification, robots_per_human=2)
        stint.start(UserFactory())
        for _ in range(5):
            try:
                self.assertEqual(Hand.objects.filter(stint=stint, robot__isnull=False).count(), 4)
                break
            except AssertionError:
                sleep(5)
        self.assertEqual(Hand.objects.filter(stint=stint, robot__isnull=False).count(), 4)


class TestStintStart(EryTestCase):
    pass
