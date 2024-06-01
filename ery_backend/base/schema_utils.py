import django  # Needed to migrate
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from django.db.models.fields.related import ForeignKey

import django_filters
import graphene
from graphene import relay
from graphene.types.resolver import dict_resolver
from graphene_django.fields import DjangoConnectionField
from graphene_django.filter.fields import DjangoFilterConnectionField
from graphene_django.filter.filterset import custom_filterset_factory
from graphene_django.registry import set_connection_fields
from graphene_django.types import DjangoObjectType, DjangoObjectTypeOptions
from graphql_relay.node.node import from_global_id

from ery_backend.base.mixins import PrivilegedMixin
from ery_backend.base.utils import to_snake_case
from ery_backend.users.utils import authenticated_user
from ery_backend.roles.utils import has_privilege


class CountableConnection(relay.Connection):
    class Meta:
        abstract = True

    total_count = graphene.Int()

    def resolve_total_count(self, info):
        return self.unlimited_iterable.count()


def ery_object_default_resolver(attname, default_value, root, info, **args):
    """
    Overrides functionality of the default graphene resolver, adding dataloader integration.

    Args:
        attname (str)
        default_value (str)
        root (:class:`django.db.models.Model`)
        info (Dict): Graphql info dictionary.
        args (Dict): Additional kwargs

    Note: Taken from graphene.types.resolvers.dict_or_attr_resolver

    Returns:
        Union(int, float, :class:`django.db.models.Model`, str, List, Dict)
    """

    def ery_attr_resolver(attname, default_value, root, info, **args):
        from ery_backend.base.models import EryModel
        from ery_backend.users.models import User

        if issubclass(root.__class__, EryModel) or isinstance(root, User) and hasattr(root, attname):
            try:
                field = root._meta.get_field(attname)
            except FieldDoesNotExist:
                pass
            else:
                if isinstance(field, ForeignKey) and hasattr(field, "id"):
                    related_id = getattr(root, f"{attname}_id")
                    if related_id is not None:
                        return info.context.get_data_loader(field.related_model).load(related_id)

        return getattr(root, attname, default_value)

    resolver = ery_attr_resolver
    if isinstance(root, dict):
        resolver = dict_resolver
    return resolver(attname, default_value, root, info, **args)


def _is_reverse_model_field(model, field_name):
    return isinstance(model._meta.get_field(field_name), django.db.models.fields.reverse_related.OneToOneRel)


def _get_many_to_many_attrs(model, attrs):
    m2m_attrs = {}
    related_attr_names = [ro.name for ro in list(model._meta.related_objects) + list(model._meta.local_many_to_many)]
    for attr in attrs:
        # don't include reverse relationships
        if attr in related_attr_names and not _is_reverse_model_field(model, attr):
            m2m_attrs[attr] = attrs[attr]

    return m2m_attrs


def _set_many_to_many_attrs(obj, m2m_attrs):
    for attr in m2m_attrs:
        m2m_field = getattr(obj, attr)
        gql_ids = m2m_attrs[attr]
        stripped_gql_ids = gql_ids.strip("][")
        if stripped_gql_ids:
            for gql_id in stripped_gql_ids.split(","):
                _, pk = from_global_id(gql_id.strip("' "))
                m2m_field.add(m2m_field.model.objects.get(pk=pk))
    return m2m_attrs


class EryObjectTypeOptions(DjangoObjectTypeOptions):
    model_field_name = None
    filter_privilege = None
    use_dataloader = None
    use_connection = None


class EryObjectType(DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        connection=None,
        connection_class=None,
        model=None,
        filter_fields=None,
        filterset_class=None,
        interfaces=(),
        filter_privilege=True,
        use_connection=None,
        use_dataloader=True,
        _meta=None,
        **options,
    ):
        if not filter_fields and not filterset_class:
            filterset_class = cls._get_default_filterset(model)

        if not interfaces:
            interfaces = cls._get_default_interfaces(model)

        if not _meta:
            _meta = EryObjectTypeOptions(cls)

        if use_connection is None and interfaces:
            use_connection = any((issubclass(interface, relay.Node) for interface in interfaces))

        if use_connection and not connection:
            # We create the connection automatically
            if not connection_class:
                connection_class = CountableConnection
            connection = connection_class.create_type("{}Connection".format(cls.__name__), node=cls)

        _meta.connection = connection
        _meta.filterset_class = filterset_class
        _meta.model_field_name = model.get_field_name() if hasattr(model, "get_field_name") else to_snake_case(model.__name__)
        _meta.filter_privilege = filter_privilege
        _meta.use_dataloader = use_dataloader
        _meta.use_connection = use_connection

        super(EryObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta,
            model=model,
            filterset_class=filterset_class,
            interfaces=interfaces,
            connection=connection,
            use_connection=use_connection,
            connection_class=CountableConnection,
            default_resolver=ery_object_default_resolver,
            **options,
        )

    @staticmethod
    def _get_default_filterset(model):
        from django.contrib.postgres.fields import JSONField

        filterset_base_class = django_filters.FilterSet

        field_names = {}
        for field in model._meta.fields + model._meta.many_to_many:
            if isinstance(field, JSONField):
                continue

            field_names[field.name] = ["exact"]

            if isinstance(field, models.CharField):
                field_names[field.name].append("icontains")

            if field.related_model and "name" in [f.name for f in field.related_model._meta.fields]:
                field_names[f"{field.name}__name"] = ["exact", "icontains"]

        return custom_filterset_factory(model, filterset_base_class=filterset_base_class, **{"fields": field_names})

    @staticmethod
    def _get_default_interfaces(model):
        from ery_backend.folders.schema_interfaces import EryFileInterface

        from .models import EryModel, EryNamed, EryNamedSlugged, EryFile
        from .schema_interfaces import EryInterface, EryNamedInterface

        if issubclass(model, EryFile):
            return (relay.Node, EryFileInterface)
        if issubclass(model, EryNamed) or issubclass(model, EryNamedSlugged):
            return (relay.Node, EryNamedInterface)
        if issubclass(model, EryModel):
            return (relay.Node, EryInterface)

        return (relay.Node,)

    @classmethod
    def get_create_mutation_class(cls, input_class):
        from ery_backend.folders.schema import LinkEdge
        from .models import EryFile
        from .schema import EryMutationMixin

        model = cls._meta.model
        model_name = cls._meta.model_field_name
        new_class_name = f"Create{model.__name__}"
        edge_class = cls._meta.connection.Edge

        @classmethod
        def mutate_and_get_payload(cls, root, info, **inputs):
            from ery_backend.folders.models import Folder

            attrs = {}
            m2m_attrs = {}
            privileged = issubclass(model, PrivilegedMixin)
            has_parent = hasattr(model, "parent_field") and getattr(model, "parent_field") is not None
            user = authenticated_user(info.context)
            if privileged and has_parent:
                pk = cls.gql_id_to_pk(inputs.pop(model.parent_field))
                parent_obj = model.get_parent_model().objects.get(pk=pk)
                if not has_privilege(parent_obj, user, "update"):
                    raise ValueError("not authorized")

                attrs.update({model.parent_field: parent_obj})

            attrs.update(cls.get_all_attributes(model, inputs))
            m2m_attrs = _get_many_to_many_attrs(model, attrs)
            ret = {}
            with transaction.atomic():
                if privileged and not has_parent:
                    obj = model.objects.create_with_owner(
                        user, **{name: value for name, value in attrs.items() if name not in m2m_attrs},
                    )
                    if issubclass(model, EryFile):
                        if "folder" in inputs:
                            folder = Folder.objects.get(pk=cls.gql_id_to_pk(inputs.pop("folder")))
                            if has_privilege(folder, user, "update"):
                                obj.create_link(folder)
                                ret["link_edge"] = LinkEdge(node=folder)
                else:
                    obj = model.objects.create(**{name: value for name, value in attrs.items() if name not in m2m_attrs})
                _set_many_to_many_attrs(obj, m2m_attrs)
                ret[f"{model_name}_edge"] = edge_class(node=obj)

            return cls(**ret)

        input_attrs = {}
        if model.parent_field is not None:
            input_attrs[model.parent_field] = graphene.ID(
                description=f"GQL ID of parent field ({model.parent_field})", required=True,
            )
        if issubclass(model, EryFile):
            # If 'folder'-field is filled, create a Link instance to stash the EryFile into the given Folder
            input_attrs["folder"] = graphene.ID(description=f"GQL ID of folder")

        classattrs = {
            f"{model_name}_edge": graphene.Field(edge_class, required=True),
            "Input": type("Input", (input_class,), input_attrs),
            "mutate_and_get_payload": mutate_and_get_payload,
            "_model": model,
        }

        if model.parent_field is not None:
            classattrs["_parent_model"] = model.get_parent_model()

        if isinstance(model, EryFile):
            classattrs["link_edge"] = graphene.Field(LinkEdge)

        return type(new_class_name, (EryMutationMixin, relay.ClientIDMutation), classattrs)

    @classmethod
    def get_update_mutation_class(cls, input_class):
        from ery_backend.base.schema import EryMutationMixin

        model = cls._meta.model
        model_name = cls._meta.model_field_name
        new_class_name = f"Update{model.__name__}"

        @classmethod
        def mutate_and_get_payload(cls, root, info, **inputs):
            user = authenticated_user(info.context)
            pk = cls.gql_id_to_pk(inputs.pop("id"))
            obj = cls._model.objects.get(pk=pk)

            if not has_privilege(obj, user, "update"):
                raise ValueError("not authorized")
            attrs = cls.get_all_attributes(model, inputs)
            m2m_attrs = _get_many_to_many_attrs(model, attrs)

            obj = model.objects.get(pk=pk)
            for name, value in attrs.items():
                if name not in m2m_attrs:
                    setattr(obj, name, value)
            _set_many_to_many_attrs(obj, m2m_attrs)
            obj.save()
            return cls(**{model_name: obj})

        classattrs = {
            f"{model_name}": graphene.Field(cls, required=True),
            "Input": type("Input", (input_class,), {"id": graphene.ID(description=f"GQL ID of {model_name}", required=True)},),
            "mutate_and_get_payload": mutate_and_get_payload,
            "_model": model,
        }
        return type(new_class_name, (EryMutationMixin, relay.ClientIDMutation), classattrs)

    @classmethod
    def get_delete_mutation_class(cls, input_class):
        from ery_backend.base.schema import EryMutationMixin

        model = cls._meta.model
        model_name = cls._meta.model_field_name
        new_class_name = f"Delete{model.__name__}"

        @classmethod
        def mutate_and_get_payload(cls, root, info, **inputs):
            user = authenticated_user(info.context)
            gql_id = inputs.pop("id")
            pk = cls.gql_id_to_pk(gql_id)
            obj = cls._model.objects.get(pk=pk)

            if not has_privilege(obj, user, "delete"):
                raise ValueError("not authorized")

            if hasattr(obj, "soft_delete"):
                obj.soft_delete()
            else:
                obj.delete()

            # pylint:disable=unexpected-keyword-arg,no-value-for-parameter
            return cls(id=gql_id)

        classattrs = {
            "id": graphene.GlobalID(required=True),
            "Input": type("Input", (input_class,), {"id": graphene.ID(description=f"GQL ID of {model_name}", required=True)},),
            "mutate_and_get_payload": mutate_and_get_payload,
            "_model": model,
        }
        return type(new_class_name, (EryMutationMixin, relay.ClientIDMutation), classattrs)

    @classmethod
    def get_mutation_input(cls):
        def _get_graphene_input_field_from_django_field(field):
            kwargs = {}
            if hasattr(field, "help_text"):
                kwargs["description"] = field.help_text
            conversions = {
                django.db.models.fields.related.ForeignKey: graphene.ID,
                django.db.models.fields.related.OneToOneField: graphene.ID,
                django.db.models.fields.related_descriptors.create_forward_many_to_many_manager: graphene.List,
                django.db.models.fields.related_descriptors.create_reverse_many_to_one_manager: graphene.List,
                django.db.models.fields.BooleanField: graphene.Boolean,
                django.db.models.FloatField: graphene.Float,
                django.db.models.DecimalField: graphene.Float,
                django.db.models.IntegerField: graphene.Int,
                django.db.models.PositiveIntegerField: graphene.Int,
                django.db.models.DateField: graphene.Date,
                django.db.models.DateTimeField: graphene.DateTime,
                django.db.models.TimeField: graphene.Time,
                django.contrib.postgres.fields.JSONField: graphene.JSONString,
            }

            if type(field) in conversions:  # pylint:disable=unidiomatic-typecheck
                return conversions[type(field)](**kwargs)

            return graphene.String(**kwargs)

        exclude_field_names = ["id", "created", "modified", "slug"]

        django_fields = {
            field.name: field
            for field in sorted(list(cls._meta.model._meta.fields) + list(cls._meta.model._meta.local_many_to_many))
        }
        fields = {
            field_name: _get_graphene_input_field_from_django_field(field)
            for field_name, field in django_fields.items()
            if field.name not in exclude_field_names
        }

        return type(f"{cls._meta.model.__name__}MutationInput", tuple(), fields)

    @classmethod
    def get_query_class(cls):
        model_name = cls._meta.model_field_name
        return type(
            f"{cls._meta.model.__name__}Query",
            tuple(),
            {model_name: relay.Node.Field(cls), f"all_{model_name}s": EryFilterConnectionField(cls),},
        )

    @classmethod
    def get_mutation_class(cls):
        input_class = cls.get_mutation_input()
        name = f"{cls._meta.model._meta.verbose_name.replace(' ', '_')}"
        return type(
            f"{name}Mutation",
            tuple(),
            {
                f"create_{name}": cls.get_create_mutation_class(input_class).Field(),
                f"update_{name}": cls.get_update_mutation_class(input_class).Field(),
                f"delete_{name}": cls.get_delete_mutation_class(input_class).Field(),
            },
        )


class EryConnectionField(DjangoConnectionField):
    def __init__(self, *args, **kwargs):
        self._add_ery_fields(kwargs)
        super().__init__(*args, **kwargs)

    @staticmethod
    def _add_ery_fields(kwargs):
        kwargs["ids"] = graphene.List(graphene.ID)
        kwargs["offset"] = graphene.Int()
        kwargs["limit"] = graphene.Int()

    @staticmethod
    def apply_ery_filters(qs, kwargs):
        if "ids" in kwargs:
            django_ids = [from_global_id(gql_id)[1] for gql_id in kwargs["ids"]]
            qs = qs.filter(id__in=django_ids)

        return qs

    @staticmethod
    def _filter_foreign_key(qs, kwarg, value, field):
        possible_fk_field = f"{kwarg}_id"
        node_name, django_id = from_global_id(value)
        expected_node_name = f"{field.related_model.__name__}Node"
        if node_name == expected_node_name:
            filter_kwarg = {possible_fk_field: django_id}
            return qs.filter(**filter_kwarg)
        return qs

    @classmethod
    def apply_id_filters(cls, qs, kwargs):
        from ery_backend.base.models import EryModel
        from ery_backend.users.models import User

        output_qs = qs
        if issubclass(qs.model, EryModel) or qs.model == User:
            for kwarg in kwargs:
                if hasattr(qs.model, kwarg):
                    try:
                        field = qs.model._meta.get_field(kwarg)
                        if isinstance(field, ForeignKey):
                            return cls._filter_foreign_key(qs, kwarg, kwargs[kwarg], field)
                    except FieldDoesNotExist:
                        pass
        return output_qs

    @staticmethod
    def apply_ery_limits(qs, kwargs):
        offset = kwargs.get("offset", 0)
        limit = kwargs.get("limit")

        if limit:
            return qs[offset : offset + kwargs["limit"]]
        if offset:
            return qs[offset:]

        return qs

    @classmethod
    def _resolve_queryset(cls, connection, queryset, info, args):
        qs = connection._meta.node.get_queryset(queryset, info)
        qs = cls.apply_ery_filters(qs, args)
        qs = cls.apply_id_filters(qs, args)

        node_meta = connection._meta.node._meta
        if issubclass(node_meta.model, PrivilegedMixin) and node_meta.filter_privilege:
            if not hasattr(info.context, "user") or not info.context.user:
                raise ValueError("not authorized")

            qs = qs.filter_privilege("read", info.context.user)

        return qs

    @classmethod
    def resolve_queryset(cls, connection, queryset, info, args):
        qs = cls._resolve_queryset(connection, queryset, info, args)
        return qs.from_dataloader(info.context)

    @classmethod
    def resolve_connection(cls, connection, args, iterable):
        unlimited_iterable = iterable._chain()  # pylint: disable=protected-access
        iterable = cls.apply_ery_limits(iterable, args)

        connection = super().resolve_connection(connection, args, iterable)
        connection.unlimited_iterable = unlimited_iterable

        return connection


class EryFilterConnectionField(DjangoFilterConnectionField, EryConnectionField):
    @classmethod
    def resolve_queryset(cls, connection, iterable, info, args, filtering_args, filterset_class):
        if isinstance(iterable, list) and iterable:
            iterable = iterable[0]._meta.model.objects.filter(pk__in=[element.pk for element in iterable])
        qs = super(EryFilterConnectionField, cls)._resolve_queryset(connection, iterable, info, args)
        filter_kwargs = {k: v for k, v in args.items() if k in filtering_args}
        return filterset_class(data=filter_kwargs, queryset=qs, request=info.context).qs


set_connection_fields(EryConnectionField, EryFilterConnectionField)
