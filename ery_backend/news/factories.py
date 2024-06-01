import factory
import factory.fuzzy


class NewsItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'syncs.NewsItem'

    text = factory.fuzzy.FuzzyText(length=100)
