import re

from django.test import override_settings, Client

from languages_plus.models import Language

from ery_backend.hands.factories import HandFactory
from ery_backend.base.testcases import EryLiveServerTestCase, get_chromedriver, create_test_stintdefinition
from ery_backend.frontends.models import Frontend
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory, WidgetChoiceFactory, WidgetChoiceTranslationFactory
from ery_backend.labs.factories import LabFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.stages.factories import StageTemplateBlockFactory, StageTemplateBlockTranslationFactory
from ery_backend.templates.factories import TemplateBlockFactory, TemplateBlockTranslationFactory
from ery_backend.templates.models import Template
from ery_backend.users.factories import UserFactory
from ery_backend.users.models import User
from ery_backend.widgets.factories import WidgetFactory


@override_settings(DEBUG=False, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestLabWebRenderClient(EryLiveServerTestCase):
    """
    Silvia has received a link to log into a stint, hosted via lab.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.client = Client()

    def setUp(self):
        self.web = Frontend.objects.get(name='Web')
        self.silvia = UserFactory(username='Silvia4prez')
        self.loggedin_client = self.get_loggedin_client(self.silvia)
        stint_definition = create_test_stintdefinition(frontend=self.web)
        stint_specification = StintSpecificationFactory(
            stint_definition=stint_definition,
            team_size=2,
            max_team_size=2,
            min_team_size=2,
            language=Language.objects.get(pk='en'),
        )
        stint = stint_specification.realize()
        self.lab = LabFactory(current_stint=stint)
        other_stint = stint_specification.realize()
        for _ in range(2):
            HandFactory(stint=other_stint, user=UserFactory(), frontend=self.web)
        self.random_hand = other_stint.hands.first()
        self.other_lab = LabFactory(current_stint=other_stint)

    def test_current_stint_dne(self):
        """
        The Administrator forgets to run stint_specification.realize for the lab, which therefore has no current stint.
        """
        # setup environment
        self.lab.current_stint = None
        self.lab.save()

        response = self.client.get(f'{self.live_server_url}/lab/{self.lab.secret}/1/')
        self.assertEqual(response.status_code, 404)

    def test_silvia_accesses_stint_directly(self):
        """
        Silvia doesn't follow the directions given by the Stint's host to go to the play_most_recent url. She instead tries to
        access another running stint using a random hand id.
        """
        self.other_lab.current_stint.start(UserFactory())
        response = self.loggedin_client.get(f'{self.live_server_url}/lab/{self.random_hand.id}/')
        self.assertEqual(response.status_code, 404)


@override_settings(DEBUG=False, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestLabWebRenderDriver(EryLiveServerTestCase):
    """
    Silvia has received a link to log into a stint, hosted via lab.
    """

    def setUp(self):
        self.driver = get_chromedriver(headless=True)
        web = Frontend.objects.get(name='Web')
        stint_definition = create_test_stintdefinition(frontend=web)
        stint_specification = StintSpecificationFactory(
            stint_definition=stint_definition,
            team_size=2,
            max_team_size=2,
            min_team_size=2,
            language=Language.objects.get(pk='en'),
        )
        self.lab = LabFactory()
        self.lab.set_stint(stint_specification.id, UserFactory())
        self.lab.start(2, UserFactory())
        self.hand = self.lab.current_stint.hands.first()

    def test_silvia_logs_into_url_but_stint_isnt_active(self):
        """
        Silvia logs into the Stint at the correct url, but is the first to log in and must wait for another hand.
        """
        from ery_backend.stints.models import Stint

        self.lab.current_stint.set_status(Stint.STATUS_CHOICES.cancelled)
        self.driver.get(f'{self.live_server_url}/lab/{self.lab.secret}/1/')
        self.assertIn('Please Wait', self.driver.title)

    def test_silvia_logs_into_url_and_stint_is_active(self):
        """
        Silvia retries with the correct url and reaches the Stint's first page.
        """
        # setup environment on top of shared setUp
        block_prefix = f'{self.hand.current_module_definition.slug.lower()}-{self.hand.stage.stage_definition.name.lower()}'
        self.driver.get(f'{self.live_server_url}/lab/{self.lab.secret}/1/')

        questions_block = self.driver.find_element_by_id(f'{block_prefix}-questions')
        self.assertTrue(
            re.match(
                'This is the content for the questions block belonging to StageDefinition0' r' \(ModuleDefinition[\w]+\)',
                questions_block.get_attribute('textContent'),
            )
        )

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=False, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestStintWebRenderClient(EryLiveServerTestCase):
    """
    Karen has a link to a stint.
    """

    def setUp(self):
        web = Frontend.objects.get(name='Web')
        stint_definition = create_test_stintdefinition(frontend=web)
        stint_specification = StintSpecificationFactory(
            stint_definition=stint_definition,
            team_size=2,
            max_team_size=2,
            min_team_size=2,
            language=Language.objects.get(pk='en'),
        )
        stint = stint_specification.realize()
        self.lab = LabFactory(current_stint=stint)

        self.karen = UserFactory(username='sharingiskaren')
        self.loggedin_client = self.get_loggedin_client(self.karen)

    def test_karen_accesses_nonexistent_stint(self):
        """
        Karen enters a non-existent Stint id.
        """
        response = self.loggedin_client.get(f'{self.live_server_url}/stint/23/')
        self.assertEqual(response.status_code, 400)

    def test_karen_accesses_incorrect_url(self):
        """
        Karen enters a url for the wrong stint.
        """
        web = Frontend.objects.get(name='Web')
        stint_definition = create_test_stintdefinition(frontend=web)
        stint_specification = StintSpecificationFactory(
            stint_definition=stint_definition,
            team_size=1,
            max_team_size=1,
            min_team_size=1,
            language=Language.objects.get(pk='en'),
        )
        stint = stint_specification.realize()
        response = self.loggedin_client.get(f'{self.live_server_url}/stint/{stint.gql_id}/')
        self.assertEqual(response.status_code, 404)


@override_settings(DEBUG=False, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestStintWebRenderDriver(EryLiveServerTestCase):
    """
    Karen has a link to a stint.
    """

    def setUp(self):
        web = Frontend.objects.get(name='Web')
        self.stint_definition = create_test_stintdefinition(frontend=web)
        stint_specification = StintSpecificationFactory(
            stint_definition=self.stint_definition,
            team_size=2,
            max_team_size=2,
            min_team_size=2,
            language=Language.objects.get(pk='en'),
        )
        self.driver = self.get_loggedin_driver('sharingiskaren', headless=True)
        self.karen = User.objects.get(username='sharingiskaren')
        self.stint = stint_specification.realize()
        HandFactory(stint=self.stint, user=self.karen)

    def test_karen_accesses_url_and_stint_is_not_ready(self):
        self.driver.get(f'{self.live_server_url}/stint/{self.stint.gql_id}/')
        self.assertIn('Please Wait', self.driver.title)

    def test_karen_accesses_url_and_stint_is_ready(self):
        """
        Karen retries with the correct url and reaches the Stint's first page.
        """
        # preload additional user and start stint
        hand = HandFactory(stint=self.stint, user=UserFactory())
        stintdef_moduledef = self.stint_definition.stint_definition_module_definitions.first()
        start_stagedef = stintdef_moduledef.module_definition.start_stage
        hand.stage = start_stagedef.realize()
        hand.save()
        hand.refresh_from_db()
        self.stint.start(UserFactory())
        block_prefix = f'{start_stagedef.module_definition.slug.lower()}-{start_stagedef.name.lower()}'

        self.driver.get(f'{self.live_server_url}/stint/{self.stint.gql_id}/')
        questions_block = self.driver.find_element_by_id(f'{block_prefix}-questions')
        self.assertTrue(
            re.match(
                'This is the content for the questions block belonging to StageDefinition0' r' \(ModuleDefinition[\w]+\)',
                questions_block.get_attribute('innerHTML'),
            )
        )

    def tearDown(self):
        self.driver.close()


@override_settings(DEBUG=False, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
class TestForeignLanguages(EryLiveServerTestCase):
    """
    Karen has decided to spontaneously learn tamil and hindi, and wants to read everything in those languages because she's all
    about immersion.
    """

    def setUp(self):
        self.driver = get_chromedriver(headless=True)
        language = Language.objects.get(pk='en')
        web = Frontend.objects.get(name='Web')
        self.stint_definition = create_test_stintdefinition(frontend=web)
        self.module_definition = self.stint_definition.module_definitions.first()
        stage_template = self.module_definition.start_stage.stage_templates.get(template__frontend__name='Web')
        stint_specification = StintSpecificationFactory(
            stint_definition=self.stint_definition,
            team_size=2,
            max_team_size=2,
            min_team_size=2,
            language=Language.objects.get(pk='en'),
        )

        # tamil

        # template
        root_template = Template.objects.get(name='TestRoot', frontend__name='Web')
        root_translation = root_template.blocks.get(name='Root').translations.get(language=language)
        content_template = Template.objects.get(name='ContentTemplate', frontend__name='Web')
        root_translation.content += '<Tamil/>'
        root_translation.save()
        tamil_block = TemplateBlockFactory(template=content_template, name='Tamil')
        self.tamil = 'உங்கள் குடும்பத்தினருக்கு சொந்தமான கழிவறை உள்ளதா?'
        self.tamil_2 = 'காகம் ஜூன் மாதம் பறக்கிறது'
        TemplateBlockTranslationFactory(template_block=tamil_block, content=self.tamil, language=language)

        widget = WidgetFactory(
            name='ModuleDefinitionWidget',
            code="""
<div>
    {(function(props){
        let children = [];
        const choices = getChoices(props);
        for (let i = 0; i < choices.length; i++){
            children.push(<div>{choices[i].caption}</div>);
        }
        return <div>{children}</div>;
    })(this.props) }
</div>""",
            frontend=Frontend.objects.get(name='Web'),
        )

        # module_definition_widget (through stage template block)
        module_definition_widget_1 = ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=widget)
        widget_choice_1 = WidgetChoiceFactory(widget=module_definition_widget_1, order=1)
        WidgetChoiceTranslationFactory(language=language, widget_choice=widget_choice_1, caption=self.tamil_2)

        # hindi

        # template
        self.hindi = 'क्या आपके घर में शौचालय है?'
        self.hindi_2 = 'कौवा एक पेड़ हिट करता है'
        root_translation.content += '<Hindi/>'
        root_translation.save()
        hindi_block = TemplateBlockFactory(template=content_template, name='Hindi')
        TemplateBlockTranslationFactory(template_block=hindi_block, language=language, content=self.hindi)

        # module_definition_widget (through stage template block)
        module_definition_widget_2 = ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=widget)
        widget_choice_2 = WidgetChoiceFactory(widget=module_definition_widget_2, order=1)
        WidgetChoiceTranslationFactory(language=language, widget_choice=widget_choice_2, caption=self.hindi_2)

        root_translation.content += '<ModuleDefinitionWidgets/>'
        root_translation.save()
        module_definition_widgets_block = StageTemplateBlockFactory(
            name='ModuleDefinitionWidgets', stage_template=stage_template
        )
        StageTemplateBlockTranslationFactory(
            stage_template_block=module_definition_widgets_block,
            language=language,
            content=f'<Widget.{module_definition_widget_1.name}/>' f'<Widget.{module_definition_widget_2.name}/>',
            frontend=Frontend.objects.get(name='Web'),
        )
        self.driver = self.get_loggedin_driver('sharingisstillkaren', headless=True)
        self.karen = User.objects.get(username='sharingisstillkaren')
        self.stint = stint_specification.realize()
        HandFactory(stint=self.stint, user=self.karen)
        HandFactory(stint=self.stint, user=UserFactory())
        self.stint.start(UserFactory())

    def test_karen_sees_all_the_languages(self):
        block_prefix = f'{self.module_definition.slug.lower()}-{self.module_definition.start_stage.name.lower()}'
        self.driver.get(f'{self.live_server_url}/stint/{self.stint.gql_id}/')
        # Karen fails to read the successfully rendered tamil from template block on her screen
        tamil_block = self.driver.find_element_by_id(f'{block_prefix}-tamil')
        self.assertEqual(tamil_block.get_attribute('textContent'), self.tamil)

        # Karen sort of reads the successfully  rendered hindi from template block on her screen
        hindi_block = self.driver.find_element_by_id(f'{block_prefix}-hindi')
        self.assertEqual(hindi_block.get_attribute('textContent'), self.hindi)

        # Karen recognizes a module_definition_widget in tamil and another in hindi
        module_definition_widgets_block = self.driver.find_element_by_id(f'{block_prefix}-moduledefinitionwidgets')

        self.assertIn(self.tamil_2, module_definition_widgets_block.get_attribute('innerHTML'))
        self.assertIn(self.hindi_2, module_definition_widgets_block.get_attribute('innerHTML'))

    def tearDown(self):
        self.driver.close()
