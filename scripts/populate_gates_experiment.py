import random
import time

from ery_backend.frontends.sms_utils import opt_in
from ery_backend.hands.models import Hand
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.variables.models import HandVariable


def populate_gates():
    sender = str(random.randint(1111111111, 9999999999))
    stint_specification = StintSpecification.objects.get(name='TestGates')
    opt_in(stint_specification.opt_in_code, sender)
    time.sleep(5)  # Allows for creation of vars
    hand_vars = {}
    hand_vars['other_ne_response'] = 10
    hand_vars['other_willingness_response'] = 1
    hand_vars['str_pw_response'] = 'no'
    hand_vars['str_ne_response'] = random.choice(['no', 'yes'])

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
        found_var.value = value
        found_var.save()


def run():
    populate_gates()
