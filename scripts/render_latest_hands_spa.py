import os

from ery_backend.frontends.renderers import ReactStintRenderer
from ery_backend.hands.models import Hand

spa_dir = "react-spa/es6"


def run():
    h = Hand.objects.last()
    r = ReactStintRenderer(h.stint_definition, h.language)

    for subdirectory in ("Module", "Stage", "Templates", "ModuleWidget", "TemplateWidget", "Widget", "Form"):
        directory = f"{spa_dir}/{subdirectory}"
        if not os.path.exists(directory):
            os.makedirs(directory)

    es6_files = r.render(raw=True)
    for filename, content in es6_files.items():
        with open(f"{spa_dir}/{filename}", "w") as text_file:
            text_file.write(content)
