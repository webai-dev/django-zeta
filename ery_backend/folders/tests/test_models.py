from unittest import mock

from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.testcases import EryTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.roles.models import Role
from ery_backend.roles.utils import grant_role
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.users.factories import UserFactory
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.widgets.factories import WidgetFactory

from ..factories import FolderFactory, LinkFactory

model_map = {
    StintDefinitionFactory: 'stint_definition',
    ModuleDefinitionFactory: 'module_definition',
    TemplateFactory: 'template',
    ThemeFactory: 'theme',
    ProcedureFactory: 'procedure',
    WidgetFactory: 'widget',
    ImageAssetFactory: 'image_asset',
    ValidatorFactory: 'validator',
}


def _get_instance_from_fileobj(obj):
    for attr in model_map.values():
        if attr in obj.keys():
            return obj[attr]
    raise Exception(f"No attr from {model_map.values()} found in {obj}")


def _get_instance_from_link(link):
    for attr in model_map.values():
        instance = getattr(link, attr)
        if instance:
            return instance
    raise Exception(f"No attr from {model_map.values()} found in {link}")


class TestFolder(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.owner = Role.objects.get(name='owner')

    def setUp(self):
        self.user = UserFactory()
        self.folder = FolderFactory()

    def test_exists(self):
        self.assertIsNotNone(self.folder)

    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def test_query_files(self, mock_bucket):
        generated_instances = []
        links = []
        for factory, name in model_map.items():
            instance = factory()
            generated_instances.append(instance)
            kwargs = {name: instance}
            links.append(LinkFactory(parent_folder=self.folder, **kwargs))
            grant_role(self.owner, instance, self.user)

        fileobjs = self.folder.query_files(self.user)
        for generated_instance in generated_instances:
            expected_file_obj = {
                generated_instance.get_field_name(): generated_instance,
                'owner': self.user,
                'popularity': generated_instance.filestar_set.count(),
            }
            match = fileobjs.index(expected_file_obj)
            self.assertIsNotNone(match)
            self.assertEqual(fileobjs[match]['owner'], self.user)


class TestLink(EryTestCase):
    @mock.patch('ery_backend.assets.models.ImageAsset.bucket')
    def setUp(self, mock_bucket):
        self.parent_folder = FolderFactory()
        self.folder = FolderFactory()
        self.image_asset = ImageAssetFactory()
        self.module_definition = ModuleDefinitionFactory()
        self.procedure = ProcedureFactory()
        self.stint_definition = StintDefinitionFactory()
        self.template = TemplateFactory()
        self.widget = WidgetFactory()
        self.image_asset_link = LinkFactory(
            parent_folder=self.parent_folder, image_asset=self.image_asset, reference_type='image_asset'
        )
        self.stint_link = LinkFactory(
            parent_folder=self.parent_folder, stint_definition=self.stint_definition, reference_type='stint_definition'
        )
        self.module_link = LinkFactory(
            parent_folder=self.parent_folder, module_definition=self.module_definition, reference_type='module_definition'
        )
        self.procedure_link = LinkFactory(
            parent_folder=self.parent_folder, procedure=self.procedure, reference_type='procedure'
        )

        self.template_link = LinkFactory(parent_folder=self.parent_folder, template=self.template, reference_type='template')
        self.widget_link = LinkFactory(parent_folder=self.parent_folder, widget=self.widget, reference_type='widget')
        self.folder_link = LinkFactory(parent_folder=self.parent_folder, folder=self.folder, reference_type='folder')

    def test_exists(self):
        self.assertIsNotNone(self.image_asset_link)

    def test_expected_attributes(self):
        self.image_asset_link.refresh_from_db()
        self.assertEqual(self.image_asset_link.parent_folder, self.parent_folder)
        self.assertEqual(self.stint_link.stint_definition, self.stint_definition)
        self.assertEqual(self.module_link.module_definition, self.module_definition)
        self.assertEqual(self.image_asset_link.image_asset, self.image_asset)
        self.assertEqual(self.procedure_link.procedure, self.procedure)
        self.assertEqual(self.template_link.template, self.template)
        self.assertEqual(self.folder_link.folder, self.folder)
        self.assertEqual(self.widget_link.widget, self.widget)

    def test_clean(self):
        """
        Verify link must have refernece to folder and reference to a nullable related model
        """
        # Missing nullable related model
        with self.assertRaises(ValueError):
            LinkFactory(parent_folder=self.folder, reference_type='module_definition')
        # Two+ nullable related models
        with self.assertRaises(ValueError):
            LinkFactory(
                parent_folder=self.folder,
                stint_definition=self.stint_definition,
                module_definition=self.module_definition,
                reference_type='stint_definition',
            )
