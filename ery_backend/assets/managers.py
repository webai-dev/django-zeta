import io
import imghdr
import logging

from ery_backend.base.managers import EryFileManager


logger = logging.getLogger(__name__)


class GoogleAssetManager(EryFileManager):
    def create_file(self, file_data, **kwargs):
        """
        Create a GoogleAsset object.

        Args:
            file_data: the data to be saved in google storage

        Returns:
            :class:`GoogleAsset`
        """
        asset = self.model(**kwargs)
        asset.save()

        file_io = io.BytesIO(file_data)

        try:
            bucket = asset.bucket
            blob = bucket.blob(asset.filename)
            blob.upload_from_file(file_io)
            logger.info("Uploaded file: %s, to Google Cloud Storage.", asset.filename)
        except Exception as err:
            asset.delete()
            raise err

        return asset


class ImageAssetManager(GoogleAssetManager):
    def create_file(self, file_data, **kwargs):
        """
        Creates an ImageAsset object

        Args:
            file_data: the data to be saved in google storage

        Returns:
            :class:`ImageAsset`
        """
        content_type = imghdr.what("", file_data)
        asset = super().create_file(file_data, content_type=content_type, **kwargs)

        return asset
