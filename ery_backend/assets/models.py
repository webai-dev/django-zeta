import logging

from django.db import models
from django.conf import settings
from django.http import HttpResponse

from google.cloud import storage
from model_utils import Choices

from ery_backend.base.models import EryFile, EryPrivileged

from .managers import GoogleAssetManager, ImageAssetManager

logger = logging.getLogger(__name__)


class GoogleAssetMixin:
    """
    Save files on the google storage platform.
    """

    content_type = NotImplemented
    objects = GoogleAssetManager()

    @property
    def filename(self):
        """
        Filenames are used to identify and retrieve the data from google storage buckets.
        """
        if self.pk is None:
            raise ValueError("Cannot have a file name without a pk")

        return f"{self.__class__.__name__.lower()}/{self.pk}.{self.content_type.lower()}"

    @property
    def http_response(self):
        raise NotImplementedError('Method not implemented!')

    @property
    def bucket(self):
        client = storage.Client()
        bucket_name = "ery_backend"

        if settings.TESTING:
            bucket_name = f"{bucket_name}-testing"

        bucket = client.bucket(bucket_name)

        if not bucket.exists():
            logger.info("Datastore bucket %s did not exist. Creating.", bucket_name)
            bucket.create("us")
            logger.info("Created bucket: %s, in Google Cloud Storage.", bucket_name)

        return bucket

    @property
    def blob(self):
        bucket = self.bucket
        blob = bucket.get_blob(self.filename)

        if blob is None:
            raise ValueError(f"Missing {self.filename} from google storage bucket {bucket.name}")

        return blob

    def delete(self, **kwargs):
        bucket = self.bucket
        bucket.delete_blob(self.filename)
        logger.info("Deleted file: %s, from Google Cloud Storage.", self.filename)
        super().delete(**kwargs)


class ImageAsset(EryFile, GoogleAssetMixin):
    """
    Save images on the google storage platform.
    """

    HTTP_CONTENT_TYPES = Choices(("gif", "image/gif"), ("png", "image/png"), ("jpeg", "image/jpeg"))

    objects = ImageAssetManager()

    content_type = models.CharField(max_length=4, choices=HTTP_CONTENT_TYPES)

    @property
    def http_response(self):
        """
        Produces the stored data as an http response
        """
        ct = self.HTTP_CONTENT_TYPES[self.content_type]
        hr = HttpResponse(content_type=ct)
        self.blob.download_to_file(hr)
        return hr

    def delete(self, **kwargs):
        """
        Combine inherited delete method from :class:`~ery_backend.base.models.EryFile` with that
        inherited from :class:`GoogleAssetMixin`.
        """
        bucket = self.bucket
        bucket.delete_blob(self.filename)
        logger.info("Deleted file: %s, from Google Cloud Storage.", self.filename)
        super().delete(**kwargs)


class DatasetAsset(EryPrivileged, GoogleAssetMixin):
    """
    Save Dataset Asset CSV
    """

    objects = GoogleAssetManager()
    content_type = 'csv'

    @property
    def http_response(self):
        """
        Produces the stored data as an http response
        """
        hr = HttpResponse(content_type="text/csv")
        self.blob.download_to_file(hr)
        return hr
