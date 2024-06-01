import random
import unittest
from unittest import mock

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.keywords.factories import KeywordFactory
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.stages.factories import StageDefinitionFactory, RedirectFactory
from ery_backend.stages.models import StageDefinition
from ery_backend.templates.factories import TemplateWidgetFactory

from ..factories import WidgetFactory, WidgetEventFactory, WidgetConnectionFactory, WidgetEventStepFactory, WidgetPropFactory
from ..models import Widget, WidgetEvent, WidgetEventStep


class TestWidgetEvent(EryTestCase):
    def setUp(self):
        self.widget = WidgetFactory(frontend=Frontend.objects.get(name='Web'))
        self.widget_event = WidgetEventFactory(
            widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange, include_event_steps=False, name='special'
        )

    def test_exists(self):
        self.assertIsNotNone(self.widget_event)

    def test_expected_attributes(self):
        self.widget_event.refresh_from_db()
        self.assertEqual(self.widget_event.widget, self.widget)
        self.assertEqual(self.widget_event.event_type, WidgetEvent.REACT_EVENT_CHOICES.onChange)
        self.assertEqual(self.widget_event.name, 'special')

    def test_format(self):
        """Confirm adheres to React naming conventions, and starts with lower case"""
        with self.assertRaises(ValidationError):
            WidgetEventFactory(name='all_the_way_left')
        with self.assertRaises(ValidationError):
            WidgetEventFactory(name='1LeftWithNumbers')
        with self.assertRaises(ValidationError):
            WidgetEventFactory(name='left With Spaces')

    @unittest.skip("XXX: Address in issue #815")
    def test_unique_together(self):
        """Two widget_events cannot have the same name, event_type for the same widget"""
        # This is fine
        web = Frontend.objects.get(name='Web')
        widget = WidgetFactory(frontend=web)
        WidgetEventFactory(name='starting', widget=widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)
        WidgetEventFactory(name='starting', widget=widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick)

        # Also fine
        widget_a = WidgetFactory(frontend=web)
        widget_b = WidgetFactory(frontend=web)
        WidgetEventFactory(name='starting', widget=widget_a, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)
        WidgetEventFactory(name='starting', widget=widget_b, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)

        # This is not
        widget_a = WidgetFactory(frontend=web)
        WidgetEventFactory(name='starting', widget=widget_a, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)
        with self.assertRaises(IntegrityError):
            WidgetEventFactory(name='starting', widget=widget_a, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)


class TestWidgetEventStep(EryTestCase):
    def setUp(self):
        self.widget = WidgetFactory()
        self.widget_event = WidgetEventFactory(widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)
        self.widget_event_step = WidgetEventStepFactory(
            code='test code',
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
            widget_event=self.widget_event,
            order=3,
        )

    def test_exists(self):
        self.assertIsNotNone(self.widget_event_step)

    def test_expected_attributes(self):
        self.widget_event_step.refresh_from_db()
        self.assertEqual(self.widget_event_step.widget_event, self.widget_event)
        self.assertEqual(self.widget_event_step.event_action_type, WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code)
        self.assertEqual(self.widget_event_step.code, 'test code')
        self.assertEqual(self.widget_event_step.order, 3)

    def test_expected_errors(self):
        """
        WidgetEventStep must be of type 'code' for code attribute to have value.
        """
        WidgetEventStepFactory(event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code, code='some code here')
        with self.assertRaises(ValidationError):
            WidgetEventStepFactory(event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.submit, code='some code here')

    def test_execution_order(self):
        """
        Steps should be executed in order.
        """
        hand = create_test_hands(module_definition_n=1, stage_n=3, redirects=True).first()
        stagedef_1, stagedef_2, _ = list(hand.current_module_definition.stage_definitions.order_by('id').all())
        widget_event = WidgetEventFactory()
        we_step_1 = WidgetEventStepFactory(
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.back, widget_event=widget_event
        )
        we_step_2 = WidgetEventStepFactory(
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.submit, widget_event=widget_event
        )
        self.assertTrue(we_step_1.order < we_step_2.order)
        self.assertEqual(hand.stage.stage_definition, stagedef_1)
        widget_event.trigger(hand)
        hand.refresh_from_db()
        self.assertEqual(hand.stage.stage_definition, stagedef_2)
        we_step_1.order = 3
        we_step_1.save()
        we_step_2.order = 2
        we_step_2.save()
        self.assertTrue(we_step_1.order > we_step_2.order)
        hand.set_stage(stage_definition=stagedef_1)
        hand.refresh_from_db()
        self.assertEqual(hand.stage.stage_definition, stagedef_1)
        widget_event.trigger(hand)
        hand.refresh_from_db()
        self.assertEqual(hand.stage.stage_definition, stagedef_2)


class TestWidget(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.web = Frontend.objects.get(name='Web')
        cls.sms = Frontend.objects.get(name='SMS')
        cls.email = Frontend.objects.get(name='Email')

    def setUp(self):
        self.widget = WidgetFactory(
            name='TestWidget', comment='Tester of the Widgets', frontend=self.web, code='Test the rainbow', external=False
        )
        self.external_widget = WidgetFactory(
            name='TestExternalWidget',
            comment='Tester of the outsiders',
            frontend=self.web,
            code='from TESTS import the rainbow',
            namespace='TESTS',
            external=True,
            address='somewhereoutthere',
        )

    def test_exists(self):
        self.assertIsNotNone(self.widget)
        self.assertIsNotNone(self.external_widget)

    def test_expected_attributes(self):
        self.widget.refresh_from_db()
        self.assertEqual(self.widget.name, 'TestWidget')
        self.assertEqual(self.widget.comment, 'Tester of the Widgets')
        self.assertEqual(self.widget.frontend, Frontend.objects.get(name='Web'))
        self.assertEqual(self.widget.code, 'Test the rainbow')
        self.assertEqual(self.widget.namespace, 'Widget')
        self.assertFalse(self.widget.external)

        self.assertTrue(self.external_widget.external)

    def test_attribute_errors(self):
        with self.assertRaises(EryValidationError):
            WidgetFactory(code=None, external=False)

        with self.assertRaises(EryValidationError):
            WidgetFactory(address=None, external=True)

    def test_get_related_widgets(self):
        sms_widget = WidgetFactory(name='SMSWidget', frontend=self.sms)
        self.widget.connect(sms_widget)
        email_widget = WidgetFactory(name='EmailWidget', frontend=self.email)
        self.widget.connect(email_widget)
        # Reverse connection
        other_widget = WidgetFactory(name='OtherWidget', frontend=FrontendFactory())
        other_widget.connect(self.widget)
        for widget in [sms_widget, email_widget, other_widget]:
            self.assertIn(widget, self.widget.connected_widgets.all())

    def test_frontend_change_error(self):
        """
        Validate frontend cannot be changed if such change conflicts with a connected widget.
        """
        sms_widget = WidgetFactory(frontend=self.sms)
        self.widget.connect(sms_widget)
        with self.assertRaises(EryValidationError):
            self.widget.frontend = self.sms
            self.widget.save()

    def test_connect_errors(self):
        """
        Verify Widgets with non-unique frontends cannot be connected.
        """
        # same frontend as self
        duplicate_web_widget = WidgetFactory(frontend=self.web)
        with self.assertRaises(EryValidationError):
            self.widget.connect(duplicate_web_widget)

        # nonunique frontend
        sms_widget = WidgetFactory(frontend=self.sms)
        self.widget.connect(sms_widget)
        duplicate_sms_widget = WidgetFactory(frontend=self.sms)
        with self.assertRaises(EryValidationError):
            self.widget.connect(duplicate_sms_widget)

        # reverse connection on already connected model
        with self.assertRaises(EryValidationError):
            sms_widget.connect(self.widget)

    def test_disconnect(self):
        """
        Verify Widgets can be disconnected regardless of the direction of their relationship.
        """
        sms_widget = WidgetFactory(frontend=self.sms)
        # forward facing
        self.widget.connect(sms_widget)
        self.assertIn(sms_widget, self.widget.connected_widgets.all())
        self.widget.disconnect(sms_widget)
        self.assertNotIn(sms_widget, self.widget.connected_widgets.all())

        # reverse facing
        sms_widget.connect(self.widget)
        self.assertIn(sms_widget, self.widget.connected_widgets.all())
        self.widget.disconnect(sms_widget)
        self.assertNotIn(sms_widget, self.widget.connected_widgets.all())

        # ignore non-connected widgets without returning failure message
        whothatwidget = WidgetFactory()
        self.widget.disconnect(whothatwidget)

    def test_import(self):
        WidgetFactory(frontend=self.sms, slug='notarealslug-asdghjkl')

        xml = open('ery_backend/widgets/tests/data/widget-0.bxml', 'rb')
        new_widget = Widget.import_instance_from_xml(xml, name='NewWidget')
        self.assertEqual(new_widget.name, 'NewWidget')
        self.assertEqual(new_widget.frontend, Frontend.objects.get(name='Web'))
        self.assertEqual(new_widget.events.count(), 2)
        for event in new_widget.events.all():
            self.assertEqual(event.steps.count(), 1)
        # XXX: Address in issue #363.
        # self.assertIn(sms_widget, new_widget.connected_widgets.all())

    @unittest.skip("Address in issue #383")
    def test_duplicate_errors(self):
        """
        Verify duplicate with connect_widgets fails if connected widgets with same frontend exist.
        """
        sms_widget = WidgetFactory(frontend=self.sms)
        self.widget.connect(sms_widget)

        with self.assertRaises(EryValidationError):
            self.widget.duplicate(connect_widgets=True)

    def test_duplicate(self):
        preload_keywords = [KeywordFactory() for _ in range(3)]
        preload_connections = [WidgetConnectionFactory(originator=self.widget) for _ in range(3)]
        for keyword in preload_keywords:
            self.widget.keywords.add(keyword)

        # sms_widget should be disregarded during duplicate
        sms_widget = WidgetFactory(frontend=self.sms)
        self.widget.connect(sms_widget)

        widget_event_1 = WidgetEventFactory(widget=self.widget)
        widget_event_2 = WidgetEventFactory(widget=self.widget)
        duplicated_widget = self.widget.duplicate(connect_widgets=False)
        self.assertEqual(f'{self.widget.name}Copy', duplicated_widget.name)
        self.assertEqual(self.widget.comment, duplicated_widget.comment)
        self.assertEqual(self.widget.frontend, duplicated_widget.frontend)
        self.assertTrue(
            duplicated_widget.events.filter(event_type=widget_event_1.event_type, name=widget_event_1.name).exists()
        )
        self.assertTrue(
            duplicated_widget.events.filter(event_type=widget_event_2.event_type, name=widget_event_2.name).exists()
        )
        duplicate_connections = duplicated_widget.connections.all()
        duplicate_targets = [connection.target for connection in duplicate_connections]
        for connection in preload_connections:
            self.assertIn(connection.target, duplicate_targets)

        # Expected keywords
        for keyword in preload_keywords:
            self.assertIn(keyword, duplicated_widget.keywords.all())

    @mock.patch('ery_backend.widgets.models.WidgetEvent.trigger', autospec=True)
    def test_trigger_events(self, mock_trigger):
        hand = HandFactory()
        on_click_event = WidgetEventFactory(widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick)
        for _ in range(3):
            WidgetEventStepFactory(widget_event=on_click_event)
        on_change_event = WidgetEventFactory(
            name=on_click_event.name, widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange
        )
        for _ in range(2):
            WidgetEventStepFactory(widget_event=on_change_event)

        template_widget = TemplateWidgetFactory(widget=self.widget)
        template_widget.trigger_events(on_click_event.name, WidgetEvent.REACT_EVENT_CHOICES.onClick, hand)
        # should be called
        mock_trigger.assert_any_call(on_click_event, hand)
        # should not be called
        with self.assertRaises(AssertionError):
            mock_trigger.assert_any_call(on_change_event, hand)

        template_widget.trigger_events(on_click_event.name, WidgetEvent.REACT_EVENT_CHOICES.onChange, hand)
        # should be called now
        mock_trigger.assert_any_call(on_change_event, hand)

    @unittest.skip("Add in #379")
    def test_get_alternative_widget(self):
        pass


class TestWidgetConnection(EryTestCase):
    def setUp(self):
        self.originator = WidgetFactory()
        self.target = WidgetFactory()
        self.name = 'WidgetWidget'
        self.widget_connection = WidgetConnectionFactory(originator=self.originator, target=self.target, name=self.name)

    def test_exists(self):
        self.assertIsNotNone(self.widget_connection)

    def test_expected_attributes(self):
        self.assertEqual(self.originator, self.widget_connection.originator)
        self.assertEqual(self.target, self.widget_connection.target)
        self.assertEqual(self.name, self.widget_connection.name)


@unittest.skip("Address in issue #395")
class TestPreview(EryTestCase):
    """
    Confirm preview correctly calls babel/engine based on the frontend.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1, signal_pubsub=False).first()

    @unittest.skip('Fix in issue #395')
    @staticmethod
    def test_web():
        frontend = Frontend.objects.get(name='Web')
        widget = WidgetFactory(frontend=frontend, name='TestWidget')
        # pylint:disable=protected-access
        # expected_code = f'{get_widget_components(frontend)}\n<Widget.TestWidget/>'
        widget.preview()
        # mock_es6.assert_called_with(expected_code)

    @unittest.skip('Fix in issue #395')
    @mock.patch('ery_backend.widgets.models.evaluate_without_side_effects')
    def test_sms(self, mock_evaluate):
        mock_evaluate.return_value = 'codes'
        frontend = Frontend.objects.get(name='SMS')
        widget = WidgetFactory(frontend=frontend)
        self.assertEqual(widget.preview(self.hand), 'codes')
        mock_evaluate.assert_called_with(str(widget), self.hand, widget.code)


class TestForwardWidgetEvent(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.submit_widget = Widget.objects.get(name='SubmitButton')

    def setUp(self):
        self.hand = create_test_hands(signal_pubsub=False).first()
        self.hand.stage.stage_definition.redirect_on_submit = True
        self.hand.stage.stage_definition.save()
        self.next_stage = StageDefinitionFactory(module_definition=self.hand.current_module_definition)
        RedirectFactory(stage_definition=self.hand.stage.stage_definition, next_stage_definition=self.next_stage)

    def test_redirect_next(self):
        """
        If no breadcrumb, submit widget_event should change hand stage using
        redirect.
        """
        self.assertNotEqual(self.hand.stage.stage_definition, self.next_stage)
        template_widget = TemplateWidgetFactory(widget=self.submit_widget)
        template_widget.trigger_events(name='', event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, hand=self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, self.next_stage)

    def test_next_breadcrumb(self):
        """
        Stage specified by next_breadcrumb should be preferred over
        redirect.
        """
        breadcrumb_stage_definition = StageDefinitionFactory(module_definition=self.hand.current_module_definition)
        initial_stage = self.hand.stage
        self.hand.set_stage(stage_definition=breadcrumb_stage_definition)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, breadcrumb_stage_definition)
        breadcrumb = self.hand.create_breadcrumb(self.hand.stage)
        self.hand.set_breadcrumb(breadcrumb)
        self.hand.refresh_from_db()
        breadcrumb_stage = self.hand.stage
        self.hand.set_breadcrumb(breadcrumb.previous_breadcrumb)
        self.hand.set_stage(initial_stage)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage, initial_stage)
        template_widget = TemplateWidgetFactory(widget=self.submit_widget)
        template_widget.trigger_events(name='', event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, hand=self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage, breadcrumb_stage)


class TestBackWidgetEvent(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.back_widget = Widget.objects.get(name='BackButton')

    def setUp(self):
        self.hand = create_test_hands(signal_pubsub=False).first()
        self.start_stagedef = self.hand.stage.stage_definition
        self.next_stagedef = StageDefinitionFactory(
            module_definition=self.hand.current_module_definition, breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.all
        )
        self.hand.set_stage(stage_definition=self.next_stagedef)
        next_breadcrumb = self.hand.create_breadcrumb(self.hand.stage)
        self.hand.set_breadcrumb(next_breadcrumb)

    def test_previous_breadcrumb(self):
        """
        Traverse to stage specified by previous_breadcrumb using back widget action.
        """
        self.assertEqual(self.hand.stage.stage_definition, self.next_stagedef)
        template_widget = TemplateWidgetFactory(widget=self.back_widget)
        template_widget.trigger_events(name='', event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, hand=self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, self.start_stagedef)

    def test_silent_failure(self):
        """
        Silent failure should occur if no previous stage or
        breadcrumb type does not allow back.
        """
        # No back movement allowed
        self.next_stagedef.breadcrumb_type = StageDefinition.BREADCRUMB_TYPE_CHOICES.none
        self.next_stagedef.save()
        template_widget = TemplateWidgetFactory(widget=self.back_widget)
        template_widget.trigger_events(name=None, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, hand=self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, self.next_stagedef)

        # No previous stage
        self.next_stagedef.breadcrumb_type = StageDefinition.BREADCRUMB_TYPE_CHOICES.all
        self.next_stagedef.save()
        self.start_stagedef.delete()
        self.hand.refresh_from_db()
        template_widget.trigger_events(name=None, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, hand=self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, self.next_stagedef)


class TestWidgetProp(EryTestCase):
    def test_reserved_words(self):
        with self.assertRaises(ValueError):
            WidgetPropFactory(name='choices')


class TestNestedConnectedWidgetIds(EryTestCase):
    def setUp(self):
        self.widget = WidgetFactory()

    def test_single_chain(self):
        widget_connection = WidgetConnectionFactory(originator=self.widget)
        # pylint: disable=protected-access
        self.assertEqual({widget_connection.target.id}, self.widget.get_nested_connected_widget_ids(self.widget.id))

    def test_branching(self):
        target_ids = set()
        for _ in range(random.randint(1, 10)):
            connection = WidgetConnectionFactory(originator=self.widget)
            target_ids.add(connection.target.id)

        # pylint: disable=protected-access
        self.assertEqual(target_ids, self.widget.get_nested_connected_widget_ids(self.widget.id))

    def test_nested(self):
        target_ids = set()
        for _ in range(random.randint(1, 10)):
            connection = WidgetConnectionFactory(originator=self.widget)
            target_ids.add(connection.target.id)
            for _ in range(random.randint(1, 10)):
                nested_connection = WidgetConnectionFactory(originator=connection.target)
                target_ids.add(nested_connection.target.id)
                for _ in range(random.randint(1, 10)):
                    doubly_nested = WidgetConnectionFactory(originator=nested_connection.target)
                    target_ids.add(doubly_nested.target.id)

        # pylint: disable=protected-access
        self.assertEqual(target_ids, self.widget.get_nested_connected_widget_ids(self.widget.id))


class TestAllConnectedWidgets(EryTestCase):
    def test_ids_same_as_nested_connected_widget_ids(self):
        widget = WidgetFactory()
        self.assertEqual(
            widget.get_nested_connected_widget_ids(widget.id),  # pylint: disable=protected-access
            set(widget.get_all_connected_widgets().values_list('id', flat=True)),
        )
        nested_widgets = [
            WidgetConnectionFactory(originator=widget, target=WidgetFactory(frontend=widget.frontend)).target
            for _ in range(random.randint(1, 10))
        ]
        self.assertEqual(
            widget.get_nested_connected_widget_ids(widget.id),  # pylint: disable=protected-access
            set(widget.get_all_connected_widgets().values_list('id', flat=True)),
        )
        for _ in range(random.randint(1, 10)):
            WidgetConnectionFactory(originator=random.choice(nested_widgets), target=WidgetFactory(frontend=widget.frontend))
        self.assertEqual(
            widget.get_nested_connected_widget_ids(widget.id),  # pylint: disable=protected-access
            set(widget.get_all_connected_widgets().values_list('id', flat=True)),
        )
