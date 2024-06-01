import logging

import grpc

from .grpc.ledger_pb2 import Peer, Transferal, StintInfo, Payment
from .grpc.ledger_pb2_grpc import LedgerStub

logger = logging.getLogger(__name__)


def _make_peer(user):
    return Peer(id=user.id, name=user.username)


def _make_transferal(amount, creditor, debitor, stint):
    creditor = _make_peer(creditor)
    debitor = _make_peer(debitor)
    description = f"Payment for {stint}."
    return Transferal(creditor=creditor, debitor=debitor, amount=amount, fee=0, description=description)


def _make_stint_info(hand, action_step=None):
    kwargs = {
        'stint_specification_id': hand.stint.stint_specification.id,
        'stint_id': hand.stint.id,
        'module_id': hand.current_module.id,
        'hand_id': hand.id,
    }
    if action_step:
        kwargs.update({'action_id': action_step.action.id, 'action_step_id': action_step.id})

    return StintInfo(**kwargs)


def _make_payment(amount, hand, action_step=None):
    transferal = _make_transferal(amount, hand.user, hand.stint.started_by, hand.stint)
    stint_info = _make_stint_info(hand, action_step)
    immediate_payment_method = getattr(Payment, hand.stint.stint_specification.immediate_payment_method)
    return Payment(transfer=transferal, stint=stint_info, immediate_payment_method=immediate_payment_method)


def send_payment(amount, hand, action_step=None):
    """
    Use EryLedger to distribute payment from debitor to creditor.
    """
    channel = grpc.insecure_channel('localhost:30002')
    try:
        ledger = LedgerStub(channel)
        payment = _make_payment(amount, hand, action_step)
        ledger.Pay(payment)

    except grpc.RpcError as exc:
        logger.error(exc)
