import re

from django.core.exceptions import ValidationError
from django.db import models

from languages_plus.models import Language

from ery_backend.base.exceptions import EryValueError
from ery_backend.base.models import EryFile, EryPrivileged


class ValidatorTranslation(EryPrivileged):
    class Meta(EryPrivileged.Meta):
        unique_together = (('validator', 'language'),)

    validator = models.ForeignKey('validators.Validator', on_delete=models.CASCADE, related_name='translations')
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    error_message = models.CharField(
        max_length=255, blank=True, null=True, help_text="Error string that will be evaluated with.format(value)"
    )

    def get_error_message(self, value):
        return self.error_message.format(value)


class Validator(EryFile):
    """
    A validator runs a validation of a'value' argument (obtained from associated Variable/ModuleDefinitionWidget)
    as it is passed to its method self.validate(value).

    Notes:
        - A validator either has its 'code' or 'regex' attribute configured, but not both.
        - If 'code' is set the 'validate'-method will only return 'true' if the JS script in 'code' sets \
          its JS variable 'valid' to the boolean value True. The JS script will have the 'value' passed in \
          to the 'validate'-method available in its context under the JS variable name 'value'.
        - If 'regex' is set a regex match runs on the expression specified in the attribute regex.

    """

    class SerializerMeta(EryFile.SerializerMeta):
        model_serializer_fields = ('translations',)

    code = models.TextField(null=True, blank=True)  # XXX: Implement in issue #64
    regex = models.TextField(null=True, blank=True)
    nullable = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if not self.code and not self.regex:
            raise ValidationError(
                {'code': "Only one attribute of both code and regex can be null for validator: {}.".format(self)}
            )
        if self.regex:
            if self.code:
                raise ValidationError(
                    {'code': "Only one attribute of both code and regex may have a value for validator: {}.".format(self)}
                )
            try:
                re.compile(self.regex)
            except re.error as e:
                raise ValidationError({'code': e.msg})

    def validate(self, value, obj):
        if value is None and not self.nullable:
            if not self.nullable and value is None:
                raise EryValueError(f"{obj}, has a non-nullable validator. Therefore," " it cannot have a null value.")

        if value is not None and self.regex:
            if not re.search(self.regex, str(value)):
                raise EryValueError(
                    f"Value: '{value}', does not contain match to {obj}'s validator's required regex:" f" {self.regex}"
                )

        if self.code:
            pass

        return True

    def get_error_message(self, language, value):
        try:
            return self.translations.get(language=language).get_error_message()
        except ValidatorTranslation.DoesNotExist:
            return f"Error: No error message for validator {self.name} and translation {language}."
