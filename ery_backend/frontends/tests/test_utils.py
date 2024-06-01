import random

from ery_backend.base.testcases import EryTestCase, create_test_hands, create_test_stintdefinition
from ery_backend.frontends.models import Frontend
from ery_backend.frontends.renderers import ReactStintRenderer
from ery_backend.hands.factories import HandFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.templates.factories import TemplateWidgetFactory, TemplateFactory
from ery_backend.widgets.factories import WidgetFactory


file_naming_function = ReactStintRenderer._get_file_name  # pylint: disable=protected-access


class TestWidgetRender(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(frontend_type='Web', module_definition_n=1, stage_n=1).first()
        self.widget_template = self.hand.stage.stage_definition.stage_templates.get(
            template__frontend=self.hand.frontend
        ).template

    def test_avoid_naming_conflicts(self):
        """
        Confirm widgets with the same name don't override each other
        """
        widget_1 = WidgetFactory(name='ConflictWidget', frontend=self.hand.frontend)
        widget_2 = WidgetFactory(name='ConflictWidget', frontend=self.hand.frontend)
        TemplateWidgetFactory(name='ConflictWidget1', template=self.widget_template, widget=widget_1)
        TemplateWidgetFactory(name='ConflictWidget2', template=self.widget_template, widget=widget_2)
        es6_output = ReactStintRenderer(
            stint_definition=self.hand.stint.stint_specification.stint_definition,
            is_marketplace=False,
            language=self.hand.language,
        ).render(raw=True)
        self.assertIn(f"Widget/{file_naming_function(widget_1)}.js", es6_output)
        self.assertIn(f"Widget/{file_naming_function(widget_2)}.js", es6_output)


class TestTemplateWidgetRender(EryTestCase):
    def setUp(self):
        web = Frontend.objects.get(name='Web')
        sd = create_test_stintdefinition(frontend=web)
        stint_specification = StintSpecificationFactory(stint_definition=sd)
        stage_def = sd.module_definitions.first().start_stage
        stage_template = stage_def.stage_templates.get(template__frontend=web)
        self.widget = WidgetFactory(frontend=web)
        self.content_template = stage_template.template.parental_template
        stint = sd.realize(stint_specification=stint_specification)
        self.hand = HandFactory(stint=stint)

    def test_avoid_naming_conflicts(self):
        tw_primary = TemplateWidgetFactory(widget=self.widget, template=self.content_template)
        secondary_content_template = TemplateFactory(name=self.content_template.name)
        tw_secondary = TemplateWidgetFactory(widget=self.widget, template=secondary_content_template)
        secondary_content_template.parental_template = self.content_template.parental_template
        secondary_content_template.save()
        self.content_template.parental_template = secondary_content_template
        self.content_template.save()
        es6_output = ReactStintRenderer(
            stint_definition=self.hand.stint.stint_specification.stint_definition,
            is_marketplace=False,
            language=self.hand.language,
        ).render(raw=True)
        self.assertIn(f"TemplateWidget/{file_naming_function(self.content_template)}_{tw_primary.name}.js", es6_output)
        self.assertIn(f"TemplateWidget/{file_naming_function(secondary_content_template)}_{tw_secondary.name}.js", es6_output)


class TestReactStageRender(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(frontend_type='Web', module_definition_n=1, stage_n=1).first()
        self.renderer = ReactStintRenderer(
            stint_definition=self.hand.stint.stint_specification.stint_definition,
            is_marketplace=False,
            language=self.hand.language,
        )
        self.stage_n = self.hand.stage.stage_definition.name.split('Definition')[-1]
        self.module_n = self.hand.current_module_definition.name.split('Definition')[-1]
        self.actual_output = self.renderer.render(raw=True)[
            f'Stage/ModuleDefinition{self.module_n}StageDefinition{self.stage_n}.js'
        ]

    # XXX: Add in preview-render
    def test_generate_stage_name(self):
        pass

    def test_generate_block_names(self):
        self.assertIn('const Content =', self.actual_output)
        self.assertIn('const Questions = ', self.actual_output)
        self.assertIn('const Answers =', self.actual_output)
        self.assertIn('const Footer = ', self.actual_output)

    def test_generate_block_content(self):
        """Confirm correct content in block"""
        expected_content = (
            f"This is the content for the questions block belonging to StageDefinition{self.stage_n} "
            f"(ModuleDefinition{self.module_n})."
        )
        self.assertIn(expected_content, self.actual_output)


class TestReactModuleRender(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(
            frontend_type='Web', module_definition_n=random.randint(1, 5), stage_n=random.randint(1, 5)
        ).first()
        cls.renderer = ReactStintRenderer(
            stint_definition=cls.hand.stint.stint_specification.stint_definition,
            is_marketplace=False,
            language=cls.hand.language,
        )
        cls.full_output = cls.renderer.render(raw=True)
        cls.module_outputs = {}
        for module in cls.hand.stint.modules.all():
            md_name = module.stint_definition_module_definition.module_definition.name
            cls.module_outputs[md_name] = cls.full_output[f'Module/{md_name}.js']

    def test_expected_module_names(self):
        for module in self.hand.stint.modules.all():
            md_name = module.stint_definition_module_definition.module_definition.name
            self.assertIn(f'const Module{md_name}', self.module_outputs[md_name])

    def test_expected_stage_names(self):
        for module in self.hand.stint.modules.all():
            stage_names = module.stint_definition_module_definition.module_definition.stage_definitions.order_by(
                'id'
            ).values_list('name', flat=True)
            md_name = module.stint_definition_module_definition.module_definition.name
            self.assertIn('const stages = {', self.module_outputs[md_name])
            for stage_name in stage_names:
                self.assertIn(
                    f'"{stage_name}": React.lazy(() => import(\'../Stage/{md_name}{stage_name}\'))',
                    self.module_outputs[md_name],
                )


# XXX: Revisit in issue concerning client-side evaluation
# class TestProcedureIntegration(EryTestCase):
#     """
#     """
#     def test_fail(self):
#         raise NotImplementedError()
