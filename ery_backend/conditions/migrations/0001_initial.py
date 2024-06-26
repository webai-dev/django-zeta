# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Condition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(help_text='Name of the model instance.', max_length=512)),
                ('comment', models.TextField(blank=True, help_text='Comment documenting the purpose of this model instance.', null=True)),
                ('left_type', models.CharField(choices=[('variable', 'Variable'), ('sub_condition', 'Sub-condition'), ('expression', 'Expression')], help_text='Selection (from TYPE_CHOICES) for left side of :class:`Condition` during :py:meth:`Condition.evaluate`', max_length=100)),
                ('right_type', models.CharField(choices=[('variable', 'Variable'), ('sub_condition', 'Sub-condition'), ('expression', 'Expression')], help_text='Selection (from TYPE_CHOICES) for right side of :class:`Condition` during :py:meth:`Condition.evaluate`', max_length=100)),
                ('left_expression', models.TextField(blank=True, help_text='Javascript to be executed for left side of :class:`Condition` based on a :class:`~ery_backend.hands.models.Hand` or :class:`~ery_backend.teams.models.Team` context during py:meth:`Condition.evaluate`', null=True)),
                ('right_expression', models.TextField(blank=True, help_text='Javascript to be executed for right side of :class:`Condition` based on a :class:`~ery_backend.hands.models.Hand` or :class:`~ery_backend.teams.models.Team` context during py:meth:`Condition.evaluate`', null=True)),
                ('relation', models.CharField(blank=True, choices=[('equal', '=='), ('not_equal', '!='), ('less', '<'), ('greater', '>'), ('less_or_equal', '<='), ('greater_or_equal', '>=')], default='equal', help_text='Selection (from RELATION_CHOICES) to be used for comparing left/right expression or :class:`~ery_backend.variables.models.VariableDefinition` values during :py:meth:`Condition.evaluate`', max_length=100, null=True)),
                ('operator', models.CharField(blank=True, choices=[('op_and', '&&'), ('op_or', '||'), ('op_exclusive_or', '^')], help_text='Selection (from BINARY_OPERATOR_CHOICES) to be used for comparing sub :class:`Condition` values with any other type (from TYPE_CHOICES) during :py:meth:`Condition.evaluate`', max_length=100, null=True)),
                ('left_sub_condition', models.ForeignKey(blank=True, help_text=':class:`Condition` for left side of current instance from which to obtain value (via :py:meth:`Condition.evaluate`) based on :class:`~ery_backend.hands.models.Hand` or :class:`~ery_backend.teams.models.Team`', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='conditions.Condition')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
