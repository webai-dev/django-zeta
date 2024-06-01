# pylint: disable=too-many-lines
# XXX Split me up!

import re

from django.test import override_settings

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ery_backend.base.testcases import EryChannelsTestCase, create_test_stintdefinition
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.labs.factories import LabFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.users.factories import UserFactory


def _clean_name(name):
    from string import punctuation

    output = ''
    for char in name:
        if char not in punctuation:
            output += char
    return output


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestApp(EryChannelsTestCase):
    """
    Confirm full app rendered as expected.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)

    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        web = Frontend.objects.get(name='Web')
        self.lab = LabFactory()
        # XXX: re-add procedure in issue #463
        stint_definition = create_test_stintdefinition(frontend=web, render_args=['module_definition_widget', 'variable'])
        combo_obj = {'frontend': web, 'language': get_default_language()}
        stint_specification = StintSpecificationFactory(stint_definition=stint_definition, add_languagefrontends=[combo_obj])
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(1, jdeezy)
        self.hand = self.lab.current_stint.hands.first()
        hand = self.lab.current_stint.hands.first()
        self.module_definition_widget = hand.stage.stage_definition.module_definition.module_widgets.all()
        self.driver = self.get_loggedin_driver('test-user', headless=True, vendor=stint_specification.vendor)

    def test_render(self):
        block_prefix = f'{self.hand.current_module_definition.slug.lower()}-{self.hand.stage.stage_definition.name.lower()}'
        self.driver.get(f'{self.live_server_url}/labs/{self.lab.secret}/1')
        questions = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, f'{block_prefix}-questions')))
        self.assertTrue(
            re.match(
                'This is the content for the questions block belonging to StageDefinition0' r' \(ModuleDefinition[\w]+\)\.',
                questions.get_attribute('innerHTML'),
            )
        )
        answers = self.driver.find_element_by_id(f'{block_prefix}-answers')
        self.assertTrue(
            re.match(
                'This is the content for the answers block belonging to StageDefinition0' r' \(ModuleDefinition[\w]+\)\.',
                answers.get_attribute('innerHTML'),
            )
        )
        # XXX: re-add procedure in issue #463
        # procedure = self.driver.find_element_by_id(f'{block_prefix}-procedure')
        # self.assertTrue(re.match('This is the content for the procedure block of stage StageDefinition0 from'
        #                          r' module_definition ModuleDefinition[\w]+: 5.0',
        #                          procedure.get_attribute('innerHTML')))
        button_1_text = self.driver.find_element_by_xpath("//button[contains(@id, 'button-0')]/span[1]")
        self.assertTrue(
            re.match(
                'Sample text for module_definition_widget ModuleDefinitionWidgeta choice 1 of stage StageDefinition0'
                r' from module_definition ModuleDefinition[\w]+',
                button_1_text.get_attribute('innerHTML'),
            )
        )
        button_2_text = self.driver.find_element_by_xpath("//button[contains(@id, 'button-1')]/span[1]")

        self.assertTrue(
            re.match(
                'Sample text for module_definition_widget ModuleDefinitionWidgeta choice 2 of stage StageDefinition0'
                r' from module_definition ModuleDefinition[\w]+',
                button_2_text.get_attribute('innerHTML'),
            )
        )
        variable = self.driver.find_element_by_id(f"variable")
        self.assertTrue(
            re.match(
                'This is the content for the variable block of StageDefinition0 from module_definition'
                r' ModuleDefinition[\w]+: My name is...eraeraslimshady',
                variable.get_attribute('innerHTML'),
            )
        )

    def tearDown(self):
        self.driver.close()


# @override_settings(DEBUG=False, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
# class TestClientSideVars(EryChannelsTestCase):
#     @classmethod
#     def setUpClass(cls, *args, **kwargs):
#         super().setUpClass(*args, **kwargs)
#         cls.driver_1 = get_chromedriver(headless=True)
#         cls.driver_2 = get_chromedriver(headless=True)
#         cls.driver_3 = get_chromedriver(headless=True)

#     def setUp(self):
#         jdeezy = UserFactory(username='jdeezy')
#         web = Frontend.objects.get(name='Web')
#         self.lab = LabFactory()
#         self.stint_def = create_test_stintdefinition(frontend=web, module_definition_n=2, stage_n=2)
#         stintdef_moddef_1 = self.stint_def.stint_definition_module_definitions.order_by('order').first()
#         stintdef_moddef_2 = self.stint_def.stint_definition_module_definitions.exclude(id=stintdef_moddef_1.id).first()
#         self.mod_def_1 = stintdef_moddef_1.module_definition
#         self.module1_end_stage = self.mod_def_1.stage_definitions.last()
#         self.module1_end_stage.end_stage = True
#         self.module1_end_stage.save()
#         self.mod_def_2 = stintdef_moddef_2.module_definition
#         self.module1_module_vardef = VariableDefinitionFactory(
#             module_definition=self.mod_def_1, scope=VariableDefinition.SCOPE_CHOICES.module,
#             name='module_type', data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
#             validator=None, default_value='pay_me_now'
#         )
#         self.module2_module_vardef = VariableDefinitionFactory(
#             module_definition=self.mod_def_2, scope=VariableDefinition.SCOPE_CHOICES.module,
#             name='module_type', data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
#             validator=None, default_value='pay_me_later'
#         )
#         self.module1_team_vardef = VariableDefinitionFactory(
#             module_definition=self.mod_def_1, scope=VariableDefinition.SCOPE_CHOICES.team,
#             name='team_type', data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
#             validator=None, default_value='a_team'
#         )
#         self.module1_team_var_widget = ModuleDefinitionWidgetFactory(
#             module_definition=self.mod_def_1, variable_definition=self.module1_team_vardef
#         )
#         ModuleEventFactory(
#             widget=self.module1_team_var_widget,
#             event_type=ModuleEvent.EVENT_TYPE_CHOICES.save_var,
#             event=ModuleEvent.EVENT_CHOICES.onChange)
#         self.module2_team_vardef = VariableDefinitionFactory(
#             module_definition=self.mod_def_2, scope=VariableDefinition.SCOPE_CHOICES.team,
#             name='team_type', data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
#             validator=None, default_value='b_team'
#         )
#         self.module1_hand_vardef = VariableDefinitionFactory(
#             module_definition=self.mod_def_1, scope=VariableDefinition.SCOPE_CHOICES.hand,
#             name='free_money', data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
#             validator=None, default_value=55.56
#         )
#         self.module1_hand_var_widget = ModuleDefinitionWidgetFactory(
#             module_definition=self.mod_def_1, variable_definition=self.module1_hand_vardef
#         )
#         ModuleEventFactory(
#             widget=self.module1_hand_var_widget,
#             event_type=ModuleEvent.EVENT_TYPE_CHOICES.save_var,
#             event=ModuleEvent.EVENT_CHOICES.onChange)
#         self.module2_hand_vardef = VariableDefinitionFactory(
#             module_definition=self.mod_def_2, scope=VariableDefinition.SCOPE_CHOICES.hand,
#             name='free_money', data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
#             validator=None, default_value=555555.0
#         )
#         combo_obj = StintSpecificationAllowedLanguageFrontend.objects.get_or_create(frontend=web,
#                                                                                     language=get_default_language())[0]
#         combo_obj = StintSpecificationAllowedLanguageFrontend.objects.get_or_create(frontend=web,
#                                                                                     language=get_default_language())[0]

#         stint_specification = StintSpecificationFactory(stint_definition=self.stint_def,
#                                                         add_languagefrontends=[combo_obj],
#                                                         team_size=2, min_team_size=2, max_team_size=2)
#         self.lab.set_stint(stint_specification.id, jdeezy)
#         self.lab.start(4, jdeezy)
#         self.hands = list(self.lab.current_stint.hands.all())
#         stage_template = self.hands[0].stage.stage_definition.stage_templates.get(template__primary_frontend=web)
#         root_block = stage_template.get_root_block()
#         root_translation = root_block.translations.first()
#         root_translation.content = """

# This is the 1st hand var: {this.context.variables.free_money}.
# This is the 1st team var: {this.context.variables.team.team_type}.
# This is the 1st module var: {this.context.variables.module.module_type}."""
#         root_translation.save()
#         moddef_2_stagetemplate = self.mod_def_2.start_stage.stage_templates.get(template__primary_frontend=web)
#         root_block = moddef_2_stagetemplate.get_root_block()
#         root_translation = root_block.translations.first()
#         root_translation.content = """
# This is the 2nd hand var: {this.context.variables.free_money}.
# This is the 2nd team var: {this.context.variables.team.team_type}.
# This is the 2nd module var: {this.context.variables.module.module_type}."""
#         root_translation.save()

#     def test_variables_via_react_context(self):
#         hand = self.hands[0]
#         root_block_id = f'{self.mod_def_1.slug.lower()}-{hand.stage.stage_definition.name.lower()}-root'
#         self.driver_1.get(f'{self.live_server_url}/lab/{self.lab.secret}/1')
#         root_block = WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located(
#             (By.ID, root_block_id)))
#         block_text = (root_block.get_attribute('innerHTML'))
#         hand_var = hand.variables.get(variable_definition=self.module1_hand_vardef)
#         team_var = hand.current_team.variables.get(variable_definition=self.module1_team_vardef)
#         module_var = hand.current_module.variables.get(variable_definition=self.module1_module_vardef)

#         self.assertIn(f'This is the 1st hand var: {hand_var.value}', block_text)
#         self.assertIn(f'This is the 1st team var: {team_var.value}', block_text)
#         self.assertIn(f'This is the 1st module var: {module_var.value}', block_text)

#     def test_update_hand_variable_on_value_change(self):
#         hand = self.hands[0]
#         root_block_id = f'{self.mod_def_1.slug.lower()}-{hand.stage.stage_definition.name.lower()}-root'
#         self.driver_1.get(f'{self.live_server_url}/lab/{self.lab.secret}/1')
#         root_block = WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located(
#             (By.ID, root_block_id)))
#         block_text = root_block.get_attribute('innerHTML')
#         hand_var = hand.variables.get(variable_definition=self.module1_hand_vardef)
#         first_value = hand_var.value
#         self.assertIn(f'This is the 1st hand var: {first_value}', block_text)
#         time.sleep(.5)
#         # Dummy message must be sent for set_variable's message to be recieved
#         send_websocket_message(
#             hand, {'type': 'websocket.send', 'event': 'dummy_message', 'data': 'But why though?'})

#         # Change hand_var
#         self.module1_hand_var_widget.trigger_events(event=ModuleEvent.EVENT_CHOICES.onChange, hand=hand, value='24')
#         hand_var.refresh_from_db()
#         second_value = hand_var.value
#         time.sleep(.5)
#         root_block = WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located(
#             (By.ID, root_block_id)))
#         block_text = (root_block.get_attribute('innerHTML'))
#         self.assertIn(f'This is the 1st hand var: {second_value}', block_text)
#         ModuleDefinition.objects.all().delete()

#     @unittest.skip("Fix in issue #697")
#     def test_update_team_variable_on_value_change(self):
#         hand_1 = self.hands[0]
#         hand_2 = self.hands[1]
#         hand_3 = self.hands[2]
#         self.driver_1.get(f'{self.live_server_url}/lab/{self.lab.secret}/1')
#         self.driver_2.get(f'{self.live_server_url}/lab/{self.lab.secret}/2')
#         self.driver_3.get(f'{self.live_server_url}/lab/{self.lab.secret}/3')
#         # Dummy message must be sent for set_variable's message to be recieved
#         for hand in (hand_1, hand_2, hand_3):
#             send_websocket_message(
#                 hand, {'type': 'websocket.send', 'event': 'dummy_message', 'data': 'But why though?'})

#         hand_1_root_block_id = f'{self.mod_def_1.slug.lower()}-{hand_1.stage.stage_definition.name.lower()}-root'
#         root_block = WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located(
#             (By.ID, hand_1_root_block_id)))
#         block_text = root_block.get_attribute('innerHTML')
#         hand_1_team_var = hand_1.current_team.variables.get(variable_definition=self.module1_team_vardef)
#         hand_1_first_value = hand_1_team_var.value
#         self.assertIn(f'This is the 1st team var: {hand_1_first_value}', block_text)

#         hand_2_root_block_id = f'{self.mod_def_1.slug.lower()}-{hand_2.stage.stage_definition.name.lower()}-root'
#         root_block = WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located(
#             (By.ID, hand_2_root_block_id)))
#         block_text = root_block.get_attribute('innerHTML')
#         hand_2_team_var = hand_2.current_team.variables.get(variable_definition=self.module1_team_vardef)
#         hand_2_first_value = hand_2_team_var.value
#         self.assertIn(f'This is the 1st team var: {hand_2_first_value}', block_text)


#         # Change teammate's variable should lead to change in content on other teammates page.
#         self.module1_team_var_widget.trigger_events(event=ModuleEvent.EVENT_CHOICES.onChange, hand=hand_2, value='g_team')
#         time.sleep(.5)
#         hand_1_team_var.refresh_from_db()
#         hand_1_second_value = hand_1_team_var.value
#         self.assertEqual(hand_1_second_value, 'g_team')
#         root_block = self.driver_1.find_element_by_id(hand_1_root_block_id)
#         block_text = root_block.get_attribute('innerHTML')
#         self.assertIn(f'This is the 1st team var: {hand_1_second_value}', block_text)

#         # Should not change content of hand not on same team
#         hand_3_root_block_id = f'{self.mod_def_1.slug.lower()}-{hand_3.stage.stage_definition.name.lower()}-root'
#         hand_3_team_var = hand_3.current_team.variables.get(variable_definition=self.module1_team_vardef)
#         self.assertEqual(hand_3_team_var.value, hand_1_first_value)
#         root_block = self.driver_3.find_element_by_id(hand_3_root_block_id)
#         block_text = root_block.get_attribute('innerHTML')
#         self.assertIn(f'This is the 1st team var: {hand_1_first_value}', block_text)

#     @unittest.skip("Fix in issue #697")
#     def test_update_module_variable_on_value_change(self):
#         hand_1 = self.hands[0]
#         self.driver_1.get(f'{self.live_server_url}/lab/{self.lab.secret}/1')
#         hand_2 = self.hands[1]
#         self.driver_2.get(f'{self.live_server_url}/lab/{self.lab.secret}/2')
#         hand_3 = self.hands[2]
#         self.driver_3.get(f'{self.live_server_url}/lab/{self.lab.secret}/3')

#         # Dummy message must be sent for set_variable's message to be recieved
#         for hand in (hand_1, hand_2, hand_3):
#             send_websocket_message(
#                 hand, {'type': 'websocket.send', 'event': 'dummy_message', 'data': 'But why though?'})

#         hand_1_root_block_id = f'{self.mod_def_1.slug.lower()}-{hand_1.stage.stage_definition.name.lower()}-root'
#         root_block = self.driver_1.find_element_by_id(hand_1_root_block_id)
#         block_text = root_block.get_attribute('innerHTML')
#         hand_1_module_var = hand_1.current_module.variables.get(variable_definition=self.module1_module_vardef)
#         hand_1_first_value = hand_1_module_var.value
#         self.assertIn(f'This is the 1st module var: {hand_1_first_value}', block_text)

#         hand_2_root_block_id = f'{self.mod_def_1.slug.lower()}-{hand_2.stage.stage_definition.name.lower()}-root'
#         root_block = self.driver_2.find_element_by_id(hand_2_root_block_id)
#         block_text = root_block.get_attribute('innerHTML')
#         hand_2_module_var = hand_1.current_module.variables.get(variable_definition=self.module1_module_vardef)
#         hand_2_first_value = hand_2_module_var.value
#         self.assertIn(f'This is the 1st module var: {hand_2_first_value}', block_text)

#         # Move ahead a module
#         _, changed = hand_3.set_stage(stage_definition=self.module1_end_stage)
#         messages = gen_socket_messages_from_arg(changed, hand_3)
#         send_websocket_message(hand_3, {'type': 'websocket.send', 'messages': messages})

#         time.sleep(.5)
#         hand_3_root_block_id = f'{self.mod_def_2.slug.lower()}-{hand_3.stage.stage_definition.name.lower()}-root'
#         hand_3_module_var = hand_3.current_module.variables.get(variable_definition=self.module2_module_vardef)
#         root_block = self.driver_3.find_element_by_id(hand_3_root_block_id)
#         block_text = root_block.get_attribute('innerHTML')
#         self.assertIn(f'This is the 2nd module var: {hand_3_module_var.value}', block_text)
#         time.sleep(5)

#         # Should affect content of hands in same module
#         variable, _ = hand_1.stint.set_variable(variable_definition=self.module1_module_vardef, value='already_paid',
#                                                 hand=hand_1)
#         messages = gen_socket_messages_from_arg(variable, hand_1)
#         send_websocket_message(hand, {'type': 'websocket.send', 'messages': messages})

#         time.sleep(.5)
#         hand_2_module_var.refresh_from_db()
#         hand_2_second_value = hand_2_module_var.value
#         self.assertEqual(hand_2_second_value, 'already_paid')
#         root_block = self.driver_2.find_element_by_id(hand_1_root_block_id)
#         block_text = root_block.get_attribute('innerHTML')
#         self.assertIn(f'This is the 1st module var: {hand_2_second_value}', block_text)

#         # Should not change content of hands in different module
#         hand_3_root_block_id = f'{self.mod_def_2.slug.lower()}-{hand_3.stage.stage_definition.name.lower()}-root'
#         root_block = self.driver_3.find_element_by_id(hand_3_root_block_id)
#         block_text = root_block.get_attribute('innerHTML')
#         self.assertIn(f'This is the 2nd module var: {hand_3_module_var.value}', block_text)
#         time.sleep(5)


#     @unittest.skip("Fix in issue #697")
#     def test_update_all_variables_on_module_change(self):
#         hand = self.hands[0]
#         send_websocket_message(
#             hand, {'type': 'websocket.send', 'event': 'dummy_message', 'data': 'But why though?'})

#         root_block_id = f'{self.mod_def_1.slug.lower()}-{hand.stage.stage_definition.name.lower()}-root'
#         self.driver_1.get(f'{self.live_server_url}/lab/{self.lab.secret}/1')
#         root_block = self.driver_1.find_element_by_id(root_block_id)
#         block_text = (root_block.get_attribute('innerHTML'))
#         hand_var = hand.variables.get(variable_definition=self.module1_hand_vardef)
#         team_var = hand.current_team.variables.get(variable_definition=self.module1_team_vardef)
#         module_var = hand.current_module.variables.get(variable_definition=self.module1_module_vardef)

#         self.assertIn(f'This is the 1st hand var: {hand_var.value}', block_text)
#         self.assertIn(f'This is the 1st team var: {team_var.value}', block_text)
#         self.assertIn(f'This is the 1st module var: {module_var.value}', block_text)

#         _, changed = hand.set_stage(stage_definition=self.module1_end_stage)
#         messages = gen_socket_messages_from_arg(changed, hand)
#         send_websocket_message(hand, {'type': 'websocket.send', 'messages': messages})

#         hand.refresh_from_db()
#         time.sleep(.5)
#         root_block_id = f'{self.mod_def_2.slug.lower()}-{hand.stage.stage_definition.name.lower()}-root'
#         root_block = self.driver_1.find_element_by_id(root_block_id)
#         block_text = (root_block.get_attribute('innerHTML'))
#         hand_var = hand.variables.get(variable_definition=self.module2_hand_vardef)
#         team_var = hand.current_team.variables.get(variable_definition=self.module2_team_vardef)
#         module_var = hand.current_module.variables.get(variable_definition=self.module2_module_vardef)

#         self.assertIn(f'This is the 2nd hand var: {hand_var.value}', block_text)
#         self.assertIn(f'This is the 2nd team var: {team_var.value}', block_text)
#         self.assertIn(f'This is the 2nd module var: {module_var.value}', block_text)

#     @classmethod
#     def tearDownClass(cls, *args, **kwargs):
#         super().tearDownClass(*args, **kwargs)
#         for driver in (cls.driver_1, cls.driver_2, cls.driver_3):
#             driver.close()
