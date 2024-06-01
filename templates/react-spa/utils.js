{% macro lowercase_first(str_1) -%}
  {{str_1[0]|lower}}{{str_1[1:] if str_1|length > 1 else ""}}
{%- endmacro -%}

{% macro capitalize_first(str_1) -%}
  {{str_1[0]|upper}}{{str_1[1:] if str_1|length > 1 else ""}}
{%- endmacro -%}

{% macro camelcase(str_1, str_2) -%}
  {%- if str_1 -%}
    {{lowercase_first(str_1)}}{{capitalize_first(str_2)}}
  {%- else -%}
    {{lowercase_first(str_2)}}
  {%- endif -%}
{%- endmacro -%}
