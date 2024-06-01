from ery_backend.base.cache import ery_cache


@ery_cache
# XXX: Needs to be invalidated on module_definition or procedure change
def get_procedure_functions(module_definition, target):
    module_definition_procedures = module_definition.moduledefinitionprocedure_set
    procedures = sorted(
        [
            alias.procedure
            for alias in module_definition_procedures.order_by('procedure').distinct('procedure').select_related('procedure')
        ],
        key=lambda alias: alias.name,
    )
    function_names = {procedure.slug: procedure.js_name for procedure in procedures}

    procedure_definitions = '\n'.join(
        [f"{function_names[procedure.slug]} = {procedure.generate_js_function(target)}" for procedure in procedures]
    )

    alias_assignments = '\n'.join(
        [f"var {alias.name} = {function_names[alias.procedure.slug]};" for alias in module_definition_procedures.all()]
    )

    return f'{procedure_definitions}\n{alias_assignments}' if procedure_definitions else ''
