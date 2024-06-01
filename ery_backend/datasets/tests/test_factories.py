import os
from ery_backend.base.testcases import EryTestCase

from ..models import Dataset
from ..factories import DatasetFactory


class TestDatasetFromFile(EryTestCase):
    def setUp(self):
        self.dataset = Dataset()
        self.file_loc = os.getcwd() + '/ery_backend/datasets/tests/data/test.csv'

    def test_dataset_set_datastore_from_file_produces_correct_headers(self):
        read_file = open(self.file_loc, 'rb')
        self.dataset.set_datastore_from_file(read_file.read())
        for header in ['a', 'b', 'c']:
            self.assertIn(header, self.dataset.headers)

    def test_dataset_set_datastore_from_file_produces_correct_rows(self):
        read_file = open(self.file_loc, 'rb')
        self.dataset.set_datastore_from_file(read_file.read())
        target_row = self.dataset.rows[0]
        self.assertEqual(target_row['a'], '1')
        self.assertEqual(target_row['b'], '2')
        self.assertEqual(target_row['c'], '3')


class TestDatasetFactory(EryTestCase):
    def setUp(self):
        self.known_data = []
        self.known_data.append({'a': '1', 'b': '2', 'c': '3'})
        self.known_data.append({'a': '2', 'b': '3', 'c': '1'})
        self.known_data.append({'a': '4', 'b': '5', 'c': '6'})

    def test_set_datastore_produces_expected_results_from_extracted_factory_data(self):
        dataset = DatasetFactory(to_dataset=self.known_data)
        lookups = [
            [('a', '1'), ('b', '2'), ('c', '3')],
            [('a', '2'), ('b', '3'), ('c', '1')],
            [('a', '4'), ('b', '5'), ('c', '6')],
        ]
        counter = 0
        for row in dataset.rows:
            for lookup_key, lookup_value in lookups[counter]:
                self.assertEqual(row[lookup_key], lookup_value)
            counter += 1
