import random
import unittest

import graphene

from ery_backend.base.testcases import GQLTestCase, create_test_hands
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.hands.schema import HandQuery
from ery_backend.mutations import WidgetMutation, WidgetEventMutation, WidgetEventStepMutation
from ery_backend.roles.utils import grant_role

from ..factories import WidgetFactory, WidgetEventFactory, WidgetEventStepFactory, WidgetConnectionFactory
from ..models import Widget, WidgetEvent, WidgetEventStep
from ..schema import WidgetQuery, WidgetEventQuery, WidgetEventStepQuery


class TestQuery(HandQuery, WidgetQuery, WidgetEventQuery, WidgetEventStepQuery, graphene.ObjectType):
    pass


class TestMutation(WidgetMutation, WidgetEventMutation, WidgetEventStepMutation, graphene.ObjectType):
    pass


class TestReadWidget(GQLTestCase):
    """Ensure reading Widget works"""

    node_name = "WidgetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allWidgets query without a user is unauthorized"""
        query = """{allWidgets{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        widget = WidgetFactory(external=True)
        td = {"widgetid": widget.gql_id}

        query = """query WidgetQuery($widgetid: ID!){widget(id: $widgetid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allWidgets{ edges{ node{ id }}}}"""
        widgets = [WidgetFactory(external=True) for _ in range(3)]

        for obj in widgets:
            grant_role(self.viewer["role"], obj, self.viewer["user"])

        for obj in widgets[1:]:
            grant_role(self.editor["role"], obj, self.editor["user"])

        grant_role(self.owner["role"], widgets[2], self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertNotIn(widgets[0].gql_id, [data["node"]["id"] for data in result["data"]["allWidgets"]["edges"]])

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        for widget in widgets:
            self.assertIn(widget.gql_id, [data["node"]["id"] for data in result["data"]["allWidgets"]["edges"]])

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        for widget in widgets[1:]:
            self.assertIn(widget.gql_id, [data["node"]["id"] for data in result["data"]["allWidgets"]["edges"]])
        self.assertNotIn(widgets[0].gql_id, [data["node"]["id"] for data in result["data"]["allWidgets"]["edges"]])

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertIn(widgets[2].gql_id, [data["node"]["id"] for data in result["data"]["allWidgets"]["edges"]])
        self.assertNotIn(widgets[0].gql_id, [data["node"]["id"] for data in result["data"]["allWidgets"]["edges"]])


class TestCreateWidget(GQLTestCase):
    node_name = 'WidgetNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """
mutation CreateWidget($name: String, $comment: String, $external: Boolean, $code: String, $frontend: ID!) {
    createWidget(input: {
        name: $name
        comment: $comment
        external: $external
        code: $code
        frontend: $frontend
    }) {
        widgetEdge {
            node {
                id
                name
                comment
                events { edges{ node{ steps{ edges{ node{ id }}}}}}
                external
                code
            }
        }
    }
}
"""
        cls.td = {
            "name": "TestCreateRequiresPrivileges",
            "comment": "you shall not haz",
            "external": False,
            "code": "do_the_codes()",
            "frontend": FrontendFactory().gql_id,
        }

    def test_create_produces_results(self):
        result = self.gql_client.execute(
            self.query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )

        self.fail_on_errors(result)

        self.td.pop('frontend')

        for field in self.td:
            self.assertEqual(result['data']['createWidget']['widgetEdge']['node'][field], self.td[field])

        lookup = Widget.objects.get(name=self.td['name'])

        for field in self.td:
            self.assertEqual(getattr(lookup, field, None), self.td[field])


class TestUpdateWidget(GQLTestCase):
    node_name = 'WidgetNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.widget = WidgetFactory(external=True)
        self.td = {'gql_id': self.widget.gql_id, 'name': "TestUpdateRequiresPrivilege", 'comment': "don't do the update"}
        self.query = """mutation UpdateWidget($gql_id: ID!, $name: String, $comment: String)
                   { updateWidget(input: {
                   id: $gql_id
                   name: $name
                   comment: $comment})
                   {widget {id name comment}}}
                """

    def test_update_requires_privilege(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner['role'], self.widget, self.owner['user'])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop('gql_id')
        for field in self.td:
            self.assertEqual(result['data']['updateWidget']['widget'][field], self.td[field])

        self.widget.refresh_from_db()
        for field in self.td:
            self.assertEqual(getattr(self.widget, field, None), self.td[field], msg="mismatch on %s" % (field,))


class TestDeleteWidget(GQLTestCase):
    node_name = 'WidgetNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        widget = WidgetFactory(external=True)
        grant_role(self.viewer['role'], widget, self.viewer['user'])
        td = {"gql_id": widget.gql_id}

        query = """mutation DeleteWidget($gql_id: ID!){deleteWidget(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_delete_produces_result(self):
        widget = WidgetFactory(external=True)
        grant_role(self.owner['role'], widget, self.owner['user'])
        td = {"gql_id": widget.gql_id}

        query = """mutation DeleteWidget($gql_id: ID!){deleteWidget(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result['data']['deleteWidget']['id'])

        widget.refresh_from_db()
        self.assertEqual(widget.state, widget.STATE_CHOICES.deleted)


class TestReadWidgetEvent(GQLTestCase):
    """Ensure reading WidgetEvent works"""

    node_name = "WidgetEventNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allWidgetEvents query without a user is unauthorized"""
        query = """{allWidgetEvents{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        widget_event = WidgetEventFactory()
        td = {"widgeteventid": widget_event.gql_id}

        query = """query WidgetEventsQuery($widgeteventid: ID!){widgetEvent(id: $widgeteventid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allWidgetEvents{ edges{ node{ id }}}}"""
        widget_events = [WidgetEventFactory() for _ in range(3)]

        for obj in widget_events:
            grant_role(self.viewer["role"], obj.widget, self.viewer["user"])

        for obj in widget_events[1:]:
            grant_role(self.editor["role"], obj.widget, self.editor["user"])

        grant_role(self.owner["role"], widget_events[2].widget, self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allWidgetEvents"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allWidgetEvents"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allWidgetEvents"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allWidgetEvents"]["edges"]), 1)


class TestCreateWidgetEvent(GQLTestCase):
    node_name = 'WidgetEventNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """
mutation CreateWidgetEvent($name: String, $event_type: String, $widget: ID!) {
    createWidgetEvent(input: {
        name: $name
        eventType: $event_type
        widget: $widget
    }) {
        widgetEventEdge {
            node {
                id
                name
                steps { edges{ node{ id }}}
                widget { id }
            }
        }
    }
}
"""
        widget = WidgetFactory(frontend=Frontend.objects.get(name='Web'))
        grant_role(cls.owner['role'], widget, cls.owner['user'])
        cls.td = {"name": "prefix", "widget": widget.gql_id, "event_type": WidgetEvent.REACT_EVENT_CHOICES.onChange}

    def test_create_produces_results(self):
        result = self.gql_client.execute(
            self.query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )

        self.fail_on_errors(result)

        self.td.pop('widget')
        self.td.pop('event_type')

        for field in self.td:
            self.assertEqual(result['data']['createWidgetEvent']['widgetEventEdge']['node'][field], self.td[field])

        lookup = WidgetEvent.objects.get(name=self.td['name'])

        for field in self.td:
            self.assertEqual(getattr(lookup, field, None), self.td[field])


class TestUpdateWidgetEvent(GQLTestCase):
    node_name = 'WidgetEventNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.widget = WidgetFactory(frontend=Frontend.objects.get(name='Web'))
        self.widget_event = WidgetEventFactory(widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)
        self.td = {'gql_id': self.widget_event.gql_id, 'event_type': WidgetEvent.REACT_EVENT_CHOICES.onSubmit}
        self.query = """mutation UpdateWidgetEvent($gql_id: ID!, $event_type: String)
                   { updateWidgetEvent(input: {
                   id: $gql_id
                   eventType: $event_type
                   })
                   {widgetEvent { widget{ id } id eventType steps{ edges{ node{ id }}} }}}
                """

    def test_update_requires_privilege(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner['role'], self.widget_event.widget, self.owner['user'])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop('gql_id')
        self.td.pop('event_type')

        for field in self.td:
            field_result = result['data']['updateWidgetEvent']['widgetEvent'][field]
            self.assertEqual(field_result, self.td[field].upper())  # Due to uppercase choice result returned by gql
            self.assertEqual(
                result['data']['updateWidgetEvent']['widgetEvent']['eventType'], self.td['event_type'].upper()
            )  # Due to uppercase choice result returned by gql

        self.widget_event.refresh_from_db()
        for field in self.td:
            self.assertEqual(getattr(self.widget_event, field, None), self.td[field], msg="mismatch on %s" % (field,))


class TestDeleteWidgetEvent(GQLTestCase):
    node_name = 'WidgetEventNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        widget_event = WidgetEventFactory()
        grant_role(self.viewer['role'], widget_event.widget, self.viewer['user'])
        td = {"gql_id": widget_event.gql_id}

        query = """mutation DeleteWidgetEvent($gql_id: ID!){deleteWidgetEvent(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_delete_produces_result(self):
        widget_event = WidgetEventFactory()
        grant_role(self.owner['role'], widget_event.widget, self.owner['user'])
        td = {"gql_id": widget_event.gql_id}

        query = """mutation DeleteWidgetEvent($gql_id: ID!){deleteWidgetEvent(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result['data']['deleteWidgetEvent']['id'])
        self.assertRaises(WidgetEvent.DoesNotExist, WidgetEvent.objects.get, **{'pk': widget_event.id})


class TestReadWidgetEventStep(GQLTestCase):
    """Ensure reading WidgetEventStep works"""

    node_name = "WidgetEventStepNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allWidgetEvents query without a user is unauthorized"""
        query = """{allWidgetEventSteps{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        widget_event_step = WidgetEventStepFactory()
        td = {"widgeteventstepid": widget_event_step.gql_id}

        query = """query WidgetEventStep($widgeteventstepid: ID!){widgetEventStep(id: $widgeteventstepid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allWidgetEventSteps{ edges{ node{ id }}}}"""
        widget_event_steps = [WidgetEventStepFactory() for _ in range(3)]

        for obj in widget_event_steps:
            grant_role(self.viewer["role"], obj.widget_event.widget, self.viewer["user"])

        for obj in widget_event_steps[1:]:
            grant_role(self.editor["role"], obj.widget_event.widget, self.editor["user"])

        grant_role(self.owner["role"], widget_event_steps[2].widget_event.widget, self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allWidgetEventSteps"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allWidgetEventSteps"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allWidgetEventSteps"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allWidgetEventSteps"]["edges"]), 1)


class TestCreateWidgetEventStep(GQLTestCase):
    node_name = 'WidgetEventStepNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """
mutation CreateWidgetEventStep($event_action_type: String, $code: String, $widget_event: ID!) {
    createWidgetEventStep(input: {
        eventActionType: $event_action_type
        code: $code
        widgetEvent: $widget_event
    }) {
        widgetEventStepEdge {
            node {
                id
                eventActionType
                code
                widgetEvent { id }
            }
        }
    }
}
"""
        widget = WidgetFactory(frontend=Frontend.objects.get(name='Web'))
        widget_event = WidgetEventFactory(widget=widget)
        grant_role(cls.owner['role'], widget_event.get_privilege_ancestor(), cls.owner['user'])
        cls.td = {
            "code": "run_the_codes()",
            "widget_event": widget_event.gql_id,
            "event_action_type": WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
        }

    def test_create_produces_results(self):
        result = self.gql_client.execute(
            self.query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )

        self.fail_on_errors(result)

        self.td.pop('widget_event')
        self.td.pop('event_action_type')

        for field in self.td:
            self.assertEqual(result['data']['createWidgetEventStep']['widgetEventStepEdge']['node'][field], self.td[field])

        lookup = WidgetEventStep.objects.get(code=self.td['code'])

        for field in self.td:
            self.assertEqual(getattr(lookup, field, None), self.td[field])


class TestUpdateWidgetEventStep(GQLTestCase):
    node_name = 'WidgetEventStepNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.widget_event_step = WidgetEventStepFactory(event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code)
        self.td = {'gql_id': self.widget_event_step.gql_id, 'code': "run_the_codes()"}
        self.query = """mutation UpdateWidgetEventStep($gql_id: ID!, $code: String)
                   { updateWidgetEventStep(input: {
                   id: $gql_id
                   code: $code
                   })
                   {widgetEventStep {id code }}}
                """

    def test_update_requires_privilege(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner['role'], self.widget_event_step.widget_event.widget, self.owner['user'])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop('gql_id')
        for field in self.td:
            self.assertEqual(result['data']['updateWidgetEventStep']['widgetEventStep'][field], self.td[field])

        self.widget_event_step.refresh_from_db()
        for field in self.td:
            self.assertEqual(getattr(self.widget_event_step, field, None), self.td[field], msg="mismatch on %s" % (field,))


class TestDeleteWidgetEventStep(GQLTestCase):
    node_name = 'WidgetEventStepNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        widget_event_step = WidgetEventStepFactory()
        grant_role(self.viewer['role'], widget_event_step.get_privilege_ancestor(), self.viewer['user'])
        td = {"gql_id": widget_event_step.gql_id}

        query = """mutation DeleteWidgetEventStep($gql_id: ID!){deleteWidgetEventStep(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_delete_produces_result(self):
        widget_event_step = WidgetEventStepFactory()
        grant_role(self.owner['role'], widget_event_step.get_privilege_ancestor(), self.owner['user'])
        td = {"gql_id": widget_event_step.gql_id}

        query = """mutation DeleteWidgetEventStep($gql_id: ID!){deleteWidgetEventStep(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result['data']['deleteWidgetEventStep']['id'])
        self.assertRaises(WidgetEventStep.DoesNotExist, WidgetEventStep.objects.get, **{'pk': widget_event_step.id})


@unittest.skip("Address in issue #395")
class TestPreviewWidget(GQLTestCase):
    """
    Confirm preview code is requested from babel or engine based on frontend.
    """

    node_name = "WidgetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1, signal_pubsub=False).first()

    # @mock.patch('ery_backend.widgets.models.Widget.preview', autospec=True)
    def test_web_frontend(self, mock_preview):
        frontend = Frontend.objects.get(name='Web')
        widget = WidgetFactory(frontend=frontend)
        grant_role(self.viewer["role"], widget, self.viewer["user"])
        td = {
            "widgetid": widget.gql_id,
            "handid": self.hand.gql_id,
        }

        query = """query WidgetQuery($handid: ID!, $widgetid: ID!){widget(id: $widgetid){ preview(hand: $handid) }}"""
        self.gql_client.execute(query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        mock_preview.assert_called_with(widget, self.hand)

    # @mock.patch('ery_backend.widgets.models.Widget.preview', autospec=True)
    def test_sms_frontend(self, mock_preview):
        frontend = Frontend.objects.get(name='SMS')
        widget = WidgetFactory(frontend=frontend)
        grant_role(self.viewer["role"], widget, self.viewer["user"])
        td = {
            "widgetid": widget.gql_id,
            "handid": self.hand.gql_id,
        }

        query = """query WidgetQuery($handid: ID!, $widgetid: ID!){widget(id: $widgetid){ preview(hand: $handid) }}"""
        self.gql_client.execute(query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        mock_preview.assert_called_with(widget, self.hand)


class TestAllConnectedWidgets(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_ids_same_as_nested_connected_widget_ids(self):
        widget = WidgetFactory()
        td = {'widgetid': widget.gql_id}
        grant_role(self.owner['role'], widget, self.owner['user'])
        nested_widgets = [
            WidgetConnectionFactory(originator=widget, target=WidgetFactory(frontend=widget.frontend)).target
            for _ in range(random.randint(1, 10))
        ]
        for _ in range(random.randint(1, 10)):
            nested_widgets.append(
                WidgetConnectionFactory(
                    originator=random.choice(nested_widgets), target=WidgetFactory(frontend=widget.frontend)
                ).target
            )

        query = """
query ConnectedWidgets($widgetid: ID!){
    widget(id: $widgetid){
        allConnectedWidgets{
            id
        }
    }
}"""
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        result_ids = [data['id'] for data in result['data']['widget']['allConnectedWidgets']]

        for widget in nested_widgets:
            self.assertIn(widget.gql_id, result_ids)
