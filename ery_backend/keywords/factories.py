import factory
import factory.fuzzy


class KeywordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'keywords.Keyword'

    name = factory.fuzzy.FuzzyText(length=10)
    comment = factory.fuzzy.FuzzyText(length=50)
