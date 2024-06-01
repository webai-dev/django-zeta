from django.core.exceptions import ValidationError
from django.db import models

from model_utils import Choices

from ery_backend.modules.models import ModuleDefinitionNamedModel
from ery_backend.scripts import engine_client


class Condition(ModuleDefinitionNamedModel):
    """
    Specify the circumstance(s) under which an :class:`~ery_backend.models.actions.ActionStep` may be executed.

    Args:
        TYPE_CHOICES: All possible attributes for use in :py:meth:`Condition.evaluate`.
        RELATION_CHOICES: All possible operators for use with :py:meth:`Condition.evaluate`
          (when no sub :class:`Condition` is present).
        BINARY_OPERATOR_CHOICES: All possible operators for use with sub :class:`Condition` in :py:meth:`Condition.evaluate`.
    """

    parent_field = 'module_definition'

    TYPE_CHOICES = Choices(('variable', 'Variable'), ('sub_condition', 'Sub-condition'), ('expression', 'Expression'),)
    BINARY_OPERATOR_CHOICES = Choices(('op_and', '&&'), ('op_or', '||'), ('op_exclusive_or', '^'))
    RELATION_CHOICES = Choices(
        ('equal', '=='),
        ('not_equal', '!='),
        ('less', '<'),
        ('greater', '>'),
        ('less_or_equal', '<='),
        ('greater_or_equal', '>='),
    )

    left_type = models.CharField(
        choices=TYPE_CHOICES,
        max_length=100,
        help_text="Selection (from TYPE_CHOICES) for left side of :class:`Condition` during :py:meth:`Condition.evaluate`",
    )
    right_type = models.CharField(
        choices=TYPE_CHOICES,
        max_length=100,
        help_text="Selection (from TYPE_CHOICES) for right side of :class:`Condition` during :py:meth:`Condition.evaluate`",
    )
    left_expression = models.TextField(
        null=True,
        blank=True,
        help_text="Javascript to be executed for left side of :class:`Condition` based on a"
        " :class:`~ery_backend.hands.models.Hand` or"
        " :class:`~ery_backend.teams.models.Team` context during py:meth:`Condition.evaluate`",
    )
    right_expression = models.TextField(
        null=True,
        blank=True,
        help_text="Javascript to be executed for right side of :class:`Condition` based on a"
        " :class:`~ery_backend.hands.models.Hand` or"
        " :class:`~ery_backend.teams.models.Team` context during py:meth:`Condition.evaluate`",
    )
    left_variable_definition = models.ForeignKey(
        'variables.VariableDefinition',
        related_name='+',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=":class:`~ery_backend.variables.models.VariableDefinition` for left side of :class:`Condition` from which to"
        " obtain value based on  :class:`~ery_backend.hands.models.Hand` during :py:meth:`Condition.evaluate`",
    )
    right_variable_definition = models.ForeignKey(
        'variables.VariableDefinition',
        related_name='+',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=":class:`~ery_backend.variables.models.VariableDefinition` for left side of :class:`Condition` from which to"
        " obtain value based on  :class:`~ery_backend.hands.models.Hand` during :py:meth:`Condition.evaluate`",
    )
    left_sub_condition = models.ForeignKey(
        'conditions.Condition',
        related_name='+',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=":class:`Condition` for left side of current instance from which to obtain value"
        " (via :py:meth:`Condition.evaluate`) based on"
        " :class:`~ery_backend.hands.models.Hand` or :class:`~ery_backend.teams.models.Team`",
    )
    right_sub_condition = models.ForeignKey(
        "conditions.Condition",
        related_name='+',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=":class:`Condition` for right side of current instance from which to obtain value"
        " (via :py:meth:`Condition.evaluate`) based on"
        " :class:`~ery_backend.hands.models.Hand` or :class:`~ery_backend.teams.models.Team`",
    )
    relation = models.CharField(
        choices=RELATION_CHOICES,
        default='equal',
        max_length=100,
        null=True,
        blank=True,
        help_text="Selection (from RELATION_CHOICES) to be used for comparing left/right expression or"
        " :class:`~ery_backend.variables.models.VariableDefinition` values during :py:meth:`Condition.evaluate`",
    )
    operator = models.CharField(
        choices=BINARY_OPERATOR_CHOICES,
        max_length=100,
        null=True,
        blank=True,
        help_text="Selection (from BINARY_OPERATOR_CHOICES) to be used for comparing sub :class:`Condition` values with any"
        " other type (from TYPE_CHOICES) during :py:meth:`Condition.evaluate`",
    )

    @staticmethod
    def get_bxml_serializer():
        from .serializers import ConditionBXMLSerializer

        return ConditionBXMLSerializer

    @staticmethod
    def get_duplication_serializer():
        from .serializers import ConditionDuplicationSerializer

        return ConditionDuplicationSerializer

    @staticmethod
    def get_value(value_type, expression=None, variable_definition=None, sub_condition=None):
        """
        Get value of attribute specified by value_type.

        Args:
            value_type (str): Left_type or right_type used to select :class:`Condition` object's attribute.
            expression (str): Expression to be directly retrieved.
            variable_definition (:class:`~ery_backend.variables.models.VariableDefinition`): Instance from which
              name is retrieved.
            sub_condition (:class:`Condition`): Instance from which result of :py:meth:`Condition.evaluate` is retrieved.

        Returns:
            Union[str, int, float, bool, dict, list]: Based on the value of the corresponding expression,
              :class:`~ery_backend.variables.models.VariableDefinition`, or sub :class:`Condition`.
        """

        def _str_to_bool(value):
            if value.lower() in ['true', 'false']:
                return value.lower()
            return value

        if value_type == Condition.TYPE_CHOICES.expression:
            return _str_to_bool(expression)
        if value_type == Condition.TYPE_CHOICES.variable:
            return variable_definition.name
        if value_type == Condition.TYPE_CHOICES.sub_condition:
            return sub_condition.as_javascript()

    def get_left_value(self):
        """
        Get value as specified by left_type.

        Args:
            hand (:class:`~ery_backend.hands.models.Hand`): Provides context for value of :class:`Condition` object's
              left_type.

        Returns:
            Union[str, int, float, bool, dict, list]: Based on the value of the corresponding expression,
              :class:`~ery_backend.variables.models.VariableDefinition`, or sub :class:`Condition`.
        """

        return self.get_value(
            value_type=self.left_type,
            expression=self.left_expression,
            variable_definition=self.left_variable_definition,
            sub_condition=self.left_sub_condition,
        )

    def get_right_value(self):
        """
        Get value as specified by right_type.

        Args:
            hand (:class:`~ery_backend.hands.models.Hand`): Provides context for value of :class:`Condition` object's
              right_type.

        Returns:
            Union[str, int, float, bool, dict, list]: Based on the value of the corresponding expression,
              :class:`~ery_backend.variables.models.VariableDefinition`, or sub :class:`Condition`.
        """
        return self.get_value(
            value_type=self.right_type,
            expression=self.right_expression,
            variable_definition=self.right_variable_definition,
            sub_condition=self.right_sub_condition,
        )

    # XXX: Needs to invalidate on changes to VariableDefinitions and Sub-conditions
    def as_javascript(self):
        """
        Create JS expression to be evaluated by EryEngine.

        Args:
            hand (:class:`~ery_backend.hands.models.Hand`): Provides context for values of :class:`Condition` object's left
              and right types.

        Notes:
            - When the operator is && and the left condition fails, there is no reason to execute the right condition. Doing so
              will even trigger an undefined error if the left condition checks whether a variable is defined.
        Returns:
            str: consists of corresponding values of left and right type, and the specified relation or operator.
        """
        if self.relation:
            return f'({self.get_left_value()}) {self.RELATION_CHOICES[self.relation]} ({self.get_right_value()})'

        return f'({self.get_left_value()}) {self.BINARY_OPERATOR_CHOICES[self.operator]} ({self.get_right_value()})'

    def evaluate(self, hand, team=None):
        """
        Perform evaluation on left/right value and operator or relation.

        Args:
            hand (:class:`~ery_backend.hands.models.Hand`): Provides context sent to EryEngine during evaluation.

        Notes:
          - See get_value for details on how values, operator, and relation are obtained.
          - This method is cached with no invalidation.

        Returns:
            bool: Result of comparison in EryEngine.
        """
        return engine_client.evaluate_without_side_effects(str(self), self.as_javascript(), hand)

    def _is_none(self, validation_attr, type_choice, value, side):
        """
        Generate error message specific to attribute if value is None.

        First arg is whether or not an error should be triggered, with the second arg as the optional message.
        """
        if value is None:
            error_message = ValidationError(
                {
                    validation_attr: "If {}_type == \'{}\', a {} is required for"
                    " {}".format(side, type_choice, validation_attr, self)
                }
            )
            return True, error_message
        return False, None

    def _pre_validate_expression(self, expression, side):
        """
        Confirms expression is not None.

        First arg is whether or not an error should be triggered, with the second arg as the optional message.
        """
        validation_attr = '{}_expression'.format(side)
        expression_is_none, error_message = self._is_none(validation_attr, Condition.TYPE_CHOICES.expression, expression, side)
        if expression_is_none:
            return False, error_message
        return True, None

    def _pre_validate_vardef(self, vardef, side):
        """
        Confirms variable definition is not None.

        First arg is whether or not an error should be triggered, with the second arg as the optional message.
        """
        validation_attr = '{}_variable_definition'.format(side)
        varaible_definition_is_none, error_message = self._is_none(
            validation_attr, Condition.TYPE_CHOICES.variable, vardef, side
        )
        if varaible_definition_is_none:
            return False, error_message
        return True, None

    @staticmethod
    def _pre_handle_is_valid(side_is_valid, error_message):
        """
        Raise error (as required) before save.
        """
        if not side_is_valid:
            raise ValidationError(error_message)

    def _post_handle_is_valid(self, side_is_valid, error_message):
        """
        Raise error (as required) after save.
        """
        if not side_is_valid:
            self.delete()
            raise ValidationError(error_message)

    def clean(self):
        """
        Default django method, with additional enforcement of required attribute combinations.

        Raises:
            :class:`ValidationError`: Triggered on violation of required attribute combination(s).
        """
        super().clean()
        if self.TYPE_CHOICES.sub_condition not in (self.left_type, self.right_type):
            # XXX: Address in issue # 813
            # sub_condition = Condition.TYPE_CHOICES.sub_condition
            # if sub_condition in (self.left_type, self.right_type):
            #     if not (self.left_type == sub_condition and self.right_type == sub_condition):
            #         raise ValidationError(
            #             {
            #                 'left_type': f"If either left_type or right_type == '{sub_condition}', the other type must"
            #                 f"  be equal to '{sub_condition}' as well for {self}.".strip('\n')
            #             }
            #         )
            #     if not self.left_sub_condition or not self.right_sub_condition:
            #         raise ValidationError(
            #             {
            #                 'left_sub_condition': f"If either left_type or right_type == '{sub_condition}', a"
            #                 f" left_sub_condition and right sub_condition are required for {self}".strip('\n')
            #             }
            #         )
            #     if not self.operator:
            #         raise ValidationError(
            #             {
            #                 'operator': f"If either left_type or right_type == '{sub_condition}', an operator is required"
            #                 f" for {self}".strip('\n')
            #             }
            #         )
            # else:
            type_set = [Condition.TYPE_CHOICES.expression, Condition.TYPE_CHOICES.variable]
            if not self.relation:
                raise ValidationError(
                    {
                        'relation': f"If either left_type or right_type is {type_set[0]} or {type_set[1]},"
                        f" a relation is required for {self}.".strip('\n')
                    }
                )
            if self.left_type == Condition.TYPE_CHOICES.expression:
                self._pre_handle_is_valid(*self._pre_validate_expression(self.left_expression, 'left'))

            #     elif self.left_type == Condition.TYPE_CHOICES.variable:
            #         self._pre_handle_is_valid(*self._pre_validate_vardef(self.left_variable_definition, 'left'))

            if self.right_type == Condition.TYPE_CHOICES.expression:
                self._pre_handle_is_valid(*self._pre_validate_expression(self.right_expression, 'right'))
        #     elif self.right_type == Condition.TYPE_CHOICES.variable:
        #         self._pre_handle_is_valid(*self._pre_validate_vardef(self.right_variable_definition, 'right'))
