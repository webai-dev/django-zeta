from abc import ABC
import json

from django.template.loader import render_to_string

from ery_backend.frontends.models import Frontend
from ery_backend.scripts.babel_client import convert_es6_bundle


class ReactRenderer(ABC):
    def __init__(self, language):
        self.frontend = Frontend.objects.get(name='Web')
        self.language = language

    @staticmethod
    def _get_file_name(file_instance):
        """Use unique slugs instead of non-unique names"""
        return file_instance.slug.capitalize().replace('-', '_')

    @staticmethod
    def generate_variables(hand):
        """
        Creates dictionary of all relevant variables for current :class:`~ery_backend.hands.models.Hand`.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`)
        Notes:
            - :class:`~ery_backend.variables.models.HandVariable` instances are kept at the 1st level of the dictionary.
            - :class:`~ery_backend.variables.models.TeamVariable`, :class:`~ery_backend.variables.models.ModuleVariable`,
              and :class:`~ery_backend.variables.models.StintVariable` instances are assigned to sublevels labeled 'team',
              'module', and 'stint', respectively.

        Returns:
            Dict[str, Union[str, Dict[str, str]]]
        """
        variables = hand.stint.get_context(hand, target='babel')['variables']
        return json.dumps(variables)


class ReactModuleWidgetRenderer(ReactRenderer):
    def __init__(self, module_widget, language):
        self.module_widget = module_widget
        super().__init__(language)

    def render(self, is_preview=False):
        """
        Generate an ES5 based view with definitions needed to display the given instance.

        Args:
            - is_preview(Optional[bool]): Whether to render as standalone component.

        Returns:
            str: ES5 code.
        """
        require_communicate = self.module_widget.events.exists()
        choices = json.dumps(self.module_widget.get_choices(self.language)) if self.module_widget.is_multiple_choice else None

        return render_to_string(
            "ModuleWidget.js",
            context={
                "choices": choices,
                "module_widget": self.module_widget,
                "require_communicate": require_communicate,
                "validators": [
                    (validation.validator, validation.get_error_message(self.language))
                    for validation in self.module_widget.validations.all()
                ],
            },
        )


class ReactTemplateWidgetRenderer(ReactRenderer):
    def __init__(self, template_widget, language):
        self.template_widget = template_widget
        super().__init__(language)

    def render(self, is_preview=False):
        """
        Generate an ES5 based view with definitions needed to display the given instance.

        Args:
            - is_preview(Optional[bool]): Whether to render as standalone component.

        Returns:
            str: ES5 code.
        """
        return render_to_string(
            "TemplateWidget.js", context={"template_widget": self.template_widget, "is_preview": is_preview,}
        )


class ReactWidgetRenderer(ReactRenderer):
    def __init__(self, widget, language):
        self.widget = widget
        super().__init__(language)

    def render(self, is_preview=False):
        """
        Generate an ES5 based view with definitions needed to display the given instance.

        Args:
            - is_preview(Optional[bool]): Whether to render as standalone component.

        Returns:
            str: ES5 code.
        """
        from ery_backend.widgets.models import WidgetEventStep

        return render_to_string(
            "Widget.js",
            context={
                "widget": self.widget,
                "dependencies": self.widget.connections.select_related('target').all(),
                "require_communicate": (
                    self.widget.events.filter(
                        steps__event_action_type__in=WidgetEventStep.REQUIRE_COMMUNCIATE_ACTION_TYPES
                    ).exists()
                ),
                "is_preview": is_preview,
            },
        )


class ReactFormRenderer(ReactRenderer):
    def __init__(self, form, language):
        self.form = form
        super().__init__(language)

    def render(self, is_preview=False):
        """
        Generate an ES5 based view with definitions needed to display the given instance.

        Args:
            - is_preview(Optional[bool]): Whether to render as standalone component.

        Returns:
            str: ES5 code.
        """
        template_widgets = set()
        form_field_items = self.form.items.exclude(field=None).all()
        form_widgets = {item.field.widget for item in form_field_items}
        module_widgets = {item.field.get_module_widget() for item in form_field_items}
        for item in self.form.items.exclude(button_list=None).all():
            for button in item.button_list.buttons.all():
                form_widgets.add(button.widget)

        return render_to_string(
            "Form.js",
            context={
                "form": self.form,
                "form_widgets": form_widgets,
                "module_definition": self.form.module_definition,
                "module_widgets": module_widgets,
                "template_widgets": template_widgets,
                "validations": [],
                "is_preview": is_preview,
                "language": self.language,
            },
        )


class ReactTemplateRenderer(ReactRenderer):
    def __init__(self, template, language):
        self.template = template
        super().__init__(language)

    def render(self):
        template_widget_names = set()
        template_widgets = self.template.get_template_widgets()

        output = {}
        output[f"Template/{self.name}.js"] = render_to_string(
            "react-spa/Template.js",
            context={
                "template": self.template,
                "template_widget_names": list(template_widgets.values_list('name', flat=True)),
                "root_block_name": self.get_root_block().name,
            },
        )
        raise NotImplementedError("Implement is_preview method!")


class ReactStageRenderer(ReactRenderer):
    def __init__(self, stage_template, language):
        self.stage_template = stage_template
        super().__init__(language)

    def render(self, is_preview=False):
        """
        Generate an ES5 based view with definitions needed to display the given instance.

        Args:
            - is_preview(Optional[bool]): Whether to render as standalone component.
        Returns:
            str: ES5 code.
        """
        module_definition = self.stage_template.stage_definition.module_definition
        # XXX: Not sure how we'll allocate team name without hand
        variables = list(module_definition.variabledefinition_set.values_list('name', flat=True))
        theme = self.stage_template.theme or module_definition.default_theme

        template = self.stage_template.template or module_definition.default_template

        return render_to_string(
            "Stage.js",
            context={
                "blocks": self.stage_template.get_blocks(self.frontend, self.language),
                "forms": module_definition.forms.all(),
                "is_preview": is_preview,
                "module_definition": module_definition,
                "module_widgets": module_definition.module_widgets.all(),
                "root_block_name": self.stage_template.get_root_block().name,
                "stage_definition": self.stage_template.stage_definition,
                "template_widgets": template.template_widgets.all(),
                "theme": theme.get_mui_theme(),
                "variables": variables,
            },
        )


class ReactStintRenderer(ReactRenderer):
    def __init__(self, stint_definition, language, vendor=None, is_marketplace=False):
        self.stint_definition = stint_definition
        self.vendor = vendor
        self.is_marketplace = is_marketplace
        super().__init__(language)

    def render_module_widget_files(self, module_widgets):
        return {
            f"ModuleWidget/"
            f"{self._get_file_name(module_widget.module_definition)}_{module_widget.name}.js": ReactModuleWidgetRenderer(
                module_widget, self.language
            ).render()
            for module_widget in module_widgets
        }

    @classmethod
    def render_template_widget_files(cls, template_widgets, language):
        return {
            f"TemplateWidget/"
            f"{cls._get_file_name(template_widget.template)}_{template_widget.name}.js": ReactTemplateWidgetRenderer(
                template_widget, language
            ).render()
            for template_widget in template_widgets
        }

    def render_module_files(self, module_definitions):
        return {
            f"Module/{module_definition.name}.js": render_to_string(
                "Module.js", context={"stint_definition": self.stint_definition, "module_definition": module_definition,}
            )
            for module_definition in module_definitions
        }

    def render_stage_files(self, stage_definitions):
        output = {}

        for stage_definition in stage_definitions:
            filename = f"Stage/{stage_definition.module_definition.name}{stage_definition.name}.js"
            stage_template = stage_definition.stage_templates.get(template__frontend=self.frontend)
            output[filename] = stage_template.render_web(self.language)

        return output

    def render_widget_files(self, widgets):
        return {f"Widget/{self._get_file_name(widget)}.js": widget.render_web(self.language) for widget in widgets}

    def render_form_files(self, forms):
        return {
            f"Form/{self._get_file_name(form.module_definition)}_{form.name}.js": form.render_web(self.language)
            for form in forms
        }

    def render(self, raw=False):
        """
        Generate an ES5 based view with definitions needed to display the given instance.

        Args:
            - raw (Optional[bool]): For testing purposes. Setting to True returns ES6 code,
              instead of transpiled ES5 code.

        Returns:
            str: Component definitions.
        """
        from ery_backend.forms.models import Form
        from ery_backend.stages.models import StageDefinition

        module_definitions = self.stint_definition.module_definitions.all()
        forms = Form.objects.filter(id__in=self.stint_definition.module_definitions.values_list('forms__id', flat=True))
        stage_definition_ids = self.stint_definition.module_definitions.values_list('stage_definitions__id', flat=True)
        stage_definitions = StageDefinition.objects.filter(id__in=stage_definition_ids).all()
        widgets = self.stint_definition.get_widgets(self.frontend)
        template_widgets = self.stint_definition.get_template_widgets(self.frontend).all()
        module_widgets = self.stint_definition.get_module_widgets(self.frontend)

        es6_index_file = render_to_string('index.js')
        es6_app_file = render_to_string('App.js', context={"stint_definition": self.stint_definition, "initial_context": {},})
        es6_stint_file = render_to_string(
            'Stint.js', context={"stint_definition": self.stint_definition, "module_definitions": module_definitions,}
        )
        es6_bundle = {
            'index.js': es6_index_file,
            'MyCssBaseline.js': render_to_string('MyCssBaseline.js'),
            'App.js': es6_app_file,
            'Stint.js': es6_stint_file,
            **self.render_form_files(forms),
            **self.render_module_files(module_definitions),
            **self.render_widget_files(widgets),
            **self.render_template_widget_files(template_widgets, self.language),
            **self.render_module_widget_files(module_widgets),
            **self.render_stage_files(stage_definitions),
            'LoadingPage.js': render_to_string('LoadingPage.js'),
        }

        # import pprint

        # pp = pprint.PrettyPrinter(indent=2, width=127)
        # pp.pprint(es6_bundle)
        if raw:
            return es6_bundle

        es5_code = convert_es6_bundle(es6_bundle)
        return render_to_string(
            'index.html',
            context={
                "stint_definition": self.stint_definition,
                "vendor": self.vendor,
                "is_marketplace": self.is_marketplace,
                "error": es5_code.error,
                "code": es5_code.code,
            },
        )
