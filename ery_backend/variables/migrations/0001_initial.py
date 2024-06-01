# Generated by Django 2.2.11 on 2020-04-29 21:25

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('languages_plus', '0004_auto_20171214_0004'),
        ('teams', '0001_initial'),
        ('validators', '0001_initial'),
        ('modules', '0002_auto_20200429_2125'),
        ('stints', '0001_initial'),
        ('hands', '0004_auto_20200429_2125'),
    ]

    operations = [
        migrations.CreateModel(
            name='VariableDefinition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('slug', models.CharField(max_length=621, unique=True)),
                ('name', models.CharField(help_text='Name of the model instance.', max_length=512)),
                ('comment', models.TextField(blank=True, help_text='Comment documenting the purpose of this model instance.', null=True)),
                ('scope', models.CharField(choices=[('hand', 'Hand-wide'), ('team', 'Team-wide'), ('module', 'Module-wide')], default='hand', max_length=255)),
                ('data_type', models.CharField(choices=[('int', 'Integer'), ('float', 'Real number'), ('choice', 'Choice'), ('str', 'String'), ('list', 'List'), ('dict', 'Dictionary'), ('bool', 'Boolean'), ('stage', 'Stage')], default='int', max_length=255)),
                ('default_value', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('specifiable', models.BooleanField(default=False)),
                ('is_payoff', models.BooleanField(default=False)),
                ('is_output_data', models.BooleanField(default=False)),
                ('monitored', models.BooleanField(default=False, help_text='Determine whether adminstrative :class:`~ery_backend.users.models.User` may view the value of the given instance.')),
                ('module_definition', models.ForeignKey(help_text='Parent :class:`~ery_backend.modules.models.ModuleDefinition`', on_delete=django.db.models.deletion.CASCADE, to='modules.ModuleDefinition')),
                ('validator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='validators.Validator')),
            ],
            options={
                'abstract': False,
                'unique_together': {('name', 'module_definition')},
            },
        ),
        migrations.CreateModel(
            name='VariableChoiceItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('value', models.CharField(blank=True, max_length=255)),
                ('variable_definition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='variables.VariableDefinition')),
            ],
            options={
                'unique_together': {('variable_definition', 'value')},
            },
        ),
        migrations.CreateModel(
            name='VariableChoiceItemTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('caption', models.CharField(help_text='Text to be rendered with :class:`VariableChoiceItem`', max_length=512)),
                ('language', models.ForeignKey(default='en', help_text=':class:`Language` of value content', on_delete=django.db.models.deletion.SET_DEFAULT, to='languages_plus.Language')),
                ('variable_choice_item', models.ForeignKey(help_text='Parental instance', on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='variables.VariableChoiceItem')),
            ],
            options={
                'unique_together': {('variable_choice_item', 'language')},
            },
        ),
        migrations.CreateModel(
            name='TeamVariable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('value', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('module', models.ForeignKey(help_text='Grand-parental instance', on_delete=django.db.models.deletion.CASCADE, related_name='team_variables', to='modules.Module')),
                ('stint_definition_variable_definition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='stints.StintDefinitionVariableDefinition')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='variables', to='teams.Team')),
                ('variable_definition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='variables.VariableDefinition')),
            ],
            options={
                'ordering': ('team',),
                'unique_together': {('team', 'variable_definition'), ('team', 'stint_definition_variable_definition')},
            },
        ),
        migrations.CreateModel(
            name='ModuleVariable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('value', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('module', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='variables', to='modules.Module')),
                ('stint_definition_variable_definition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='stints.StintDefinitionVariableDefinition')),
                ('variable_definition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='variables.VariableDefinition')),
            ],
            options={
                'ordering': ('module',),
                'unique_together': {('module', 'variable_definition'), ('module', 'stint_definition_variable_definition')},
            },
        ),
        migrations.CreateModel(
            name='HandVariable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('value', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('hand', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='variables', to='hands.Hand')),
                ('module', models.ForeignKey(help_text='Grand-parental instance', on_delete=django.db.models.deletion.CASCADE, related_name='hand_variables', to='modules.Module')),
                ('stint_definition_variable_definition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='stints.StintDefinitionVariableDefinition')),
                ('variable_definition', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='variables.VariableDefinition')),
            ],
            options={
                'ordering': ('hand',),
                'unique_together': {('hand', 'stint_definition_variable_definition'), ('hand', 'variable_definition')},
            },
        ),
    ]
