# XXX: Address in issue #525
# from datetime import datetime
# import pytz

# from google.api_core.exceptions import ServiceUnavailable

# from ery_backend.base.testcases import EryTestCase
# from ery_backend.datastore.ery_client import ery_datastore_client
# from ..factories import DatasetFactory


# class TestDataset(EryTestCase):
#     """
#     test dataset correctly being put into the datastore and can be rendered to pd and viewed as csv or gsheet.
#     """

#     def setUpClass()
#     client = ery_datastore_client
#     dataset = DatasetFactory()


#     def test_dataset_entity(self):
#         try:
#             self.client.put(datasetEntity)
#             datasetEntity = self.client.get(dataset.key)
#         except ServiceUnavailable:
#             raise Exception("Could not connect to datastore")
#         self.assertEqual(datasetEntity.kind, "Dataset")
#         self.assertEqual(datasetEntity.key.id_or_name, dataset.get("pk"))
#         self.assertEqual(datasetEntity.key.id_or_name, dataset.get("pk"))
#         self.assertEqual(datasetEntity["pk"], dataset.pk)
#         self.assertEqual(datasetEntity["headers"], dataset.headers)

#     def test_row_entity(self):
#         row = RowEntityFactory(parent=Dataset.key)
#         try:
#             self.client.put(rowEntity)
#             rowEntity = self.client.get(row.key)
#         except ServiceUnavailable:
#             raise Exception("Could not connect to datastore")
#         for row in dataset:
#             headers = headers.union(set(row.keys()))
#         self.assertEqual(rowEntity.kind, "Row")
#         self.assertEqual(rowEntity.key.id_or_name, row.get("pk"))
#         self.assertEqual(rowEntity.key.parent, Dataset.key)
#         self.assertEqual(rowEntity.key.id_or_name, row.get("pk"))
#         self.assertEqual(rowEntity["pk"], row.pk)
#         self.assertEqual(rowEntity["header"], row.value)

#     def test_to_panda(self):
#         pass

#     def test_to_csv(self):
#         pass

#     def test_to_gsheet(self):
#         pass
