from django.core.exceptions import ValidationError
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from graphql_relay.node.node import from_global_id

from .utils import channel_format, send_websocket_message, gen_socket_messages_from_arg


def _get_hand_from_context(context):
    from ery_backend.hands.models import Hand
    from ery_backend.stints.models import Stint

    user = context.scope['user']
    if not user or (user and user.is_anonymous):
        raise Exception("Logged in user not found in context!")

    query_string = context.scope['query_string'].decode('UTF-8')
    stint_channel = query_string.replace('stint_channel=', '')
    stint_id = from_global_id(stint_channel)[1]
    stint = Stint.objects.get(id=stint_id)

    hand = Hand.objects.filter(stint=stint, user=user).order_by('id').last()
    return hand


class WebRunnerConsumer(JsonWebsocketConsumer):
    def trigger_form_events(self, data):
        from ery_backend.forms.models import Form
        from ery_backend.stages.models import StageDefinition

        required_subset = set(('gql_id', 'form_data', 'event_type'))
        for element in required_subset:
            if element not in data:
                raise ValidationError(f'{element} not present in {required_subset} required for triggering of form events.')

        form = Form.objects.get(pk=from_global_id(data['gql_id'])[1])
        hand = _get_hand_from_context(self)
        socket_message_args = form.save_data(hand, data['form_data'])
        if data['event_type'] == form.FORM_EVENT_CHOICES.onSubmit and hand.stage.stage_definition.redirect_on_submit:
            # XXX: Need a way to pass this error onto user
            try:
                socket_message_args += hand.submit()
            except StageDefinition.DoesNotExist:  # No next stage
                pass
        if socket_message_args:
            messages = gen_socket_messages_from_arg(socket_message_args, hand)
            send_websocket_message(hand, {'type': 'websocket.send', 'messages': messages})

    def trigger_widget_events(self, data):
        """
        Run events connected to referenced :class:`~ery_backend.widgets.models.Widget`.

        Args:
            - data (Dict[str, str]): Contains info for :class:`~ery_backend.widgets.models.Widget`
              and :`~ery_backend.hands.models.Hand` lookup.

        Notes:
            - data value must contain:
                1) 'gql_id' key with value of connected widget's gql_id
                2) 'stint_id' key with value of connected stint's gql_id
                3) 'event' key with name of JavaScript event.
        """
        from ery_backend.hands.models import Hand
        from ery_backend.forms.models import FormButton
        from ery_backend.modules.widgets import ModuleDefinitionWidget
        from ery_backend.templates.widgets import TemplateWidget

        required_subset = set(('gql_id', 'stint_id', 'name', 'event_type'))
        for element in required_subset:
            if element not in data:
                raise ValidationError(
                    f'"{element}" not present in {required_subset} required for triggering' ' of widget events.'
                )
        wrapper_name, django_id = from_global_id(data['gql_id'])
        if wrapper_name == 'ModuleDefinitionWidgetNode':
            wrapper = ModuleDefinitionWidget.objects.get(pk=django_id)
        elif wrapper_name == 'TemplateWidgetNode':
            wrapper = TemplateWidget.objects.get(pk=django_id)
        elif wrapper_name == 'FormButtonNode':
            wrapper = FormButton.objects.get(pk=django_id)

        hand = Hand.objects.get(user=self.scope['user'], stint__id=data['stint_id'])
        value = data['value'] if 'value' in data and data['value'] != '' else None
        if data['current_stage_id'] == hand.stage.id:
            socket_message_args = wrapper.trigger_events(data['name'], data['event_type'], hand, value=value)
            if socket_message_args:
                messages = gen_socket_messages_from_arg(socket_message_args, hand)
                send_websocket_message(hand, {'type': 'websocket.send', 'messages': messages})

    def connect(self):
        # XXX: Use _get_hand_from_context
        from ery_backend.frontends.renderers import ReactRenderer
        from ery_backend.hands.models import Hand
        from ery_backend.stints.models import Stint

        query_string = self.scope['query_string'].decode('UTF-8')
        stint_channel = query_string.replace('stint_channel=', '')

        user = self.scope['user']
        if user:
            if not user.is_anonymous:
                self.accept()
                formatted_username = channel_format(user.username)
                stint_id = from_global_id(stint_channel)[1]
                stint = Stint.objects.get(id=stint_id)
                stint_definition_slug = stint.stint_specification.stint_definition.slug
                hand = Hand.objects.filter(stint=stint, user=user).order_by('id').last()
                async_to_sync(self.channel_layer.group_add)(
                    f'{stint_definition_slug}{hand.stint.id}-{formatted_username}', self.channel_name
                )
                messages = []
                stint_message = {'event': 'set_stint', 'data': stint_id}
                var_message = {'event': 'update_all_vars', 'data': ReactRenderer.generate_variables(hand)}
                module_message = {'event': 'current_module', 'data': hand.current_module_definition.name}
                stage_message = {
                    'event': 'current_stage',
                    'data': {'current_stage': hand.stage.stage_definition.name, 'current_stage_id': hand.stage.id},
                }

                messages = [stint_message, var_message, module_message, stage_message]
                send_websocket_message(hand, {'type': 'websocket.send', 'messages': messages})
        else:
            self.close()

    def disconnect(self, close_code):
        pass

    def websocket_send(self, content):
        super().send_json(content)

    def receive_json(self, content):
        data = content['data']
        event_type = content['event']
        if event_type == 'widget_event':
            self.trigger_widget_events(data)
        elif event_type == 'form_event':
            self.trigger_form_events(data)
