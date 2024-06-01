from django.db import models
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _

from languages_plus.models import Language
from model_utils import Choices
import reversion

from ery_backend.base.mixins import BlockHolderMixin, ReactNamedMixin, TranslationHolderMixin
from ery_backend.base.models import EryPrivileged, EryNamedPrivileged
from ery_backend.templates.models import Template
from ery_backend.modules.models import ModuleDefinitionNamedModel, ModuleDefinitionWidget


class StageBreadcrumb(models.Model):
    previous_breadcrumb = models.ForeignKey(
        'stages.StageBreadcrumb',
        on_delete=models.SET_NULL,
        related_name='last_crumb',
        null=True,
        blank=True,
        help_text="Records last instance in chain",
    )
    next_breadcrumb = models.ForeignKey(
        'stages.StageBreadcrumb',
        on_delete=models.SET_NULL,
        related_name='next_crumb',
        null=True,
        blank=True,
        help_text="Records next instance in chain",
    )
    stage = models.ForeignKey(
        'stages.Stage', on_delete=models.CASCADE, help_text="Current location of :class:`~ery_backend.hands.models.Hand`"
    )
    hand = models.ForeignKey(
        'hands.Hand',
        on_delete=models.CASCADE,
        help_text="Player (:class:`~ery_backend.users.models.User` or :class:`~ery_backend.robots.models.Robot`) tracked"
        " through a :class:`~ery_backend.stints.models.Stint`",
    )


@reversion.register
class StageTemplateBlockTranslation(EryPrivileged):
    """
    Unit of :class:`StageTemplateBlock` describing the language for rendering :class:`~ery_backend.frontends.models.Frontend`.
    """

    class Meta(EryPrivileged.Meta):
        unique_together = ('stage_template_block', 'language')

    def __str__(self):
        return f"{self.stage_template_block}-Translation:{self.language}"

    parent_field = 'stage_template_block'
    stage_template_block = models.ForeignKey(
        'stages.StageTemplateBlock', on_delete=models.CASCADE, help_text="Parental instance", related_name='translations'
    )
    language = models.ForeignKey(Language, on_delete=models.CASCADE, help_text="Used to render content")
    content = models.TextField(
        null=True,
        blank=True,
        help_text="Content to be rendered as part of :class:`StageDefinition` (connected through :class:`StageTemplate`).",
    )
    frontend = models.ForeignKey('frontends.Frontend', on_delete=models.PROTECT, default=1)

    @staticmethod
    def get_bxml_serializer():
        from .serializers import StageTemplateBlockTranslationBXMLSerializer

        return StageTemplateBlockTranslationBXMLSerializer

    @staticmethod
    def get_duplication_serializer():
        from .serializers import StageTemplateBlockTranslationDuplicationSerializer

        return StageTemplateBlockTranslationDuplicationSerializer

    @staticmethod
    def get_mutation_serializer():
        from .serializers import StageTemplateBlockTranslationMutationSerializer

        return StageTemplateBlockTranslationMutationSerializer


@reversion.register
class StageTemplateBlock(EryNamedPrivileged, ReactNamedMixin, TranslationHolderMixin):
    """
    Describes how :class:`StageDefinition` should be rendered.

    Attributes:
        parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.

    Notes:
        * Given the highest priority out of all blocks (i.e., :class:`StageTemplateBlock` and
          :class:`~ery_backend.templates.models.TemplateBlock`).
          Thus, the :class:`StageTemplateBlock` object obtained via :class:`StageDefinition`.get_blocks
          of preferred :class:`Language` and :class:`~ery_backend.frontends.models.Frontend` will override any matching
          content from the relevant set of :class:`~ery_backend.templates.models.TemplateBlock` objects.
        * Whereas a :class:`TemplateBlock` is :class:`StageDefinition` agnostic, a :class:`StageTemplateBlock` should be
          implemented only to describe content unique to its :class:`StageDefinition`.
    """

    class Meta(EryNamedPrivileged.Meta):
        unique_together = (('stage_template', 'name'),)

    class SerializerMeta(EryNamedPrivileged.SerializerMeta):
        model_serializer_fields = ('translations',)

    parent_field = 'stage_template'

    stage_template = models.ForeignKey(
        'stages.StageTemplate',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Parental instance",
        related_name='blocks',
    )

    @property
    def admin_name(self):
        return self.stage_template.stage_definition.name


class StageTemplate(BlockHolderMixin, EryPrivileged):
    """
    Custom intermediate model.

    Attributes:
        block_parent: Static declaration of name of related model overriden during
          :py:meth:`ery_backend.base.mixins.BlockHolderMixin.get_blocks`.
        parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.

    """

    class SerializerMeta(EryPrivileged.SerializerMeta):
        model_serializer_fields = ('blocks',)

    parent_field = 'stage_definition'
    block_parent = 'template'

    stage_definition = models.ForeignKey('stages.StageDefinition', on_delete=models.CASCADE, related_name='stage_templates')
    template = models.ForeignKey('templates.Template', on_delete=models.CASCADE, related_name='stage_templates')
    theme = models.ForeignKey('themes.Theme', on_delete=models.SET_NULL, null=True, blank=True, related_name='stage_templates')

    def __str__(self):
        return "StageTemplate: {}{}".format(self.template.frontend, "{}:{}".format(self.__class__.__name__, self.pk))

    @property
    def module_definition(self):
        return self.stage_definition.module_definition

    @property
    def render_name(self):
        return self.stage_definition.name

    def post_save_clean(self):
        """
        Unique together verification on :class:`~ery_backend.frontends.models.Frontend` connected to
        :class:`~ery_backend.templates.models.Template`.

        Notes:
            * Since verifying :class:`~ery_backend.frontends.models.Frontend` uniqueness requires current
              :class:`StageTemplate` have an id, this check must be done post_save.

        Raises:
            ~ery_backend.base.exceptions.EryIntegrityError: An error occuring if :class:`~ery_backend.users.models.User`
              attempts to save multiple :class:`StageTemplate` where multiple
              :class:`~ery_backend.templates.models.Template` have the same
              :class:`~ery_backend.frontends.models.Frontend`.

        """
        unique, stage, frontend = self.stage_definition._check_frontend_uniqueness()  # pylint: disable=protected-access
        if not unique:
            self.delete()
            raise IntegrityError(f'StageDefinition: {stage}, contains more than one template with frontend: {frontend}')

    def save(self, *args, **kwargs):
        """
        Validates connection to :class:`~ery_backend.frontends.models.Frontend`.

        Args:
            *args (list): Arguments used by inherited save method.
            **kwargs (dict): Keyword arguments used by inherited save method.

        Notes:
            * Overrides inherited save from :class:`~ery_backend.base.models.EryModel`.
        """
        super().save(*args, **kwargs)
        self.post_save_clean()

    def get_module_widgets(self):
        return ModuleDefinitionWidget.objects.filter(module_definition=self.module_definition)

    def get_template_widgets(self):
        from ery_backend.templates.models import TemplateWidget

        return TemplateWidget.objects.filter(template=self.template)

    def get_widgets(self):
        """
        Generate queryset containing all :class:`ery_backend.widgets.models.Widget` instances connected to
        :class:`~ery_backend.stints.models.StintDefinition`.

        Returns:
            :class:`django.db.models.query.Queryset`
        """
        from ery_backend.widgets.models import Widget, WidgetConnection

        widget_ids = set()
        for form in self.module_definition.forms.all():
            for item in form.items.exclude(field=None):
                widget_ids.add(item.field.widget.id)

        widget_ids.update(self.get_module_widgets().values_list("widget__id", flat=True))
        widget_ids.update(self.get_template_widgets().values_list("widget__id", flat=True))

        widget_dependency_ids = set(
            WidgetConnection.objects.filter(originator__id__in=widget_ids).values_list("target__id", flat=True)
        )

        prev_widget_dependency_ids = None
        while prev_widget_dependency_ids != widget_dependency_ids:
            prev_widget_dependency_ids = widget_dependency_ids
            widget_dependency_ids = widget_dependency_ids.union(
                WidgetConnection.objects.filter(originator__id__in=widget_dependency_ids).values_list("target__id", flat=True)
            )
        widget_ids = widget_ids.union(widget_dependency_ids)

        return Widget.objects.filter(id__in=widget_ids, frontend=self.template.frontend)

    def render(self, hand):
        """

        Generate a view (to be used during production/full testing) for the given model instance.

        Notes:
            - Blockholders cannot be rendered on the web without being part of a :class:`~ery_backend.stints.models.Stint`.
              To view web content for a Blockholder, use the preview method.

        Returns:
            str: ES6/ES5/Text (based on frontend) to be rendered in runner.
        """
        if hand.frontend.name in ['SMS']:
            return self.render_sms(hand)
        if hand.frontend.name == 'Web':
            return self.render_web(hand.language)

        raise NotImplementedError(
            f'No method exists for rendering {self} for {hand.frontend}.' ' Try using the preview method instead.'
        )

    def render_web(self, language):
        from ery_backend.frontends.renderers import ReactStageRenderer

        template_widgets = set()

        current_template = self.template
        template_widgets.update(current_template.template_widgets.all())
        while current_template.parental_template_id:
            current_template = current_template.parental_template
            template_widgets.update(current_template.template_widgets.all())

        return ReactStageRenderer(self, language).render()

    def render_sms(self, hand):  # Should not need hand, or render_web should use hand too.
        """
        Compile string from all blocks relevant to :class:`~ery_backend.StageTemplate`.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides contextual information needed for
              render.
        Returns:
            str
        """
        from ery_backend.frontends.sms_utils import SMSStageTemplateRenderer

        return SMSStageTemplateRenderer(self, hand).render()


class StageDefinition(ModuleDefinitionNamedModel, ReactNamedMixin):
    """
    Defines what should be rendered on :class:`~ery_backend.frontends.models.Frontend`.

    Notes:
        - Renders a combination of :class:`~ery_backend.templates.models.Template`, which are styled via \
          :class:`~ery_backend.themes.models.Theme`.
        - May define a pre :class:`~ery_backend.actions.models.Action`, \
          which is run via :py:meth:`ery_backend.actions.models.Action.run` \
          before the :class:`StageDefinition` is rendered.
        -  May be flagged as an end_stage to signal the end of a connected :class:`~ery_backend.modules.models.Module`.
        - A :class:`StageDefinition` must also have a :class:`~ery_backend.templates.models.Template` connected (via \
          :class:`StageTemplate`). A default is always assigned on save if another does not exist.
    """

    class SerializerMeta(ModuleDefinitionNamedModel.SerializerMeta):
        model_serializer_fields = ('redirects', 'stage_templates')
        exclude = ('templates',)

    BREADCRUMB_TYPE_CHOICES = Choices(
        ('none', _('No Breadcrumbs')), ('back', _('Back Breadcrumbs Only')), ('all', _('All Breadcrumbs'))
    )

    parent_field = 'module_definition'
    module_definition = models.ForeignKey(
        'modules.ModuleDefinition',
        on_delete=models.CASCADE,
        related_name='stage_definitions',
        help_text="The module definition this StageDefinition belongs to",
    )
    breadcrumb_type = models.CharField(
        choices=BREADCRUMB_TYPE_CHOICES,
        max_length=8,
        default=BREADCRUMB_TYPE_CHOICES.all,
        help_text=(
            "Indicates whether to create :class:`StageBreadCrumb`"
            "when :class:`StageDefinition` is assigned via"
            " :py:meth:`Hand.set_stage`"
        ),
    )
    end_stage = models.BooleanField(
        default=False, help_text="Indicates the end of the connected :class:`~ery_backend.modules.models.Module`"
    )
    templates = models.ManyToManyField(
        Template,
        through='stages.StageTemplate',
        help_text="Connected :class:`~ery_backend.templates.models.Template` instances",
    )
    pre_action = models.ForeignKey(
        'actions.Action',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=":class:`~ery_backend.actions.models.Action` run before rendering",
    )
    redirect_on_submit = models.BooleanField(default=True, help_text="Whether to execute redirect on submit event_type.")

    def _check_frontend_uniqueness(self):
        """
        Confirms that every template connected to stage through stagetemplate is connected to a unique
            frontend.
        Note: Due to use in stagetemplate.save(), returns result of uniqueness check, self, and
            frontend that fails uniqueness check for error reporting.
        """
        templates = set(stagetemplate.template for stagetemplate in self.stage_templates.all() if stagetemplate.template)
        seen = []
        for template in templates:
            if template.frontend not in seen:
                seen.append(template.frontend)
            else:
                return False, self, template.frontend
        return True, None, None

    def get_template_widgets(self, frontend):
        from ery_backend.templates.widgets import TemplateWidget

        template = self.templates.get(frontend=frontend)

        template_widget_ids = list(template.template_widgets.values_list('id', flat=True))
        while template.parental_template:
            template = template.parental_template
            template_widget_ids += list(template.template_widgets.values_list('id', flat=True))

        return TemplateWidget.objects.filter(id__in=template_widget_ids)

    def get_module_widgets(self, frontend):
        module_definition_widget_ids = self.module_definition.module_widgets.values_list('id', flat=True)
        return ModuleDefinitionWidget.objects.filter(id__in=module_definition_widget_ids)

    def get_blocks(self, hand):
        """
        Gets info on highest priority :class:`StageTemplateBlock` or
        :class:`~ery_backend.templates.models.TemplateBlock` given :class:`~ery_backend.frontends.models.Frontend`
        and :class:`Language` connected to :class:`~ery_backend.hands.models.Hand`.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Used to obtain
              :class:`ery_backend.frontends.models.Frontend` (which filters all
              :class:`~ery_backend.template.models.TemplateBlock`, such that block must be connected to
              :class:`~ery_backend.templates.models.Template` with given :class:`~ery_backend.frontends.models.Frontend`)
              and :class:`Language` (in order to prioritize all blocks of either type).

        Returns:
            A Dict mapping (str) keys (in the form of lowercase :class:`StageTemplateBlock` or
            :class:`~ery_backend.templates.models.TemplateBlock` names) to (str) content of the given block.

        Notes:
            * :class:`~ery_backend.template.models.TemplateBlock` are prioritized by :class:`Language`, then immediacy
              (blocks further downstream preferred over those upstream).
            * :class:`StageTemplateBlock` are prioritized by :class:`Language`.
            * :class:`StageTemplateBlock` are always prioritized over :class:`~ery_backend.template.models.TemplateBlock`.
        """
        stage_template = self.stage_templates.filter(template__frontend=hand.frontend).first()
        if stage_template:
            return stage_template.get_blocks(hand.frontend, hand.language)
        raise ValueError(f"No StageTemplate exists for {self} with frontend: {hand.frontend}")

    def render(self, hand):
        """
        Generate an ES5 based view for the given model instance.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context (i.e., desired
              :class:`ery_backend.frontends.models.Frontend`, :class:`Language`, and :class:`Variable`
              needed for content creation.

        Returns:
            str: ES5 javascript which includes :class:`ery_backend.users.models.User` based content and the react module
            code needed to render said content in the form of ES6 components.
        """
        stage_template = self.stage_templates.filter(template__frontend=hand.frontend).first()
        if stage_template:
            return stage_template.render(hand)
        raise ValueError(f"No StageTemplate exists for {self} with frontend: {hand.frontend}")

    def get_template(self, frontend):
        """
        Get :class:`~ery_backend.templates.models.Template` connected to :class:`StageDefinition`.

        Args:
            frontend (:class:`~ery_backend.frontends.models.Frontend`): Filters
              :class:`~ery_backend.templates.models.Template`

        Returns:
            :class:`~ery_backend.templates.models.Template`
        """
        return self.stage_templates.get(template__frontend=frontend).template

    # XXX: Address in issue #505
    def update_breadcrumbs(self):
        """
        Fix lost references of :class:`StageBreadcrumb` instances caused by deletion of a :class:`Stage`.
        """

        def _update_hand(breadcrumb):
            """
            Reconnect hand to latest breadcrumb
            """
            hand = breadcrumb.hand
            if breadcrumb == hand.current_breadcrumb:
                next_breadcrumb = breadcrumb.next_breadcrumb
                previous_breadcrumb = breadcrumb.previous_breadcrumb
                if next_breadcrumb:
                    hand.current_breadcrumb = next_breadcrumb
                elif previous_breadcrumb:
                    hand.current_breadcrumb = previous_breadcrumb
                else:
                    hand.current_breadcrumb = None
                hand.save()

        def _update_breadcrumb(breadcrumb):
            _update_hand(breadcrumb)
            previous_breadcrumb = breadcrumb.previous_breadcrumb
            next_breadcrumb = breadcrumb.next_breadcrumb
            if previous_breadcrumb and next_breadcrumb:
                if previous_breadcrumb.stage.stage_definition.breadcrumb_type == self.BREADCRUMB_TYPE_CHOICES.all:
                    previous_breadcrumb.next_breadcrumb = next_breadcrumb
                    previous_breadcrumb.save()
                if next_breadcrumb.stage.stage_definition.breadcrumb_type in [
                    self.BREADCRUMB_TYPE_CHOICES.back,
                    self.BREADCRUMB_TYPE_CHOICES.all,
                ]:
                    next_breadcrumb.previous_breadcrumb = previous_breadcrumb
                    next_breadcrumb.save()
            else:
                if previous_breadcrumb:
                    previous_breadcrumb.next_breadcrumb = None
                    previous_breadcrumb.save()
                elif next_breadcrumb:
                    next_breadcrumb.previous_breadcrumb = None
                    next_breadcrumb.save()

        for stage in self.stage_set.all():
            breadcrumbs = stage.stagebreadcrumb_set
            for breadcrumb in breadcrumbs.all():
                _update_breadcrumb(breadcrumb)

    def delete(self, **kwargs):
        """
        Add correction of :class:`StageBreadcrumb` references.

        Args:
            *args: Used in default django delete method.
            **kwargs: Used in default django delete method.
        """
        self.update_breadcrumbs()
        super().delete(**kwargs)

    def realize(self):
        """
        Instatiate a :class:`Stage` instance.
        """
        stage = Stage.objects.create(stage_definition=self)
        return stage

    def get_redirect_stage(self, hand):
        """
        Get next_stage_definition for first matching :class:`~ery_backend.stages.models.Redirect`.

        Returns:
            :class:`StageDefinition`
        """
        redirects = self.redirects.select_related('condition').order_by('order').all()
        for redirect in redirects:
            if not redirect.condition or redirect.condition.evaluate(hand):
                return redirect.next_stage_definition
        raise StageDefinition.DoesNotExist("No matching redirect exists or passes the condition requirements to be used.")

    def submit(self, hand):
        """
        Initiates submit action for :class:`~ery_backend.hands.models.Hand` instances current
        :class:`~ery_backend.stages.models.Stage`.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`)
        """
        if self.redirect_on_submit:
            if self.breadcrumb_type == self.BREADCRUMB_TYPE_CHOICES.all and hand.current_breadcrumb.next_breadcrumb:
                hand.set_stage(hand.current_breadcrumb.next_breadcrumb.stage)
                hand.set_breadcrumb(hand.current_breadcrumb.next_breadcrumb)
            else:
                hand.set_stage(stage_definition=self.get_redirect_stage(hand))
                new_breadcrumb = hand.create_breadcrumb(hand.stage)
                hand.set_breadcrumb(new_breadcrumb)


class Stage(EryPrivileged):
    """
    Instantiation of :class:`StageDefinition` for use in a running :class:`~ery_backend.stints.models.Stint`.

    Attributes:
        - parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.

    """

    parent_field = 'stage_definition'
    stage_definition = models.ForeignKey('stages.StageDefinition', on_delete=models.CASCADE, help_text="Parental instance")
    preaction_started = models.BooleanField(
        default=False, help_text="Tracks execution of :py:meth:`StageDefinition.pre_action`"
    )

    def run_preaction(self, hand):
        """
        Execute :class:`Stage` instance's connected :class:`~ery_backend.actions.models.Action`.

        Args:
            - hand (:class:`~ery_backend.hand.models.Hand`): Provides context variables to :class:`Action`.
        """
        if self.stage_definition.pre_action is not None:
            self.stage_definition.pre_action.run(hand)
            self.preaction_started = True
            self.save()

    def render(self, hand):
        """
        Generate an ES5 based view for the given model instance. Run :class:`Stage` pre_action (applicable).

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context (i.e., desired
              :class:`ery_backend.frontends.models.Frontend`, :class:`Language`, and :class:`Variable` instances
              needed for content creation.

        Returns:
            str: ES5 javascript which includes :class:`ery_backend.users.models.User` based content and the react module
            code needed to render said content in the form of ES6 components.

        """
        return self.stage_definition.render(hand)

    def _invalidate_related_tags(self, history):
        pass


class Redirect(EryPrivileged):
    """
    Connects :class:`StageDefinition` instances.
    """

    parent_field = 'stage_definition'

    stage_definition = models.ForeignKey('stages.StageDefinition', on_delete=models.CASCADE, related_name='redirects')
    order = models.PositiveIntegerField(default=0, help_text="Order of execution")
    next_stage_definition = models.ForeignKey(
        'stages.StageDefinition', on_delete=models.CASCADE, related_name='redirectTargets'
    )
    condition = models.ForeignKey(
        'conditions.Condition', on_delete=models.CASCADE, null=True, blank=True, help_text="Condition of execution"
    )

    def clean(self):
        if self.stage_definition.module_definition != self.next_stage_definition.module_definition:
            raise IntegrityError(
                {
                    'next_stage_definition': f"Redirect for {self.stage_definition} cannot connect to a"
                    " different ModuleDefinition than"
                    f" {self.stage_definition.module_definition}"
                }
            )
        super().clean()
