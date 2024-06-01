from unittest import mock

from lxml import etree

from django.core.exceptions import ObjectDoesNotExist

from ery_backend.base.testcases import EryTestCase, create_test_stintdefinition, create_test_hands
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.hands.models import Hand
from ery_backend.modules.factories import (
    ModuleDefinitionFactory,
    ModuleDefinitionWidgetFactory,
    WidgetChoiceFactory,
    WidgetChoiceTranslationFactory,
)
from ery_backend.stages.factories import (
    StageDefinitionFactory,
    StageTemplateFactory,
    StageTemplateBlockFactory,
    StageTemplateBlockTranslationFactory,
)
from ery_backend.stints.models import StintDefinitionModuleDefinition, Stint
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.syncs.factories import EraFactory
from ery_backend.templates.factories import (
    TemplateFactory,
    TemplateBlockFactory,
    TemplateBlockTranslationFactory,
    TemplateWidgetFactory,
)
from ery_backend.users.factories import UserFactory
from ery_backend.users.models import User
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetFactory
from ..models import SMSStage
from ..sms_utils import (
    get_or_create_user,
    get_or_create_stint,
    opt_in,
    get_or_create_sms_stage,
    SMSStageTemplateRenderer,
    is_opt_in,
)


# class TestTags(EryTestCase):
#    def test_get_block_tags(self):
#        """
#        Confirms full set of tags retrieved as expected.
#        """
#        blocks = {
#            'Root': {'content': '<Top /> <Middle /> <Bottom />'},
#            'Top': {'content': '<Left /> <Right />'},
#            'Middle': {'content': 'Nothing special here'},
#            'Bottom': {'content': 'No kalas here'},
#            'Left': {'content': '<Kalas />'},
#            'Right': {'content': 'Nothing special here'},
#            'Kalas': {'content': 'Kalas over here!!!'},
#            'Extra': {'content': 'issaTRAP'}
#        }
#        self.assertEqual(
#            get_block_tags('Root', blocks),
#            set(['Top', 'Middle', 'Bottom', 'Left', 'Right', 'Kalas'])
#        )


class TestUtils(EryTestCase):
    def setUp(self):
        self.stint_specification = StintSpecificationFactory(opt_in_code='test-in')

    def test_get_or_create_user(self):
        phone_number = '1-800-588-2300'  # Empiiiirreee, today
        user = get_or_create_user(phone_number)
        self.assertEqual(user.username, f'__phone_no__{phone_number}')
        self.assertIsInstance(user, User)

    def test_get_or_create_stint(self):
        module_definition = ModuleDefinitionFactory(start_stage=StageDefinitionFactory())
        module_definition.start_stage.module_definition = module_definition
        if module_definition.start_era:
            self.fail("Autogeneration fixed. Update code")
        module_definition.start_era = EraFactory(module_definition=module_definition)
        module_definition.start_stage.save()
        module_definition.save()
        StintDefinitionModuleDefinition.objects.create(
            stint_definition=self.stint_specification.stint_definition, module_definition=module_definition
        )
        user = UserFactory()
        # create
        stint = get_or_create_stint(self.stint_specification.opt_in_code, user, signal_pubsub=False)
        expected_stint = Stint.objects.get(stint_specification=self.stint_specification)
        self.assertEqual(stint, expected_stint)

        # get
        stint = get_or_create_stint(self.stint_specification.opt_in_code, user, signal_pubsub=False)
        self.assertEqual(stint, expected_stint)
        # confirm no new stints created
        self.assertEqual(Stint.objects.filter(stint_specification=self.stint_specification).count(), 1)

    def test_is_opt_in(self):
        """
        Confirm is_opt_in is case_insensitive and allows whitespace.
        """
        self.assertTrue(is_opt_in('test-in'))
        self.assertTrue(is_opt_in('TEST-IN'))
        self.assertTrue(is_opt_in('tEsT-iN'))
        self.assertTrue(is_opt_in('tesT- I n'))
        self.assertFalse(is_opt_in('test-out'))

    def test_opt_in(self):
        """
        Confirm user can log into stint with opt-in code
        """
        frontend = Frontend.objects.get(name='SMS')
        stint_definition = create_test_stintdefinition(frontend=frontend)
        self.stint_specification.stint_definition = stint_definition
        self.stint_specification.save()
        stint = self.stint_specification.stints
        self.assertFalse(stint.exists())
        opt_in(self.stint_specification.opt_in_code, '5-111-111-1111', signal_pubsub=False)
        # opt in should create a stint if one does not exist
        self.assertTrue(stint.exists())
        # opt in should create a hand linked to new stint
        self.assertIsNotNone(
            Hand.objects.get(stint=stint.first(), user=User.objects.get(username='__phone_no__5-111-111-1111'))
        )

    def test_case_insensitive_opt_in(self):
        frontend = Frontend.objects.get(name='SMS')
        stint_definition = create_test_stintdefinition(frontend=frontend)
        self.stint_specification.stint_definition = stint_definition
        self.stint_specification.save()
        stint = self.stint_specification.stints
        self.assertFalse(stint.exists())
        opt_in('test-IN', '5-111-111-1111', signal_pubsub=False)
        # opt in should create a stint if one does not exist
        self.assertTrue(stint.exists())
        # opt in should create a hand linked to new stint
        self.assertIsNotNone(
            Hand.objects.get(stint=stint.first(), user=User.objects.get(username='__phone_no__5-111-111-1111'))
        )

    def test_get_or_create_sms_stage(self):
        """
        Confirm get_or_create works as expected.
        """
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        expected_sms_stage = SMSStage.objects.filter(stage=hand.stage)
        self.assertFalse(expected_sms_stage.exists())
        get_or_create_sms_stage(hand)
        self.assertTrue(expected_sms_stage.exists())


class TestSMSStageTemplateRenderer(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.sms = Frontend.objects.get(name='SMS')
        cls.hand = HandFactory(frontend=cls.sms)
        cls.parser = etree.XMLParser()
        cls.language = get_default_language()

    def setUp(self):
        stage_def = StageDefinitionFactory()
        root_template = TemplateFactory(frontend=self.sms)
        child_template = TemplateFactory(frontend=self.sms, parental_template=root_template)
        self.root_t_block = TemplateBlockFactory(template=root_template)
        self.child_t_block_1 = TemplateBlockFactory(template=child_template)
        self.child_t_block_2 = TemplateBlockFactory(template=child_template)
        self.stage_template = StageTemplateFactory(stage_definition=stage_def, template=child_template)
        self.stage_template_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        self.renderer = SMSStageTemplateRenderer(stage_template=self.stage_template, hand=self.hand)

    def test_get_widget_from_element_no_widget(self):
        """
        Confirm widget found, but without any block context.
        """
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block, frontend=self.sms, language=self.language, content='Test text'
        )
        TemplateBlockTranslationFactory(template_block=self.child_t_block_1, frontend=self.sms, language=self.language)
        TemplateBlockTranslationFactory(template_block=self.child_t_block_2, frontend=self.sms, language=self.language)
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block, frontend=self.sms, language=self.language
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        self.assertEqual(len(self.renderer.get_widgets_from_element(root, blocks)), 0)

    def test_get_widget_from_root_template_block(self):
        """
        Confirm widget found and returned with correct information
        """
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block, frontend=self.sms, language=self.language, content='<Widget.MyWidget/>'
        )
        TemplateBlockTranslationFactory(template_block=self.child_t_block_1, frontend=self.sms, language=self.language)
        TemplateBlockTranslationFactory(template_block=self.child_t_block_2, frontend=self.sms, language=self.language)
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block, frontend=self.sms, language=self.language
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        expected_key = f'MyWidget-TemplateBlock-{self.root_t_block.template.id}'
        self.assertEqual(self.renderer.get_widgets_from_element(root, blocks), [expected_key])

    def test_get_widget_from_nested_template_block(self):
        """
        Confirm widget found and returned with correct information
        """
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_1.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_1, frontend=self.sms, language=self.language, content='<Widget.MyWidget />'
        )
        TemplateBlockTranslationFactory(template_block=self.child_t_block_2, frontend=self.sms, language=self.language)
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block, frontend=self.sms, language=self.language
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        expected_key = f'MyWidget-TemplateBlock-{self.child_t_block_1.template.id}'
        self.assertEqual(self.renderer.get_widgets_from_element(root, blocks), [expected_key])

    def test_get_widget_from_stagetemplate_block(self):
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_1.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_1,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_2.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_2,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.stage_template_block.name}/>',
        )
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block,
            frontend=self.sms,
            language=self.language,
            content='<Widget.MyWidget>Some noise</Widget.MyWidget>',
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        expected_key = f'MyWidget-StageTemplateBlock-{self.stage_template_block.get_privilege_ancestor().id}'
        self.assertEqual(self.renderer.get_widgets_from_element(root, blocks), [expected_key])

    def test_get_multiple_widgets(self):
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_1.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_1,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_2.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_2,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.stage_template_block.name}/><Widget.MyWidget/>',
        )
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block,
            frontend=self.sms,
            language=self.language,
            content='<Widget.MDWidget>Some noise</Widget.MDWidget>',
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        actual_keys = self.renderer.get_widgets_from_element(root, blocks)
        expected_keys = [
            f'MDWidget-StageTemplateBlock-{self.stage_template_block.get_privilege_ancestor().id}',
            f'MyWidget-TemplateBlock-{self.child_t_block_2.get_privilege_ancestor().id}',
        ]
        for expected_key in expected_keys:
            self.assertIn(expected_key, actual_keys)


class TestGetWidgetsFromElement(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.sms = Frontend.objects.get(name='SMS')
        cls.hand = HandFactory(frontend=cls.sms)
        cls.parser = etree.XMLParser()
        cls.language = get_default_language()
        cls.renderer = SMSStageTemplateRenderer

    def setUp(self):
        stage_def = StageDefinitionFactory()
        root_template = TemplateFactory(frontend=self.sms)
        child_template = TemplateFactory(frontend=self.sms, parental_template=root_template)
        self.root_t_block = TemplateBlockFactory(template=root_template)
        self.child_t_block_1 = TemplateBlockFactory(template=child_template)
        self.child_t_block_2 = TemplateBlockFactory(template=child_template)
        self.stage_template = StageTemplateFactory(stage_definition=stage_def, template=child_template)
        self.stage_template_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        self.renderer = SMSStageTemplateRenderer(self.stage_template, self.hand)

    def test_get_widget_from_element_no_widget(self):
        """
        Confirm widget found, but without any block context.
        """
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block, frontend=self.sms, language=self.language, content='Test text'
        )
        TemplateBlockTranslationFactory(template_block=self.child_t_block_1, frontend=self.sms, language=self.language)
        TemplateBlockTranslationFactory(template_block=self.child_t_block_2, frontend=self.sms, language=self.language)
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block, frontend=self.sms, language=self.language
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        self.assertEqual(len(self.renderer.get_widgets_from_element(root, blocks)), 0)

    def test_get_widget_from_root_template_block(self):
        """
        Confirm widget found and returned with correct information
        """
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block, frontend=self.sms, language=self.language, content='<Widget.MyWidget/>'
        )
        TemplateBlockTranslationFactory(template_block=self.child_t_block_1, frontend=self.sms, language=self.language)
        TemplateBlockTranslationFactory(template_block=self.child_t_block_2, frontend=self.sms, language=self.language)
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block, frontend=self.sms, language=self.language
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        expected_key = f'MyWidget-TemplateBlock-{self.root_t_block.template.id}'
        self.assertEqual(self.renderer.get_widgets_from_element(root, blocks), [expected_key])

    def test_get_widget_from_nested_template_block(self):
        """
        Confirm widget found and returned with correct information
        """
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_1.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_1, frontend=self.sms, language=self.language, content='<Widget.MyWidget />'
        )
        TemplateBlockTranslationFactory(template_block=self.child_t_block_2, frontend=self.sms, language=self.language)
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block, frontend=self.sms, language=self.language
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        expected_key = f'MyWidget-TemplateBlock-{self.child_t_block_1.template.id}'
        self.assertEqual(self.renderer.get_widgets_from_element(root, blocks), [expected_key])

    def test_get_widget_from_stagetemplate_block(self):
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_1.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_1,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_2.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_2,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.stage_template_block.name}/>',
        )
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block,
            frontend=self.sms,
            language=self.language,
            content='<Widget.MyWidget>Some noise</Widget.MyWidget>',
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        expected_key = f'MyWidget-StageTemplateBlock-{self.stage_template_block.get_privilege_ancestor().id}'
        self.assertEqual(self.renderer.get_widgets_from_element(root, blocks), [expected_key])

    def test_get_multiple_widgets(self):
        TemplateBlockTranslationFactory(
            template_block=self.root_t_block,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_1.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_1,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.child_t_block_2.name}/>',
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_t_block_2,
            frontend=self.sms,
            language=self.language,
            content=f'<{self.stage_template_block.name}/><Widget.MyWidget/>',
        )
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_template_block,
            frontend=self.sms,
            language=self.language,
            content='<Widget.MDWidget>Some noise</Widget.MDWidget>',
        )
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language, raw=True)
        tree = SMSStageTemplateRenderer(self.stage_template, self.hand).get_xml_tree(
            blocks[self.root_t_block.name]['content'], parser=self.parser, wrapper=self.root_t_block.name
        )
        root = tree.getroot()
        actual_keys = self.renderer.get_widgets_from_element(root, blocks)
        expected_keys = [
            f'MDWidget-StageTemplateBlock-{self.stage_template_block.get_privilege_ancestor().id}',
            f'MyWidget-TemplateBlock-{self.child_t_block_2.get_privilege_ancestor().id}',
        ]
        for expected_key in expected_keys:
            self.assertIn(expected_key, actual_keys)


class TestGetSMSWidgets(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.sms = Frontend.objects.get(name='SMS')
        cls.web = Frontend.objects.get(name='Web')
        cls.renderer = SMSStageTemplateRenderer
        cls.tricky_widget = WidgetFactory(frontend=cls.sms, code='<div>ITS G TO ROCK AROUND</div> ')
        cls.language = get_default_language()

    def setUp(self):
        self.hand = create_test_hands(frontend_type='SMS', signal_pubsub=False).first()
        base_stagedefinition = self.hand.stage.stage_definition
        self.stage_template = base_stagedefinition.stage_templates.get(template__frontend=self.sms)
        self.content_template = self.stage_template.template.parental_template
        content_block = self.content_template.blocks.get(name='Content')
        content_block_translation = content_block.translations.get(frontend=self.sms)
        content_block_translation.content = '<ChildContentOne/>'
        content_block_translation.save()
        self.child_content_one_block = TemplateBlockFactory(name='ChildContentOne', template=self.content_template)
        self.widget = WidgetFactory(name='TestWidget', frontend=self.sms)

    def test_widget_but_wrong_frontend(self):
        self.widget.frontend = self.web
        self.widget.save()
        TemplateBlockTranslationFactory(
            template_block=self.child_content_one_block, language=self.language, content='<Widget.TestWidget/>'
        )
        TemplateWidgetFactory(template=self.child_content_one_block.template, widget=self.widget)
        with self.assertRaises(ObjectDoesNotExist):
            self.renderer(self.stage_template, hand=self.hand).get_sms_widgets()

    def test_widget_but_no_template_widget(self):
        """
        TemplateWidget must be present for Template to get Widget.
        """
        TemplateBlockTranslationFactory(
            template_block=self.child_content_one_block, language=self.language, content='<Widget.TestWidget/>'
        )
        ModuleDefinitionWidgetFactory(module_definition=self.stage_template.get_privilege_ancestor(), widget=self.widget)
        with self.assertRaises(ObjectDoesNotExist):
            self.renderer(self.stage_template, hand=self.hand).get_sms_widgets()

    def test_template_widget(self):
        template_widget = TemplateWidgetFactory(
            template=self.child_content_one_block.template, widget=self.widget, name='TestWidget'
        )
        TemplateBlockTranslationFactory(
            template_block=self.child_content_one_block, language=self.language, content='<Widget.TestWidget/>'
        )
        widget_key = f'TestWidget-TemplateBlock-{template_widget.template.id}'
        self.assertEqual(self.renderer(self.stage_template, hand=self.hand).get_sms_widgets()[widget_key], template_widget)

    def test_widget_but_no_module_widget(self):
        st_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        TemplateBlockTranslationFactory(
            template_block=self.child_content_one_block, language=self.language, content=f'<{st_block.name} />'
        )
        TemplateWidgetFactory(template=self.child_content_one_block.template, widget=self.widget, name='TestWidget')
        StageTemplateBlockTranslationFactory(stage_template_block=st_block, content='<Widget.TestWidget />')
        ModuleDefinitionWidgetFactory(module_definition=self.stage_template.get_privilege_ancestor(), widget=self.widget)
        with self.assertRaises(ObjectDoesNotExist):
            self.renderer(self.stage_template, hand=self.hand).get_sms_widgets()

    def test_module_widget(self):
        st_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        TemplateBlockTranslationFactory(
            template_block=self.child_content_one_block, language=self.language, content=f'<{st_block.name} />'
        )
        TemplateWidgetFactory(template=self.child_content_one_block.template, widget=self.widget, name='TestWidget')
        StageTemplateBlockTranslationFactory(stage_template_block=st_block, content='<Widget.TestWidget />')
        module_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.stage_template.get_privilege_ancestor(), widget=self.widget, name='TestWidget'
        )
        widget_key = f'TestWidget-StageTemplateBlock-{module_widget.get_privilege_ancestor().id}'
        self.assertEqual(self.renderer(self.stage_template, hand=self.hand).get_sms_widgets()[widget_key], module_widget)

    def test_multiple_widgets_in_same_block(self):
        TemplateBlockTranslationFactory(
            template_block=self.child_content_one_block, language=self.language, content='<ChildContentTwo />'
        )
        child_content_two_block = TemplateBlockFactory(name='ChildContentTwo', template=self.content_template)
        TemplateBlockTranslationFactory(content='<GrandchildContent/>', template_block=child_content_two_block)
        grandchild_content_block = TemplateBlockFactory(name='GrandchildContent', template=self.content_template)
        TemplateBlockTranslationFactory(
            content='<div>I found <span><Widget.TestWidgetOne/></span> and' ' <span><Widget.TestWidgetTwo/></span></div>',
            template_block=grandchild_content_block,
        )
        first_widget = WidgetFactory(frontend=self.sms)
        second_widget = WidgetFactory(frontend=self.sms)
        first_t_widget = TemplateWidgetFactory(
            name='TestWidgetOne', template=grandchild_content_block.get_privilege_ancestor(), widget=first_widget
        )
        second_t_widget = TemplateWidgetFactory(
            name='TestWidgetTwo', template=grandchild_content_block.get_privilege_ancestor(), widget=second_widget
        )

        widget_keys = [
            f'TestWidgetOne-TemplateBlock-{first_t_widget.get_privilege_ancestor().id}',
            f'TestWidgetTwo-TemplateBlock-{second_t_widget.get_privilege_ancestor().id}',
        ]
        widgets = self.renderer(self.stage_template, hand=self.hand).get_sms_widgets()
        self.assertEqual(widgets[widget_keys[0]], first_t_widget)
        self.assertEqual(widgets[widget_keys[1]], second_t_widget)

    def test_multiple_widgets_in_different_blocks(self):
        TemplateBlockTranslationFactory(
            template_block=self.child_content_one_block, language=self.language, content='<ChildContentTwo />'
        )

        child_content_two_block = TemplateBlockFactory(name='ChildContentTwo', template=self.content_template)
        TemplateBlockTranslationFactory(
            content='<GrandchildContent/><Widget.TestWidgetTwo/>',
            template_block=child_content_two_block,
            frontend=self.sms,
            language=self.language,
        )
        grandchild_content_block = TemplateBlockFactory(name='GrandchildContent', template=self.content_template)
        TemplateBlockTranslationFactory(
            content='I found <Widget.TestWidgetOne/>!',
            template_block=grandchild_content_block,
            frontend=self.sms,
            language=self.language,
        )
        first_widget = WidgetFactory(frontend=self.sms)
        second_widget = WidgetFactory(frontend=self.sms)
        first_t_widget = TemplateWidgetFactory(
            name='TestWidgetOne', template=grandchild_content_block.get_privilege_ancestor(), widget=first_widget
        )
        second_t_widget = TemplateWidgetFactory(
            name='TestWidgetTwo', template=grandchild_content_block.get_privilege_ancestor(), widget=second_widget
        )
        widget_keys = [
            f'TestWidgetOne-TemplateBlock-{first_t_widget.get_privilege_ancestor().id}',
            f'TestWidgetTwo-TemplateBlock-{second_t_widget.get_privilege_ancestor().id}',
        ]
        widgets = self.renderer(self.stage_template, hand=self.hand).get_sms_widgets()
        self.assertEqual(widgets[widget_keys[0]], first_t_widget)
        self.assertEqual(widgets[widget_keys[1]], second_t_widget)


class TestRenderSMSWidget(EryTestCase):
    """Confirm SMSRenderer.render_widget calls are made as expected"""

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.sms = Frontend.objects.get(name='SMS')
        cls.language = get_default_language()
        cls.hand = HandFactory(user=UserFactory())

    def setUp(self):
        self.stage_template = StageTemplateFactory()

    @mock.patch('ery_backend.frontends.sms_utils.evaluate_without_side_effects')
    def test_render_template_widget(self, mock_eval):
        template_widget = TemplateWidgetFactory()
        SMSStageTemplateRenderer(self.stage_template, self.hand).render_widget(template_widget)
        mock_eval.assert_called_with(
            f'render_{template_widget.widget}', template_widget.widget.code, self.hand, extra_variables={}
        )

    @mock.patch('ery_backend.frontends.sms_utils.evaluate_without_side_effects')
    def test_render_template_widget_with_kwargs(self, mock_eval):
        template_widget = TemplateWidgetFactory()
        extra_kwargs = {'extra_variables': {'extra': "Because MURICA"}}
        SMSStageTemplateRenderer(self.stage_template, self.hand).render_widget(template_widget, **extra_kwargs)
        mock_eval.assert_called_with(
            f'render_{template_widget.widget}',
            template_widget.widget.code,
            self.hand,
            extra_variables=extra_kwargs['extra_variables'],
        )

    @mock.patch('ery_backend.frontends.sms_utils.evaluate_without_side_effects')
    def test_render_module_widget(self, mock_eval):
        variable_definition = VariableDefinitionFactory(
            exclude=[VariableDefinition.DATA_TYPE_CHOICES.stage, VariableDefinition.DATA_TYPE_CHOICES.choice]
        )
        md_widget = ModuleDefinitionWidgetFactory(variable_definition=variable_definition)
        SMSStageTemplateRenderer(self.stage_template, self.hand).render_widget(md_widget)
        mock_eval.assert_called_with(f'render_{md_widget.widget}', md_widget.widget.code, self.hand, extra_variables={})

    @mock.patch('ery_backend.frontends.sms_utils.evaluate_without_side_effects')
    def test_render_module_widget_with_choices(self, mock_eval):
        md_widget = ModuleDefinitionWidgetFactory()
        water_closet = WidgetChoiceFactory(widget=md_widget)
        WidgetChoiceTranslationFactory(language=self.language, widget_choice=water_closet)
        SMSStageTemplateRenderer(self.stage_template, self.hand).render_widget(md_widget)
        mock_eval.assert_called_with(
            f'render_{md_widget.widget}',
            md_widget.widget.code,
            self.hand,
            extra_variables=md_widget.get_choices_as_extra_variable(language=self.language),
        )
