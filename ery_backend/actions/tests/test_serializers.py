from ery_backend.base.testcases import EryTestCase
from ..factories import ActionFactory, ActionStepFactory
from ..models import Action, ActionStep


class TestActionStepBXMLSerializer(EryTestCase):
    def setUp(self):
        self.action_step = ActionStepFactory(subaction=ActionFactory())
        self.action_step_serializer = ActionStep.get_bxml_serializer()(self.action_step)

    def test_exists(self):
        self.assertIsNotNone(self.action_step_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.action_step_serializer.data['era'], self.action_step.era.name)
        self.assertEqual(self.action_step_serializer.data['subaction'], self.action_step.subaction.name)
        self.assertEqual(self.action_step_serializer.data['invert_condition'], self.action_step.invert_condition)
        self.assertEqual(self.action_step_serializer.data['for_each'], self.action_step.for_each)
        self.assertEqual(self.action_step_serializer.data['value'], self.action_step.value)
        self.assertEqual(self.action_step_serializer.data['code'], self.action_step.code)
        self.assertEqual(self.action_step_serializer.data['log_message'], self.action_step.log_message)


class TestActionSerializer(EryTestCase):
    def setUp(self):
        self.action = ActionFactory()
        self.action_step = ActionStepFactory(action=self.action)
        self.action_step_2 = ActionStepFactory(action=self.action)
        self.action_serializer = Action.get_bxml_serializer()(self.action)

    def test_exists(self):
        self.assertIsNotNone(self.action_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.action_serializer.data['comment'], self.action.comment)
        self.assertEqual(self.action_serializer.data['name'], self.action.name)
        self.assertIn(ActionStep.get_bxml_serializer()(self.action_step).data, self.action_serializer.data['steps'])
        self.assertIn(ActionStep.get_bxml_serializer()(self.action_step_2).data, self.action_serializer.data['steps'])
