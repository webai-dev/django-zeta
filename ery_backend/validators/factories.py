import random

import factory
import factory.fuzzy

from django.utils.crypto import get_random_string

from .models import Validator


def get_random_string_with_ery_args():
    return get_random_string(length=random.randint(1, 100))


class ValidatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'validators.validator'

    name = factory.Sequence('validator-{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    nullable = True
    slug = factory.LazyAttribute(lambda x: Validator.create_unique_slug(x.name))

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Overriden to handle clean requirement
        if 'regex' not in kwargs and 'code' not in kwargs:
            kwargs[random.choice(['regex', 'code'])] = get_random_string_with_ery_args()
        elif not kwargs.get('regex') and 'code' not in kwargs:
            kwargs['code'] = get_random_string_with_ery_args()
        elif not kwargs.get('code') and 'regex' not in kwargs:
            kwargs['regex'] = get_random_string_with_ery_args()

        obj = model_class(*args, **kwargs)
        obj.save()
        return obj
