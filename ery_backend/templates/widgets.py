from django.core.exceptions import ValidationError
from django.db import models
from django.template.loader import render_to_string

from ery_backend.base.mixins import ReactNamedMixin
from ery_backend.base.models import EryNamedPrivileged


class TemplateWidget(ReactNamedMixin, EryNamedPrivileged):
    """
    Link: class:`~ery_backend.widgets.models.Widget` to :class:`~ery_backend.templates.models.Template`.

    Additionally:
        - Adds a :class:`Template` specific identifier (i.e., name) for :class:`Widget` instance.

    Attributes:
        - parent_field (str): Name of parental attribute.

    """

    class Meta:
        unique_together = (('template', 'name'),)

    parent_field = 'template'
    template = models.ForeignKey(
        'templates.Template',
        on_delete=models.CASCADE,
        help_text="Parental :class:`Template` instance",
        related_name='template_widgets',
    )
    widget = models.ForeignKey(
        'widgets.Widget',
        on_delete=models.PROTECT,
        help_text="Javascript model used to render content of :class:`TemplateWidget`",
        related_name="template_widgets",
    )

    def _invalidate_related_tags(self, history):
        self.template.invalidate_tags(history)

    def trigger_events(self, name, event_type, hand, **kwargs):
        """
        Executes all connected event objects.

        Args:
            - event_type (str): React event.
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context during execution.

        Notes:
            - All websocket targeted messages returned from events are queued and delivered in one message after all relevant
              :class:`~ery_backend.widgets.models.WidgetEvent` instances have been triggered.

        """
        socket_message_args = []
        for widget_event_obj in self.widget.events.filter(name=name, event_type=event_type).all():
            new_socket_message_args = widget_event_obj.trigger(hand)
            if new_socket_message_args:
                socket_message_args += new_socket_message_args

        return socket_message_args

    def render_web(self):
        """
        Render self-contained ES6 code for :class:`TemplateWidget`.
        """
        if self.widget.frontend.name == 'Web':
            return render_to_string("TemplateWidget.js", context={"template_widget": self,})

        if self.widget.frontend.name == 'SMS':
            return f'{self.code}'

        raise NotImplementedError(f"Method not implemented for {self.frontend}")

    def clean(self):
        super().clean()

        if self.widget.frontend != self.template.frontend:
            raise ValidationError(
                {
                    'template_widget': "TemplateWidget: {self.name}, specified a widget {self.widget.name} "
                    "which is for frontend {self.widget.frontend}, "
                    "but template {self.template} is for frontend {self.template.frontend}"
                }
            )
