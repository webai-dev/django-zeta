import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.actions.factories import ActionFactory
from ery_backend.base.testcases import GQLTestCase
from ery_backend.frontends.models import Frontend
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import ModuleDefinitionWidgetMutation, ModuleEventMutation, ModuleEventStepMutation
from ery_backend.roles.utils import grant_role
from ery_backend.users.schema import ViewerQuery
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.widgets.factories import WidgetFactory

from ..factories import ModuleDefinitionWidgetFactory, ModuleEventFactory, ModuleEventStepFactory
from ..models import ModuleDefinitionWidget, ModuleEvent, ModuleEventStep
from ..widget_schema import ModuleDefinitionWidgetQuery, ModuleEventQuery, ModuleEventStepQuery


class TestQuery(ModuleDefinitionWidgetQuery, ModuleEventQuery, ModuleEventStepQuery, ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(ModuleDefinitionWidgetMutation, ModuleEventMutation, ModuleEventStepMutation, graphene.ObjectType):
    pass


class TestReadModuleDefinitionWidget(GQLTestCase):
    """Ensure reading ModuleDefinitionWidget works"""

    node_name = "ModuleDefinitionWidgetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = """{allModuleDefinitionWidgets{ edges{ node{ id }}}}"""
        cls.node_query = """query ModuleDefinitionWidgetQuery($moduledefinitionwidgetid: ID!){
            moduleDefinitionWidget(id: $moduledefinitionwidgetid){
                           variableDefinition { id }
                           widget { id }
                           moduleDefinition { id } }}"""

    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.module_definition_widget = ModuleDefinitionWidgetFactory(module_definition=self.module_definition)
        self.td = {
            "moduledefinitionwidgetid": self.module_definition_widget.gql_id,
            'module_definition': self.module_definition.gql_id,
        }

    def test_read_all_requires_login(self):
        """allModuleDefinitionWidgets query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        result = self.gql_client.execute(self.node_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        module_definition_widgets = [ModuleDefinitionWidgetFactory() for _ in range(3)]

        for obj in module_definition_widgets:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in module_definition_widgets[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], module_definition_widgets[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitionWidgets"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitionWidgets"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitionWidgets"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleDefinitionWidgets"]["edges"]), 1)

    def test_read_node_works(self):
        grant_role(self.viewer["role"], self.module_definition_widget.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.node_query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(
            int(from_global_id(result["data"]["moduleDefinitionWidget"]["variableDefinition"]["id"])[1]),
            self.module_definition_widget.variable_definition.id,
        )
        self.assertEqual(
            int(from_global_id(result["data"]["moduleDefinitionWidget"]["widget"]["id"])[1]),
            self.module_definition_widget.widget.id,
        )
        self.assertEqual(
            int(from_global_id(result["data"]["moduleDefinitionWidget"]["moduleDefinition"]["id"])[1]),
            self.module_definition_widget.module_definition.id,
        )


class TestCreateModuleDefinitionWidget(GQLTestCase):
    node_name = "ModuleDefinitionWidgetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.variable_definition = VariableDefinitionFactory(module_definition=self.module_definition)
        self.widget = WidgetFactory()
        self.td = {
            'moduleDefinition': self.module_definition.gql_id,
            'variableDefinition': self.variable_definition.gql_id,
            'widget': self.widget.gql_id,
            'name': 'TestModuleDefinitionWidgets',
        }

        self.query = """
mutation ($moduleDefinition: ID!, $variableDefinition: ID!, $widget: ID!, $name: String!) {
    createModuleDefinitionWidget(input: {
        moduleDefinition: $moduleDefinition,
        widget: $widget,
        variableDefinition: $variableDefinition,
        name: $name
    }) {
        moduleDefinitionWidgetEdge {
            node {
                id
                name
            }
        }
    }
}
"""

    def test_create_requires_privilege(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(ModuleDefinitionWidget.DoesNotExist, ModuleDefinitionWidget.objects.get, **{"name": self.td["name"]})

    def test_create_produces_result(self):
        grant_role(self.owner["role"], self.module_definition, self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)
        lookup = ModuleDefinitionWidget.objects.get(name=self.td["name"])

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.module_definition, self.module_definition)
        self.assertEqual(lookup.widget, self.widget)
        self.assertEqual(lookup.variable_definition, self.variable_definition)


class TestUpdateModuleDefinitionWidget(GQLTestCase):
    node_name = "ModuleDefinitionWidgetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        module_definition = ModuleDefinitionFactory()
        self.variable_definition = VariableDefinitionFactory(module_definition=module_definition)
        self.module_definition_widget = ModuleDefinitionWidgetFactory(module_definition=module_definition)
        self.widget = WidgetFactory()
        self.td = {
            "module_definition_widget": self.module_definition_widget.gql_id,
            "name": "TestModuleDefinitionWidget",
            "variableDefinition": self.variable_definition.gql_id,
            "widget": self.widget.gql_id,
        }
        self.query = """mutation ($module_definition_widget: ID!, $name: String!, $variableDefinition: ID!, $widget: ID!){
             updateModuleDefinitionWidget(input: {
                id: $module_definition_widget,
                name: $name,
                widget: $widget,
                variableDefinition: $variableDefinition
                    })
                    {moduleDefinitionWidget
                        { id }}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.module_definition_widget.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.module_definition_widget.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = ModuleDefinitionWidget.objects.get(pk=self.module_definition_widget.id)

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.widget, self.widget)
        self.assertEqual(lookup.variable_definition, self.variable_definition)


class TestDeleteModuleDefinitionWidget(GQLTestCase):
    node_name = "ModuleDefinitionWidgetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.module_definition_widget = ModuleDefinitionWidgetFactory()
        self.td = {"module_definition_widget": self.module_definition_widget.gql_id}
        self.query = """
mutation ($module_definition_widget: ID!) {
    deleteModuleDefinitionWidget(input: {
        id: $module_definition_widget,
    }) {
        id
    }
}
"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.module_definition_widget.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )

        self.assert_query_was_unauthorized(result)

        ModuleDefinitionWidget.objects.get(pk=self.module_definition_widget.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.module_definition_widget.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteModuleDefinitionWidget"]["id"])

        self.assertRaises(
            ModuleDefinitionWidget.DoesNotExist, ModuleDefinitionWidget.objects.get, **{"pk": self.module_definition_widget.id}
        )


class TestReadModuleEvent(GQLTestCase):
    """Ensure reading ModuleEvent works"""

    node_name = "ModuleEventNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allModuleEvents query without a user is unauthorized"""
        query = """{allModuleEvents{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        module_event = ModuleEventFactory()
        td = {"moduleeventid": module_event.gql_id}

        query = """query ModuleEventsQuery($moduleeventid: ID!){moduleEvent(id: $moduleeventid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allModuleEvents{ edges{ node{ id }}}}"""
        module_events = [ModuleEventFactory() for _ in range(3)]

        for obj in module_events:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in module_events[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], module_events[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleEvents"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleEvents"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleEvents"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleEvents"]["edges"]), 1)


class TestCreateModuleEvent(GQLTestCase):
    node_name = 'ModuleEventNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """
mutation CreateModuleEvent($name: String, $event_type: String, $widget: ID!) {
    createModuleEvent(input: {
        name: $name
        eventType: $event_type
        widget: $widget
    }) {
        moduleEventEdge {
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
        module_widget = ModuleDefinitionWidgetFactory(widget=widget)
        grant_role(cls.owner['role'], module_widget.get_privilege_ancestor(), cls.owner['user'])
        cls.td = {"name": "prefix", "widget": module_widget.gql_id, "event_type": ModuleEvent.REACT_EVENT_CHOICES.onChange}

    def test_create_produces_results(self):
        result = self.gql_client.execute(
            self.query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )

        self.fail_on_errors(result)

        self.td.pop('widget')
        self.td.pop('event_type')

        for field in self.td:
            self.assertEqual(result['data']['createModuleEvent']['moduleEventEdge']['node'][field], self.td[field])

        lookup = ModuleEvent.objects.get(name=self.td['name'])

        for field in self.td:
            self.assertEqual(getattr(lookup, field, None), self.td[field])


class TestUpdateModuleEvent(GQLTestCase):
    node_name = 'ModuleEventNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        widget = WidgetFactory(frontend=Frontend.objects.get(name='Web'))
        module_widget = ModuleDefinitionWidgetFactory(widget=widget)
        self.module_event = ModuleEventFactory(widget=module_widget, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange)
        self.td = {'gql_id': self.module_event.gql_id, 'event_type': ModuleEvent.REACT_EVENT_CHOICES.onSubmit}
        self.query = """mutation UpdateModuleEvent($gql_id: ID!, $event_type: String)
                   { updateModuleEvent(input: {
                   id: $gql_id
                   eventType: $event_type
                   })
                   {moduleEvent { widget{ id } id eventType steps{ edges{ node{ id }}} }}}
                """

    def test_update_requires_privilege(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner['role'], self.module_event.get_privilege_ancestor(), self.owner['user'])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop('gql_id')
        self.td.pop('event_type')

        for field in self.td:
            field_result = result['data']['updateModuleEvent']['moduleEvent'][field]
            self.assertEqual(field_result, self.td[field].upper())  # Due to uppercase choice result returned by gql
            self.assertEqual(
                result['data']['updateModuleEvent']['moduleEvent']['eventType'], self.td['event_type'].upper()
            )  # Due to uppercase choice result returned by gql

        self.module_event.refresh_from_db()
        for field in self.td:
            self.assertEqual(getattr(self.module_event, field, None), self.td[field], msg="mismatch on %s" % (field,))


class TestDeleteModuleEvent(GQLTestCase):
    node_name = 'ModuleEventNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        module_event = ModuleEventFactory()
        grant_role(self.viewer['role'], module_event.get_privilege_ancestor(), self.viewer['user'])
        td = {"gql_id": module_event.gql_id}

        query = """mutation DeleteModuleEvent($gql_id: ID!){deleteModuleEvent(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_delete_produces_result(self):
        module_event = ModuleEventFactory()
        grant_role(self.owner['role'], module_event.get_privilege_ancestor(), self.owner['user'])
        td = {"gql_id": module_event.gql_id}

        query = """mutation DeleteModuleEvent($gql_id: ID!){deleteModuleEvent(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result['data']['deleteModuleEvent']['id'])
        self.assertRaises(ModuleEvent.DoesNotExist, ModuleEvent.objects.get, **{'pk': module_event.id})


class TestReadModuleEventStep(GQLTestCase):
    """Ensure reading ModuleEventStep works"""

    node_name = "ModuleEventStepNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allModuleEvents query without a user is unauthorized"""
        query = """{allModuleEventSteps{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        module_event_step = ModuleEventStepFactory()
        td = {"moduleeventstepid": module_event_step.gql_id}

        query = """query ModuleEventStep($moduleeventstepid: ID!){moduleEventStep(id: $moduleeventstepid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allModuleEventSteps{ edges{ node{ id }}}}"""
        module_event_steps = [ModuleEventStepFactory() for _ in range(3)]

        for obj in module_event_steps:
            grant_role(self.viewer["role"], obj.module_event.get_privilege_ancestor(), self.viewer["user"])

        for obj in module_event_steps[1:]:
            grant_role(self.editor["role"], obj.module_event.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], module_event_steps[2].module_event.get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleEventSteps"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleEventSteps"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleEventSteps"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allModuleEventSteps"]["edges"]), 1)


class TestCreateModuleEventStep(GQLTestCase):
    node_name = 'ModuleEventStepNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """
mutation CreateModuleEventStep($event_action_type: String, $action: ID!, $module_event: ID!) {
    createModuleEventStep(input: {
        eventActionType: $event_action_type
        action: $action
        moduleEvent: $module_event
    }) {
        moduleEventStepEdge {
            node {
                id
                eventActionType
                action { id }
                moduleEvent { id }
            }
        }
    }
}
"""
        widget = WidgetFactory(frontend=Frontend.objects.get(name='Web'))
        module_widget = ModuleDefinitionWidgetFactory(widget=widget)
        module_event = ModuleEventFactory(widget=module_widget)
        cls.action = ActionFactory(module_definition=module_event.get_privilege_ancestor())
        grant_role(cls.owner['role'], module_event.get_privilege_ancestor(), cls.owner['user'])
        cls.td = {
            "action": cls.action.gql_id,
            "module_event": module_event.gql_id,
            "event_action_type": ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action,
        }

    def test_create_produces_results(self):
        result = self.gql_client.execute(
            self.query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=self.td
        )

        self.fail_on_errors(result)

        self.td.pop('module_event')
        self.td.pop('event_action_type')
        self.td.pop('action')

        for field in self.td:
            self.assertEqual(result['data']['createModuleEventStep']['moduleEventStepEdge']['node'][field], self.td[field])

        lookup = ModuleEventStep.objects.get(action=self.action)

        for field in self.td:
            self.assertEqual(getattr(lookup, field, None), self.td[field])


class TestUpdateModuleEventStep(GQLTestCase):
    node_name = 'ModuleEventStepNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.module_event_step = ModuleEventStepFactory(event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action)
        action = ActionFactory(module_definition=self.module_event_step.get_privilege_ancestor())
        grant_role(self.owner['role'], self.module_event_step.get_privilege_ancestor(), self.owner['user'])
        self.td = {'gql_id': self.module_event_step.gql_id, 'action': action.gql_id}
        self.query = """mutation UpdateModuleEventStep($gql_id: ID!, $action: ID!)
                   { updateModuleEventStep(input: {
                   id: $gql_id
                   action: $action
                   })
                   {moduleEventStep { id action{ id } }}}
                """

    def test_update_requires_privilege(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner['role'], self.module_event_step.module_event.get_privilege_ancestor(), self.owner['user'])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop('gql_id')
        self.td.pop('action')

        for field in self.td:
            self.assertEqual(result['data']['updateModuleEventStep']['moduleEventStep'][field], self.td[field])

        self.module_event_step.refresh_from_db()
        for field in self.td:
            self.assertEqual(getattr(self.module_event_step, field, None), self.td[field], msg="mismatch on %s" % (field,))


class TestDeleteModuleEventStep(GQLTestCase):
    node_name = 'ModuleEventStepNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        module_event_step = ModuleEventStepFactory()
        grant_role(self.viewer['role'], module_event_step.get_privilege_ancestor(), self.viewer['user'])
        td = {"gql_id": module_event_step.gql_id}

        query = """mutation DeleteModuleEventStep($gql_id: ID!){deleteModuleEventStep(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_delete_produces_result(self):
        module_event_step = ModuleEventStepFactory()
        grant_role(self.owner['role'], module_event_step.get_privilege_ancestor(), self.owner['user'])
        td = {"gql_id": module_event_step.gql_id}

        query = """mutation DeleteModuleEventStep($gql_id: ID!){deleteModuleEventStep(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result['data']['deleteModuleEventStep']['id'])
        self.assertRaises(ModuleEventStep.DoesNotExist, ModuleEventStep.objects.get, **{'pk': module_event_step.id})
