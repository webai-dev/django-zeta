# -*- coding: utf-8 -*-

# pylint: disable=too-many-lines
# XXX Split me up!

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from django.test import override_settings

from ery_backend.base.testcases import EryChannelsTestCase, create_test_stintdefinition, get_chromedriver
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory, ModuleEventFactory
from ery_backend.modules.models import ModuleEvent
from ery_backend.labs.factories import LabFactory
from ery_backend.stages.factories import StageTemplateBlockFactory, StageTemplateBlockTranslationFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.stint_specifications.models import StintSpecificationAllowedLanguageFrontend
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.models import Widget


def _clean_name(name):
    from string import punctuation

    output = ''
    for char in name:
        if char not in punctuation:
            output += char
    return output


# XXX: Address in issue # 564
# @override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
# class TestStintDefinitionVariableDefinition(EryLiveServerTestCase):
#     """
#     Make sure the StintDefinitionVariableDefinition's work ... works
#     """


#     @classmethod
#     def setUpClass(cls, *args, **kwargs):
#         super().setUpClass(*args, **kwargs)
#         cls.driver = get_chromedriver(headless=False)

#     def setUp(self, *args, **kwargs):
#         self.lab = LabFactory()
#         self.user = UserFactory()

#     def test_variable_linkage(self):
#         """Ensure that linking variable definitions results in connected data"""
#         stint_definition = create_test_stintdefinition(Frontend.objects.get(name="Web"), module_definition_n=2, stage_n=2)
#         stint_specification = StintSpecificationFactory(stint_definition=stint_definition)

#         next_button = Widget.objects.get(name="NextButton")

#         self.lab.set_stint(stint_specification.id, self.user)
#         self.lab.start(1, self.user)
#         self.driver.get(f"{self.live_server_url}/lab/{self.lab.secret}/1")
#         input("Call it")

#         #  To be continued ....
#         # Create two module definitions
#             # each module definition should link to two+ stages
#             # the stages of each module should operate as a progression*
#             # base.test_cases.create_complex_stageddefinition might cover it
# Module 1 Stage 1 needs a "pay value*" VariableDefinition
# Module 2 Stage 1 should have a VariableDefinition that shares a StintDefinitionVariableDefinition with Module 1 stage 1

#             # The default value for each variable definition should be different

#         # Add something to the pay value on module 1's variable definition*
#         # Compare final value of the first and second variable definition
#             # Both variable values should still be different
#             # Both variable values should have increased the same added amount
#         # * = I'm not sure how this is implemented ... yet


#         # --- DETAILS
#         # create_test_stint_definition(module_definition_n, stage_n)
#         # connect stages with widgets
#         #   - see babel_client_tests.TestNextButton
#         #   - use widget.trigger_events for progression
#         # Add variable definitions manually
#         # add sdvds manually
#         # add (module defintion / template)  widgets manually
#         # use an action connected to the widget to add numbers to the variable

#     def test_sdvd_connects_variables(self):
#         """
#         When variables are connected via StintDefinitionVariableDefinition,
#         they should operate as if they mean the same thing
#         in their respective modules
#         """
#         pass


@override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestClientSideVars(EryChannelsTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.driver_1 = get_chromedriver(headless=False)
        cls.driver_2 = get_chromedriver(headless=True)
        cls.driver_3 = get_chromedriver(headless=True)

    def setUp(self):
        jdeezy = UserFactory(username='jdeezy')
        web = Frontend.objects.get(name='Web')
        input_widget = Widget.objects.get(name='Input', namespace='mui')
        self.lab = LabFactory()
        # self.stint_def = create_test_stintdefinition(frontend=web, module_definition_n=2, stage_n=2)
        self.stint_def = create_test_stintdefinition(frontend=web, module_definition_n=2, stage_n=2)
        stintdef_moddef_1 = self.stint_def.stint_definition_module_definitions.order_by('order').first()
        stintdef_moddef_2 = self.stint_def.stint_definition_module_definitions.exclude(id=stintdef_moddef_1.id).first()
        self.mod_def_1 = stintdef_moddef_1.module_definition
        self.module1_end_stage = self.mod_def_1.stage_definitions.last()
        self.module1_end_stage.end_stage = True
        self.module1_end_stage.save()
        self.mod_def_2 = stintdef_moddef_2.module_definition
        self.module1_module_vardef = VariableDefinitionFactory(
            module_definition=self.mod_def_1,
            scope=VariableDefinition.SCOPE_CHOICES.module,
            name='module_type',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            validator=None,
            default_value='pay_me_now',
        )
        self.module2_module_vardef = VariableDefinitionFactory(
            module_definition=self.mod_def_2,
            scope=VariableDefinition.SCOPE_CHOICES.module,
            name='module_type',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            validator=None,
            default_value='pay_me_later',
        )
        self.module1_team_vardef = VariableDefinitionFactory(
            module_definition=self.mod_def_1,
            scope=VariableDefinition.SCOPE_CHOICES.team,
            name='team_type',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            validator=None,
            default_value='a_team',
        )
        self.module1_team_var_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.mod_def_1, variable_definition=self.module1_team_vardef, widget=input_widget
        )
        ModuleEventFactory(
            widget=self.module1_team_var_widget,
            event_type=ModuleEvent.EVENT_TYPE_CHOICES.save_var,
            event=ModuleEvent.EVENT_CHOICES.onChange,
        )
        self.module2_team_vardef = VariableDefinitionFactory(
            module_definition=self.mod_def_2,
            scope=VariableDefinition.SCOPE_CHOICES.team,
            name='team_type',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            validator=None,
            default_value='b_team',
        )
        self.module1_hand_vardef = VariableDefinitionFactory(
            module_definition=self.mod_def_1,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            name='free_money',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            validator=None,
            default_value=55.56,
        )
        self.module1_hand_var_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.mod_def_1, variable_definition=self.module1_hand_vardef, widget=input_widget
        )
        ModuleEventFactory(
            widget=self.module1_hand_var_widget,
            event_type=ModuleEvent.EVENT_TYPE_CHOICES.save_var,
            event=ModuleEvent.EVENT_CHOICES.onChange,
        )
        self.module2_hand_vardef = VariableDefinitionFactory(
            module_definition=self.mod_def_2,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            name='free_money',
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            validator=None,
            default_value=555555.0,
        )
        combo_obj = StintSpecificationAllowedLanguageFrontend.objects.get_or_create(
            frontend=web, language=get_default_language()
        )[0]

        stint_specification = StintSpecificationFactory(
            stint_definition=self.stint_def, add_languagefrontends=[combo_obj], team_size=2, min_team_size=2, max_team_size=2
        )
        self.lab.set_stint(stint_specification.id, jdeezy)
        self.lab.start(4, jdeezy)
        self.hands = list(self.lab.current_stint.hands.all())
        hand = self.hands[0]

        stage_template = self.hands[0].stage.stage_definition.stage_templates.get(template__frontend=web)
        stb = StageTemplateBlockFactory(stage_template=stage_template, name='Questions')
        translation = StageTemplateBlockTranslationFactory(
            stage_template_block=stb, language=hand.language, frontend=hand.frontend, content=""
        )
        translation.content = """
<div id='q1'>
This is the 1st hand var: {free_money}.
This is the 1st team var: {team_type}.
This is the 1st module var: {module_type}.
</div>
"""
        translation.save()
        moddef_2_stagetemplate = self.mod_def_2.start_stage.stage_templates.get(template__frontend=web)
        stb_2 = StageTemplateBlockFactory(stage_template=moddef_2_stagetemplate, name='Questions')
        translation_2 = StageTemplateBlockTranslationFactory(
            stage_template_block=stb_2, language=hand.language, frontend=hand.frontend, content=""
        )

        translation_2.content = """
<div id='q2'>
This is the 2nd hand var: {free_money}.
This is the 2nd team var: {team_type}.
This is the 2nd module var: {module_type}.
</div>
"""
        translation_2.save()

    def test_variables_via_react_context(self):
        hand = self.hands[0]
        self.driver_1.get(f'{self.live_server_url}/lab/{self.lab.secret}/1')
        time.sleep(2)
        questions_1 = WebDriverWait(self.driver_1, 10).until(EC.presence_of_element_located((By.ID, 'q1')))
        block_text = questions_1.get_attribute('innerHTML')
        hand_var = hand.variables.get(variable_definition=self.module1_hand_vardef)
        team_var = hand.current_team.variables.get(variable_definition=self.module1_team_vardef)
        module_var = hand.current_module.variables.get(variable_definition=self.module1_module_vardef)

        self.assertIn(f'This is the 1st hand var: {hand_var.value}', block_text)
        self.assertIn(f'This is the 1st team var: {team_var.value}', block_text)
        self.assertIn(f'This is the 1st module var: {module_var.value}', block_text)
