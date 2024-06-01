import logging

from time import sleep
from google.cloud import datastore
from google.api_core.exceptions import GatewayTimeout


logger = logging.getLogger(__name__)

ery_datastore_client = None


def new_client_on_failure(f):
    """Make the EryDatastoreClient reconnect to the google datastore on predictable errors"""

    def one_last_try(err, *args, **kwargs):
        logger.warning("datastore.Client failure %s on %s", err, f.__name__)
        EryDatastoreClient.reconnect()
        return f(*args, **kwargs)

    def reconnector(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except GatewayTimeout as err:
            return one_last_try(err, *args, **kwargs)

    return reconnector


class EryDatastoreClient:
    """Wrap the google datastore.Client so that we can minimize reconnection costs"""

    def __init__(self):
        self.google_client = datastore.Client()

    @classmethod
    def reconnect(cls):
        cls.google_client = datastore.Client()

    @new_client_on_failure
    def allocate_ids(self, incomplete_key, num_ids):
        """Allocate a list of IDs from a partial key."""
        return self.google_client.allocate_ids(incomplete_key, num_ids)

    @new_client_on_failure
    @property
    def base_url(self):
        """Getter for API base URL"""
        return self.google_client.base_url

    @new_client_on_failure
    def batch(self):
        """Proxy to google.cloud.datastore.bathch.Batch"""
        return self.google_client.batch()

    @new_client_on_failure
    @property
    def current_batch(self):
        """Currently-active batch"""
        return self.google_client.current_batch

    @new_client_on_failure
    @property
    def current_transaction(self):
        """Currently-active transaction"""
        return self.google_client.current_transaction

    @new_client_on_failure
    def delete(self, key):
        """Delete the key in the Cloud Datastore"""
        return self.google_client.delete(key)

    @new_client_on_failure
    def delete_multi(self, keys):
        """Delete keys from the Cloud Datastore"""
        return self.google_client.delete_multi(keys)

    @new_client_on_failure
    def get(self, key, **kwargs):
        """Retrieve an entity from a single key, if it exists."""
        return self.google_client.get(key, **kwargs)

    @new_client_on_failure
    def get_multi(self, keys, **kwargs):
        """Retrieve entities, along with their attributes"""
        return self.google_client.get_multi(keys, **kwargs)

    @new_client_on_failure
    def key(self, *path_args, **kwargs):
        """Proxy to google.cloud.datastore.key.Key"""
        return self.google_client.key(*path_args, **kwargs)

    @new_client_on_failure
    def put(self, entity):
        """Save an entity in the Cloud Datastore"""
        return self.google_client.put(entity)

    @new_client_on_failure
    def put_multi(self, entities):
        """Save entities in the Cloud Datastore.  Automatically batches."""
        return self.google_client.put_multi(entities)

    def auto_batch_puts(self, entities, delay=0):
        """Automatically batch put multiple entities.  Retry if appropriate."""

        if delay > 8:
            raise ValueError("Excessive delay for google batch process: requested {}".format(delay))

        if len(entities) > 500:
            self.auto_batch_puts(entities[:500], delay)
            self.auto_batch_puts(entities[500:], delay)
            return

        if delay > 0:
            logger.warning("Auto batch delayed by %s seconds.", delay)
            sleep(delay)

        try:
            self.put_multi(entities)
        except Exception as err:  # pylint:disable=broad-except
            logger.warning("Got %s when batch saving entities.", err)
            self.auto_batch_puts(entities, (delay + 1))

        return

    @new_client_on_failure
    def query(self, **kwargs):
        """Proxy to google.cloud.datastore.query.Query"""
        return self.google_client.query(**kwargs)

    @new_client_on_failure
    def transaction(self, **kwargs):
        """Proxy to google.cloud.datastore.transaction.Transaction"""
        return self.google_client.transaction(**kwargs)


def get_datastore_client():
    global ery_datastore_client  # pylint:disable=global-statement

    if not ery_datastore_client:
        ery_datastore_client = EryDatastoreClient()
    return ery_datastore_client
