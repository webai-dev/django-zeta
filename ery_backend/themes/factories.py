import random

import factory
import factory.fuzzy

from .models import Theme, ThemePalette, ThemeTypography


class ThemeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'themes.Theme'

    name = factory.Sequence('theme-{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    published = factory.fuzzy.FuzzyChoice([False, True])
    slug = factory.LazyAttribute(lambda x: Theme.create_unique_slug(x.name))


class ThemePaletteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'themes.ThemePalette'

    theme = factory.SubFactory('ery_backend.themes.factories.ThemeFactory')
    name = factory.fuzzy.FuzzyChoice([x for x, _ in ThemePalette.PALETTE_CHOICES])
    main = factory.fuzzy.FuzzyText(length=6, chars='0123456789abcdef', prefix='#')
    light = factory.fuzzy.FuzzyText(length=6, chars='0123456789abcdef', prefix='#')
    dark = factory.fuzzy.FuzzyText(length=6, chars='0123456789abcdef', prefix='#')
    contrast_text = factory.fuzzy.FuzzyText(length=6, chars='0123456789abcdef', prefix='#')


class ThemeTypographyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'themes.ThemeTypography'

    theme = factory.SubFactory('ery_backend.themes.factories.ThemeFactory')
    name = factory.fuzzy.FuzzyChoice([name for name, _ in ThemeTypography.TYPOGRAPHY_VARIANT_CHOICES])
    font_size = factory.LazyFunction(lambda: random.choice([random.randint(0, 200), f'{random.uniform(0.1, 10.0)}rem)']))
    font_weight = factory.fuzzy.FuzzyChoice([x for x, _ in ThemeTypography.TYPOGRAPHY_WEIGHT_CHOICES])
    font_style = factory.fuzzy.FuzzyChoice([x for x, _ in ThemeTypography.TYPOGRAPHY_STYLE_CHOICES])
