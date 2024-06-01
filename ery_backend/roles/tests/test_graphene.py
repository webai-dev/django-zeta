import graphene

from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.testcases import GQLTestCase
from ery_backend.folders.factories import FolderFactory
from ery_backend.labs.factories import LabFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.mutations import RoleMutation
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.roles.factories import PrivilegeFactory, RoleFactory
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.users.factories import UserFactory
from ery_backend.users.schema import ViewerQuery
from ery_backend.roles.utils import grant_role
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.widgets.factories import WidgetFactory

from ..factories import RoleFactory, PrivilegeFactory
from ..models import Role
from ..schema import RoleQuery, RoleAssignmentQuery
from ..utils import grant_role, has_privilege, revoke_role


class TestQuery(RoleQuery, RoleAssignmentQuery, ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(RoleMutation, graphene.ObjectType):
    pass


class TestReadRole(GQLTestCase):
    """Ensure reading Role works"""

    node_name = "RoleNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def setUp(self):
        self.all_query = """{allRoles{ edges{ node{ id }}}}"""

    def test_read_all_requires_login(self):
        """allRoles query without a user is unauthorized"""
        result = self.gql_client.execute(self.all_query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        role = RoleFactory()
        td = {"roleid": role.gql_id}

        query = """query RoleQuery($roleid: ID!){role(id: $roleid){ id }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        roles = [RoleFactory() for _ in range(3)]

        for obj in roles:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in roles[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], roles[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allRoles"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allRoles"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allRoles"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allRoles"]["edges"]), 1)


class TestCreateRole(GQLTestCase):
    node_name = "RoleNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """mutation CreateRole($name: String, $comment: String){ createRole(input: {
                        name: $name
                        comment: $comment})
                        { role{ id name comment }}}"""
        cls.td = {
            "name": "test_create_requires_privilege",
            "comment": "Lookameimacommenthey",
        }

    def test_create_requires_privilege(self):
        role = RoleFactory()
        grant_role(self.viewer["role"], role, self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        self.assertRaises(Role.DoesNotExist, Role.objects.get, **{"name": self.td["name"]})

    def test_create_produces_result(self):
        role = RoleFactory()
        grant_role(self.owner["role"], role, self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        lookup = Role.objects.get(name=self.td["name"])

        self.assertEqual(lookup.name, self.td["name"])
        self.assertEqual(lookup.comment, self.td["comment"])


class TestUpdateRole(GQLTestCase):
    node_name = "RoleNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """mutation UpdateRole($id: ID!, $name: String, $comment: String){
                        updateRole(input: {
                            id: $id
                            name: $name
                            comment: $comment})
                            { role{ id name comment }}}"""

    def setUp(self):
        self.role = RoleFactory()
        self.td = {"name": "update_works", "comment": "Lookameimupdatedhey", "id": self.role.gql_id}

    def test_update_requires_privileges(self):
        """Unprivileged users can't update roles"""
        grant_role(self.viewer["role"], self.role, self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        self.role.refresh_from_db()

    def test_update_works_correctly(self):
        """Updated fields are updated"""
        grant_role(self.editor["role"], self.role, self.editor["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.editor["user"])
        )
        self.fail_on_errors(result)

        self.role.refresh_from_db()
        self.assertEqual(self.role.name, self.td["name"])
        self.assertEqual(self.role.comment, self.td["comment"])


class TestDeleteRole(GQLTestCase):
    node_name = "RoleNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """mutation DeleteRole($id: ID!){ deleteRole(input: {
                    id: $id }){ success }}"""

    def setUp(self):
        self.role = RoleFactory()
        self.td = {'id': self.role.gql_id}

    def test_delete_requires_privilege(self):
        role_id = self.role.pk

        grant_role(self.viewer["role"], self.role, self.viewer["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        Role.objects.get(pk=role_id)

    def test_delete_produces_result(self):
        role_id = self.role.pk

        grant_role(self.owner["role"], self.role, self.owner["user"])

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteRole"]["success"])

        self.assertRaises(Role.DoesNotExist, Role.objects.get, **{"pk": role_id})


class TestGrantRole(GQLTestCase):
    node_name = "RoleNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """mutation GrantRole($id: ID!, $owner: ID!, $obj: ID!){
                        grantRole(input: {
                            id: $id, owner: $owner, obj: $obj })
                            { success roleAssignmentEdge{ node { role { name}}}}}"""
        cls.role = RoleFactory()
        privilege = PrivilegeFactory(name='doit')
        cls.role.privileges.add(privilege)
        cls.assignee = UserFactory()
        cls.module_definition = ModuleDefinitionFactory()

    def setUp(self):
        self.td = {'id': self.role.gql_id, 'owner': self.assignee.gql_id, 'obj': self.module_definition.gql_id}

    def test_grant_requires_privilege(self):
        self.assertFalse(has_privilege(self.module_definition, self.assignee, 'doit'))
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        # lacks grant permission on obj
        grant_role(self.owner['role'], self.role, self.viewer['user'])
        grant_role(self.viewer['role'], self.module_definition, self.viewer['user'])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)
        self.assertFalse(has_privilege(self.module_definition, self.assignee, 'doit'))

        # lacks grant permission on role
        revoke_role(self.owner['role'], self.role, self.viewer['user'])
        grant_role(self.viewer['role'], self.role, self.viewer['user'])
        grant_role(self.owner['role'], self.module_definition, self.viewer['user'])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)
        self.assertFalse(has_privilege(self.module_definition, self.assignee, 'doit'))

    def test_grant_produces_result(self):
        self.assertFalse(has_privilege(self.module_definition, self.assignee, 'doit'))

        grant_role(self.owner['role'], self.role, self.assignee)
        grant_role(self.owner['role'], self.module_definition, self.assignee)

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.fail_on_errors(result)

        self.assertTrue(has_privilege(self.module_definition, self.assignee, 'doit'))
        self.assertEqual(self.role.name, result['data']['grantRole']['roleAssignmentEdge']['node']['role']['name'])
        # All models from ObjectsMixin.get_role_objs tested for expected results.
        # Not needed for revoke, since it will reference same dict of objects.

        image_asset = ImageAssetFactory()
        self.td['obj'] = image_asset.gql_id
        grant_role(self.owner['role'], image_asset, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(image_asset, self.assignee, 'doit'))

        folder = FolderFactory()
        self.td['obj'] = folder.gql_id
        grant_role(self.owner['role'], folder, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(folder, self.assignee, 'doit'))

        lab = LabFactory()
        self.td['obj'] = lab.gql_id
        grant_role(self.owner['role'], lab, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(lab, self.assignee, 'doit'))

        procedure = ProcedureFactory()
        self.td['obj'] = procedure.gql_id
        grant_role(self.owner['role'], procedure, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(procedure, self.assignee, 'doit'))

        stint_definition = StintDefinitionFactory()
        self.td['obj'] = stint_definition.gql_id
        grant_role(self.owner['role'], stint_definition, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(stint_definition, self.assignee, 'doit'))

        template = TemplateFactory()
        self.td['obj'] = template.gql_id
        grant_role(self.owner['role'], template, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(template, self.assignee, 'doit'))

        theme = ThemeFactory()
        self.td['obj'] = theme.gql_id
        grant_role(self.owner['role'], theme, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(theme, self.assignee, 'doit'))

        validator = ValidatorFactory(regex=None)
        self.td['obj'] = validator.gql_id
        grant_role(self.owner['role'], validator, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(theme, self.assignee, 'doit'))

        widget = WidgetFactory()
        self.td['obj'] = widget.gql_id
        grant_role(self.owner['role'], widget, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(widget, self.assignee, 'doit'))

        role = RoleFactory()
        self.td['obj'] = role.gql_id
        grant_role(self.owner['role'], role, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(role, self.assignee, 'doit'))

        privilege = PrivilegeFactory()
        self.td['obj'] = privilege.gql_id
        grant_role(self.owner['role'], privilege, self.assignee)
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.assignee)
        )
        self.assertTrue(has_privilege(privilege, self.assignee, 'doit'))


class TestRevokeRole(GQLTestCase):
    node_name = "RoleNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.query = """
mutation RevokeRole($id: ID!, $owner: ID!, $obj: ID!) {
    revokeRole(input: {
        id: $id,
        owner: $owner,
        obj: $obj
    }) {
        success
        roleAssignmentId
    }
}"""
        cls.role = RoleFactory()
        privilege = PrivilegeFactory(name='doit')
        cls.role.privileges.add(privilege)
        cls.assignee = UserFactory()
        cls.module_definition = ModuleDefinitionFactory()
        cls.td = {'id': cls.role.gql_id, 'owner': cls.assignee.gql_id, 'obj': cls.module_definition.gql_id}

    def setUp(self):
        grant_role(self.role, self.module_definition, self.assignee)

    def test_revoke_requires_privilege(self):
        self.assertTrue(has_privilege(self.module_definition, self.assignee, 'doit'))

        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        # lacks revoke privilege on obj
        grant_role(self.viewer['role'], self.module_definition, self.viewer['user'])
        grant_role(self.owner['role'], self.role, self.viewer['user'])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        # lacks revoke privilege on role
        revoke_role(self.owner['role'], self.role, self.viewer['user'])
        grant_role(self.owner['role'], self.module_definition, self.viewer['user'])
        grant_role(self.viewer['role'], self.role, self.viewer['user'])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        self.assertTrue(has_privilege(self.module_definition, self.assignee, 'doit'))

    def test_revoke_produces_result(self):
        self.assertTrue(has_privilege(self.module_definition, self.assignee, 'doit'))

        grant_role(self.owner['role'], self.role, self.owner['user'])
        grant_role(self.owner['role'], self.module_definition, self.owner['user'])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertFalse(has_privilege(self.module_definition, self.assignee, 'doit'))
        self.assertIsInstance(result['data']['revokeRole']['roleAssignmentId'], str)


class TestReadRoleAssignment(GQLTestCase):
    """Ensure reading RoleAssignment works"""

    node_name = "RoleAssignmentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.user = UserFactory()
        cls.role = RoleFactory()

    def setUp(self):
        self.obj = ModuleDefinitionFactory()
        self.td = {"mdid": self.obj.gql_id}

    def test_query_assignments_from_node(self):
        query = """query RoleAssignmentQuery($mdid: ID!){
                    viewer{ moduleDefinition(id: $mdid){ roleAssignments{ edges{ node{ user{ username } }} }}}}
                """
        grant_role(self.viewer["role"], self.obj, self.viewer["user"])
        result = self.gql_client.execute(
            query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )

        self.fail_on_errors(result)
        self.assertEqual(
            result["data"]["viewer"]["moduleDefinition"]["roleAssignments"]["edges"][0]["node"]["user"]["username"],
            self.viewer["user"].username,
        )
