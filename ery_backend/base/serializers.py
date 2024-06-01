# pylint: disable=too-many-lines
from collections import OrderedDict
import copy
from io import BytesIO

from lxml import etree

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import FieldError
from django.db import transaction
from django.db.models import ProtectedError, FieldDoesNotExist
from django.db.models.fields import NOT_PROVIDED
from django.db.models.fields.related import ForeignObjectRel
import django.db
from django.utils.translation import gettext_lazy as _
from drf_writable_nested.mixins import BaseNestedModelSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.utils import model_meta
from rest_framework_xml.parsers import XMLParser
from rest_framework_xml.renderers import XMLRenderer

from .cache import ery_cache
from .models import EryFile
from .utils import to_snake_case


class EryXMLParser(XMLParser):
    item_tag_name = 'item'

    def _xml_convert(self, element):
        """Return the xml `element` (set) as a data dictionary for the corresponding python object."""
        children = list(element)

        if not children:  # pylint:disable=no-else-return
            return self._type_convert(element.text)
        else:
            # if the first child tag is list-item, all children are list-item
            if children[0].tag == self.item_tag_name:
                data = []
                for child in children:
                    data.append(self._xml_convert(child))
            else:
                data = {}
                for child in children:
                    data[child.tag] = self._xml_convert(child)

        return data


class EryXMLRenderer(XMLRenderer):
    item_tag_name = 'item'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Return prettified string xml."""
        data = super().render(data, accepted_media_type, renderer_context)
        data = etree.fromstring(data.encode('UTF-8'))  # parse data using etree
        # convert to pretty printed xml
        pretty_xml_as_string = etree.tostring(data, encoding='UTF-8', xml_declaration=True, pretty_print=True)
        return pretty_xml_as_string


class FrontendXMLRenderer(EryXMLRenderer):
    """XMLRenderer for Frontend objects"""

    root_tag_name = 'frontend'

    @staticmethod
    def get_model():
        """Return model class"""
        from ..frontends.models import Frontend

        return Frontend


class FrontendXMLParser(EryXMLParser):
    """XMLRenderer for Frontend objects"""

    root_tag_name = 'frontend'


class LabXMLRenderer(EryXMLRenderer):
    """XMLRenderer for Frontend objects"""

    root_tag_name = 'lab'

    @staticmethod
    def get_model():
        from ..labs.models import Lab

        return Lab


class LabXMLParser(EryXMLParser):
    root_tag_name = 'lab'


class WidgetXMLRenderer(EryXMLRenderer):
    """XMLRenderer for Widget objects."""

    root_tag_name = 'widget'

    @staticmethod
    def get_model():
        """Return model class."""
        from ..widgets.models import Widget

        return Widget


class WidgetXMLParser(EryXMLParser):
    """XMLParser for Widget objects."""

    root_tag_name = 'widget'


class ProcedureXMLRenderer(EryXMLRenderer):
    """XMLRenderer for Procedure objects."""

    root_tag_name = 'procedure'

    @staticmethod
    def get_model():
        """Return model class."""
        from ..procedures.models import Procedure

        return Procedure


class ProcedureXMLParser(EryXMLParser):
    """XMLParser for Procedure objects."""

    root_tag_name = 'procedure'


class ModuleDefinitionXMLRenderer(EryXMLRenderer):
    """XMLRenderer for ModuleDefinition objects."""

    root_tag_name = 'module_definition'

    @staticmethod
    def get_model():
        """
        Returns model class.
        """
        from ..modules.models import ModuleDefinition

        return ModuleDefinition


class ModuleDefinitionXMLParser(EryXMLParser):
    """XMLParser for serialized ModuleDefinition objects."""

    root_tag_name = 'module_definition'


class StintDefinitionXMLRenderer(EryXMLRenderer):
    """XMLRenderer for StintDefinition objects."""

    root_tag_name = 'stint_definition'

    @staticmethod
    def get_model():
        """Return model class."""
        from ..stints.models import StintDefinition

        return StintDefinition


class StintDefinitionXMLParser(EryXMLParser):
    """XMLParser for StintDefinition objects."""

    root_tag_name = 'stint_definition'


class TemplateXMLRenderer(EryXMLRenderer):
    """XMLRenderer for Template objects."""

    root_tag_name = 'template'

    @staticmethod
    def get_model():
        """Return model class."""
        from ..templates.models import Template

        return Template


class TemplateXMLParser(EryXMLParser):
    """XMLParser for Template objects."""

    root_tag_name = 'template'


class ThemeXMLRenderer(EryXMLRenderer):
    """XMLRenderer for Theme objects."""

    root_tag_name = 'theme'

    @staticmethod
    def get_model():
        """Return model class."""
        from ..themes.models import Theme

        return Theme


class ThemeXMLParser(EryXMLParser):
    """XMLParser for Theme objects."""

    root_tag_name = 'theme'


class ValidatorXMLRenderer(EryXMLRenderer):
    """XMLRenderer for Theme objects."""

    root_tag_name = 'validator'

    @staticmethod
    def get_model():
        """Return model class."""
        from ..validators.models import Validator

        return Validator


class ValidatorXMLParser(EryXMLParser):
    """XMLParser for Theme objects."""

    root_tag_name = 'validator'


class FileDependentSlugRelatedField(serializers.SlugRelatedField):
    """
    Used where a child can be found be searching for its name and a file available in the parent's data.
    A condition with a pre-action can use the action's name and the condition's file (module definition).
    A formfield with disable can use the condition's name and the form field's file (module definition).
    """

    file_pk = None  # Must be set by a parent serializer during validation

    default_error_messages = {
        'invalid_key': _('Invalid keyword: "SlugField: {slug_field}". {available_choices}.'),
        'filter_kwargs': _('Could not lookup filter_kwargs: "SlugField: {slug_field}". {lookup_key}.'),
        **serializers.SlugRelatedField.default_error_messages,
    }

    def __init__(self, **kwargs):
        assert 'file_name' in kwargs, 'file_name is a required argument.'
        self.file_name = kwargs.pop('file_name')
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        qs = self.get_queryset()

        if not self.file_pk:
            self.fail("filter_kwargs", slug_field=self.slug_field, lookup_key=self.file_name)
        filter_kwargs = {self.file_name: self.file_pk, self.slug_field: data}

        try:
            return qs.get(**filter_kwargs)
        except qs.model.DoesNotExist:
            self.fail("does_not_exist", slug_name=self.slug_field, value=f"data: {data}, with lookup kwargs: {filter_kwargs}")
        except (TypeError, ValueError) as e:
            self.fail(e)

        except (FieldError) as e:
            self.fail("invalid_key", slug_field=self.slug_field, available_choices={e})


class ErySerializer(BaseNestedModelSerializer, serializers.ModelSerializer):
    """
    Base class for all serialization and deserialization.

    Constants:
        MODEL_DEPENDENCIES (tuple[str]): Related model instances required for current object creation.

        ATTRIBUTE_MAP (dict or OrderedDict[dict[str, Union[bool, str, model_cls]]]): Tracks many relationship boolean
          (quantity), model class (for obtaining model serializer), and optional simple serialization option
          (uses simple serializer instead of regular serializer) of children. Implemented as OrderedDict if order
          of serialization is important).

        IGNORE (tuple[str]): Children created outside of normal nested create flow.
        POST_IGNORE (tuple[str]): Children dependent on siblings created outside of normal nested create flow.
        INSTRUCTION_KWARGS (Dict[str, Dict[str, Union[str]: Specify whether to get, create, or perform get_or_create to obtain
          serialized children. For get method, using lookup syntax ('..' to access parent and '.' to access attributes) allows
          accessing specific serialized parent/child data or data from an instantiate parent.
          For create, replacement_kwargs use same syntax to allow passing in parent (and its attributes)
          to children. Implemented as dictionary.

    """

    IGNORE = ()
    POST_IGNORE = ()
    MODEL_FIELDS = ()
    DEPENDENCIES = ()
    POST_CREATE = ()

    MANY_FIELD_TYPES = (
        django.db.models.fields.reverse_related.ManyToOneRel,
        django.db.models.fields.reverse_related.ManyToManyRel,
        django.db.models.fields.related.ManyToManyField,
    )

    @classmethod
    def get_pk_attr(cls):
        return cls.Meta.model._meta.pk.attname if not issubclass(cls.Meta.model, EryFile) else 'id'

    def to_internal_value(self, data):
        """
        Dict of native values <- Dict of primitive datatypes.

        Notes:
            - Add instance's file pk to all FileDependentFields that need it.
        """
        # Add file pk
        model = self.Meta.model
        is_file = issubclass(model, EryFile)
        top_level_cls = (
            model.get_privilege_ancestor_cls() if (not is_file and hasattr(model, 'get_privilege_ancestor_cls')) else model
        )
        is_part_of_file = not is_file and issubclass(top_level_cls, EryFile)
        if (is_part_of_file and model.parent_field in data) or (is_file and 'id' in data):
            file_dependent_fields = [
                field
                for field in self._writable_fields
                if (isinstance(field, FileDependentSlugRelatedField) and field.file_pk is None)
                or (
                    isinstance(field, serializers.ManyRelatedField)
                    and isinstance(field.child_relation, FileDependentSlugRelatedField)
                    and field.child_relation.file_pk is None
                )
            ]
            if file_dependent_fields:
                if is_file:
                    file_pk = data.get('id')

                else:
                    file_pk = (
                        model._meta.get_field(model.parent_field)
                        .related_model.objects.get(pk=data[model.parent_field])
                        .get_privilege_ancestor()
                        .pk
                    )

                for field in file_dependent_fields:
                    if isinstance(field, serializers.ManyRelatedField):
                        field.child_relation.file_pk = file_pk
                    else:
                        field.file_pk = file_pk

        # Fill defaults
        needed_default_fields = [
            field
            for field in self._writable_fields
            if field.required
            and self.get_model_field(self.Meta.model, field.source).default != NOT_PROVIDED
            and not data.get(field.source)
        ]
        if needed_default_fields:
            for field in needed_default_fields:
                if isinstance(field, serializers.SlugRelatedField):
                    model_field = self.get_model_field(self.Meta.model, field.source)
                    slug = model_field.related_model.objects.filter(pk=model_field.default).values_list(
                        field.slug_field, flat=True
                    )[0]
                    data[field.source] = slug
                else:
                    data[field.source] = self.get_model_field(self.Meta.model, field.source).default
        return super().to_internal_value(data)

    @staticmethod
    @ery_cache
    def get_model_field(model_class, field_name):
        """
        Retrieve implicit/explicit model field's by name.

        Args:
            - model_cls (:class:`~ery_backend.base.models.EryModel`).
            - field_name (str): Name of attribute.

        Returns:
            - Union(:class:`django.db.models.fields.Field`, descriptor from `django.db.models.fields.related_descriptors`)
        """
        try:
            model_field = model_class._meta.get_field(field_name)
        except FieldDoesNotExist:
            # If `related_name` is not set, field name does not include
            # `_set` -> remove it and check again
            default_postfix = '_set'
            if field_name.endswith(default_postfix):
                model_field = model_class._meta.get_field(field_name[: -len(default_postfix)])
            else:
                raise
        return model_field

    def fill_parent_kwarg(self, field_name, data, parent_instance):
        """
        Inject parent primary_key into child field data for successful validation/save.

        Args:
            - data (Union[List[Dict]], Dict)
            - parent_instance (:class:`~ery_backend.base.models.EryModel`)
        """
        if isinstance(data, dict):
            data[self.Meta.model.parent_field] = parent_instance.pk
        elif isinstance(data, list):
            for instance_data in data:
                instance_data[self.Meta.model.parent_field] = parent_instance.pk
        else:
            raise ValidationError({field_name: f"Expected list or dict, not: {data}"})

    def update_or_create_direct_relations(self, attrs, relations):
        """
        Identify/create and connect foreign key and one to one relationships.

        Args:
            attrs (Dict[str: Union[str, float, int, List, Dict]]): Serializer values for relations.
            relations (Dict[str: Tuple[:class:`rest_framework.fields.Field`, str]]: Field and source.

        Notes:
            - Overloads method of same name from django-writable-nested
        """
        retry_required = False  # Whether to re-run update_or_create_direct_relations with unsuccessful data
        retry_info = []
        invalid_related_fields = []
        for field_name, (field, field_source) in relations.items():
            related_data = attrs.get(field_name, None)
            if related_data is None:
                if self.instance:
                    setattr(self.instance, field_source, None)
                    self.instance.save()
                continue

            obj, serializer = None, None
            if isinstance(field, ErySerializer):
                model_class = field.Meta.model
                pk = self._get_related_pk(related_data, field.Meta.model)
                if pk:
                    obj = model_class.objects.filter(pk=pk,).first()
                serializer = self._get_serializer_for_field(field, instance=obj, data=related_data)
                serializer.bind(field_name, self)  # Bind parent for better context in errors

                # nested_retry_info specified methods to re-run if save partially succeeds, failing to connect relations
                related_instance, nested_retry_info = serializer.validate_and_save(
                    nested=True, **self._get_save_kwargs(field_name)
                )
                retry_info += nested_retry_info

                if related_instance:
                    setattr(self.instance, field_source, related_instance)
                    self.instance.save()
                    del attrs[field_name]
                else:
                    retry_required = True
                    invalid_related_fields.append(serializer)

            # May require the parent's id, which is added after initial validation
            elif issubclass(field.__class__, serializers.RelatedField):
                try:
                    related_instance = field.run_validation(data=related_data)
                    setattr(self.instance, field_source, related_instance)
                    self.instance.save()
                    del attrs[field_name]

                except ValidationError as exc:
                    retry_required = True
                    if not field.field_name:
                        field.bind(field_name, self)  # Bind parent for better context in errors
                    field.errors = exc
                    invalid_related_fields.append(field)
            else:
                raise Exception(f"No code to handle updating/create direct relation for {field_name: field}")

        if retry_required:
            return (
                [(self.update_or_create_direct_relations, {'attrs': attrs, 'relations': relations})],
                invalid_related_fields,
            )
        return (retry_info, invalid_related_fields)

    def reset_is_valid(self):
        if hasattr(self, '_validated_data'):
            delattr(self, '_validated_data')
        self._errors = {}  # pylint: disable=attribute-defined-outside-init

    def update_or_create_reverse_relations(self, reverse_relations, relations_data):  # pylint:disable=too-many-branches
        # many-to-one, many-to-many, reversed one-to-one
        retry_required = False  # Whether to re-run update_or_create_direct_relations with unsuccessful data
        retry_info = []
        invalid_related_fields = []
        # pylint: disable=too-many-nested-blocks
        for field_name, (related_field, field, field_source) in reverse_relations.items():
            related_data = relations_data.get(field_name, None)

            if isinstance(field, ErySerializer):
                # Skip processing for empty data or not-specified field.
                # The field can be defined in validated_data but isn't defined
                # in initial_data (for example, if multipart form data used)

                # For injection of pks
                if not related_data:
                    continue

                if related_field.one_to_one:
                    # If an object already exists, fill in the pk so we don't try to duplicate it
                    pk_name = field.get_pk_attr()
                    if pk_name not in related_data and 'pk' in related_data:
                        pk_name = 'pk'
                    if pk_name not in related_data:
                        related_instance = getattr(self.instance, field_source, None)
                        if related_instance:
                            related_data[pk_name] = related_instance.pk

                    # Expand to array of one item for one-to-one for uniformity
                    related_data = [related_data]

                instances = self._prefetch_related_instances(field, related_data)

                save_kwargs = self._get_save_kwargs(field_name)
                if isinstance(related_field, GenericRelation):
                    save_kwargs.update(self._get_generic_lookup(instance, related_field),)
                elif not related_field.many_to_many:
                    save_kwargs[related_field.name] = self.instance

                new_related_instances = []
                for data in related_data:

                    obj = instances.get(self._get_related_pk(data, field.Meta.model))
                    initially_had_obj = obj is not None
                    serializer = self._get_serializer_for_field(field, instance=obj, data=data,)

                    related_instance, nested_retry_info = serializer.validate_and_save(nested=True, **save_kwargs)
                    retry_info += nested_retry_info

                    if related_instance:
                        # This must be updated with pk to not be deleted during update
                        data[serializer.get_pk_attr()] = related_instance.pk

                        if not initially_had_obj:
                            new_related_instances.append(related_instance)

                    else:  # Save failed completely
                        serializer.bind(field_name, self)  # Bind parent for better context in errors
                        invalid_related_fields.append(serializer)
                        retry_required = True

                if related_field.many_to_many:
                    # Add m2m instances to through model via add
                    m2m_manager = getattr(instance, field_source)
                    m2m_manager.add(*new_related_instances)

            else:
                if related_data is None:
                    related_data = []

                try:
                    instances = field.run_validation(related_data)
                    if related_field.many_to_many and instances:
                        m2m_manager = getattr(self.instance, field_source)
                        manager_pks = m2m_manager.values_list('pk', flat=True)
                        for instance in instances:
                            if instance.pk not in manager_pks:
                                m2m_manager.add(instance)

                except ValidationError as exc:
                    retry_required = True
                    field.errors = exc
                    invalid_related_fields.append(field)

        if retry_required:
            invalid_related_fields.append(self)
            return (
                [
                    (
                        self.update_or_create_reverse_relations,
                        {'reverse_relations': reverse_relations, 'relations_data': relations_data},
                    )
                ],
                invalid_related_fields,
            )
        return (retry_info, invalid_related_fields)

    def _get_relations(self, data):  # pylint:disable=too-many-branches
        def _field_is_many(field_name):
            model_field = ErySerializer.get_model_field(self.Meta.model, field_name)
            # because isinstance(OneToOne field, reverse_related.ManyToOneRel) is true
            return type(model_field) in self.many_field_types  # pylint: disable=unidiomatic-typecheck

        relations, reverse_relations = {}, {}
        django_model = self.Meta.model

        for field_name, field in self.fields.items():
            # Parents should never be extracted
            if field_name in (self.Meta.model.parent_field, self.get_pk_attr()) or field.read_only:
                continue
            try:
                related_field, direct = self._get_related_field(field)
            except FieldDoesNotExist:
                continue

            if isinstance(field, serializers.ListSerializer):
                if field.source not in data:
                    # Skip field if field is not required
                    continue

                reverse_relations[field_name] = (related_field, field.child, field.source)

            elif issubclass(field.__class__, ErySerializer):
                if field.source not in data:
                    # Skip field if field is not required
                    continue

                if (
                    data.get(field.source) is None
                    and direct
                    and not (hasattr(django_model, 'parent_field') and django_model.parent_field == field_name)
                ):
                    # Don't process null value for direct relations that aren't the parent
                    # Native create/update processes these values
                    continue

                # Reversed one-to-one looks like direct foreign keys but they
                # are reverse relations
                if direct:
                    relations[field_name] = (field, field.source)
                else:
                    reverse_relations[field_name] = (related_field, field, field.source)

            # May require the parent's id, which is added after validation
            elif issubclass(field.__class__, serializers.RelatedField):
                if field.source not in data:
                    continue
                relations[field_name] = (field, field.source)

            elif isinstance(field, serializers.ManyRelatedField):
                if field.source not in data:
                    continue
                reverse_relations[field_name] = (related_field, field, field.source)

        return relations, reverse_relations

    @classmethod
    def _get_direct_relations(cls, direct_relations, null):
        null_specified_relations = {}
        for field_name, (field, _) in direct_relations.items():
            if not (field.required) == null:
                null_specified_relations[field_name] = direct_relations[field_name]
        return null_specified_relations

    @classmethod
    def _get_nullable_direct_relations(cls, direct_relations):
        # Remove related fields from validated data for future manipulations
        return cls._get_direct_relations(direct_relations, null=True)

    @classmethod
    def _get_required_direct_relations(cls, direct_relations):
        return cls._get_direct_relations(direct_relations, null=False)

    @classmethod
    def xml_decode(cls, stream):
        """
        Parses XML module files for deserialization.

        Returns:
            byte encoded string.
        """
        from ery_backend.frontends.models import Frontend
        from ery_backend.labs.models import Lab
        from ery_backend.modules.models import ModuleDefinition
        from ery_backend.procedures.models import Procedure
        from ery_backend.stints.models import StintDefinition
        from ery_backend.templates.models import Template
        from ery_backend.themes.models import Theme
        from ery_backend.validators.models import Validator
        from ery_backend.widgets.models import Widget

        if cls.Meta.model == Widget:
            parser = WidgetXMLParser
        elif cls.Meta.model == Lab:
            parser = LabXMLParser
        elif cls.Meta.model == ModuleDefinition:
            parser = ModuleDefinitionXMLParser
        elif cls.Meta.model == Procedure:
            parser = ProcedureXMLParser
        elif cls.Meta.model == StintDefinition:
            parser = StintDefinitionXMLParser
        elif cls.Meta.model == Template:
            parser = TemplateXMLParser
        elif cls.Meta.model == Theme:
            parser = ThemeXMLParser
        elif cls.Meta.model == Validator:
            parser = ValidatorXMLParser
        elif cls.Meta.model == Frontend:
            parser = FrontendXMLParser
        else:
            raise Exception(f"No parser exists for {cls.Meta.model}")

        return parser().parse(BytesIO(stream))

    @staticmethod
    def set_empty(data_set):
        """
        Return boolean indicating if set has any non-null values.

        Note: Required due to use of None as placeholder in data_set.
        """
        return data_set is None or all(element is None for element in data_set)

    def delete_undeclared_reverse_relations(self, instance, data, reverse_relations):  # pylint:disable=too-many-branches
        # Reverse `reverse_relations` for correct delete priority
        reverse_relations = OrderedDict(reversed(list(reverse_relations.items())))

        # Delete instances which is missed in data
        for field_name, (related_field, field, field_source) in reverse_relations.items():
            related_data = data.get(field_name, [])
            if related_data is None:
                related_data = []

            if isinstance(field, serializers.ManyRelatedField):
                qs = field.child_relation.get_queryset()
                model_class = qs.model
                if issubclass(field.child_relation.__class__, serializers.SlugRelatedField):
                    pks_to_delete = qs.exclude(**{f'{field.child_relation.slug_field}__in': related_data}).values_list(
                        'pk', flat=True
                    )
                else:
                    qs = field.child_relation.get_queryset()
                    pks_to_delete = qs.exclude(pk__in=related_data).values_list('pk', flat=True)
            else:
                model_class = field.Meta.model
                if related_data is not None:
                    # Expand to array of one item for one-to-one for uniformity
                    if related_field.one_to_one:
                        related_data = [related_data]

                # M2M relation can be as direct or as reverse. For direct relation
                # we should use reverse relation name
                if related_field.many_to_many and not isinstance(related_field, ForeignObjectRel):
                    related_field_lookup = {
                        related_field.remote_field.name: instance,
                    }
                elif isinstance(related_field, GenericRelation):
                    related_field_lookup = self._get_generic_lookup(instance, related_field)
                else:
                    related_field_lookup = {
                        related_field.name: instance,
                    }

                if not isinstance(related_data, list):
                    raise ValidationError(
                        {self.get_error_context(field): f"Incorrect data type. Expected {list}, got {type(related_data)}"}
                    )

                # Allow for null declarations in order to remove all pre-existing relations
                current_ids = self._extract_related_pks(field, related_data) if related_data else []
                pks_to_delete = list(
                    model_class.objects.filter(**related_field_lookup).exclude(pk__in=current_ids).values_list('pk', flat=True)
                )
            try:
                if related_field.many_to_many:
                    # Remove relations from m2m table
                    m2m_manager = getattr(instance, field_source)
                    m2m_manager.remove(*pks_to_delete)
                else:
                    model_class.objects.filter(pk__in=pks_to_delete).delete()

            except ProtectedError as e:
                instances = e.args[1]
                self.fail('cannot_delete_protected', instances=", ".join([str(instance) for instance in instances]))

    @staticmethod
    def get_error_context(field):
        """
        Generate str path tracing the ancestry of a given serializer for error contextualization.

        Args:
            - field(:class:`rest_framework.fields.Field`)
        """
        ancestry = field.source
        parent = field.parent
        while parent:
            if parent.field_name:
                prefix = parent.field_name
            else:
                prefix = parent.Meta.model._meta.object_name

            ancestry = f'{to_snake_case(prefix)}.{ancestry}'
            parent = parent.parent

        return ancestry

    def get_minimally_valid_serializer(self):  # pylint:disable=too-many-branches
        """
        Generate instantiated model serializer with only its required relationships.

        All non-required relationships are separated to be created/updated by a queue hander through bounded methods.

        Notes:
            - Save is run on model serializer.

        Raises:
            - :class:`rest_framework.exceptions.ValidationError`: Triggered on failure to generate minimally valid serializer.

        Returns:
            - Tuple[:class:`ErySerializer', List]: List contains all queued create/update methods from current and
              nested serializers.
        """
        if not hasattr(self, 'initial_data'):
            raise ValidationError({self.__class__.__name__: "Has no data"})

        # better to keep initial_data unmodified in case of further development later on
        modified_data = copy.deepcopy(self.initial_data)

        pk_field = self.get_pk_attr()
        pk = modified_data.get(pk_field)

        queued_methods = []
        direct_relations, reverse_relations = self._get_relations(modified_data)
        required_direct_relations = self._get_required_direct_relations(direct_relations)
        nullable_direct_relations = self._get_nullable_direct_relations(direct_relations)
        # One to one parent_field is included in relations
        excludes = [self.Meta.model.parent_field, pk_field]
        nullable_direct_relation_data = {
            key: modified_data.pop(key) for key in nullable_direct_relations if key not in excludes
        }
        reverse_relation_data = {key: modified_data.pop(key) for key in reverse_relations if key not in excludes}
        for field_name, (field, _) in required_direct_relations.items():
            related_data = modified_data.get(field_name)
            if related_data is None:
                raise ValidationError({field_name: "This field is required"})
            if isinstance(field, ErySerializer):
                serializer = self._get_serializer_for_field(field, instance=None, data=related_data)
                pk_field = serializer.get_pk_attr()

                if not serializer.is_valid():
                    nested_minimal_serializer, nested_queued_methods = serializer.get_minimally_valid_serializer()
                    queued_methods += nested_queued_methods
                    modified_data[field_name] = nested_minimal_serializer.data
                    # Some serializers don't have pk as a readable field
                    modified_data[field_name][pk_field] = nested_minimal_serializer.instance.pk
                else:
                    # update modified_data with pk of instance made by serializer instead of instance
                    # in order to run is_valid, save on minimal serialier
                    serializer.save()
                    modified_data[field_name][pk_field] = serializer.instance.pk

        instance = self.Meta.model.objects.get(pk=pk) if pk else None

        minimal_serializer = self._get_serializer_for_field(self, instance=instance, data=modified_data)
        if not minimal_serializer.is_valid():
            raise ValidationError({minimal_serializer.__class__.__name__: minimal_serializer.errors})

        # save in order to guarantee minimal_serializer.data does not error when called later
        instance = minimal_serializer.save()
        self.delete_undeclared_reverse_relations(instance, reverse_relation_data, reverse_relations)

        # Add validated_id
        minimal_serializer.reset_is_valid()
        minimal_serializer.initial_data[pk_field] = instance.pk
        minimal_serializer.is_valid(raise_exception=True)

        # Some nullable relationships may be invalid because they require the serializer's instance/ file_instance

        nullable_relations_data = {**nullable_direct_relation_data, **reverse_relation_data}

        children_in_need_of_parents = {
            **{
                field_name: field
                for field_name, (field, _) in nullable_direct_relations.items()
                if isinstance(field, serializers.ModelSerializer)
            },
            **{
                field_name: field
                for field_name, (_, field, _) in reverse_relations.items()
                if isinstance(field, serializers.ModelSerializer)
            },
        }

        children_in_need_of_files = {
            **{
                field_name: field
                for field_name, (field, _) in nullable_direct_relations.items()
                if isinstance(field, FileDependentSlugRelatedField)
            },
            **{
                field_name: field
                for field_name, (_, field, _) in reverse_relations.items()
                if isinstance(field, serializers.ManyRelatedField)
                and isinstance(field.child_relation, FileDependentSlugRelatedField)
            },
        }

        for field_name, field in children_in_need_of_parents.items():
            if field_name in nullable_relations_data and nullable_relations_data[field_name] is not None:
                if field_name in nullable_direct_relation_data:
                    field.fill_parent_kwarg(field_name, nullable_direct_relation_data[field_name], instance)
                else:
                    field.fill_parent_kwarg(field_name, reverse_relation_data[field_name], instance)

        for field_name, field in children_in_need_of_files.items():
            if field_name in nullable_relations_data and nullable_relations_data[field_name] is not None:
                file_pk = instance.get_privilege_ancestor().pk
                if isinstance(field, serializers.ManyRelatedField):
                    field.child_relation.file_pk = file_pk
                else:
                    field.file_pk = file_pk

        return (
            minimal_serializer,
            [
                (
                    minimal_serializer.update_or_create_direct_relations,
                    {'attrs': nullable_direct_relation_data, 'relations': nullable_direct_relations},
                ),
                (
                    minimal_serializer.update_or_create_reverse_relations,
                    {'reverse_relations': reverse_relations, 'relations_data': reverse_relation_data},
                ),
                *queued_methods,
            ],
        )

    def handle_queue(self, queue):
        """
        Add docs
        """
        while len(queue) > 0:  # If queue can't be resolved at some point, invalid data
            old_queue = queue
            queue = []
            errors = []

            for (method, kwargs) in old_queue:
                nested_retry_info, nested_invalid_fields = method(**kwargs)
                queue += nested_retry_info
                errors += [
                    {self.get_error_context(invalid_field): invalid_field.errors} for invalid_field in nested_invalid_fields
                ]

            if old_queue == queue:
                raise serializers.ValidationError(errors)

    def _validate_and_save(self, nested, **kwargs):
        # Even if original is valid, we want to add nullable relations seperately to handle writable nested fields
        minimally_valid_serializer, queued_methods = self.get_minimally_valid_serializer()
        if not nested:
            self.handle_queue(queued_methods)
            return minimally_valid_serializer.instance
        return minimally_valid_serializer.instance, queued_methods

    def validate_and_save(self, nested=False, **kwargs):
        if not nested:
            with transaction.atomic():
                return self._validate_and_save(nested, **kwargs)
        return self._validate_and_save(nested, **kwargs)

    def create(self, validated_data):
        """
        Instantiate serializer model from validated data.

        Args:
            -  validated_data: Dict[str: Union[str, int, float, List, Dict]]: Generated from
              :py:meth:`ErySerializer`.is_valid`

        Returns:
            :class:`~ery_backend.base.models.EryModel`
        """
        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        info = model_meta.get_field_info(self.Meta.model)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        for field in self._writable_fields:
            if isinstance(field, serializers.ModelSerializer) and field.field_name in validated_data:
                data = validated_data[field.field_name]
                if isinstance(data, dict):  # Not yet converted
                    serializer = self._get_serializer_for_field(field, data=validated_data[field.field_name])
                    pk_name = serializer.get_pk_attr()
                    if pk_name in serializer.initial_data:
                        pk_data = serializer.initial_data[pk_name]
                        # If serializer initialized with validated data through a nested create, this may be a relation
                        if isinstance(pk_data, serializer.Meta.model):
                            original_instance = pk_data
                        else:
                            original_instance = serializer.Meta.model.objects.get(pk=pk_data)
                        nested_instance = serializer.update(original_instance, serializer.initial_data)
                    else:
                        nested_instance = serializer.create(serializer.initial_data)
                    validated_data[field.field_name] = nested_instance

        instance = self.Meta.model.objects.create(**validated_data)
        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in many_to_many.items():
                if value:
                    field = getattr(instance, field_name)
                    field.set(value)

        return instance

    def update(self, instance, validated_data):  # pylint:disable=too-many-branches
        """
        Update :class:`~ery_backend.base.models.EryModel` using validated data.

        Args:
            -  validated_data: Dict[str: Union[str, int, float, List, Dict]]: Generated from
              :py:meth:`ErySerializer`.is_valid`

        Returns:
            :class:`~ery_backend.base.models.EryModel`
        """

        pk_name = self.get_pk_attr()
        # Omitted from duplication serializers
        if not pk_name in validated_data:
            validated_data[pk_name] = instance.pk

        # ids are often PKRelatedFields for compatability with Mutation serializers.
        elif isinstance(validated_data[pk_name], instance.__class__):
            validated_data[pk_name] = instance.pk

        for field in self._writable_fields:
            if isinstance(field, serializers.ModelSerializer) and field.field_name in validated_data:
                data = validated_data[field.field_name]
                if isinstance(data, dict):  # Not yet converted
                    pk_name = serializer.get_pk_attr()
                    serializer = self._get_serializer_for_field(field, data=validated_data[field.field_name])
                    if pk_name in serializer.initial_data:
                        pk_data = serializer.initial_data[pk_name]
                        # If serializer initialized with validated data through a nested create, this may be a relation
                        if isinstance(pk_data, serializer.Meta.model):
                            original_instance = pk_data
                        else:
                            original_instance = serializer.Meta.model.objects.get(pk=pk_data)
                        nested_instance = serializer.update(original_instance, serializer.initial_data)
                    else:
                        nested_instance = serializer.create(serializer.initial_data)

                    validated_data[field.field_name] = nested_instance

        info = model_meta.get_field_info(instance)
        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        m2m_fields = []
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                m2m_fields.append((attr, value))
            else:
                setattr(instance, attr, value)
        instance.save()

        # Note that many-to-many fields are set after updating instance.
        # Setting m2m fields triggers signals which could potentially change
        # updated instance and we do not want it to collide with .update()
        for attr, value in m2m_fields:
            if value:
                field = getattr(instance, attr)
                field.set(value)

        return instance
