{%- from "import_widgets.js" import import_widgets, import_module_widgets, import_template_widgets -%}

import React, { useState, useContext } from 'react';

import { ErrorMessage, Formik, Form, Field } from 'formik';
import Box from '@material-ui/core/Box';
import Grid from '@material-ui/core/Grid';
import { AppContext, BlockContext } from '../App';

{{ import_widgets (form_widgets) }}
{{ import_module_widgets(module_widgets) }}
{% for module_widget in module_widgets -%}
  const {{module_widget.name}} = Imported{{module_widget.name}};
{% endfor %}

{%- for item in form.items.filter(field__isnull=False) %}
  const Field{{item.field.name}} = {
    "name": "{{form.name}}-{{item.order}}-{{item.field.name}}",
    "variableName": "{{item.field.variable_definition.name}}",
    "fieldName": "{{item.field.name}}",
    "initialValue": {{item.field.get_initial_value()|safe}},
    "required": "{{item.field.required}}" === "True",
    "tabIndex": {{item.tab_order}},
    "helperText": "{{item.field.helper_text|safe}}",
    "gqlId": "{{item.field.get_module_widget().gql_id}}",
  {% if item.field.is_multiple_choice -%}
    "choices": JSON.stringify({{item.field.get_choices(language)|safe}}),
  {%- endif %}
  }
{%- endfor %}

{%- for item in form.items.filter(button_list__isnull=False) %}
  {%- for button in item.button_list.buttons.all() %}
  const Button{{button.name}} = {
    "name": "{{button.name}}",
    "gqlId": "{{button.gql_id}}",
    "buttonText": "{{button.button_text|safe}}",
  }
  {%- endfor %}
{%- endfor %}

{% if validations -%}
const validate = {
  values => {
    const errors = {};
  {% for validation in validations %}
    if ((() => {
      {{validation.validator|indent(6)|safe}}
    })() === false) {
      errors[validation.from_field.name] = validation.error_message;
    }
  {% endfor %}
    return errors;
  }
};
{% endif -%}

const {{module_definition.name}}{{form.name}} = props => {
  const variables = useContext(BlockContext);

  const handleSubmit = (values, { setSubmitting }) => {
    setSubmitting(true);
    triggerFormEvent("{{form.gql_id}}", "onSubmit", values);

  };
  const [values, setValues] = useState({})
  const { triggerFormEvent } = useContext(AppContext);

  const initialValues = {};
  {% for item in form.items.filter(field__isnull=False) %}
    {%- set field_obj = "Field" + item.field.name -%}
    initialValues[{{field_obj}}.name] = variables[{{field_obj}}.variableName] != null ? variables[{{field_obj}}.variableName] : {{field_obj}}.initialValue;
  {%- endfor %}
  return (
    <Formik
      initialValues={initialValues}
      onSubmit={handleSubmit}
{% if validations %}
      validate={validate}
      validateOnChange={false}
      validateOnBlur={true}
{% endif %}
      {...props}
    >
      {({ values, isSubmitting}) => (
        <Form>
{%- for item in form.items.all() -%}
  {%- if item.field -%}
    {%- set module_widget_name = item.field.get_module_widget().name -%}
    {%- set field_obj = "Field" + item.field.name -%}
          <Field
            name={ {{field_obj}}.name }
          >
            {({field, meta}) => (
              <{{module_widget_name}}
                id={ {{field_obj}}.name }
                label={ {{field_obj}}.fieldName }
                required={ {{field_obj}}.required }
                tabIndex={ {{field_obj}}.tabIndex }
                helperText={ {{field_obj}}.helperText }
                value = { values[{{field_obj}}.name] }
                gqlId = { {{field_obj}}.gqlId }
                choices = { {{field_obj}}.choices }
                meta = {meta}
                {...field}
              />
            )}
          </Field>
  {%- elif item.button_list %}
          <Box>
            <br/>
            <Grid container spacing={2}>
    {%- for button in item.button_list.buttons.all() %}
      {%- set widget_name = button.widget.name -%}
      {%- set button_obj = "Button" + button.name -%}
              <Grid item>
                <{{widget_name}}
                  name={ {{button_obj}}.name }
                  gqlId={ {{button_obj}}.gqlId }
                  disabled={isSubmitting}
      {%- if button.submit %}
                  type="submit"
      {%- endif %}
                >{ {{button_obj}}.buttonText}</{{widget_name}}>
              </Grid>              
    {%- endfor %}
            </Grid>      
          </Box>
  {%- endif %}
{%- endfor %}
        </Form>
      )}
    </Formik>
  );
};

export default {{module_definition.name}}{{form.name}};
