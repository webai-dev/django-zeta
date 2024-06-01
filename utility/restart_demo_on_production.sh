#!/bin/bash

TEST_COUNT=32

NAMESPACE=production make k8s-shell <<EOF
from ery_backend.labs.models import Lab
from ery_backend.users.models import User
from ery_backend.stints.models import StintDefinition

user = User.objects.get(username='admin')
lab = Lab.objects.get_or_create(secret='dnm', name='dnmlab')[0]
stint_definition = StintDefinition.objects.get(name='DescriptiveNormMessaging')
stint_specification = stint_definition.specifications.first()
lab.set_stint(stint_specification.id, user)

lab.start($TEST_COUNT, user)
EOF
