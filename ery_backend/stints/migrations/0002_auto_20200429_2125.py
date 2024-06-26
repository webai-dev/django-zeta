# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('variables', '0001_initial'),
        ('labs', '0002_lab_current_stint'),
        ('stint_specifications', '0001_initial'),
        ('assets', '0001_initial'),
        ('wardens', '0001_initial'),
        ('modules', '0002_auto_20200429_2125'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('stints', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stintdefinitionvariabledefinition',
            name='variable_definitions',
            field=models.ManyToManyField(related_name='stint_definition_variable_definitions', to='variables.VariableDefinition'),
        ),
        migrations.AddField(
            model_name='stintdefinitionmoduledefinition',
            name='module_definition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stint_definition_module_definitions', to='modules.ModuleDefinition'),
        ),
        migrations.AddField(
            model_name='stintdefinitionmoduledefinition',
            name='stint_definition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stint_definition_module_definitions', to='stints.StintDefinition'),
        ),
        migrations.AddField(
            model_name='stintdefinition',
            name='cover_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.ImageAsset'),
        ),
        migrations.AddField(
            model_name='stintdefinition',
            name='module_definitions',
            field=models.ManyToManyField(help_text='Connected set of :class:`~ery_backend.modules.models.ModuleDefinition` children', through='stints.StintDefinitionModuleDefinition', to='modules.ModuleDefinition'),
        ),
        migrations.AddField(
            model_name='stint',
            name='lab',
            field=models.ForeignKey(blank=True, help_text='Endpoint for :class:`Stint`', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='stints', to='labs.Lab'),
        ),
        migrations.AddField(
            model_name='stint',
            name='started_by',
            field=models.ForeignKey(blank=True, help_text=':class:`User` who initiates via :py:meth:`Stint.start`', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='started_stints', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='stint',
            name='stint_specification',
            field=models.ForeignKey(help_text='Parental instance', on_delete=django.db.models.deletion.CASCADE, related_name='stints', to='stint_specifications.StintSpecification'),
        ),
        migrations.AddField(
            model_name='stint',
            name='stopped_by',
            field=models.ForeignKey(blank=True, help_text=':class:`User` who cancels via :py:meth:`Stint.stop`', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stopped_stints', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='stint',
            name='warden',
            field=models.OneToOneField(blank=True, help_text='Serves as administrator', null=True, on_delete=django.db.models.deletion.CASCADE, to='wardens.Warden'),
        ),
    ]
