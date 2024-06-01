import graphene

from ery_backend.base.testcases import GQLTestCase
from ery_backend.roles.utils import grant_role

from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory
from ery_backend.mutations import RobotMutation, RobotRuleMutation
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition

from ..models import Robot, RobotRule
from ..factories import RobotFactory, RobotRuleFactory
from ..schema import RobotQuery, RobotRuleQuery


class TestQuery(RobotQuery, RobotRuleQuery, graphene.ObjectType):
    pass


class TestMutation(RobotMutation, RobotRuleMutation, graphene.ObjectType):
    pass


class TestReadRobot(GQLTestCase):
    node_name = "RobotNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allRobots query without a user is unauthorized"""
        query = """{allRobots{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_reqires_login(self):
        robot = RobotFactory()
        td = {"robotid": robot.gql_id}

        query = """query RobotQuery($robotid: ID!){robot(id:$robotid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        robots = [RobotFactory() for i in range(3)]

        for robot in robots:
            grant_role(self.viewer['role'], robot.module_definition, self.viewer['user'])

        for robot in robots[1:]:
            grant_role(self.editor['role'], robot.module_definition, self.editor['user'])

        grant_role(self.owner['role'], robots[2].module_definition, self.owner['user'])

        query = """{allRobots{edges {node {id name comment}}}}"""

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        # Viewer
        self.assertEqual(len(result['data']['allRobots']['edges']), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result['data']['allRobots']['edges']), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result['data']['allRobots']['edges']), 1)


class TestCreateRobot(GQLTestCase):
    node_name = 'RobotNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_privileges(self):
        md = ModuleDefinitionFactory()
        grant_role(self.viewer["role"], md, self.viewer["user"])

        td = {"md_id": md.gql_id, "name": "test create requires privileges", "comment": "you shall not haz"}

        query = """mutation CreateRobot($md_id: ID!, $name: String, $comment: String)
                    { createRobot(input: {
                    moduleDefinition: $md_id
                    name: $name
                    comment: $comment
                   }){robot {id name comment}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_results(self):
        md = ModuleDefinitionFactory()
        grant_role(self.owner['role'], md, self.owner['user'])

        td = {'md_id': md.gql_id, 'name': "test create produces result", 'comment': "it has been created"}

        query = """mutation CreatRobot($md_id: ID!, $name: String, $comment: String)
                    { createRobot(input: {
                    moduleDefinition: $md_id,
                    name: $name,
                    comment: $comment
                   }){robot {id name comment}}}
                """

        result = self.gql_client.execute(
            query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=td
        )

        self.fail_on_errors(result)
        td.pop("md_id")

        for field in td:
            self.assertEqual(result['data']['createRobot']['robot'][field], td[field])

        lookup = Robot.objects.get(name=td['name'])

        for field in td:
            self.assertEqual(getattr(lookup, field, None), td[field])

        self.assertEqual(lookup.module_definition.pk, md.pk)


class TestUpdateRobot(GQLTestCase):
    node_name = 'RobotNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        robot = RobotFactory()
        grant_role(self.viewer['role'], robot.module_definition, self.viewer['user'])

        td = {'gql_id': robot.gql_id, 'name': "test update requires privilege", 'comment': "don't do the update"}

        query = """mutation UpdateRobot($gql_id: ID!, $name: String, $comment: String)
                   { updateRobot(input: {
                   id: $gql_id
                   name: $name
                   comment: $comment})
                   {robot {id name comment}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        robot = RobotFactory()
        grant_role(self.owner['role'], robot.module_definition, self.owner['user'])
        td = {'gql_id': robot.gql_id, 'name': "test update produces result", 'comment': "good to go"}

        query = """mutation UpdateRobot($gql_id: ID!, $name: String, $comment: String)
                   { updateRobot(input: {
                   id: $gql_id
                   name: $name 
                   comment: $comment})
                   {robot {id name comment}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        td.pop('gql_id')
        for field in td:
            self.assertEqual(result['data']['updateRobot']['robot'][field], td[field])

        robot.refresh_from_db()
        for field in td:
            self.assertEqual(getattr(robot, field, None), td[field], msg="mismatch on %s" % (field,))


class TestDeleteRobot(GQLTestCase):
    node_name = 'RobotNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        robot = RobotFactory()
        grant_role(self.viewer['role'], robot.module_definition, self.viewer['user'])
        td = {"gql_id": robot.gql_id}

        query = """mutation DeleteRobot($gql_id: ID!){deleteRobot(input: {id: $gql_id}){success}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_delete_produces_result(self):
        robot = RobotFactory()
        robot_id = robot.pk
        grant_role(self.owner['role'], robot.module_definition, self.owner['user'])
        td = {"gql_id": robot.gql_id}

        query = """mutation DeleteRobot($gql_id: ID!){deleteRobot(input: {id: $gql_id}){success}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result['data']['deleteRobot']['success'])
        self.assertRaises(Robot.DoesNotExist, Robot.objects.get, **{'pk': robot_id})


class TestReadRobotRule(GQLTestCase):
    node_name = "RobotRuleNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allRobotRules query without a user is unauthorized"""
        query = """{allRobotRules{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_reqires_login(self):
        robot_rule = RobotRuleFactory()
        td = {"robot_rule_id": robot_rule.gql_id}

        query = """query RobotRuleQuery($robot_rule_id: ID!){robotRule(id:$robot_rule_id){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        robot_rules = [RobotRuleFactory() for i in range(3)]

        for robot_rule in robot_rules:
            grant_role(self.viewer['role'], robot_rule.robot.module_definition, self.viewer['user'])

        for robot_rule in robot_rules[1:]:
            grant_role(self.editor['role'], robot_rule.robot.module_definition, self.editor['user'])

        grant_role(self.owner['role'], robot_rules[2].robot.module_definition, self.owner['user'])

        query = """{allRobotRules{edges {node {id }}}}"""

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        # Viewer
        self.assertEqual(len(result['data']['allRobotRules']['edges']), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result['data']['allRobotRules']['edges']), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)

        self.assertEqual(len(result['data']['allRobotRules']['edges']), 1)


class TestCreateRobotRule(GQLTestCase):
    node_name = 'RobotRuleNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_privileges(self):
        robot = RobotFactory()
        module_definition_widget = ModuleDefinitionWidgetFactory()
        grant_role(self.viewer["role"], robot.module_definition, self.viewer["user"])

        td = {
            "robot_id": robot.gql_id,
            "module_definition_widget_id": module_definition_widget.gql_id,
            "rule_type": "static",
            "static_value": "my static value",
        }

        query = """mutation CreateRobotRule(
            $robot_id: ID!, $module_definition_widget_id: ID!, $rule_type: String, $static_value: String)
                    { createRobotRule(input: {
                    robot: $robot_id,
                    widget: $module_definition_widget_id,
                    ruleType: $rule_type,
                    staticValue: $static_value
                   }){robotRule {id robot {id name comment} ruleType staticValue}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_results(self):
        robot = RobotFactory()
        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=variable_definition)
        grant_role(self.owner["role"], robot.module_definition, self.owner["user"])

        td = {
            "robot_id": robot.gql_id,
            "mdw_id": module_definition_widget.gql_id,
            "rule_type": "static",
            "static_value": "my static value",
        }

        query = """mutation CreateRobotRule($robot_id: ID!, $mdw_id: ID!, $rule_type: String, $static_value: String)
                    { createRobotRule(input: {
                    robot: $robot_id,
                    widget: $mdw_id,
                    ruleType: $rule_type,
                    staticValue: $static_value
                   }){robotRule {id ruleType staticValue}}}
                """

        result = self.gql_client.execute(
            query, context_value=self.gql_client.get_context(user=self.owner["user"]), variable_values=td
        )

        self.fail_on_errors(result)
        td.pop("robot_id")
        td.pop("mdw_id")  # Not sure why I can't query this, if anyone knows let me know

        self.assertEqual(result['data']['createRobotRule']['robotRule']['ruleType'], td['rule_type'].upper())
        self.assertEqual(result['data']['createRobotRule']['robotRule']['staticValue'], td['static_value'])

        lookup = RobotRule.objects.get()

        for field in td:
            self.assertEqual(getattr(lookup, field, None), td[field])

        self.assertEqual(lookup.robot.pk, robot.pk)


class TestUpdateRobotRule(GQLTestCase):
    node_name = 'RobotRuleNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privilege(self):
        robot_rule = RobotRuleFactory()
        module_definition_widget = ModuleDefinitionWidgetFactory()
        grant_role(self.viewer["role"], robot_rule.robot.module_definition, self.viewer["user"])

        td = {
            "gql_id": robot_rule.gql_id,
            "mdw_id": module_definition_widget.gql_id,
            "rule_type": "static",
            "static_value": "my static value",
        }

        query = """mutation UpdateRobotRule($gql_id: ID!, $mdw_id: ID!, $rule_type: String, $static_value: String)
                   { updateRobotRule(input: {
                   id: $gql_id
                   widget: $mdw_id
                   ruleType: $rule_type
                   staticValue: $static_value})
                   {robotRule {id robot{id } ruleType staticValue}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        robot_rule = RobotRuleFactory()

        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=variable_definition)
        grant_role(self.owner["role"], robot_rule.robot.module_definition, self.owner["user"])

        td = {
            "gql_id": robot_rule.gql_id,
            "mdw_id": module_definition_widget.gql_id,
            "rule_type": "static",
            "static_value": "my static value",
        }

        query = """mutation UpdateRobotRule($gql_id: ID!, $mdw_id: ID!, $rule_type: String, $static_value: String)
                   { updateRobotRule(input: {
                   id: $gql_id
                   widget: $mdw_id
                   ruleType: $rule_type
                   staticValue: $static_value})
                   {robotRule {id robot{id } ruleType staticValue}}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        td.pop('gql_id')
        td.pop("mdw_id")
        self.assertEqual(result['data']['updateRobotRule']['robotRule']['ruleType'], td['rule_type'].upper())
        self.assertEqual(result['data']['updateRobotRule']['robotRule']['staticValue'], td['static_value'])

        robot_rule.refresh_from_db()
        for field in td:
            self.assertEqual(getattr(robot_rule, field, None), td[field], msg="mismatch on %s" % (field,))


class TestDeleteRobotRule(GQLTestCase):
    node_name = 'RobotRuleNode'
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        robot_rule = RobotRuleFactory()
        grant_role(self.viewer['role'], robot_rule.robot.module_definition, self.viewer['user'])
        td = {"gql_id": robot_rule.gql_id}

        query = """mutation DeleteRobotRule($gql_id: ID!){deleteRobotRule(input: {id: $gql_id}){success}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_delete_produces_result(self):
        robot_rule = RobotRuleFactory()
        robot_rule_id = robot_rule.pk
        grant_role(self.owner['role'], robot_rule.robot.module_definition, self.owner['user'])
        td = {"gql_id": robot_rule.gql_id}

        query = """mutation DeleteRobotRule($gql_id: ID!){deleteRobotRule(input: {id: $gql_id}){success}}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result['data']['deleteRobotRule']['success'])
        self.assertRaises(RobotRule.DoesNotExist, RobotRule.objects.get, **{'pk': robot_rule_id})
