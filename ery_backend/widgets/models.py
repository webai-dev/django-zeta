import json

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import gettext_lazy as _

from languages_plus.models import Language
from model_utils import Choices

from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.models import EryFile, EventModel, EventStepModel, EryNamedPrivileged
from ery_backend.base.mixins import ReactNamedMixin
from ery_backend.base.utils import get_default_language


class WidgetState(EryNamedPrivileged):
    parent_field = 'widget'

    widget = models.ForeignKey('widgets.Widget', on_delete=models.CASCADE, related_name="states")
    default_value = JSONField(blank=True, null=True)
    from_prop = models.BooleanField(default=False, help_text="Default value should be taken from a passed prop")

    def get_default_value(self):
        return json.dumps(self.default_value)

    @property
    def json_default_value(self):
        return json.dumps(self.default_value)


class WidgetEvent(EventModel):
    """
    Define specific circumstances during which a set of actions (server-side or client-side) should be run.

    Attributes:
        - REACT_EVENT_CHOICES: Possible React events that can trigger associated actions (from :class:`EventModel`).
        - SMS_EVENT_CHOICES: Possible SMS events that can trigger associated actions (from :class:`EventModel`).
    """

    class Meta(EventModel.Meta):
        # XXX: Address in issue #815
        # unique_together = (('widget', 'event_type', 'name'),)
        pass

    class SerializerMeta(EventModel.SerializerMeta):
        model_serializer_fields = ('steps',)

    parent_field = 'widget'

    widget = models.ForeignKey(
        'widgets.Widget', on_delete=models.CASCADE, related_name='events', help_text="Parental instance"
    )

    @staticmethod
    def get_bxml_serializer():
        from .serializers import WidgetEventBXMLSerializer

        return WidgetEventBXMLSerializer

    @staticmethod
    def get_duplication_serializer():
        from .serializers import WidgetEventDuplicationSerializer

        return WidgetEventDuplicationSerializer

    def trigger(self, hand):
        """
        Signal event to execute associated action, as determined by event_type attribute.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context (if required)
              during execution of associated action.
        """
        socket_message_args = []

        for step in self.steps.all():
            if step.event_action_type == step.EVENT_ACTION_TYPE_CHOICES.submit:
                socket_message_args += hand.submit()
            elif step.event_action_type == step.EVENT_ACTION_TYPE_CHOICES.back:
                socket_message_args += hand.back()
        return socket_message_args


class WidgetEventStep(EventStepModel):
    """
    Define specific circumstances during which a set of actions (server-side or client-side) should be run.

    Attributes:
        - EVENT_TYPE_CHOICES: Types of actions associated with the given instance.

    """

    parent_field = 'widget_event'

    EVENT_ACTION_TYPE_CHOICES = Choices(('run_code', _('Code')), ('back', _('Back')), ('submit', _('Submit')))

    REQUIRE_COMMUNCIATE_ACTION_TYPES = ('back', 'submit')

    widget_event = models.ForeignKey(
        'widgets.WidgetEvent', on_delete=models.CASCADE, related_name='steps', help_text="Parental instance"
    )
    code = models.TextField(help_text="Javascript evaluated on trigger", blank=True, null=True)
    event_action_type = models.CharField(max_length=16, choices=EVENT_ACTION_TYPE_CHOICES)

    def clean(self):
        super().clean()
        if self.code not in [None, ""] and self.event_action_type != self.EVENT_ACTION_TYPE_CHOICES.run_code:
            raise ValidationError(
                {
                    'event_action_type': f"event_action_type must be '{self.EVENT_ACTION_TYPE_CHOICES.run_code}' for"
                    f" {self.__class__.__name__}.code (belonging to {self.widget_event}) to"
                    " have a value."
                }
            )


class WidgetProp(EryNamedPrivileged):
    RESERVED_NAMES = ('choices',)

    parent_field = 'widget'

    widget = models.ForeignKey('widgets.Widget', on_delete=models.CASCADE, related_name='props')
    default_value = JSONField(blank=True, null=True)
    preview_value = JSONField(blank=True, null=True)

    @property
    def json_default_value(self):
        return json.dumps(self.default_value)

    @property
    def json_preview_value(self):
        return json.dumps(self.preview_value)

    def clean(self):
        super().clean()
        if self.name in self.RESERVED_NAMES:
            raise ValueError(f'{self.name} is a reserved word')


def _gen_default_widget_parameters():
    return ['event']


class Widget(ReactNamedMixin, EryFile):
    """
    Define how the associated model should be rendered for given :class:`~ery_backend.frontends.models.Frontend`.

    Attributes:
        - is_multiple_choice (Bool): Flagged by user to allow addition of choice fields
          (e.g., :class:`~ery_backend.forms.models.FormFieldChoice, :class:`~ery_backend.modules.models.WidgetChoice`)
          on the frontend.
    """

    class SerializerMeta(EryFile.SerializerMeta):
        model_serializer_fields = ('connections', 'events', 'props', 'states')

    code = models.TextField(blank=True, null=True, help_text="Javascript used to render model instance")
    is_multiple_choice = models.BooleanField(default=False)
    primary_language = models.ForeignKey(
        Language,
        default=get_default_language(pk=True),
        on_delete=models.SET_DEFAULT,
        help_text="Language for the primary implementation of the widget.",
    )
    save_null = models.BooleanField(
        default=True,
        help_text="Whether to save null values recieved in a :class:`~ery_backend.modules.widgets.ModuleEvent or"
        ":class:`~ery_backend.widgets.models.Event`",
    )

    # length determined to leave room for extremly long package names.
    address = models.CharField(max_length=256, blank=True, null=True, help_text="Location of package code to import")
    external = models.BooleanField(default=False, help_text="Used to flag external packages")
    frontend = models.ForeignKey('frontends.Frontend', on_delete=models.PROTECT)
    namespace = models.CharField(max_length=24, default='Widget', help_text="This is case insensitive and always capitalized")
    parameters = JSONField(
        default=_gen_default_widget_parameters, help_text="Expected parameters for associated React synthetic events."
    )
    related_widgets = models.ManyToManyField(
        'widgets.Widget',
        blank=True,
        help_text=":class:`Widget` objects having unique :class:`ery_backend.frontends.models.Frontend` objects to"
        " be used as replacements.",
    )
    value_parameter = models.CharField(
        max_length=80, default='event.target.value', help_text="Expected value paramter in associated React synthetic events."
    )

    parameters = JSONField(
        default=_gen_default_widget_parameters, help_text="Expected parameters for associated React synthetic events."
    )
    save_null = models.BooleanField(
        default=True,
        help_text="Whether to save null values recieved in a :class:`~ery_backend.modules.widgets.ModuleEvent or"
        ":class:`~ery_backend.widgets.models.Event`",
    )

    @property
    def connected_widgets(self):
        """
        Convenience method combining forward and reverse relationships with other :class:`Widget` objects.

        Notes:
            - Given our low amount of intended frontends and limitation of one connected
              :class:`Widget` per :class:`~ery_backend.frontends.models.Frontend`, the uses of
              'all' in this query should never be expensive.
        """
        # XXX: Address in issue #506. Require edit privilege on both models to connect via mutation.
        return self.related_widgets.all().union(self.widget_set.all())

    @classmethod
    def get_nested_connected_widget_ids(cls, widget_id):
        """
        Get ids of all dependencies.

        Attrs:
            - widget_id (int): Originating widget.

        Returns:
            set
        """
        output = set()

        nested_ids = WidgetConnection.objects.filter(originator__id=widget_id).values_list('target__id', flat=True)
        for nested_id in nested_ids:
            output.update(cls.get_nested_connected_widget_ids(nested_id))
            output.update((nested_id,))

        return output

    def get_all_connected_widgets(self):
        return Widget.objects.filter(id__in=self.get_nested_connected_widget_ids(self.id))

    @classmethod
    def import_instance_from_xml(cls, xml, name=None, connect_widgets=False):
        return super().import_instance_from_xml(xml, name)

    def duplicate(self, name=None, connect_widgets=False):
        """
        Returns:
            A duplicated model instance, with option of modifying attributes.

        Args:
            - name(str): If specified, the new name that will be used instead of the original.
            - replace_kwargs(Dict[str: Union[str, EryModel]]): If specified, key-value dictionary
              where key specifies attributes to be used instead of the original ones.
            - connect_widgets(bool): If True, an attempt is made to connect related_widgets. This
              will fail if any of the designated :class:`Widget` objects are connected to different
              :class:`Widget` objects of the same :class:`~ery_backend.frontend.models.Frontend`.
        """
        return super().duplicate()

    def render_web(self, language):
        """
        Render self-contained ES6 code for :class:`Widget`.

        Notes:
            - Includes all relevant :class:`Widget` and :class:`ExternalWidget` definitions for reference.
        """
        from ery_backend.frontends.renderers import ReactWidgetRenderer

        if self.frontend.name == 'Web':
            return ReactWidgetRenderer(self, language).render()

        if self.frontend.name == 'SMS':
            return f'{self.code}'

        raise NotImplementedError(f"Method not implemented for {self.frontend}")

    def connect(self, widget):
        """
        Convenience method for adding a :class:`Widget`.

        Args:
            - widget (:class:`Widget`): Must have different, unique :class:`~ery_backend.frontend.models.Frontend`
              (out of set of :class:`Widget` objects connected to the given :class:`Widget`.)
        """
        if widget in self.connected_widgets.all():
            raise EryValidationError(f'Widget: {widget}, has already been connected to Widget: {self}.')
        if widget.frontend.id in list(self.connected_widgets.values_list('frontend', flat=True)) + [self.frontend.id]:
            raise EryValidationError(
                f'Widget: {widget}, has a frontend already present in the set of' f' frontends connected to Widget: {self}.'
            )
        if self.frontend.id in list(widget.connected_widgets.values_list('frontend', flat=True)) + [widget.frontend.id]:
            raise EryValidationError(
                f'Widget: {self}, has a frontend already present in the set of' f' frontends connected to Widget: {widget}.'
            )
        self.related_widgets.add(widget)

    def disconnect(self, widget):
        """
        Convenience method for disconnecting a :class:`Widget`.

        Args:
            - widget (:class:`Widget`)
        """
        if widget in self.related_widgets.all():
            self.related_widgets.remove(widget)
        elif widget in self.widget_set.all():
            widget.related_widgets.remove(self)

    def clean(self):
        super().clean()
        if self.id:
            if self.frontend.id in list(self.connected_widgets.values_list('frontend', flat=True)):
                raise EryValidationError(
                    f"A widget with frontend: {self.frontend}, is already connected to Widget: {self}."
                    f" Widget: {self} may not take on said frontend until the connected widget is"
                    " disconnected."
                )
        if not self.external and not self.code:
            raise EryValidationError({'code': f'Widgets with external=False require a value for their code attribute.'})
        if self.external and not self.address:
            raise EryValidationError({'address': f'Widgets with external=True require a value for their address attribute.'})

    def _invalidate_related_tags(self, history):
        for widget_wrapper_manager in [self.module_widgets, self.template_widgets]:
            for widget_wrapper in widget_wrapper_manager.all():
                widget_wrapper.invalidate_tags(history)

    def get_events_info(self):
        return [
            (
                event.name,
                event.event_type,
                event.steps.filter(event_action_type__in=WidgetEventStep.REQUIRE_COMMUNCIATE_ACTION_TYPES).exists(),
                [
                    (i, step.code)
                    for i, step in enumerate(
                        event.steps.filter(event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code)
                    )
                ],
            )
            for event in self.events.all()
        ]


class WidgetConnection(ReactNamedMixin, EryNamedPrivileged):
    """
    Add alias for the target Widget :class:`~ery_backend.widgets.models.Widget` when used
    in the originator :class:`~ery_backend.widgets.models.Widget`.

    Additionally:
        - Adds a unique identifier (i.e., name) for :class:`Widget` instance.
    """

    parent_field = "originator"

    originator = models.ForeignKey(
        'widgets.Widget', on_delete=models.CASCADE, related_name='connections', help_text="Originating :class:`Widget`"
    )
    target = models.ForeignKey(
        'widgets.Widget', on_delete=models.CASCADE, related_name='targets', help_text="Target :class:`Widget`"
    )

    def _invalidate_related_tags(self, history):
        """
        Invalidate own cache tag and those of related models.

        Args:
            - history (List[:class:`EryModel`]): Keeps track of which models have already
              had their tags invalidated to prevent circularity.
        """

        self.originator.invalidate_tags(history)
