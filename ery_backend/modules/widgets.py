import json
import random

from django.db import models, IntegrityError
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from model_utils import Choices
from languages_plus.models import Language

from ery_backend.base.mixins import ChoiceMixin, ReactNamedMixin, ChoiceHolderMixin
from ery_backend.base.models import EryPrivileged, EryNamedPrivileged, EventModel, EventStepModel


class WidgetChoiceTranslation(EryPrivileged):
    """
    Units of :class:`WidgetChoice` describing the :class:`Language` for rendering content.
    """

    class Meta:
        """Meta"""

        unique_together = (('widget_choice', 'language',),)
        db_table = 'modules_widgetchoicetranslation'

    parent_field = 'widget_choice'
    widget_choice = models.ForeignKey(
        'modules.WidgetChoice', on_delete=models.CASCADE, related_name='translations', help_text="Parental instance"
    )
    caption = models.CharField(max_length=512, help_text="Text to be rendered with :class:`WidgetChoice`")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, help_text=":class:`Language` of value content")

    @staticmethod
    def get_bxml_serializer():
        from .widget_serializers import WidgetChoiceTranslationBXMLSerializer

        return WidgetChoiceTranslationBXMLSerializer


class WidgetChoice(ChoiceMixin, EryPrivileged):
    """
    Choices in a multiple choice :class:`ModuleDefinitionWidget`.

    Attributes:
        parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.

    Notes:
        - If multiple :class:`WidgetChoiceTranslation` objects exist (differing by :class:`Language`), that of the preferred
          :class:`Language` is priorized during :py:meth:`ModuleDefinitionWidget.get_choices`.

    Each :class:`WidgetChoice` also defines its order (in a set of :class:`WidgetChoice` objects) of rendering.
    """

    class Meta:
        """Meta"""

        ordering = ('order',)
        unique_together = (('widget', 'value'), ('widget', 'order'))
        db_table = 'modules_widgetchoice'

    class SerializerMeta(EryPrivileged.SerializerMeta):
        model_serializer_fields = ('translations',)

    parent_field = 'widget'

    widget = models.ForeignKey(
        'modules.ModuleDefinitionWidget',
        on_delete=models.CASCADE,
        related_name='choices',
        help_text="Parental model instance",
    )
    value = models.CharField(max_length=512)
    order = models.IntegerField(default=0, help_text="Default order of presentation")

    def __str__(self):
        return f"{self.widget}-Choice:{self.order}"

    def clean(self):
        """
        Prevent save when doing so will violate :class:`~ery_backend.variables.models.VariableDefinition` related
        restrictions.

        Specifically:
            - :class:`~ery_backend.variables.models.VariableDefinition` object connected to parental \
                :class:`ModuleDefinitionWidget` must be of DATA_TYPE_CHOICE 'choice' or 'str'.

        Raises:
            :class:`TypeError`: An error occuring if :class:`~ery_backend.users.models.User` attempts
              to create an :class:`WidgetChoice` with a :class:`ModuleDefinitionWidget` whose
              :class:`~ery_backend.variables.models.VariableDefinition` is not of type 'choice' or 'str'.
        """
        # from ery_backend.variables.models import VariableDefinition

        # XXX: Address in issue #813
        # if (
        #     self.widget.variable_definition
        #     and self.widget.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.choice
        # ):
        #     variable_definition_values = self.widget.variable_definition.get_values()
        #     # Any widget choice must be subset of var choice item set
        #     if self.value not in variable_definition_values:
        #         raise ValueError(
        #             f"Value, {self.value}, of WidgetChoice not found in VariableChoiceItem values,"
        #             f" {variable_definition_values}, for widget's VariableDefinition of name,"
        #             f" {self.widget.variable_definition.name}"
        #     )
        if self.value is not None:
            if (
                self.widget.choices.annotate(value_lower=Lower('value'))
                .filter(value_lower=str(self.value).lower())
                .exclude(id=self.id)
                .exists()
            ):
                raise IntegrityError(f"A case-insensitive version of {self.value} already exists in {self.widget} choices")

    # pylint:disable=useless-super-delegation
    # XXX: Remove this method?
    def get_info(self, language):
        """
        Get value and caption of specified :class:`Language`.

        Args:
            language (:class:`Language`): Used to filter :class:`WidgetChoiceTranslation`.

        Returns:
            dict: Contains :class:`WidgetChoice` value and caption from selected :class:`WidgetChoiceTranslation`.

        Notes:
            - If translation matching specified :class:`Language` does not exist, default :class:`Language`
              as specified by parental :class:`~ery_backend.modules.models.ModuleDefinition` is used instead.
        """
        return super().get_info(language)

    def get_translation(self, language):
        """
        Get :class:`WidgetChoiceTranslation` caption specified by given :class:`Language`.

        If :class:`WidgetChoiceTranslation` does not exist for given :class:`Language`, get one
        matching default :class:`Language` of connected :class:`~ery_backend.modules.models.ModuleDefinition`.

        Args:
            language (:class:`Language`): Used to filter :class:`WidgetChoiceTranslation` set.

        Returns:
            str: :class:`WidgetChoiceTranslation` caption.
        """
        return super().get_translation(language)


class WidgetValidationTranslations(EryPrivileged):
    class Meta:
        unique_together = (('widget_validation', 'language'),)

    widget_validation = models.ForeignKey('modules.WidgetValidation', on_delete=models.CASCADE, related_name='translations')
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    error_message = models.CharField(max_length=255, help_text="Error string that will be evaluated with.format(value)")

    def get_error_message(self, value):
        return self.error_message.format(value)


class WidgetValidation(EryPrivileged):
    class Meta:
        ordering = ('order',)

    module_definition_widget = models.ForeignKey(
        'modules.ModuleDefinitionWidget', on_delete=models.CASCADE, related_name='validations'
    )
    validator = models.ForeignKey('validators.Validator', on_delete=models.CASCADE, related_name='validations')
    order = models.PositiveIntegerField()

    def get_error_message(self, language, value):
        try:
            return self.translations.get(language=language).get_error_message()
        except WidgetValidationTranslations.DoesNotExist:
            return self.validator.get_error_message(language, value)


class ModuleEventStep(EventStepModel):
    """
    Define specific circumstances during which an :class:`~ery_backend.actions.models.Action` should be run.

    Attributes:
        - parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.
    """

    parent_field = 'module_event'

    EVENT_ACTION_TYPE_CHOICES = Choices(
        ('back', _('Back')), ('run_action', _('Run Action')), ('save_var', _('Save Variable')), ('submit', _('Submit')),
    )

    REQUIRE_COMMUNCIATE_ACTION_TYPES = ('back', 'save_var', 'submit')

    module_event = models.ForeignKey(
        'modules.ModuleEvent', on_delete=models.CASCADE, related_name='steps', help_text="Parental instance"
    )

    action = models.ForeignKey(
        'actions.Action',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Run upon triggering of specified Javascript event",
    )

    event_action_type = models.CharField(max_length=14, choices=EVENT_ACTION_TYPE_CHOICES)

    # XXX: Address in issue #813
    # def clean(self):
    #     super().clean()
    #     if (
    #         self.event_action_type == self.EVENT_ACTION_TYPE_CHOICES.save_var
    #         and not self.module_event.widget.variable_definition
    #     ):
    #         raise ValidationError(
    #             {
    #                 'variable_definition': "VariableDefinition required on parental widget for"
    #                 f" save_var action for widget {self.module_event.widget}"
    #             }
    #         )
    #     if self.event_action_type == self.EVENT_ACTION_TYPE_CHOICES.run_action and not self.action:
    #         raise ValidationError(
    #             {'action': f"Action required for 'run_action' action for widget: {self.module_event.widget}"}
    #         )


class ModuleEvent(EventModel):
    """
    Define specific circumstances during which an :class:`~ery_backend.actions.models.Action` should be run.

    Attributes:
        - REACT_EVENT_CHOICES: Possible React events that can trigger associated actions (from :class:`EventModel`).
        - SMS_EVENT_CHOICES: Possible SMS events that can trigger associated actions (from :class:`EventModel`).
        - parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.
    """

    class Meta:
        unique_together = ('widget', 'event_type', 'name')

    class SerializerMeta(EventModel.SerializerMeta):
        model_serializer_fields = ('steps',)

    parent_field = 'widget'

    widget = models.ForeignKey(
        'modules.ModuleDefinitionWidget', on_delete=models.CASCADE, related_name='events', help_text="Parental instance"
    )

    @staticmethod
    def get_bxml_serializer():
        from .widget_serializers import ModuleEventBXMLSerializer

        return ModuleEventBXMLSerializer

    @staticmethod
    def get_duplication_serializer():
        from .widget_serializers import ModuleEventDuplicationSerializer

        return ModuleEventDuplicationSerializer

    # XXX: Needs to accept team in issue #458
    def trigger(self, hand, value=None):
        """
        Signal event to execute associated action, as determined by event_type attribute.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context (if required)
              during execution of associated action.
        """
        socket_message_args = []

        for step in self.steps.all():
            if step.event_action_type == step.EVENT_ACTION_TYPE_CHOICES.save_var:
                variable, changed = hand.stint.set_variable(self.widget.variable_definition, value, hand=hand)
                if changed:
                    socket_message_args.append(variable)
            elif step.event_action_type == step.EVENT_ACTION_TYPE_CHOICES.run_action:
                socket_message_args += step.action.run(hand)
            elif step.event_action_type == step.EVENT_ACTION_TYPE_CHOICES.back:
                socket_message_args += hand.back()
            elif step.event_action_type == step.EVENT_ACTION_TYPE_CHOICES.submit:
                socket_message_args += hand.submit()
        return socket_message_args


# Does not use ModuleDefinitionNamedModel to avoid circular imports
class ModuleDefinitionWidget(ChoiceHolderMixin, ReactNamedMixin, EryNamedPrivileged):
    """
    Link :class:`~ery_backend.widgets.models.Widget` to :class:`~ery_backend.modules.models.ModuleDefinition.`

    Additionally:
        - Adds :class:`ModuleDefinition` specific aspects of the :class:`Widget` instance's fields.
        - Adds a :class:`ModuleDefinition` specific identifier (i.e., name) for :class:`Widget` instance.

    Attributes:
        RANDOM_CHOICES: Randomization options applied during presentation.

    Notes:
        - Connected :class:`~ery_backend.actions.models.Action` instances executed on triggering of any connected
          :class:`ModuleEvent`.
        - :class:`~ery_backend.users.models.User` entered values are saved to connected variable
          (:class:`~ery_backend.variables.models.HandVariable`, :class:`~ery_backend.variables.models.TeamVariable`, etc)
          defined by the scope of the connected :class:`~ery_backend.variables.models.VariableDefinition`.
        - Assumed to be multiple choice field if related :class:`WidgetChoice` exist(s).
          This requires that the connected :class:`~ery_backend.variables.models.VariableDefinition` either has data_type
          set to 'string' or 'choice'. In the latter case, each :class:`WidgetChoice` value must be a subset of the set of
          :class:`~ery_backend.variables.models.VariableChoiceItem` values.
    """

    class Meta:
        unique_together = ("name", "module_definition")
        db_table = 'modules_moduledefinitionwidget'

    class SerializerMeta(EryNamedPrivileged.SerializerMeta):
        model_serializer_fields = ('choices', 'events')

    parent_field = 'module_definition'

    module_definition = models.ForeignKey(
        'modules.ModuleDefinition',
        on_delete=models.CASCADE,
        help_text="Parent :class:`~ery_backend.modules.models.ModuleDefinition`",
        related_name='module_widgets',
    )
    form_field = models.OneToOneField(
        'forms.FormField',
        null=True,
        on_delete=models.CASCADE,
        help_text="If ModuleDefinitionWidget is part of a Form, this is the FormField it belongs to.",
        related_name="module_definition_widget",
    )

    required_widget = models.BooleanField(
        default=False,
        help_text="ModuleDefinitionWidget required to proceed to next" " :class:`~ery_backend.stages.models.Stage`",
    )
    initial_value = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text="Value displayed in :class:`ModuleDefinitionWidget` immediately on render",
    )
    random_mode = models.CharField(
        max_length=50,
        choices=ChoiceHolderMixin.RANDOM_CHOICES,
        default='asc',
        help_text="Randomization option applied during presentation",
    )
    widget = models.ForeignKey(
        'widgets.Widget',
        default=9,
        on_delete=models.SET_DEFAULT,
        related_name='module_widgets',
        help_text="Javascript model used to render content of :class:`ModuleDefinitionWidget`",
    )
    variable_definition = models.ForeignKey(
        'variables.VariableDefinition',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='widgets',
        help_text="Model used to store user input captured via model instance",
    )

    @property
    def json_initial_value(self):
        if self.initial_value is not None and self.initial_value != '':
            return json.dumps(self.initial_value)
        return None

    @staticmethod
    def get_bxml_serializer():
        """
        Get serializer class.
        """
        from .serializers import ModuleDefinitionWidgetBXMLSerializer

        return ModuleDefinitionWidgetBXMLSerializer

    @staticmethod
    def get_duplication_serializer():
        """
        Get serializer class.
        """
        from .serializers import ModuleDefinitionWidgetDuplicationSerializer

        return ModuleDefinitionWidgetDuplicationSerializer

    @staticmethod
    def get_mutation_serializer():
        """
        Get serializer class.
        """
        from .serializers import ModuleDefinitionWidgetMutationSerializer

        return ModuleDefinitionWidgetMutationSerializer

    def get_choices(self, language=None):
        # pylint: disable=too-many-branches
        """
        Get set of :class:`WidgetChoice` object information.

        Returns:
            list: Consists of dicts representing :class:`WidgetChoice` value and
            :class:`Language` specific caption.

        Notes:
            - If no :class:`Language` is specified, the default of the connected
              :class:`~ery_backend.modules.models.ModuleDefinition` is used.
            - Because :class:`~ery_backend.variables.models.VariableChoiceItem` instances have no order,
              id is used in place of order if no :class:`WidgetChoice` items exist.
        """
        from ery_backend.variables.models import VariableChoiceItem

        if not self.is_multiple_choice:
            raise TypeError(
                f"Cannot run get_choices on widget with name, {self.name}, as this widget does not pass"
                " is_multiple_choice check"
            )

        if not language:
            language = self.module_definition.primary_language

        if self.choices.all():
            choices = self.choices
            choice_model = WidgetChoice
        else:
            choices = self.variable_definition.variablechoiceitem_set
            choice_model = VariableChoiceItem

        if choices:
            if self.random_mode == self.RANDOM_CHOICES.asc:
                output = choices.all()
            elif self.random_mode == self.RANDOM_CHOICES.desc:
                if choice_model == WidgetChoice:
                    output = choices.order_by('-order').all()
                else:
                    output = choices.order_by('-id').all()
            elif self.random_mode == self.RANDOM_CHOICES.shuffle:
                output = choices.order_by('?').all()

            if self.random_mode == self.RANDOM_CHOICES.random_asc_desc:
                rand_choices = ['order', '-order'] if choice_model == WidgetChoice else ['id', '-id']
                order_mode = random.choice(rand_choices)
                output = choices.order_by(order_mode).all()

            return [widget_choice.get_info(language) for widget_choice in list(output)]
        return None

    def trigger_events(self, name, event_type, hand, **kwargs):
        """
        Executes all connected event objects.

        Args:
            - event (str): JavaScript event.
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context during execution.

        Notes:
            - All websocket targeted messages returned from events are queued and delivered in one message after all relevant
              :class:`ModuleEvent` and :class:`~ery_backend.widgets.models.WidgetEvent` instances have been triggered for
              :class:`~ery_backend.hands.models.Hand` instance with a Web
              :class:`~ery_backend.frontends.models.Frontend`.
        """
        socket_message_args = []
        event_objs = self.events.filter(name=name, event_type=event_type)
        for event_obj in event_objs.all():
            if kwargs.get('value') is not None or self.widget.save_null:
                new_socket_message_args = event_obj.trigger(hand, **kwargs)
                if new_socket_message_args:
                    socket_message_args += new_socket_message_args

        for widget_event_obj in self.widget.events.filter(name=name, event_type=event_type).all():
            new_socket_message_args = widget_event_obj.trigger(hand)
            if new_socket_message_args:
                socket_message_args += new_socket_message_args

        return socket_message_args

    def get_events_info(self):
        events_info = []
        for event in self.events.all():
            do_communicate = (
                event.steps.exists()
                and not self.widget.events.filter(
                    steps__event_action_type__in=ModuleEventStep.REQUIRE_COMMUNCIATE_ACTION_TYPES
                ).exists()
            )
            events_info.append((event.name or '', event.event_type, do_communicate))

        return events_info
