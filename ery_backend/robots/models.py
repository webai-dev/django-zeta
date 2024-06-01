from django.db import models
from django.core.exceptions import ValidationError

from model_utils import Choices

from ery_backend.base.models import EryPrivileged
from ery_backend.modules.models import ModuleDefinitionNamedModel, ModuleDefinitionWidget


class Robot(ModuleDefinitionNamedModel):
    class SerializerMeta(ModuleDefinitionNamedModel.SerializerMeta):
        model_serializer_fields = ('rules',)

    parent_field = 'module_definition'

    module_definition = models.ForeignKey(
        'modules.ModuleDefinition',
        on_delete=models.CASCADE,
        help_text="Parent :class:`~ery_backend.modules.models.ModuleDefinition`",
        related_name='robots',
    )


class RobotRule(EryPrivileged):
    RULE_TYPE_CHOICES = Choices(('static', "Static"), ('randomize', "Randomize"))

    parent_field = 'robot'
    robot = models.ForeignKey(Robot, on_delete=models.CASCADE, null=False, related_name='rules')
    widget = models.ForeignKey(ModuleDefinitionWidget, on_delete=models.CASCADE, null=False)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES, null=False)
    static_value = models.CharField(max_length=512, null=True, blank=True)

    def clean(self):
        """
        Prevent save if rule type is `static` and `static_value` is `None` or
        if `static_value` violates :class:`~ery_backend.variables.models.VariableDefinition` related
        restrictions.

        Specifically:
            - :class:`~ery_backend.variables.models.VariableDefinition` object connected to parental :class:`Robot` must be of
              DATA_TYPE_CHOICE 'choice' or 'str'.

        Raises:
            - :class:`~ery_backend.base.exceptions.ValidationError`:
              Raised if rule type is `static` and `static_value` is `None`.
            - ~ery_backend.base.exceptions.EryTypeError: An error occuring if :class:`~ery_backend.robots.models.Robot`
              attempts to create an :class:`RobotRule` with an :class:`ModuleDefinitionWidget` whose
              :class:`~ery_backend.variables.models.VariableDefinition` is not of type choice or 'str'.
        """
        super().clean()
        if self.rule_type == 'static' and self.static_value is None:
            raise ValidationError({'static_value': "Can not leave static_value empty when rule_type is set to static."})

        # XXX: Address in issue #815
        # if self.widget.variable_definition:
        #     if self.widget.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.choice:
        #         variable_definition_values = self.widget.variable_definition.get_values()

        #         # Any widget choice must be subset of var choice item set
        #         if self.static_value not in variable_definition_values:
        #             raise EryValueError(
        #                 f"Value, {self.static_value}, of RobotRule not found in VariableChoiceItem values,"
        #                 f" {variable_definition_values}, for widget's VariableDefinition of name,"
        #                 f" {self.widget.variable_definition.name}"
        # )

    def get_value(self):
        """
        Get static value or random value based on rule_type
        """
        if self.rule_type == 'static':
            return self.static_value

        return self.widget.variable_definition.get_random_value()
