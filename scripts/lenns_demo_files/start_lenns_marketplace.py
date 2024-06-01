from ery_backend.base.utils import get_gql_id
from ery_backend.stints.models import StintDefinition
from ery_backend.users.models import User


def start():
    user = User.objects.get(username='admin')
    stint_definition = StintDefinition.objects.filter(name='DescriptiveNormMessaging').last()
    stint_specification = stint_definition.specifications.first()
    stint = stint_definition.realize(stint_specification)
    stint.start(user)
    print(f"Access suffix is {get_gql_id('UserNode', user.id)}")
