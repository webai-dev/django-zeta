from django.db import models

from ery_backend.base.models import EryNamedSlugged


class Frontend(EryNamedSlugged):
    pass


class SMSStage(models.Model):
    stage = models.OneToOneField('stages.Stage', on_delete=models.CASCADE)
    send = models.IntegerField(default=0)
    replayed = models.IntegerField(default=0)
    faulty_inputs = models.IntegerField(default=0)

    def get_sms_widgets(self, hand):
        """
        Search related content for :class:`~ery_backend.modules.models.ModuleDefinitionWidget`
        or :class:`~ery_backend.templates.models.TemplateWidget`.

        Returns:
            Union[:class:`~ery_backend.modules.models.ModuleDefinitionWidget`,
              :class:`~ery_backend.templates.models.TemplateWidget`]: First found instance. Otherwise, returns False.
              False is used instead of None for caching.
        """
        from .sms_utils import SMSStageTemplateRenderer
        from ery_backend.stages.models import StageTemplate

        result = None
        stage_template = StageTemplate.objects.get(
            stage_definition=self.stage.stage_definition, template__frontend__name='SMS'
        )
        widgets = SMSStageTemplateRenderer(stage_template, hand).get_sms_widgets()
        if widgets:
            result = widgets.values()
        return result
