# Derived from https://github.com/NateScarlet/graphene-django-tools/blob/master/graphene_django_tools/dataloader/middleware.py

import logging

from promise import Promise
from promise.dataloader import DataLoader

logger = logging.getLogger(__name__)


def get_model_batch_load_fn(model):
    """Create batch load function for model.  """

    def batch_load_fn(keys):
        logger.debug("Loading dataloader for %s with %s", model, keys)
        return Promise.resolve(model.objects.filter(id__in=keys))

    return batch_load_fn


def get_model_data_loader(model):
    """Create dataloader for model.  """
    return DataLoader(get_model_batch_load_fn(model))


class DataLoaderMiddleware:
    """Middleware to add `context.get_dataloader` method.  """

    cache_attrname = 'data_loader_cache'

    def resolve(self, resolve_next, parent, info, **kwargs):
        """Graphene middleware resolve method."""

        def get_data_loader(model):
            attrname = self.cache_attrname
            if not hasattr(info.context, attrname):
                setattr(info.context, attrname, {})
            cache = getattr(info.context, attrname)
            if model not in cache:
                cache[model] = get_model_data_loader(model)
            return cache[model]

        info.context.get_data_loader = get_data_loader
        return resolve_next(parent, info, **kwargs)
