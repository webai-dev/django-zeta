import os

from tools import confirm

model_name = confirm(input('Enter model name: '))
model_name_slug = confirm(input('Enter model name slug: '))
model_name_camel = model_name[0].lower() + model_name[1:]
node_name = f"{model_name}Node"
multi_line_quote = '\"\"\"'
versions = confirm(input('Versions? Enter y or n: '))
module_definition_model = confirm(input('Is this a ModuleDefinitionModel?. Enter y or n: '))
ery_file_model = confirm(input('Is this an EryFileModel?. Enter y or n: '))


imports = f"""
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from ery_backend import roles
from ery_backend.base.schema import EryMutationMixin, VersionMixin
{'from ery_backend.modules.models import ModuleDefinition' if module_definition_model == 'y' else ''}
from ery_backend.roles.schema import RoleAssignmentNodeMixin
from ery_backend.users.utils import authenticated_user

from .models import {model_name}
"""

node_inheritance = (
    "RoleAssignmentNodeMixin, VersionMixin, DjangoObjectType" if versions else "RoleAssignmentNodeMixin, DjangoObjectType"
)

node_code = f"""
class {node_name}({node_inheritance}):
    class Meta:
        model = {model_name}
        interfaces = (relay.Node,)
        filter_fields = []
"""

filter_code = (
    f'return {model_name}.objects.filter_privilege("read", user)'
    if ery_file_model == 'n'
    else f'return {model_name}.objects.filter_privilege("read", user).exclude(' f'state={model_name}.STATE_CHOICES.deleted)'
)

query_code = f"""
class {model_name}Query():
    {model_name_slug} = relay.Node.Field({node_name})
    all_{model_name_slug}s = DjangoFilterConnectionField({node_name})

    def resolve_all_{model_name_slug}s(self, info):
        user = authenticated_user(info.context)
        {filter_code}
"""

input_code = f"""
class Input{model_name}:
    pass
"""

module_definition_create_code = None
if module_definition_model == 'y':
    create_input_code = (
        f'module_definition = graphene.ID(\n{" "*12}'
        f'description="GQL ID of the parental ModuleDefinition",\n{" "*12}required=True)'
    )
    module_definition_create_code = f"""
        mdid = cls.gql_id_to_pk(inputs["module_definition"])
        md = ModuleDefinition.objects.get(pk=mdid)

        if md is None:
            raise ValueError("moduleDefinition not found")

        if not roles.utils.has_privilege(md, user, "create"):
            raise ValueError("not authorized")
"""

create_code = f"""
class Create{model_name}(EryMutationMixin, relay.ClientIDMutation):
    {model_name_slug} = graphene.Field({node_name})

    class Input(Input{model_name}):
        {'pass' if not module_definition_model == 'y' else create_input_code}

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        {'user = authenticated_user(info.context)' if module_definition_model == 'y' else 'authenticated_user(info.context)'}
        {module_definition_create_code if module_definition_model == 'y' else ''}
        {model_name_slug} = {model_name}()
        cls.add_all_attributes({model_name_slug}, inputs)
        {model_name_slug}.save()

        return Create{model_name}({model_name_slug}={model_name_slug})
"""

update_code = f"""
class Update{model_name}(EryMutationMixin, relay.ClientIDMutation):
    {model_name_slug} = graphene.Field({node_name})

    class Input(Input{model_name}):
        id = graphene.ID(description="GQL ID of the {model_name}", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        {model_name_slug}_id = cls.gql_id_to_pk(inputs.pop("id"))
        {model_name_slug} = {model_name}.objects.get(pk={model_name_slug}_id)

        if {model_name_slug} is None:
            raise ValueError("{model_name} not found")

        if not roles.utils.has_privilege({model_name_slug}, user, "update"):
            raise ValueError("not authorized")

        cls.add_all_attributes({model_name_slug}, inputs)
        {model_name_slug}.save()

        return Update{model_name}({model_name_slug}={model_name_slug})
"""

delete_model_statement = '{model_name_slug}.soft_delete()' if ery_file_model == 'y' else f'{model_name_slug}.delete()'
delete_code = f"""
class Delete{model_name}(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()

    class Input():
        id = graphene.ID(description="GQL ID of the {model_name}", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        {model_name_slug}_id = cls.gql_id_to_pk(inputs.pop("id"))
        {model_name_slug} = {model_name}.objects.get(pk={model_name_slug}_id)

        if {model_name_slug} is None:
            raise ValueError("{model_name} not found")

        if not roles.utils.has_privilege({model_name_slug}, user, "delete"):
            raise ValueError("not authorized")

        {delete_model_statement}

        return Delete{model_name}(success=True)
"""

mutation_code = f"""
class {model_name}Mutation():
    create_{model_name_slug} = Create{model_name}.Field()
    update_{model_name_slug} = Update{model_name}.Field()
    delete_{model_name_slug} = Delete{model_name}.Field()
"""

output_location = f'{os.getcwd()}/schema_code.py'
with open(output_location, 'w') as f:
    f.write('\n'.join([imports, node_code, query_code, input_code, create_code, update_code, delete_code, mutation_code]))
