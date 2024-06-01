"""Test Javascript gRPC interface"""
import time

from django.conf import settings
from django.core.cache import cache

import grpc

from ery_backend.base.cache import get_func_cache_key_for_hand
from .grpc.engine_pb2 import Javascript, Result, Stint, Stage, Era, Variable, Value, Struct, ListValue, Context, JavascriptOp

from .grpc.engine_pb2_grpc import JavascriptEngineStub


def _generate_value(value):
    # For declaring attribute of gRPC Value to set
    value_map = {
        bool: 'bool_value',
        int: 'number_value',
        float: 'number_value',
        str: 'string_value',
        list: 'list_value',
        dict: 'struct_value',
    }

    if isinstance(value, list):  # pylint:disable=no-else-return
        list_value = ListValue()
        list_value.values.extend([_generate_value(sub_value) for sub_value in value])
        return Value(list_value=list_value)

    elif isinstance(value, dict):
        struct_value = Struct()
        for k, v in value.items():
            value_type = type(v)
            # Assigning submessage (which is in this case dynamic) requires referencing an undefined key (k)
            # (see https://developers.google.com/protocol-buffers/docs/reference/python-generated)
            setattr(struct_value.fields[k], value_map[value_type], v)
        return Value(struct_value=struct_value)
    return Value(**{value_map[type(value)]: value})


def interpret_backend_variable(variable):
    """Returns a proto Variable message from passed ery_backend Variable instance."""
    converted_variable = Variable(
        variable_definition_id=variable.variable_definition.id, value=_generate_value(variable.value)
    )
    return converted_variable


def make_javascript_op(name, code, hand, context=None):
    """
    Returns a protobuf JavascriptOP from code, including gRPC Context from
    :class:`~ery_backend.hands.models.Hand` instance.

    Args:
        - code (str): To be evaluated in EryEngine.
        - backend_hand (:class:`~ery_backend.hands.models.Hand`): Provides context to EryEngine.
        - appends (Dict[str, Union(obj, Dict, List)]): Added to context using str as key and contents of value \
            as protobuf Variable.
    """
    javascript = Javascript(name=name, version=str(time.time()), code=code)
    if not context:
        context = hand.stint.get_context(hand)
    stint = Stint(name=context['stint'])
    stage = Stage(name=hand.stage.stage_definition.name)
    era = Era(name=hand.era.name)
    formatted_variables = {}
    for variable_name, variable in context["variables"].items():
        if variable:  # Team scope may be empty
            variable_definition_id, value = variable
            if value is not None:
                converted_variable = Variable(variable_definition_id=variable_definition_id, value=_generate_value(value))
                formatted_variables[variable_name] = converted_variable
    ctx = Context(stint=stint, era=era, stage=stage, variables=formatted_variables)
    return JavascriptOp(script=javascript, context=ctx)


def _interpret_result_value(value):
    """Reads gRPC Result Value and returns corresponding python type."""
    kind = value.WhichOneof("kind")
    if kind == "bool_value":
        return value.bool_value
    if kind == "number_value":
        return value.number_value
    if kind == "string_value":
        return value.string_value
    if kind == "list_value":
        return [_interpret_result_value(element) for element in value.list_value.values]
    if kind == "struct_value":
        return {name: _interpret_result_value(element) for name, element in value.struct_value.fields.items()}
    return value


def _run_javascript_op(javascript_op):
    channel = grpc.insecure_channel(settings.ERY_ENGINE_HOSTPORT)
    engine = JavascriptEngineStub(channel)
    result = engine.Run(javascript_op)
    return result


def _evaluate(name, hand, code, cached, extra_variables=None):
    """
    extra_variables should be a list of dictionaries.
    """
    from ery_backend.procedures.utils import get_procedure_functions

    result = None
    context = hand.stint.get_context(hand)
    if extra_variables:
        for variable_name, variable_value in extra_variables.items():
            # extra variables are not tied to a VariableDefinition, and thus have no corresponding id.
            context['variables'][variable_name] = (None, variable_value)

    functions_code = get_procedure_functions(
        hand.current_module.stint_definition_module_definition.module_definition, target='engine'
    )
    if functions_code:
        code = f"{functions_code}\n{code}"

    if cached:
        cache_key = get_func_cache_key_for_hand(code, hand, context)
        serialized_result = cache.get(cache_key)
        if not serialized_result is None:
            result = Result.FromString(serialized_result)

    if result is None:
        javascript_op = make_javascript_op(name, code, hand, context)
        result = _run_javascript_op(javascript_op)
        if cached:
            cache.set(cache_key, result.SerializeToString())

    return result


def evaluate_without_side_effects(name, code, hand, cached=True, extra_variables=None):
    """Connect to gRPC server and run supplied javascript, returning error message or evaluated value."""
    result = _evaluate(name, hand, code, cached, extra_variables)
    return _interpret_result_value(result.value)


def evaluate(name, hand, code, cached=True, extra_variables=None):
    """
        Connect to gRPC server and run supplied javascript, returning error message or evaluated value.

        If the value of a Variable is manipulated by the code. The corresponding variable
        (~ery_backend.variables.models.Variable) is updated.
    """
    # XXX: Address in issue #492
    # from ery_backend.variables.models import VariableDefinition
    result = _evaluate(name, hand, code, cached, extra_variables)
    # for _, variable in result.state.variables.items():
    #     variable_definition_id = variable.variable_definition_id
    #         value = _interpret_result_value(variable.value)
    #         variable_definition = VariableDefinition.objects.get(id=variable_definition_id)
    #         hand.stint.set_variable(variable_definition, value, hand=hand)

    return _interpret_result_value(result.value)
