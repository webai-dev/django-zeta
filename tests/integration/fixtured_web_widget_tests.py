import random
import time
import unittest

import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from django.test import override_settings
from languages_plus.models import Language

from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryChannelsTestCase, create_test_stintdefinition
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.labs.factories import LabFactory
from ery_backend.modules.factories import (
    ModuleDefinitionWidgetFactory,
    ModuleEventFactory,
    ModuleEventStepFactory,
    WidgetChoiceFactory,
)
from ery_backend.modules.models import ModuleEvent, ModuleEventStep
from ery_backend.stages.factories import StageTemplateBlockFactory, StageTemplateBlockTranslationFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.users.factories import UserFactory
from ery_backend.users.models import User
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.models import Widget


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestDropdown(EryChannelsTestCase):
    def setUp(self):
        starter = UserFactory()
        self.taker = User.objects.create_user('taker', {})
        web = Frontend.objects.get(name='Web')
        language = get_default_language()

        sd = create_test_stintdefinition(web)

        md = sd.module_definitions.first()
        vd = VariableDefinitionFactory(
            module_definition=md,
            name='testvar',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            default_value=None,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
        )
        dropdown = Widget.objects.get(name='Dropdown')
        module_dropdown = ModuleDefinitionWidgetFactory(
            name='Dropdown', module_definition=md, widget=dropdown, variable_definition=vd
        )
        save_event = ModuleEventFactory(widget=module_dropdown, event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick, name='')
        ModuleEventStepFactory(module_event=save_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.save_var)

        self.choices = [WidgetChoiceFactory(widget=module_dropdown) for _ in range(random.randint(1, 5))]
        st = md.start_stage.stage_templates.first()
        stb = StageTemplateBlockFactory(name='DropdownBlock', stage_template=st)
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            content='<Dropdown defaultValue={testvar || ""} id=\'test-widget\' />',
            language=language,
            frontend=web,
        )
        root_block_translation = st.get_root_block().translations.first()
        root_block_translation.content = '<DropdownBlock/>'
        root_block_translation.save()

        language_frontends = [{'language': language, 'frontend': web}]
        ss = StintSpecificationFactory(add_languagefrontends=language_frontends, stint_definition=sd)
        self.stint = ss.realize(starter)
        self.stint.start(starter)
        self.stint.join_user(self.taker, web)

    def test_save_onclick(self):
        driver = self.get_loggedin_driver(self.taker.username, headless=True, vendor=self.stint.stint_specification.vendor)
        hand = self.stint.hands.first()
        url = f'{self.live_server_url}/stints/{self.stint.gql_id}/'
        driver.get(url)
        dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "test-widget")))
        dropdown.click()
        time.sleep(2)
        choice_values = [choice.value for choice in self.choices]
        choices = [e for e in driver.find_elements_by_xpath(f"//ul/li") if e.get_attribute('data-value') in choice_values]
        choice = random.choice(choices)
        chosen_value = choice.get_attribute('data-value')  # Set to avoid stale element reference later on
        choice.click()
        time.sleep(2)
        dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "test-widget")))
        self.assertEqual(dropdown.get_attribute('innerHTML'), chosen_value)
        self.assertEqual(hand.variables.get(variable_definition__name='testvar').value, chosen_value)


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestRadioButtons(EryChannelsTestCase):
    def setUp(self):
        starter = UserFactory()
        self.taker = User.objects.create_user('taker', {})
        web = Frontend.objects.get(name='Web')
        language = get_default_language()

        sd = create_test_stintdefinition(web)

        md = sd.module_definitions.first()
        vd = VariableDefinitionFactory(
            module_definition=md,
            name='testvar',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            default_value=None,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
        )
        radios = Widget.objects.get(name='RadioButtons')
        self.module_radios = ModuleDefinitionWidgetFactory(
            name='RadioButtons', module_definition=md, widget=radios, variable_definition=vd
        )
        save_event = ModuleEventFactory(
            widget=self.module_radios, event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange, name=''
        )
        ModuleEventStepFactory(module_event=save_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.save_var)

        self.choices = [WidgetChoiceFactory(widget=self.module_radios) for _ in range(random.randint(1, 5))]
        st = md.start_stage.stage_templates.first()
        stb = StageTemplateBlockFactory(name='RadioButtonsBlock', stage_template=st)
        self.stage_block_translation = StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            content='<RadioButtons id=\'test-widget\' defaultValue={testvar || ""} id=\'test-widget\' />',
            language=language,
            frontend=web,
        )
        root_block_translation = st.get_root_block().translations.first()
        root_block_translation.content = '<RadioButtonsBlock/>'
        root_block_translation.save()

        language_frontends = [{'language': language, 'frontend': web}]
        ss = StintSpecificationFactory(add_languagefrontends=language_frontends, stint_definition=sd)
        self.stint = ss.realize(starter)
        self.stint.start(starter)
        self.stint.join_user(self.taker, web)
        self.driver = self.get_loggedin_driver(self.taker.username, headless=True, vendor=ss.vendor)

    def test_save_onradioclick(self):
        hand = self.stint.hands.first()
        self.driver.get(f'{self.live_server_url}/stints/{self.stint.gql_id}/')
        # Confirm presence of radio buttons
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "test-widget")))
        choice_values = [choice.value for choice in self.choices]
        choice_value = random.choice(choice_values)  # Set to avoid stale element reference later on
        choice_widget = self.driver.find_element_by_xpath(f"//input[@value='{choice_value}']")
        choice_widget.click()
        time.sleep(2)
        choice_widget = self.driver.find_element_by_xpath(f"//input[@value='{choice_value}']")
        self.assertTrue(choice_widget.get_attribute('checked'))
        self.assertEqual(hand.variables.get(variable_definition__name='testvar').value, choice_value)

    def test_choices_static_prop(self):
        self.module_radios.choices.all().delete()
        for _ in range(random.randint(1, 10)):
            WidgetChoiceFactory(add_translation=get_default_language(), widget=self.module_radios)
        block_content = """
{RadioButtons.choices.map((choice) => <div class="widget-choice">{choice.caption}</div>)}
"""
        self.stage_block_translation.content = block_content
        self.stage_block_translation.save()
        self.driver.get(f'{self.live_server_url}/stints/{self.stint.gql_id}/')
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "widget-choice")))
        choice_elements = self.driver.find_elements_by_class_name("widget-choice")
        captions = [choice['caption'] for choice in self.module_radios.get_choices(language=get_default_language())]
        self.assertEqual(len(choice_elements), len(captions))
        for choice_element in choice_elements:
            self.assertIn(choice_element.get_attribute('innerHTML'), captions)


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestGeolocation(EryChannelsTestCase):
    """
    Confirm input widget rendered as expected.
    """

    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        web = Frontend.objects.get(name='Web')
        self.lab = LabFactory()
        self.language = Language.objects.get(pk='en')
        self.web = Frontend.objects.get(name='Web')
        stint_definition = create_test_stintdefinition(frontend=web, render_args=['input'])
        combo_obj = {'frontend': web, 'language': get_default_language()}
        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        stint = self.lab.current_stint
        self.hand = stint.hands.first()
        self.stage = self.hand.stage.stage_definition
        self.module_definition = self.hand.current_module.stint_definition_module_definition.module_definition
        self.st = self.stage.stage_templates.first()
        self.content_block = self.st.template.parental_template.blocks.get(name='Content')
        self.root_translation = self.content_block.translations.first()
        self.driver = self.get_loggedin_driver(
            username='testuser', headless=False, vendor=self.hand.stint.stint_specification.vendor
        )

    @unittest.skip("Address in issue #829")
    def test_allow_geolocation(self):
        geolocation = Widget.objects.get(name='EryGeolocation')
        ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=geolocation, name='MyLocation')
        self.root_translation.content = '<div id=\'test-widget\'><MyLocationBlock/></div>'
        self.root_translation.save()
        stb = StageTemplateBlockFactory(name='MyLocationBlock', stage_template=self.st)
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb, frontend=self.hand.frontend, language=self.hand.language, content='<MyLocation />'
        )
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        allow_tracking = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "geolocation-tracking-toggle"))
        )
        allow_tracking.click()
        time.sleep(0.5)
        table_cells = self.driver.find_elements_by_tag_name('td')
        expected_table_cell_names = ['Latitude', 'Longitude', 'Altitude', 'Heading', 'Speed']
        found_table_cell_names = []
        for table_cell in table_cells:
            value = table_cell.get_attribute('innerHTML')
            if value in expected_table_cell_names:
                found_table_cell_names.append(value)
        self.assertEqual(sorted(expected_table_cell_names), sorted(found_table_cell_names))

    def test_disallow_geolocation(self):
        geolocation = Widget.objects.get(name='EryGeolocation')
        ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=geolocation, name='MyLocation')
        self.root_translation.content = '<div id=\'test-widget\'><MyLocationBlock/></div>'
        self.root_translation.save()
        stb = StageTemplateBlockFactory(name='MyLocationBlock', stage_template=self.st)
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb, frontend=self.hand.frontend, language=self.hand.language, content='<MyLocation />'
        )
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        allow_tracking = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "geolocation-tracking-toggle"))
        )
        title = allow_tracking.find_element_by_xpath('./span')
        self.assertEqual(title.get_attribute('innerHTML'), 'Allow Tracking')
        allow_tracking.click()
        time.sleep(3)
        # XXX: Re-enable on issue #829
        # WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//td[contains(., "Latitude")]')))
        disallow_tracking = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "geolocation-tracking-toggle"))
        )
        title = disallow_tracking.find_element_by_xpath('./span')
        self.assertEqual(title.get_attribute('innerHTML'), 'Stop Tracking')
        disallow_tracking.click()
        allow_tracking = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "geolocation-tracking-toggle"))
        )
        title = allow_tracking.find_element_by_xpath('./span')
        self.assertEqual(title.get_attribute('innerHTML'), 'Allow Tracking')

    def tearDown(self):
        super().tearDown()
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestEryDialog(EryChannelsTestCase):
    """
    Confirm dialog widget rendered as expected.
    """

    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        web = Frontend.objects.get(name='Web')
        self.lab = LabFactory()
        self.language = Language.objects.get(pk='en')
        self.web = Frontend.objects.get(name='Web')
        stint_definition = create_test_stintdefinition(frontend=web, render_args=['input'])
        self.vd = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=stint_definition.module_definitions.first(),
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            default_value=None,
        )
        combo_obj = {'frontend': web, 'language': get_default_language()}
        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        stint = self.lab.current_stint
        self.hand = stint.hands.first()
        self.stage = self.hand.stage.stage_definition
        self.module_definition = self.hand.current_module.stint_definition_module_definition.module_definition
        self.st = self.stage.stage_templates.first()
        self.content_block = self.st.template.parental_template.blocks.get(name='Content')
        self.root_translation = self.content_block.translations.first()
        self.driver = self.get_loggedin_driver(username='test_user', headless=True, vendor=stint_specification.vendor)

    def test_open_dialog(self):
        dialog = Widget.objects.get(name='EryDialog')
        ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=dialog, name='MyDialog', variable_definition=self.vd
        )
        self.root_translation.content = '<MyDialogBlock id=\'test-block\'/>'
        self.root_translation.save()
        stb = StageTemplateBlockFactory(name='MyDialogBlock', stage_template=self.st)
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            frontend=self.hand.frontend,
            language=self.hand.language,
            content=f'<MyDialog id="test-widget" open={{ {self.vd.name} == "abc"}} />',
        )
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        with self.assertRaises(selenium.common.exceptions.TimeoutException):
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        self.hand.stint.set_variable(self.vd, 'abc', hand=self.hand)
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        WebDriverWait(self.driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, 'close-dialog')))

    def test_close_dialog(self):
        dialog = Widget.objects.get(name='EryDialog')
        ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=dialog, name='MyDialog')
        self.root_translation.content = '<MyDialogBlock id=\'test-block\'/>'
        self.root_translation.save()
        stb = StageTemplateBlockFactory(name='MyDialogBlock', stage_template=self.st)
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            frontend=self.hand.frontend,
            language=self.hand.language,
            content='<MyDialog id="test-widget" open={true} />',
        )
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        close_button = WebDriverWait(self.driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, 'close-dialog')))
        close_button.click()
        with self.assertRaises(selenium.common.exceptions.TimeoutException):
            WebDriverWait(self.driver, 2).until(EC.presence_of_element_located((By.ID, 'test-widget')))

    def test_custom_close_widget(self):
        """
        Allow special actions on close using ModuleWidget wrapping DialogCloser.
        """
        dialog = Widget.objects.get(name='EryDialog')
        closer = Widget.objects.get(name='DialogCloser')
        ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=dialog, name='MyDialog')
        closer_mdw = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=closer, name='DialogCloser'
        )
        mevent = ModuleEventFactory(event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick, name='', widget=closer_mdw)
        action = ActionFactory(module_definition=self.hand.current_module_definition)
        ActionStepFactory(
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            value='"abc123"',
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action=action,
            condition=None,
            variable_definition=self.vd,
        )
        ModuleEventStepFactory(
            module_event=mevent, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action, action=action
        )
        self.root_translation.content = '<MyDialogBlock id=\'test-block\'/>'
        self.root_translation.save()
        stb = StageTemplateBlockFactory(name='MyDialogBlock', stage_template=self.st)
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            frontend=self.hand.frontend,
            language=self.hand.language,
            content='<MyDialog id="test-widget" open={true} closeWidget={DialogCloser} />',
        )
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        close_button = WebDriverWait(self.driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, 'close-dialog')))
        close_button.click()
        time.sleep(2)
        self.assertEqual(self.hand.variables.get(variable_definition=self.vd).value, 'abc123')

    def tearDown(self):
        self.driver.close()
