{% from "import_widgets.js" import import_template_widgets, import_module_widgets, import_forms -%}

{% if not is_preview %}
import React, { useContext } from 'react';
import { ThemeProvider, withTheme, createMuiTheme, responsiveFontSizes } from '@material-ui/core/styles';
{{ import_module_widgets(module_widgets) }}

import { BlockContext } from '../App';
{{ import_forms(forms) }}
{% endif %}

const Stage{% if not is_preview %}{{module_definition.name}}{% endif %}{{stage_definition.name}} = withTheme(props => {
{% for block_name, info in blocks.items() %}
    const {{block_name}} = props => {
      const BlockComponent = props => {
  {% if info['block_type'] == 'TemplateBlock' %}
    {% if is_preview %}
      {% for template_widget in info['ancestor'].template_widgets.all() %}
        {% with template_widget=template_widget, is_preview=True %}
          {% include 'TemplateWidget.js' %}
        {% endwith %}
      {% endfor %}
    {% else %}
      {{ import_template_widgets(info['ancestor'].template_widgets.all()) }}
    {%- endif %}
  {%- elif info['block_type'] == 'StageTemplateBlock' -%}
    {% if is_preview %}
      {% for module_widget in info['ancestor'].module_widgets.all() %}
        {% with module_widget=module_widget, is_preview=True %}
          {% include 'ModuleWidget.js' %}
        {% endwith %}
      {% endfor %}
    {% else %}
      {% for module_widget in info['ancestor'].module_widgets.all() %}
        const {{module_widget.name}} = Imported{{module_widget.name}};
      {% endfor %}
    {%- endif %}
    const variables = {% if is_preview %}{}{% else %}useContext(BlockContext){% endif %};
  {%- endif %}

  {% if info['block_type'] == 'StageTemplateBlock' -%}
    {%- for variable in variables -%}
        const {{variable}} = variables["{{variable}}"];
    {%- endfor -%}
  {%- endif -%}
      return (
          <React.Fragment>
            {{info['content'].replace('\t', '  ')|indent|safe if info['content'] is not none else ""}}
          </React.Fragment>
        );
      };
    return <BlockComponent {...props} />;
  };
{% endfor %}

  return (
    <ThemeProvider
      theme={responsiveFontSizes(createMuiTheme({{theme|indent(6)|safe}}))}
    >
      <{{root_block_name}} />
    </ThemeProvider>
  );
});

{% if not is_preview %}
export default Stage{{module_definition.name}}{{stage_definition.name}};
{% endif %}
