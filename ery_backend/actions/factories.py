import factory
import factory.fuzzy

from ery_backend.variables.factories import VariableDefinitionFactory

from .models import ActionStep


class ActionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'actions.Action'

    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
    name = factory.Sequence('action-{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)


class ActionStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'actions.ActionStep'

    action = factory.SubFactory('ery_backend.actions.factories.ActionFactory')
    subaction = factory.SubFactory('ery_backend.actions.factories.ActionFactory')
    order = factory.Sequence(lambda n: n)
    for_each = factory.fuzzy.FuzzyChoice(
        [
            ActionStep.FOR_EACH_CHOICES.current_hand_only,
            ActionStep.FOR_EACH_CHOICES.hand_in_neighborhood,
            ActionStep.FOR_EACH_CHOICES.hand_in_team,
            ActionStep.FOR_EACH_CHOICES.hand_in_stint,
            ActionStep.FOR_EACH_CHOICES.team_in_stint,
        ]
    )
    action_type = factory.fuzzy.FuzzyChoice(
        [
            ActionStep.ACTION_TYPE_CHOICES.set_variable,
            ActionStep.ACTION_TYPE_CHOICES.set_era,
            ActionStep.ACTION_TYPE_CHOICES.run_code,
            ActionStep.ACTION_TYPE_CHOICES.log,
            ActionStep.ACTION_TYPE_CHOICES.save_data,
        ]
    )
    value = factory.fuzzy.FuzzyText(length=25)
    code = factory.fuzzy.FuzzyText(length=100)
    variable_definition = factory.SubFactory('ery_backend.variables.factories.VariableDefinitionFactory')
    era = factory.SubFactory('ery_backend.syncs.factories.EraFactory')
    log_message = factory.fuzzy.FuzzyText(length=100)

    @factory.post_generation
    def to_save(self, create, extracted, **kwargs):
        if not create:
            self.to_save.add(VariableDefinitionFactory())

        if extracted:
            for variable_definition in extracted:
                self.to_save.add(variable_definition)
