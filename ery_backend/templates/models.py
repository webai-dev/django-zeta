from django.core.exceptions import ValidationError
from django.db import models
from django.template.loader import render_to_string

from languages_plus.models import Language

from ery_backend.base.cache import get_func_cache_key, tag_key
from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.mixins import ReactNamedMixin, TranslationHolderMixin, BlockHolderMixin
from ery_backend.base.models import EryPrivileged, EryFile
from ery_backend.base.utils import get_default_language

# pylint:disable=unused-import
from .widgets import TemplateWidget


class TemplateBlockTranslation(EryPrivileged):
    """
    Units of :class:`TemplateBlock` describing the :class:`Language` for rendering content.

    """

    class Meta(EryPrivileged.Meta):
        unique_together = ('template_block', 'language')

    parent_field = "template_block"
    template_block = models.ForeignKey(
        'templates.TemplateBlock',
        on_delete=models.CASCADE,
        help_text="Parental :class:`TemplateBlock`",
        related_name='translations',
    )
    language = models.ForeignKey(Language, on_delete=models.CASCADE, help_text=":class:`Language` used for rendering content")
    content = models.TextField(help_text="Javascript to be rendered as part of :class:`Stage`", null=True, blank=True)

    @staticmethod
    def get_bxml_serializer():
        """
        Get serializer class.
        """
        from .serializers import TemplateBlockTranslationBXMLSerializer

        return TemplateBlockTranslationBXMLSerializer


class TemplateBlock(ReactNamedMixin, TranslationHolderMixin, EryPrivileged):
    """
    Units of :class:`Template` which describe how to render a :class:`Frontend`.

    Attributes:
        parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.

    Notes:
        * Two TemplateBlocks are combined by rendering the content of one block (e.g., 'Content') within the tag of another
          block with the same name (e.g., '<Content/>'').
        * TemplateBlocks should be Stage agnostic, with Stage level rendering specifications described via StageTemplateBlocks.
        * A TemplateBlockTranslation is created automatically (if does not exist) on save in the parental Template's default
          language.
        * Any name given to a :class:`TemplateBlock` is prefixed with an 'Ery' string. During
          :py:meth:`~ery_backend.stages.models.Stage.render`, all instances of said name within the content body of all
          connected blocks will be converted to this prefixed name. This may effect html tags (e.g., 'title' tags will be
          converted to EryTitle, causing an override of the corresponding html tag).
          This is assumed to be an intentional decision of the content creator.
    """

    class Meta(EryPrivileged.Meta):
        unique_together = (('template', 'name'),)

    class SerializerMeta(EryPrivileged.SerializerMeta):
        model_serializer_fields = ('translations',)

    parent_field = 'template'
    template = models.ForeignKey(
        'templates.Template', on_delete=models.CASCADE, help_text="Parental :class:`Template` instance", related_name='blocks'
    )
    name = models.CharField(max_length=512,)

    @property
    def admin_name(self):
        return self.template.name

    def get_translation(self, language):
        """
        Gets preferred :class:`TemplateBlockTranslation` content as specified by :class:`Language`.

        Args:
            - language :class:`Language` to be prioritized upon retrieval
              of :class:`TemplateBlockTranslation` objects for the same :class:`TemplateBlock`.

        Returns:
            str: The returned content of preferred :class:`TemplateBlockTranslation` as specified by :class:`Language`.
        """
        return self.get_translation_by_frontend_language(language=language)

    def clean(self):
        """
        Performs :class:`TemplateBlock` assignment restricting and auto name assignment.

        Prevents assignment of multiple :class:`TemplateBlock` objects to root :class:`Template`.
        Auto assigns name to root :class:`Template`.

        Notes:
            * A root :class:`Template` is a :class:`Template` object with no parental :class:`Template`.
            * Overrides :py:meth:`ery_backend.base.mixins.ReactNamedMixin.clean`.

        """

        super().clean()
        if not self.template.parental_template:
            template_blocks = TemplateBlock.objects.filter(template=self.template)
            if template_blocks and self not in list(template_blocks):
                raise ValidationError(
                    {
                        'template': "TemplateBlocks: {}, are already linked to template: {}."
                        " Since a template with no parental template can only be linked to one template block,"
                        " TemplateBlock: {} cannot be saved.".format(template_blocks, self.template, self)
                    }
                )
        if not self.template.parental_template:
            self.name = 'Root'

    def is_ready(self, language):
        """
        Confirms :class:`TemplateBlock` has a :class:`TemplateBlockTranslation` with :class:`Language`
        matching the primary :class:`Language` of the parental :class:`Template`.

        Args:
            - :class:`Language`
        Returns:
            bool
        """
        try:
            self.get_translation(language)
            return (True, None)
        except EryValidationError as e:
            return (False, e)


class Template(BlockHolderMixin, EryFile):
    """
    Define (through :class:`TemplateBlock` objects) what should be rendered on the
    :class:`~ery_backend.frontends.models.Frontend`.

    Attributes:
        block_parent: Static declaration of name of related model overriden during
          :py:meth:`ery_backend.base.mixins.BlockHolderMixin.get_blocks`.

    Notes:
        * A root Template can have only one TemplateBlock.
        * Child Templates should be used to populate the content expressed in the root.
          Further levels of detail are expressed through the TemplateBlocks of eachs successive generation.

    """

    class SerializerMeta(EryFile.SerializerMeta):
        model_serializer_fields = ('template_widgets', 'blocks')

    block_parent = 'parental_template'

    parental_template = models.ForeignKey(
        'templates.Template',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Parental :class:`Template` instance",
        related_name='child_templates',
    )
    frontend = models.ForeignKey(
        'frontends.Frontend', on_delete=models.CASCADE, null=True, blank=True, help_text=":class:`Frontend` instance"
    )
    primary_language = models.ForeignKey(
        Language,
        default=get_default_language(pk=True),
        on_delete=models.SET_DEFAULT,
        help_text=":class:`Language` instance used as default for all related content",
    )

    @staticmethod
    def get_bxml_serializer():
        from .serializers import TemplateBXMLSerializer

        return TemplateBXMLSerializer

    def get_blocks(self, language):
        return self.get_blocks_by_frontend_language(language=language)

    def get_widgets(self):
        from ery_backend.widgets.models import Widget

        additional_tags = []  # Not covered by ery_cache method
        widget_ids = set(self.template_widgets.values_list('widget', flat=True).all())
        connected_widget_ids = set()
        for widget_id in widget_ids:
            connected_widget_ids.update(Widget.get_nested_connected_widget_ids(widget_id))
        widget_ids.update(connected_widget_ids)
        additional_tags += [Widget.get_cache_tag_by_pk(pk) for pk in widget_ids]
        current_template = self
        while current_template.parental_template:
            current_template = current_template.parental_template
            additional_tags.append(current_template.get_cache_tag())
            ancestral_widget_ids = set(current_template.template_widgets.values_list('widget', flat=True))
            additional_tags += [Widget.get_cache_tag_by_pk(pk) for pk in ancestral_widget_ids]
            ancestral_connected_widget_ids = set()
            for ancestral_widget_id in ancestral_widget_ids:
                ancestral_connected_widget_ids.update(Widget.get_nested_connected_widget_ids(ancestral_widget_id))
            additional_tags += [Widget.get_cache_tag_by_pk(pk) for pk in ancestral_connected_widget_ids]
            widget_ids.update(ancestral_widget_ids, ancestral_connected_widget_ids)
        cache_key = get_func_cache_key(self.get_widgets, self)
        tag_key(additional_tags, cache_key)

        return Widget.objects.filter(id__in=widget_ids)

    def get_ancestoral_template_widget_ids(self):
        template_widget_ids = set()

        current_template = self
        while current_template is not None:
            template_widget_ids.update(set(current_template.template_widgets.values_list('id', flat=True)))
            current_template = current_template.parental_template

        return template_widget_ids

    def get_ancestoral_template_widgets(self, include_ancestoral=False):
        if include_ancestoral:
            return TemplateWidget.objects.filter(id__in=list(self.get_ancestoral_template_widget_ids()))
        return self.template_widgets.all()

    def _validate_not_circular(self, children=None):
        """
        Report circularity  between a pair of ancestors on addition/change of parental_template.
        """

        if self.parental_template:
            if not children:
                children = [self]
            else:
                children.append(self)

            if self.parental_template in children:
                return False
            if not self.parental_template._validate_not_circular(children):  # pylint: disable=protected-access
                return False
        return True

    def clean(self):
        """
        Performs circularity prevention, :class:`TemplateBlock` assignment restricting, and auto name assignment.

        Specifically:
            * Prevents circular references between chains of :class:`Template` objects.
            * Prevents removal of parental :class:`Template` from a :class:`Template` with multiple :class:`TemplateBlock`
              objects.
            * Auto assigns name 'Root' to a :class:`TemplateBlock` belong to a :class:`Template` with no parental
              :class:`Template`.

        Notes:
            * Auto assigning of :class:`TemplateBlock` name is duplicated (it is additionally found at the
              :class:`TemplateBlock` level) to catch any cases in which a nonroot :class:`Template` becomes one
              due to the removal of its parental :class:`Template`.
        """
        super().clean()

        # this is run pre_save, since relationship is assessed upward.
        if not self._validate_not_circular():
            raise ValidationError(
                {
                    'parental_template': f'Can not set specified parent of {self} as it leads to a circular reference'
                    ' Template inheritance.'
                }
            )

        if self.parental_template and self.parental_template.frontend != self.frontend:
            raise ValidationError(
                {
                    'parental_template': f"Can not set specified parent {self.parental_template} "
                    "of {self} as it uses frontend {self.parental_template.frontend} "
                    "and the current template uses {self.frontend}"
                }
            )

        if not all([self.frontend == widget.frontend for widget in self.template_widgets.all()]):
            raise ValidationError(
                {'template': f"Can not set frontend {self.frontend} as there are widget(s) using a different frontend"}
            )

        n_template_blocks = self.blocks.count()
        if n_template_blocks >= 1:
            if not self.parental_template:
                if n_template_blocks > 1:
                    raise ValidationError(
                        {
                            'parental_template': f'Since template: {self.name}, has more than one'
                            'template_block, it must have a parental_template'
                        }
                    )
                block = self.blocks.first()
                block.name = 'Root'
                block.save()

    def is_ready(self, language):
        """
        Confirms each :class:`TemplateBlock` belonging to :class:`Template` and its ancestors has a
        :class:`TemplateBlockTranslation` with :class:`Language`
        matching the primary :class:`Language` of its parental :class:`Template`.

        Returns:
            error Union[bool, string]
        """
        if not self.blocks.exists():
            return (False, f'No block exists for {self.__class__}: {self}')
        for block in self.blocks.all():
            block_ready, message = block.is_ready(language)
            if not block_ready:
                return (False, message)
        if self.parental_template:
            return self.parental_template.is_ready(language)
        return (True, None)

    def _invalidate_related_tags(self, history):
        for child_template in self.child_templates.all():
            child_template.invalidate_tags(history)
        for stage_template in self.stage_templates.all():
            stage_template.invalidate_tags(history)

    def render_web(self, language):
        template_widget_names = set()
        current_template = self

        while current_template.parental_template_id:
            template_widget_names.update(current_template.template_widgets.values_list('name', flat=True))
            current_template = current_template.parental_template

        return render_to_string(
            "react-spa/Template.js",
            context={
                "template": self,
                "theme": "{}",
                "template_widget_names": [],  # list(template_widget_names),
                "root_block_name": self.get_root_block().name,
                "blocks": self.get_blocks(language),
            },
        )

    def render_sms(self, hand):
        pass
