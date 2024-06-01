import string

import factory
import factory.fuzzy

from ery_backend.base.testcases import ReactNamedFactoryMixin
from ery_backend.base.utils import get_default_language


class CommandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'commands.Command'

    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
    action = factory.SubFactory(
        'ery_backend.actions.factories.ActionFactory',
        module_definition=factory.LazyAttribute(lambda x: x.factory_parent.module_definition),
    )
    trigger_pattern = factory.fuzzy.FuzzyText(length=8)
    name = factory.fuzzy.FuzzyText(length=10, chars=string.ascii_lowercase)
    comment = factory.fuzzy.FuzzyText(length=50)


class CommandTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'commands.CommandTemplate'

    template = factory.SubFactory('ery_backend.templates.factories.TemplateFactory')
    command = factory.SubFactory('ery_backend.commands.factories.CommandFactory')


class CommandTemplateBlockFactory(ReactNamedFactoryMixin):
    class Meta:
        model = 'commands.CommandTemplateBlock'

    name = factory.Sequence('CommandTemplateBlock{0}'.format)
    command_template = factory.SubFactory('ery_backend.commands.factories.CommandTemplateFactory')


class CommandTemplateBlockTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'commands.CommandTemplateBlockTranslation'

    command_template_block = factory.SubFactory('ery_backend.commands.factories.CommandTemplateBlockFactory')
    content = factory.fuzzy.FuzzyText(length=100)
    language = factory.LazyFunction(get_default_language)
