import json

from django.db import models

from model_utils import Choices

from ery_backend.base.models import EryFile, EryPrivileged


class Theme(EryFile):
    """
    Together with Templates and Stages, Themes define what should be rendered on the frontend.
    Themes describe styling that should be applied to a template, in the form of ThemePalettes.

    """

    logo = models.ForeignKey('assets.ImageAsset', on_delete=models.SET_NULL, blank=True, null=True)
    legal_text = models.TextField(blank=True, null=True)

    class SerializerMeta(EryFile.SerializerMeta):
        model_serializer_fields = ('palettes', 'typographies')

    def _invalidate_related_tags(self, history):
        for stage_template in self.stage_templates.all():
            stage_template.invalidate_tags(history)

    def get_mui_theme(self):
        theme = {
            'palette': {},
            'typography': {},
        }

        def update_if_spec(to_update, obj, attrs):
            for attr in attrs:
                value = getattr(obj, attr)
                if value:
                    to_update[attr] = value

        for palette in self.palettes.all():
            theme['palette'][palette.name] = {'main': palette.main}
            update_if_spec(theme['palette'][palette.name], palette, ('light', 'dark', 'contrast_text'))
        for typography in self.typographies.all():
            theme['typography'][typography.name] = {}
            update_if_spec(theme['typography'][typography.name], typography, ('font_size', 'font_style', 'font_weight'))

        return json.dumps(theme, indent=2)


class ThemePalette(EryPrivileged):
    """
    Theme Palettes are the components of a Theme configuring the colors to be applied to a Stage.
    """

    class Meta(EryPrivileged.Meta):
        # XXX: Address in issue #815
        # unique_together = (('theme', 'name'),)
        pass

    parent_field = 'theme'

    PALETTE_CHOICES = Choices(('primary', 'Primary'), ('secondary', 'Secondary'), ('error', 'Error'))

    theme = models.ForeignKey('themes.Theme', on_delete=models.CASCADE, related_name='palettes')
    name = models.CharField(max_length=12, choices=PALETTE_CHOICES, help_text="Material UI color intention type.")
    main = models.CharField(max_length=7, help_text="Default color tone.")
    light = models.CharField(max_length=7, blank=True, null=True, help_text="Lighter tonal offset of main color.")
    dark = models.CharField(max_length=7, blank=True, null=True, help_text="Darker tonal offset of main color.")
    contrast_text = models.CharField(max_length=7, blank=True, null=True, help_text="Contrast between background and text.")


class ThemeTypography(EryPrivileged):
    """
    Theme Typographys are the components of a Theme configuring the fonts to be applied to a Stage.
    """

    class Meta(EryPrivileged.Meta):
        # XXX: Address in issue #815
        # unique_together = (('theme', 'name'),)
        pass

    parent_field = 'theme'

    TYPOGRAPHY_VARIANT_CHOICES = Choices(
        ('h1', "Header 1"),
        ('h2', "Header 2"),
        ('h3', "Header 3"),
        ('h4', "Header 4"),
        ('h5', "Header 5"),
        ('h6', "Header 6"),
        ('subtitle1', "Subtitle 1"),
        ('subtitle2', "Subtitle 2"),
        ('body1', "Body 1"),
        ('body2', "Body 2"),
        ('button', "Button"),
        ('caption', "Caption"),
        ('overline', "Overline"),
    )

    TYPOGRAPHY_STYLE_CHOICES = Choices(('normal', "Normal"), ('italic', "Italic"), ('oblique', "Oblique"))

    TYPOGRAPHY_WEIGHT_CHOICES = Choices(
        ('normal', "Equivalent of 400."),
        ('bold', "Equivalent of 700."),
        ('bolder', "Bolder than the inherited font weight."),
        ('lighter', "Lighter than the inherited font weight."),
        ('100', "100"),
        ('200', "200"),
        ('300', "300"),
        ('400', "400"),
        ('500', "500"),
        ('600', "600"),
        ('700', "700"),
        ('800', "800"),
        ('900', "900"),
        ('initial', "Initial value provided by browser."),
        ('inherit', "Value provider by parent (if any). If none, uses browser default."),
    )

    theme = models.ForeignKey('themes.Theme', on_delete=models.CASCADE, related_name='typographies')
    name = models.CharField(
        max_length=12, choices=TYPOGRAPHY_VARIANT_CHOICES, help_text="Material UI typography variant type."
    )
    # max length assumes 12 character max number with rem suffix
    font_size = models.CharField(
        max_length=15, help_text="Exact (in pixels) or responsive (in rem) specification" " of font size for given typography."
    )
    font_weight = models.CharField(
        max_length=12,
        choices=TYPOGRAPHY_WEIGHT_CHOICES,
        help_text="Exact (numerical) or descriptive (e.g., bold) specification" "of font emphasis for given typography.",
    )
    font_style = models.CharField(max_length=12, choices=TYPOGRAPHY_STYLE_CHOICES)
