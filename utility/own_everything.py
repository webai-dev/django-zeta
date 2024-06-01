#! /usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys

from django.core.wsgi import get_wsgi_application
from django.contrib.auth import get_user_model

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(base_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.backend.local")
application = get_wsgi_application()

# pylint: disable=wrong-import-position
from ery_backend.datasets.models import Dataset
from ery_backend.folders.models import Folder
from ery_backend.modules.models import ModuleDefinition
from ery_backend.roles.models import Role
from ery_backend.roles.utils import grant_role
from ery_backend.stints.models import StintDefinition
from ery_backend.templates.models import Template
from ery_backend.widgets.models import Widget

User = get_user_model()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Given user will own all the things")
    ap.add_argument("username", type=str, help="Username")
    ap.add_argument("--password", type=str, help="Set password")
    args = ap.parse_args()

    try:
        user = User.objects.get(username=args.username)
    except User.DoesNotExist as err:
        user = User(username=args.username)

    if args.password is not None:
        user.set_password(args.password)

    user.save()

    ownership = Role.objects.get(name="owner")

    for md in ModuleDefinition.objects.all():
        grant_role(ownership, md, user)

    for s in StintDefinition.objects.all():
        grant_role(ownership, s, user)

    for f in Folder.objects.all():
        grant_role(ownership, f, user)

    for w in Widget.objects.all():
        grant_role(ownership, w, user)

    for ds in Dataset.objects.all():
        grant_role(ownership, ds, user)

    for t in Template.objects.all():
        grant_role(ownership, t, user)
