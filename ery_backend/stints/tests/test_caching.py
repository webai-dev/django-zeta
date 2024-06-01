import unittest

from ery_backend.base.cache import cache
from ery_backend.base.testcases import EryTestCase

from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.widget_factories import ModuleDefinitionWidgetFactory, ModuleEventFactory
from ery_backend.roles.utils import has_privilege
from ery_backend.stages.factories import (
    StageDefinitionFactory,
    StageTemplateFactory,
    StageTemplateBlockFactory,
    StageTemplateBlockTranslationFactory,
)
from ery_backend.stints.factories import StintDefinitionFactory
from ery_backend.stints.models import StintDefinitionModuleDefinition
from ery_backend.themes.factories import ThemeFactory, ThemePaletteFactory
from ery_backend.templates.factories import (
    TemplateWidgetFactory,
    TemplateFactory,
    TemplateBlockFactory,
    TemplateBlockTranslationFactory,
)
from ery_backend.users.factories import UserFactory
from ery_backend.widgets.factories import WidgetFactory, WidgetEventFactory


@unittest.skip('Address in issue #710')
class TestWidgetRelatedCacheInvalidation(EryTestCase):
    """
    Confirm related models are invalidate as expected on add, update, delete.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.user = UserFactory()
        cls.sd = StintDefinitionFactory()
        cls.module_definition = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=cls.sd, module_definition=cls.module_definition)

    def setUp(self):
        self.widget = WidgetFactory()
        # add tag to cache
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_md_connect(self):
        ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=self.widget)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_save(self):
        ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=self.widget)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        self.widget.save()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_delete(self):
        ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=self.widget)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        self.widget.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_template_connect(self):
        stage_definition = StageDefinitionFactory(module_definition=self.module_definition)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        TemplateWidgetFactory(template=stage_template.template, widget=self.widget)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_widgetevent_connect(self):
        stage_definition = StageDefinitionFactory(module_definition=self.module_definition)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        TemplateWidgetFactory(template=stage_template.template, widget=self.widget)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        WidgetEventFactory(widget=self.widget)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_widgetevent_delete(self):
        stage_definition = StageDefinitionFactory(module_definition=self.module_definition)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        TemplateWidgetFactory(template=stage_template.template, widget=self.widget)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        event = WidgetEventFactory(widget=self.widget)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        event.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_moduleevent_connect(self):
        widget = ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=self.widget)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        ModuleEventFactory(widget=widget)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_moduleevent_delete(self):
        widget = ModuleDefinitionWidgetFactory(module_definition=self.module_definition, widget=self.widget)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        event = ModuleEventFactory(widget=widget)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        event.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))


@unittest.skip('Address in issue #710')
class TestModuleRelatedCacheInvalidation(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.user = UserFactory()

    def setUp(self):
        self.sd = StintDefinitionFactory()
        # add tag to cache
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_md_connect(self):
        md = ModuleDefinitionFactory()
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_md_save(self):
        md = ModuleDefinitionFactory()
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        md.save()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_md_delete(self):
        md = ModuleDefinitionFactory()
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        md.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_stagedefinition_connect(self):
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        StageDefinitionFactory(module_definition=md)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_stagedefinition_delete(self):
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        stage_definition.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_stagetemplate_connect(self):
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        StageTemplateFactory(stage_definition=stage_definition)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_stagetemplate_delete(self):
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        stage_template.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_stagetemplateblock_connect(self):
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        StageTemplateBlockFactory(stage_template=stage_template)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_stagetemplateblock_delete(self):
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        stb = StageTemplateBlockFactory(stage_template=stage_template)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        stb.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_stagetemplateblocktranslation_connect(self):
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        stb = StageTemplateBlockFactory(stage_template=stage_template)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        StageTemplateBlockTranslationFactory(stage_template_block=stb)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_stagetemplateblocktranslation_delete(self):
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md)
        stage_template = StageTemplateFactory(stage_definition=stage_definition)
        stb = StageTemplateBlockFactory(stage_template=stage_template)
        stb_translation = StageTemplateBlockTranslationFactory(stage_template_block=stb)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        stb_translation.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))


@unittest.skip('Address in issue #710')
class TestTemplateRelatedCacheInvalidation(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.user = UserFactory()

    def setUp(self):
        self.sd = StintDefinitionFactory()
        # add tag to cache
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        self.stage_definition = StageDefinitionFactory(module_definition=md)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_template_connect(self):
        StageTemplateFactory(stage_definition=self.stage_definition)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_template_delete(self):
        stage_template = StageTemplateFactory(stage_definition=self.stage_definition)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        stage_template.template.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_ancestraltemplate_save(self):
        stage_template = StageTemplateFactory(stage_definition=self.stage_definition)
        connection = stage_template.template
        parent = TemplateFactory()
        connection.parental_template = parent
        connection.save()
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        # Parent
        parent.save()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))
        # Ancestor
        ancestor = TemplateFactory()
        parent.parental_template = ancestor
        parent.save()
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        ancestor.save()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_ancestraltemplate_delete(self):
        stage_template = StageTemplateFactory(stage_definition=self.stage_definition)
        connection = stage_template.template
        parent = TemplateFactory()
        connection.parental_template = parent
        connection.save()
        ancestor = TemplateFactory()
        parent.parental_template = ancestor
        parent.save()
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        ancestor.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_ancestraltemplateblock_connect(self):
        stage_template = StageTemplateFactory(stage_definition=self.stage_definition)
        connection = stage_template.template
        parent = TemplateFactory()
        connection.parental_template = parent
        connection.save()
        ancestor = TemplateFactory()
        parent.parental_template = ancestor
        parent.save()
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        TemplateBlockFactory(template=ancestor)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_ancestraltemplateblock_delete(self):
        stage_template = StageTemplateFactory(stage_definition=self.stage_definition)
        connection = stage_template.template
        parent = TemplateFactory()
        connection.parental_template = parent
        connection.save()
        ancestor = TemplateFactory()
        parent.parental_template = ancestor
        parent.save()
        template_block = TemplateBlockFactory(template=ancestor)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        template_block.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_templateblocktranslation_connect(self):
        stage_template = StageTemplateFactory(stage_definition=self.stage_definition)
        connection = stage_template.template
        parent = TemplateFactory()
        connection.parental_template = parent
        connection.save()
        template_block = TemplateBlockFactory(template=parent)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        TemplateBlockTranslationFactory(template_block=template_block)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_templateblocktranslation_delete(self):
        stage_template = StageTemplateFactory(stage_definition=self.stage_definition)
        connection = stage_template.template
        parent = TemplateFactory()
        connection.parental_template = parent
        connection.save()
        template_block = TemplateBlockFactory(template=parent)
        tb_translation = TemplateBlockTranslationFactory(template_block=template_block)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        tb_translation.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))


@unittest.skip('Address in issue #710')
class TestThemeRelatedCacheInvalidation(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.user = UserFactory()

    def setUp(self):
        self.sd = StintDefinitionFactory()
        # add tag to cache
        md = ModuleDefinitionFactory()
        StintDefinitionModuleDefinition.objects.create(stint_definition=self.sd, module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md)
        self.stage_template = StageTemplateFactory(stage_definition=stage_definition)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_theme_save(self):
        theme = ThemeFactory()
        self.stage_template.theme = theme
        self.stage_template.save()
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        theme.save()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_theme_delete(self):
        theme = ThemeFactory()
        self.stage_template.theme = theme
        self.stage_template.save()
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        theme.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_themepalette_connect(self):
        theme = ThemeFactory()
        self.stage_template.theme = theme
        self.stage_template.save()
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        ThemePaletteFactory(theme=theme)
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))

    def test_sd_invalidated_on_themepalette_delete(self):
        theme = ThemeFactory()
        self.stage_template.theme = theme
        self.stage_template.save()
        td = ThemePaletteFactory(theme=theme)
        has_privilege(self.sd, self.user, 'create')
        self.assertIn(self.sd.get_cache_tag(), cache.keys('*'))
        td.delete()
        self.assertNotIn(self.sd.get_cache_tag(), cache.keys('*'))
