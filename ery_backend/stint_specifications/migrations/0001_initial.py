# Generated by Django 2.2.11 on 2020-04-29 21:25

import django.contrib.postgres.fields.jsonb
import django.core.validators
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
            name='StintModuleSpecification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('hand_timeout', models.PositiveIntegerField(default=0, help_text="Number of seconds before status of :class:`~ery_backend.hands.models.Hand` is set to 'quit'.")),
                ('hand_warn_timeout', models.PositiveIntegerField(default=0, help_text='Number of seconds before warning :class:`~ery_backend.users.models.User` about :class:`~ery_backend.hands.models.Hand` timeout')),
                ('stop_on_quit', models.BooleanField(default=True, help_text="Determines whether :class:`~ery_backend.stints.models.Stint` status should be set to 'canceled' if :class:`~ery_backend.hands.models.Hand` instance quits or times out.")),
                ('min_earnings', models.FloatField(blank=True, help_text='Minimum possible earnings per :class:`~ery_backend.hands.models.Hand` for :class:`~ery_backend.modules.models.Module`', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('max_earnings', models.FloatField(blank=True, help_text='Maximum possible earnings per :class:`~ery_backend.hands.models.Hand` for :class:`~ery_backend.modules.models.Module`', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('timeout_earnings', models.FloatField(default=0, help_text='Amount earned on timeout during :class:`~ery_backend.modules.model.Module`', validators=[django.core.validators.MinValueValidator(0)])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StintSpecification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(help_text='Name of the model instance.', max_length=512)),
                ('comment', models.TextField(blank=True, help_text='Comment documenting the purpose of this model instance.', null=True)),
                ('where_to_run', models.CharField(choices=[('lab', 'Lab'), ('market', 'Marketplace'), ('simulation', 'Simulation')], max_length=10)),
                ('team_size', models.PositiveIntegerField(blank=True, help_text='Number of :class:`~ery_backend.hands.models.Hand` instances per :class:`~ery_backend.teams.models.Team`', null=True)),
                ('min_team_size', models.PositiveIntegerField(blank=True, help_text='DEFINE DURING IMPLEMENTATION', null=True)),
                ('max_team_size', models.PositiveIntegerField(blank=True, help_text='DEFINE DURING IMPLEMENTATION', null=True)),
                ('max_num_humans', models.PositiveIntegerField(blank=True, help_text='DEFINE DURING IMPLEMENTATION', null=True)),
                ('min_earnings', models.FloatField(blank=True, help_text='Minimum possible earnings per :class:`~ery_backend.hands.models.Hand` for :class:`~ery_backend.stints.models.Stint`', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('max_earnings', models.FloatField(blank=True, help_text='Maximum possible earnings per :class:`~ery_backend.hands.models.Hand` for :class:`~ery_backend.stints.models.Stint`', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('late_arrival', models.BooleanField(default=False, help_text='Whether to accept new :class:`~ery_backend.hands.models.Hand` instances after start.')),
                ('opt_in_code', models.CharField(blank=True, help_text='Used to link :class:`~ery_backend.users.models.User` instances to the currently active associated :class:`~ery_backend.stints.models.Stint` instance', max_length=32, null=True, unique=True)),
                ('immediate_payment_method', models.CharField(blank=True, choices=[('PHONE_RECHARGE', 'Phone Recharge')], max_length=50, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='StintSpecificationAllowedLanguageFrontend',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
            ],
        ),
        migrations.CreateModel(
            name='StintSpecificationCountry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
            ],
            options={
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='StintSpecificationRobot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('number', models.PositiveIntegerField(blank=True, help_text='Specifies the number of robots to include per stint specification.', null=True)),
                ('robots_per_human', models.PositiveIntegerField(blank=True, help_text='Specifies the number of robots per human to include per stint specification.', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StintSpecificationVariable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('set_to_every_nth', models.PositiveIntegerField(default=1, help_text='WHAT IS THIS FOR?')),
                ('value', django.contrib.postgres.fields.jsonb.JSONField(blank=True, help_text='Used to set value attribute of specified variable during initialization of its definition.', null=True)),
                ('stint_specification', models.ForeignKey(help_text='Connected :class:`StintSpecification`', on_delete=django.db.models.deletion.CASCADE, related_name='variables', to='stint_specifications.StintSpecification')),
            ],
        ),
    ]