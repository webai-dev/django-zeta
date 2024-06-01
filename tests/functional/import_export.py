from csv import DictReader
import os
import unittest

from ery_backend.base.testcases import EryLiveServerTestCase, grant_owner_to_obj
from ery_backend.datasets.models import Dataset
from ery_backend.folders.models import Link
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.models import ModuleDefinition
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.procedures.models import Procedure
from ery_backend.roles.utils import has_privilege
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.stints.models import StintDefinition, StintDefinitionModuleDefinition
from ery_backend.stint_specifications.factories import StintSpecificationFactory, StintSpecificationVariableFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.templates.models import Template
from ery_backend.themes.factories import ThemeFactory
from ery_backend.themes.models import Theme
from ery_backend.users.factories import UserFactory
from ery_backend.users.models import User
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.widgets.factories import WidgetFactory
from ery_backend.widgets.models import Widget


class TestExports(EryLiveServerTestCase):
    """
    Alexia wants to make changes to different models offline.
    """

    def setUp(self):
        self.alexia = UserFactory(username='alexia')
        # alexia must be logged in
        self.client = self.get_loggedin_client(self.alexia)

    def test_moduledefinition_export(self):
        """
        Alexia visits link to export ModuleDefinition, and receives a bxml file.
        """
        # moduledefinition to be exported
        module_definition = ModuleDefinitionFactory(name='ModuledefinitionZero')
        grant_owner_to_obj(module_definition, self.alexia)

        # alexia visits link
        response = self.client.get(f'/export/module_definition/{module_definition.gql_id}')
        # alexia receives properly named bxml file
        self.assertEqual(response.get('Content-Disposition'), f'attachment; filename={module_definition.name}.bxml')

        # alexia confirms serialized module definition is of correct name inside of file
        self.assertIn(f'{module_definition.name}', response.content.decode('utf-8'))

    def test_procedures_export(self):
        """
        Alexia visits link to export Procedure, and receives a bxml file.
        """
        procedure = ProcedureFactory(name='test_procedure')
        grant_owner_to_obj(procedure, self.alexia)

        response = self.client.get(f'/export/procedure/{procedure.gql_id}')
        # alexia recieves properly named bxml file
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename=test_procedure.bxml')

        # alexia confirms serialized procedure is of correct name inside of file
        self.assertIn('test_procedure', response.content.decode('utf-8'))

    def test_stintdefinition_export(self):
        """
        Alexia visits link to export StintDefinition, and receives a bxml file.
        """

        # stintdefinition to be exported
        stintdefinition = StintDefinitionFactory(name='StintDefinitionZero')
        moduledefinition = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=stintdefinition, module_definition=moduledefinition)
        stintspecification = StintSpecificationFactory(stint_definition=stintdefinition)
        ss_variables = []
        for _ in range(100):
            variable_definition = VariableDefinitionFactory(module_definition=moduledefinition)
            ss_variables.append(
                StintSpecificationVariableFactory(
                    variable_definition=variable_definition, stint_specification=stintspecification
                )
            )

        grant_owner_to_obj(stintdefinition, self.alexia)

        response = self.client.get(f'/export/stint_definition/{stintdefinition.gql_id}')
        # alexia receives properly named bxml file
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename=StintDefinitionZero.bxml')

        # alexia confirms serialized stint definition is of correct name inside of file
        self.assertIn('StintDefinitionZero', response.content.decode('utf-8'))

    def test_stintdefinitionsimple_export(self):
        """
        Alexia visits link to export StintDefinition (without its fully serialized children),
        and recieves a bxml file.
        """
        # stintdefinitiont to be exported
        stintdefinition = StintDefinitionFactory(name='StintDefinitionZero')
        grant_owner_to_obj(stintdefinition, self.alexia)

        response = self.client.get(f'/export/simple_stint_definition/{stintdefinition.gql_id}')
        # alexia receives properly named bxml file

        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename=StintDefinitionZero.bxml')

        # alexia confirms serialized stint definition is of correct name inside of file
        self.assertIn('StintDefinitionZero', response.content.decode('utf-8'))

    def test_template_export(self):
        """
        Alexia visits link to export Template, and receives a bxml file.
        """
        # template to be exported
        template = TemplateFactory(name='template-0')
        grant_owner_to_obj(template, self.alexia)

        response = self.client.get(f'/export/template/{template.gql_id}')
        # alexia receives properly named bxml file
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename=template-0.bxml')

        # alexia confirms serialized template is of correct name inside of file
        self.assertIn('template-0', response.content.decode('utf-8'))

    def test_widget_export(self):
        """
        Alexia visits link to export Widget, and receives a bxml file.
        """
        # widget to be exported
        widget = WidgetFactory(name='WidgetZero')
        grant_owner_to_obj(widget, self.alexia)

        response = self.client.get(f'/export/widget/{widget.gql_id}')
        # alexia receives properly named bxml file
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename=WidgetZero.bxml')

        # alexia confirms serialized widget is of correct name inside of file
        self.assertIn('WidgetZero', response.content.decode('utf-8'))

    def test_theme_export(self):
        """
        Alexia visits link to export Theme, and recieves a bxml file.
        """
        # theme to be exported
        theme = ThemeFactory(name='theme-0')
        grant_owner_to_obj(theme, self.alexia)

        response = self.client.get(f'/export/theme/{theme.gql_id}')
        # alexia receives properly named bxml file
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename=theme-0.bxml')

        # alexia confirms serialized inputtheme is of correct name inside of file
        self.assertIn('theme-0', response.content.decode('utf-8'))

    @unittest.skip
    def test_validator_export(self):
        """
        Alexia visits link to export Validator, and recieves a bxml file.
        """
        # XXX: Requires completion of issue #347.
        # validator to be exported
        validator = ValidatorFactory(name='validator-0', regex=None)
        grant_owner_to_obj(validator, self.alexia)

        response = self.client.get(f'/export/validator/{validator.id}')
        # alexia receives properly named bxml file
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename=validator-0.bxml')

        # alexia confirms serialized validator is of correct name inside of file
        self.assertIn('validator-0', response.content.decode('utf-8'))


class TestImports(EryLiveServerTestCase):
    """
    Alexia wants to reupload changes as a new object.
    """

    def setUp(self):
        # alexia must be logged in
        self.driver = self.get_loggedin_driver('alexia')  # Headless = True by default
        self.alexia = User.objects.get(username='alexia')

    def test_import_dataset(self):
        """
        Alexia has created a csv dataset and wants to upload it to stintery.
        """
        Dataset.objects.all().delete()
        dataset_address = f'{os.getcwd()}/ery_backend/datasets/tests/data/real_estate_sample.csv'
        reader = DictReader(open(dataset_address))
        # alexia visits link
        self.driver.get(f'{self.live_server_url}/import/dataset_file')
        # alexia enters name into DataSet name field
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys("AlexiasFunkayDataSet")
        # alexia loads the intended xml file
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(dataset_address)
        # alexia submits the file
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        imported_dataset = Dataset.objects.filter(name='AlexiasFunkayDataSet').first()
        self.assertIsNotNone(imported_dataset)
        self.assertTrue(has_privilege(imported_dataset, self.alexia, 'create'))
        self.assertTrue(Link.objects.filter(dataset=imported_dataset, parent_folder=self.alexia.my_folder).exists())
        entity_rows = imported_dataset.rows
        headers = imported_dataset.headers
        for row_entity in entity_rows:
            original_row = next(reader)
            dataset_row = {header: row_entity[header] for header in headers}
            self.assertEqual(original_row, dataset_row)

    def test_import_moduledefinition(self):
        """
        Alexia has edited a moduledefinition bxml offline and wants to create a new instance.
        """
        ModuleDefinition.objects.all().delete()
        # alexia visits link
        self.driver.get(f'{self.live_server_url}/import/module_definition_file')
        # alexia enters new module definition name into ModuleDefinition name field
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys("AlexiasFunkayModuleDefinition")
        # alexia loads the intended xml file
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/modules/tests/data/module_definition-0.bxml')
        # alexia submits the file
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        imported_md = ModuleDefinition.objects.filter(name='AlexiasFunkayModuleDefinition').first()
        self.assertIsNotNone(imported_md)
        self.assertTrue(has_privilege(imported_md, self.alexia, 'create'))
        self.assertTrue(Link.objects.filter(module_definition=imported_md, parent_folder=self.alexia.my_folder).exists())

    def test_import_procedure(self):
        """
        Alexia has edited a procedure bxml offline and wants to create a new instance.
        """
        Procedure.objects.all().delete()
        # alexia visits link
        self.driver.get(f'{self.live_server_url}/import/procedure_file')
        # alexia enters new procedure name into Procedure name field
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys("alexias_funkay_procedure")
        # alexia loads the intended xml file
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/procedures/tests/data/procedure-0.bxml')
        # alexia submits the file
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        imported_procedure = Procedure.objects.filter(name='alexias_funkay_procedure').first()
        self.assertIsNotNone(imported_procedure)
        self.assertTrue(has_privilege(imported_procedure, self.alexia, 'create'))
        self.assertTrue(Link.objects.filter(procedure=imported_procedure, parent_folder=self.alexia.my_folder).exists())

    def test_import_simple_stintdefinition(self):
        """
        Alexia has edited a simple stintdefinition bxml offline and wants to create a new instance.
        """
        StintDefinition.objects.all().delete()
        # required to import stintdefinition
        ModuleDefinitionFactory(slug='moduledefinition1-PBdzLcxg')
        ModuleDefinitionFactory(slug='moduledefinition0-tTPTcTkz')

        # alexia visits link
        self.driver.get(f'{self.live_server_url}/import/stint_definition_file')
        # alexia enters new stint definition name into StintDefinition name field
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys("AlexiaFunkaySimpleStintDefinition")
        # alexia loads the intended xml file
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/stints/tests/data/simple-stint-0.bxml')
        # alexia clicks the simple box
        simple_box = self.driver.find_element_by_id('simplebox')
        simple_box.click()
        # alexia submits the file
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        imported_sd = StintDefinition.objects.filter(name='AlexiaFunkaySimpleStintDefinition').first()
        self.assertIsNotNone(imported_sd)
        self.assertTrue(has_privilege(imported_sd, self.alexia, 'create'))
        self.assertTrue(Link.objects.filter(stint_definition=imported_sd, parent_folder=self.alexia.my_folder).exists())

    def test_import_stintdefinition(self):
        """
        Alexia has edited a stintdefinition bxml offline and wants to create a new instance.
        """
        StintDefinition.objects.all().delete()
        # alexia visits link
        self.driver.get(f'{self.live_server_url}/import/stint_definition_file')
        # alexia enters new stint definition name into StintDefinition name field
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys("AlexiasFunkayStintDefinition")
        # alexia loads the intended xml file
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/stints/tests/data/stint-0.bxml')
        # alexia submits the file
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        self.assertTrue(StintDefinition.objects.filter(name='AlexiasFunkayStintDefinition').exists())
        imported_sd = StintDefinition.objects.filter(name='AlexiasFunkayStintDefinition').first()
        first_specification = imported_sd.specifications.first()
        self.assertEqual(first_specification.variables.count(), 100)
        self.assertTrue(has_privilege(imported_sd, self.alexia, 'create'))
        self.assertTrue(Link.objects.filter(stint_definition=imported_sd, parent_folder=self.alexia.my_folder).exists())

    def test_import_template(self):
        """
        Alexia has edited a template bxml offline and wants to create a new instance.
        """
        Template.objects.all().delete()
        # required to import template
        WidgetFactory(slug='testwidget-abc123')
        WidgetFactory(slug='testwidget-abc456')
        TemplateFactory(slug='moduledefinitiontemplate2-mXsMkPUQ')
        FrontendFactory(slug='moduledefinitionfrontend1-JoiGtMdE')
        template = TemplateFactory(name='template-0')
        grant_owner_to_obj(template, self.alexia)
        # alexia visits link
        self.driver.get(f'{self.live_server_url}/import/template_file')
        # alexia enters new template name into Template name field
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys("AlexiasFunkayTemplate")
        # alexia loads the intended xml file
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/templates/tests/data/module_definition-template-1.bxml')
        # alexia submits the file
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        imported_template = Template.objects.filter(name='AlexiasFunkayTemplate').first()
        self.assertIsNotNone(imported_template)
        self.assertTrue(has_privilege(imported_template, self.alexia, 'create'))
        self.assertTrue(Link.objects.filter(template=imported_template, parent_folder=self.alexia.my_folder).exists())

    def test_import_widget(self):
        """
        Alexia has edited an widget bxml offline and wants to create a new instance.
        """
        # required as related_widget
        Widget.objects.all().delete()
        WidgetFactory(frontend=Frontend.objects.get(name='SMS'), slug='notarealslug-asdghjkl')
        # alexia visits link
        self.driver.get(f'{self.live_server_url}/import/widget_file')
        # alexia enters new widget name into Widget name field
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys("AlexiasFunkayWidget")
        # alexia loads the intended xml file
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/widgets/tests/data/widget-0.bxml')
        # alexia clicks the connect box
        connect_box = self.driver.find_element_by_id('connectbox')
        connect_box.click()
        # alexia submits the file
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        imported_widget = Widget.objects.filter(name='AlexiasFunkayWidget').first()
        self.assertIsNotNone(imported_widget)
        self.assertTrue(has_privilege(imported_widget, self.alexia, 'create'))
        self.assertTrue(Link.objects.filter(widget=imported_widget, parent_folder=self.alexia.my_folder).exists())

    def test_import_theme(self):
        """
        Alexia has edited a theme bxml offline and wants to create a new instance.
        """
        Theme.objects.all().delete()
        # alexia visits link
        self.driver.get(f'{self.live_server_url}/import/theme_file')
        # alexia enters new theme name into Theme name field
        name_field = self.driver.find_element_by_id('name')
        name_field.send_keys("AlexiasFunkayTheme")
        # alexia loads the intended xml file
        bxml_field = self.driver.find_element_by_id('file_to_import')
        bxml_field.send_keys(f'{os.getcwd()}/ery_backend/themes/tests/data/module_definition-theme-1.bxml')
        # alexia submits the file
        submit_button = self.driver.find_element_by_id('submit_button')
        submit_button.click()
        imported_theme = Theme.objects.filter(name='AlexiasFunkayTheme').first()
        self.assertIsNotNone(imported_theme)
        self.assertTrue(has_privilege(imported_theme, self.alexia, 'create'))
        self.assertTrue(Link.objects.filter(theme=imported_theme, parent_folder=self.alexia.my_folder).exists())
