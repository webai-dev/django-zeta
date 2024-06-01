{%- from "import_widgets.js" import import_widget_dependencies -%}
{%- from "utils.js" import capitalize_first, camelcase -%}
import { geolocated } from "react-geolocated";

{% if not is_preview -%}
{{ import_widget_dependencies(dependencies) }}
import React, { useContext, useState } from 'react';
import { AppContext } from '../App';

  {% if widget.external %}
import External{{widget.name}} from '{{widget.address}}';
const External = { {{widget.name}}: External{{widget.name}} };
  {% endif -%}
{%- endif %}

{% set parameters_str = widget.parameters|join(', ') %}


const {{widget.name}} = (props, ref) => {
  {%- for prop in widget.props.all() %}
      {% set default_prop_value = prop.default_value or none %}
  const {{ prop.name }} = props.{{prop.name}} {% if default_prop_value %} || {{prop.json_default_value|safe}}{% endif %};
    {%- endfor %}
      const children = props.children;
{% if is_preview %}
  {% for connection in widget.connections.all() %}
    {% with widget=connection.target, is_preview=True %}
      {% include 'Widget.js' %}
    {% endwith %}
  {% endfor %}
{% else %}
  {% if require_communicate %}
  const {triggerWidgetEvent} = useContext(AppContext);
  {% endif %}
{% endif %}
{% for state in widget.states.all() -%}
  {%- set initial_state = state.default_value or none %}
  const [{{state.name}}, set{{capitalize_first(state.name)}}] = useState(
    {{state.default_value|safe if state.from_prop else state.json_default_value|safe }});
{% endfor %}
let choices = props.choices;
if (choices){
  choices = JSON.parse(choices);
}
{% for user_prefix, event_type, do_communicate, code_steps in widget.get_events_info() -%}
  {%- set prefix = user_prefix or "" -%}
  {# the event triggering action performed client-side #}
  {%- set js_event = event_type|replace("on", "") -%}
  {%- set react_event = camelcase(prefix, js_event) -%}
  {# how the user refers to current event #}
  {%- set event_name = camelcase(prefix, event_type) -%}
    const handle{{capitalize_first(react_event)}} = ({{parameters_str}} ) => {
  {% for code_step_order, code_step_code in code_steps -%}
      const handle{{capitalize_first(react_event)}}{{code_step_order}} = ({{parameters_str}}) => {
        {{code_step_code|safe}}
      };
      handle{{capitalize_first(react_event)}}{{code_step_order}}({{parameters_str}});
  {%- endfor %}
  {% if do_communicate %}
      {% if not is_preview %}
    triggerWidgetEvent(props.gqlId, "{{user_prefix}}"||null, "{{event_type}}", {{widget.value_parameter}});
      {% endif %}
  {% endif %}
  {#- for separation from paired listener-handler below #}
  if (props.{{event_name}}){
    props.{{event_name}}({{parameters_str}});
  }
};
{%- endfor %}

{%- if widget.external %}
    return (
      <External{{widget.name}}
  {% for user_prefix, event_type, _, _ in widget.get_events_info() -%}
    {%- set prefix = user_prefix or "" -%}
    {%- set js_event = event_type|replace("on", "") -%}
    {%- set react_event = camelcase(prefix, js_event) -%}
    {%- set event_name = camelcase(prefix, event_type) -%}
        {{event_name}}={ handle{{capitalize_first(react_event)}}}
  {%- endfor %}
        {...props}
  {% for prop in widget.props.all() -%}
        {{prop.name}}={ {{prop.name}} }
  {%- endfor %}
      >
        {children || null}
      </External{{widget.name}}>
    );
{% else %}
    return (
      <React.Fragment>
        {{widget.code|indent(6)|safe}}
      </React.Fragment>
    );
{% endif %}
  };

{% if not is_preview %}
export default React.forwardRef({{widget.name}});
{% endif %}
