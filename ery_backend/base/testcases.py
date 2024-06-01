import datetime as dt
import logging
import os
import random

import django
from django.core.exceptions import ObjectDoesNotExist
from django.test import TransactionTestCase, LiveServerTestCase
from django.utils.crypto import get_random_string

from channels.http import AsgiRequest
from channels.testing import ChannelsLiveServerTestCase
from graphene.test import Client as GQLClient

import factory
from languages_plus.models import Language
import reversion
from seleniumwire import webdriver
from test_plus.test import TestCase

from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.procedures.factories import ProcedureFactory, ProcedureArgumentFactory
from ery_backend.roles.models import Role
from ery_backend.stages.models import StageTemplateBlock
from ery_backend.stints.models import StintDefinitionModuleDefinition
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.templates.models import TemplateBlock
from ery_backend.users.factories import UserFactory
from ery_backend.users.models import User
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.models import Widget

from .middleware import DataLoaderMiddleware
from .utils import get_gql_id, get_default_language, get_loggedin_client

logger = logging.getLogger(__name__)


def get_chromedriver(headless=False):
    """
    Returns:
        An (optionally headless) instance of Google Chrome webdriver.
    """
    if headless:
        from pyvirtualdisplay import Display

        display = Display(visible=0, size=(800, 600))
        display.start()

    return webdriver.Chrome(f'{os.getcwd()}/drivers/chromedriver')


def create_revisions(objs_info, revision_n, squash=False, user=None):
    """
    Create revision(s) for an object or set of objects.

    Revisions can either be done individually for each object or for the entire group of objects.

    Args:
        objs_info (List[Dict[str: Union[obj, str]]): Contains dictionaries specifying object ('obj') to revise and
          attribute ('attr') of said obj to revise. For example [{'obj': action, 'attr': 'comment'}], specifies to change
          the comment attribute of object, action during revisions..

        revision_n (int): Number of revisions to make.
        squash (bool): Whether to make revisions per object or per group of objects.
        user (:class:`~ery_backend.users.models.User`): Saved as the initiator of each :class:`reversion.models.Revision`.
    """

    def _revise(obj_info, i):
        obj = obj_info['obj']
        attr = obj_info['attr']
        # pylint:disable=protected-access
        field_type = obj._meta.get_field(attr).get_internal_type()
        if isinstance(obj, (TemplateBlock, StageTemplateBlock)):
            if not attr == 'name':
                raise ValueError('Test revisions should be specified on name for (Stage)TemplateBlocks')
            val = f"{obj.__class__.__name__}ChangeRevision" f"{get_random_string(allowed_chars='abcdefghijklmnopqrstuvwxyz')}"
        else:
            if field_type in ['CharField', 'TextField']:
                val = get_random_string()
            else:
                raise Exception(f"Encountered unexpected datatype: '{field_type}'' for attr '{attr}'")
        setattr(obj, attr, val)
        obj_info['obj'].save()

    for i in range(revision_n):
        if squash:
            with reversion.create_revision():
                for obj_info in objs_info:
                    _revise(obj_info, i)
                if user:
                    reversion.set_user(user)
        else:
            for obj_info in objs_info:
                with reversion.create_revision():
                    _revise(obj_info, i)
                    if user:
                        reversion.set_user(user)


def create_base_stagedefinition(frontend, name=None, module_definition=None):
    """
    Gets minimal environment needed to perform :py:meth:`~ery_backend.stages.models.Stage.render`.

    Args:
        - frontend (:class:`~ery_backend.frontends.models.Frontend`)
        - name (Optional[str]): Used for instance creation.
        - module_definition (Optional[:class:`~ery_backend.modules.models.ModuleDefinition`]): Use for instance creation.

    Returns:
        :class:`~ery_backend.stages.models.StageDefinition` connected to
        :class:`~ery_backend.templates.models.Template` with root
        :class:`~ery_backend.templates.models.TemplateBlock` and
        :class:`~ery_backend.stages.models.StageTemplateBlock`.
    """
    from ery_backend.stages.factories import StageDefinitionFactory, StageTemplateFactory
    from ery_backend.templates.factories import TemplateFactory, TemplateBlockFactory, TemplateBlockTranslationFactory

    kwargs = {'module_definition__primary_language': Language.objects.get(pk='en'), 'redirect_on_submit': True}
    if name:
        kwargs['name'] = name
    if module_definition:
        kwargs['module_definition'] = module_definition
    stage_definition = StageDefinitionFactory(**kwargs)
    root_template = TemplateFactory(frontend=frontend, name='TestRoot')
    root_template_block = TemplateBlockFactory(template=root_template, name='Root')
    language = stage_definition.module_definition.primary_language
    root_template_block.save()
    TemplateBlockTranslationFactory(template_block=root_template_block, language=language, content='<Content/><Footer/>\n')
    content_template = TemplateFactory(parental_template=root_template, name='ContentTemplate', frontend=frontend)
    content_template_block = TemplateBlockFactory(template=content_template, name='Content')
    footer_template_block = TemplateBlockFactory(template=content_template, name='Footer')
    TemplateBlockTranslationFactory(template_block=footer_template_block, language=language, content=f"")

    TemplateBlockTranslationFactory(
        template_block=content_template_block, language=language, content=f"<Questions/>\n<Answers/>"
    )
    questions_template_block = TemplateBlockFactory(template=content_template, name='Questions')
    tbt_1 = TemplateBlockTranslationFactory(
        template_block=questions_template_block,
        language=language,
        content=f"This is the content for the questions block belonging to {stage_definition.name}"
        f" ({stage_definition.module_definition.name}).",
    )
    if frontend.name == 'Web':
        web_prefix = f'<div id="{stage_definition.module_definition.slug.lower()}-{stage_definition.name.lower()}-questions">'
        tbt_1.content = f'{web_prefix}{tbt_1.content}</div>'
        tbt_1.save()
    answers_template_block = TemplateBlockFactory(template=content_template, name='Answers')
    tbt_2 = TemplateBlockTranslationFactory(
        template_block=answers_template_block,
        language=language,
        content=f"This is the content for the answers block belonging to {stage_definition.name}"
        f" ({stage_definition.module_definition.name}).",
    )
    if frontend.name == 'Web':
        web_prefix = f'<div id="{stage_definition.module_definition.slug.lower()}-{stage_definition.name.lower()}-answers">'
        tbt_2.content = f'{web_prefix}{tbt_2.content}</div>'
        tbt_2.save()
    StageTemplateFactory(
        stage_definition=stage_definition, template=TemplateFactory(frontend=frontend, parental_template=content_template)
    )
    return stage_definition


def create_complex_stagedefinition(frontend, include=None, name=None, module_definition=None):
    """
    Gets minimal environment (see :py:attr:`add_base_stagedefinition`) with additional renderable components.

    Args:
        - frontend (:class:`~ery_backend.frontends.models.Frontend`)
        - include (Optional[List['str']]): Additional models to be rendered. See notes.
        - name (Optional[str]): Used for instance creation.
        - module_definition (Optional[:class:`~ery_backend.modules.models.ModuleDefinition`]): Use for instance creation.

    Notes:
        - All additional components created via include are given a name (matching the available arg), which is given \
        a tag in the root block to allow for render.

    Additional components that may be created via include args:
        - procedure
        - module_definition_widget
        - variable

    Returns:
        :class:`~ery_backend.stages.models.StageDefinition`
    """
    from ery_backend.modules.factories import (
        ModuleDefinitionProcedureFactory,
        ModuleDefinitionWidgetFactory,
        WidgetChoiceFactory,
        WidgetChoiceTranslationFactory,
    )
    from ery_backend.modules.models import ModuleDefinitionWidget
    from ery_backend.templates.factories import TemplateBlockFactory, TemplateBlockTranslationFactory
    from ery_backend.stages.factories import StageTemplateBlockFactory, StageTemplateBlockTranslationFactory

    stage_definition = create_base_stagedefinition(frontend, name=name, module_definition=module_definition)
    language = stage_definition.module_definition.primary_language
    stage_template = stage_definition.stage_templates.get(template__frontend__name=frontend.name)
    # Add to tags of root block
    root_block = stage_template.template.parental_template.parental_template.blocks.get(name='Root')
    root_translation = root_block.translations.get(language__pk='en')
    content_template = root_block.template.child_templates.get(name='ContentTemplate')

    if isinstance(include, list):
        if 'procedure' in include:
            procedure = ProcedureFactory(name='add', code='x+y')
            ModuleDefinitionProcedureFactory(
                procedure=procedure, name='addalias', module_definition=stage_definition.module_definition
            )
            ProcedureArgumentFactory(procedure=procedure, name='x', order=0, default=1)
            ProcedureArgumentFactory(procedure=procedure, name='y', order=1, default=2)
            root_translation.content += '<Procedure/>\n'
            root_translation.save()
            procedure_template_block = TemplateBlockFactory(template=content_template, name='Procedure')
            TemplateBlockTranslationFactory(
                template_block=procedure_template_block,
                language=language,
                content=f"This is the content for the procedure block of stage {stage_definition.name} from"
                f" module_definition {module_definition.name}: {{{{addalias(2, 3)}}}}",
            )

        if 'module_definition_widget' in include:
            widget = Widget.objects.get(slug='webemptywidget-uJIkXXbk')
            # XXX: Change back on issue #379
            if frontend.name == 'Web':
                widget = Widget.objects.get(slug='webmultiplechoicewidget-ujIkXxBK')
            elif frontend.name == 'SMS':
                widget = Widget.objects.get(slug='smsmultiplechoicecaptionvaluewidget-ujIkXxBK')
            module_definition_widget_1_vd = VariableDefinitionFactory(
                data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
                module_definition=stage_definition.module_definition,
                scope=VariableDefinition.SCOPE_CHOICES.hand,
            )
            module_definition_widget_1 = ModuleDefinitionWidgetFactory(
                module_definition=stage_definition.module_definition,
                widget=widget,
                variable_definition=module_definition_widget_1_vd,
                random_mode=ModuleDefinitionWidget.RANDOM_CHOICES.asc,
            )
            for i in range(2):
                widget_choice = WidgetChoiceFactory(widget=module_definition_widget_1, order=i)
                WidgetChoiceTranslationFactory(
                    widget_choice=widget_choice,
                    language=language,
                    caption=f"Sample text for module_definition_widget {module_definition_widget_1.name} choice {i+1} of stage"
                    f" {stage_definition.name} from"
                    f" module_definition {module_definition.name}",
                )

            root_translation.content += '<ModuleDefinitionWidgets/>\n'
            root_translation.save()
            module_definition_widget_template_block = StageTemplateBlockFactory(
                stage_template=stage_template, name='ModuleDefinitionWidgets'
            )
            StageTemplateBlockTranslationFactory(
                stage_template_block=module_definition_widget_template_block,
                frontend=frontend,
                language=language,
                content=f"<{module_definition_widget_1.name}/>",
            )

        if 'variable' in include:
            if frontend.name == 'Web':
                variable_call = '{myname}'
            else:
                variable_call = '{{myname}}'
            VariableDefinitionFactory(
                module_definition=stage_definition.module_definition,
                scope=VariableDefinition.SCOPE_CHOICES.hand,
                name='myname',
                data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
                default_value='eraeraslimshady',
            )
            root_translation.content += '<Variable/>\n'
            root_translation.save()
            variable_template_block = StageTemplateBlockFactory(stage_template=stage_template, name='Variable')
            StageTemplateBlockTranslationFactory(
                stage_template_block=variable_template_block,
                language=language,
                frontend=frontend,
                content=f"<div id='variable'>This is the content for the variable block of {stage_definition.name} from"
                f" module_definition {module_definition.name}: My name is...{variable_call}</div>",
            )

    return stage_definition


def create_test_stintdefinition(frontend, render_args=None, module_definition_n=1, stage_n=1, redirects=False):
    """
    Creates:class:`~ery_backend.stints.models.StintDefinition` attached to a
    :class:`~ery_backend.modules.models.ModuleDefinition` with start
    :class:`~ery_backend.stages.models.StageDefinition` (see :py:meth:`create_test_stage`)
    and start :class:`~ery_backend.syncs.models.Era`.

    Args:
        - frontend (:class:`~ery_backend.frontends.models.Frontend`).
        - render_args (Optional[List[str]]): Example components added per stage (see below).
        - module_definition_n (int): Number of :class:`~ery_backend.modules.models.ModuleDefinition` instances
          per :class:`~ery_backend.stints.models.StintDefinition`.
        - stage_n (int): Number of :class:`~ery_backend.stages.models.StageDefinition` instances per
          :class:`~ery_backend.modules.models.ModuleDefinition`.
        - redirects (bool): Whether to create a linear flow of :class:`~ery_backend.stages.models.Redirect` objects
           between :class:`~ery_backend.stages.models.StageDefinition` instances.

    Notes:
        - Additional components that may be created via render_args:
          1) procedure
          2) module_definition_widget
          3) variable

    Returns:
        :class:`~ery_backend.stints.models.StintDefinition`
    """
    from ery_backend.modules.factories import ModuleDefinitionFactory
    from ery_backend.stages.factories import RedirectFactory
    from ery_backend.stints.factories import StintDefinitionFactory
    from ery_backend.syncs.factories import EraFactory

    stint_definition = StintDefinitionFactory()
    order_counter = 0  # for through model creation
    module_definitions = [
        ModuleDefinitionFactory(primary_language=get_default_language(), primary_frontend=frontend)
        for _ in range(module_definition_n)
    ]
    stage_definition_map = {}
    for module_definition in module_definitions:
        if render_args:
            stage_definitions = [
                create_complex_stagedefinition(
                    frontend, render_args, module_definition=module_definition, name=f"StageDefinition{i}"
                )
                for i in range(stage_n)
            ]
        else:
            stage_definitions = [
                create_base_stagedefinition(frontend, module_definition=module_definition, name=f"StageDefinition{i}")
                for i in range(stage_n)
            ]
        module_definition.start_stage = stage_definitions[0]
        if module_definition.start_era:
            raise Exception("Autogeneration fixed. Update this code")
        module_definition.start_era = EraFactory(module_definition=module_definition)
        module_definition.save()
        StintDefinitionModuleDefinition.objects.create(
            stint_definition=stint_definition, module_definition=module_definition, order=order_counter
        )
        order_counter += 1
        stage_definition_map[module_definition.name] = stage_definitions
    for module_definition in module_definitions:
        stage_definitions = stage_definition_map[module_definition.name]
        for stage_definition in stage_definitions:
            if redirects:
                if len(stage_definitions) > 1:
                    if stage_definitions.index(stage_definition) + 1 < len(stage_definitions):
                        RedirectFactory(
                            stage_definition=stage_definition,
                            condition=None,
                            next_stage_definition=stage_definitions[stage_definitions.index(stage_definition) + 1],
                        )
                    # End stages only allowed if more than one stage. Otherwise, hand will have status set to finished
                    # on stint start.
                    if stage_definition == stage_definitions[-1]:
                        stage_definition.end_stage = True
                        stage_definition.save()
    return stint_definition


def create_test_hands(
    n=1,
    team_size=1,
    frontend_type='Web',
    render_args=None,
    module_definition_n=1,
    stage_n=1,
    late_arrival=False,
    redirects=False,
    signal_pubsub=True,
):
    """
    Creates :class:`~ery_backend.hands.models.Hand` objects connected to :class:`~ery_backend.stints.models.Stint` with a
    current :class:`~ery_backend.modules.models.Module` (see :py:meth:`create_test_stintdefinition`).

    Args:
        - n (int): Number of :class:`~ery_backend.hands.models.Hand` to create.
        - team_size (int): Set corresponding :class:`~ery_backend.stint_specifications.models.StintSpecification` attribute.
        - frontend_type (str): Name of designated :class:`~ery_backend.frontends.models.Frontend`.
        - render_args (List[str]): Example components added per stage (see below).
        - module_definition_n (int): Number of :class:`~ery_backend.modules.models.ModuleDefinition` instances
          per :class:`~ery_backend.stints.models.StintDefinition`.
        - stage_n (int): Number of :class:`~ery_backend.stages.models.StageDefinition` instances per
          :class:`~ery_backend.modules.models.ModuleDefinition`.
        - redirects (bool): Whether to create a linear flow of :class:`~ery_backend.stages.models.Redirect` objects
           between :class:`~ery_backend.stages.models.StageDefinition` instances.
        - signal_pubsub (bool): Whether to send a signal to the Robot Runner using Google Pubsub during stint.start.
    Notes:
        - Additional components that may be created via render_args:
          1) procedure
          2) module_definition_widget
          3) variable

    Returns:
        :class:`django.db.models.query.Queryset`: Contains :class:`~ery_backend.hands.models.Hand` objects belonging to
          created :class:`~ery_backend.stints.models.Stint`.
    """
    frontend_choices = ['Web', 'SMS', 'Email']
    try:
        frontend = Frontend.objects.get(name=frontend_type)
    except ObjectDoesNotExist:
        raise Exception(f"frontend_type must be in {frontend_choices}")
    if redirects and stage_n < 1:
        raise Exception("There must be more than one stage if redirects=True")
    stint_definition = create_test_stintdefinition(frontend, render_args, module_definition_n, stage_n, redirects)
    stint_specification = StintSpecificationFactory(
        stint_definition=stint_definition,
        team_size=team_size,
        min_team_size=team_size,
        max_team_size=team_size,
        late_arrival=late_arrival,
        add_languagefrontends=[{'frontend': frontend, 'language': get_default_language()}],
    )
    user = User.objects.get_or_create(username='jumpman', profile={})[0]
    stint = stint_specification.realize(user)
    for _ in range(n):
        HandFactory(user=UserFactory(profile={}), stint=stint, frontend=frontend)
    stint.start(user, signal_pubsub=False)
    return stint.hands.order_by('id')


def grant_owner_to_obj(obj, user):
    """
    Convenience method for granting ownership
    """
    from ery_backend.roles.utils import grant_role

    owner = Role.objects.get(name='owner')
    grant_role(owner, obj, user)


class EryTestCase(TestCase):
    """
    Includes all functionality of django-test-plus testcase, with 10 preloaded
    Language objects for use in testing.

    """

    fixtures = ['countries', 'frontends', 'languages', 'roles_privileges', 'templates', 'themes', 'widgets']

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        logger.info("Running %s at %s", cls, dt.datetime.now())
        super().setUpClass(*args, **kwargs)


class EryTransactionTestCase(TransactionTestCase):
    """
    Add fixtures to default django TransactionTestCase and delete all model instances on
    teardown.

    Notes:
        - Use this if you need to know the activity of a test outside of the testing-environment
          (e.g., when using a runner such as robot_runner.)

    """

    fixtures = ['languages', 'countries', 'roles_privileges', 'frontends', 'templates', 'widgets']

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        logger.info("Running %s at %s", cls, dt.datetime.now())
        super().setUpClass(*args, **kwargs)

    @classmethod
    def tearDownClass(cls, *args, **kwargs):
        model_clses = django.apps.apps.get_models()
        for model_cls in model_clses:
            model_cls.objects.all().delete()


class EryLiveServerTestCase(LiveServerTestCase):
    """
    Adds fixtures and convenience methods to all functionality of django LiveServerTestCase.

    Includes fixtures for following objects:
        * :class:`Language`: 10 instances.
        * :class:`~ery_backend.roles.models.Role`: All instances.
        * :class:`~ery_backend.roles.models.Privilege`: All instances.
        * :class:`SocialApp`: FaceBook and LinkedIn instances.

    Convenience methods included for following purposes:
        * User login
    """

    fixtures = ['languages', 'countries', 'roles_privileges', 'frontends', 'templates', 'themes', 'widgets']

    @staticmethod
    def get_loggedin_client(user):
        """
        Gets  django :class:`Client` with logged in :class:`~ery_backend.users.models.User`.

        Args:
            user (:class:`~ery_backend.users.models.User`): Logged into session and attached to returned :class:`Client`.

        Returns:
            A django :class:`Client` instance.
        """
        return get_loggedin_client(user)

    def get_loggedin_driver(self, username, headless=True, vendor=None):
        """
        Gets selenium Chrome :class:`Webdriver` with logged in :class:`ery_backend.users.models.User`.

        Args:
            username (str): Used to get_or_create and login.
            password (str): Used to login.

        Returns:
            A selenium Chrome :class:`Webdriver` instance.
        """
        user = User.objects.filter(username=username, profile={}).exclude(my_folder=None).first()
        if not user:
            user = User.objects._create_user(username, profile={})  # pylint:disable=protected-access
        password = get_random_string()
        user.set_password(password)
        user.save()
        if headless:
            driver = get_chromedriver(headless=True)
        else:
            driver = get_chromedriver()
        if vendor:
            driver.header_overrides = {'META': {'HTTP_HOST': vendor.homepage_url}}
        driver.get(f'{self.live_server_url}/admin/')
        login_field = driver.find_element_by_id('id_username')
        login_field.send_keys(username)
        password_field = driver.find_element_by_id('id_password')
        password_field.send_keys(password)
        submit = driver.find_element_by_xpath("//input[@type='submit']")
        submit.click()
        return driver


class EryChannelsTestCase(ChannelsLiveServerTestCase, EryLiveServerTestCase):
    """
    Add django channels functionality to EryLiveServerTestCase.

    Notes:
    - Allows websocket connections through urls specified in :py:meth:`~ery_backend.base.routing.websocket_urlpatterns`
    """


class EryGQLClient(GQLClient):
    @staticmethod
    def get_context(**kwargs):
        """
        Create a blank AsgiRequest (plus optional injected attributes) to be used as context.

        Args:
            - kwargs: Attributes to inject.

        Returns:
            :class:`channels.http.AsgiRequest`
        """
        request = AsgiRequest(scope={'path': 'blank'.encode('UTF-8'), 'method': 'blank'}, stream='blank'.encode('UTF-8'))
        for key, value in kwargs.items():
            setattr(request, key, value)
        return request

    def execute(self, query, context_value=None, variable_values=None):
        if not context_value:
            context_value = self.get_context()
        return super().execute(query, context_value=context_value, variable_values=variable_values)


class GQLTestCase(TestCase):
    """
    GQLTestCase provides several helpers for testing our GraphQL interface
    """

    fixtures = ['countries', 'frontends', 'languages', 'roles_privileges', 'templates', 'widgets']

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        """Set up users, roles, tokens"""

        super().setUpClass(*args, **kwargs)

        cls.no_roles = {'user': UserFactory(username='test-no-roles')}
        cls.viewer = {'user': UserFactory(username="test-viewer"), 'role': Role.objects.get(name='viewer')}
        cls.editor = {'user': UserFactory(username='test-editor'), 'role': Role.objects.get(name='editor')}
        cls.owner = {'user': UserFactory(username='test-owner'), 'role': Role.objects.get(name='owner')}

    @classmethod
    def get_gql_client(cls, schema, middleware=None):
        if not middleware:
            middleware = [DataLoaderMiddleware()]
        return EryGQLClient(schema, middleware=middleware)

    @classmethod
    def get_version_node_ids(cls, obj, user=None):
        from reversion.models import Version

        versions = Version.objects.get_for_object(obj)
        if user:
            versions = versions.filter(revision__user=user)
        version_ids = [get_gql_id('Version', version_id) for version_id in versions.values_list('id', flat=True)]
        return version_ids

    def assert_query_was_unauthorized(self, result):
        """
        Ensure that the provided :class:`graphql.execution.base.ExecutionResult` contains a "not authorized" error.
        """
        errors = result.get("errors", [])
        self.assertIn("not authorized", [e["message"] for e in errors])

    @staticmethod
    def fail_on_errors(result):
        """
        Ensure that the provided :class:`graphql.execution.base.ExecutionResult` contains no errors
        """
        if result.get("errors", None) is not None:
            message = "Query errors:\n   " + "\n   ".join(str(e) for e in result["errors"])
            raise AssertionError(message)


class ReactNamedFactoryMixin(factory.django.DjangoModelFactory):
    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        kwargs['name'] = kwargs['name'][0].upper() + kwargs['name'][1:] if len(kwargs['name']) > 1 else kwargs['name'].upper()
        return kwargs


def random_dt(exclude=None):
    """
    Randomly generate data type from :class:`~ery_backend.variables.models.VariableDefinition` DATA_TYPE_CHOICES.

    Args:
        - exclude (Optional[List[str]]): Data types to exclude from choice subset.

    Returns:
        str
    """
    if not exclude:
        exclude = [VariableDefinition.DATA_TYPE_CHOICES.stage]
    opts = [data_type for data_type, _ in VariableDefinition.DATA_TYPE_CHOICES if data_type not in exclude]
    return random.choice(opts)


def random_dt_value(data_type, module_definition=None):
    """
    Randomly generate value matching data_type from :class:`~ery_backend.variables.models.VariableDefinition`
    DATA_TYPE_CHOICES.

    Args:
        - data_type (str): Data type choice from choice subset.
        - module_definition (:class:`~ery_backend.modules.models.ModuleDefinition`): Use to generate
          :class:`~ery_backend.stages.models.StageDefinition`.

    Returns:
        Union[str, int, float, Dict, List, :class:`~ery_backend.stages.models.StageDefinition`]
    """

    def random_dict():
        output = {}
        for _ in range(random.randint(1, 10)):
            key = get_random_string(length=random.randint(1, 10))
            if key not in output:
                output[key] = get_random_string(length=random.randint(1, 10))
        return output

    value_generators = {
        VariableDefinition.DATA_TYPE_CHOICES.int: lambda: random.randint(1, 100),
        VariableDefinition.DATA_TYPE_CHOICES.choice: lambda: get_random_string(length=random.randint(1, 10)),
        VariableDefinition.DATA_TYPE_CHOICES.bool: lambda: random.choice([True, False]),
        VariableDefinition.DATA_TYPE_CHOICES.float: random.random,
        VariableDefinition.DATA_TYPE_CHOICES.str: lambda: get_random_string(length=random.randint(1, 10)),
        VariableDefinition.DATA_TYPE_CHOICES.list: lambda: [random.randint(1, 10) for _ in range(random.randint(1, 5))],
        VariableDefinition.DATA_TYPE_CHOICES.dict: random_dict,
    }
    return value_generators[data_type]()
