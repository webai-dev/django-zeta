from ery_backend.frontends.models import Frontend
from ery_backend.labs.models import Lab
from ery_backend.modules.models import ModuleDefinition
from ery_backend.procedures.models import Procedure
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.stints.models import StintDefinition
from ery_backend.syncs.models import Era
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from ery_backend.validators.models import Validator
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.models import Widget

for model in [
    Frontend,
    Lab,
    ModuleDefinition,
    Procedure,
    StintSpecification,
    StintDefinition,
    Era,
    Template,
    Theme,
    Validator,
    VariableDefinition,
    Widget,
]:
    for instance in model.objects.all():
        if not instance.slug:
            instance.save()
