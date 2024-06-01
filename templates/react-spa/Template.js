import React from 'react';
import { ThemeProvider, withTheme, createMuiTheme, responsiveFontSizes } from '@material-ui/core/styles';

{% from "import_widgets.js" import import_template_widgets -%}
{{import_template_widgets(template_widget_names)}}

{% for name, info in blocks.items() %}
const {{name}} = withTheme(props => ( // eslint-disable-line no-unused-vars
  <React.Fragment>
    {{info['content'].replace('\t', '  ')|indent|safe}}
  </React.Fragment>
));
{% endfor %}

const Template{{template.name}} = props => ( // eslint-disable-line no-unused-vars
  <ThemeProvider
    theme={responsiveFontSizes(createMuiTheme({{theme|indent(4)|safe}}))}
  >
    <React.Fragment>
      <{{root_block_name}} />
    </React.Fragment>
  </ThemeProvider>
);

export default Template{{template.name}};

