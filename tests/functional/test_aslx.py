from ery_backend.base.testcases import EryTestCase
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.modules.models import ModuleDefinition
from ery_backend.templates.factories import TemplateFactory
from ery_backend.themes.factories import ThemeFactory


class TestCase(EryTestCase):
    def setUp(self):
        FrontendFactory()
        ThemeFactory(name="default", slug="default-theme")
        TemplateFactory(name="default", slug="default-template")
        self.xml = open('tests/functional/game.bxml', 'rb')

    def test_module_import(self):
        module_definition = ModuleDefinition.import_instance_from_xml(self.xml, name='Game')
        self.assertIsNotNone(module_definition)
