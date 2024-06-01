import os

from ery_backend.modules.models import ModuleDefinition
from ery_backend.roles.utils import grant_ownership
from ery_backend.stints.models import StintDefinition
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from ery_backend.users.models import User
from ery_backend.vendors.models import Vendor
from ery_backend.widgets.models import Widget


def assign_ownership(obj):
    for user in User.objects.filter(is_creator=True):
        grant_ownership(obj, user)
        if user.my_folder:
            obj.create_link(user.my_folder)
        if isinstance(obj, StintDefinition):
            for md in obj.module_definitions.all():
                assign_ownership(md)


def setup():
    xml_base_address = f'{os.getcwd()}/scripts/lenns_demo_files/lenns_exports'

    Vendor.objects.get_or_create(slug="lenns-asdaXXx", name="lenns")

    widgets = {'cls': Widget, 'elements': ['SummaryTable']}

    templates = {
        'cls': Template,
        'elements': ['DNMHcfChildForward', 'DNMHcfChildProgression', 'OneQuestionSixContent'],
    }
    themes = {'cls': Theme, 'elements': ['LennsTheme']}
    stint_definition = {'cls': StintDefinition, 'elements': ['DescriptiveNormMessaging_v10']}

    ModuleDefinition.objects.filter(name='Main').delete()
    for element in ['LennsHcfChild', 'LennsHcfChildProgression', 'LennsHcfChildForward']:
        Template.objects.filter(name=element).delete()

    for element_dict in [widgets, themes, templates, stint_definition]:
        element_cls = element_dict['cls']
        print(f'Installing {element_cls} models')
        for element in element_dict['elements']:
            print(f'Installing {element}')
            element_cls.objects.filter(name=element).delete()
            xml_file = open(f'{xml_base_address}/{element}.bxml', 'rb')
            element_instance = element_cls.import_instance_from_xml(xml_file)
            assign_ownership(element_instance)
            print(f'Successfully installed {element}')
        print(f'Process completed')
