from ery_backend.labs.models import Lab
from ery_backend.roles.models import Role
from ery_backend.roles.utils import grant_role
from ery_backend.stints.models import StintDefinition
from ery_backend.users.models import User


def start(test_count):
    user = User.objects.get(username='admin')
    lab = Lab.objects.get_or_create(secret='dnm', name='dnmlab')[0]
    stint_definition = StintDefinition.objects.filter(name='DescriptiveNormMessaging').last()
    stint_specification = stint_definition.specifications.first()
    lab.set_stint(stint_specification.id, user)
    lab.start(test_count, user)

    for user in User.objects.filter(is_creator=True):
        grant_role(Role.objects.get(name="administrator"), lab, user)
        grant_role(Role.objects.get(name="administrator"), lab.current_stint, user)
