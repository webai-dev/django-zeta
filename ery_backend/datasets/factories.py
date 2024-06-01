import random

from django.utils.crypto import get_random_string

import factory

from .models import Dataset


# XXX: #525 Add datasetasset factory as well. Not required for Dataset model.
class DatasetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'datasets.Dataset'

    name = factory.Sequence('dataset-{0}'.format)
    slug = factory.LazyAttribute(lambda x: Dataset.create_unique_slug(x.name))

    @factory.post_generation
    def to_dataset(obj, create, extracted, **kwargs):
        if extracted:
            data = extracted
        else:
            data = []
            column_n = random.randint(1, 10)
            headers = []
            for _ in range(column_n):
                headers.append(get_random_string(length=random.randint(5, 10)))
            for _ in range(random.randint(1, 10)):
                row = {}
                for header in headers:
                    choice = random.choice([int, str, float])
                    if choice == int:
                        element = random.randint(1, 10)
                    elif choice == float:
                        element = random.random()
                    else:
                        element = get_random_string(length=random.randint(5, 10))
                    row[header] = str(element)
                data.append(row)
        obj.set_datastore(data)
