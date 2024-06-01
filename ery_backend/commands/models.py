from django.db import models
from django.db.utils import IntegrityError

from languages_plus.models import Language

from ery_backend.base.cache import ery_cache
from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.mixins import BlockHolderMixin, ReactNamedMixin, TranslationHolderMixin, JavascriptNamedMixin
from ery_backend.base.models import EryNamedPrivileged, EryPrivileged
from ery_backend.modules.models import ModuleDefinitionNamedModel


class Command(ModuleDefinitionNamedModel, JavascriptNamedMixin):
    """
    Make associated :class:`~ery_backend.actions.models.Action` instance triggerable across
    :class:`~ery_backend.modules.models.ModuleDefinition`.
    """

    class SerializerMeta(ModuleDefinitionNamedModel.SerializerMeta):
        model_serializer_fields = ('command_templates',)

    parent_field = 'module_definition'
    action = models.ForeignKey(
        'actions.Action', on_delete=models.CASCADE, null=True, blank=True, related_name='triggering_commands'
    )
    trigger_pattern = models.CharField(max_length=100)

    def _check_frontend_uniqueness(self):
        """
        Confirms that every template connected to command through commandcommandtemplate.command_template
            is connected to a unique frontend.
        Note: Due to use in commandcommandtemplate.save(), returns result of uniqueness check, self, and
            frontend that fails uniqueness check for error reporting.
        """
        templates = set(command_template.template for command_template in self.command_templates.all())
        seen = []
        for template in templates:
            if template.frontend not in seen:
                seen.append(template.frontend)
            else:
                return False, self, template.frontend
        return True, None, None

    def render(self, hand):
        """
        Generate a text based view for the given model instance.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context (i.e., desired
              :class:`ery_backend.frontends.models.Frontend`, :class:`Language`, and :class:`Variable`
              instances needed for content creation.

        Returns:
            str: Text which includes :class:`ery_backend.users.models.User` based content.
        """
        command_template = self.command_templates.filter(template__frontend=hand.frontend).first()
        if command_template:
            if hand.frontend.name == 'Web':
                return command_template.render_web(hand.language)
            return command_template.render_sms(hand)
        raise EryValidationError(f"No CommandTemplate exists for {self} with frontend: {hand.frontend}")


class CommandTemplate(BlockHolderMixin, EryPrivileged):
    """
    Custom intermediate model connecting :class:`CommandTemplateBlock` instances to a parental
    :class:`~ery_backend.templates.models.Template`.

    Attributes:
        block_parent: Static declaration of name of related model overriden during
          :py:meth:`ery_backend.base.mixins.BlockHolderMixin.get_blocks`.
        parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.
    """

    class SerializerMeta(EryPrivileged.SerializerMeta):
        model_serializer_fields = ('blocks',)

    block_parent = 'template'
    parent_field = 'command'
    command = models.ForeignKey(
        'commands.Command', on_delete=models.CASCADE, related_name='command_templates', help_text="Parental instance."
    )
    template = models.ForeignKey(
        'templates.Template',
        on_delete=models.CASCADE,
        related_name='command_templates',
        help_text="Parental instance for child :class:`CommandTemplateBlock` instances",
    )

    def get_frontend(self):
        """
        Gets connected :class:`~ery_backend.frontends.models.Frontend`.

        Returns:
            :class:`~ery_backend.frontends.models.Frontend`
        """
        return self.template.get_frontend()

    def render_sms(self, hand):
        """
        Compile string from all blocks relevant to :class:`CommandTemplate`.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides contextual information needed for
              render.
        Returns:
            str
        """
        from ery_backend.frontends.sms_utils import SMSCommandTemplateRenderer

        return SMSCommandTemplateRenderer(self, hand).render()

    @ery_cache
    def render_web(self, language):
        from ery_backend.frontends.models import Frontend

        Frontend.object.get(name='Web')
        raise NotImplementedError

    def post_save_clean(self):
        """
        Unique together verification on :class:`~ery_backend.frontends.models.Frontend` connected to
        :class:`~ery_backend.templates.models.Template`.

        Notes:
            * Since verifying :class:`~ery_backend.frontends.models.Frontend` uniqueness requires current
              :class:`CommandTemplate` have an id, this check must be done post_save.

        Raises:
            ~ery_backend.base.exceptions.EryIntegrityError: An error occuring if :class:`~ery_backend.users.models.User`
              attempts to save multiple :class:`CommandTemplate` where multiple connected
              :class:`~ery_backend.templates.models.Template` have the same
              :class:`~ery_backend.frontends.models.Frontend`.

        """
        unique, command, frontend = self.command._check_frontend_uniqueness()  # pylint: disable=protected-access
        if not unique:
            self.delete()
            raise IntegrityError(f'Command: {command}, contains more than one template with frontend: {frontend}')


class CommandTemplateBlock(EryNamedPrivileged, ReactNamedMixin, TranslationHolderMixin):
    """
    Describes how :class:`Command` should be rendered.

    Attributes:
        parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.
    Notes:
        * Given the highest priority out of all blocks (i.e., :class:`CommandTemplateBlock` and
          :class:`~ery_backend.templates.models.TemplateBlock`).
          Thus, the :class:`CommandTemplateBlock` object obtained via :class:`StageDefinition`.get_blocks
          of preferred :class:`Language` and :class:`~ery_backend.frontends.models.Frontend` will override any matching
          content from the relevant set of :class:`~ery_backend.templates.models.TemplateBlock` objects.
        * Whereas a :class:`TemplateBlock` is :class:`Command` agnostic, a :class:`CommandTemplateBlock` should be
          implemented only to describe content unique to its :class:`Command`.
    """

    class Meta(EryNamedPrivileged.Meta):
        unique_together = (('command_template', 'name'),)

    class SerializerMeta(EryNamedPrivileged.SerializerMeta):
        model_serializer_fields = ('translations',)

    parent_field = 'command_template'

    command_template = models.ForeignKey(
        'commands.CommandTemplate', on_delete=models.CASCADE, help_text="Parental instance", related_name='blocks'
    )

    def save(self, *args, **kwargs):
        """
        Validates :class:`CommandTemplateBlockTranslation`.

        Specifically, confirms that a :class:`CommandTemplateBlockTranslation` exists for the default :class:`Language` of the
        connected :class:`Command`, and creates one otherwise.

        Args:
            *args (list): Arguments used by inherited save method.
            **kwargs (dict): Keyword arguments used by inherited save method.

        Notes:
            * Overrides inherited save from :class:`~ery_backend.base.models.EryModel`
        """
        self.clean()
        super().save(*args, **kwargs)

    def get_translation(self, frontend, language):
        """
        Gets :class:`CommandTemplateBlockTranslation` of specified :class:`Language`.

        If :class:`CommandTemplateBlockTranslation` does not exist for specified :class:`Language`,
        gets :class:`CommandTemplateBlockTranslation` for default :class:`Language` of connected
        :class:`~ery_backend.modules.models.ModuleDefinition`.

        Args:
            - frontend (:class:`~ery_backend.frontends.models.Frontend`): Used to filter
              :class:`CommandTemplateBlockTranslation`.
            - language (:class:`Language`): Used to filter :class:`CommandTemplateBlockTranslation`.

          Notes:
            - Arg, frontend, is optional because not all models with translations,
              (e.g., :class:`~ery_backend.modules.models.WidgetChoice`), allow filtering by
              :class:`~ery_backend.frontends.models.Frontend`. For these models, only :class:`Language` is required.

        Returns:
            :class:`CommandTemplateBlockTranslation`.
        """
        return super().get_translation(frontend, language).content


class CommandTemplateBlockTranslation(EryPrivileged):
    """
    Unit of :class:`CommandTemplateBlock` describing the language for rendering
    :class:`~ery_backend.frontends.models.Frontend`.
    """

    class Meta(EryPrivileged.Meta):
        unique_together = (('command_template_block', 'language', 'frontend'),)

    def __str__(self):
        return f"{self.command_template_block}-Translation:{self.language}"

    @staticmethod
    def get_bxml_serializer():
        from .serializers import CommandTemplateBlockTranslationBXMLSerializer

        return CommandTemplateBlockTranslationBXMLSerializer

    parent_field = 'command_template_block'
    command_template_block = models.ForeignKey(
        'commands.CommandTemplateBlock', on_delete=models.CASCADE, related_name='translations', help_text="Parental instance"
    )
    language = models.ForeignKey(Language, on_delete=models.CASCADE, help_text="Used to render content")
    frontend = models.ForeignKey(
        'frontends.Frontend', on_delete=models.PROTECT, default=1, related_name='command_template_block_translations'
    )
    content = models.TextField(
        help_text="Content to be rendered as part of :class:`Command` (connected through :class:`CommandTemplate`)."
    )
