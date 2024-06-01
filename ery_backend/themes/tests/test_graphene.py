import graphene

from ery_backend.base.testcases import GQLTestCase
from ery_backend.mutations import ThemeMutation, ThemePaletteMutation
from ery_backend.roles.utils import grant_role, grant_ownership
from ery_backend.themes.models import Theme, ThemePalette
from ery_backend.themes.factories import ThemeFactory, ThemePaletteFactory

from ..schema import ThemeQuery, ThemePaletteQuery


class TestQuery(ThemeQuery, ThemePaletteQuery, graphene.ObjectType):
    pass


class TestMutation(ThemeMutation, ThemePaletteMutation, graphene.ObjectType):
    pass


class TestReadTheme(GQLTestCase):
    node_name = "ThemeNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_queries_require_login(self):
        theme = ThemeFactory()
        td = {"gqlId": theme.gql_id}

        query = """{allThemes {edges { node { id name comment published}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        query = """query Theme($gqlId: ID!){ theme(id: $gqlId){ id name comment published }}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allThemes {edges { node { id name comment published }}}}"""

        themes = [ThemeFactory(published=False) for _ in range(3)]

        for t in themes:
            grant_role(self.viewer["role"], t, self.viewer["user"])

        for t in themes[1:]:
            grant_role(self.editor["role"], t, self.editor["user"])

        grant_role(self.owner["role"], themes[2], self.owner["user"])

        # No Roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allThemes"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allThemes"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allThemes"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allThemes"]["edges"]), 1)

    def test_read_node_accuracy(self):
        theme = ThemeFactory()
        td = {"gqlId": theme.gql_id}

        grant_role(self.viewer["role"], theme, self.viewer["user"])

        query = """query Theme($gqlId: ID!){ theme(id: $gqlId){ id name comment published }}"""
        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.fail_on_errors(result)

        for field in ["name", "comment", "published"]:
            self.assertEqual(result["data"]["theme"][field], getattr(theme, field, None), msg=f"mismatch on {field}")

    def test_no_soft_deletes_in_all_query(self):
        """
        Confirm soft_deleted objects are not returned in query.
        """
        query = """{allThemes { edges{ node{ id }}}}"""
        theme = ThemeFactory()
        grant_role(self.viewer["role"], theme, self.viewer["user"])

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allThemes"]["edges"]), 1)

        theme.soft_delete()
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assertEqual(len(result["data"]["allThemes"]["edges"]), 0)

    def test_no_soft_deletes_in_single_query(self):
        """
        Confirms soft_deleted object not returned in query.
        """
        query = """query ThemeQuery($themeid: ID!){
            theme(id: $themeid){ id }}
            """
        theme = ThemeFactory()
        grant_role(self.viewer["role"], theme, self.viewer["user"])

        result = self.gql_client.execute(
            query,
            variable_values={"themeid": theme.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.fail_on_errors(result)

        theme.soft_delete()
        result = self.gql_client.execute(
            query,
            variable_values={"themeid": theme.gql_id},
            context_value=self.gql_client.get_context(user=self.viewer["user"]),
        )
        self.assertEqual('Theme matching query does not exist.', result['errors'][0]['message'])


class TestCreateTheme(GQLTestCase):
    node_name = "ThemeNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    query = """mutation CreateTheme($name: String, $comment: String, $published: Boolean){
                createTheme(input: {
                    name: $name,
                    comment: $comment,
                    published: $published }){
                themeEdge{ node{ id name comment published} }}}"""

    def test_create_requires_login(self):
        td = {"name": "Test Create Requires Login", "comment": "Don't create this", "published": False}

        result = self.gql_client.execute(self.query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_create_produces_results(self):
        td = {"name": "Test Create Produces Result", "comment": "Hooray!", "published": False}

        result = self.gql_client.execute(
            self.query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        for field in td:
            self.assertEqual(result["data"]["createTheme"]["themeEdge"]["node"][field], td[field], msg=f"mismatch on {field}")

        lookup = Theme.objects.get(name=td["name"])

        for field in td:
            self.assertEqual(getattr(lookup, field, None), td[field])


class TestUpdateTheme(GQLTestCase):
    node_name = "ThemeNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_ownership(self):
        theme = ThemeFactory()

        grant_role(self.owner["role"], theme, self.owner["user"])

        td = {
            "gqlId": theme.gql_id,
            "name": "test update requires ownership",
            "comment": "do not change this",
            "published": True,
        }

        query = """mutation UpdateTheme($gqlId: ID!, $name: String, $comment: String, $published: Boolean)
                    { updateTheme(input: {
                    id: $gqlId,
                    name: $name,
                    comment: $comment,
                    published: $published }) { theme {
                        id name comment published }}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_change(self):
        theme = ThemeFactory()
        tid = theme.pk

        grant_role(self.owner["role"], theme, self.owner["user"])

        td = {"gqlId": theme.gql_id, "name": "test update produces change", "comment": "ftw", "published": False}

        query = """mutation UpdateTheme($gqlId: ID!, $name: String, $comment: String, $published: Boolean)
                    { updateTheme(input: {
                    id: $gqlId,
                    name: $name,
                    comment: $comment,
                    published: $published }){ theme {
                        id name comment published }}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        td.pop("gqlId")
        for field in td:
            self.assertEqual(result["data"]["updateTheme"]["theme"][field], td[field], msg=f"mismatch on {field}")

        lookup = Theme.objects.get(pk=tid)

        for field in td:
            self.assertEqual(getattr(lookup, field, None), td[field], msg=f"mismatch on {field}")


class TestDeleteTheme(GQLTestCase):
    node_name = "ThemeNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privilege(self):
        theme = ThemeFactory()
        tid = theme.pk
        td = {"gqlId": theme.gql_id}

        grant_role(self.owner["role"], theme, self.owner["user"])

        query = """mutation DeleteTheme($gqlId: ID!){ deleteTheme(input:
                    { id: $gqlId }){ id }}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        Theme.objects.get(pk=tid)

    def test_delete_works(self):
        theme = ThemeFactory()
        td = {"gqlId": theme.gql_id}

        grant_role(self.owner["role"], theme, self.owner["user"])

        query = """mutation DeleteTheme($gqlId: ID!){ deleteTheme(input:
                    { id: $gqlId }){ id }}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )

        self.fail_on_errors(result)

        theme.refresh_from_db()
        self.assertEqual(theme.state, theme.STATE_CHOICES.deleted)


class TestReadThemePalette(GQLTestCase):
    node_name = "ThemePaletteNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        theme = ThemeFactory()
        grant_role(self.viewer["role"], theme, self.viewer["user"])
        theme_palette = ThemePaletteFactory(theme=theme)

        query = """{allThemePalettes {edges {node {id name}}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

        td = {"gqlId": theme_palette.gql_id}

        query = """query ThemePalette($gqlId: ID!){themePalette(id: $gqlId){name main}}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        themes = [ThemeFactory(), ThemeFactory(), ThemeFactory()]

        for t in themes:
            grant_role(self.viewer["role"], t, self.viewer["user"])
            ThemePaletteFactory(theme=t)

        for t in themes[1:]:
            grant_role(self.editor["role"], t, self.editor["user"])

        grant_role(self.owner["role"], themes[2], self.owner["user"])
        query = """{allThemePalettes {edges {node {id name}}}}"""

        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allThemePalettes"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allThemePalettes"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allThemePalettes"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allThemePalettes"]["edges"]), 1)


class TestCreateThemePalette(GQLTestCase):
    node_name = "ThemePaletteNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_login(self):
        theme = ThemeFactory()

        td = {"name": "primary", "main": "001243jid", "gqlId": theme.gql_id}

        query = """mutation CreateThemePalette($gqlId: ID!, $name: String, $main: String)
                    { createThemePalette(input: {
                    name: $name,
                    main: $main,
                    theme: $gqlId}){
                   themePaletteEdge{ node{ id name main} }}}
                """

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_create_produces_theme_palette(self):
        theme = ThemeFactory()
        grant_ownership(theme, self.owner["user"])

        td = {"gqlId": theme.gql_id, "name": ThemePalette.PALETTE_CHOICES.primary, "main": "#01243j"}

        query = """mutation CreateThemePalette($gqlId: ID!, $name: String, $main: String)
                    { createThemePalette(input: {
                    name: $name,
                    main: $main
                    theme: $gqlId}){
                   themePaletteEdge{ node{ id name main} }}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        td.pop("gqlId")
        for field in td:
            expected_value = td[field]
            if field == 'name':
                expected_value = expected_value.upper()
            self.assertEqual(
                result["data"]["createThemePalette"]["themePaletteEdge"]["node"][field],
                expected_value,
                msg=f"mismatch on {field}",
            )

        lookup = ThemePalette.objects.get(name=td["name"])

        for field in td:
            # XXX: See #751 about uppercased return
            self.assertEqual(getattr(lookup, field, None), td[field], msg=f"mismatch on {field}")

    def test_update_requires_permission(self):
        theme = ThemeFactory()
        grant_role(self.viewer["role"], theme, self.viewer["user"])
        theme_palette = ThemePaletteFactory(theme=theme)

        td = {"name": ThemePalette.PALETTE_CHOICES.secondary, "main": "0711034", "gqlId": theme_palette.gql_id}

        query = """mutation UpdateThemePalette($gqlId: ID!, $name: String, $main: String)
                    { updateThemePalette(input: {
                    id: $gqlId,
                    name: $name,
                    main: $main}){
                   themePalette { id name main }}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_change(self):
        theme = ThemeFactory()
        grant_role(self.owner["role"], theme, self.owner["user"])
        theme_palette = ThemePaletteFactory(theme=theme)
        tdid = theme_palette.pk

        td = {"name": ThemePalette.PALETTE_CHOICES.secondary, "main": "0711035", "gqlId": theme_palette.gql_id}

        query = """mutation UpdateThemePalette($gqlId: ID!, $name: String, $main: String)
                    { updateThemePalette(input: {
                    id: $gqlId,
                    name: $name,
                    main: $main}){
                   themePalette { id name main }}}
                """

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        td.pop("gqlId")
        for field in td:
            # XXX: See #751 about uppercased return
            expected_value = td[field]
            if field == 'name':
                expected_value = expected_value.upper()
            self.assertEqual(
                result["data"]["updateThemePalette"]["themePalette"][field], expected_value, msg=f"mismatch on {field}"
            )

        lookup = ThemePalette.objects.get(pk=tdid)

        for field in td:
            self.assertEqual(getattr(lookup, field, None), td[field], msg=f"mismatch on {field}")


class TestDeleteThemePalette(GQLTestCase):
    node_name = "ThemePaletteNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_permission(self):
        theme = ThemeFactory()
        grant_role(self.viewer["role"], theme, self.viewer["user"])
        theme_palette = ThemePaletteFactory(theme=theme)
        tdid = theme_palette.pk
        td = {"gqlId": theme_palette.gql_id}

        query = """mutation deleteThemePalette($gqlId: ID!){ deleteThemePalette(input: { id: $gqlId}){ id }}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)
        ThemePalette.objects.get(pk=tdid)

    def test_delete_produces_result(self):
        theme = ThemeFactory()
        grant_role(self.owner["role"], theme, self.owner["user"])
        theme_palette = ThemePaletteFactory(theme=theme)
        tdid = theme_palette.pk
        td = {"gqlId": theme_palette.gql_id}

        query = """mutation DeleteThemePalette($gqlId: ID!){ deleteThemePalette(input: { id: $gqlId}){ id }}"""

        result = self.gql_client.execute(
            query, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertIsNotNone(result["data"]["deleteThemePalette"]["id"])

        self.assertRaises(ThemePalette.DoesNotExist, ThemePalette.objects.get, **{"pk": tdid})
