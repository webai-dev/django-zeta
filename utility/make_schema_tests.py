import os

from tools import confirm

model_name = confirm(input('Enter model name: '))
model_name_slug = confirm(input('Enter model name slug: '))
model_name_camel = model_name[0].lower() + model_name[1:]
node_name = f"{model_name}Node"
model_name_id = f"{model_name_slug.replace('_', '')}id"
multi_line_quote = '\"\"\"'
versions = confirm(input('Versions? Enter y or n: '))
if versions == 'y':
    reversion_attribute = confirm(input('Enter name of attribute for reversions: '))
module_definition_model = confirm(input('Is this a ModuleDefinitionModel?. Enter y or n: '))
ery_file_model = confirm(input('Is this an EryFileModel?. Enter y or n: '))
newline = '\n'
tab = ' ' * 4

soft_delete_code = ''
if ery_file_model == 'y':
    soft_delete_code = f"""
    def test_no_soft_deletes_in_all_query(self):
        {multi_line_quote}
        Confirm soft_deleted objects are not returned in query.
        {multi_line_quote}
        query = {multi_line_quote}{{all{model_name}s {{ edges{{ node{{ id }}}}}}}}{multi_line_quote}
        {model_name_slug} = {model_name}Factory()
        grant_role(self.viewer["role"], {model_name_slug}, self.viewer["user"])

        result = self.gql_client.execute(query, context_value={{"user": self.viewer["user"]}})
        self.assertEqual(len(result["data"]["all{model_name}s"]["edges"]), 1)

        {model_name_slug}.soft_delete()
        result = self.gql_client.execute(query, context_value={{"user": self.viewer["user"]}})
        self.assertEqual(len(result["data"]["all{model_name}s"]["edges"]), 0)

    def test_no_soft_deletes_in_single_query(self):
        {multi_line_quote}
        Confirms soft_deleted object not returned in query.
        {multi_line_quote}
        query = {multi_line_quote}query {model_name}Query(${model_name_camel}id: ID!){{
            {model_name_camel}(id: ${model_name_camel}id){{ id }}}}
            {multi_line_quote}
        {model_name_slug} = {model_name}Factory()
        grant_role(self.viewer["role"], {model_name_slug}, self.viewer["user"])

        result = self.gql_client.execute(query, variable_values={{"{model_name_camel}id": self.gql_id({model_name_slug}.pk)}},
                                         context_value={{"user": self.viewer["user"]}})
        self.fail_on_errors(result)

        {model_name_slug}.soft_delete()
        result = self.gql_client.execute(query, variable_values={{"{model_name_camel}id": self.gql_id({model_name_slug}.pk)}},
                                         context_value={{"user": self.viewer["user"]}})
        self.assertEqual('{model_name} matching query does not exist.', result['errors'][0]['message'])
"""


module_definition_lookup = (
    f'self.assertEqual({tab}int(from_global_id(result["data"]["{model_name_camel}"]["moduleDefinition"]["id"])[1]),'
    f' self.{model_name_slug}.module_definition.id)'
    if module_definition_model == 'y'
    else ''
)

read_output = f"""import graphene
from graphene.test import Client as GQLClient
from graphql_relay.node.node import from_global_id

from ery_backend.base.testcases import {"GQLTestCase, create_revisions" if versions == 'y' else "GQLTestCase"}
{'from ery_backend.modules.factories import ModuleDefinitionFactory' if module_definition_model == 'y' else ''}
from ery_backend.roles.utils import grant_role
from ..factories import {model_name}Factory
from ..models import {model_name}
from ..schema import {model_name}Query, {model_name}Mutation

class TestQuery({model_name}Query, graphene.ObjectType):
    pass

class TestMutation({model_name}Mutation, graphene.ObjectType):
    pass

class TestRead{model_name}(GQLTestCase):
    {multi_line_quote}Ensure reading {model_name} works{multi_line_quote}
    node_name = "{model_name}Node"
    gql_client = GQLClient(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.all_query = {multi_line_quote}{{all{model_name}s{{ edges{{ node{{ id }}}}}}}}{multi_line_quote}
        cls.node_query = {multi_line_quote}query {model_name}Query(${model_name_id}: ID!){{
            {model_name_camel}(id: ${model_name_id}){{ id {'moduleDefinition{ id }' if module_definition_model == 'y' else ''} }}}}{multi_line_quote}

    def setUp(self):
        {'self.module_definition = ModuleDefinitionFactory()' if module_definition_model == 'y' else ''}
        self.{model_name_slug} = {model_name}Factory({'module_definition=self.module_definition' if module_definition_model == 'y' else ''})
        self.td = {{"{model_name_id}": self.gql_id(self.{model_name_slug}.pk),
                   {"'module_definition': self.gql_id(self.module_definition.pk, 'ModuleDefinitionNode')" if module_definition_model == 'y' else ''}}}

    def test_read_all_requires_login(self):
        {multi_line_quote}all{model_name}s query without a user is unauthorized{multi_line_quote}
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        result = self.gql_client.execute(self.node_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        {model_name_slug}s = [{model_name}Factory({'module_definition=self.module_definition' if module_definition_model == 'y' else ''}) for _ in range(3)]

        for obj in {model_name_slug}s:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(),
                       self.viewer["user"])

        for obj in {model_name_slug}s[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(),
                       self.editor["user"])

        grant_role(self.owner["role"], {model_name_slug}s[2].get_privilege_ancestor(),
                   self.owner["user"])
        # No roles
        result = self.gql_client.execute(self.all_query, context_value={{"user": self.no_roles["user"]}})
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["all{model_name}s"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value={{"user": self.viewer["user"]}})
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["all{model_name}s"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value={{"user": self.editor["user"]}})
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["all{model_name}s"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value={{"user": self.owner["user"]}})
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["all{model_name}s"]["edges"]), 1)

    def test_read_node_works(self):
        grant_role(self.viewer["role"], self.{model_name_slug}.get_privilege_ancestor(),
                   self.viewer["user"])
        result = self.gql_client.execute(self.node_query, variable_values=self.td,
                                         context_value={{"user": self.viewer["user"]}})
        self.fail_on_errors(result)
        self.assertEqual(int(from_global_id(result["data"]["{model_name_camel}"]["id"])[1]), self.{model_name_slug}.id)
        {module_definition_lookup}
    {soft_delete_code}
"""

if versions == 'y':
    read_output += f"""
    def test_read_versions(self):
        # setup
        grant_role(self.editor['role'], self.{model_name_slug}.get_privilege_ancestor(), self.editor['user'])
        create_revisions([{{'obj': self.{model_name_slug}, 'attr': '{reversion_attribute}'}}], revision_n=1, user=self.editor['user'])
        query = {multi_line_quote}{{all{model_name}s{{ edges{{ node{{ versions{{ edges{{ node{{ id }}}}}}}}}}}}}}{multi_line_quote}
        result = self.gql_client.execute(query, context_value={{"user": self.editor['user']}})

        # the number of version nodes should match the number of revisions created per object.
        version_nodes = result['data']['all{model_name}s']['edges'][0]['node']['versions']['edges']
        self.assertEqual(len(version_nodes), 1)
"""

create_output = f"""class TestCreate{model_name}(GQLTestCase):
    node_name = "{model_name}Node"
    gql_client = GQLClient(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        {'self.module_definition = ModuleDefinitionFactory()' if module_definition_model == 'y' else ''}
        self.td = {{
            {"'moduleDefinition': self.gql_id(self.module_definition.pk, 'ModuleDefinitionNode')" if module_definition_model == 'y' else ''}
        }}

        self.query = {multi_line_quote}mutation ({'$moduleDefinition: ID!' if module_definition_model == 'y' else ''}){{
             create{model_name}(input: {{
                {'moduleDefinition: $moduleDefinition' if module_definition_model == 'y' else ''}
                    }})
                   {{{model_name_camel}
                   {{id }}}}}}
                {multi_line_quote}

    def test_create_requires_privilege(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises({model_name}.DoesNotExist,
                          {model_name}.objects.get,
                          **{{"name": self.td["name"]}})

    def test_create_produces_result(self):
        {'grant_role(self.owner["role"], self.module_definition, self.owner["user"])' if module_definition_model == 'y' else ''}
        result = self.gql_client.execute(self.query, variable_values=self.td, context_value={{"user": self.owner["user"]}})
        self.fail_on_errors(result)

        lookup = {model_name}.objects.get(name=self.td["name"])

        self.assertEqual(lookup.name, self.td["name"])
        {'self.assertEqual(lookup.module_definition, self.module_definition)' if module_definition_model == 'y' else ''}
"""

update_output = f"""class TestUpdate{model_name}(GQLTestCase):
    node_name = "{model_name}Node"
    gql_client = GQLClient(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.{model_name_slug} = {model_name}Factory()
        self.td = {{
            "{model_name_camel}": self.gql_id(self.{model_name_slug}.pk),
            "name": "Test{model_name}"
        }}
        self.query = {multi_line_quote}mutation (${model_name_camel}: ID!, $name: String!){{
             update{model_name}(input: {{
                id: ${model_name_camel},
                name: $name
                    }})
                   {{{model_name_camel}
                   {{id }}}}}}
                {multi_line_quote}

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.{model_name_slug}.get_privilege_ancestor(),
                   self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.{model_name_slug}.get_privilege_ancestor(),
                   self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td,
                                         context_value={{"user": self.owner["user"]}})
        self.fail_on_errors(result)

        lookup = {model_name}.objects.get(pk=self.{model_name_slug}.id)

        self.assertEqual(lookup.name, self.td["name"])
"""

hard_delete_test = (
    f'self.assertRaises({newline}{tab}{tab}{tab}{model_name}.DoesNotExist,{newline}{tab}{tab}{tab}'
    f'{model_name}.objects.get,{newline}{tab}{tab}{tab}**{{"pk": self.{model_name_slug}.id}})'
)

soft_delete_test = (
    f'self.{model_name_slug}.refresh_from_db(){newline}{tab}{tab}'
    f'self.assertEqual(self.{model_name_slug}.state, self.{model_name_slug}.STATE_CHOICES.deleted)'
)

delete_output = f"""class TestDelete{model_name}(GQLTestCase):
    node_name = "{model_name}Node"
    gql_client = GQLClient(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.{model_name_slug} = {model_name}Factory()
        self.td = {{
            "{model_name_camel}": self.gql_id(self.{model_name_slug}.pk)
        }}
        self.query = {multi_line_quote}mutation (${model_name_camel}: ID!){{
             delete{model_name}(input: {{
                id: ${model_name_camel},
                    }})
                   {{ success }}
                   }}
                {multi_line_quote}

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.{model_name_slug}.get_privilege_ancestor(),
                   self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(self.query, variable_values=self.td,
                                         context_value={{"user": self.viewer["user"]}})
        self.assert_query_was_unauthorized(result)

        {model_name}.objects.get(pk=self.{model_name_slug}.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.{model_name_slug}.get_privilege_ancestor(),
                   self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td,
                                         context_value={{"user": self.owner["user"]}})
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["delete{model_name}"]["success"])

        {soft_delete_test if ery_file_model == 'y' else hard_delete_test}
"""

output_location = f'{os.getcwd()}/schema_test.py'
with open(output_location, 'w') as f:
    f.write(f'{read_output}\n{create_output}\n{update_output}\n{delete_output}')
