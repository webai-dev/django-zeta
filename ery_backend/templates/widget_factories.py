import factory


class TemplateWidgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'templates.TemplateWidget'

    template = factory.SubFactory('ery_backend.templates.factories.TemplateFactory')
    widget = factory.SubFactory('ery_backend.widgets.factories.WidgetFactory')
    name = factory.Sequence('TemplateWidget{}'.format)
