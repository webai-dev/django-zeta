import os

from ery_backend.base.utils import get_loggedin_client
from ery_backend.roles.utils import grant_ownership
from ery_backend.frontends.models import Frontend
from ery_backend.labs.models import Lab
from ery_backend.modules.models import ModuleDefinition
from ery_backend.stints.models import StintDefinition
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from ery_backend.users.models import User
from ery_backend.validators.models import Validator
from ery_backend.widgets.models import Widget


user = User.objects.first()
client = get_loggedin_client(user)


def run(path):  # pylint:disable=too-many-branches
    default_path = 'fixtures/bxmls'
    path_parts = path.split('/')
    for i in range(1, len(path_parts) + 1):
        if not os.path.exists('/'.join(path_parts[:i])):
            os.mkdir('/'.join(path_parts[:i]))

    is_default_path = path == default_path
    for file_type, file_cls in (
        ('frontend', Frontend),
        ('lab', Lab),
        ('stint_definition', StintDefinition),
        ('theme', Theme),
        ('template', Template),
        ('widget', Widget),
        ('validator', Validator),
    ):
        if not os.path.exists(f'{default_path}/{file_type}s'):
            os.mkdir(f'{default_path}/{file_type}s')
        if not os.path.exists(f'{path}/{file_type}s'):
            os.mkdir(f'{path}/{file_type}s')

        default_file_slugs = []
        if not is_default_path:
            default_file_slugs = [file_name.split('.')[0] for file_name in os.listdir(f'{default_path}/{file_type}s')]
        for file_instance in file_cls.objects.exclude(slug__in=default_file_slugs).all():
            if not file_instance.slug:
                file_instance.save()
            grant_ownership(file_instance, user)
            response = client.get(f'http://localhost:8000/export/{file_type}/{file_instance.gql_id}/slugged')
            if response.status_code != 200:
                raise Exception(f"Could not export {file_type}: {file_instance}. Status code: {response.status_code}")
            with open(f'{path}/{file_type}s/{file_instance.slug}.bxml', 'wb') as f:
                f.write(response.content)

    if not os.path.exists(f'{default_path}/module_definitions'):
        os.mkdir(f'{default_path}/module_definitions')
    if not os.path.exists(f'{path}/module_definitions'):
        os.mkdir(f'{path}/module_definitions')

    if not is_default_path:
        default_file_slugs = [file_name.split('.')[0] for file_name in os.listdir(f'{default_path}/module_definitions')]
    for module_definition in (
        ModuleDefinition.objects.exclude(slug__in=default_file_slugs)
        .filter(stint_definition_module_definitions__isnull=True)
        .all()
    ):
        if not module_definition.slug:
            module_definition.save()
        grant_ownership(module_definition, user)
        response = client.get(f'http://localhost:8000/export/module_definition/{module_definition.gql_id}/slugged')
        if response.status_code != 200:
            raise Exception(f"Could not export module_definition: {module_definition}. Status code: {response.status_code}")

        with open(f'{path}/module_definitions/{module_definition.slug}.bxml', 'wb') as f:
            f.write(response.content)
