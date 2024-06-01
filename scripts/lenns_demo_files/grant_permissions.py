from ery_backend.folders.models import Link
from ery_backend.labs.models import Lab
from ery_backend.roles.utils import grant_ownership
from ery_backend.stints.models import StintDefinition
from ery_backend.users.models import User

lab = Lab.objects.get_or_create(name='DNMLab', secret='dnm')[0]
sd = StintDefinition.objects.get(name='DescriptiveNormMessaging')


print('Running script')
for user in User.objects.all():
    print(f'Granting ownership of lab to {user.username}')
    grant_ownership(lab, user)
    if user.my_folder:
        print(f'Add link (if needed) to stint_definition and grant ownership')
        Link.objects.get_or_create(stint_definition=sd, parent_folder=user.my_folder)
        grant_ownership(sd, user)
print('Script completed')
