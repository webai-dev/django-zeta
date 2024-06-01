# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('variables', '0001_initial'),
        ('languages_plus', '0004_auto_20171214_0004'),
        ('robots', '0001_initial'),
        ('frontends', '0002_smsstage_stage'),
        ('stint_specifications', '0001_initial'),
        ('countries_plus', '0005_auto_20160224_1804'),
        ('stints', '0002_auto_20200429_2125'),
        ('datasets', '0001_initial'),
        ('vendors', '0001_initial'),
        ('modules', '0003_moduledefinitionwidget_variable_definition'),
    ]

    operations = [
        migrations.AddField(
            model_name='stintspecificationvariable',
            name='variable_definition',
            field=models.ForeignKey(help_text='Connected :class:`~ery_backend.variables.models.VariableDefinition`', on_delete=django.db.models.deletion.CASCADE, to='variables.VariableDefinition'),
        ),
        migrations.AddField(
            model_name='stintspecificationrobot',
            name='robots',
            field=models.ManyToManyField(related_name='stint_specification_robots', to='robots.Robot'),
        ),
        migrations.AddField(
            model_name='stintspecificationrobot',
            name='stint_specification',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stint_specification_robots', to='stint_specifications.StintSpecification'),
        ),
        migrations.AddField(
            model_name='stintspecificationcountry',
            name='country',
            field=models.ForeignKey(help_text='Linked :class:`Country` instance.', on_delete=django.db.models.deletion.CASCADE, related_name='stint_specification_countries', to='countries_plus.Country'),
        ),
        migrations.AddField(
            model_name='stintspecificationcountry',
            name='stint_specification',
            field=models.ForeignKey(help_text='Linked :class:`StintSpecification` instance', on_delete=django.db.models.deletion.CASCADE, related_name='stint_specification_countries', to='stint_specifications.StintSpecification'),
        ),
        migrations.AddField(
            model_name='stintspecificationallowedlanguagefrontend',
            name='frontend',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frontends.Frontend'),
        ),
        migrations.AddField(
            model_name='stintspecificationallowedlanguagefrontend',
            name='language',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='languages_plus.Language'),
        ),
        migrations.AddField(
            model_name='stintspecificationallowedlanguagefrontend',
            name='stint_specification',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allowed_language_frontend_combinations', to='stint_specifications.StintSpecification'),
        ),
        migrations.AddField(
            model_name='stintspecification',
            name='backup_stint_specification',
            field=models.ForeignKey(blank=True, help_text='Assigned to users who do not fit into a :class:`~ery_backend.teams.models.Team` in the primary :class:`StintSpecification`', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stints_backupstint', to='stint_specifications.StintSpecification'),
        ),
        migrations.AddField(
            model_name='stintspecification',
            name='dataset',
            field=models.ForeignKey(blank=True, help_text='Specifies :class:`StintSpecificationVariable` values to override when starting a :class:`~ery_backend.stints.models.Stint`', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stint_specifications', to='datasets.Dataset'),
        ),
        migrations.AddField(
            model_name='stintspecification',
            name='stint_definition',
            field=models.ForeignKey(help_text='Connected :class:`~ery_backend.stints.models.StintDefintion`', on_delete=django.db.models.deletion.CASCADE, related_name='specifications', to='stints.StintDefinition'),
        ),
        migrations.AddField(
            model_name='stintspecification',
            name='subject_countries',
            field=models.ManyToManyField(help_text=':class:`Country` instances used to limit :class:`~ery_backend.hands.models.User` participatation in associated :class:`~ery_backend.stints.models.Stint` instances', through='stint_specifications.StintSpecificationCountry', to='countries_plus.Country'),
        ),
        migrations.AddField(
            model_name='stintspecification',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='vendors.Vendor'),
        ),
        migrations.AddField(
            model_name='stintmodulespecification',
            name='module_definition',
            field=models.ForeignKey(help_text='Parent :class:`~ery_backend.modules.models.ModuleDefinition`', on_delete=django.db.models.deletion.CASCADE, to='modules.ModuleDefinition'),
        ),
        migrations.AddField(
            model_name='stintmodulespecification',
            name='stint_specification',
            field=models.ForeignKey(help_text='Parental :class:`StintSpecification`', on_delete=django.db.models.deletion.CASCADE, related_name='module_specifications', to='stint_specifications.StintSpecification'),
        ),
        migrations.AlterUniqueTogether(
            name='stintspecificationallowedlanguagefrontend',
            unique_together={('language', 'frontend', 'stint_specification')},
        ),
        migrations.AlterUniqueTogether(
            name='stintspecification',
            unique_together={('name', 'stint_definition')},
        ),
    ]