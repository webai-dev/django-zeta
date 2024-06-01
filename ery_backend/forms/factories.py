import random

import factory
import factory.fuzzy

from languages_plus.models import Language

from ery_backend.base.testcases import random_dt_value, random_dt
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetFactory

from .models import Form


class FormFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'forms.Form'

    name = factory.Sequence('Form{}'.format)
    slug = factory.LazyAttribute(lambda x: Form.create_unique_slug(x.name))
    comment = factory.fuzzy.FuzzyText(length=100)
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')


class FormFieldFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'forms.FormField'

    name = factory.Sequence('FormField{}'.format)
    form_item = factory.SubFactory('ery_backend.forms.factories.FormItemFactory', child_type=False)
    helper_text = factory.fuzzy.FuzzyText()
    required = factory.fuzzy.FuzzyChoice([True, False])
    widget = factory.LazyFunction(
        lambda frontend_cls=Frontend, widget_factory=WidgetFactory: WidgetFactory(
            frontend=frontend_cls.objects.get(name='Web')
        )
    )

    @factory.lazy_attribute
    def variable_definition(self):
        from ery_backend.variables.factories import VariableDefinitionFactory

        return VariableDefinitionFactory(module_definition=self.form_item.form.module_definition)

    @factory.lazy_attribute
    def disable(self):
        from ery_backend.conditions.factories import ConditionFactory

        return ConditionFactory(module_definition=self.form_item.form.module_definition)

    @factory.lazy_attribute
    def initial_value(self):
        return random_dt_value(self.variable_definition.data_type)

    @factory.post_generation
    def add_choices(self, create, extracted, **kwargs):
        add_translations = 'translations' in kwargs and kwargs['translations']
        if extracted:
            limit = 2 if self.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.bool else 10
            for _ in range(random.randint(1, limit)):
                FormFieldChoiceFactory(field=self, add_translations=add_translations)


class FormItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'forms.FormItem'

    class Params:
        use_field = factory.fuzzy.FuzzyChoice([True, False])

    form = factory.SubFactory('ery_backend.forms.factories.FormFactory')

    @factory.lazy_attribute
    def order(self):
        last_order = self.form.items.order_by('-order').values_list('order', flat=True).first()
        if last_order is not None:
            return last_order + 1
        return 0

    @factory.lazy_attribute
    def tab_order(self):
        last_order = self.form.items.order_by('-tab_order').values_list('tab_order', flat=True).first()
        if last_order is not None:
            return last_order + 1
        return 0

    @factory.post_generation
    def child_type(obj, create, extracted, **kwargs):
        if extracted is not False:
            child_choices = {'field': FormFieldFactory, 'button_list': FormButtonListFactory}
            if not hasattr(obj, 'field') and not hasattr(obj, 'button_list'):
                # It means something else if extracted is None
                if extracted != False:  # pylint: disable=singleton-comparison
                    child_attr = extracted if extracted else random.choice(['field', 'button_list'])
                    child_choices[child_attr](form_item=obj)


class FormFieldChoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'forms.FormFieldChoice'

    field = factory.SubFactory('ery_backend.forms.factories.FormFieldFactory')

    @factory.lazy_attribute
    def order(self):
        last_order = self.field.choices.order_by('-order').values_list('order', flat=True).first()
        if last_order is not None:
            return last_order + 1
        return 0

    @factory.lazy_attribute
    def value(self):
        from ery_backend.variables.models import VariableChoiceItem

        existing_choices = list(self.field.choices.values_list('value', flat=True))

        def _create_value(has_vd=True):
            if has_vd:
                # This is done on __init__ of var choice
                value = str(random_dt_value(self.field.variable_definition.data_type)).lower()
            else:
                value = str(
                    random_dt_value(
                        random_dt(
                            exclude=[VariableDefinition.DATA_TYPE_CHOICES.choice, VariableDefinition.DATA_TYPE_CHOICES.stage]
                        )
                    )
                ).lower()
            return value

        has_vd = self.field.variable_definition is not None
        value = _create_value(has_vd)
        counter = 0
        while value in existing_choices:
            value = _create_value(has_vd)
            counter += 1
            if counter > 100 and self.field.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.bool:
                raise Exception(
                    "Tried to create a third variable choice item for a boolean variable while making choice"
                    f" item for FieldFactory"
                )

        if has_vd and self.field.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.choice:
            VariableChoiceItem.objects.get_or_create(variable_definition=self.field.variable_definition, value=value)
        return value

    @factory.post_generation
    def add_translations(self, create, extracted, **kwargs):
        if extracted:
            if not isinstance(extracted, Language):
                languages_used = []
                for _ in range(random.randint(1, 10)):
                    language = Language.objects.exclude(pk__in=languages_used).order_by('?').first()
                    languages_used.append(language.pk)
                    FormFieldChoiceTranslationFactory(
                        language=language,
                        caption="Caption for f{self.__class__.__name__}, order: {self.order}, value: {self.value}",
                        field_choice=self,
                    )
            else:
                language = extracted
                FormFieldChoiceTranslationFactory(
                    language=language,
                    caption="Caption for f{self.__class__.__name__}, order: {self.order}, value: {self.value}",
                    field_choice=self,
                )


class FormFieldChoiceTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'forms.FormFieldChoiceTranslation'

    field_choice = factory.SubFactory('ery_backend.forms.factories.FormFieldChoiceFactory')
    caption = factory.fuzzy.FuzzyText(length=5)

    @factory.lazy_attribute
    def language(self):
        language_pks = self.field_choice.translations.values_list('language__pk', flat=True)
        default_language = get_default_language()
        if not default_language.pk in language_pks:
            return default_language
        use_language = Language.objects.exclude(pk__in=language_pks).first()
        if not use_language:
            raise Exception(f"Cannot create translation for choice: {self.field_choice}. All languages used!")
        return use_language


class FormButtonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'forms.FormButton'

    button_list = factory.SubFactory('ery_backend.forms.factories.FormButtonListFactory')
    widget = factory.LazyFunction(
        lambda WidgetFactory=WidgetFactory, Frontend=Frontend: WidgetFactory(frontend=Frontend.objects.get(name='Web'))
    )
    submit = factory.fuzzy.FuzzyChoice([True, False])
    name = factory.Sequence('FormButton{}'.format)
    button_text = factory.Sequence('Form Button {}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)

    @factory.lazy_attribute
    def disable(self):
        from ery_backend.conditions.factories import ConditionFactory

        return ConditionFactory(module_definition=self.button_list.get_privilege_ancestor())

    @factory.lazy_attribute
    def hide(self):
        from ery_backend.conditions.factories import ConditionFactory

        return ConditionFactory(module_definition=self.button_list.get_privilege_ancestor())


class FormButtonListFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'forms.FormButtonList'

    form_item = factory.SubFactory('ery_backend.forms.factories.FormItemFactory', child_type=False)
    name = factory.Sequence('FormButtonList{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)

    @factory.post_generation
    def add_buttons(self, create, extracted=True, **kwargs):
        if extracted:
            for _ in range(random.randint(1, 10)):
                FormButtonFactory(button_list=self)
