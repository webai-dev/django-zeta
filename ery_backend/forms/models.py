import random

from django.contrib.postgres.fields import JSONField
from django.db import models, IntegrityError
from django.db.models.functions import Lower

from languages_plus.models import Language
from model_utils import Choices

from ery_backend.base.mixins import ChoiceMixin, ChoiceHolderMixin, PrivilegedMixin, ReactNamedMixin, SluggedMixin
from ery_backend.base.models import EryNamedPrivileged, EryNamedSlugged, EryPrivileged
from ery_backend.modules.models import ModuleDefinitionNamedModel, ModuleDefinitionWidget


class Form(SluggedMixin, ReactNamedMixin, ModuleDefinitionNamedModel):
    class SerializerMeta(ModuleDefinitionNamedModel.SerializerMeta):
        model_serializer_fields = ('items',)

    FORM_EVENT_CHOICES = Choices(('onSubmit', 'On Submit'),)
    parent_field = 'module_definition'

    module_definition = models.ForeignKey(
        'modules.ModuleDefinition',
        on_delete=models.CASCADE,
        related_name='forms',
        help_text="The module definition this Form belongs to",
    )

    def get_module_widgets(self):
        return [item.field.get_module_widget() for item in self.items.exclude(field=None)]

    def get_widgets(self):
        ret = set()

        for module_widget in self.get_module_widgets():
            ret.update({module_widget.widget,}.union(module_widget.widget.get_all_connected_widgets()))

        for button_list_item in self.items.exclude(button_list=None):
            ret.update({button.widget for button in button_list_item.button_list.buttons.all()})

        return ret

    def render_web(self, language):
        from ery_backend.frontends.renderers import ReactFormRenderer

        return ReactFormRenderer(self, language).render()

    def save_data(self, hand, form_data):
        """
        Update variable values of relevant :class:`FormField` objects.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`)
            - form_data (Dict[str, Union[str, int, float, List, Dict]]]):
              :class:`FormField` name, value.
        """
        socket_message_args = []
        if not isinstance(form_data, dict):
            raise TypeError("form_data must be a dictionary")
        for full_field_name, value in form_data.items():
            field_name = full_field_name.split('-')[-1]
            variable_definition = self.items.get(field__name=field_name).field.variable_definition
            variable, changed = hand.stint.set_variable(variable_definition, value, hand=hand)
            if changed:
                socket_message_args.append(variable)
        return socket_message_args


class FormItem(EryPrivileged):
    class Meta(EryPrivileged.Meta):
        ordering = ('order', 'tab_order')
        unique_together = (('form', 'tab_order'),)

    class SerializerMeta(EryPrivileged.SerializerMeta):
        model_serializer_fields = ('field', 'button_list')

    parent_field = 'form'

    form = models.ForeignKey('forms.Form', on_delete=models.CASCADE, related_name='items')
    # Has reverse OneToOneFields called form_item and button_list

    order = models.PositiveIntegerField()
    tab_order = models.PositiveIntegerField()


class FormField(ReactNamedMixin, ChoiceHolderMixin, PrivilegedMixin, EryNamedSlugged):
    """
    Notes:
        - A one to one exists between :class:`FormField` and parental :class:`FormItem`.
    """

    # class Meta(EryNamedSlugged.Meta):
    #     constraints = [
    #         models.UniqueConstraint(fields=['name', 'form_item__form'], name='unique_form_field')
    #     ]

    class SerializerMeta(EryNamedPrivileged.SerializerMeta):
        model_serializer_fields = ('choices',)

    parent_field = 'form_item'
    slug_separator = ''

    form_item = models.OneToOneField('forms.FormItem', on_delete=models.CASCADE, blank=True, null=True, related_name='field')
    validator = models.ForeignKey(
        'validators.Validator', on_delete=models.PROTECT, blank=True, null=True, related_name='form_fields'
    )
    variable_definition = models.ForeignKey(
        'variables.VariableDefinition', on_delete=models.CASCADE, related_name='form_fields'
    )
    widget = models.ForeignKey('widgets.Widget', on_delete=models.CASCADE)

    # rename to disable_on
    disable = models.ForeignKey('conditions.Condition', on_delete=models.SET_NULL, blank=True, null=True)
    initial_value = JSONField(null=True, blank=True)
    helper_text = models.TextField()
    random_mode = models.CharField(
        max_length=50,
        choices=ChoiceHolderMixin.RANDOM_CHOICES,
        default='asc',
        help_text="Randomization option applied during presentation",
    )
    required = models.BooleanField(default=False)

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
            choice_model = FormFieldChoice
        else:
            choices = self.variable_definition.variablechoiceitem_set
            choice_model = VariableChoiceItem

        if choices:
            if self.random_mode == self.RANDOM_CHOICES.asc:
                output = choices.all()
            elif self.random_mode == self.RANDOM_CHOICES.desc:
                if choice_model == FormFieldChoice:
                    output = choices.order_by('-order').all()
                else:
                    output = choices.order_by('-id').all()
            elif self.random_mode == self.RANDOM_CHOICES.shuffle:
                output = choices.order_by('?').all()

            if self.random_mode == self.RANDOM_CHOICES.random_asc_desc:
                rand_choices = ['order', '-order'] if choice_model == FormFieldChoice else ['id', '-id']
                order_mode = random.choice(rand_choices)
                output = choices.order_by(order_mode).all()

            return [widget_choice.get_info(language) for widget_choice in list(output)]
        return None

    def get_initial_value(self):
        import json

        return json.dumps(self.initial_value)

    def get_module_widget(self):
        try:
            return self.module_definition_widget
        except FormField.module_definition_widget.RelatedObjectDoesNotExist:
            return ModuleDefinitionWidget.objects.create(
                module_definition=self.form_item.form.module_definition,
                form_field=self,
                name=f"FormField{self.form_item.form.name}{self.slug}",
                variable_definition=self.variable_definition,
                widget=self.widget,
            )


class FormButtonList(EryNamedPrivileged):
    # class Meta(EryNamedPrivileged.Meta):
    #     constraints = [
    #         models.UniqueConstraint(fields=['name', 'form_item__form'], name='unique_form_field')
    #     ]

    class SerializerMeta(EryNamedPrivileged.SerializerMeta):
        model_serializer_fields = ('buttons',)

    parent_field = 'form_item'

    form_item = models.OneToOneField(
        'forms.FormItem', on_delete=models.CASCADE, blank=True, null=True, related_name='button_list'
    )


class FormButton(ReactNamedMixin, EryNamedPrivileged):
    class Meta(EryNamedPrivileged.Meta):
        unique_together = (('name', 'button_list'),)

    parent_field = 'button_list'

    button_text = models.CharField(max_length=24)
    button_list = models.ForeignKey('forms.FormButtonList', on_delete=models.CASCADE, related_name='buttons')
    widget = models.ForeignKey('widgets.Widget', on_delete=models.CASCADE)

    submit = models.BooleanField(default=False)
    disable = models.ForeignKey('conditions.Condition', on_delete=models.SET_NULL, blank=True, null=True, related_name='+')
    hide = models.ForeignKey('conditions.Condition', on_delete=models.SET_NULL, blank=True, null=True, related_name='++')

    def trigger_events(self, name, event_type, hand, **kwargs):
        """
        Executes all connected event objects.

        Args:
            - event_type (str): React event.
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context during execution.

        Notes:
            - All websocket targeted messages returned from events are queued and delivered in one message after all relevant
              :class:`~ery_backend.widgets.models.WidgetEvent` instances have been triggered.

        """
        socket_message_args = []
        for widget_event_obj in self.widget.events.filter(name=name, event_type=event_type).all():
            new_socket_message_args = widget_event_obj.trigger(hand)
            if new_socket_message_args:
                socket_message_args += new_socket_message_args

        return socket_message_args


class FormFieldChoice(ChoiceMixin, EryPrivileged):
    """
    Choices in a multiple choice :class:`FormField`.

    Attributes:
        parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.

    Notes:
        - If multiple :class:`FormFieldChoiceTranslation` objects exist (differing by :class:`Language`), that of the preferred
          :class:`Language` is priorized during :py:meth:`FormField.get_choices`.

    Each :class:`FormFieldChoice` also defines its order (in a set of :class:`FormFieldChoice` objects) of rendering.
    """

    class Meta(EryPrivileged.Meta):
        ordering = ('order',)
        unique_together = (
            ('field', 'value'),
            ('field', 'order'),
        )

    class SerializerMeta(EryPrivileged.SerializerMeta):
        model_serializer_fields = ('translations',)

    parent_field = 'field'

    field = models.ForeignKey(
        'forms.FormField', on_delete=models.CASCADE, related_name='choices', help_text="Parental model instance",
    )
    value = models.CharField(max_length=512)
    order = models.IntegerField(default=0, help_text="Default order of presentation")

    def __str__(self):
        return f"{self.field}-Choice:{self.order}"

    def clean(self):
        """
        Prevent save when doing so will violate :class:`~ery_backend.variables.models.VariableDefinition` related
        restrictions.

        Specifically:
            - :class:`~ery_backend.variables.models.VariableDefinition` object connected to parental \
                :class:`FormField` must be of DATA_TYPE_CHOICE 'choice' or 'str'.

        Raises:
            :class:`TypeError`: An error occuring if :class:`~ery_backend.users.models.User` attempts
              to create an :class:`FormFieldChoice` with a :class:`FormField` whose
              :class:`~ery_backend.variables.models.VariableDefinition` is not of type 'choice' or 'str'.
        """
        from ery_backend.variables.models import VariableDefinition

        if (
            self.field.variable_definition
            and self.field.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.choice
        ):
            variable_definition_values = self.field.variable_definition.get_values()
            # Any widget choice must be subset of var choice item set
            if self.value not in variable_definition_values:
                raise ValueError(
                    f"Value, {self.value}, of FormFieldChoice not found in VariableChoiceItem values,"
                    f" {variable_definition_values}, for field's VariableDefinition of name,"
                    f" {self.field.variable_definition.name}"
                )
        if self.value is not None:
            if (
                self.field.choices.annotate(value_lower=Lower('value'))
                .filter(value_lower=str(self.value).lower())
                .exclude(id=self.id)
                .exists()
            ):
                raise IntegrityError(f"A case-insensitive version of {self.value} already exists in {self.field} choices")

    # pylint:disable=useless-super-delegation
    # XXX: Remove this method?
    def get_info(self, language):
        """
        Get value and caption of specified :class:`Language`.

        Args:
            language (:class:`Language`): Used to filter :class:`FormFieldChoiceTranslation`.

        Returns:
            dict: Contains :class:`FormFieldChoice` value and caption from selected :class:`FormFieldChoiceTranslation`.

        Notes:
            - If translation matching specified :class:`Language` does not exist, default :class:`Language`
              as specified by parental :class:`~ery_backend.fields.models.Field` is used instead.
        """
        return super().get_info(language)

    def get_translation(self, language):
        """
        Get :class:`FormFieldChoiceTranslation` caption specified by given :class:`Language`.

        If :class:`FormFieldChoiceTranslation` does not exist for given :class:`Language`, get one
        matching default :class:`Language` of connected :class:`~ery_backend.modules.models.ModuleDefinition`.

        Args:
            language (:class:`Language`): Used to filter :class:`FormFieldChoiceTranslation` set.

        Returns:
            str: :class:`FormFieldChoiceTranslation` caption.
        """
        return super().get_translation(language)


class FormFieldChoiceTranslation(EryPrivileged):
    """
    Units of :class:`FormFieldChoice` describing the :class:`Language` for rendering content.
    """

    class Meta(EryPrivileged.Meta):
        unique_together = (('field_choice', 'language',),)

    parent_field = 'field_choice'

    field_choice = models.ForeignKey(
        'forms.FormFieldChoice', on_delete=models.CASCADE, related_name='translations', help_text="Parental instance"
    )
    caption = models.CharField(max_length=512, help_text="Text to be rendered with :class:`WidgetChoice`")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, help_text=":class:`Language` of value content")
