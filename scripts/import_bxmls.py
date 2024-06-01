import os

from django.db import transaction
import django.core.exceptions
from rest_framework import serializers

from ery_backend.frontends.models import Frontend
from ery_backend.labs.models import Lab
from ery_backend.modules.models import ModuleDefinition
from ery_backend.stints.models import StintDefinition
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from ery_backend.validators.models import Validator
from ery_backend.widgets.models import Widget


base_file_dir_path = '../fixtures/bxmls'
model_map = {
    'frontends': Frontend,
    'labs': Lab,
    'module_definitions': ModuleDefinition,
    'stint_definitions': StintDefinition,
    'templates': Template,
    'themes': Theme,
    'widgets': Widget,
    'validators': Validator,
}


def handle_queue(queue):
    """
    Add docs
    """
    # reimported due to scoping when running scripts in shell
    from rest_framework import serializers  # pylint: disable=redefined-outer-name, reimported

    while len(queue) > 0:  # If queue can't be resolved at some point, invalid data
        old_queue = queue
        queue = []
        errors = []

        for method, path in old_queue:
            try:
                failed_file_bytes = open(path, 'rb')
                method(failed_file_bytes)
            except serializers.ValidationError as exc:
                queue.append((method, path))
                errors.append({path: exc})
            finally:
                failed_file_bytes.close()
        if old_queue == queue:
            raise serializers.ValidationError(errors)


def run(path):
    with transaction.atomic():
        fail_queue = []
        for model_path in model_map:
            if os.path.exists(f'{path}/{model_path}'):
                for instance_path in os.listdir(f'{path}/{model_path}'):
                    try:
                        file_bytes = open(f'{path}/{model_path}/{instance_path}', 'rb')
                        model_map[model_path].import_instance_from_xml(file_bytes)
                    except (serializers.ValidationError, django.core.exceptions.ValidationError):
                        fail_queue.append(
                            (model_map[model_path].import_instance_from_xml, f'{path}/{model_path}/{instance_path}')
                        )
                    finally:
                        file_bytes.close()
        handle_queue(fail_queue)
