#! /usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from functools import reduce

from django.core.wsgi import get_wsgi_application

import ery_backend  # pylint:disable=unused-import
from ery_backend.base.serializers import EryXMLRenderer


base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(base_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.backend.local")
application = get_wsgi_application()


def str_to_class(classname):
    """
    Given the name of a desired class, return the class constructor if possible
    """
    return reduce(getattr, classname.split("."), sys.modules[__name__])


def render_xml(item, name):
    """
    Given a seriazable object, return the XML rendering
    """
    renderer = EryXMLRenderer()
    renderer.root_tag_name = name

    xml = renderer.render(item.serialize(), "application/bry+xml").decode("utf-8")
    return xml


def uncamel(text):
    """
    Convert CamelCase text to lower_with_underscore
    """
    end = len(text)

    if end < 2:
        return text.lower()

    rsf = ""
    i = 1

    while i < end:
        g = i - 2
        h = i - 1

        if text[h].islower() and text[i].isupper():
            rsf += text[h] + "_"
        elif i > 1 and text[g].isupper() and text[h].isupper() and text[i].islower():
            rsf += "_" + text[h].lower()
        else:
            rsf += text[h].lower()

        i += 1

    rsf += text[-1].lower()
    return rsf


if __name__ == "__main__":
    ap = argparse.ArgumentParser("Serialize a given object and pk")
    ap.add_argument(
        "class_name",
        type=str,
        help="Class of an ery model. Expect full, dot-separated class, such as"
        + "ery.backend.modules.models.ModuleDefinition",
    )

    ap.add_argument("--name", type=str, help="ID the object by name")
    ap.add_argument("--pk", type=str, help="ID the object by primary key")
    args = ap.parse_args()

    Object = str_to_class(args.class_name)

    filters = {}

    if args.name is not None:
        filters["name"] = args.name

    if args.pk is not None:
        filters["pk"] = int(args.pk)

    try:
        obj = Object.objects.get(**filters)
    except Object.DoesNotExist:
        cls = args.class_name
        sys.exit(f"That {cls} does not exist")

    root_name = uncamel(args.class_name.split(".")[-1])
    print(render_xml(obj, root_name))
