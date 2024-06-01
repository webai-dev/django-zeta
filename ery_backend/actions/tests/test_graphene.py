from string import Template

import graphene

from ery_backend.mutations import ActionMutation, ActionStepMutation
from ery_backend.base.testcases import GQLTestCase, create_revisions
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.syncs.factories import EraFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.roles.utils import grant_role

from ..models import Action, ActionStep
from ..factories import ActionFactory, ActionStepFactory
from ..schema import ActionQuery, ActionStepQuery


class TestQuery(ActionQuery, ActionStepQuery, graphene.ObjectType):
    pass


class TestMutation(ActionMutation, ActionStepMutation, graphene.ObjectType):
    pass


class TestReadAction(GQLTestCase):
    """Ensure Reading Works"""

    node_name = 'ActionNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_all_requires_login(self):
        action = ActionFactory()
        grant_role(self.viewer['role'], action.module_definition, self.viewer['user'])

        query = """{allActions {edges {node {id name comment}}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        query = """query ActionQuery($gql_id: ID!){action(id: $gql_id){ id name comment }}"""

        result = self.gql_client.execute(query, variable_values={"gql_id": action.gql_id})
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        actions = [ActionFactory(), ActionFactory(), ActionFactory()]
        for action in actions:
            grant_role(self.viewer['role'], action.module_definition, self.viewer['user'])

        for action in actions[1:]:
            grant_role(self.editor['role'], action.module_definition, self.editor['user'])

        grant_role(self.owner['role'], actions[2].module_definition, self.owner['user'])

        query = '''{allActions {edges {node {id name comment}}}}'''

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        # includes autocreated actions belonging to module_definitions
        self.assertEqual(len(result['data']['allActions']['edges']), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result['data']['allActions']['edges']), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result['data']['allActions']['edges']), 1)


class TestCreateAction(GQLTestCase):
    node_name = 'ActionNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_privileges(self):
        md = ModuleDefinitionFactory()
        grant_role(self.viewer["role"], md, self.viewer["user"])

        td = {"md_id": md.gql_id, "name": "test create requires privileges", "comment": "you shall not haz"}

        query = """
mutation CreateAction($md_id: ID!, $name: String, $comment: String) {
    createAction(input: {
        moduleDefinition: $md_id
        name: $name
        comment: $comment
    }) {
        actionEdge {
            node {
                id
                name
                comment
            }
        }
    }
}
"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_results(self):
        md = ModuleDefinitionFactory()
        grant_role(self.owner['role'], md, self.owner['user'])

        td = {'md_id': md.gql_id, 'name': "test create produces result", 'comment': "it has been created"}

        query = """
mutation CreatAction($md_id: ID!, $name: String, $comment: String) {
    createAction(input: {
        moduleDefinition: $md_id,
        name: $name,
        comment: $comment
    }){
        actionEdge {
            node {
                id
                name
                comment
            }
        }
    }
}"""

        result = self.gql_client.execute(
            query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=td
        )

        self.fail_on_errors(result)
        td.pop("md_id")

        for field in td:
            self.assertEqual(result['data']['createAction']['actionEdge']['node'][field], td[field])

        lookup = Action.objects.get(name=td['name'])

        for field in td:
            self.assertEqual(getattr(lookup, field, None), td[field])

        self.assertEqual(lookup.module_definition.pk, md.pk)


class TestUpdateAction(GQLTestCase):
    node_name = 'ActionNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        action = ActionFactory()
        grant_role(self.viewer['role'], action.module_definition, self.viewer['user'])

        td = {'gql_id': action.gql_id, 'name': "test update requires privilege", 'comment': "don't do the update"}

        query = """mutation UpdateAction($gql_id: ID!, $name: String, $comment: String)
                   { updateAction(input: {
                   id: $gql_id
                   name: $name
                   comment: $comment})
                   {action {id name comment}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        action = ActionFactory()
        grant_role(self.owner['role'], action.module_definition, self.owner['user'])
        td = {'gql_id': action.gql_id, 'name': "test update produces result", 'comment': "good to go"}

        query = """mutation UpdateAction($gql_id: ID!, $name: String, $comment: String)
                   { updateAction(input: {
                   id: $gql_id
                   name: $name 
                   comment: $comment})
                   {action {id name comment}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        td.pop('gql_id')
        for field in td:
            self.assertEqual(result['data']['updateAction']['action'][field], td[field])

        action.refresh_from_db()
        for field in td:
            self.assertEqual(getattr(action, field, None), td[field], msg="mismatch on %s" % (field,))


class TestDeleteAction(GQLTestCase):
    node_name = 'ActionNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        action = ActionFactory()
        grant_role(self.viewer['role'], action.module_definition, self.viewer['user'])
        td = {"gql_id": action.gql_id}

        query = """mutation DeleteAction($gql_id: ID!){deleteAction(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_delete_produces_result(self):
        action = ActionFactory()
        grant_role(self.owner['role'], action.module_definition, self.owner['user'])
        td = {"gql_id": action.gql_id}

        query = """mutation DeleteAction($gql_id: ID!){deleteAction(input: {id: $gql_id}){id}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result['data']['deleteAction']['id'])
        self.assertRaises(Action.DoesNotExist, Action.objects.get, **{'pk': action.id})


class TestReadActionStep(GQLTestCase):
    node_name = 'ActionStepNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        action_step = ActionStepFactory()
        gql_id = action_step.gql_id

        query = """{allActionSteps{ edges { node { id order invertCondition }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        query = """query ActionStep($gql_id: ID!){actionStep(id: $gql_id){id order invertCondition}}"""
        self.gql_client.execute(query, variable_values={"gql_id": gql_id})
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        action_steps = [ActionStepFactory(), ActionStepFactory(), ActionStepFactory()]

        for action_step in action_steps:
            grant_role(self.viewer['role'], action_step.action.module_definition, self.viewer['user'])

        for action_step in action_steps[1:]:
            grant_role(self.editor['role'], action_step.action.module_definition, self.editor['user'])

        grant_role(self.owner['role'], action_steps[2].action.module_definition, self.owner['user'])

        query = """{allActionSteps{ edges { node { id order }}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        # includes actionsteps belonging to actions belonging to module definition commands
        self.assertEqual(len(result['data']['allActionSteps']['edges']), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result['data']['allActionSteps']['edges']), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result['data']['allActionSteps']['edges']), 1)

    def test_general_version_nodes(self):
        """
        Get all version nodes from multiple actionsteps.
        """
        actionstep_1 = ActionStepFactory()
        actionstep_2 = ActionStepFactory()
        create_revisions([{'obj': actionstep_1, 'attr': 'log_message'}], 2, user=self.editor['user'])
        create_revisions([{'obj': actionstep_2, 'attr': 'log_message'}], 3, user=self.editor['user'])
        for actionstep in [actionstep_1, actionstep_2]:
            grant_role(self.editor['role'], actionstep.action.module_definition, self.editor['user'])
        query = """{allActionSteps{ edges{ node{ versions{ edges{ node{ id }}}}}}}"""

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)

        # the number of version nodes should match the number of revisions created for object
        actionstep_1_version_node_ids = self.get_version_node_ids(actionstep_1)
        actionstep_2_version_node_ids = self.get_version_node_ids(actionstep_2)
        version_node_ids = list()
        result_edges = result['data']['allActionSteps']['edges']
        for result_edge in result_edges:
            version_node_ids += [node_edge['node']['id'] for node_edge in result_edge['node']['versions']['edges']]
        for actionstep_1_version_node_id in actionstep_1_version_node_ids:
            self.assertIn(actionstep_1_version_node_id, version_node_ids)
        for actionstep_2_version_node_id in actionstep_2_version_node_ids:
            self.assertIn(actionstep_2_version_node_id, version_node_ids)


class TestCreateActionStep(GQLTestCase):
    node_name = "ActionStepNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_action_step_requires_privilege(self):
        """
        Only a privileged user should be able to create ActionSteps
        """
        action = ActionFactory()
        md = action.module_definition

        subaction = ActionFactory(module_definition=md)

        condition = ConditionFactory(module_definition=md)

        era = EraFactory(module_definition=md)

        vd = VariableDefinitionFactory(module_definition=md)

        grant_role(self.viewer["role"], md, self.viewer["user"])

        test_ids = {
            "action": action.gql_id,
            "subaction": subaction.gql_id,
            "condition": condition.gql_id,
            "era": era.gql_id,
            "variableDefinition": vd.gql_id,
        }

        query = Template(
            """
mutation {
    createActionStep(input: {
        action: "$action",
        subaction: "$subaction",
        condition: "$condition",
        era: "$era",
        variableDefinition: "$variableDefinition"
    }) {
        actionStepEdge {
            node {
                id
            }
        }
    }
}
"""
        ).substitute(**test_ids)

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_create_action_step_produces_result(self):
        """
        Only a privileged user should be able to create ActionSteps
        """
        action = ActionFactory()
        md = action.module_definition

        subaction = ActionFactory(module_definition=md)

        condition = ConditionFactory(module_definition=md)

        era = EraFactory(module_definition=md)

        vd = VariableDefinitionFactory(module_definition=md)

        grant_role(self.owner["role"], md, self.owner["user"])

        test_ids = {
            "action": action.gql_id,
            "subaction": subaction.gql_id,
            "condition": condition.gql_id,
            "era": era.gql_id,
            "variableDefinition": vd.gql_id,
        }

        query = Template(
            """
mutation {
    createActionStep(input: {
        action: "$action",
        actionType: "setVariable",
        subaction: "$subaction",
        condition: "$condition",
        era: "$era",
        variableDefinition: "$variableDefinition"
        value: "my_value"
    }) {
        actionStepEdge {
            node {
                id
            }
        }
    }
}"""
        ).substitute(**test_ids)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        lookup = ActionStep.objects.get(action=action, condition=condition, era=era)

        self.assertEqual(result['data']['createActionStep']['actionStepEdge']['node']['id'], lookup.gql_id)


class TestUpdateActionStep(GQLTestCase):
    node_name = "ActionStepNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        action_step1 = ActionStepFactory()

        grant_role(self.viewer["role"], action_step1.action.module_definition, self.viewer["user"])

        action_step2 = ActionStepFactory()
        td = {
            "order": action_step2.order,
            "forEach": action_step2.for_each,
            "value": action_step2.value,
            "code": action_step2.code,
            "logMessage": action_step2.log_message,
        }

        query = Template(
            """mutation{ updateActionStep(input: {
            id: "$as_gql_id",
            order: $order,
            forEach: "$forEach",
            code: "$code",
            value: "$value",
            logMessage: "$logMessage"}){ actionStep {
            order invertCondition forEach code logMessage }}}
            """
        ).substitute(as_gql_id=action_step1.gql_id, **td)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        action_step1 = ActionStepFactory()
        grant_role(self.owner["role"], action_step1.action.module_definition, self.owner["user"])

        action_step2 = ActionStepFactory()
        td = {
            "order": action_step2.order,
            "forEach": action_step2.for_each,
            "value": action_step2.value,
            "code": action_step2.code,
            "logMessage": action_step2.log_message,
        }

        query = Template(
            """mutation{ updateActionStep(input: {
            id: "$as_gql_id",
            order: $order,
            forEach: "$forEach",
            code: "$code",
            value: "$value",
            logMessage: "$logMessage"}){ actionStep {
            order invertCondition forEach code logMessage }}}
            """
        ).substitute(as_gql_id=action_step1.gql_id, **td)

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = ActionStep.objects.get(pk=action_step1.id)

        self.assertEqual(lookup.order, td["order"])
        self.assertEqual(lookup.for_each, td["forEach"])
        self.assertEqual(lookup.value, td["value"])
        self.assertEqual(lookup.code, td["code"])
        self.assertEqual(lookup.log_message, td["logMessage"])


class TestDeleteActionStep(GQLTestCase):
    node_name = "ActionStepNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        action_step = ActionStepFactory()

        grant_role(self.viewer["role"], action_step.action.module_definition, self.viewer["user"])

        query = Template(
            """mutation{ deleteActionStep(input: {
            id: "$as_gql_id" }) { id }}"""
        ).substitute(as_gql_id=action_step.gql_id)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assert_query_was_unauthorized(result)

        ActionStep.objects.get(pk=action_step.id)

    def test_delete_produces_result(self):
        action_step = ActionStepFactory()

        grant_role(self.owner["role"], action_step.action.module_definition, self.owner["user"])

        query = Template(
            """mutation{ deleteActionStep(input: {
            id: "$as_gql_id" }) { id }}"""
        ).substitute(as_gql_id=action_step.gql_id)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertRaises(ActionStep.DoesNotExist, ActionStep.objects.get, **{"pk": action_step.id})
