from .models import Frontend


def render_sms(hand):
    """
    Render message to SMS :class:`~ery_backend.users.models.User` based on current
    :class:`~ery_backend.stages.models.Stage`

    Args:
        phone_number (str): Used to locate SMS :class:`~ery_backend.users.models.User`.

    Returns:
        str
    """
    sms_frontend = Frontend.objects.get(name='SMS')
    if not hand.frontend == sms_frontend:
        hand.frontend = sms_frontend
        hand.save()
    # render stage with sms frontend
    stage_text = hand.stage.render(hand)
    hand.update_last_seen()

    return stage_text


# issue, keeping track of widgetchoiceitem values on sms reply/
# i have caption and enumeration, but I don't have randomization order, which should be set per choice on render.
