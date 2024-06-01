import django
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.fields.related import ManyToManyField
from django.db.models.fields.reverse_related import ManyToOneRel, ManyToManyRel
from django.utils.translation import gettext_lazy as _
from model_utils import Choices
from model_utils.models import TimeStampedModel
from rest_framework import fields, serializers
from rest_framework.utils import model_meta

from ery_backend.keywords.mixins import KeywordMixin

from .cache import ery_cache
from .exceptions import EryValidationError
from .managers import EryManager, EryFileManager
from .mixins import NamedMixin, PrivilegedMixin, SluggedMixin, StateMixin, JavascriptValidationMixin
from .utils import get_gql_id


# pylint: disable=too-many-public-methods
class EryModel(TimeStampedModel):
    """
    Abstract base model inherited in most model classes.

    Args:
        - parent_field (str): str of attr referring to parental instance. Used for tracing ancestry.

    Notes:
        - Contains custom manager and save method.
        - Contains serialization and caching functionality.
        - Contains convenience wrappers for getting class attributes.
    """

    class Meta:
        ordering = ('created',)
        abstract = True

    class SerializerMeta:
        exclude = None
        model_serializer_fields = None
        non_model_serializer_reverse_fields = None

    objects = EryManager()  # for role based access control

    parent_field = None

    @classmethod
    @ery_cache
    def get_gql_id(cls, pk):
        """Create the expected gql id for a given node's class name and pk."""
        return get_gql_id(f'{cls._meta.object_name}', pk)

    @property
    def gql_id(self):
        """Create the expected gql id for a given node's class name and pk."""
        return self.get_gql_id(self.pk)

    @property
    def parent(self):
        """
        Obtain parental model instance, if any.

        Returns:
            :class:`EryModel`
        """
        if self.parent_field is not None:
            return getattr(self, self.parent_field)
        return None

    @classmethod
    def get_parent_model(cls):
        if cls.parent_field is not None:
            field = getattr(cls, cls.parent_field)
            if isinstance(field, django.db.models.fields.related_descriptors.ReverseOneToOneDescriptor):
                return field.related.related_model
            return field.field.related_model
        return None

    @classmethod
    def get_field_name(cls):
        """
        Returns the field name version of the given class.

        Note: Based on assertion that all :class:`EryModel` subclasses are represented
        as ForeignKey fields using the snake casing of their name.
        """
        from ery_backend.base.utils import to_snake_case

        return to_snake_case(cls.__name__)

    @classmethod
    def get_cache_tag_by_pk(cls, pk):
        """
        Generate cache key for tagging methods to given instance.

        Returns:
        str
        """
        return f"CT:{cls.__name__}:{pk}"

    @classmethod
    def get_cache_key_by_pk(cls, pk):
        """
        Generate representation of instance for use as parameter in other cache keys.

        Returns:
        str
        """
        return f"CK:{cls.__name__}:{pk}"

    @classmethod
    def get_content_type(cls):
        """Convenience wrapper over django ContentType queryset manager."""
        return ContentType.objects.get_for_model(cls)

    @classmethod
    def get_ids_by_role_assignment(cls, role_ids, user=None, group=None):
        """
        Returns:
            ids of all objects accessible via passed in roles.

        Notes:
            - Used in EryManager.filter_privilege.
            - Keys are invalidated upon granting/revoking a new role for user or group/group users.
        """
        from ..roles.models import RoleAssignment
        from ..users.models import User, Group

        if not user and not group:
            raise EryValidationError(
                "A user or group is required to execute get_ids_by_role_assignment"
                " for: {}, with role_ids: {}".format(cls, role_ids)
            )
        if user and group:
            raise EryValidationError(
                "Either a user OR group can be used to execute get_ids_by_role_assignment"
                " for: {}, with role_ids: {}, user: {}, group: {}".format(cls, role_ids, user, group)
            )
        if not isinstance(user, User) and not isinstance(group, Group):
            raise EryValidationError(
                "Either a user of type: {}, or group of type: {}, can be used to "
                " execute get_ids_by_role_assignment for: {}, with role_ids: {},"
                " user: {}, group: {}".format(User, Group, cls, role_ids, user, group)
            )

        content_type = cls.get_content_type()

        if user:
            group_ids = user.groups.values_list('id', flat=True)
        else:
            group_ids = (group.id,)

        # XXX: Address in issue #783
        # cache_key = cls.get_ids_by_role_assignment.cache_key(cls, role_ids, user, group)
        # tag_key([Role.get_cache_tag_by_pk(role_id) for role_id in role_ids], cache_key)
        # tag_key([Group.get_cache_tag_by_pk(group_id) for group_id in group_ids], cache_key)
        # if user:
        # tag_key(user.get_cache_tag(), cache_key)

        query_1 = RoleAssignment.objects.filter(role__in=role_ids, content_type=content_type, group__id__in=group_ids)
        if user:
            query_2 = RoleAssignment.objects.filter(role__in=role_ids, content_type=content_type, user=user)
            query_1 = query_1.union(query_2)

        output_ids = query_1.values_list('object_id', flat=True)
        return list(output_ids)  # convert to list for caching purposes

    def get_cache_tag(self):
        return self.get_cache_tag_by_pk(self.pk)

    def get_cache_key(self):
        return self.get_cache_key_by_pk(self.pk)

    def post_save_clean(self):
        """
        Exists for use by all models having clean functionality related to ManyToMany Relationships, or depending
         on for-free functionality provided by save (such as type-casting).

        Notes:
            - If this method is used, by convention, a reason for doing so should be specified via docsting.
        """

    def touch(self):
        """Touch will update versions of objects and their parent_fields."""
        if self.parent:
            self.parent.touch()

    def _invalidate_tag(self):
        """
        Invalidate cache tag.
        """
        from .cache import invalidate_tag

        invalidate_tag(self.get_cache_tag())

    def _invalidate_related_tags(self, history):
        """
        Invalidate cache tags of related models.
        """
        # XXX: Depth first recursion (address in issue #523)
        if self.parent:
            self.parent.invalidate_tags(history)

    def invalidate_tags(self, history=None):
        """
        Invalidate own cache tag and those of related models.

        Args:
            - history (List[:class:`EryModel`]): Keeps track of which models have already
              had their tags invalidated to prevent circularity.
        """
        if not history:
            history = [self]
        self._invalidate_tag()
        self._invalidate_related_tags(history)

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Override of default django method, including clean, post_save_clean, and tag invalidation methods.

        Note: Transactions are declared as atomic (via @transaction.atomic) to ensure commits only occur if all methods
            within save are completed.
        """
        self.clean()
        self.touch()
        super().save(*args, **kwargs)
        self.post_save_clean()
        self.invalidate_tags()

    def delete(self, **kwargs):
        """
        Override of default django method, including tag invalidation method.
        """
        self.invalidate_tags()
        super().delete(**kwargs)

    @classmethod
    def _is_required_field(cls, field):
        from django.db.models.fields import NOT_PROVIDED

        if isinstance(field, (ManyToOneRel, ManyToManyRel, ManyToManyField)):  # Many fields are not required
            return False
        if any([field.name in group for group in cls._meta.unique_together]):
            return True
        return not any([field.default != NOT_PROVIDED, field.blank, field.null])

    @classmethod
    def _is_file_dependent_field(cls, field):
        # Keyword is an example of a privileged model without a parent field. Those aren't file dependent.
        model_cls = field.related_model or field.model
        if (
            issubclass(model_cls, (EryPrivileged, EryNamedPrivileged))
            and model_cls.parent_field
            and hasattr(model_cls, 'name')
        ):
            model_file = model_cls.get_privilege_ancestor_cls()

            # If this is the parent of the serializer's model, we expect its pk to be passed into data
            if field.name != cls.parent_field and model_file == cls.get_privilege_ancestor_cls():
                return True
        return False

    @classmethod
    def _is_many_field(cls, field):
        from ery_backend.base.serializers import ErySerializer

        # because isinstance(OneToOne field, reverse_relatd.ManyToOneRel) is true
        return type(field) in ErySerializer.MANY_FIELD_TYPES  # pylint: disable=unidiomatic-typecheck

    @classmethod
    def _create_nested_fields(cls, field_info, model_serializer_fields, serializer_method):
        """
        Assign serializer fields for relations.

        Args:
         - serializer_method (str): Obtained from field model to cast nested serializer_types for
           specified model_serializer_fields.
        """
        from .serializers import ErySerializer

        if serializer_method not in ('get_bxml_serializer', 'get_duplication_serializer', 'get_mutation_serializer'):
            raise Exception("Invalid serializer method")

        classattrs = {}
        for field_name in model_serializer_fields:
            model_field = ErySerializer.get_model_field(cls, field_name)
            model_serializer = getattr(model_field.related_model, serializer_method)()
            required = cls._is_required_field(model_field)
            model_serializer_kwargs = {
                'many': cls._is_many_field(model_field),
                'required': required,
                'allow_null': (not required),
            }
            classattrs[field_name] = model_serializer(**model_serializer_kwargs)
        return classattrs

    @classmethod
    def _create_file_dependent_fields(cls, field_info, exclude, extra_fields):
        """
        Assign file dependent fields for relations.

        Attrs:
            - extra_fields (List[str]): Other relations to convert
        """
        from .serializers import ErySerializer, FileDependentSlugRelatedField

        classattrs = {}
        for field_name in list(field_info.forward_relations) + extra_fields:
            if field_name not in exclude:
                model_field = ErySerializer.get_model_field(cls, field_name)
                if cls._is_file_dependent_field(model_field):
                    queryset = model_field.related_model.objects.get_queryset()
                    required = cls._is_required_field(model_field)
                    field_kwargs = {
                        'queryset': queryset,
                        'many': cls._is_many_field(model_field),
                        'required': required,
                        'allow_null': (not required),
                    }
                    field_kwargs['slug_field'] = 'name'

                    # Assumes file names are the slug_cased representation of class name
                    file_name = '_'.join(cls.get_privilege_ancestor_cls()._meta.verbose_name.split())
                    field_kwargs['file_name'] = file_name
                    classattrs[field_name] = FileDependentSlugRelatedField(**field_kwargs)
        return classattrs

    # pylint:disable = too-many-branches
    @classmethod
    def _get_nonnested_related_field_attrs(cls, base_serializer, field_info, exclude, extra_fields, serializer_type):
        """
        Attrs:
            - extra_fields (List[str]): Other relations to convert
        """
        from ery_backend.base.serializers import ErySerializer, FileDependentSlugRelatedField

        base_serializer_fields = base_serializer().fields

        nonnested_related_info = {}

        remaining_related_field_names = extra_fields  # If there are no extra_fields, we expect an empty list
        for field_name in field_info.forward_relations:
            if field_name not in exclude:
                # if field_name in base_serializer_fields:  # Implicit reverse_relationships not included
                if isinstance(base_serializer_fields[field_name], FileDependentSlugRelatedField):
                    continue
                if isinstance(base_serializer_fields[field_name], serializers.ManyRelatedField) and isinstance(
                    base_serializer_fields[field_name].child_relation, FileDependentSlugRelatedField
                ):
                    continue
                remaining_related_field_names.append(field_name)

        parent_field_base_kwargs = {'required': True, 'allow_null': False}

        for field_name in remaining_related_field_names:
            model_field = ErySerializer.get_model_field(cls, field_name)
            required = cls._is_required_field(model_field)
            field_kwargs = {
                'queryset': model_field.related_model.objects.get_queryset(),
                'required': cls._is_required_field(model_field),
                'allow_null': (not required),
                'many': cls._is_many_field(model_field),
            }

            if serializer_type == 'bxml':
                if hasattr(cls, 'parent_field') and field_name == cls.parent_field:
                    field_kwargs['write_only'] = True
                    field_kwargs.update(parent_field_base_kwargs)
                    nonnested_related_info[field_name] = serializers.PrimaryKeyRelatedField(**field_kwargs)
                else:
                    model_field = ErySerializer.get_model_field(cls, field_name)
                    if hasattr(model_field.related_model, 'slug'):
                        # A slug_field is required to add non file-dependent/non-parent fields automatically
                        field_kwargs['slug_field'] = 'slug'
                        nonnested_related_info[field_name] = serializers.SlugRelatedField(**field_kwargs)
                    else:
                        # A slug_field must be set manually
                        nonnested_related_info[field_name] = None

            elif serializer_type in ('duplication', 'mutation'):
                if hasattr(cls, 'parent_field') and field_name == cls.parent_field:
                    field_kwargs.update(parent_field_base_kwargs)
                    if serializer_type == 'duplication':
                        field_kwargs['write_only'] = True
                nonnested_related_info[field_name] = serializers.PrimaryKeyRelatedField(**field_kwargs)

        if cls.parent_field and cls.parent_field not in remaining_related_field_names:  # Reverse relation
            model_field = ErySerializer.get_model_field(cls, cls.parent_field)
            field_kwargs = {
                'queryset': model_field.related_model.objects.get_queryset(),
                'required': False,
                'allow_null': True,
                'many': False,
            }
            nonnested_related_info[cls.parent_field] = field_kwargs

        return nonnested_related_info

    @classmethod
    def _validate_exclusions(cls, exclude, field_info):
        """Don't include reverse_related exlusions"""
        validated_exclusions = []
        hidden_exclusions = []
        for field_name in exclude:
            if field_name in field_info.reverse_relations:
                try:
                    cls._meta.get_field(field_name)
                    if field_name in field_info.fields:
                        validated_exclusions.append(field_name)
                    else:
                        hidden_exclusions.append(field_name)
                except django.core.exceptions.FieldDoesNotExist:
                    # If `related_name` is not set, field name does not include
                    # `_set` -> remove it and check again
                    default_postfix = '_set'
                    if field_name.endswith(default_postfix):
                        hidden_field_name = field_name[: -len(default_postfix)]
                        try:
                            cls._meta.get_field(hidden_field_name)
                            hidden_exclusions.append(field_name)
                        except django.core.exceptions.FieldDoesNotExist:
                            continue
            else:
                validated_exclusions.append(field_name)
        return validated_exclusions, hidden_exclusions

    @classmethod
    def _create_base_serializer(cls, field_info):
        """Add all non-related/non-id/non-parent fields"""
        from .serializers import ErySerializer

        new_class_name = f'Base{cls._meta.object_name}Serializer'
        meta_args = {'model': cls}

        model_serializer_fields = cls.SerializerMeta.model_serializer_fields or []
        non_model_serializer_reverse_fields = cls.SerializerMeta.non_model_serializer_reverse_fields or []
        exclude = cls.SerializerMeta.exclude or []
        for name, specification in (
            ('model_serializer_fields', model_serializer_fields),
            ('exclude', exclude),
            ('non_model_serializer_reverse_fields', non_model_serializer_reverse_fields),
        ):
            if specification and not isinstance(specification, (tuple, list, set)):
                raise ValidationError({name: "Must be a tuple, list, or set"})

        if model_serializer_fields:
            model_serializer_fields = [field_name for field_name in model_serializer_fields if hasattr(cls, field_name)]

        if non_model_serializer_reverse_fields:
            non_model_serializer_reverse_fields = [
                field_name for field_name in non_model_serializer_reverse_fields if hasattr(cls, field_name)
            ]

        exclude = list(
            set(exclude).union({field_name for field_name in ('created', 'modified', 'version') if hasattr(cls, field_name)})
        )

        classattrs = {}

        if hasattr(cls, 'slug') and 'slug' not in exclude:
            classattrs['slug'] = serializers.SlugField(required=False, allow_null=True, write_only=True)
        meta_args['exclude'] = exclude
        meta_args['non_model_serializer_reverse_fields'] = non_model_serializer_reverse_fields

        # override default ModelSerializer behavior of casting choice char fields to ChoiceField
        # due to gql mutation input incompatibility
        for field_name, model_field in field_info.fields.items():
            if isinstance(model_field, models.CharField) and model_field.choices:
                if field_name not in exclude:
                    model_field = field_info.fields[field_name]
                    required = cls._is_required_field(model_field)
                    classattrs[model_field.name] = fields.CharField(
                        allow_blank=model_field.blank,
                        max_length=model_field.max_length,
                        required=required,
                        allow_null=(not required),
                    )

        classattrs.update(
            cls._create_file_dependent_fields(
                field_info, exclude + model_serializer_fields, non_model_serializer_reverse_fields
            )
        )

        meta_class = type('Meta', (), meta_args)
        classattrs['Meta'] = meta_class

        return type(new_class_name, (ErySerializer,), classattrs)

    @classmethod
    def create_bxml_serializer(cls):
        model_serializer_fields = cls.SerializerMeta.model_serializer_fields or []
        # validators handled by ModelSerializer
        field_info = model_meta.get_field_info(cls)

        base_serializer = cls._create_base_serializer(field_info)
        exclude = base_serializer.Meta.exclude
        non_model_serializer_reverse_fields = base_serializer.Meta.non_model_serializer_reverse_fields

        new_class_name = f'{cls._meta.object_name}BXMLSerializer'

        id_field = serializers.PrimaryKeyRelatedField(
            queryset=base_serializer.Meta.model.objects.get_queryset(),
            required=False,
            many=False,
            write_only=True,
            allow_null=True,
        )

        # id required for get_minimally_valid_serializer/create. If the first does not keep an id in validated data,
        # the latter will create a new instance when data is nested.
        classattrs = {'id': id_field}

        classattrs.update(
            cls._get_nonnested_related_field_attrs(
                base_serializer, field_info, exclude, non_model_serializer_reverse_fields, 'bxml'
            )
        )

        classattrs.update(cls._create_nested_fields(field_info, model_serializer_fields, 'get_bxml_serializer'))

        meta_class = type('Meta', (base_serializer.Meta,), {})
        classattrs['Meta'] = meta_class
        return type(new_class_name, (base_serializer,), classattrs)

    @classmethod
    def create_duplication_serializer(cls):
        model_serializer_fields = cls.SerializerMeta.model_serializer_fields or []

        # validators handled by ModelSerializer
        field_info = model_meta.get_field_info(cls)

        base_serializer = cls._create_base_serializer(field_info)

        exclude = base_serializer.Meta.exclude
        non_model_serializer_reverse_fields = base_serializer.Meta.non_model_serializer_reverse_fields

        new_class_name = f'{cls._meta.object_name}DuplicationSerializer'

        classattrs = {}

        classattrs.update(
            cls._get_nonnested_related_field_attrs(
                base_serializer, field_info, exclude, non_model_serializer_reverse_fields, 'duplication'
            )
        )

        classattrs.update(cls._create_nested_fields(field_info, model_serializer_fields, 'get_duplication_serializer'))

        meta_class = type('Meta', (base_serializer.Meta,), {'exclude': base_serializer.Meta.exclude + ['id']})
        classattrs['Meta'] = meta_class
        return type(new_class_name, (base_serializer,), classattrs)

    @classmethod
    def create_mutation_serializer(cls):
        model_serializer_fields = cls.SerializerMeta.model_serializer_fields or []

        # validators handled by ModelSerializer
        field_info = model_meta.get_field_info(cls)

        base_serializer = cls._create_base_serializer(field_info)

        exclude = base_serializer.Meta.exclude
        non_model_serializer_reverse_fields = base_serializer.Meta.non_model_serializer_reverse_fields or []

        new_class_name = f'{cls._meta.object_name}MutationSerializer'

        id_field = serializers.PrimaryKeyRelatedField(
            queryset=cls.objects.get_queryset(), required=False, many=False, allow_null=True
        )

        classattrs = {'id': id_field}

        classattrs.update(
            cls._get_nonnested_related_field_attrs(
                base_serializer, field_info, exclude, non_model_serializer_reverse_fields, 'mutation'
            )
        )

        classattrs.update(cls._create_nested_fields(field_info, model_serializer_fields, 'get_mutation_serializer'))

        meta_class = type('Meta', (base_serializer.Meta,), {})
        classattrs['Meta'] = meta_class
        return type(new_class_name, (base_serializer,), classattrs)

    @classmethod
    def get_bxml_serializer(cls):
        # This can be overloaded if you want to further customize the serializer
        return cls.create_bxml_serializer()

    @classmethod
    def get_duplication_serializer(cls):
        # This can be overloaded if you want to further customize the serializer
        return cls.create_duplication_serializer()

    @classmethod
    def get_mutation_serializer(cls):
        # This can be overloaded if you want to further customize the serializer
        return cls.create_mutation_serializer()


class EryNamed(EryModel, NamedMixin):
    """Abstract models providing a unique name and comment."""

    class Meta(EryModel.Meta):
        abstract = True
        ordering = ("name",)


class EryNamedSlugged(EryNamed, SluggedMixin):
    """Abstract models providing a unique name, a slug and a comment."""

    class Meta(EryNamed.Meta):
        abstract = True


class EryPrivileged(EryModel, PrivilegedMixin):
    """
    Used for models which require functionality provided by EryModel and role based access control.
        See EryModel and PrivilegedMixin for details.
    """

    class Meta(EryModel.Meta):
        abstract = True

    class SerializerMeta(EryModel.SerializerMeta):
        pass


class EryNamedPrivileged(EryNamed, PrivilegedMixin):
    """
    Used for named models which require functionality provided by EryModel and role based access control.
        See EryModel and PrivilegedMixin for details.
    """

    class Meta(EryNamed.Meta):
        abstract = True


class EventStepModel(EryPrivileged):
    class Meta(EryPrivileged.Meta):
        abstract = True
        ordering = ("order",)

    EVENT_ACTION_TYPE_CHOICES = Choices()

    # max-length is twice the length of the largest choices
    event_action_type = models.CharField(max_length=14, choices=EVENT_ACTION_TYPE_CHOICES)
    order = models.PositiveIntegerField(default=0)


class EventModel(JavascriptValidationMixin, EryPrivileged):
    """
    :class:`EryPrivileged` with event attribute (JavaScript trigger).

    Attributes:
        - EVENT_TYPE_CHOICES: Types of actions associated with the given instance.
        - EVENT_CHOICES: Types of JavaScript events associated with the given instance.
    """

    class Meta(EryPrivileged.Meta):
        abstract = True

    allow_underscores = False

    REACT_EVENT_CHOICES = Choices(
        ('onBlur', _('On Blur')),
        ('onChange', _('On Change')),
        ('onChangeCommitted', _('On Change Committed')),
        ('onClick', _('On Click')),
        ('onFocus', _('On Focus')),
        ('onInput', _('On Input')),
        ('onKeyDown', _('On Key Down')),
        ('onMouseUp', _('On Mouse Up')),
        ('onSubmit', _('On Submit')),
        ('onScan', _('On Scan')),
    )

    SMS_EVENT_CHOICES = Choices(('onReply', _('On Reply')),)

    # Prefix shouldn't be that long. Limit is 3x the estimated usage.
    name = models.CharField(
        max_length=24, blank=True, default='', help_text="Use to group subset of actions for a given event_type."
    )
    event_type = models.CharField(
        max_length=50, choices=REACT_EVENT_CHOICES + SMS_EVENT_CHOICES, help_text="Javascript or SMS event trigger."
    )

    def trigger(self, hand, **kwargs):
        """
        Signal event to execute associated action, as determined by event_type attribute.


        Args:
            hand (:class:`~ery_backend.hands.models.Hand`): Provides context
            during execution of associated action.
        """
        raise NotImplementedError()

    def _validate(self):
        if self.name not in [None, '']:
            if self._starts_with_number():
                raise ValidationError(f"{self.__class__.__name__} with name: '{self.name}', must start" " with a letter.")
            super()._validate()


class EryFile(EryNamed, PrivilegedMixin, KeywordMixin, SluggedMixin, StateMixin):
    """
    Combined inheritance model for objects to be represented as files in Ery.

    :class:`EryFile` subclasses share the following properties:
        - They can be exported, imported, and duplicated.
        - They are sorted within :class:`~ery_backend.folders.models.Folder` instances using
          :class:`~ery_backend.folders.models.Link` instances.

    Notes:
        - :class:`EryFile` objects are soft_deleted through their delete mutation (their state is changed).
        - The delete method must be run at the Django level to remove an EryFile from the database.
    """

    class Meta(EryNamed.Meta):
        pass

    objects = EryFileManager()  # for role based access control and annotation method

    name = models.CharField(max_length=512, unique=False, blank=False, help_text="Name of instance")
    published = models.BooleanField(default=False, help_text="Publically viewable")

    def create_link(self, folder):
        from ery_backend.folders.models import Link

        file_reference = self.get_field_name()
        return Link.objects.create(parent_folder=folder, **{file_reference: self})

    def soft_delete(self):
        """
        Remove instance from graphene level queries.
        """
        self.invalidate_tags()
        self.state = self.STATE_CHOICES.deleted
        self.save()


class EryFileReference(EryModel):
    """
    Connect :class:`~ery_backend.base.models.EryFile` objects to :class:`Folder` objects.
    """

    class Meta(EryModel.Meta):
        abstract = True

    FILE_CHOICES = Choices(
        ('dataset', "Dataset"),
        ('image_asset', "Image Asset"),
        ('procedure', "Procedure"),
        ('module_definition', "Module Definition"),
        ('stint_definition', "Stint Definition"),
        ('template', "Template"),
        ('widget', "Widget"),
        ('theme', "Theme"),
        ('validator', "Validator"),
    )

    reference_type = models.CharField(choices=FILE_CHOICES, max_length=32)
    dataset = models.ForeignKey(
        'datasets.Dataset',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=":class:`~ery_backend.users.models.User` uploaded :class:`~ery_backend.datasets.models.Dataset`",
    )
    image_asset = models.ForeignKey(
        'assets.ImageAsset',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=":class:`~ery_backend.users.models.User` uploaded image.",
    )
    procedure = models.ForeignKey('procedures.Procedure', on_delete=models.CASCADE, null=True, blank=True)
    module_definition = models.ForeignKey('modules.ModuleDefinition', on_delete=models.CASCADE, null=True, blank=True)
    stint_definition = models.ForeignKey('stints.StintDefinition', on_delete=models.CASCADE, null=True, blank=True)
    template = models.ForeignKey('templates.Template', on_delete=models.CASCADE, null=True, blank=True)
    widget = models.ForeignKey('widgets.Widget', on_delete=models.CASCADE, null=True, blank=True)
    theme = models.ForeignKey('themes.Theme', on_delete=models.CASCADE, null=True, blank=True)
    validator = models.ForeignKey('validators.Validator', on_delete=models.CASCADE, null=True, blank=True)

    def get_obj(self):
        """
        Return the field name and file object referred to by the EryFileReference
        """
        return getattr(self, self.reference_type)

    def clean(self):
        # If not set yet, set reference_type
        if not self.reference_type:
            for field, _ in list(self.FILE_CHOICES):
                if hasattr(self, field) and getattr(self, field) is not None:
                    self.reference_type = field
                    break

        for field, field_name in list(self.FILE_CHOICES):
            value = getattr(self, field)
            if field == self.reference_type:
                if value is None:
                    raise ValueError(f"File reference of type \"{self.reference_type}\" must specify its {field_name}")
            else:
                if value is not None:
                    raise ValueError(f"File reference of type \"{self.reference_type}\" may NOT specify its {field_name}")

        super().clean()
