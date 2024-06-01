from django.utils.crypto import get_random_string

from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.modules.models import ModuleDefinitionWidget
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory, WidgetChoiceTranslationFactory, WidgetChoiceFactory
from ery_backend.stages.factories import StageTemplateBlockFactory, StageTemplateBlockTranslationFactory
from ery_backend.templates.factories import TemplateWidgetFactory
from ery_backend.widgets.factories import WidgetFactory


class TestSMSWidget(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.frontend = Frontend.objects.get(name='SMS')
        cls.language = get_default_language()

    def setUp(self):
        self.hand = create_test_hands(n=1, frontend_type='SMS').first()
        self.stage_template = self.hand.stage.stage_definition.stage_templates.get(template__frontend__name='SMS')
        self.parental_template = self.stage_template.template.parental_template
        parental_template_block = self.parental_template.blocks.first()
        self.parental_translation = parental_template_block.translations.get(language__pk='en')

    def test_sms_widget(self):
        """
        Confirm widget renders as expected for SMS.
        """
        widget = WidgetFactory(
            frontend=self.frontend, code='output = \'\'; for (i=0; i<3; i++){ new_line = \'a\'; output += new_line;}; output;'
        )
        TemplateWidgetFactory(template=self.parental_template, widget=widget, name=widget.name)
        self.parental_translation.content = f'<Widget.{widget.name}/>'
        self.parental_translation.save()
        output = self.hand.stage.render(self.hand)
        self.assertEqual(output, 'aaa\n')

    def test_sms_module_widget(self):
        """
        Confirm widget renders as expected for SMS.
        """
        from ery_backend.widgets.models import Widget

        sms_widget = Widget.objects.get(name='SMSMultipleChoiceCaptionValueWidget')
        module_definition_widget = ModuleDefinitionWidgetFactory(
            widget=sms_widget,
            random_mode=ModuleDefinitionWidget.RANDOM_CHOICES.asc,
            module_definition=self.hand.current_module_definition,
        )
        widget_choices = [WidgetChoiceFactory(widget=module_definition_widget, order=i, value=i) for i in range(3)]
        for widget_choice in widget_choices:
            widget_choice_translation = WidgetChoiceTranslationFactory(widget_choice=widget_choice, language=self.language)
            widget_choice_translation.caption = get_random_string(10)
            widget_choice_translation.save()
        choices = module_definition_widget.get_choices(self.language)
        stage_template_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        StageTemplateBlockTranslationFactory(
            stage_template_block=stage_template_block,
            content=f'<Widget.{module_definition_widget.name}/>',
            language=self.language,
            frontend=self.frontend,
        )
        self.parental_translation.content = f'<{stage_template_block.name} />'
        self.parental_translation.save()
        output = self.hand.stage.render(self.hand)
        self.assertIn(f"0 for {choices[0]['caption']}", output)
        self.assertIn(f"1 for {choices[1]['caption']}", output)
        self.assertIn(f"2 for {choices[2]['caption']}", output)

    def test_multiple_widgets(self):
        """
        Confirm widgets render as expected for SMS.
        """
        from ery_backend.widgets.models import Widget

        widget = WidgetFactory(
            frontend=self.frontend, code='output = \'\'; for (i=0; i<3; i++){ new_line = \'a\'; output += new_line;}; output;'
        )
        TemplateWidgetFactory(template=self.parental_template, widget=widget, name=widget.name)
        choice_widget = Widget.objects.get(name='SMSMultipleChoiceCaptionValueWidget')
        module_definition_widget = ModuleDefinitionWidgetFactory(
            widget=choice_widget,
            random_mode=ModuleDefinitionWidget.RANDOM_CHOICES.asc,
            module_definition=self.hand.current_module_definition,
        )
        widget_choices = [WidgetChoiceFactory(widget=module_definition_widget, order=i, value=i) for i in range(3)]
        for widget_choice in widget_choices:
            widget_choice_translation = WidgetChoiceTranslationFactory(widget_choice=widget_choice, language=self.language)
            widget_choice_translation.caption = get_random_string(10)
            widget_choice_translation.save()
        choices = module_definition_widget.get_choices(self.language)
        stage_template_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        StageTemplateBlockTranslationFactory(
            stage_template_block=stage_template_block,
            content=f'<Widget.{module_definition_widget.name}/>',
            language=get_default_language(),
            frontend=self.frontend,
        )
        self.parental_translation.content = f'<Widget.{widget.name}/><{stage_template_block.name} />'
        self.parental_translation.save()
        output = self.hand.stage.render(self.hand)
        self.assertIn('aaa', output)
        self.assertIn(f"0 for {choices[0]['caption']}", output)
        self.assertIn(f"1 for {choices[1]['caption']}", output)
        self.assertIn(f"2 for {choices[2]['caption']}", output)
