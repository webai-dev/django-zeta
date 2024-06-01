import factory
import factory.fuzzy

from ery_backend.base.utils import get_default_language
from ery_backend.base.testcases import ReactNamedFactoryMixin

from .models import Template

# pylint:disable=unused-import
from .widget_factories import TemplateWidgetFactory


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'templates.Template'

    name = factory.Sequence('template-{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    primary_language = factory.LazyFunction(get_default_language)
    frontend = factory.SubFactory('ery_backend.frontends.factories.FrontendFactory')
    slug = factory.LazyAttribute(lambda x: Template.create_unique_slug(x.name))


class TemplateBlockFactory(ReactNamedFactoryMixin):
    class Meta:
        model = 'templates.TemplateBlock'

    template = factory.SubFactory('ery_backend.templates.factories.TemplateFactory')
    name = factory.Sequence('TemplateBlock{}'.format)


class TemplateBlockTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'templates.TemplateBlockTranslation'

    template_block = factory.SubFactory('ery_backend.templates.factories.TemplateBlockFactory')
    language = factory.LazyFunction(get_default_language)
    content = factory.fuzzy.FuzzyText(length=25)
