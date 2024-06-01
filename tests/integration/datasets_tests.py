import json
import os
from random import randrange
from string import Template
import unittest

import pandas as pd

import graphene
from graphql_relay.node.node import from_global_id

from django.test import Client as DjangoClient
from django.core.files.uploadedfile import SimpleUploadedFile

from ery_backend.base.testcases import EryLiveServerTestCase, GQLTestCase, create_test_stintdefinition
from ery_backend.datasets.models import Dataset
from ery_backend.datasets.schema import DatasetQuery
from ery_backend.datastore.ery_client import get_datastore_client
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.mutations import DatasetMutation
from ery_backend.roles.utils import grant_role
from ery_backend.stint_specifications.factories import StintSpecificationFactory, StintSpecificationVariableFactory
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition, HandVariable

DEMO_CSV_NAME = f"{os.getcwd()}/ery_backend/datasets/tests/data/real_estate_sample.csv"
DEMO_HEADERS = [
    "street",
    "city",
    "zip",
    "state",
    "beds",
    "baths",
    "sq__ft",
    "type",
    "sale_date",
    "price",
    "latitude",
    "longitude",
]


class TestDatasetModel(EryLiveServerTestCase):
    """Validate the Dataset model functions"""

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        with open(DEMO_CSV_NAME, "rb") as f:
            cls.data = f.read()

        cls.dataset = Dataset.objects.create_dataset_from_file("test_dataset", cls.data)
        cls.dataset.save()
        cls.dataset.refresh_from_db()

    def setUp(self):
        self.client = get_datastore_client()

    def test_asset_filename(self):
        """
        The asset should have the correct filename
        """
        self.assertEqual(self.dataset.asset.filename, "datasetasset/{}.csv".format(self.dataset.pk))

    def test_asset_data(self):
        """The asset blob should contain the exact same data as the original file."""
        asset = self.dataset.asset
        self.assertEqual(asset.blob.download_as_string(), self.data)

    def test_saved_headers_to_datastore(self):
        """Verify that Dataset._save_headers_to_datastore worked"""
        key = self.client.key("dataset", self.dataset.slug)
        result = self.client.get(key)
        headers = result["headers"]
        headers.sort()
        demo_headers_copy = DEMO_HEADERS.copy()
        demo_headers_copy.sort()
        self.assertEqual(result["headers"], demo_headers_copy)

    def test_rows_saved_to_datastore(self):
        """Verify that Dataset._save_rows_to_datastore worked"""
        dataset_key = self.client.key("dataset", self.dataset.slug)
        row_key1 = self.client.key("row", 1, parent=dataset_key)
        result = self.client.get(row_key1)

        self.assertEqual(result["street"], "3526 HIGH ST")
        self.assertEqual(result["city"], "SACRAMENTO")
        self.assertEqual(result["zip"], "95838")
        self.assertEqual(result["state"], "CA")
        self.assertEqual(result["beds"], "2")
        self.assertEqual(result["baths"], "1")
        self.assertEqual(result["sq__ft"], "836")
        self.assertEqual(result["type"], "Residential")
        self.assertEqual(result["sale_date"], "Wed May 21 00:00:00 EDT 2008")
        self.assertEqual(result["price"], "59222")
        self.assertEqual(result["latitude"], "38.631913")
        self.assertEqual(result["longitude"], "-121.434879")

        row_key4 = self.client.key("row", 4, parent=dataset_key)
        result = self.client.get(row_key4)

        self.assertEqual(result["street"], "2805 JANETTE WAY")
        self.assertEqual(result["city"], "SACRAMENTO")
        self.assertEqual(result["zip"], "95815")
        self.assertEqual(result["state"], "CA")
        self.assertEqual(result["beds"], "2")
        self.assertEqual(result["baths"], "1")
        self.assertEqual(result["sq__ft"], "852")
        self.assertEqual(result["type"], "Residential")
        self.assertEqual(result["sale_date"], "Wed May 21 00:00:00 EDT 2008")
        self.assertEqual(result["price"], "69307")
        self.assertEqual(result["latitude"], "38.616835")
        self.assertEqual(result["longitude"], "-121.439146")

    def test_header_property(self):
        """Verify that Dataset.header returns headers"""
        headers = self.dataset.headers
        headers.sort()
        demo_headers_copy = DEMO_HEADERS.copy()
        demo_headers_copy.sort()
        self.assertEqual(headers, demo_headers_copy)

    def test_iterable_rows(self):
        """Verify that Dataset.rows is iterable"""
        rows = list(self.dataset.rows)
        self.assertEqual(
            [rows[0][col] for col in DEMO_HEADERS],
            [
                "3526 HIGH ST",
                "SACRAMENTO",
                "95838",
                "CA",
                "2",
                "1",
                "836",
                "Residential",
                "Wed May 21 00:00:00 EDT 2008",
                "59222",
                "38.631913",
                "-121.434879",
            ],
        )

        self.assertEqual(
            [rows[3][col] for col in DEMO_HEADERS],
            [
                "2805 JANETTE WAY",
                "SACRAMENTO",
                "95815",
                "CA",
                "2",
                "1",
                "852",
                "Residential",
                "Wed May 21 00:00:00 EDT 2008",
                "69307",
                "38.616835",
                "-121.439146",
            ],
        )

    def test_delete_dataset(self):
        with open(DEMO_CSV_NAME, "rb") as f:
            data = f.read()
            dataset = Dataset.objects.create_dataset_from_file("test-delete-name", data)

        dataset_key = dataset.dataset_key
        query = self.client.query(kind="row", ancestor=dataset_key)
        dataset.delete_datastore()

        self.assertEqual(self.client.get(dataset_key), None)
        self.assertEqual(list(query.fetch()), [])

    @unittest.skip("XXX: Address in #711")
    def test_datastore_to_pandas(self):
        data = {header: [] for header in self.dataset.headers}
        df = pd.DataFrame(data)
        self.assertNotEqual(df, self.dataset.to_pandas())


class TestQuery(DatasetQuery, graphene.ObjectType):
    pass


class TestMutation(DatasetMutation, graphene.ObjectType):
    pass


class TestReadDatasetSchema(GQLTestCase):
    node_name = "DatasetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)

        with open(DEMO_CSV_NAME, "rb") as f:
            data = f.read()
            dataset = Dataset.objects.create_dataset_from_file("test-read-database-name", data)

            grant_role(cls.viewer["role"], dataset, cls.viewer["user"])

            cls.dataset = dataset
            cls.dataset_gql_id = dataset.gql_id

    def test_read_requires_privs(self):
        query = Template("""{ dataset(id: "$gi"){ rows { columns }}}""").substitute(gi=self.dataset_gql_id)
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_full_dataset(self):
        query = Template("""{ dataset(id: "$gi"){ rows { columns }}}""").substitute(gi=self.dataset_gql_id)
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        row1 = result["data"]["dataset"]["rows"][0]
        self.assertEqual(row1["columns"][self.dataset.headers.index('street')], "3526 HIGH ST")
        self.assertEqual(row1["columns"][self.dataset.headers.index('city')], "SACRAMENTO")
        self.assertEqual(row1["columns"][self.dataset.headers.index('zip')], "95838")
        self.assertEqual(row1["columns"][self.dataset.headers.index('state')], "CA")
        self.assertEqual(row1["columns"][self.dataset.headers.index('beds')], "2")
        self.assertEqual(row1["columns"][self.dataset.headers.index('baths')], "1")
        self.assertEqual(row1["columns"][self.dataset.headers.index('sq__ft')], "836")
        self.assertEqual(row1["columns"][self.dataset.headers.index('type')], "Residential")
        self.assertEqual(row1["columns"][self.dataset.headers.index('sale_date')], "Wed May 21 00:00:00 EDT 2008")
        self.assertEqual(row1["columns"][self.dataset.headers.index('price')], "59222")
        self.assertEqual(row1["columns"][self.dataset.headers.index('latitude')], "38.631913")
        self.assertEqual(row1["columns"][self.dataset.headers.index('longitude')], "-121.434879")

        row4 = result["data"]["dataset"]["rows"][3]

        self.assertEqual(row4["columns"][self.dataset.headers.index('street')], "2805 JANETTE WAY")
        self.assertEqual(row4["columns"][self.dataset.headers.index('city')], "SACRAMENTO")
        self.assertEqual(row4["columns"][self.dataset.headers.index('zip')], "95815")
        self.assertEqual(row4["columns"][self.dataset.headers.index('state')], "CA")
        self.assertEqual(row4["columns"][self.dataset.headers.index('beds')], "2")
        self.assertEqual(row4["columns"][self.dataset.headers.index('baths')], "1")
        self.assertEqual(row4["columns"][self.dataset.headers.index('sq__ft')], "852")
        self.assertEqual(row4["columns"][self.dataset.headers.index('type')], "Residential")
        self.assertEqual(row4["columns"][self.dataset.headers.index('sale_date')], "Wed May 21 00:00:00 EDT 2008")
        self.assertEqual(row4["columns"][self.dataset.headers.index('price')], "69307")
        self.assertEqual(row4["columns"][self.dataset.headers.index('latitude')], "38.616835")
        self.assertEqual(row4["columns"][self.dataset.headers.index('longitude')], "-121.439146")

    def test_read_row_ids(self):
        query = Template("""{ dataset(id: "$gi"){ rows { id columns }}}""").substitute(gi=self.dataset_gql_id)
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        rows = result["data"]["dataset"]["rows"]
        row_number = randrange(0, len(rows))
        row = rows[row_number]

        columns1 = row["columns"]

        query = Template("""{datasetRow(id: "$ri"){id columns}}""").substitute(ri=row["id"])
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)

        columns2 = result["data"]["datasetRow"]["columns"]

        for i, _ in enumerate(columns2):
            self.assertEqual(
                columns2[i],
                columns1[i],
                msg="row {} column {} mismatch."
                "ID: {}".format(row_number, i, from_global_id(result["data"]["datasetRow"]["id"])),
            )


class TestDeleteDatasetSchema(GQLTestCase):
    node_name = "DatasetNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def prep_dataset(self):
        with open(DEMO_CSV_NAME, "rb") as f:
            data = f.read()
            dataset = Dataset.objects.create_dataset_from_file("test-delete-dataset", data)
            grant_role(self.owner["role"], dataset, self.owner["user"])

            return dataset

    def test_delete_requires_privs(self):
        dataset = self.prep_dataset()
        ds_id = dataset.pk
        ds_gql_id = dataset.gql_id
        mutation = """mutation DeleteDataset{deleteDataset(input: {id: "%s"}){id}}""" % (ds_gql_id,)

        response = self.gql_client.execute(mutation)
        self.assert_query_was_unauthorized(response)

        response = self.gql_client.execute(mutation, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.assert_query_was_unauthorized(response)
        Dataset.objects.get(pk=ds_id)

    def test_delete_produces_result(self):
        dataset = self.prep_dataset()
        ds_gql_id = dataset.gql_id
        mutation = """mutation DeleteDataset{deleteDataset(input: {id: "%s"}){id}}""" % (ds_gql_id,)

        response = self.gql_client.execute(mutation, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(response)
        dataset.refresh_from_db()
        self.assertEqual(dataset.state, dataset.STATE_CHOICES.deleted)


class TestImportDatasetFromCSV(EryLiveServerTestCase):
    def setUp(self):
        self.driver = self.get_loggedin_driver('user', headless=True)

    def test_import_csv(self):
        self.driver.get(f'{self.live_server_url}/import/dataset_file')
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys('TestDataset')
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/datasets/tests/data/test.csv')
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        dataset_qs = Dataset.objects.filter(name='TestDataset')
        self.assertEqual(dataset_qs.count(), 1)
        dataset = dataset_qs.first()
        headers = dataset.headers
        headers.sort()
        row = dataset.rows[0]

        self.assertEqual(headers, ['a', 'b', 'c'])
        self.assertEqual(row, {'a': '1', 'b': '2', 'c': '3'})


class TestUploadDataset(EryLiveServerTestCase):
    def test_upload_requires_privilege(self):
        with open(DEMO_CSV_NAME, "rb") as f:
            data = f.read()
            file_obj = SimpleUploadedFile(name="real_estate.csv", content=data, content_type="text/csv")

        client = DjangoClient()
        mutation_response = client.post(
            f'{self.live_server_url}/graphql/',
            {
                'file': file_obj,
                'query': """
mutation {
    uploadDataset(input: {}) {
        success
        datasetEdge {
            node {
                id
            }
        }
    }
}""",
            },
        )
        mutation_content = json.loads(mutation_response.content.decode('utf-8'))
        self.assertEqual(mutation_content['errors'][0]['message'], 'not authorized')

    def test_upload_produces_result(self):
        with open(DEMO_CSV_NAME, "rb") as f:
            data = f.read()
            file_obj = SimpleUploadedFile(name="real_estate.csv", content=data, content_type="text/csv")

        user = UserFactory()
        loggedin_client = self.get_loggedin_client(user)
        mutation_response = loggedin_client.post(
            f'{self.live_server_url}/graphql/',
            {
                'file': file_obj,
                'query': """
mutation {
    uploadDataset(input: {}) {
        success
        datasetEdge {
            node {
                id
            }
        }
    }
}""",
            },
        )
        mutation_content = json.loads(mutation_response.content.decode('utf-8'))
        self.assertTrue(mutation_content['data']['uploadDataset']['success'])

        query_response = loggedin_client.post(
            f'{self.live_server_url}/graphql/',
            {
                'query': """
query DatasetQuery{
    viewer{
        allDatasets {
            edges {
                node{
                    id
                    name
                }
            }
        }
    }
}"""
            },
        )
        query_content = json.loads(query_response.content.decode('utf-8'))
        self.assertIsNotNone(query_content['data']['viewer']['allDatasets']['edges'][0]['node']['id'])

    def test_upload_with_folder(self):
        with open(DEMO_CSV_NAME, "rb") as f:
            data = f.read()
            file_obj = SimpleUploadedFile(name="real_estate.csv", content=data, content_type="text/csv")

        user = UserFactory()
        loggedin_client = self.get_loggedin_client(user)
        mutation_response = loggedin_client.post(
            f'{self.live_server_url}/graphql/',
            {
                'file': file_obj,
                'query': """
mutation {
    uploadDataset(input: {
        folder: "%s"
    }) {
        success
        datasetEdge {
            node {
                id
            }
        }
    }
}"""
                % user.my_folder.gql_id,
            },
        )

        mutation_content = json.loads(mutation_response.content.decode('utf-8'))
        self.assertTrue(mutation_content['data']['uploadDataset']['success'])
        query_response = loggedin_client.post(
            f'{self.live_server_url}/graphql/',
            {
                'query': """
query DatasetQuery {
    viewer {
        myFolder {
            links {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    }
}"""
            },
        )
        query_content = json.loads(query_response.content.decode('utf-8'))
        self.assertEqual(len(query_content['data']['viewer']['myFolder']['links']['edges']), 1)


class TestImportDatasetToStintSpecificationVariables(EryLiveServerTestCase):
    """
    Confirm dataset can be imported and used to populate variables that would normally be configured by
    StintSpecificationVariable
    """

    def setUp(self):
        self.driver = self.get_loggedin_driver('user', headless=True)

    def test_import_to_ssv(self):
        # First, import dataset
        self.driver.get(f'{self.live_server_url}/import/dataset_file')
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys('TestDataset')
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/datasets/tests/data/test.csv')
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        dataset_qs = Dataset.objects.filter(name='TestDataset')
        self.assertEqual(dataset_qs.count(), 1)
        dataset = dataset_qs.first()

        # Second, link to specification (w/ StintSpecVars to be overriden)
        stint_definition = create_test_stintdefinition(Frontend.objects.get(name='Web'))
        stint_specification = StintSpecificationFactory(stint_definition=stint_definition)
        md = stint_definition.module_definitions.first()
        int_type = VariableDefinition.DATA_TYPE_CHOICES.int
        hand_scope = VariableDefinition.SCOPE_CHOICES.hand
        vd1 = VariableDefinitionFactory(module_definition=md, name='a', data_type=int_type, scope=hand_scope)
        StintSpecificationVariableFactory(variable_definition=vd1, stint_specification=stint_specification, value=None)
        vd2 = VariableDefinitionFactory(module_definition=md, name='b', data_type=int_type, scope=hand_scope)
        StintSpecificationVariableFactory(variable_definition=vd2, stint_specification=stint_specification, value=None)
        vd3 = VariableDefinitionFactory(module_definition=md, name='c', data_type=int_type, scope=hand_scope)
        StintSpecificationVariableFactory(variable_definition=vd3, stint_specification=stint_specification, value=None)
        stint_specification.dataset = dataset
        stint_specification.save()

        # Third, be informed of changed values
        id_vals = stint_specification.get_dataset_variables()
        vd_ids = list(id_vals.keys())
        id_names = dict(VariableDefinition.objects.filter(id__in=vd_ids).values_list('id', 'name'))
        names_vals = {id_names[vd_id]: id_vals[vd_id] for vd_id in vd_ids}
        self.assertEqual(dataset.rows[0], names_vals)

        # Third, populate variables and confirm values are from dataset
        ids_vals = stint_specification.get_dataset_variables()
        user = UserFactory()
        stint = stint_specification.realize(user)
        HandFactory(stint=stint, current_module=None)
        stint.start(user)
        hv1 = HandVariable.objects.get(variable_definition=vd1)
        self.assertEqual(hv1.value, int(ids_vals[vd1.id]))
        hv2 = HandVariable.objects.get(variable_definition=vd2)
        self.assertEqual(hv2.value, int(ids_vals[vd2.id]))
        hv3 = HandVariable.objects.get(variable_definition=vd3)
        self.assertEqual(hv3.value, int(ids_vals[vd3.id]))
