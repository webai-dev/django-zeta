{%- from "import_widgets.js" import import_widget -%}

{% if not is_preview %}
import React from 'react';

{{ import_widget(template_widget.widget) }}
{% endif %}

const {% if not is_preview %}Template{% endif %}{{template_widget.name}} = props => {
  {% if is_preview %}
    {% with widget=template_widget.widget, parameter_str=', '.join(template_widget.widget.parameters), is_preview=True %}
      {% include 'Widget.js' %}
    {% endwith %}
  {% endif %}

  return (
    <{{template_widget.widget.name}}
{%- if template_widget.widget.initial_value %}
      default_value={{template_widget.widget.initial_value}}
{% endif %}
      gqlId="{{template_widget.gql_id}}"
      children={props.children}
      {...props}
    />
  );
};

{% if not is_preview %}
export default Template{{ template_widget.name }};
{% endif %}
