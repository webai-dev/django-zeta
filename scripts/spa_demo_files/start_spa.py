from ery_backend.labs.models import Lab
from ery_backend.stints.models import StintDefinition
from ery_backend.users.models import User


def start(test_count):
    user = User.objects.get(username='admin')
    Lab.objects.filter(secret='test').all().delete()
    lab = Lab.objects.get_or_create(secret='test', name='spa', slug=Lab.create_unique_slug('spa'))[0]
    stint_definition = StintDefinition.objects.get(name='RenderTest')
    stint_specification = stint_definition.specifications.first()
    lab.set_stint(stint_specification.id, user)
    lab.start(test_count, user)
