# pylint: disable=too-many-lines
# XXX Split me up!
import random
import re
import time
import unittest

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from django.test import override_settings
from languages_plus.models import Language

from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryChannelsTestCase, create_test_stintdefinition, create_test_hands
from ery_backend.base.utils import get_default_language
from ery_backend.syncs.factories import EraFactory
from ery_backend.frontends.models import Frontend
from ery_backend.modules.factories import (
    ModuleDefinitionWidgetFactory,
    ModuleEventFactory,
    ModuleEventStepFactory,
    WidgetChoiceFactory,
    WidgetChoiceTranslationFactory,
)
from ery_backend.modules.models import ModuleEvent, ModuleEventStep
from ery_backend.labs.factories import LabFactory
from ery_backend.stages.factories import (
    StageDefinitionFactory,
    StageTemplateFactory,
    StageTemplateBlockFactory,
    StageTemplateBlockTranslationFactory,
)
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.templates.factories import TemplateWidgetFactory
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import HandVariableFactory, VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetFactory, WidgetEventFactory, WidgetConnectionFactory, WidgetEventStepFactory
from ery_backend.widgets.models import WidgetEvent, Widget, WidgetEventStep, WidgetProp


def _clean_name(name):
    from string import punctuation

    output = ''
    for char in name:
        if char not in punctuation:
            output += char
    return output


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestTemplateWidgetRender(EryChannelsTestCase):
    """
    Confirm mui widget rendered as expected.
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
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_external_render(self):
        TemplateWidgetFactory(
            template=self.content_block.template, widget=Widget.objects.get(name='Card', namespace='mui'), name='Card'
        )
        self.translation.content = f'<div id="test-external-render"><Card>{self.translation.content}</Card>' '</div>'
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        # Let app receive socket messages
        time.sleep(3)
        questions_block = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f'//*[contains(@id, "test-external-render")]/div/div[1]'))
        )
        self.assertTrue(
            re.match(
                'This is the content for the questions block belonging to StageDefinition0' r' \(ModuleDefinition[\w]+\)\.',
                questions_block.get_attribute('innerHTML'),
            )
        )
        answers_block = self.driver.find_element_by_xpath(f'//*[contains(@id, "test-external-render")]/div/div[2]')
        self.assertTrue(
            re.match(
                'This is the content for the answers block belonging to StageDefinition0' r' \(ModuleDefinition[\w]+\)\.',
                answers_block.get_attribute('innerHTML'),
            )
        )

    def test_external_onclick_render(self):
        """
        Confirms onClick/onChange events work on a rendered external.
        """
        widget = Widget.objects.get(name='Input', namespace='mui')
        widget_event_1 = WidgetEvent.objects.get(event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, widget=widget, name='')
        WidgetEventStepFactory(
            widget_event=widget_event_1,
            code="alert('Im an alert');",
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
        )
        WidgetEventStepFactory(
            widget_event=widget_event_1,
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
            code="alert('I too am an alert');",
        )
        widget_event_2 = WidgetEvent.objects.get(event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange, widget=widget, name='')
        WidgetEventStepFactory(
            widget_event=widget_event_2,
            code="alert('I am the final alert');",
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
        )

        TemplateWidgetFactory(name='TestWidget', template=self.content_block.template, widget=widget)
        self.translation.content = "<TestWidget id='test-widget'>Click Me Please</TestWidget>"
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        mui_widget = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "test-widget")))
        mui_widget.click()
        # Alert 1
        alert = self.driver.switch_to_alert()
        alert.accept()
        # Alert 2
        alert = self.driver.switch_to_alert()
        alert.accept()
        mui_widget.send_keys('entering some values')
        # Alert 3
        alert = self.driver.switch_to_alert()
        alert.accept()

    def test_internal_render(self):
        widget = WidgetFactory(
            name='TestWidget',
            frontend=Frontend.objects.get(name='Web'),
            code='<Button id="test-widget">{children}</Button>',
            external=False,
        )

        WidgetConnectionFactory(originator=widget, target=Widget.objects.get(name='Button', namespace='mui'), name='Button')

        TemplateWidgetFactory(template=self.content_block.template, name='TestWidget', widget=widget)
        self.translation.content = f'<TestWidget>We Got A Widget Though!!!</TestWidget>'
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        widget_block = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        widget_block_span = widget_block.find_element_by_xpath('./span[1]')
        self.assertIn("We Got A Widget", widget_block_span.get_attribute('innerHTML'))

    @unittest.skip
    def test_nested_render(self):
        """
        Confirm widgets can be nested.
        """
        widget = WidgetFactory(
            name='CrazyWidget', code='<Button>{children}</Button>', frontend=Frontend.objects.get(name='Web'), external=False
        )
        TemplateWidgetFactory(name='CrazyWidget', template=self.content_block.template, widget=widget)
        WidgetConnectionFactory(originator=widget, target=Widget.objects.get(name='Button', namespace='mui'), name='Button')
        self.translation.content = f'<div id="test-widget"><CrazyWidget>Some extra stuff</CrazyWidget></div>'
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        content_block = WebDriverWait(self.driver, 10).until(
            EC.presence_of_elemengt_located((By.XPATH, "//*[contains(@id, 'test-widget')]/button/span[1]"))
        )
        self.assertIn("Some extra stuff", content_block.get_attribute('innerHTML'))

    def test_internal_onclick_render(self):
        """
        Confirms onClick/onChange events work on a rendered widget.
        """
        widget = WidgetFactory(
            name='TestWidget',
            code="<div id={id} onClick={handleClick}>I'm an alert</div>",
            frontend=Frontend.objects.get(name='Web'),
            external=False,
        )
        WidgetProp.objects.create(name='id', widget=widget)
        on_click_event = WidgetEventFactory(widget=widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, name='')
        WidgetEventStepFactory(
            widget_event=on_click_event,
            code="alert('Im an alert');",
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
        )
        WidgetEventStepFactory(
            widget_event=on_click_event,
            code="alert('I too am an alert');",
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
        )
        TemplateWidgetFactory(name='TestWidget', template=self.content_block.template, widget=widget)
        self.translation.content = "<TestWidget id='test-widget'>We got a widget though</TestWidget>"
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        mui_widget = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        mui_widget.click()
        # Alert 1
        alert = self.driver.switch_to_alert()
        alert.accept()
        # Alert 2
        alert = self.driver.switch_to_alert()
        alert.accept()

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestModuleWidgetRender(EryChannelsTestCase):
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
        stb = StageTemplateBlockFactory(stage_template=st, name='Questions')
        self.translation = StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            language=self.hand.language,
            frontend=self.hand.frontend,
            content='<Button id="test-widget">I am that. That am I.</Button>',
        )
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_external_render(self):
        ModuleDefinitionWidgetFactory(
            widget=Widget.objects.get(name='Button', namespace='mui'),
            module_definition=self.hand.current_module_definition,
            name='Button',
        )

        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        # Let app receive socket messages
        time.sleep(3)
        widget_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//button[contains(@id, "test-widget")]/span[1]'))
        )
        self.assertEqual('I am that. That am I.', widget_button.get_attribute('innerHTML'))

    def test_external_onclick_render(self):
        """
        Confirms onClick/onChange events in a Widget work when wrapped by ModuleWidget.
        """
        widget = Widget.objects.get(name='Input', namespace='mui')
        widget_event_1 = WidgetEvent.objects.get(event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, widget=widget, name='')
        WidgetEventStepFactory(
            widget_event=widget_event_1,
            code="alert('Im an alert');",
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
        )
        WidgetEventStepFactory(
            widget_event=widget_event_1,
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
            code="alert('I too am an alert');",
        )
        widget_event_2 = WidgetEvent.objects.get(event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange, widget=widget, name='')
        WidgetEventStepFactory(
            widget_event=widget_event_2,
            code="alert('I am the final alert');",
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
        )
        mdw = ModuleDefinitionWidgetFactory(
            name='TestWidget',
            widget=widget,
            module_definition=self.hand.current_module_definition,
            variable_definition__scope=VariableDefinition.SCOPE_CHOICES.hand,
        )
        HandVariableFactory(hand=self.hand, variable_definition=mdw.variable_definition)
        self.translation.content = "<TestWidget id='test-widget'>Click Me Please</TestWidget>"
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        mui_widget = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        mui_widget.click()
        # Alert 1
        alert = self.driver.switch_to_alert()
        alert.accept()
        # Alert 2
        alert = self.driver.switch_to_alert()
        alert.accept()
        mui_widget.send_keys('entering some values')
        # Alert 3
        alert = self.driver.switch_to_alert()
        alert.accept()

    def test_internal_render(self):
        widget = WidgetFactory(
            name='TestWidget',
            frontend=Frontend.objects.get(name='Web'),
            external=False,
            code='<Button {...props}>{children}</Button>',
        )

        WidgetConnectionFactory(originator=widget, target=Widget.objects.get(name='Button', namespace='mui'), name='Button')

        ModuleDefinitionWidgetFactory(name='TestWidget', widget=widget, module_definition=self.hand.current_module_definition)
        self.translation.content = f'<TestWidget id=\'test-widget\'>We Got A Widget Though!!!</TestWidget>'
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        widget_block = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        widget_block_span = widget_block.find_element_by_xpath('./span[1]')
        self.assertIn("We Got A Widget", widget_block_span.get_attribute('innerHTML'))

    @unittest.skip
    def test_nested_render(self):
        """
        Confirm widgets can be nested.
        """
        widget = WidgetFactory(
            name='CrazyWidget', code='<Button {...props}>{children}</Button>', frontend=Frontend.objects.get(name='Web')
        )
        WidgetConnectionFactory(originator=widget, target=Widget.objects.get(name='Button', namespace='mui'), name='Button')
        ModuleDefinitionWidgetFactory(name='CrazyWidget', widget=widget, module_definition=self.hand.current_module_definition)
        self.translation.content = f'<CrazyWidget id="test-widget">Some extra stuff</CrazyWidget>'
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        content_block = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        content_block_span = content_block.find_element_by_xpath('./span[1]')
        self.assertIn("Some extra stuff", content_block_span.get_attribute('innerHTML'))

    def test_internal_onclick_render(self):
        """
        Confirms onClick/onChange events work on a rendered widget.
        """
        widget = WidgetFactory(
            name='TestWidget',
            code="<Input onClick={handleClick} onChange={handleChange} {...props}>I'm an alert</Input>",
            frontend=Frontend.objects.get(name='Web'),
            external=False,
        )
        onclick_event = WidgetEventFactory(widget=widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, name='')
        WidgetEventStepFactory(
            widget_event=onclick_event,
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
            code="alert(\"I'm an alert\");",
        )
        WidgetEventStepFactory(
            widget_event=onclick_event,
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
            code="alert(\"I too am an alert\");",
        )
        onchange_event = WidgetEventFactory(widget=widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange, name='')
        WidgetEventStepFactory(
            widget_event=onchange_event,
            event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
            code="alert(\"I'm the final alert\");",
        )

        WidgetConnectionFactory(originator=widget, target=Widget.objects.get(name='Input', namespace='mui'), name='Input')
        ModuleDefinitionWidgetFactory(name='TestWidget', widget=widget, module_definition=self.hand.current_module_definition)
        self.translation.content = "<TestWidget id='test-widget'>We got a widget though</TestWidget>"
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        mui_widget = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        mui_widget.click()
        # Alert 1
        alert = self.driver.switch_to_alert()
        alert.accept()
        # Alert 2
        alert = self.driver.switch_to_alert()
        alert.accept()
        mui_widget.send_keys('entering some values')
        # Alert 3
        alert = self.driver.switch_to_alert()
        alert.accept()

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestBackButtonRender(EryChannelsTestCase):
    def setUp(self):
        web = Frontend.objects.get(name='Web')
        jdeezy = UserFactory(username='jdeezy')
        stint_definition = create_test_stintdefinition(frontend=web, module_definition_n=2, stage_n=2)
        combo_obj = {'frontend': web, 'language': get_default_language()}
        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab = LabFactory()
        self.lab.set_stint(stint_specification.pk, jdeezy)
        self.lab.start(1, jdeezy)
        self.hand = self.lab.current_stint.hands.first()
        self.initial_stagedef = self.hand.stage.stage_definition
        self.back_button = Widget.objects.get(name='BackButton')
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_back_button_intermodule(self):
        next_stagedef = (
            self.hand.stint.stint_specification.stint_definition.module_definitions.exclude(
                id=self.initial_stagedef.module_definition.id
            )
            .first()
            .start_stage
        )
        next_stagedef.breadcrumb_type = next_stagedef.BREADCRUMB_TYPE_CHOICES.all
        next_stagedef.save()
        next_stagedef.refresh_from_db()
        self.hand.set_stage(stage_definition=next_stagedef)
        self.hand.refresh_from_db()
        next_crumb = self.hand.create_breadcrumb(self.hand.stage)
        self.hand.set_breadcrumb(next_crumb)
        self.hand.refresh_from_db()
        stage_template = next_stagedef.stage_templates.get(template__frontend__name='Web')
        questions_block = stage_template.template.parental_template.blocks.get(name='Questions')
        TemplateWidgetFactory(name='BackButton', widget=self.back_button, template=questions_block.template)
        translation = questions_block.translations.get(language__pk='en')
        translation.content = '<BackButton id=\'mui-button\' {...props}/>'
        translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(2)  # Let it load, let it load
        answers_2_id = (
            f'{self.hand.current_module_definition.slug.lower()}-' f'{self.hand.stage.stage_definition.name.lower()}-answers'
        )
        answers_2 = self.driver.find_element_by_xpath(f'//div[contains(@id, "{answers_2_id}")]')
        module_num_2 = int(_clean_name(answers_2.get_attribute('innerHTML').split('ModuleDefinition')[-1]))
        button = self.driver.find_element_by_id('mui-button')
        button.click()
        time.sleep(3)
        self.hand.refresh_from_db()
        answers_1_id = (
            f'{self.hand.current_module_definition.slug.lower()}-' f'{self.hand.stage.stage_definition.name.lower()}-answers'
        )
        answers_1 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, answers_1_id)))
        module_num_1 = int(_clean_name(answers_1.get_attribute('innerHTML').split('ModuleDefinition')[-1]))
        self.assertNotEqual(module_num_1, module_num_2)

    def test_back_button_intramodule(self):
        next_stagedef = self.hand.current_module_definition.stage_definitions.exclude(id=self.initial_stagedef.id).first()
        next_stagedef.breadcrumb_type = next_stagedef.BREADCRUMB_TYPE_CHOICES.all
        next_stagedef.save()
        next_stagedef.refresh_from_db()
        self.hand.set_stage(stage_definition=next_stagedef)
        self.hand.refresh_from_db()
        next_crumb = self.hand.create_breadcrumb(self.hand.stage)
        self.hand.set_breadcrumb(next_crumb)
        self.hand.refresh_from_db()
        stage_template = next_stagedef.stage_templates.get(template__frontend__name='Web')
        questions_block = stage_template.template.parental_template.blocks.get(name='Questions')
        TemplateWidgetFactory(name='BackButton', widget=self.back_button, template=questions_block.template)
        translation = questions_block.translations.get(language__pk='en')
        translation.content = '<BackButton id=\'mui-button\' />'
        translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        answers_2_id = (
            f'{self.hand.current_module_definition.slug.lower()}-' f'{self.hand.stage.stage_definition.name.lower()}-answers'
        )
        time.sleep(3)  # websocket needs time to connect
        answers_2 = self.driver.find_element_by_xpath(f'//div[contains(@id, "{answers_2_id}")]')
        stage_num_2 = int(
            _clean_name(answers_2.get_attribute('innerHTML').split('StageDefinition')[-1].split('ModuleDefinition')[0])
        )
        button = self.driver.find_element_by_id('mui-button')
        button.click()
        time.sleep(3)
        self.hand.refresh_from_db()
        answers_1_id = (
            f'{self.hand.current_module_definition.slug.lower()}-' f'{self.hand.stage.stage_definition.name.lower()}-answers'
        )
        answers_1 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, answers_1_id)))
        stage_num_1 = int(
            _clean_name(answers_1.get_attribute('innerHTML').split('StageDefinition')[-1].split('ModuleDefinition')[0])
        )
        self.assertNotEqual(stage_num_1, stage_num_2)

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=False, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestSubmitButtonRender(EryChannelsTestCase):
    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        hand = create_test_hands(n=1, module_definition_n=2, stage_n=2, redirects=True).first()
        stint_specification = hand.stint.stint_specification
        stage_template = hand.stage.stage_definition.stage_templates.get(template__frontend__name='Web')
        submit_button = Widget.objects.get(name='SubmitButton')
        questions_block = stage_template.template.parental_template.blocks.get(name='Questions')
        TemplateWidgetFactory(name='SubmitButton', widget=submit_button, template=questions_block.template)
        translation = questions_block.translations.get(language__pk='en')
        translation.content = '<SubmitButton id=\'mui-button\'/>'
        translation.save()
        self.lab = LabFactory()
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_submit_button_render(self):
        hand = self.lab.current_stint.hands.first()
        answers_1_id = (
            f'{hand.stage.stage_definition.module_definition.slug.lower()}-'
            f'{hand.stage.stage_definition.name.lower()}-answers'
        )
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        # Wait for socket messages
        time.sleep(3)
        answers_1 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, answers_1_id)))
        md_num_1 = int(_clean_name(answers_1.get_attribute('innerHTML').split('ModuleDefinition')[-1]))
        button = self.driver.find_element_by_id('mui-button')
        button.click()
        time.sleep(3)
        hand.refresh_from_db()
        answers_2_id = (
            f'{hand.stage.stage_definition.module_definition.slug.lower()}-'
            f'{hand.stage.stage_definition.name.lower()}-answers'
        )
        answers_2 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, answers_2_id)))
        md_num_2 = int(_clean_name(answers_2.get_attribute('innerHTML').split('ModuleDefinition')[-1]))
        self.assertNotEqual(md_num_1, md_num_2)

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestModuleBackButtonRender(EryChannelsTestCase):
    def setUp(self):
        web = Frontend.objects.get(name='Web')
        jdeezy = UserFactory(username='jdeezy')
        stint_definition = create_test_stintdefinition(frontend=web, module_definition_n=2, stage_n=2)
        combo_obj = {'frontend': web, 'language': get_default_language()}
        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.language = get_default_language()
        self.lab = LabFactory()
        self.lab.set_stint(stint_specification.pk, jdeezy)
        self.lab.start(1, jdeezy)
        self.hand = self.lab.current_stint.hands.first()
        self.initial_stagedef = self.hand.stage.stage_definition
        widget = Widget.objects.get(name='Button', namespace='mui')
        # XXX: Address in issue #539.
        wrapping_widget = WidgetFactory(
            name='RapButton', code='<Button id={id} onClick={handleClick}>Back</Button>', frontend=web, external=False
        )
        WidgetProp.objects.create(name='id', widget=wrapping_widget)
        WidgetEventFactory(name='', event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, widget=wrapping_widget)
        WidgetConnectionFactory(originator=wrapping_widget, target=widget, name='Button')
        self.back_button = ModuleDefinitionWidgetFactory(
            module_definition=self.hand.current_module_definition, widget=wrapping_widget, name="BackButton"
        )
        module_event = ModuleEventFactory(event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick, widget=self.back_button, name='')
        ModuleEventStepFactory(event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.back, module_event=module_event)
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_back_button_intramodule(self):
        next_stagedef = self.hand.current_module_definition.stage_definitions.exclude(id=self.initial_stagedef.id).first()
        next_stagedef.breadcrumb_type = next_stagedef.BREADCRUMB_TYPE_CHOICES.all
        next_stagedef.save()
        next_stagedef.refresh_from_db()
        self.hand.set_stage(stage_definition=next_stagedef)
        self.hand.refresh_from_db()
        next_crumb = self.hand.create_breadcrumb(self.hand.stage)
        self.hand.set_breadcrumb(next_crumb)
        self.hand.refresh_from_db()
        stage_template = next_stagedef.stage_templates.get(template__frontend__name='Web')
        stb = StageTemplateBlockFactory(stage_template=stage_template, name='Questions')
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            language=self.language,
            frontend=self.hand.frontend,
            content='<BackButton id=\'mui-button\'>Back</BackButton>',
        )
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        answers_2_id = (
            f'{self.hand.current_module_definition.slug.lower()}-' f'{self.hand.stage.stage_definition.name.lower()}-answers'
        )
        answers_2 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, answers_2_id)))
        stage_num_2 = int(
            _clean_name(answers_2.get_attribute('innerHTML').split('StageDefinition')[-1].split('ModuleDefinition')[0])
        )
        time.sleep(2)  # websocket needs time to connect
        button = self.driver.find_element_by_id('mui-button')
        button.click()
        time.sleep(2)
        self.hand.refresh_from_db()
        answers_1_id = (
            f'{self.hand.current_module_definition.slug.lower()}-' f'{self.hand.stage.stage_definition.name.lower()}-answers'
        )
        answers_1 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, answers_1_id)))
        stage_num_1 = int(
            _clean_name(answers_1.get_attribute('innerHTML').split('StageDefinition')[-1].split('ModuleDefinition')[0])
        )
        self.assertNotEqual(stage_num_1, stage_num_2)

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestModuleSubmitButtonRender(EryChannelsTestCase):
    def setUp(self):
        web = Frontend.objects.get(name='Web')
        jdeezy = UserFactory(username='jdeezy')
        hand = create_test_hands(n=1, module_definition_n=2, stage_n=2, redirects=True).first()
        stint_specification = hand.stint.stint_specification
        stage_template = hand.stage.stage_definition.stage_templates.get(template__frontend__name='Web')
        language = get_default_language()
        widget = Widget.objects.get(name='Button', namespace='mui')
        wrapping_widget = WidgetFactory(
            name='RapButton', code='<Button id={id} onClick={handleClick}>{children}</Button>', frontend=web, external=False
        )

        WidgetEventFactory(name='', event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick, widget=wrapping_widget)
        WidgetProp.objects.create(name='id', widget=wrapping_widget)
        WidgetConnectionFactory(originator=wrapping_widget, target=widget, name='Button')
        submit_button = ModuleDefinitionWidgetFactory(
            module_definition=hand.current_module_definition, widget=wrapping_widget, name="SubmitButton"
        )
        module_event = ModuleEventFactory(event_type=ModuleEvent.REACT_EVENT_CHOICES.onClick, widget=submit_button, name='')
        ModuleEventStepFactory(module_event=module_event, event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.submit)
        stb = StageTemplateBlockFactory(stage_template=stage_template, name='Questions')
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            language=language,
            frontend=hand.frontend,
            content='<SubmitButton id=\'mui-button\'>Submit</SubmitButton>',
        )
        self.lab = LabFactory()
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        self.end_stagedef = StageDefinitionFactory(module_definition=hand.current_module_definition, end_stage=True)
        template = hand.stage.stage_definition.stage_templates.get(template__frontend__name='Web').template
        StageTemplateFactory(stage_definition=self.end_stagedef, template=template)
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_submit_button_render(self):
        hand = self.lab.current_stint.hands.first()
        hand.stage.stage_definition.next_stage = self.end_stagedef
        hand.stage.stage_definition.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        answers_1_id = f'{hand.current_module_definition.slug.lower()}-' f'{hand.stage.stage_definition.name.lower()}-answers'
        time.sleep(2)  # websocket needs time to connect
        answers_1 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, answers_1_id)))
        md_num_1 = int(_clean_name(answers_1.get_attribute('innerHTML').split('ModuleDefinition')[-1]))
        button = self.driver.find_element_by_id('mui-button')
        button.click()
        time.sleep(3)
        hand.refresh_from_db()
        answers_2_id = f'{hand.current_module_definition.slug.lower()}-' f'{hand.stage.stage_definition.name.lower()}-answers'
        answers_2 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, answers_2_id)))
        md_num_2 = int(_clean_name(answers_2.get_attribute('innerHTML').split('ModuleDefinition')[-1]))
        self.assertNotEqual(md_num_1, md_num_2)

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestSaveVar(EryChannelsTestCase):
    """
    Confirm variable values can be set via the save_var ModuleWidgetEvent.
    """

    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        web = Frontend.objects.get(name='Web')
        self.lab = LabFactory()
        stint_definition = create_test_stintdefinition(frontend=web, module_definition_n=1, stage_n=2, redirects=True)
        combo_obj = {'frontend': web, 'language': get_default_language()}

        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        self.hand = self.lab.current_stint.hands.first()
        save_vd = VariableDefinitionFactory(
            module_definition=self.hand.current_module_definition,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            validator=None,
        )
        self.save_var = HandVariableFactory(variable_definition=save_vd, hand=self.hand)
        input_widget = Widget.objects.get(name='Input', namespace='mui')
        self.input_widget_wrapper = WidgetFactory(
            name='InputWrapper', external=False, code='<Input id={id} onChange={handleChange}/>', frontend=web
        )
        WidgetConnectionFactory(originator=self.input_widget_wrapper, target=input_widget, name='Input')
        WidgetProp.objects.create(widget=self.input_widget_wrapper, name='id')
        WidgetEventFactory(event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange, widget=self.input_widget_wrapper, name='')
        md_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.hand.current_module_definition,
            widget=self.input_widget_wrapper,
            name='InputWrapper',
            initial_value='',
            variable_definition=save_vd,
        )
        module_event = ModuleEventFactory(event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange, widget=md_widget, name='')
        ModuleEventStepFactory(event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.save_var, module_event=module_event)
        stage_template = self.hand.stage.stage_definition.stage_templates.get(template__frontend=web)
        content_translation = stage_template.template.parental_template.blocks.get(name='Content').translations.first()
        content_translation.content = '<TestSave />'
        content_translation.save()
        stb = StageTemplateBlockFactory(name='TestSave', stage_template=stage_template)

        StageTemplateBlockTranslationFactory(
            stage_template_block=stb, content='<InputWrapper id=\'test-widget\'>Click Me!</InputWrapper>', frontend=web
        )
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_save_input(self):
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(2)
        widget = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//*[contains(@id, 'test-widget')]"))
        )
        widget.send_keys('Some keys')
        time.sleep(2)  # Give enough time to save 5 times
        self.save_var.refresh_from_db()
        self.assertEqual(self.save_var.value, 'Some keys')

    def test_combined_event(self):
        """
        Confirm save and next can be performed simultaneously.
        """
        next_stage = self.hand.current_module_definition.stage_definitions.exclude(
            id=self.hand.stage.stage_definition.id
        ).first()
        widget_event = self.input_widget_wrapper.events.get(event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)
        WidgetEventStepFactory(event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.submit, widget_event=widget_event)
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(2)  # Give enough time to save and change stage client-side
        widget = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        widget.send_keys('a')
        time.sleep(2)  # Give enough time to save and change stage client-side
        self.save_var.refresh_from_db()
        self.hand.refresh_from_db()
        self.assertEqual(self.save_var.value, 'a')
        questions_id = (
            f'{self.hand.current_module_definition.slug.lower()}-' f'{self.hand.stage.stage_definition.name.lower()}-questions'
        )
        questions = self.driver.find_element_by_id(questions_id)
        sd_num = _clean_name(questions.get_attribute('innerHTML').split('StageDefinition')[-1]).split(' ')[0]
        self.assertEqual(sd_num, next_stage.name[-1])

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestRunAction(EryChannelsTestCase):
    """
    Confirm era can be set via the run_action ModuleWidgetEvent.
    """

    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        web = Frontend.objects.get(name='Web')
        self.lab = LabFactory()
        stint_definition = create_test_stintdefinition(frontend=web, module_definition_n=1, stage_n=2)
        combo_obj = {'frontend': web, 'language': get_default_language()}

        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        self.hand = self.lab.current_stint.hands.first()
        self.era = EraFactory(module_definition=self.hand.current_module_definition)
        input_widget = Widget.objects.get(name='Input', namespace='mui')
        self.input_widget_wrapper = WidgetFactory(
            name='InputWrapper', external=False, code='<Input {...props}/>', frontend=web
        )
        WidgetEventFactory(name='', widget=self.input_widget_wrapper, event_type=WidgetEvent.REACT_EVENT_CHOICES.onChange)
        WidgetConnectionFactory(originator=self.input_widget_wrapper, target=input_widget, name='Input')
        md_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.hand.current_module_definition,
            widget=self.input_widget_wrapper,
            name='InputWrapper',
            initial_value='',
        )
        action = ActionFactory(module_definition=self.hand.current_module_definition)
        ActionStepFactory(
            action=action,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
            era=self.era,
            condition=None,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        module_event = ModuleEventFactory(event_type=ModuleEvent.REACT_EVENT_CHOICES.onChange, widget=md_widget, name='')

        ModuleEventStepFactory(
            event_action_type=ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action, action=action, module_event=module_event
        )
        stage_template = self.hand.stage.stage_definition.stage_templates.get(template__frontend=web)
        content_translation = stage_template.template.parental_template.blocks.get(name='Content').translations.first()
        content_translation.content = '<TestAction/>'
        content_translation.save()
        stb = StageTemplateBlockFactory(name='TestAction', stage_template=stage_template)

        StageTemplateBlockTranslationFactory(
            stage_template_block=stb, content='<InputWrapper id=\'test-widget\'>Click Me!</InputWrapper>', frontend=web
        )
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_set_era(self):
        self.assertNotEqual(self.hand.era, self.era)
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(3)
        widget = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'test-widget')))
        widget.send_keys('a')
        time.sleep(1)  # Give enough time to set_era
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.era, self.era)

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestInputRender(EryChannelsTestCase):
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
        self.translation = self.content_block.translations.first()
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_button_render(self):
        widget = WidgetFactory(name='InputWidget', code='<Button>{children}</Button>', frontend=self.web, external=False)
        WidgetConnectionFactory(originator=widget, target=Widget.objects.get(name='Button', namespace='mui'), name='Button')
        TemplateWidgetFactory(template=self.content_block.template, widget=widget, name='MyModuleDefinitionWidget')
        self.translation.content = (
            '<div id=\'test-widget\'><MyModuleDefinitionWidget>It\'s a button, so press it!'
            '</MyModuleDefinitionWidget></div>'
        )
        self.translation.save()
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        time.sleep(2)
        button_block = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@id, 'test-widget')]/button/span[1]"))
        )

        self.assertIn("It's a button, so press it!", button_block.get_attribute('innerHTML'))

    def test_choices_render(self):
        widget = WidgetFactory(
            name='InputWidget',
            code="{(choices).map((choice, index) => "
            "<React.Fragment><Button id={'button-' + String(index)} key={index}>{choice.caption}</Button>"
            "<Divider/></React.Fragment>)}",
            frontend=self.web,
            external=False,
        )
        variable_definition = VariableDefinitionFactory(
            data_type=random.choice(
                [
                    data_type
                    for data_type, _ in VariableDefinition.DATA_TYPE_CHOICES
                    if data_type not in [VariableDefinition.DATA_TYPE_CHOICES.bool, VariableDefinition.DATA_TYPE_CHOICES.stage]
                ]
            )
        )
        module_definition_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition,
            widget=widget,
            name='MyModuleDefinitionWidget',
            variable_definition=variable_definition,
        )
        widget_choice1 = WidgetChoiceFactory(widget=module_definition_widget, order=0)
        widget_choice2 = WidgetChoiceFactory(widget=module_definition_widget, order=1)
        widget_choice3 = WidgetChoiceFactory(widget=module_definition_widget, order=2)
        translation1 = WidgetChoiceTranslationFactory(
            language=self.module_definition.primary_language, widget_choice=widget_choice1, caption="Show me the money!"
        )
        translation2 = WidgetChoiceTranslationFactory(
            language=self.module_definition.primary_language, widget_choice=widget_choice2, caption="I love the potato man!"
        )
        translation3 = WidgetChoiceTranslationFactory(
            language=self.module_definition.primary_language, widget_choice=widget_choice3, caption="You're my other brother!"
        )
        WidgetConnectionFactory(originator=widget, target=Widget.objects.get(name='Button', namespace='mui'), name='Button')
        WidgetConnectionFactory(originator=widget, target=Widget.objects.get(name='Divider', namespace='mui'), name='Divider')

        self.translation.content = '<ChoiceTest />'
        self.translation.save()
        stb = StageTemplateBlockFactory(stage_template=self.st, name='ChoiceTest')
        StageTemplateBlockTranslationFactory(
            stage_template_block=stb,
            content='<MyModuleDefinitionWidget name="choice-test">Such and such</MyModuleDefinitionWidget>',
            language=self.language,
            frontend=self.web,
        )
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[contains(@id, 'button-0')]")))
        widget_blocks = self.driver.find_elements_by_xpath("//div[contains(@id, 'container')]/button/span")
        input_text = [block.get_attribute('innerHTML') for block in widget_blocks]
        self.assertIn(translation1.caption, input_text)
        self.assertIn(translation2.caption, input_text)
        self.assertIn(translation3.caption, input_text)

    def tearDown(self):
        self.driver.close()
