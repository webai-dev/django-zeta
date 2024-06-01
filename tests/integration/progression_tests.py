import time

from django.test import override_settings

import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ery_backend.base.testcases import EryChannelsTestCase, create_test_stintdefinition
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.labs.factories import LabFactory
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory, ModuleEventFactory, ModuleEventStepFactory
from ery_backend.modules.models import ModuleEvent, ModuleEventStep
from ery_backend.stages.factories import StageTemplateBlockFactory, StageTemplateBlockTranslationFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.templates.factories import TemplateWidgetFactory
from ery_backend.templates.models import TemplateBlock
from ery_backend.users.factories import UserFactory
from ery_backend.widgets.models import Widget


def _clean_name(name):
    from string import punctuation

    output = ''
    for char in name:
        if char not in punctuation:
            output += char
    return output


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestUpdateStage(EryChannelsTestCase):
    """
    Confirm advancement (from server) of hand's stage leads to change in client react content.
    """

    def setUp(self):
        web = Frontend.objects.get(name='Web')
        jdeezy = UserFactory()
        stint_definition = create_test_stintdefinition(frontend=web, stage_n=2, redirects=True)
        combo_obj = {'frontend': web, 'language': get_default_language()}

        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab = LabFactory()
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        self.hand = self.lab.current_stint.hands.first()
        tb = TemplateBlock.objects.get(
            name='Questions', template=self.hand.stage.stage_definition.stage_templates.first().template.parental_template
        )
        TemplateWidgetFactory(template=tb.template, widget=Widget.objects.get(name='SubmitButton'), name='SubmitButton')
        tb_translation = tb.translations.first()
        tb_translation.content += '<div id=\'test-widget\'><SubmitButton>Submit</SubmitButton></div>'
        tb_translation.save()
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_update_stage(self):
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(0.5)  # websocket needs time to connect
        questions_1_id = (
            f'{self.hand.stage.stage_definition.module_definition.slug.lower()}-'
            f'{self.hand.stage.stage_definition.name.lower()}-questions'
        )
        questions = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, questions_1_id)))
        button = self.driver.find_element_by_xpath('//div[contains(@id, "test-widget")]/button')
        sd_num = int(_clean_name(questions.get_attribute('innerHTML').split('StageDefinition')[-1]).split(' ')[0])
        button.click()
        # Wait till it loads dang it!
        time.sleep(3)
        self.hand.refresh_from_db()
        questions_2_id = (
            f'{self.hand.stage.stage_definition.module_definition.slug.lower()}-'
            f'{self.hand.stage.stage_definition.name.lower()}-questions'
        )
        questions_2 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, questions_2_id)))

        sd_num_2 = int(_clean_name(questions_2.get_attribute('innerHTML').split('StageDefinition')[-1]).split(' ')[0])
        self.assertTrue(sd_num < sd_num_2)

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestStageLock(EryChannelsTestCase):
    """
    Confirm pressing submit quickly does not allow unauthorized progression over multiple stages.
    """

    def setUp(self):
        web = Frontend.objects.get(name='Web')
        jdeezy = UserFactory()
        stint_definition = create_test_stintdefinition(frontend=web, stage_n=4, redirects=True)
        combo_obj = {'frontend': web, 'language': get_default_language()}

        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab = LabFactory()
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        self.hand = self.lab.current_stint.hands.first()
        stage_template = self.hand.stage.stage_definition.stage_templates.get(template__frontend__name='Web')
        self.root_block_translation = stage_template.get_root_block().translations.get(language=self.hand.language)
        self.root_block_translation.content = "<div id='test-widget'><SubmitButton/></div>"
        self.root_block_translation.save()
        submit_button = Widget.objects.get(name='SubmitButton')
        TemplateWidgetFactory(
            template=self.root_block_translation.template_block.template, widget=submit_button, name='SubmitButton'
        )
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_update_stage_with_template_widget(self):
        stage_definitions = self.hand.current_module_definition.stage_definitions.order_by('id')
        self.assertEqual(self.hand.stage.stage_definition, stage_definitions[0])
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(0.5)  # websocket needs time to connect
        next_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "test-widget")]/button'))
        )
        try:
            next_button.click()
            next_button.click()
            next_button.click()
        except selenium.common.exceptions.StaleElementReferenceException:  # If page has changed already
            pass
        time.sleep(3)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, stage_definitions[1])

    def test_update_stage_with_module_widget(self):
        self.root_block_translation.content = '<StageBlock/>'
        self.root_block_translation.save()
        stage_definitions = self.hand.current_module_definition.stage_definitions.order_by('id')
        for stage_definition in stage_definitions:
            stage_template = stage_definition.stage_templates.get(template__frontend=self.hand.frontend)
            stb = StageTemplateBlockFactory(stage_template=stage_template, name='StageBlock')
            StageTemplateBlockTranslationFactory(
                stage_template_block=stb,
                language=self.hand.language,
                frontend=self.hand.frontend,
                content='<div id=\'test-widget\'><ModuleSubmitButton>Submit</ModuleSubmitButton></div>',
            )
        button = Widget.objects.get(name='Button', namespace='mui')
        md_widget = ModuleDefinitionWidgetFactory(
            widget=button, name='ModuleSubmitButton', module_definition=self.hand.current_module_definition
        )
        module_event = ModuleEventFactory(widget=md_widget, event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick, name='')
        ModuleEventStepFactory(
            module_event=module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.submit,
        )
        self.assertEqual(self.hand.stage.stage_definition, stage_definitions[0])
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(0.5)  # websocket needs time to connect
        next_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "test-widget")]/button'))
        )
        try:
            next_button.click()
            next_button.click()
            next_button.click()
        except selenium.common.exceptions.StaleElementReferenceException:  # If page has changed already
            pass
        time.sleep(3)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, stage_definitions[1])

    def test_combined_event(self):
        """Confirm communicate works as expected when ModuleWidget/child Widget both communicate events"""
        self.root_block_translation.content = '<StageBlock/>'
        self.root_block_translation.save()
        stage_definitions = self.hand.current_module_definition.stage_definitions.order_by('id')
        for stage_definition in stage_definitions:
            stage_template = stage_definition.stage_templates.get(template__frontend=self.hand.frontend)
            stb = StageTemplateBlockFactory(stage_template=stage_template, name='StageBlock')
            StageTemplateBlockTranslationFactory(
                stage_template_block=stb,
                language=self.hand.language,
                frontend=self.hand.frontend,
                content='<ModuleSubmitButton>Submit</ModuleSubmitButton>',
            )
        button = Widget.objects.get(name='SubmitButton')
        md_widget = ModuleDefinitionWidgetFactory(
            widget=button, name='ModuleSubmitButton', module_definition=self.hand.current_module_definition
        )
        module_event = ModuleEventFactory(widget=md_widget, event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick, name='')
        ModuleEventStepFactory(module_event=module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.submit)

        self.assertEqual(self.hand.stage.stage_definition, stage_definitions[0])
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(2)  # websocket needs time to connect
        next_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'mui-button')))
        try:
            next_button.click()
            next_button.click()
            next_button.click()
        except selenium.common.exceptions.StaleElementReferenceException:  # If page has changed already
            pass
        time.sleep(2)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, stage_definitions[2])

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=False, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestUpdateModule(EryChannelsTestCase):
    """
    Confirm advancement (from server) of hand's module leads to change in client react content.
    """

    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        web = Frontend.objects.get(name='Web')
        self.lab = LabFactory()
        stint_definition = create_test_stintdefinition(frontend=web, module_definition_n=2, stage_n=2, redirects=True)
        combo_obj = {'frontend': web, 'language': get_default_language()}

        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        self.hand = self.lab.current_stint.hands.first()
        tb = TemplateBlock.objects.get(
            name='Footer', template=self.hand.stage.stage_definition.stage_templates.first().template.parental_template
        )
        TemplateWidgetFactory(template=tb.template, widget=Widget.objects.get(name='SubmitButton'), name='SubmitButton')
        tb_translation = tb.translations.first()
        tb_translation.content += '<SubmitButton id=\'test-widget\'>Submit</SubmitButton>'
        tb_translation.save()
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_update_module(self):
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(0.5)  # websocket needs time to connect
        questions_1_id = (
            f'{self.hand.stage.stage_definition.module_definition.slug.lower()}-'
            f'{self.hand.stage.stage_definition.name.lower()}-questions'
        )

        questions = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, questions_1_id)))
        md_num = int(_clean_name(questions.get_attribute('innerHTML').split('ModuleDefinition')[-1]))
        button = self.driver.find_element_by_id('mui-button')
        button.click()
        time.sleep(3)
        self.hand.refresh_from_db()
        questions_2_id = (
            f'{self.hand.stage.stage_definition.module_definition.slug.lower()}-'
            f'{self.hand.stage.stage_definition.name.lower()}-questions'
        )

        questions_2 = self.driver.find_element_by_id(questions_2_id)
        new_md_num = int(_clean_name(questions_2.get_attribute('innerHTML').split('ModuleDefinition')[-1]))
        self.assertTrue(md_num < new_md_num)

    def tearDown(self):
        self.driver.close()
