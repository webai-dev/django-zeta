import ast
import logging

import django
from django.core.exceptions import ValidationError
from django.db import transaction
import django_filters
import graphene
from graphene import relay
from graphql_relay import from_global_id
from reversion.models import Version, Revision
from rest_framework import serializers

from ery_backend.base.mixins import PrivilegedMixin
from ery_backend.base.utils import get_gql_id
from ery_backend.roles.utils import grant_ownership, has_privilege
from ery_backend.users.utils import authenticated_user

from .schema_utils import EryObjectType, EryFilterConnectionField
from .utils import verified_revert


logger = logging.getLogger(__name__)


class PrivilegedNodeMixin:
    """Standard get_node for privileged Graphene nodes"""

    @classmethod
    def get_node(cls, info, node_id, exclude_kwargs=None, filter_kwargs=None):
        user = authenticated_user(info.context)
        django_model = cls._meta.model
        data_loader = info.context.get_data_loader(django_model)

        qs = cls._meta.model.objects
        if filter_kwargs:
            qs = qs.filter(**filter_kwargs)
        if exclude_kwargs:
            qs = qs.exclude(**exclude_kwargs)
        django_object = qs.get(pk=node_id)

        if has_privilege(django_object, user, 'read'):
            return data_loader.load(django_object.id)

        raise ValueError("not authorized")


class EryMutationMixin:
    """Automatically handle common input patterns"""

    @classmethod
    def gql_id_to_pk(cls, gql_id):
        """
        Get the django primary key from a gql id
        """
        _, pk = from_global_id(gql_id)

        try:
            return int(pk)
        except ValueError:
            return pk

    @classmethod
    def _get_attribute(cls, field, input_data):
        logger.debug("Adding attribute {%s: %s}", field, input_data)

        if isinstance(field, django.db.models.fields.related.ForeignKey):
            if isinstance(input_data, str):
                key = cls.gql_id_to_pk(input_data)
                return field.related_model.objects.get(pk=key)
            if input_data is None:
                if not field.null:
                    logger.error("Could not set field '%s' to None as the field is non-nullable.", field.name)
        elif input_data is not None:
            return input_data

        return None

    @classmethod
    def get_all_attributes(cls, model_class, graphene_input):
        """item: django.Model requiring additions
        graphene_input: graphene.InputObjectType, instantiated with desired data
        """
        ret = {}

        for input_field, input_data in graphene_input.items():
            try:
                field = model_class._meta.get_field(input_field)
                ret[field.name] = cls._get_attribute(field, input_data)
            except django.core.exceptions.FieldDoesNotExist:
                logger.error("Field '%s' does not exist on %s.", input_field, model_class._meta.verbose_name_plural)

        return ret

    @classmethod
    def add_all_attributes(cls, item, graphene_input):
        """item: django.Model requiring additions
        graphene_input: graphene.InputObjectType, instantiated with desired data
        """

        for input_field, input_data in graphene_input.items():
            try:
                field = item._meta.get_field(input_field)  # pylint:disable=protected-access
                setattr(item, field.name, cls._get_attribute(field, input_data))
            except django.core.exceptions.FieldDoesNotExist:
                # pylint:disable=protected-access
                logger.error("Field '%s' does not exist on %s.", input_field, item._meta.verbose_name_plural)


class NamedNode(relay.Node):
    name = graphene.String()
    comment = graphene.String()
    created = graphene.DateTime()
    modified = graphene.DateTime()
    state = graphene.String()


class VersionFilter(django_filters.FilterSet):
    class Meta:
        model = Version
        fields = ['content_type_id', 'object_id', 'revision__user']


class VersionNode(EryObjectType):
    class Meta:
        model = Version
        interfaces = (relay.Node,)
        filter_privilege = False
        use_dataloader = False

    @classmethod
    def get_node(cls, info, node_id):
        return cls._meta.model.objects.get(pk=node_id)


class VersionQuery:
    version = relay.Node.Field(VersionNode)


class VersionMixin:
    versions = EryFilterConnectionField(VersionNode)

    def resolve_versions(self, info):
        user = authenticated_user(info.context)
        if has_privilege(self, user, 'view_versions'):
            qs = Version.objects.get_for_object(self)
        else:
            qs = Version.objects.get_for_object(self).filter(revision__user=user)
        return qs


class VersionInput(graphene.ObjectType):
    gql_id = graphene.Int()


class RevertVersion(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(required=True, description="Gql ID of the Version to revert")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        django_pk = cls.gql_id_to_pk(inputs.pop('id'))
        version = Version.objects.get(pk=django_pk)

        if not has_privilege(version.object, user, 'update'):
            raise ValueError("not authorized")

        verified_revert(version)
        return RevertVersion(success=True)


class VersionMutation:
    revert_version = RevertVersion.Field()


class RevisionNode(EryObjectType):
    class Meta:
        model = Revision
        interfaces = (relay.Node,)
        use_dataloader = False
        filter_privilege = False

    @classmethod
    def get_node(cls, info, node_id):
        return cls._meta.model.objects.get(pk=node_id)


class RevisionQuery:
    revision = relay.Node.Field(RevisionNode)
    all_revisions = EryFilterConnectionField(RevisionNode)


class RevertRevision(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(required=True, description='Gql ID of the Revision to revert.')

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        django_pk = cls.gql_id_to_pk(inputs.pop('id'))
        revision = Revision.objects.get(pk=django_pk)

        with transaction.atomic():
            for version in revision.version_set.all():
                if not has_privilege(version.object, user, 'update'):
                    raise ValueError("not authorized")
                verified_revert(version)

        return RevertRevision(success=True)


class RevisionMutation:
    revert_revision = RevertRevision.Field()


class ErySerializerMutationMixin:
    class Meta:
        convert_choices_to_enum = False

    @classmethod
    def convert_pk_id(cls, value):
        try:
            return from_global_id(value)[1]
        except Exception as e:  # incorrect padding
            raise Exception(f'Error during convert_pk_ids for {cls} with value: {value}... {e}')

    @classmethod
    def convert_pk_ids(cls, values):
        if not isinstance(values, list):
            raise ValidationError({'value': f"Expected list of values to convert to django ids. Got {values}"})
        return [cls.convert_pk_id(value) for value in values]

    @classmethod
    def convert_ids(cls, serializer_fields, item_info):
        def convert_model_serializer_ids(model_serializer, data):
            error_msg = {'data': f"data must be a single dictionary or list of dictionaries, not {data}"}
            if not isinstance(data, dict) and not (
                isinstance(data, list) and all([isinstance(item_info, dict) for item_info in data])
            ):
                raise ValidationError(error_msg)

            if isinstance(data, list):
                for item_info in data:
                    cls.convert_ids(model_serializer, item_info)
            else:
                cls.convert_ids(model_serializer, data)

            return data

        # many=True
        for field_name, value in item_info.items():
            if value is not None and field_name in serializer_fields:
                serializer_field = serializer_fields[field_name]
                if isinstance(serializer_field, serializers.ListSerializer):
                    values = ast.literal_eval(str(value))
                    if isinstance(serializer_field.child, serializers.ModelSerializer):  # list of dicts
                        item_info[field_name] = convert_model_serializer_ids(serializer_field.child.fields, values)
                    elif isinstance(serializer_field.child, serializers.PrimaryKeyRelatedField):
                        item_info[field_name] = cls.convert_pk_ids(values)
                elif isinstance(serializer_field, serializers.ModelSerializer):
                    item_info[field_name] = convert_model_serializer_ids(serializer_field.fields, value)
                elif isinstance(serializer_field, serializers.PrimaryKeyRelatedField):
                    item_info[field_name] = cls.convert_pk_id(value)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **user_input):
        model_serializer = cls._meta.serializer_class
        cls.convert_ids(model_serializer().fields, user_input)
        kwargs = cls.get_serializer_kwargs(root, info, **user_input)
        serializer_instance = model_serializer(**kwargs)
        return cls.perform_mutate(serializer_instance, info)

    @classmethod
    def perform_mutate(cls, serializer, info):
        from .models import EryFile

        many_field_types = (
            django.db.models.fields.reverse_related.ManyToOneRel,
            django.db.models.fields.reverse_related.ManyToManyRel,
            django.db.models.fields.related.ManyToManyField,
        )

        obj = serializer.validate_and_save()
        if issubclass(cls, PrivilegedMixin) and obj.get_privilege_ancestor() == obj:
            grant_ownership(obj.get_privilege_ancestor(), info.context.user)

        kwargs = {serializer.get_pk_attr(): obj.gql_id} if not issubclass(cls._meta.model_class, EryFile) else {}
        for field_name, field in serializer.fields.items():
            if not field.write_only:
                # pylint: disable=protected-access
                model_field = serializer.get_model_field(cls._meta.model_class, field_name)
                if hasattr(field, 'pk_field'):  # PK fields need conversion (id/iso_639_1)
                    # pk field, which is a PrimaryKeyrelatedField, doesn't not have a related model
                    field_model = model_field.related_model if model_field.related_model else model_field.model
                    pk_obj = field.get_attribute(obj)
                    value = get_gql_id(field_model._meta.object_name, pk_obj.pk) if pk_obj.pk else None
                else:
                    if model_field.is_relation:
                        field_model = model_field.related_model
                        # because isinstance(OneToOne field, reverse_relatd.ManyToOneRel) is true
                        if type(model_field) in many_field_types:  # pylint: disable=unidiomatic-typecheck
                            qs = field.get_attribute(obj)
                            value = qs.all()
                        else:
                            initial_value = field.get_attribute(obj)
                            pk = initial_value.pk if hasattr(initial_value, 'pk') else None
                            value = get_gql_id(field_model._meta.object_name, pk) if pk else None
                    else:
                        value = field.get_attribute(obj)

                kwargs[field_name] = value
        return cls(errors=None, **kwargs)
