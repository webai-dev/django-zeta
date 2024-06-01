import factory
import factory.fuzzy

from ery_backend.base.testcases import ReactNamedFactoryMixin
from ery_backend.base.utils import get_default_language

from .models import Redirect


class StageDefinitionFactory(ReactNamedFactoryMixin):
    class Meta:
        model = 'stages.StageDefinition'

    name = factory.Sequence('StageDefinition{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')


class StageTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stages.StageTemplate'

    stage_definition = factory.SubFactory('ery_backend.stages.factories.StageDefinitionFactory')
    template = factory.SubFactory('ery_backend.templates.factories.TemplateFactory')
    theme = factory.SubFactory('ery_backend.themes.factories.ThemeFactory')


class StageTemplateBlockFactory(ReactNamedFactoryMixin):
    class Meta:
        model = 'stages.StageTemplateBlock'

    stage_template = factory.SubFactory('ery_backend.stages.factories.StageTemplateFactory')
    name = factory.Sequence(lambda n: f'StageTemplateBlock{n}')


class StageTemplateBlockTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stages.StageTemplateBlockTranslation'

    stage_template_block = factory.SubFactory('ery_backend.stages.factories.StageTemplateBlockFactory')
    content = factory.fuzzy.FuzzyText(length=100)
    language = factory.LazyFunction(get_default_language)


class StageBreadcrumbFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stages.StageBreadcrumb'

    hand = factory.SubFactory('ery_backend.hands.factories.HandFactory')
    stage = factory.SubFactory('ery_backend.stages.factories.StageFactory')


class StageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stages.Stage'

    stage_definition = factory.SubFactory('ery_backend.stages.factories.StageDefinitionFactory')
    preaction_started = False


def _get_order(instance):
    qs = Redirect.objects.filter(stage_definition=instance.stage_definition)
    if not qs.exists():
        return 0
    return qs.count()


class RedirectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stages.Redirect'

    stage_definition = factory.SubFactory('ery_backend.stages.factories.StageDefinitionFactory')
    order = factory.LazyAttribute(_get_order)
    next_stage_definition = factory.SubFactory(
        'ery_backend.stages.factories.StageDefinitionFactory',
        module_definition=factory.SelfAttribute('..stage_definition.module_definition'),
    )
