from django.db import models


class KeywordMixin(models.Model):
    """
    Adds field for index :class:`~ery_backend.keywords.models.Keyword` instances.
    """

    class Meta:
        abstract = True

    keywords = models.ManyToManyField(
        'keywords.Keyword',
        blank=True,
        related_name='+',
        help_text=":class:`~ery_backend.keywords.models.Keyword` objects for indexing.",
    )
