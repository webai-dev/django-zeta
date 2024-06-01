import random

import factory
import factory.fuzzy

from countries_plus.models import Country
from languages_plus.models import Language

from .models import StintSpecification, StintSpecificationAllowedLanguageFrontend


class StintSpecificationCountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stint_specifications.StintSpecificationCountry'

    stint_specification = factory.SubFactory('ery_backend.stint_specifications.factories.StintSpecificationFactory')

    @factory.lazy_attribute
    def country(self):
        preexisting_country_pks = self.stint_specification.stint_specification_countries.values_list('country__pk', flat=True)
        return Country.objects.exclude(pk__in=preexisting_country_pks).order_by('?').first()


class StintSpecificationAllowedLanguageFrontendFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stint_specifications.StintSpecificationAllowedLanguageFrontend'

    stint_specification = factory.SubFactory('ery_backend.stint_specifications.factories.StintSpecificationFactory')
    frontend = factory.SubFactory('ery_backend.frontends.factories.FrontendFactory')

    @factory.lazy_attribute
    def language(self):
        preexisting_language_pks = list(
            self.stint_specification.allowed_language_frontend_combinations.values_list('language__pk', flat=True)
        )
        return Language.objects.exclude(pk__in=preexisting_language_pks).order_by('?').first()


class StintSpecificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stint_specifications.StintSpecification'

    name = factory.Sequence('stint-specification-{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    stint_definition = factory.SubFactory('ery_backend.stints.factories.StintDefinitionFactory')
    team_size = factory.fuzzy.FuzzyInteger(1, 50)
    min_earnings = factory.fuzzy.FuzzyFloat(0, 50)
    immediate_payment_method = factory.fuzzy.FuzzyChoice([pay_method for pay_method, _ in StintSpecification.PAYMENT_CHOICES])
    where_to_run = factory.fuzzy.FuzzyChoice([run_choice for run_choice, _ in StintSpecification.WHERE_TO_RUN_CHOICES])
    late_arrival = factory.fuzzy.FuzzyChoice([True, False])
    vendor = factory.SubFactory('ery_backend.vendors.factories.VendorFactory')

    @factory.lazy_attribute
    def min_team_size(self):
        return random.randint(1, self.team_size)

    @factory.lazy_attribute
    def max_team_size(self):
        return random.randint(self.team_size, 100)

    @factory.lazy_attribute
    def max_earnings(self):
        return random.uniform(self.min_earnings, 1000)

    @factory.post_generation
    def add_languagefrontends(obj, create, extracted, **kwargs):
        exception_msg = "Extracted must be a list of dicts containing {frontend: model, language: model}"
        if extracted:
            if not isinstance(extracted, list):
                raise Exception(exception_msg)
            for obj_info in extracted:
                if not isinstance(obj_info, dict):
                    raise Exception(exception_msg)
            for obj_info in extracted:
                allowed_obj = StintSpecificationAllowedLanguageFrontend.objects.create(
                    frontend=obj_info['frontend'], language=obj_info['language'], stint_specification=obj
                )
                obj.allowed_language_frontend_combinations.add(allowed_obj)
        else:
            allowed_obj = StintSpecificationAllowedLanguageFrontendFactory(stint_specification=obj)
            obj.allowed_language_frontend_combinations.add(allowed_obj)


class StintSpecificationRobotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stint_specifications.StintSpecificationRobot'

    stint_specification = factory.SubFactory('ery_backend.stint_specifications.factories.StintSpecificationFactory')

    @classmethod
    def _after_postgeneration(cls, obj, create, results=None):
        from ery_backend.robots.factories import RobotFactory

        obj.robots.add(RobotFactory())
        return obj


class StintSpecificationVariableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stint_specifications.StintSpecificationVariable'

    stint_specification = factory.SubFactory('ery_backend.stint_specifications.factories.StintSpecificationFactory')
    variable_definition = factory.SubFactory('ery_backend.variables.factories.VariableDefinitionFactory')
    set_to_every_nth = factory.fuzzy.FuzzyInteger(0, 9)

    @factory.lazy_attribute
    def value(self):
        from ery_backend.base.testcases import random_dt_value
        from ery_backend.variables.models import VariableChoiceItem

        value = random_dt_value(self.variable_definition.data_type)
        if self.variable_definition.data_type == self.variable_definition.DATA_TYPE_CHOICES.choice:
            value = value.lower()  # for case insensitive choices
            VariableChoiceItem.objects.get_or_create(variable_definition=self.variable_definition, value=value)
        return value


class StintModuleSpecificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stint_specifications.StintModuleSpecification'

    hand_timeout = factory.fuzzy.FuzzyInteger(0, 60)
    hand_warn_timeout = factory.fuzzy.FuzzyInteger(0, 60)
    stop_on_quit = factory.fuzzy.FuzzyChoice([True, False])
    timeout_earnings = factory.fuzzy.FuzzyFloat(0, 5)
    stint_specification = factory.SubFactory('ery_backend.stint_specifications.factories.StintSpecificationFactory')
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')

    @factory.lazy_attribute
    def max_earnings(self):
        current_max_earnings_sum = sum(self.stint_specification.module_specifications.values_list('max_earnings', flat=True))
        max_earnings_remainder = self.stint_specification.max_earnings - current_max_earnings_sum
        return random.uniform(0, max_earnings_remainder)

    @factory.lazy_attribute
    def min_earnings(self):
        current_min_earnings_sum = sum(self.stint_specification.module_specifications.values_list('min_earnings', flat=True))
        min_earnings_remainder = self.stint_specification.min_earnings - current_min_earnings_sum
        limit = min([min_earnings_remainder, self.max_earnings])
        return random.uniform(0, limit)
