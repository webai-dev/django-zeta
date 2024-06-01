import random

import factory

from ery_backend.conditions.models import Condition
from ery_backend.variables.factories import VariableDefinitionFactory


class ConditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conditions.Condition'

    name = factory.Sequence('condition-{0}'.format)
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
    left_type = factory.fuzzy.FuzzyChoice([choice for choice, _ in Condition.TYPE_CHOICES])
    right_type = factory.fuzzy.FuzzyChoice([choice for choice, _ in Condition.TYPE_CHOICES])

    @factory.lazy_attribute
    def left_variable_definition(self):
        if self.left_type == Condition.TYPE_CHOICES.variable:
            return VariableDefinitionFactory(module_definition=self.module_definition)
        return None

    @factory.lazy_attribute
    def right_variable_definition(self):
        if self.right_type == Condition.TYPE_CHOICES.variable:
            return VariableDefinitionFactory(module_definition=self.module_definition)
        return None

    @factory.lazy_attribute
    def left_expression(self):
        if self.left_type == Condition.TYPE_CHOICES.expression:
            return str(random.randint(1, 10))
        return None

    @factory.lazy_attribute
    def right_expression(self):
        if self.right_type == Condition.TYPE_CHOICES.expression:
            return str(random.randint(1, 10))
        return None

    @factory.lazy_attribute
    def left_sub_condition(self):
        if self.left_type == Condition.TYPE_CHOICES.sub_condition:
            return ConditionFactory(module_definition=self.module_definition)
        return None

    @factory.lazy_attribute
    def right_sub_condition(self):
        if self.right_type == Condition.TYPE_CHOICES.sub_condition:
            return ConditionFactory(module_definition=self.module_definition)
        return None
