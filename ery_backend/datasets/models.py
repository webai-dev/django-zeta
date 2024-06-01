import csv
import logging
import pandas as pd
import pygsheets
from google.cloud.datastore.entity import Entity

from django.db import models
from django.utils.crypto import get_random_string

from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.models import EryFile
from ery_backend.base.cache import ery_cache
from ery_backend.datastore.ery_client import get_datastore_client

from .managers import DatasetManager


logger = logging.getLogger(__name__)


class Dataset(EryFile):
    asset = models.OneToOneField("assets.DatasetAsset", on_delete=models.CASCADE, null=True, blank=True)

    objects = DatasetManager()

    _header = None
    _rows = None

    def __init__(self, *args, **kwargs):
        self.datastore_key = None
        self.client = get_datastore_client()
        super().__init__(*args, **kwargs)

    def assign_slug(self, name=None):
        """
        Sets a unique slug for identification during import and duplication methods.

        Args:
            - name (Optional[str]): Slug prefix (included before random string).

        Notes:
            - Model is not saved in this method, which should be used as part of a save override.
        """
        name = self.name if not name else name
        if not name:
            name = get_random_string()

        self.slug = self.create_unique_slug(name)

    @property
    @ery_cache(timeout=3)
    def headers(self):
        key = self.dataset_key
        entity = self.client.get(key)

        if not entity or "headers" not in entity:
            return []

        return entity["headers"]

    @property
    @ery_cache(timeout=3)
    def rows(self):
        query = self.client.query(kind="row", ancestor=self.dataset_key)
        return list(query.fetch())

    @property
    def dataset_key(self):
        if self.datastore_key is None:
            if not self.slug:
                self.assign_slug()
            self.datastore_key = self.client.key("dataset", self.slug)

        return self.datastore_key

    def set_datastore(self, data):
        headers = set()
        row_entities = []

        dataset_entity = Entity(self.dataset_key)
        rows = list(data)
        for row in rows:
            headers = headers.union(set(row.keys()))
        dataset_entity["headers"] = list(headers)

        for i, row in enumerate(rows):
            row_key = self.client.key("row", i + 1, parent=dataset_entity.key)
            entity = Entity(row_key)

            for header in headers:
                entity[header] = row.get(header, None)

            row_entities.append(entity)

        self.client.auto_batch_puts([dataset_entity] + row_entities)

    def set_datastore_from_file(self, file_data):
        def _is_empty(text):
            filtered_text_lines = text.split('\n')
            return not any(line.strip() for line in filtered_text_lines)

        text = file_data.decode("utf-8")
        if _is_empty(text):
            raise EryValidationError("Cannot create datastore from an empty file.")
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(text)
        lines = text.splitlines()

        reader = csv.DictReader(lines, dialect=dialect)

        self.set_datastore(reader)

    def delete_datastore(self, **kwargs):
        """Delete this entity"""
        query = self.client.query(kind="row", ancestor=self.dataset_key)
        row_entities = query.fetch()

        for k in [self.dataset_key] + [row.key for row in row_entities]:
            self.client.delete(k)

        self.asset.delete()
        super().delete(**kwargs)

    def to_pandas(self):
        data = {header: [] for header in self.headers}

        for row in self.rows:
            for header, value in row.items():
                data[header].append(value)

        return pd.DataFrame(data)

    def to_gsheet(self, credentials):
        client = pygsheets.client.Client(credentials)
        sheet = client.create(f"Exported Dataset: {self.name}")
        worksheet = sheet[0]
        worksheet.title = "dataset"

        worksheet.set_dataframe(self.to_pandas(), (1, 1))
        return sheet.url
