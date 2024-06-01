import base64
import json
import re
from string import punctuation

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from languages_plus.models import Language

from .cache import ery_cache


@ery_cache
def get_gql_id(model_name, pk):
    return base64.b64encode(f"{model_name}Node:{pk}".encode('utf-8')).decode('utf-8')


def get_loggedin_client(user):
    """
    Gets  django :class:`Client` with logged in :class:`~ery_backend.users.models.User`.

    Args:
        user (:class:`~ery_backend.users.models.User`): Logged into session and attached to returned :class:`Client`.

    Returns:
        A django :class:`Client` instance.
    """
    from django.test import Client as DjangoClient

    client = DjangoClient()
    client.force_login(user)
    return client


def str_to_bool(value):
    """
    Convert serialized values to bools for evaluation

    Args:
        value (str)
    """
    return value not in ['False', '0', '']


def str_is_num(value):
    """
    Confirms str is a float or int.

    Args:
        value (str): Value to be assessed.

    Returns:
        bool
        value: If bool is True.

    Raises:
        ValueError: If value parameter is not of type str.
    """
    if not isinstance(value, str):
        raise ValueError("Method str_is_num received a value: {}, not of type str".format(value))
    try:
        num = float(value)
        result = True
    except ValueError:
        result = False
        num = None
    return result, num


def str_is_whole(value):
    """
    Check if str is the equivalent of a positive integer.

    Args:
        value (str): Value to be assessed.

    Returns:
        bool
        value: If bool is True.

    Raises:
        ValueError: If valuep arameter is not of type str.
    """
    if not isinstance(value, str):
        raise ValueError("Method parameter_is_whole received a value: {}, not of type str".format(value))
    is_whole = value.isnumeric()
    if is_whole:
        return True, int(value)
    return False, None


def verify(version):
    """
    Confirms all referenced foreign keys in the :class:`reversion.models.Version` instance still exist.

    Args:
        version (:class:`reversion.models.Version`): Past instance state intended for restoration.

    Returns:
        Tuple(bool, Optional(Dict[str: Union[object, str]])): Result of verification and information for error reporting.
    """
    from django.db.models.fields import NOT_PROVIDED

    fields = json.loads(version.serialized_data)[0]['fields']
    for field_str, value in fields.items():
        field = version._model._meta.get_field(field_str)  # pylint:disable=protected-access
        if field.is_relation and not any([field.null, field.default == NOT_PROVIDED]):
            if not field.related_model.objects.filter(pk=value).exists():
                error_info = {'model': field.related_model, 'value': value}
                return False, error_info
    return True, None


def verified_revert(version):
    """
    Wraps :py:meth:`reversion.models.Version.revert` with a check confirming that all referenced foreign keys in the
    :class:`reversion.models.Version` instance still exist.

    Args:
        version (:class:`reversion.models.Version`): Past instance state intended for restoration.

    Raises:
        ValueError: Raised if :class:`reversion.models.Version` instance's serialized_data contains a reference to a
        non-existent related model.
    """
    is_verified, error_info = verify(version)
    if not is_verified:
        raise ValueError(
            f"Version for object, {version.object}, references a nonexistent related model: {error_info['model']}"
            f" with pk {error_info['value']}, and cannot be re-created."
        )
    version.revert()


def opt_out(hand):
    """
    Set :class:`~ery_backend.hands.models.Hand` instance's status to quit.

    Args:
        hand (:class:`~ery_backend.hands.models.Hand`): Target instance.

    Returns:
        str: Success message used as a reply for text based :class:`~ery_backend.frontends.models.Frontend` instances.
    """
    from ery_backend.hands.models import Hand
    from ery_backend.stints.models import Stint

    hand.set_status(Hand.STATUS_CHOICES.quit)
    # XXX: This should be dependent on the stint.cancel_on_quit option. Address in issue #520.
    hand.stint.set_status(Stint.STATUS_CHOICES.cancelled)
    return "You have been logged out"


def get_default_language(pk=False):
    """
    Handles loading order issues from setting language via a regular attribute
    """
    if pk:
        return settings.DEFAULT_LANGUAGE
    return Language.objects.get(pk=settings.DEFAULT_LANGUAGE)


def channel_format(string):
    """Remove or replace characters that are illegal in channel layer naming."""
    for char in string:
        if char in punctuation and char not in ['.', '-']:
            string = string.replace(char, '-')
    return string


def gen_update_variable_message(variable, value, hand):
    """
    Generate websocket update message and target given for a given :class:`~ery_backend.variables.models.VariableMixin`.

    Args:
        variable (:class:`~ery_backend.variables.models.VariableMixin`)
        value (Union[int, float, str, List, Dict])
        hand (:class:`~ery_backend.hands.models.Hand`)
    """
    variable_definition = variable.variable_definition
    message = {}
    message['data'] = {'name': variable_definition.name, 'value': variable.value}
    message['event'] = 'update_var'
    if variable_definition.scope == variable_definition.SCOPE_CHOICES.hand:
        message['data']['scope'] = 'hand'
        group = 'hand'
    elif variable_definition.scope == variable_definition.SCOPE_CHOICES.team:
        message['data']['scope'] = 'team'
        group = 'team'
    elif variable_definition.scope == variable_definition.SCOPE_CHOICES.module:
        message['data']['scope'] = 'module'
        group = 'module'
    return message, group


def gen_socket_messages_from_arg(arg, hand):
    """
    Generate websocket update message.

    Args:
        arg (Union[:class:`Stage`, :class:`ModuleDefinition`, :class:`VariableMixin`])
        hand (:class:`~ery_backend.hands.models.Hand`)
    """
    from ery_backend.frontends.renderers import ReactRenderer
    from ery_backend.modules.models import ModuleDefinition
    from ery_backend.stages.models import Stage
    from ery_backend.variables.models import HandVariable, TeamVariable, ModuleVariable

    if isinstance(arg, list):
        output = []
        for sub_arg in arg:
            output += gen_socket_messages_from_arg(sub_arg, hand)
        return output
    if isinstance(arg, Stage):
        return [{'event': 'current_stage', 'data': {'current_stage': arg.stage_definition.name, 'current_stage_id': arg.id}}]
    if isinstance(arg, ModuleDefinition):
        return [
            {'event': 'current_module', 'data': arg.name},
            {'event': 'update_all_vars', 'data': ReactRenderer.generate_variables(hand)},
        ]

    if isinstance(arg, (HandVariable, TeamVariable, ModuleVariable)):
        return [gen_update_variable_message(arg, arg.value, hand)[0]]

    raise Exception(f'Unknown arg type for {arg}: type{arg}')


def send_websocket_message(hand, message, group='hand'):
    channel_layer = get_channel_layer()
    stint_channel = f'{hand.stint.stint_specification.stint_definition.slug}{hand.stint.id}'
    if group == 'hand':
        channel_name = channel_format(f'{stint_channel}-{hand.user.username}')
        async_to_sync(channel_layer.group_send)(channel_name, message)
    elif group == 'team':
        for team_hand in hand.current_team.hands.filter(status=hand.STATUS_CHOICES.active).all():
            channel_name = channel_format(f'{stint_channel}-{team_hand.user.username}')
            async_to_sync(channel_layer.group_send)(channel_name, message)
    elif group == 'module':
        for module_hand in hand.current_module.current_hands.filter(status=hand.STATUS_CHOICES.active).all():
            channel_name = channel_format(f'{stint_channel}-{module_hand.user.username}')
            async_to_sync(channel_layer.group_send)(channel_name, message)
    else:
        for stint_hand in hand.stint.hands.filter(status=hand.STATUS_CHOICES.active).all():
            channel_name = channel_format(f'{stint_channel}-{stint_hand.user.username}')
            async_to_sync(channel_layer.group_send)(channel_name, message)


def to_snake_case(camelcase):
    """
    Convert camelcase formatted name to snake case

    Args:
        camelcase (str)

    Returns:
        str
    """
    first_cap_re = re.compile('(.)([A-Z][a-z]+)')
    all_cap_re = re.compile('([a-z0-9])([A-Z])')
    s1 = first_cap_re.sub(r'\1_\2', camelcase)
    return all_cap_re.sub(r'\1_\2', s1).lower()
