from django.db import models

from ery_backend.base.models import EryModel


class NewsItem(EryModel):
    class Meta(EryModel.Meta):
        ordering = ('-created',)

    title = models.CharField(max_length=255)
    content = models.TextField()

    def __str__(self):
        return f"{self.title} ({self.created})"
