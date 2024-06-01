import random

from countries_plus.models import Country
from languages_plus.models import Language
import graphene
from graphql_relay import from_global_id

from ery_backend.base.testcases import GQLTestCase, create_test_stintdefinition
from ery_backend.base.utils import get_gql_id
from ery_backend.frontends.models import Frontend
from ery_backend.mutations import StintSpecificationMutation
from ery_backend.stints.models import Stint
from ery_backend.stints.factories import StintFactory
from ery_backend.roles.utils import grant_role
from ..factories import (
    StintSpecificationFactory,
    StintSpecificationCountryFactory,
    StintSpecificationAllowedLanguageFrontendFactory,
    StintSpecificationRobotFactory,
    StintSpecificationVariableFactory,
)
from ..models import StintSpecification
from ..schema import StintSpecificationQuery


class TestQuery(StintSpecificationQuery, graphene.ObjectType):
    pass


class TestMutation(StintSpecificationMutation, graphene.ObjectType):
    pass


class TestReadStintSpecification(GQLTestCase):
    """Ensure reading StintSpecification works"""

    node_name = "StintSpecificationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allStintSpecifications query without a user is unauthorized"""
        query = """{allStintSpecifications{ edges{ node{ id }}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        stint_specification = StintSpecificationFactory()
        td = {"stintspecificationid": stint_specification.gql_id}

        query = """
query StintSpecificationQuery($stintspecificationid: ID!){stintSpecification(id: $stintspecificationid){ id }}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """{allStintSpecifications{ edges{ node{ id }}}}"""
        stint_specifications = [StintSpecificationFactory() for _ in range(3)]

        for obj in stint_specifications:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in stint_specifications[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], stint_specifications[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStintSpecifications"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStintSpecifications"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStintSpecifications"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allStintSpecifications"]["edges"]), 1)


class TestReadRelationships(GQLTestCase):
    """
    Confirm user can access related models as intended.
    """

    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def setUp(self):
        self.stint_specification = StintSpecificationFactory()
        grant_role(self.viewer["role"], self.stint_specification.get_privilege_ancestor(), self.viewer["user"])
        self.td = {"gqlId": self.stint_specification.gql_id}
        self.context = self.gql_client.get_context(user=self.viewer["user"])

    def test_stint(self):
        stint = StintFactory(stint_specification=self.stint_specification)
        grant_role(self.viewer["role"], stint, self.viewer["user"])
        stint_id = stint.gql_id

        query = """
query StintSpecificationQuery($gqlId: ID!){stintSpecification(id: $gqlId){ stints { edges { node { id status } } } } }"""
        result = self.gql_client.execute(query, variable_values=self.td, context_value=self.context)
        stint_ids = [edge['node']['id'] for edge in result['data']['stintSpecification']['stints']['edges']]
        self.assertIn(stint_id, stint_ids)

    def test_stintdefinition(self):
        stint_definition_id = self.stint_specification.stint_definition.gql_id
        query = """query StintSpecificationQuery($gqlId: ID!){stintSpecification(id: $gqlId){ stintDefinition { id ready }}}"""
        result = self.gql_client.execute(query, variable_values=self.td, context_value=self.context)
        self.assertEqual(stint_definition_id, result['data']['stintSpecification']['stintDefinition']['id'])
        self.assertEqual(False, result['data']['stintSpecification']['stintDefinition']['ready'])


class TestRealizeStintSpecification(GQLTestCase):
    node_name = "StintSpecificationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        stint_definition = create_test_stintdefinition(Frontend.objects.get(name='Web'))
        self.stint_specification = StintSpecificationFactory(stint_definition=stint_definition)
        self.test_data = {
            "gqlId": self.stint_specification.gql_id,
        }
        self.query = """
mutation RealizeStintSpecification($gqlId: ID!){
    realizeStintSpecification(input: {id: $gqlId}){
        stint{ id status }
    }
}"""

    def test_realize_requires_authorization(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_realize_stint_specification(self):
        grant_role(self.owner["role"], self.stint_specification.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.test_data, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        stint = Stint.objects.get(stint_specification=self.stint_specification)
        self.assertEqual(result['data']['realizeStintSpecification']['stint']['id'], stint.gql_id)


class TestStintSpecificationSerializerCreate(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.stint_definition = create_test_stintdefinition(frontend=Frontend.objects.get(name='Web'))
        self.input = {
            "input": {
                "name": "TestLabDNM",
                "stintDefinition": self.stint_definition.gql_id,
                "whereToRun": StintSpecification.WHERE_TO_RUN_CHOICES.lab,
                "minTeamSize": 1,
                "maxTeamSize": 2,
                "teamSize": 2,
                "maxNumHumans": 1,
                "minEarnings": 0.5,
                "maxEarnings": 0.75,
                "backupStintSpecification": None,
            }
        }

        self.mutation = """
mutation SerializedStintSpecificationMutation($input: SerializedStintSpecificationInput!){
    serializedStintSpecification(input: $input){
        id
        name
        whereToRun
        minTeamSize
        maxTeamSize
        teamSize
        maxNumHumans
        minEarnings
        maxEarnings
        backupStintSpecification
        allowedLanguageFrontendCombinations{ id }
        stintSpecificationCountries { id }
        moduleSpecifications { id }
        errors {
            field
            messages
        }
    }
}"""

    def test_create(self):
        result = self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        data = result['data']['serializedStintSpecification']
        del data['errors']
        backup_stint_spec = data.pop('backupStintSpecification')
        self.assertEqual(backup_stint_spec, None)
        django_ss_id = from_global_id(data.pop('id'))[1]
        self.assertTrue(StintSpecification.objects.filter(id=django_ss_id).exists())
        data.pop('allowedLanguageFrontendCombinations')
        data.pop('stintSpecificationCountries')
        data.pop('moduleSpecifications')
        for field_name in data:
            self.assertEqual(data[field_name], self.input['input'][field_name])

    def test_create_with_file_field(self):
        backup_stint_spec = StintSpecificationFactory(stint_definition=self.stint_definition)
        self.input['input']['backupStintSpecification'] = backup_stint_spec.name
        result = self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        data = result['data']['serializedStintSpecification']
        del data['errors']
        data.pop('id')
        data.pop('allowedLanguageFrontendCombinations')
        data.pop('stintSpecificationCountries')
        data.pop('moduleSpecifications')
        data_gql_backup_stint_spec_id = data.pop('backupStintSpecification')
        self.assertEqual(data_gql_backup_stint_spec_id, backup_stint_spec.gql_id)
        for field_name in data:
            self.assertEqual(data[field_name], self.input['input'][field_name])

    def test_create_with_many(self):
        frontend = Frontend.objects.get(name='Web')
        language_gql_id = get_gql_id('Language', 'en')
        Language.objects.get(pk=from_global_id(language_gql_id)[1])
        backup_stint_spec = StintSpecificationFactory(stint_definition=self.stint_definition)
        self.input['input']['backupStintSpecification'] = backup_stint_spec.name

        allowedLanguageFrontendCombinations = [{'frontend': frontend.gql_id, 'language': language_gql_id}]
        self.input['input']['allowedLanguageFrontendCombinations'] = allowedLanguageFrontendCombinations
        result = self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        data = result['data']['serializedStintSpecification']
        django_ss_id = from_global_id(data.pop('id'))[1]
        data.pop('errors')
        data.pop('stintSpecificationCountries')
        data.pop('moduleSpecifications')
        backup_stint_spec_data = data.pop('backupStintSpecification')
        allowed_lfcs_data = data.pop('allowedLanguageFrontendCombinations')
        actual_allowed_lfcs = list(
            StintSpecification.objects.get(id=django_ss_id).allowed_language_frontend_combinations.values_list('id', flat=True)
        )
        for lfc_data in allowed_lfcs_data:
            self.assertIn(int(from_global_id(lfc_data['id'])[1]), actual_allowed_lfcs)
        self.assertEqual(backup_stint_spec_data, backup_stint_spec.gql_id)
        for field_name in data:
            self.assertEqual(data[field_name], self.input['input'][field_name])


class TestStintSpecificationSerializerUpdate(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.web = Frontend.objects.get(name='Web')
        self.stint_definition = create_test_stintdefinition(frontend=self.web)
        self.backup_ss = StintSpecificationFactory(stint_definition=self.stint_definition)
        allowed_obj_info = [{'frontend': self.web, 'language': Language.objects.get(pk='en')}]
        self.ss = StintSpecificationFactory(
            stint_definition=self.stint_definition,
            backup_stint_specification=self.backup_ss,
            add_languagefrontends=allowed_obj_info,
        )
        for _ in range(random.randint(1, 3)):
            StintSpecificationCountryFactory(stint_specification=self.ss)
        for _ in range(random.randint(1, 3)):
            StintSpecificationRobotFactory(stint_specification=self.ss)
        for _ in range(random.randint(1, 3)):
            StintSpecificationVariableFactory(stint_specification=self.ss)

        self.input = {
            "input": {
                "id": self.ss.gql_id,
                "stintDefinition": self.stint_definition.gql_id,
                "name": "NewNameWhoDis",
                "whereToRun": StintSpecification.WHERE_TO_RUN_CHOICES.lab,
                "minTeamSize": 4,
                "maxTeamSize": 6,
                "teamSize": 5,
                "maxNumHumans": 2,
                "minEarnings": 300000,
                "maxEarnings": 500000,
                "backupStintSpecification": None,
                "allowedLanguageFrontendCombinations": [],
            }
        }

        # XXX: Add StintModuleSpecification
        self.mutation = """
mutation SerializedStintSpecificationMutation($input: SerializedStintSpecificationInput!){
    serializedStintSpecification(input: $input){
        id
        name
        whereToRun
        minTeamSize
        maxTeamSize
        teamSize
        maxNumHumans
        minEarnings
        maxEarnings
        backupStintSpecification
        allowedLanguageFrontendCombinations{ id }
        stintSpecificationCountries { id }
        errors {
            field
            messages
        }
    }
}"""

    def test_update_non_foreign_attrs(self):
        self.assertEqual(self.ss.allowed_language_frontend_combinations.count(), 1)
        self.assertEqual(self.ss.backup_stint_specification, self.backup_ss)
        self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.ss.refresh_from_db()
        # Declaring null value on m2m should erase instances
        self.assertEqual(self.ss.allowed_language_frontend_combinations.count(), 0)
        self.assertIsNone(self.ss.backup_stint_specification)

        # Checked already
        self.input['input'].pop('allowedLanguageFrontendCombinations')
        self.input['input'].pop('backupStintSpecification')

        # Should not be edited
        self.input['input'].pop('stintDefinition')

        declared_data = self.input['input']
        self.assertEqual(self.ss.name, declared_data['name'])
        self.assertEqual(self.ss.where_to_run, declared_data['whereToRun'])
        self.assertEqual(self.ss.min_team_size, declared_data['minTeamSize'])
        self.assertEqual(self.ss.max_team_size, declared_data['maxTeamSize'])
        self.assertEqual(self.ss.team_size, declared_data['teamSize'])
        self.assertEqual(self.ss.max_num_humans, declared_data['maxNumHumans'])
        self.assertEqual(self.ss.min_earnings, declared_data['minEarnings'])
        self.assertEqual(self.ss.max_earnings, declared_data['maxEarnings'])

    def test_update_file_field(self):
        new_bss = StintSpecificationFactory(stint_definition=self.stint_definition)
        self.input['input']['backupStintSpecification'] = new_bss.name
        self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.ss.refresh_from_db()
        self.assertEqual(self.ss.backup_stint_specification, new_bss)

    def test_update_preexisting_m2m(self):
        for _ in range(random.randint(1, 8)):
            StintSpecificationAllowedLanguageFrontendFactory(stint_specification=self.ss, frontend=self.web)

        preexisting_combo_objs_qs = self.ss.allowed_language_frontend_combinations
        preexisting_combo_objs = list(preexisting_combo_objs_qs.all())
        preexisting_combo_obj_ids = list(preexisting_combo_objs_qs.values_list('id', flat=True))
        preexisting_language_pks = list(preexisting_combo_objs_qs.values_list('language__pk', flat=True))
        preexisting = list(
            self.ss.allowed_language_frontend_combinations.values('id', 'frontend', 'language', 'stint_specification')
        )
        gql_info = []
        for info in preexisting:
            new_info = {}
            new_info['id'] = get_gql_id('StintSpecificationAllowedLanguageFrontend', info['id'])
            new_info['language'] = get_gql_id('Language', info['language'])
            new_info['frontend'] = get_gql_id('Frontend', info['frontend'])
            new_info['stintSpecification'] = get_gql_id('StintSpecification', info['stint_specification'])
            gql_info.append(new_info)
        language = Language.objects.exclude(pk__in=preexisting_language_pks).order_by('?').first()
        new_info = []
        new_info.append(
            {
                'frontend': get_gql_id('Frontend', self.web.pk),
                'language': get_gql_id('Language', language.pk),
                'stintSpecification': self.ss.gql_id,
            }
        )

        stint_spec_country_info = {}
        stint_spec_country_info['stintSpecification'] = self.ss.gql_id
        country_pk = (
            Country.objects.exclude(pk__in=self.ss.stint_specification_countries.values_list('country__pk'))
            .order_by('?')
            .values_list('pk', flat=True)
            .first()
        )
        stint_spec_country_info['country'] = get_gql_id('Country', country_pk)
        self.input['input']['stintSpecificationCountries'] = [stint_spec_country_info]
        gql_info += new_info
        self.input['input']['allowedLanguageFrontendCombinations'] = gql_info
        result = self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        allowedlf_m2m_data = result['data']['serializedStintSpecification']['allowedLanguageFrontendCombinations']
        allowedlf_m2m_ids = [info['id'] for info in allowedlf_m2m_data]
        for combo_obj in preexisting_combo_objs:
            self.assertIn(combo_obj.gql_id, allowedlf_m2m_ids)

        new_combo_objs = self.ss.allowed_language_frontend_combinations.exclude(id__in=preexisting_combo_obj_ids)
        for obj in new_combo_objs.all():
            created_info = {
                'stintSpecification': self.ss.gql_id,
                'frontend': obj.frontend.gql_id,
                'language': get_gql_id('Language', obj.language.pk),
            }
            self.assertIn(created_info, new_info)

        self.assertIsNotNone(self.ss.stint_specification_countries.get(country__pk=country_pk))

    def test_remove_preexisting_m2m(self):
        for _ in range(random.randint(1, 8)):
            StintSpecificationAllowedLanguageFrontendFactory(stint_specification=self.ss, frontend=self.web)

        preexisting_combo_objs_qs = self.ss.allowed_language_frontend_combinations
        preexisting_combo_objs = list(preexisting_combo_objs_qs.all())
        preexisting_combo_obj_ids = list(preexisting_combo_objs_qs.values_list('id', flat=True))
        preexisting_language_pks = list(preexisting_combo_objs_qs.values_list('language__pk', flat=True))

        gql_info = []
        language = Language.objects.exclude(pk__in=preexisting_language_pks).order_by('?').first()
        gql_info.append(
            {
                'frontend': get_gql_id('Frontend', self.web.pk),
                'language': get_gql_id('Language', language.pk),
                'stintSpecification': self.ss.gql_id,
            }
        )
        self.input['input']['allowedLanguageFrontendCombinations'] = gql_info
        result = self.gql_client.execute(
            self.mutation, variable_values=self.input, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        m2m_data = result['data']['serializedStintSpecification']['allowedLanguageFrontendCombinations']
        m2m_ids = [info['id'] for info in m2m_data]
        for combo_obj in preexisting_combo_objs:
            self.assertNotIn(combo_obj.gql_id, m2m_ids)

        new_combo_objs = self.ss.allowed_language_frontend_combinations.exclude(id__in=preexisting_combo_obj_ids)
        for obj in new_combo_objs.all():
            created_info = {
                'stintSpecification': self.ss.gql_id,
                'frontend': obj.frontend.gql_id,
                'language': get_gql_id('Language', obj.language.pk),
            }
            self.assertIn(created_info, gql_info)
