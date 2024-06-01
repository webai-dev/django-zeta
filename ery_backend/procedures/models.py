from django.contrib.postgres.fields import JSONField
from django.db import models

from ery_backend.base.mixins import JavascriptNamedMixin, JavascriptArgumentNamedMixin
from ery_backend.base.models import EryFile, EryNamedPrivileged


class Procedure(JavascriptNamedMixin, EryFile):
    """
    Definition of Javascript function to be evaluated server-side or
    prepended to client-side code.
    """

    class SerializerMeta(EryFile.SerializerMeta):
        model_serializer_fields = ('arguments',)

    code = models.TextField()

    @property
    def js_name(self):
        return f"__ery_procedure_{self.slug.replace('-', '_')}"

    def evaluate(self, hand):
        """
        Evaluate code server-side in ery_engine.
        """
        from ery_backend.scripts.engine_client import evaluate_without_side_effects

        return evaluate_without_side_effects(self.js_name, self.code, hand)

    def generate_js_function(self, target='engine'):
        """
        Build Javascript function from code attribute.
        """

        def _get_jstyped_default(default):
            """
            Converts bools from python type to js type for engine.
            """
            if isinstance(default, bool):
                return str(default).lower()
            return default

        def _prepend_defaults():
            """
            This method is used due to lack of support for optional parameters in ES5.
            """
            prepend_text = ''
            for arg in self.arguments.filter(default__isnull=False).all():
                prefix = (
                    f'if (typeof {arg.name} === \'undefined\'){{' f' {arg.name} = {_get_jstyped_default(arg.default)}}};\n'
                )
                prepend_text += prefix
            return prepend_text

        def _get_args():
            args = list()
            for arg in self.arguments.all():
                args.append(arg.name)
            return ', '.join(args)

        args = _get_args()
        if target == 'engine':
            return f'function ({args}){{ {_prepend_defaults()} return {self.code} }};'
        # XXX: May be readded in later issue #270
        # elif target == 'babel':
        #     return f'{self.name}({args}){{{_prepend_defaults()} return {self.code}}};'
        return NotImplementedError(f"No handling present for target: {target}")


class ProcedureArgument(JavascriptArgumentNamedMixin, EryNamedPrivileged):
    """
    Argument belonging to parental Javascript function.
    """

    class Meta(EryNamedPrivileged.Meta):
        ordering = ('order',)
        unique_together = (('procedure', 'order'), ('procedure', 'name'))

    parent_field = 'procedure'
    procedure = models.ForeignKey(
        'procedures.Procedure', on_delete=models.CASCADE, help_text="Parental instance", related_name='arguments'
    )
    order = models.PositiveIntegerField(
        default=0, help_text="Order of arguments in :class:`~ery_backend.procedures.models.Procedure` call"
    )
    default = JSONField(null=True, blank=True, help_text="Default value for argument")
