import factory


class RoleAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'roles.RoleAssignment'


class PrivilegeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'roles.Privilege'

    name = factory.Sequence('privilege-{}'.format)


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'roles.Role'

    name = factory.Sequence('role-{}'.format)


class RoleParentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'roles.RoleParent'

    role = factory.SubFactory('ery_backend.roles.factories.RoleFactory')
    parent = factory.SubFactory('ery_backend.roles.factories.RoleFactory')
