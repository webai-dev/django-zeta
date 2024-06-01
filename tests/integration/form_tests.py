import time

from django.test import override_settings

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ery_backend.base.testcases import EryChannelsTestCase, create_test_stintdefinition
from ery_backend.base.utils import get_default_language
from ery_backend.forms.factories import (
    FormFactory,
    FormFieldFactory,
    FormItemFactory,
    FormButtonFactory,
    FormButtonListFactory,
)
from ery_backend.frontends.models import Frontend
from ery_backend.labs.factories import LabFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import HandVariableFactory, VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetConnectionFactory
from ery_backend.widgets.models import Widget


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestFormFieldRender(EryChannelsTestCase):
    """
    Render basic form with one field.
    """

    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        web = Frontend.objects.get(name='Web')
        self.lab = LabFactory()
        stint_definition = create_test_stintdefinition(frontend=web)
        combo_obj = {'frontend': web, 'language': get_default_language()}
        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        stint = self.lab.current_stint
        self.hand = stint.hands.first()
        stage = self.hand.stage.stage_definition
        st = stage.stage_templates.first()
        self.content_block = st.template.parental_template.blocks.get(name='Content')
        self.translation = self.content_block.translations.first()
        self.input_widget = Widget.objects.get(name='Input', namespace='mui')
        WidgetConnectionFactory(
            name='MInput', originator=self.input_widget, target=Widget.objects.get(name='Input', namespace='mui')
        )
        self.form = FormFactory(module_definition=self.hand.current_module_definition, name='Form')
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_form_render(self):
        form_item = FormItemFactory(form=self.form, child_type=False)
        field = FormFieldFactory(
            name='FirstField',
            form_item=form_item,
            widget=self.input_widget,
            disable=None,
            initial_value='TYPE SOMETHING RIGHT NOW',
        )
        FormItemFactory(field=field, form=self.form)
        self.translation.content = f'<Form id="test-external-render">Yup</Form>'
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(2)
        field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, f'{self.form.name}-{form_item.order}-{field.name}'))
        )
        self.assertIsNotNone(field)

    def test_multiple_fields(self):
        item_1 = FormItemFactory(form=self.form, child_type=False)
        field_1 = FormFieldFactory(
            name='FirstField',
            form_item=item_1,
            widget=self.input_widget,
            disable=None,
            initial_value='TYPE SOMETHING RIGHT NOW',
        )
        item_2 = FormItemFactory(form=self.form, child_type=False)
        field_2 = FormFieldFactory(name='SecondField', form_item=item_2, widget=self.input_widget, disable=None)
        self.translation.content = f'<Form id="test-external-render">Yup</Form>'
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        # Let app receive socket messages
        time.sleep(3)
        field_1_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, f'{field_1.form_item.form.name}-{item_1.order}-{field_1.name}'))
        )
        self.assertIsNotNone(field_1_element)
        field_2_element = self.driver.find_element_by_id(f"{field_2.form_item.form.name}-{item_2.order}-{field_2.name}")
        self.assertIsNotNone(field_2_element)

    def test_form_submit(self):
        vd_1 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand, data_type=VariableDefinition.DATA_TYPE_CHOICES.str, default_value=None
        )
        hv_1 = HandVariableFactory(hand=self.hand, module=self.hand.current_module, variable_definition=vd_1, value=None)
        item_1 = FormItemFactory(form=self.form, child_type=False)
        field_1 = FormFieldFactory(
            name='FirstField',
            form_item=item_1,
            widget=self.input_widget,
            disable=None,
            initial_value='',
            variable_definition=vd_1,
        )
        vd_2 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand, data_type=VariableDefinition.DATA_TYPE_CHOICES.str, default_value=None
        )
        hv_2 = HandVariableFactory(hand=self.hand, module=self.hand.current_module, variable_definition=vd_2, value=None)

        item_2 = FormItemFactory(form=self.form, child_type=False)
        field_2 = FormFieldFactory(
            name='SecondField',
            form_item=item_2,
            widget=self.input_widget,
            disable=None,
            initial_value='',
            variable_definition=vd_2,
        )
        submit_widget = Widget.objects.get(name='FormSubmitButton')
        item_3 = FormItemFactory(form=self.form, child_type=False)
        button_list = FormButtonListFactory(form_item=item_3)
        FormButtonFactory(button_list=button_list, widget=submit_widget, name='SubmitButton')
        self.translation.content = f'<div id="test-external-render"><Form>Yup</Form>' '</div>'
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        # Let app receive socket messages
        time.sleep(3)
        field_1_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, f'{field_1.form_item.form.name}-{item_1.order}-{field_1.name}'))
        )
        field_1_element.send_keys('alpharomeo')
        field_2_element = self.driver.find_element_by_id(f"{field_2.form_item.form.name}-{item_2.order}-{field_2.name}")
        field_2_element.send_keys('alphagiulietta')
        submit_button = self.driver.find_element_by_id("submit-button")
        submit_button.click()
        time.sleep(3)
        field_1_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, f'{field_1.form_item.form.name}-{item_1.order}-{field_1.name}'))
        )
        field_2_element = self.driver.find_element_by_id(f"{field_2.form_item.form.name}-{item_2.order}-{field_2.name}")
        # Field values should retain after submit
        self.assertEqual(field_1_element.get_attribute('value'), 'alpharomeo')
        self.assertEqual(field_2_element.get_attribute('value'), 'alphagiulietta')
        hv_1.refresh_from_db()
        hv_2.refresh_from_db()
        self.assertEqual(hv_1.value, 'alpharomeo')
        self.assertEqual(hv_2.value, 'alphagiulietta')

    def tearDown(self):
        self.driver.close()
