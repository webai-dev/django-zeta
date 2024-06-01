from rest_framework import serializers
from test_plus.test import TestCase

from ery_backend.base.testcases import EryTestCase
from ery_backend.forms.models import FormField
from ery_backend.modules.factories import ModuleFactory
from ery_backend.modules.models import ModuleDefinition
from ery_backend.roles.utils import has_privilege
from ery_backend.stints.factories import StintFactory
from ery_backend.stints.models import Stint
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.templates.factories import TemplateFactory
from ery_backend.users.factories import GroupFactory, UserFactory
from ..exceptions import EryValidationError
from ..testcases import EryTestCase


class TestSlugMixin(EryTestCase):
    def setUp(self):
        self.template = TemplateFactory()

    def test_slug_exists(self):
        self.assertIsNotNone(self.template.slug)

    def test_unique(self):
        unique_check = []
        for _ in range(1000):
            self.template.slug = None
            self.template.save()
            self.assertTrue(self.template.slug not in unique_check)
            unique_check.append(self.template.slug)


class TestGetCachedObjIdsByRoles(EryTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.group = GroupFactory()

    def test_expected_errors(self):
        # no user or group
        with self.assertRaises(EryValidationError):
            ModuleDefinition.get_ids_by_role_assignment([1])
        # user and group
        with self.assertRaises(EryValidationError):
            ModuleDefinition.get_ids_by_role_assignment([1], self.user, self.group)
        # incorrect user type
        with self.assertRaises(EryValidationError):
            ModuleDefinition.get_ids_by_role_assignment([1], self.group)
        # incorrect group type
        with self.assertRaises(EryValidationError):
            ModuleDefinition.get_ids_by_role_assignment([1], self.user, self.user)


class TestQSBoolEvaluation(EryTestCase):
    """
    Test how django querysets are evaluated by bool.
    """

    def test_eval_noobj(self):
        """
        Confirm cls.object should always be evaluated as true, since the related manager always exists. Queryset should be
        false when empty.
        """
        related = Stint.objects
        self.assertTrue(related)
        # The queryset returned by .first is empty
        self.assertFalse(related.first())
        StintFactory()
        self.assertTrue(related.first())

    def test_eval_obj(self):
        """
        Confirm instance.rel should always be  evaluated as true, since the related manager always exists. Queryset should be
        false when empty.
        """
        stint = StintFactory()
        self.assertTrue(stint.modules)
        # The queryset returned by .first is empty
        self.assertFalse(stint.modules.first())
        stint.modules.add(ModuleFactory())
        stint.refresh_from_db()
        self.assertTrue(stint.modules)

    def test_values_list_eval_noobj(self):
        """
        Confirm values list obtained via cls.object.values_list should be evaluated as false with no values and true with
        values.
        """
        qs = Stint.objects.values_list('pk', flat=True)
        self.assertFalse(qs)
        StintFactory()
        qs = Stint.objects.values_list('pk', flat=True)
        self.assertTrue(qs)

    def test_values_list_eval_obj(self):
        """
        Confirm values list obtained via instance.related.values_list should be evaluated as false with no values and true with
        values.
        """
        stint = StintFactory()
        self.assertFalse(stint.modules.values_list('pk', flat=True))
        stint.modules.add(ModuleFactory(stint=stint))
        self.assertTrue(stint.modules.values_list('pk', flat=True))


class TestCommandRenderSMSFixtures(TestCase):
    fixtures = ['languages', 'templates', 'themes', 'widgets', 'command_render_sms']

    def test_load_fixture(self):
        pass


class TestCountriesFixtures(TestCase):
    fixtures = ['countries']

    def test_load_fixture(self):
        pass


class TestBaseModuleFixture(TestCase):
    fixtures = ['languages', 'export_base_module']

    def test_load_fixture(self):
        pass


class TestBaseStintDefinitionFixture(TestCase):
    fixtures = ['languages', 'export_base_stint_definition']

    def test_load_fixture(self):
        pass


class TestFrontendFixture(TestCase):
    fixtures = ['frontends.json']

    def test_load_fixture(self):
        pass


class TestWidgetsFixture(TestCase):
    fixtures = ['languages', 'frontends', 'themes', 'templates', 'widgets']

    def test_load_fixture(self):
        pass


class TestModuleFixture(TestCase):
    fixtures = ['languages', 'export_module']

    def test_load_fixture(self):
        pass


class TestStintModuleFixture(TestCase):
    fixtures = ['languages', 'export_stint_module']

    def test_load_fixture(self):
        pass


class TestLabFixture(TestCase):
    fixtures = ['languages', 'lab']

    def test_load_fixture(self):
        pass


class TestLanguageFixture(TestCase):
    fixtures = ['languages']

    def test_load_fixture(self):
        pass


class TestRenderForeignSMSFixture(TestCase):
    fixtures = ['languages', 'renderforeignsms']

    def test_load_fixture(self):
        pass


class TestRenderSMSFixture(TestCase):
    fixtures = ['languages', 'rendersms']

    def test_load_fixture(self):
        pass


class TestRolePrivilegeFixture(TestCase):
    fixtures = ['roles_privileges']

    def test_load_fixture(self):
        pass


class TestTemplateFixture(TestCase):
    fixtures = ['languages', 'frontends', 'templates', 'themes', 'widgets']

    def test_load_fixture(self):
        pass


class TestEventModel(TestCase):
    def test_trigger_events(self):
        """
        See ery_backend.widgets.tests.test_models.TestWidget.test_trigger_events.
        """


class TestEryFile(EryTestCase):
    def setUp(self):
        self.template = TemplateFactory()
        self.user = UserFactory()

    def test_expected_attributes(self):
        self.assertFalse(self.template.published)

    def test_has_read_privilege_when_published(self):
        # dummy check
        self.assertFalse(has_privilege(self.template, self.user, 'create'))
        self.assertFalse(has_privilege(self.template, self.user, 'read'))
        self.template.published = True
        self.template.save()
        # should pass has_privilege for 'read' when published
        self.assertTrue(has_privilege(self.template, self.user, 'read'))
        # but not for other privileges
        self.assertFalse(has_privilege(self.template, self.user, 'create'))


class TestCreateSerializer(EryTestCase):
    def setUp(self):
        self.serializer = StintSpecification.get_duplication_serializer()

    def test_meta(self):
        """Confirm class has expected meta attributes"""
        self.assertEqual(self.serializer.Meta.model, StintSpecification)
        self.assertEqual(
            sorted(self.serializer.Meta.exclude), sorted(['created', 'modified', 'subject_countries', 'opt_in_code', 'id'])
        )

    def test_fk_pk_field(self):
        widget = FormField.get_duplication_serializer()().fields['widget']
        # Many is false
        self.assertIsInstance(widget, serializers.PrimaryKeyRelatedField)
        self.assertTrue(widget.required)
        self.assertFalse(widget.allow_null)

    def test_m2m_modelserializer_field(self):
        stint_spec_countries = self.serializer().get_fields()['stint_specification_countries'].child
        self.assertEqual(stint_spec_countries.__class__.__name__, 'StintSpecificationCountryDuplicationSerializer')
        self.assertFalse(stint_spec_countries.required)
        self.assertTrue(stint_spec_countries.allow_null)
        # Many is true
        self.assertIsInstance(self.serializer().get_fields()['stint_specification_countries'], serializers.ListSerializer)
