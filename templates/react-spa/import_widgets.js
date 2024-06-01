{% macro get_file_name(widget) -%}
{{widget.slug.capitalize().replace('-', '_')}}
{%- endmacro %}

{%- macro import_widget_dependencies(dependencies) %}
  {%- for dependency in dependencies %}
import {{dependency.name}} from '../Widget/{{get_file_name(dependency.target)}}';
  {%- endfor %}
{% endmacro %}

{% macro import_widget(widget) %}
import {{widget.name}} from '../Widget/{{get_file_name(widget)}}';
{% endmacro %}

{%- macro import_widgets(widgets) -%}
  {%- for widget in widgets %}
{{ import_widget(widget) }}
  {%- endfor %}
{%- endmacro -%}

{%- macro import_template_widgets(template_widgets) -%}
  {%- for template_widget in template_widgets %}
const {{template_widget.name}} = React.lazy(() => import('../TemplateWidget/{{get_file_name(template_widget.template)}}_{{template_widget.name}}'));
  {%- endfor %}
{%- endmacro -%}

// Needs context for server and stage_id
{%- macro import_module_widgets(module_widgets) %}
  {%- for module_widget in module_widgets %}
  import Imported{{module_widget.name}} from '../ModuleWidget/{{get_file_name(module_widget.module_definition)}}_{{module_widget.name}}';
  {%- endfor %}
{% endmacro %}

{% macro import_forms(forms) %}
{% for form in forms %}
const {{form.name}} = React.lazy(() => import('../Form/{{get_file_name(form.module_definition)}}_{{form.name}}'));
{% endfor %}
{% endmacro %}
