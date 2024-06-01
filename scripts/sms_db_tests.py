import time

from languages_plus.models import Language
import requests

from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import create_test_stintdefinition
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.hands.models import Hand
from ery_backend.modules.factories import (
    ModuleEventFactory,
    ModuleDefinitionWidgetFactory,
    WidgetChoiceFactory,
    WidgetChoiceTranslationFactory,
)
from ery_backend.modules.models import ModuleEvent
from ery_backend.stages.factories import StageTemplateBlockFactory, StageTemplateBlockTranslationFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.syncs.factories import EraFactory
from ery_backend.templates.factories import TemplateWidgetFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition, TeamVariable
from ery_backend.widgets.models import Widget


def test_update_stage():
    """
    Confirm advancement (from server) of hand's stage leads to change in client react content.
    """
    sms = Frontend.objects.get(name='SMS')
    stint_definition = create_test_stintdefinition(frontend=sms, stage_n=2)
    stint_specification = StintSpecificationFactory(
        stint_definition=stint_definition, language=Language.objects.get(pk='en'), opt_in_code='TestUpdateStage'
    )
    stage_one = stint_definition.stint_definition_module_definitions.first().module_definition.start_stage
    stage_two = (
        stint_definition.stint_definition_module_definitions.first()
        .module_definition.stage_definitions.exclude(id=stage_one.id)
        .first()
    )
    stage_one.next_stage = stage_two
    stage_one.save()
    stage_template_one = stage_one.stage_templates.get(template__frontend=sms)
    root_block_one = stage_template_one.get_root_block()
    root_translation_one = root_block_one.translations.first()
    next_widget = Widget.objects.get(slug='SMSNextButton-sGuVqQCu')
    TemplateWidgetFactory(widget=next_widget, template=root_block_one.template, name='NextButton')
    root_translation_one.content = "Say something I'm giving up on yoooouuuuuu\n<Widget.NextButton/>"
    root_translation_one.save()

    sender = '1112223333'
    to = 'a'
    date = '2016-01-01'
    message = f'{stint_specification.opt_in_code}'
    url = f"http://localhost:30036/smser?to={to}&from=%2B{sender}&date={date}%2012%3A00%3A00&msg={message}"
    requests.post(url)
    time.sleep(5)
    hand = Hand.objects.get(user__username='__phone_no__+1112223333')
    assert hand.stage.stage_definition == stage_one

    message = "But you said we'd be FOREVER, Pierre Jean Paul!!!"
    url = f"http://localhost:30036/smser?to={to}&from=%2B{sender}&date={date}%2012%3A00%3A00&msg={message}"
    requests.post(url)

    time.sleep(5)
    hand.refresh_from_db()
    stint_definition.delete()
    assert hand.stage.stage_definition == stage_two


def test_set_var():
    """
    Confirm change in hand's variable value via WidgetEvent.
    """
    sms = Frontend.objects.get(name='SMS')
    stint_definition = create_test_stintdefinition(frontend=sms, stage_n=2)
    stint_specification = StintSpecificationFactory(
        stint_definition=stint_definition, language=Language.objects.get(pk='en'), opt_in_code='TestSetVar'
    )
    stintdef_moduledef_one = stint_definition.stint_definition_module_definitions.first()
    stage_one = stintdef_moduledef_one.module_definition.start_stage
    stage_two = stintdef_moduledef_one.module_definition.stage_definitions.exclude(id=stage_one.id).first()
    stage_one.next_stage = stage_two
    stage_one.save()
    stage_template_one = stage_one.stage_templates.get(template__frontend=sms)
    st_block = StageTemplateBlockFactory(stage_template=stage_template_one)
    StageTemplateBlockTranslationFactory(stage_template_block=st_block, content="<Widget.SayHoPlease/>")
    root_block_one = stage_template_one.get_root_block()
    root_translation_one = root_block_one.translations.first()
    next_widget = Widget.objects.get(slug='SMSNextButton-sGuVqQCu')
    TemplateWidgetFactory(widget=next_widget, template=root_block_one.template, name='NextButton')
    choice_widget = Widget.objects.get(slug='smsmultiplechoicecaptionvaluewidget-ujIkXxBK')
    variable_definition = VariableDefinitionFactory(
        module_definition=stage_one.module_definition,
        data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
        scope=VariableDefinition.SCOPE_CHOICES.hand,
        validator=None,
    )
    md_widget = ModuleDefinitionWidgetFactory(
        widget=choice_widget,
        module_definition=stage_one.module_definition,
        name='SayHoPlease',
        variable_definition=variable_definition,
    )
    only_choice = WidgetChoiceFactory(widget=md_widget, value="Ho")
    WidgetChoiceTranslationFactory(widget_choice=only_choice, language=get_default_language(), caption="Ho")
    ModuleEventFactory(
        event=ModuleEvent.EVENT_CHOICES.onReply, event_type=ModuleEvent.EVENT_TYPE_CHOICES.save_var, widget=md_widget
    )
    root_translation_one.content = f"When I say HAAAAAY, you say ...\n<{st_block.name}/><Widget.NextButton/>"
    root_translation_one.save()

    sender = '1112223333'
    to = 'a'
    date = '2016-01-01'
    message = f'{stint_specification.opt_in_code}'
    url = f"http://localhost:30036/smser?to={to}&from=%2B{sender}&date={date}%2012%3A00%3A00&msg={message}"
    requests.post(url)
    time.sleep(5)
    hand = Hand.objects.get(user__username='__phone_no__+1112223333')
    message = "Ho"
    assert hand.variables.first().value != message

    url = f"http://localhost:30036/smser?to={to}&from=%2B{sender}&date={date}%2012%3A00%3A00&msg={message}"
    requests.post(url)

    time.sleep(5)
    hand.refresh_from_db()
    assert hand.variables.first().value == message
    stint_definition.delete()


def test_update_era():
    """
    Confirm change in hand's era via WidgetEvent.
    """
    sms = Frontend.objects.get(name='SMS')
    stint_definition = create_test_stintdefinition(frontend=sms, stage_n=2)
    stint_specification = StintSpecificationFactory(
        stint_definition=stint_definition, language=Language.objects.get(pk='en'), opt_in_code='TestAction'
    )
    stintdef_moduledef_one = stint_definition.stint_definition_module_definitions.first()
    stage_one = stintdef_moduledef_one.module_definition.start_stage
    stage_two = stintdef_moduledef_one.module_definition.stage_definitions.exclude(id=stage_one.id).first()
    stage_one.next_stage = stage_two
    stage_one.save()
    stage_template_one = stage_one.stage_templates.get(template__frontend=sms)
    st_block = StageTemplateBlockFactory(stage_template=stage_template_one)
    StageTemplateBlockTranslationFactory(stage_template_block=st_block, content="<Widget.TestAction/>")
    root_block_one = stage_template_one.get_root_block()
    root_translation_one = root_block_one.translations.first()
    widget = Widget.objects.get(slug='smsemptywidget-ujjIkXxBk')
    era = EraFactory(module_definition=stage_one.module_definition)
    action = ActionFactory(module_definition=stage_one.module_definition)
    ActionStepFactory(
        action=action,
        action_type=ActionStep.ACTION_TYPE_CHOICES.set_era,
        era=era,
        condition=None,
        for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
    )

    md_widget = ModuleDefinitionWidgetFactory(widget=widget, module_definition=stage_one.module_definition, name='TestAction')
    ModuleEventFactory(
        event=ModuleEvent.EVENT_CHOICES.onReply,
        event_type=ModuleEvent.EVENT_TYPE_CHOICES.run_action,
        widget=md_widget,
        action=action,
    )
    root_translation_one.content = f"When I say HAAAAAY, you say ...\n<{st_block.name}/>"
    root_translation_one.save()

    sender = '1112223333'
    to = 'a'
    date = '2016-01-01'
    message = f'{stint_specification.opt_in_code}'
    url = f"http://localhost:30036/smser?to={to}&from=%2B{sender}&date={date}%2012%3A00%3A00&msg={message}"
    requests.post(url)
    time.sleep(5)
    hand = Hand.objects.get(user__username='__phone_no__+1112223333')
    message = "Hoooooooooooooooooooo"
    assert hand.era != era

    url = f"http://localhost:30036/smser?to={to}&from=%2B{sender}&date={date}%2012%3A00%3A00&msg={message}"
    requests.post(url)

    time.sleep(5)
    hand.refresh_from_db()
    assert hand.era == era
    stint_definition.delete()


def test_join_users():
    sms = Frontend.objects.get(name='SMS')
    stint_definition = create_test_stintdefinition(frontend=sms, stage_n=2)
    stint_specification = StintSpecificationFactory(
        stint_definition=stint_definition, language=Language.objects.get(pk='en'), opt_in_code='TestJoin', late_arrival=True
    )
    stintdef_moduledef_one = stint_definition.stint_definition_module_definitions.first()
    module_definition_one = stintdef_moduledef_one.module_definition
    crew_depth = VariableDefinitionFactory(
        scope=VariableDefinition.SCOPE_CHOICES.team,
        data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        default_value=0,
        name='hands_n',
        module_definition=module_definition_one,
    )
    stage_one = module_definition_one.start_stage
    stage_template_one = stage_one.stage_templates.get(template__frontend=sms)
    root_block_one = stage_template_one.get_root_block()
    root_translation_1 = root_block_one.translations.first()
    root_translation_1.content = 'Ayo, how DEEP is your crew?<Widget.NextButton/>'
    root_translation_1.save()
    next_widget = Widget.objects.get(slug='SMSNextButton-sGuVqQCu')
    TemplateWidgetFactory(widget=next_widget, template=root_block_one.template, name='NextButton')
    deepen_crew = ActionFactory(module_definition=module_definition_one)
    ActionStepFactory(
        action=deepen_crew,
        for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
        variable_definition=crew_depth,
        value='hands_n + 1',
    )
    stage_two = module_definition_one.stage_definitions.exclude(id=stage_one.id).first()
    stage_two.pre_action = deepen_crew
    stage_two.save()
    stage_one.next_stage = stage_two
    stage_one.save()

    stage_template_two = stage_two.stage_templates.get(template__frontend=sms)
    root_block_two = stage_template_two.get_root_block()
    root_translation_2 = root_block_two.translations.first()
    root_translation_2.content = 'There are {{hands_n}} people in this stint right now.'
    root_translation_2.save()

    sender_one = '1112223333'
    sender_two = '3332221111'
    to = 'a'
    date = '2016-01-01'
    message = f'{stint_specification.opt_in_code}'
    for sender in (sender_one, sender_two):
        url = f"http://localhost:30036/smser?to={to}&from=%2B{sender}&date={date}%2012%3A00%3A00&msg={message}"
        requests.post(url)
        time.sleep(5)

    message = 'How deep is my crew, though???'
    for sender in (sender_one, sender_two):
        url = f"http://localhost:30036/smser?to={to}&from=%2B{sender}&date={date}%2012%3A00%3A00&msg={message}"
        requests.post(url)
        time.sleep(5)  # Allow time for action

    variable = TeamVariable.objects.get(variable_definition__name='hands_n')
    assert variable.value == 2
    stint_definition.delete()


def populate_gates(cond):
    import random
    from ery_backend.stint_specifications.models import StintSpecification
    from ery_backend.frontends.sms_utils import opt_in
    from ery_backend.variables.models import HandVariable

    sender = str(random.randint(1111111111, 9999999999))
    stint_specification = StintSpecification.objects.get(name='TestGates')
    opt_in(stint_specification.opt_in_code, sender)
    time.sleep(5)  # Allows for creation of vars
    hand_vars = {}
    if cond[0] == 'N':
        hand_vars['pb_response'] = 0
    else:
        hand_vars['pb_response'] = 1
    if cond[1] == 'N':
        hand_vars['ps_response'] = 0
    else:
        hand_vars['ps_response'] = 1

    hand = None
    while not hand:
        hand = Hand.objects.filter(user__username__contains=sender).first()
        if not hand:
            time.sleep(1)
    for var, value in hand_vars.items():
        found_var = None
        while not found_var:
            found_var = HandVariable.objects.filter(hand=hand, variable_definition__name=var).first()
            if not found_var:
                time.sleep(1)
        hand.stint.set_variable(found_var.variable_definition, value, hand=hand)


def test_gates():
    from google.cloud import pubsub_v1
    import json
    import environ
    import random
    from ery_backend.base.cache import cache
    from django.utils.crypto import get_random_string

    env = environ.Env()
    deployment = env("DEPLOYMENT", default="local")
    project_name = "eryservices-176219"
    topic_name = f'projects/{project_name}/topics/{deployment}-incoming_sms'
    publisher = pubsub_v1.PublisherClient()
    sender = get_random_string(11)
    msg = {'ID': '1', 'To': '+19163180999', 'Message': 'gates', 'From': sender}
    b = json.dumps(msg)
    start = ['gates']
    pre_messages = []
    for _ in range(2):
        pre_messages.append(random.choice(['Y', 'n']))
    for _ in range(2):
        pre_messages.append(str(random.randint(0, 10)))
    pre_messages.append('y')
    s1_check = lambda num: Hand.objects.filter(user__username__contains=num).exists()

    def s2_check(hand):
        expected_value = 1 if pre_messages[0] == "Y" else 0
        return (hand.variables.get(variable_definition__name='str_pb_response').value == pre_messages[0]) and (
            hand.variables.get(variable_definition__name='pb_response').value == expected_value
        )

    def s3_check(hand):
        expected_value = 1 if pre_messages[1] == "Y" else 0
        return (hand.variables.get(variable_definition__name='str_ps_response').value == pre_messages[1]) and (
            hand.variables.get(variable_definition__name='ps_response').value == expected_value
        )

    def s4_check(hand):
        return hand.variables.get(variable_definition__name='other_pb_response').value == int(pre_messages[2])

    def s5_check(hand):
        return hand.variables.get(variable_definition__name='other_ps_response').value == int(pre_messages[3])

    def s6_check(hand):
        hand.refresh_from_db()
        return hand.stage.stage_definition.name == 'Fin'

    check_functions = [s1_check, s2_check, s3_check, s4_check, s5_check, s6_check]
    counter = 0

    for message in start + pre_messages:
        last_id = cache.get(f"incoming-counter-{sender}")
        last_id = int(last_id) if last_id is not None else 1
        msg['ID'] = last_id + 1
        msg['Message'] = message
        b = json.dumps(msg)
        publisher.publish(topic_name, b.encode('utf-8'))
        check_function = check_functions[counter]
        check = False
        while check is False:
            time.sleep(1)
            if counter == 0:
                check = check_function(sender)
            else:
                check = check_function(hand)
        if counter == 0:
            hand = Hand.objects.get(user__username__contains=sender)
        counter += 1


def run_threaded(n):
    import threading

    threads = []
    for _ in range(100):
        t = threading.Thread(target=test_gates)
        threads.append(t)
        t.start()
    for one_thread in threads:
        one_thread.join()


def run():
    # test_update_stage()
    # test_set_var()
    # test_update_era()
    # test_join_users()
    test_gates()
