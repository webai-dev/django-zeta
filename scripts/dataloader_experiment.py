import logging

from promise import Promise
from promise.dataloader import DataLoader

from ery_backend.stints.models import Stint

logger = logging.getLogger(__name__)


def get_model_batch_load_fn(model):
    """Create batch load function for model.  """

    def batch_load_fn(keys):
        print(f'Loading dataloader for {model} with {keys}')
        return Promise.resolve(model.objects.filter(id__in=keys))

    return batch_load_fn


def get_model_data_loader(model):
    """Create dataloader for model.  """
    return DataLoader(get_model_batch_load_fn(model))


def run():
    stint_dl = get_model_data_loader(Stint)
    print(stint_dl.load(162))
