"""
Tag:
    A string we use to link a set of keys in the cache. A tag is always a key in the cache,
    and exists to link other keys together for joint invalidation. A tag should not be
    nested within another tag. Rather, invalidation should work on multiple tags if necessary.
"""
from functools import wraps, partial
import logging
import graphql

from django.core.cache import cache

logger = logging.getLogger(__name__)


def _get_update_cache_tag_lock(tag):
    """Return locking handler for cache tag updates."""
    return cache.lock(f'UT:{tag}')


def tag_key(tags, key):
    """
    Link tags to a given key in the cache, such that cache[tag] = [key, ...]
    """
    if isinstance(tags, str):  # If passed a single string, make into an iterable.
        tags = (tags,)

    for tag in tags:
        with _get_update_cache_tag_lock(tag):
            tagged = cache.get(tag) or set()  # Create empty set if new
            tagged.add(key)
            cache.set(tag, tagged)


def set_tagged(key, value, tags, timeout=None):
    """
    Adds key to set of each tag specified in tags.

    Returns:
        True if operation is successful.
    """
    tag_key(tags, key)
    return cache.set(key, value, timeout)


def get_func_cache_key(function, *args, **kwargs):
    """
    Returns:
        Cache key for saving results of functions that are expensive and used often.
    """
    from ery_backend.base.models import EryModel
    from ery_backend.users.models import User

    # XXX: We need to escape ':' in the strings that build up our cache key
    # Will be resolved by issue: #529
    def _argument_key(arg):
        if issubclass(arg.__class__, EryModel) or isinstance(arg, User):
            return arg.get_cache_key()
        if isinstance(arg, graphql.execution.base.ResolveInfo):
            return 'gql_info'
        return repr(arg)

    qn = function.__qualname__

    arg_strings = ",".join([f"{_argument_key(x)}" for x in args])

    kwarg_strings = ",".join([f",{_argument_key(k)}={_argument_key(v)}" for k, v in kwargs.items()])
    key = f"FCK:{qn}:{arg_strings}:{kwarg_strings}"

    return key


def get_func_cache_key_for_hand(code, hand, context=None):
    """
    Generates cache key for JavaScript code given the :class:`~ery_backend.hands.models.Hand` instance's context
    and the version of its connected :class:`~ery_backend.modules.models.ModuleDefinition`.

    Args:
        code (str): Evaluated in EryEngine.
        hand (:class:`~ery_backend.hands.models.Hand`): Provides context and version information.

    Returns:
        Union(bool, str, int, float, List, Dict): Javascript evaluation of code.
    """
    module_definition = hand.current_module.stint_definition_module_definition.module_definition

    if not context:
        context = hand.stint.get_context(hand)

    return f'func:{code}:{context}:{module_definition.version}'


def invalidate_tag(tag):
    """
    Deletes all cache keys in the set of values belonging to tag, as well as tag itself.

    Note:
        If a value or tag intended for deletion does not exist, no error is triggered on cache.delete.
    """
    to_invalidate_items = cache.get(tag)
    if to_invalidate_items is not None:
        with _get_update_cache_tag_lock(tag):
            for item in to_invalidate_items:
                cache.delete(item)
            cache.delete(tag)


def invalidate_handler(sender, instance, **kwargs):
    """
    Convenience method for getting an objects's cache_key and invalidating it. Used in signals.py
    """
    tag = instance.get_cache_tag()
    invalidate_tag(tag)


def ery_cache(func=None, timeout=3600):
    """
    Decorator to memoize function calls using django cache
    """
    if not func:
        return partial(ery_cache, timeout=timeout)

    def _get_tags(args):
        from ery_backend.base.models import EryModel

        ret = set()
        for arg in args:
            if issubclass(arg.__class__, EryModel):
                ret.add(arg.get_cache_tag())
        return ret

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Cache the provided function
        """
        cache_hit = False
        cache_key = get_func_cache_key(func, *args, **kwargs)

        with cache.lock(f'CGS:{cache_key}'):
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                tags = _get_tags(args + tuple(kwargs.values()))
                set_tagged(cache_key, result, tags, timeout)
            else:
                cache_hit = True
        if cache_hit:
            logger.debug("Returning a cached value for key: %s", cache_key)
        else:
            logger.debug("Stored a new cache key: %s", cache_key)

        return result

    wrapper.invalidate = lambda *args, **kwargs: cache.delete(get_func_cache_key(func, *args, **kwargs))
    wrapper.cache_key = lambda *args, **kwargs: get_func_cache_key(func, *args, **kwargs)
    return wrapper
