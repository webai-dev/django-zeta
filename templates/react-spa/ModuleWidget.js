{% from "import_widgets.js" import import_widget -%}
{% from "utils.js" import camelcase -%}

{% macro capitalize_first(str) -%}
  {{str[0]|upper}}{{str[1:]}}
{%- endmacro -%}

{% if not is_preview %}
import React, { useContext } from 'react';

import { AppContext, ModuleContext } from '../App';

{{ import_widget(module_widget.widget) }}
{% endif %}

{% set widget = module_widget.widget %}
{% set parameters_str = widget.parameters|join(', ') %}
{%- set value = widget.value_parameter  -%}
{% if choices %}
const choices = {{choices|safe}};
{% endif %}

const {% if not is_preview %}Module{% endif %}{{module_widget.name}} = props => {
{% if is_preview %}
  {% with widget=module_widget.widget, parameter_str=', '.join(module_widget.widget.parameters), is_preview=True %}
    {% include 'Widget.js' %}
  {% endwith %}
{% else %}
  const { stageID } = useContext(ModuleContext);
  {% if require_communicate %}
  const {triggerWidgetEvent} = useContext(AppContext);
  {% endif %}
{% endif %}
{% for user_prefix, event_type, do_communicate in module_widget.get_events_info() %}
  {%- set prefix = user_prefix or "" -%}
  {%- set js_event = event_type|replace("on", "") %}
  const handle{{capitalize_first(camelcase(prefix, js_event))}} = ({{parameters_str}}) => {
  {% if do_communicate %}
    triggerWidgetEvent("{{module_widget.gql_id}}", "{{user_prefix}}"||null, "{{event_type}}", {{widget.value_parameter}});
  {% endif %}
  };
{% endfor %}
{% if validations %}
  const validate = (value) => {
  {% for validator, error_message in validations %}
    if (
    {% if validator.regex %}
      {{validator.regex}}.test(value) === false
    {% else %}
      ((value) => { {{validator.code}} })() === false
    {% endif %}
    ) {
      return {{error_message}};
    }
  {% endfor %}
  };
{% endif %}

  return (
    <{{widget.name}}
{%- set initial_value = module_widget.initial_value or none %}
{% if initial_value is not none -%}
      defaultValue = {% if initial_value == '' -%}
      '' {%- else -%}{ {{module_widget.json_initial_value|safe }} } {%- endif %}
{%- endif %}
{% if validations -%}
      validate={validate}
{% endif %}
{% for user_prefix, event_type, _ in module_widget.get_events_info() -%}
  {%- set prefix = user_prefix or "" -%}
  {%- set js_event = event_type|replace("on", "") -%}
      on{{capitalize_first(camelcase(prefix, js_event))}}={handle{{capitalize_first(camelcase(prefix, js_event))}}}
{%- endfor %}
      gqlId="{{module_widget.gql_id}}"
      children={props.children}
  {% if choices -%}choices={JSON.stringify(choices)} {%- endif %}
      {...props}
    />
  );
};


{% if not is_preview %}
  {% if choices -%}
    Module{{ module_widget.name }}.choices = {{choices|safe}};
  {%- endif %}
export default Module{{ module_widget.name }};
{% endif %}
