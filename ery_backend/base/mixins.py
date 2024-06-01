import random
import re
import string

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models

import graphene
from model_utils import Choices

from .exceptions import EryValueError, EryValidationError


class SluggedMixin(models.Model):
    """
    Mixin adding slug and punctuation cls attributes, as well as slug auto-generation.
    """

    class Meta:
        abstract = True

    slug_length = 8
    slug_separator = '-'
    slug_sub_expr = re.compile('[^a-zA-Z0-9]')

    # max_length determined by max_length of name + 8 random letters + dash + 100 chars headroom
    slug = models.CharField(max_length=621, null=False, blank=False, unique=True)

    def clean(self):
        """Default django method, with additional slug assignment (if necessary)."""
        if not self.slug:
            self.assign_slug()
        super().clean()

    @classmethod
    def create_unique_slug(cls, name):
        """
        Sets a unique slug for identification during import and duplication methods.

        Args:
            - cls (~ery_backend.base.models.ErySlugged): Model class of instance assigned slug.
            - name (str)
        """

        def create_slug(name):
            """
            Generates a slug using given name.

            Args:
            -  name (str)
            Returns:
                str: slug generated from name and randomly selected letters.
            """
            rand_str = ''.join([random.choice(string.ascii_letters) for i in range(cls.slug_length)])
            formatted_name = cls.slug_sub_expr.sub('', name)
            return f'{formatted_name}{cls.slug_separator}{rand_str}'

        slug = create_slug(name)
        while cls.objects.filter(slug=slug).exists():
            slug = create_slug(name)
        return slug

    def assign_slug(self, name=None):
        """
        Sets a unique slug for identification during import and duplication methods.

        Args:
            - name (Optional[str]): Slug prefix (included before random string).

        Notes:
            - Model is not saved in this method, which should be used as part of a save override.
        """
        if not name:
            name = self.name

        self.slug = self.create_unique_slug(name)


class NameValidationMixin(models.Model):
    """
    Adds basic name validation methods, with method for including additional validation.

    Attributes:
        allow_spaces (bool): Whether spaces are allowed in name.
        allow_underscores (bool): Whether underscores are allowed in name.
        allow_uppers (bool): Whether uppercased letters are allowed in name.

    Notes:
        Validation of the use of underscores and spaces within name is included in the
        clean method.
    """

    class Meta:
        abstract = True

    allow_underscores = True
    allow_spaces = True
    allow_uppers = True

    def _has_space(self):
        return ' ' in self.name

    def _has_upper(self):
        for letter in self.name:
            if letter.isupper():
                return True
        return False

    def _validate_underscores(self):
        if not self.allow_underscores and '_' in self.name:
            raise ValidationError(f"Underscores cannot be used when naming {self.__class__.__name__}s.")

    def _validate_spaces(self):
        if ' ' in self.name and not self.allow_spaces:
            raise ValidationError(f"Spaces cannot be used when naming {self.__class__.__name__}s.")

    def _validate_uppers(self):
        if self._has_upper() and not self.allow_uppers:
            raise ValidationError({'name': f" Name for {self} cannot contain uppercased letters."})

    def _starts_with_number(self):
        return self.name[0].isnumeric()

    def _starts_with_lower(self):
        return self.name[0].islower()

    def _validate(self):
        self._validate_underscores()
        self._validate_spaces()
        self._validate_uppers()

    def clean(self):
        """
        Default django method, with additional validation of name.

        Specifically
            - Underscores allowed only if model has allow_underscores = True
        """
        self._validate()
        super().clean()


class NamedMixin(NameValidationMixin):
    """Mixin providing name and comment to abstract models, and methods for model duplication."""

    class Meta:
        abstract = True
        ordering = ('name',)

    name = models.CharField(max_length=512, help_text="Name of the model instance.")

    comment = models.TextField(null=True, blank=True, help_text="Comment documenting the purpose of this model instance.")

    def __str__(self):
        return f"{self.name} ({self.pk})"

    def duplicate(self, name=None):
        """
        Returns:
            A duplicated model instance, with option of modifying attributes.

        Args:
            - name(str): If specified, the new name that will be used instead of the original.
            - replace_kwargs(Dict[str: Union[str, EryModel]]): If specified, key-value dictionary
              where key specifies attributes to be used instead of the original ones.
        """
        if not hasattr(self, 'get_duplication_serializer'):
            raise NotImplementedError(f"{self} has no get_duplication_serializer method!")

        serializer_cls = self.get_duplication_serializer()
        data = serializer_cls(instance=self).data

        if self.parent:
            data[self.parent_field] = self.parent.pk

        if not name:
            name = f"{self.name}{'_copy' if self.allow_underscores else 'Copy'}"

        data.update({'name': name, self._meta.pk.attname: None})

        return serializer_cls(data=data).validate_and_save()

    @classmethod
    def import_instance_from_xml(cls, xml, name=None):
        """
        Make model instance using data from xml file.

        Args:
            - xml (IO[bytes]: Used for creation of model instance.
            - name (Optional[str]): Replaces the name attribute of the new instance.

        Returns:
            model instance
        """

        model_serializer = cls.get_bxml_serializer()
        stream = xml.read()
        decoded_data = model_serializer.xml_decode(stream)
        replace_kwargs = {'name': name} if name else {}
        decoded_data.update(replace_kwargs)
        return model_serializer(data=decoded_data).validate_and_save()


class PrivilegedMixin(models.Model):
    """
    Establishes status as either a root model from which other descendants inherit privilege
        or one of those said descendants.
    """

    class Meta:
        abstract = True

    def get_privilege_ancestor(self):
        """Return root ancestor from which privileges are inherited for permissions checking."""
        if self.parent:
            privilege_ancestor = self.parent.get_privilege_ancestor()
            return privilege_ancestor
        return self

    @classmethod
    def get_privilege_ancestor_cls(cls):
        """
        Return class of root ancestor from which privileges are inherited for permissions checking.

        Returns:
            :class:`~ery_backend.base.models.EryModel`
        """
        if cls.parent_field:
            privilege_ancestor_cls = cls._meta.get_field(cls.parent_field).related_model.get_privilege_ancestor_cls()
            return privilege_ancestor_cls
        return cls

    @classmethod
    def _get_privilege_ancestor_path(cls):
        """
        Return a string joining all the parent_field_str returns between the current class
            and the privilege ancestor class.

        Returns:
            str
        """
        strs = []
        if cls.parent_field:
            pp = cls._meta.get_field(cls.parent_field)
            upper_strs = pp.related_model._get_privilege_ancestor_path()  # pylint: disable=protected-access
            if upper_strs:
                strs += upper_strs
            strs.insert(0, cls.parent_field)
        return strs

    @classmethod
    def get_privilege_ancestor_filter_path(cls):
        """
        Return a string (formatted for use in an object manager's filter statement)
            connecting current model and root ancestor. Allows for querying the current class
            based on attributes of the privilege ancestor.

        Returns:
            str
        """
        linear_path_as_list = cls._get_privilege_ancestor_path()
        formatted_path = '__'.join(linear_path_as_list)
        return formatted_path

    def get_owner(self):
        """
        Find :class:`ery_backend.users.models.User` with ownership over current instance.

        Specifically:
            Get :class:`~ery_backend.users.models.User` belonging to first matched
            :class:`~ery_backend.roles.models.RoleAssignment` with owner :class:`~ery_backend.roles.models.Role`.

        Returns:
            :class:`ery_backend.users.models.User`

        """
        from ery_backend.roles.models import Role, RoleAssignment

        owner = Role.objects.get(name='owner')
        content_type = self.get_content_type()
        owner_role_assignment = (
            RoleAssignment.objects.filter(role=owner, content_type=content_type, object_id=self.id).exclude(user=None).first()
        )
        if owner_role_assignment:
            return owner_role_assignment.user
        return None


class JavascriptValidationMixin(NameValidationMixin):
    """
    Enforces javascript specific conventions on model.name.

    Specifically:
        1.  No illegal punctuation allowed in name.
        2.  Validation of legal javascript naming pattern.

    Attributes:
        allow_spaces (bool): Whether spaces are allowed in name.

    """

    class Meta:
        abstract = True

    allow_spaces = False

    def _has_js_illegal_punctuation(self):
        for char in self.name:
            if char in string.punctuation and char not in ['$', '_']:
                return True
        return False

    def _has_invalid_name(self):
        from ery_backend.validators.utils import js_valid_pattern

        return js_valid_pattern.match(self.name) is None

    def _validate(self):
        if self._has_js_illegal_punctuation():
            raise ValidationError(
                f"{self._meta.object_name } name for {self} cannot contain punctuation," " with the exception of '$' and '_'."
            )
        if self._has_invalid_name():
            raise ValidationError(
                f"{self._meta.object_name } name for {self} cannot be used because it is" " invalid or reserved by Javascript."
            )
        super()._validate()


class JavascriptNamedMixin(JavascriptValidationMixin):
    """
    Enforces JavaScript function naming conventions on model.name.

    Name convention rules:
        1.  No illegal punctuation allowed in name.
        2.  Validation of legal javascript naming pattern.
        3.  No spaces allowed in name.
        4.  No numbers allowed at beginning of name.

    Attributes:
        - allow_underscores (bool): Whether underscores are allowed in name.
    """

    class Meta:
        """Meta."""

        abstract = True

    allow_underscores = True
    allow_uppers = False


class ReactNamedMixin(JavascriptValidationMixin):
    """
    Enforces React naming conventions on model.name.

    Name convention rules:
        1. No punctuation allowed in name.
        2. Validation of legal javascript naming pattern.
        3. No spaces allowed in name.
        4. No numbers allowed at beginning of name.
        5. First letter must be capitalized.

    Attributes:
        allow_underscores (bool): Whether underscores are allowed in name.
    """

    class Meta:
        abstract = True

    allow_underscores = False

    def _validate(self):
        if self._starts_with_number() or self._starts_with_lower():
            raise EryValueError(f"{self.__class__.__name__} with name: '{self.name}', must start" " with a capital letter.")
        super()._validate()


class JavascriptArgumentNamedMixin(JavascriptNamedMixin):
    """
    Enforces JavaScript argument naming conventions on model.name.

    Name convention rules:
        1.  No illegal punctuation allowed in name.
        2.  Validation of legal javascript naming pattern.
        3.  No spaces allowed in name.
        4.  No numbers allowed at beginning of name.
    """

    class Meta:
        """Meta."""

        abstract = True


class TranslationHolderMixin(models.Model):
    """
    Adds methods for retireving associated translation objects.
    """

    class Meta:
        abstract = True

    def get_translation_by_frontend_language(self, frontend=None, language=None):
        """
        Get caption specified by given :class:`Frontend` and :class:`Language`.

        Args:
            - frontend (:class:`~ery_backend.frontends.models.Frontend`): Used to filter translation set.
            - language (:class:`Language`): Used to filter translation set.

        Returns:
            str: Translation model's caption.

        """
        try:
            if hasattr(self.translations.model, 'frontend'):
                return self.translations.get(frontend=frontend, language=language)
            return self.translations.get(language=language)
        except ObjectDoesNotExist:
            raise EryValidationError(
                f'No translation of language: {language}, exists for frontend: {frontend}, for {self.__class__}, {self}.'
                if hasattr(self.translations.model, 'frontend')
                else f'No translation of language: {language} for {self.__class__}, {self}.'
            )

    def get_translation(self, frontend, language):
        return self.get_translation_by_frontend_language(frontend, language)


class RenderMixin(models.Model):
    class Meta:
        abstract = True

    def render(self, hand):
        """
        Generate ES5 code or text (depending on :class:`~ery_backend.frontends.models.Frontend`) for given instance.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Gives context during render.
        Returns:
            str

        """
        raise NotImplementedError(f"Method not implemented")

    def render_web(self, language):
        """
        Generate ES5 code or text (depending on :class:`~ery_backend.frontends.models.Frontend`) for given instance.
        """
        raise NotImplementedError(f"Method not implemented for Web frontend")

    def render_sms(self, hand):
        """
        Generate ES5 code or text (depending on :class:`~ery_backend.frontends.models.Frontend`) for given instance.
        """
        raise NotImplementedError(f"Method not implemented for {hand.frontend}")


class BlockHolderMixin(RenderMixin):  # pylint: disable=abstract-method
    """
    Add methods for rendering via connected block models.

    Connected blocks contain content that is hierarchically overriden with the lowest blocks having
    the highest priority.

    Attributes:
        block_parent: Static declaration of name of related model overriden during
          :py:meth:`ery_backend.base.mixins.BlockHolderMixin.get_blocks`.
    """

    class Meta:
        abstract = True

    class BlockInfoNode(graphene.ObjectType):

        name = graphene.String()
        content = graphene.String()
        block_type = graphene.String()
        ancestor_template_id = graphene.ID()

    block_parent = None

    def get_root_block(self):
        """
        Get root model instance (ancestor of :class:`App` instance's originator).

        # XXX: Update in issue #397.
        Returns:
            Union[:class:`~ery_backend.template.models.TemplateBlock`,
                  :class:`~ery_backend.commands.models.CommandTemplateBlock`]
        """
        element = self
        while getattr(element, element.block_parent):
            element = getattr(element, element.block_parent)
        return element.blocks.first()

    @staticmethod
    def _get_server_side_evaluation_calls(block_content):
        regex_pattern = r'\{\{(.*?)\}\}'
        return re.findall(regex_pattern, block_content)

    @staticmethod
    def _replace_server_side_evaluation_call(block_content, match, eval_code):
        return block_content.replace(f'{{{{{match}}}}}', str(eval_code))

    @staticmethod
    def _escape_server_side_evaluation_call(block_content):
        # pylint:disable=anomalous-backslash-in-string
        return block_content.replace('\{\{', '{{').replace('\}\}', '}}')

    def evaluate_block(self, block_content, hand):
        """
        Perform server side eval as necessary on blocks.
        """
        # XXX: Address in issue #463
        # XXX: Further address in issue #708
        # from ery_backend.scripts.engine_client import evaluate_without_side_effects
        matches = self._get_server_side_evaluation_calls(block_content)
        for match in matches:
            # eval_code = evaluate_without_side_effects('block_ss_eval', match, hand)
            eval_code = block_content
            block_content = self._replace_server_side_evaluation_call(block_content, match, eval_code)
        # pylint:disable=anomalous-backslash-in-string
        return self._escape_server_side_evaluation_call(block_content)

    def get_local_blocks(self, frontend, language, raw=False):
        """
        Collects block info into dict.
        """
        return {
            block.name: {
                # Handle optional frontend in BlockHolder
                'content': block.get_translation_by_frontend_language(frontend, language).content,
                # XXX: Re-add evaluate_block(block.get_translation(frontend, language)) in issue #708
                # 'content': block.get_translation(frontend, language) if raw else evaluate_block(
                #     block.get_translation(frontend, language)),
                'block_type': block.__class__.__name__,
                'ancestor_id': block.get_privilege_ancestor().id,
                'ancestor': block.get_privilege_ancestor(),
            }
            for block in self.blocks.all()
        }

    def get_ancestor_blocks(self, frontend, language, raw=False):
        ancestral_blocks = {}

        if self.block_parent:
            block_model = getattr(self, self.block_parent)
            if block_model:
                ancestral_blocks.update(block_model.get_blocks_by_frontend_language(frontend, language, raw))

        return ancestral_blocks

    def get_blocks_by_frontend_language(self, frontend=None, language=None, raw=False):
        """
        Gets information regarding all block objects connected to model instance.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides
              :class:`~ery_backend.frontends.models.Frontend` used to filter connected
              :class:`~ery_backend.stages.models.StageTemplateBlock` and
              :class:`~ery_backend.templates.models.TemplateBlock` instances.
            - raw (boolean): If false, perform server side evaluation of blocks.

        Returns:
            dict: Model instance information. Keys represent the (str) lower cased name of each retrieved
            Model instance and values represent the names (user and formatted) and content of said block.
        """
        blocks = self.get_local_blocks(frontend, language, raw)
        blocks.update({k: v for (k, v) in self.get_ancestor_blocks(frontend, language, raw).items() if k not in blocks})

        return blocks

    def get_blocks(self, frontend, language):
        return self.get_blocks_by_frontend_language(frontend=frontend, language=language)

    def render(self, hand):
        """

        Generate a view (to be used during production/full testing) for the given model instance.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Gives context during render.

        Notes:
            - Blockholders cannot be rendered on the web without being part of a :class:`~ery_backend.stints.models.Stint`.
              To view web content for a Blockholder, use the preview method.

        Returns:
            str: Text to be rendered in SMSRunner.
        """
        if hand.frontend.name in ['SMS']:
            return self.render_sms(hand)
        if hand.frontend.name == 'Web':
            return self.render_web(hand.language)

        raise NotImplementedError(
            f'No method exists for rendering {self} for {hand.frontend}.' ' Try using the preview method instead.'
        )


#    def render_sms(self, frontend, language, context):
#        from ery_backend.frontends.sms_utils import SMSRenderer
#
#        blocks = self.get_blocks(hand.frontend, hand.language)
#        inputs = hand.current_module_definition.get_input_blocks(hand)
#        root_block = self._get_root_block()
#        root = SMSRenderer.create_tree(root_block.name, blocks[root_block.name], blocks, inputs)
#
#        return SMSRenderer.compile_sms_content(root)


class ChoiceMixin(TranslationHolderMixin):
    """
    Base class for obtaining info from a model's choice items.
    """

    class Meta:
        abstract = True

    def get_translation(self, language):
        """
        Get caption specified by given :class:`Language`.

        Args:
            - language (:class:`Language`): Used to filter translation set.

        Returns:
            str: Translation model's caption.
        """
        try:
            translation = self.translations.get(language=language)
            return translation.caption
        except self.translations.model.DoesNotExist:
            return self.value

    def get_info(self, language):
        """
        Get value and caption of specified :class:`Language`.

        Args:
            language (:class:`Language`): Used to filter translation.

        Returns:
            dict: Contains model value and caption from selected translation.

        Notes:
            - If translation matching specified :class:`Language` does not exist, default :class:`Language`
              as specified by parental :class:`~ery_backend.modules.models.ModuleDefinition` is used instead.
        """
        return {'value': self.value, 'caption': self.get_translation(language)}


class ChoiceHolderMixin:
    """
    Contains choices that can be ordered in various ways.
    """

    class Meta:
        abstract = True

    RANDOM_CHOICES = Choices(
        ('asc', "Order Ascending"),
        ('desc', "Order Descending"),
        ('shuffle', "Shuffle (once per display)"),
        ('random_asc_desc', "Order random ascending/descending (once per display)"),
    )

    @property
    def is_multiple_choice(self):
        """
        Confirm whether model instance can be rendered as a multiple choice widget.

        At least one :class:`WidgetChoice` must exist for this method to return True.

        Returns:
            bool: Indicates whether model instance can be rendered as a multiple choice widget.
        """
        from ery_backend.variables.models import VariableDefinition

        choice_type = VariableDefinition.DATA_TYPE_CHOICES.choice
        is_multiple_choice = self.choices.exists()
        if self.variable_definition and not is_multiple_choice:
            is_multiple_choice = self.variable_definition.data_type == choice_type
        return is_multiple_choice

    def get_choices(self, language=None):
        # pylint: disable=too-many-branches
        """
        Get set of :class:`WidgetChoice` object information.

        Returns:
            list: Consists of dicts representing :class:`WidgetChoice` value and
            :class:`Language` specific caption.

        Notes:
            - If no :class:`Language` is specified, the default of the connected
              :class:`~ery_backend.modules.models.ModuleDefinition` is used.
            - Because :class:`~ery_backend.variables.models.VariableChoiceItem` instances have no order,
              id is used in place of order if no :class:`WidgetChoice` items exist.
        """
        raise NotImplementedError

    def get_choices_as_extra_variable(self, language=None):
        """
        Gets choices as a dictionary to be added to the context of a protobuff JavascriptOp message.

        Args:
            - stint (:class:`~ery_backend.stints.models.Stint`): Passed to :py:meth:`ModuleDefinitionWidget.get_choices` \
              as seed for randomization
            - user (:class:`~ery_backend.users.models.User`): Passed to :py:meth:`ModuleDefinitionWidget.get_choices` \
              as seed for randomization.
            - language (:class:`Language`): Used to filter :class:`WidgetChoiceTranslation` captions.

        Returns:
            Dict
        """
        return {'choices': self.get_choices(language)}

    def validate(self, value):
        if self.choices.exists() and value not in self.choices.values_list('value', flat=True):
            raise EryValueError(f"{value} is not in {self.__class__}'s choice list")

        return self.variable_definition.validate(value)

    def clean(self):
        """
        Prevents save when doing so will violate :class:`~ery_backend.variables.models.VariableDefinition` related
        restrictions.

        Specifically, instance must have a connected
        :class:`~ery_backend.variables.models.VariableDefinition` of data_type (string) or (choice). Also, confirms
        choice object's value is a subset of the set of
        :class:`~ery_backend.variables.models.VariableChoiceItem` object values connected to
        instance.

        Raises:
            - :class:`TypeError`: An error occuring if :class:`~ery_backend.users.models.User`
                attempts to save an instance connected to
                :class:`~ery_backend.variables.models.VariableDefinition` not of data_type (string) or (choice).
            - :class:`ValueError`: An error occuring if choice restrictions
                are violated.
        """
        from ery_backend.variables.models import VariableDefinition

        super().clean()
        if self.variable_definition:
            choices = [data_type for data_type, _ in VariableDefinition.DATA_TYPE_CHOICES]
            if self.variable_definition.data_type not in choices:
                raise TypeError(
                    "Variable connected to widget through variable_definition field must have data_type"
                    f" in '{choices}',"
                    f" not '{self.variable_definition.data_type}'."
                )

            if self.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.choice:
                # XXX: Address in issue #813
                # if not self.variable_definition.variablechoiceitem_set.exists():
                #     raise ValidationError(
                #         f"No variable choice items exist for instance: {self},"
                #         f" with variable_definition: {self.variable_definition}."
                #     )
                for choice in self.choices.all():
                    choice.clean()


class LogMixin:
    """
    Add logging functionality to inheriting model.

    Notes:
        - Centralizes references needed for logging, such as log levels.
    """

    @staticmethod
    def log(message, creation_kwargs, logger, log_type=None, system_only=False):
        """
        Create log via Django logger and :class:`~ery_backend.logs.models.Log` instance.

        Args:
            - message (Optional[str]): Text to be logged.
            - creation_kwargs (Dict): Model specific keyword arguments to add on :class:`~ery_backend.logs.models.Log`
              creation.
            - log_type (Optional[str]): Django log level.
            - system_only (Optional[bool]): Whether to create a :class:`~ery_backend.logs.models.Log` instance.

        Notes:
            - A :class:`~ery_backend.logs.models.Log` instance is only created for system_only=False cases.
        """
        from ..logs.models import Log

        levels = {
            Log.LOG_TYPE_CHOICES.debug: 10,
            Log.LOG_TYPE_CHOICES.info: 20,
            Log.LOG_TYPE_CHOICES.warning: 30,
            Log.LOG_TYPE_CHOICES.error: 40,
            Log.LOG_TYPE_CHOICES.critical: 50,
        }
        if not log_type:
            log_type = Log.LOG_TYPE_CHOICES.info
        logger.log(levels[log_type], message)
        if not system_only:
            Log.objects.create(message=message, log_type=log_type, **creation_kwargs)


class StateMixin(models.Model):
    """
    Adds field indicating release state.
    """

    class Meta:
        abstract = True

    STATE_CHOICES = Choices(
        ('prealpha', 'Pre-alpha'),
        ('alpha', 'Alpha'),
        ('beta', 'Beta'),
        ('release', 'Release'),
        ('archived', 'Archived'),
        ('deleted', 'Deleted'),
    )

    # max length double highest char count of current choices
    state = models.CharField(max_length=18, choices=STATE_CHOICES, default=STATE_CHOICES.prealpha)
