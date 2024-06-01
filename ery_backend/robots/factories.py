import factory
import factory.fuzzy


class RobotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'robots.Robot'

    name = factory.Sequence('robot-{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')


class RobotRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'robots.RobotRule'

    robot = factory.SubFactory('ery_backend.robots.factories.RobotFactory')
    widget = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionWidgetFactory')
    rule_type = factory.Iterator(['random', 'static'])

    @factory.lazy_attribute
    def static_value(self):
        from ery_backend.base.testcases import random_dt_value, random_dt
        from ery_backend.variables.models import VariableDefinition, VariableChoiceItem

        choice = VariableDefinition.DATA_TYPE_CHOICES.choice
        if self.widget.variable_definition and self.widget.variable_definition.data_type == choice:
            value = random_dt_value(self.widget.variable_definition.data_type).lower()  # Done in VariableChoiceItem.__init__
            VariableChoiceItem.objects.get_or_create(variable_definition=self.widget.variable_definition, value=value)
        else:
            value = random_dt_value(random_dt())
        return value
