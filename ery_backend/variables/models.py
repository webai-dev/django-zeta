from enum import Enum
import json

from django.db import models, IntegrityError
from django.db.models.functions import Lower

from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField

from languages_plus.models import Language
from model_utils import Choices
import reversion
import fastnumbers

from ery_backend.base.mixins import ChoiceMixin, SluggedMixin, JavascriptNamedMixin
from ery_backend.base.models import EryPrivileged
from ery_backend.base.exceptions import EryValueError, EryTypeError, EryValidationError
from ery_backend.base.utils import get_default_language
from ery_backend.modules.models import ModuleDefinitionNamedModel


class ScopeChoices(Enum):
    hand = 'Hand-wide'
    team = 'Team-wide'
    module = 'Module-wide'


@reversion.register()
class VariableDefinition(ModuleDefinitionNamedModel, JavascriptNamedMixin, SluggedMixin):
    """
    VariableDefinitions describe how to instantiate typed variables (see DATA_TYPE_CHOICES) at the level of Hand, Team, Module,
        and Stint (through the use of Scope).

    A Validator (required) is used to confirm the integrity of a Variable value before instatiating said variable.

    VariableDefinitions can flagged as configurable, pay-off related, or relevant to a Module's output data, and can
    specify a default value for Variable instantiation.

    VariableDefinitions can also limited the values of their instantiated forms through the use of VariableChoiceItems.

    XXX: Address in issue #465. As expressed in 2/15/18 meeting, we may want to remove validator usage on VariableDefinition,
         since it only seems relevant for debugging, and may prove cumbersome.

    Parent: Module Definition
    Children: HandVariable, TeamVariable, ModuleVariable

    Note: A slug is required during stintspecification import/duplication in order to lookup and connect
        variabledefinition without having corresponding module definition available.
    """

    class SerializerMeta(ModuleDefinitionNamedModel.SerializerMeta):
        model_serializer_fields = ('variablechoiceitem_set',)

    parent_field = 'module_definition'

    SCOPE_CHOICES = Choices(('hand', "Hand-wide"), ('team', "Team-wide"), ('module', "Module-wide"))
    DATA_TYPE_CHOICES = Choices(
        ('int', "Integer"),
        ('float', "Real number"),
        ('choice', "Choice"),
        ('str', "String"),
        ('list', "List"),
        ('dict', "Dictionary"),
        ('bool', "Boolean"),
        ('stage', "Stage"),
    )

    scope = models.CharField(choices=SCOPE_CHOICES, default=SCOPE_CHOICES.hand, max_length=255)
    data_type = models.CharField(choices=DATA_TYPE_CHOICES, default=DATA_TYPE_CHOICES.int, max_length=255)
    validator = models.ForeignKey('validators.Validator', on_delete=models.SET_NULL, null=True, blank=True)
    default_value = JSONField(null=True, blank=True)
    specifiable = models.BooleanField(default=False)
    is_payoff = models.BooleanField(default=False)
    is_output_data = models.BooleanField(default=False)
    monitored = models.BooleanField(
        default=False,
        help_text="Determine whether adminstrative :class:`~ery_backend.users.models.User` may view the value of the given"
        " instance.",
    )

    @staticmethod
    def get_bxml_serializer():
        from .serializers import VariableDefinitionBXMLSerializer

        return VariableDefinitionBXMLSerializer

    @staticmethod
    def get_duplication_serializer():
        from .serializers import VariableDefinitionDuplicationSerializer

        return VariableDefinitionDuplicationSerializer

    def get_values(self):
        return [variablechoiceitem.value for variablechoiceitem in self.variablechoiceitem_set.all()]

    @classmethod
    def get_variable_cls_from_scope(cls, scope):
        """
        Returns :class:`VariableMixin` child based on given scope.

        Args:
            - scope (str)

        Returns:
            Union[:class:`HandVariable`, :class:`TeamVariable`, :class:`ModuleVariable`]
        """
        if scope == cls.SCOPE_CHOICES.hand:
            return HandVariable
        if scope == cls.SCOPE_CHOICES.team:
            return TeamVariable
        if scope == cls.SCOPE_CHOICES.module:
            return ModuleVariable
        raise Exception(f"No variable cls exists for scope: {scope}")

    def _raise_type_error(self, value):
        raise EryTypeError(
            f"Value: \'{value}\', is of the wrong type. Values of variables associated with Variable"
            f" Definition: {self.name}, must be of type: {self.data_type}."
        )

    def _validate_choice_items(self):
        if self.data_type == self.DATA_TYPE_CHOICES.choice:
            choice_values = self.get_values()
            # XXX: Address in issue #813
            # if self.default_value is not None and self.default_value not in choice_values:
            #     if not choice_values:
            #         raise EryValueError(
            #             "Variable Choice Items are required to set a default_value for a "
            #             "variable_definition "
            #             "of data type: choice"
            #         )
            #     raise EryValueError(
            #         "Desired default value, {}, is not present in variable_definition choice"
            #         " items {}".format(self.default_value, choice_values)
            #     )
            # confirms no widget choice is invalidated by change to choice type
            for widget in self.widgets.all():
                widget.clean()
        else:
            if self.variablechoiceitem_set.exists():
                raise EryValidationError(
                    f"Cannot change data_type of VariableDefinition: {self.name} while connected" " VariableChoiceItems exist."
                )

    def _validate_choices(self, value):
        if value is not None and self.data_type == VariableDefinition.DATA_TYPE_CHOICES.choice:
            choice_values = self.get_values()
            if isinstance(value, str):
                choice_value = value.lower()
            else:
                choice_value = str(value)
            if choice_value not in choice_values:
                raise EryValueError(
                    "To save a variable instance with variable_definition of data type ,"
                    "'choice', the variable instance's value must match that of a "
                    "corresponding variable_definition choice item value. The desired value, {}, is not "
                    "present in variable_definition choice item values {}".format(value, choice_values)
                )

    def _validate_payoff(self):
        if self.is_payoff:
            if self.scope != self.SCOPE_CHOICES.hand:
                raise ValueError(
                    f"Scope must be '{self.SCOPE_CHOICES.hand}' if is_payoff == True for VariableDefinition: {self}"
                )
            if self.data_type != self.DATA_TYPE_CHOICES.float:
                raise TypeError(
                    f"Data type must be '{self.DATA_TYPE_CHOICES.float}' if is_payoff == True for VariableDefinition: {self}"
                )

    def clean(self):
        """
        Prevents save when doing so will violate data type, matching restrictions, or js_naming constrictions.

        Specifically:
            - If js_reserved_patten attribute is not None, name of model instance must match designated pattern.
            - Default value, if any, must be of type specified by data_type of attribute of model instance.
            - If default value, and data_type of model instance is choice, default value must be part of subset of
              :class:`VariableChoiceItem` values.
            - If connected :class:`~ery_backend.modules.models.ModuleDefinitionWidget`, data_type attribute must be
              str or choice.
            - If connected :class:`VariableChoiceItem`, data type attribute must be choice.

        Raise:
            ~ery_backend.base.exceptions.EryValueError: An error occuring if default_value restrictions are violated.
            ~ery_backend.base.exceptions.EryValidationError: An error occuring if related model restrictions are violated.
            ~ery_backend.base.exceptions.EryTypeError: An error occuring if data_type restrictions are violated.
        """
        # pylint: disable=too-many-branches
        super().clean()
        if self.default_value:
            self.default_value = self.cast(self.default_value)
            # XXX: This is muted to prevent crashes from validator due to invalid client-side data
            # self.validate(self.default_value)
        self._validate_choice_items()
        # Run so we have correct data_type in _validate_payoff during deserialization
        self.is_payoff = str(self.is_payoff).lower() in ['true', '1']
        self._validate_payoff()
        if self.data_type != self.DATA_TYPE_CHOICES.choice:
            if self.variablechoiceitem_set.exists():
                raise EryValidationError(
                    f"Cannot change data_type of VariableDefinition: {self.name} while connected" " VariableChoiceItems exist."
                )
        if self.data_type in [self.DATA_TYPE_CHOICES.stage]:
            if self.widgets.exists():
                raise EryValidationError(
                    f"Cannot change data_type of VariableDefinition: {self.name} to"
                    f" '{self.DATA_TYPE_CHOICES.stage}' while connected ModuleDefinitionWidgets exist."
                )
            if self.data_type == self.DATA_TYPE_CHOICES.stage:
                if self.default_value:
                    if not self.module_definition.has_stage(self.default_value):
                        raise ValueError(f"No stage found with name: {self.default_value}, for {self.module_definition}.")
        else:
            # confirms no widget choice is invalidated by change to choice type
            # confirms no module_definition_widget accesses variable definition of type choice until it is ready
            for widget in self.widgets.all():
                widget.clean()
            for form_field in self.form_fields.all():
                form_field.clean()

    # pylint:disable=R0912
    def cast(self, value):
        """
        Typecast given value based on current :class:`VariableDefinition` instance's data type.

        Args:
            value (Union[int, float, str, bool, List, Dict]): Initially typed value.

        Returns:
            Union[int, float, str, bool, List, Dict]: Correctly typed value.

        Raises:
            ValueError: Raised if given initial value cannot be typecasted to the intended value of the \
              current :class:`VariableDefinition` instance's data type.
        """
        if self.data_type == self.DATA_TYPE_CHOICES.int:  # pylint:disable=no-else-return
            if not (fastnumbers.isintlike(value) or isinstance(value, bool)):
                raise ValueError(f"An integer must be submitted for variable with definition: {self}. Not {value}.")
            return fastnumbers.fast_int(value, raise_on_invalid=True)
        elif self.data_type == self.DATA_TYPE_CHOICES.float:
            return fastnumbers.fast_real(value, raise_on_invalid=True)
        elif self.data_type == self.DATA_TYPE_CHOICES.str:
            return str(value)
        elif self.data_type == self.DATA_TYPE_CHOICES.bool:
            converted_value = str(value).lower()
            # case insensitive due to deserialization requirements.
            if converted_value not in ['true', 'false', '0', '1', '0.0', '1.0']:
                raise ValueError(
                    "Either 'true', 1, '1', 'false', 0, or '0' must be submitted as boolean values "
                    f" for variable with definition: {self}."
                )
            return converted_value in ['true', '1', '1.0']
        elif self.data_type == self.DATA_TYPE_CHOICES.list:
            if not isinstance(value, list):
                error_message = f"A list must be submitted for variable with definition: {self}"
                try:
                    loaded_value = json.loads(value)  # lists may be returned as json from frontend
                    assert isinstance(loaded_value, list)
                except TypeError:
                    raise ValueError(error_message)
                except AssertionError:
                    raise ValueError(error_message)
        elif self.data_type == self.DATA_TYPE_CHOICES.dict:
            if not isinstance(value, dict):
                error_message = f"A dict must be submitted for variable with definition: {self}"
                try:
                    loaded_value = json.loads(value)  # dicts should be returned as json from frontend
                    assert isinstance(loaded_value, dict)
                except TypeError:
                    raise ValueError(error_message)
                except AssertionError:
                    raise ValueError(error_message)
        return value

    def realize(self, module=None, teams=None, hands=None, stint_definition_variable_definition=None, value=None):
        # pylint:disable=line-too-long
        """
        Create variable for use in :class:`~ery_backend.modules.models.Module` during
        :py:meth:`~ery_backend.stints.models.Stint.start`.

        Args:
            - module (:class:`~ery_backend.modules.models.Module`): Assign parent during realization of variables.
            - teams (Optional[List[:class:`~ery_backend.teams.models.Team`]]): Realize variables of
              :class:`~ery_backend.teams.models.Team` scope.
            - hands (Optional[List[:class:`~ery_backend.hands.models.Hand`]]): Realize variables of
              :class:`~ery_backend.hands.models.Hand` scope.
            - stint_definition_variable_definition (Optional[:class:`~ery_backend.stints.models.StintDefinitionVariableDefinition`]):
              Set variable stint_definition_variable_definition instead of variable variable_definition.
            - value (Optional[Union[int, float, List, Dict, Tuple]]): Use in place of :class:`VariableDefinition`
              default_value to set value.

        Notes:
            - If value is None, the default_value of the variable's connected :class:`VarialeDefinition`
              (the first by :class:`~ery_backend.stints.models.StintDefinitionModuleDefinition` order if more than one),
              is used instead.
        """
        if self.scope == self.SCOPE_CHOICES.module and not module:
            raise EryValidationError(f'Module required to realize {self}.')
        if self.scope in [self.SCOPE_CHOICES.team] and not teams:
            raise EryValidationError(f'List of teams required to realize {self}.')
        if self.scope in [self.SCOPE_CHOICES.hand] and not hands:
            raise EryValidationError(f'List of hands required to realize {self}.')

        if hands and not module:
            module = hands[0].current_module

        if stint_definition_variable_definition is None:
            vd = self
        else:
            vd = None

        if self.scope == self.SCOPE_CHOICES.module:
            ModuleVariable.objects.create(
                module=module,
                variable_definition=vd,
                stint_definition_variable_definition=stint_definition_variable_definition,
                value=value,
            )
        elif self.scope == self.SCOPE_CHOICES.team:
            for team in teams:
                TeamVariable.objects.create(
                    team=team,
                    variable_definition=vd,
                    module=module,
                    stint_definition_variable_definition=stint_definition_variable_definition,
                    value=value,
                )
        else:
            for hand in hands:
                HandVariable.objects.create(
                    hand=hand,
                    variable_definition=vd,
                    module=module,
                    stint_definition_variable_definition=stint_definition_variable_definition,
                    value=value,
                )

    def validate(self, value):
        if value is not None:
            self._validate_choices(value)
        if self.validator is not None:
            self.validator.validate(value, self)

    def get_random_value(self):
        pass


class VariableChoiceItemTranslation(EryPrivileged):
    """
    Units of :class:`VariableChoiceItem` describing the :class:`Language` for rendering content.
    """

    class Meta(EryPrivileged.Meta):
        unique_together = (('variable_choice_item', 'language',),)

    @staticmethod
    def get_bxml_serializer():
        from .serializers import VariableChoiceItemTranslationBXMLSerializer

        return VariableChoiceItemTranslationBXMLSerializer

    @staticmethod
    def get_duplication_serializer():
        from .serializers import VariableChoiceItemTranslationDuplicationSerializer

        return VariableChoiceItemTranslationDuplicationSerializer

    parent_field = 'variable_choice_item'
    variable_choice_item = models.ForeignKey(
        'variables.VariableChoiceItem', on_delete=models.CASCADE, help_text="Parental instance", related_name='translations'
    )
    caption = models.CharField(max_length=512, help_text="Text to be rendered with :class:`VariableChoiceItem`")
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_DEFAULT,
        default=get_default_language(pk='en'),
        help_text=":class:`Language` of value content",
    )


@reversion.register()
class VariableChoiceItem(ChoiceMixin, EryPrivileged):
    """VariableChoiceItems are used to limit."""

    class Meta(EryPrivileged.Meta):
        unique_together = (('variable_definition', 'value'),)

    class SerializerMeta(EryPrivileged.SerializerMeta):
        model_serializer_fields = ('translations',)

    parent_field = 'variable_definition'
    variable_definition = models.ForeignKey('variables.VariableDefinition', on_delete=models.CASCADE)
    value = models.CharField(max_length=255, blank=True)

    # XXX: What reason do we have for disallowing the user to have different case variations?
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = self.value.lower()

    def clean(self):
        """
        Prevents save when doing so will violate :class:`~ery_backend.variables.models.VariableDefinition` related
        restrictions.

        Specifically:
            * Parental :class:`~ery_backend.variables.models.VariableDefinition` must be of DATA_TYPE_CHOICE 'choice'.

        Raise:
            ~ery_backend.base.exceptions.EryValidationError: An error occuring if restrictions are violated.
        """
        if self.variable_definition.data_type != VariableDefinition.DATA_TYPE_CHOICES.choice:
            raise EryValidationError(
                f"Cannot connect VariableChoiceItem with value {self.value} to a VariableDefinition"
                f" that is not of data_type {VariableDefinition.DATA_TYPE_CHOICES.choice}."
            )
        if self.value is not None:
            if (
                self.variable_definition.variablechoiceitem_set.annotate(value_lower=Lower('value'))
                .filter(value_lower=self.value.lower())
                .exclude(id=self.id)
                .exists()
            ):
                raise IntegrityError(
                    f"A case-insensitive version of {self.value} already exists in" f"{self.variable_definition} choices"
                )

    def delete(self, **kwargs):
        """
        Prevents delete when doing so will violate :class:`~ery_backend.modules.models.WidgetChoice` restrictions.

        Specifically:
            * If :class:`~ery_backend.modules.models.WidgetChoice` depends on value of model instance for validity, cannot
              delete.

        Raise:
            ~ery_backend.base.exceptions.EryValidationError: An error occuring if restrictions are violated.
        """
        from ery_backend.modules.models import WidgetChoice

        if self.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.choice:
            widget_ids = self.variable_definition.widgets.values_list('id', flat=True)
            match = WidgetChoice.objects.filter(value=self.value, widget__id__in=widget_ids)
            if match:
                raise EryValidationError(
                    "Cannot delete VariableChoiceItem, as doing so will invalidate WidgetChoice"
                    f" of same value, {self.value},"
                    f" connected to ModuleDefinitionWidget: {match.first().widget.name}."
                )
        super().delete(**kwargs)

    # pylint:disable=useless-super-delegation
    def get_translation(self, language):
        """
        Get :class:`VariableChoiceItemTranslation` caption specified by given :class:`Language`.

        If :class:`VariableChoiceItemTranslation` does not exist for given :class:`Language`, get one
        matching default :class:`Language` of connected :class:`~ery_backend.modules.models.ModuleDefinition`.

        Args:
            language (:class:`Language`): Used to filter :class:`VariableChoiceItemTranslation` set.

        Returns:
            str: :class:`VariableChoiceItemTranslation` caption.
        """
        return super().get_translation(language)

    # pylint:disable=useless-super-delegation
    def get_info(self, language):
        """
        Get value and caption of specified :class:`Language`.

        Args:
            language (:class:`Language`): Used to filter :class:`WidgetChoiceTranslation`.

        Returns:
        dict: Contains :class:`VariableChoiceItem` value and caption from selected :class:`VariableChoiceItemTranslation`.

        Notes:
            - If translation matching specified :class:`Language` does not exist, default :class:`Language`
              as specified by parental :class:`~ery_backend.modules.models.ModuleDefinition` is used instead.
        """
        return super().get_info(language)


class VariableMixin(models.Model):
    """Base model mixin for Variables."""

    class Meta:
        abstract = True

    variable_definition = models.ForeignKey('variables.VariableDefinition', null=True, blank=True, on_delete=models.CASCADE)
    stint_definition_variable_definition = models.ForeignKey(
        'stints.StintDefinitionVariableDefinition', null=True, blank=True, on_delete=models.CASCADE
    )

    value = JSONField(null=True, blank=True)

    def get_variable_definition(self, module_definition=None):
        """Get variable definitions related to the provided module definition"""
        if self.variable_definition:

            if module_definition is not None and self.variable_definition.module_definition != module_definition:
                raise ValueError(
                    f"This VariableDefinition belongs exclusively to {self.variable_definition.module_definition}"
                )

            return self.variable_definition

        if module_definition is None:
            stint_def_module_defs = self.module.stint.stint_specification.stint_definition.stint_definition_module_definitions
            if not stint_def_module_defs.exists():
                raise ValueError(f"Missing StintDefinitionModuleDefinition for {self}")

            variable_definition_ids = self.stint_definition_variable_definition.variable_definitions.values_list('id')

            # variable_definitions in sdmd.variable_definitions cannot have same module_definition
            for sdmd in stint_def_module_defs.select_related('module_definition').all():
                variable_definition = sdmd.module_definition.variabledefinition_set.filter(
                    id__in=variable_definition_ids
                ).first()
                if variable_definition:  # this is earliest order variable_definition by stintdefmoduledef ordering
                    return variable_definition

            raise ValueError(
                "No ModuleDefinition found belonging to StintDefinition owning" f" a variable_definition connected to {self}."
            )

        return self.stint_definition_variable_definition.variable_definitions.get(module_definition=module_definition)

    def set_default(self):
        """Set variable to its default value"""
        vd = self.get_variable_definition()
        self.value = vd.default_value
        if self.value:
            self.value = vd.cast(self.value)

    def clean(self):
        super().clean()
        vd = self.get_variable_definition()

        if self.value in [None, '']:
            self.set_default()
        else:
            self.value = vd.cast(self.value)

        if vd.data_type == VariableDefinition.DATA_TYPE_CHOICES.stage:
            if self.value:
                if not vd.module_definition.has_stage(self.value):
                    raise ValueError(
                        f"No stage found with name: {self.value}," f" for {self.variable_definition.module_definition}."
                    )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def reset_payoff(self):
        """
        Reset value of payoff :class:`Variable` instance to 0.

        Raises:
            ValidationError: Raised if instance does not have :class:`VariableDefinition` with is_payoff == True.
        """
        if not self.get_variable_definition().is_payoff:
            raise ValidationError(
                "variable_definition: 'reset_payoff' can only be executed on variables that have a parental"
                f" variable_definition with is_payoff == True. {self} with variable_definition:"
                f" {self.variable_definition} does does not match this criterion."
            )
        self.value = 0
        self.save()


class ModuleVariable(VariableMixin, EryPrivileged):
    """
    Instantiated form of VariableDefinition shared at the module level (across Hands/Teams)

    Parent: VariableDefinition
    """

    class Meta(EryPrivileged.Meta):
        ordering = ('module',)
        unique_together = (('module', 'variable_definition'), ('module', 'stint_definition_variable_definition'))

    parent_field = 'module'
    # Since this is a runtime model, its attributes should never be deleted while in use, so on_delete is irrelevant.
    module = models.ForeignKey('modules.Module', on_delete=models.CASCADE, null=True, blank=True, related_name='variables')


class TeamVariable(VariableMixin, EryPrivileged):
    """
    Instantiated form of VariableDefinition shared at the team level (across Hands belonging to said Team)
    Teams have their own scope of variable (TeamVariable) used to measure Team specific info during a stint
    (like group payoff split between hands)
    """

    class Meta(EryPrivileged.Meta):
        ordering = ('team',)
        unique_together = (('team', 'variable_definition'), ('team', 'stint_definition_variable_definition'))

    parent_field = 'module'
    # Since this is a runtime model, its attributes should never be deleted while in use, so on_delete is irrelevant.
    module = models.ForeignKey(
        'modules.Module', on_delete=models.CASCADE, related_name='team_variables', help_text="Grand-parental instance"
    )
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, null=True, blank=True, related_name='variables')


class HandVariable(VariableMixin, EryPrivileged):
    """
    Instantiated form of VariableDefinition specific to a Hand
    Hands have their own scope of variable (HandVariable) used to measure Hand specific info during a stint (such as payoff)
    """

    class Meta(EryPrivileged.Meta):
        ordering = ('hand',)
        unique_together = (
            ('hand', 'variable_definition'),
            ('hand', 'stint_definition_variable_definition'),
        )

    parent_field = 'module'
    # Since this is a runtime model, its attributes should never be deleted while in use, so on_delete is irrelevant.
    module = models.ForeignKey(
        'modules.Module', on_delete=models.CASCADE, related_name='hand_variables', help_text="Grand-parental instance"
    )
    hand = models.ForeignKey('hands.Hand', on_delete=models.CASCADE, null=True, blank=True, related_name='variables')
