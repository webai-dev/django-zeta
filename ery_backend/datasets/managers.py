from ery_backend.assets.models import DatasetAsset
from ery_backend.base.managers import EryManager


class DatasetManager(EryManager):
    def create_dataset_from_file(self, name, file_data, *args, **kwargs):
        """
        Create the asset and google entitity before providing a dataset.

        Args:
            - headers (List[str]): headers for the csv data.
            - file_data [bytes]: file contents, excluding any headers

        Returns:
           :class:`~ery_backend.datasets.models.Dataset`

        """
        asset = DatasetAsset.objects.create_file(file_data)
        dataset = self.model(name=name, asset=asset)
        dataset.save()

        dataset.set_datastore_from_file(file_data)

        return dataset
