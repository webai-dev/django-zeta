# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('languages_plus', '0004_auto_20171214_0004'),
        ('frontends', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Redirect',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('order', models.PositiveIntegerField(default=0, help_text='Order of execution')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Stage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('preaction_started', models.BooleanField(default=False, help_text='Tracks execution of :py:meth:`StageDefinition.pre_action`')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StageBreadcrumb',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='StageDefinition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(help_text='Name of the model instance.', max_length=512)),
                ('comment', models.TextField(blank=True, help_text='Comment documenting the purpose of this model instance.', null=True)),
                ('breadcrumb_type', models.CharField(choices=[('none', 'No Breadcrumbs'), ('back', 'Back Breadcrumbs Only'), ('all', 'All Breadcrumbs')], default='all', help_text='Indicates whether to create :class:`StageBreadCrumb`when :class:`StageDefinition` is assigned via :py:meth:`Hand.set_stage`', max_length=8)),
                ('end_stage', models.BooleanField(default=False, help_text='Indicates the end of the connected :class:`~ery_backend.modules.models.Module`')),
                ('redirect_on_submit', models.BooleanField(default=True, help_text='Whether to execute redirect on submit event_type.')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StageTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('stage_definition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stage_templates', to='stages.StageDefinition')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StageTemplateBlock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(help_text='Name of the model instance.', max_length=512)),
                ('comment', models.TextField(blank=True, help_text='Comment documenting the purpose of this model instance.', null=True)),
                ('stage_template', models.ForeignKey(blank=True, help_text='Parental instance', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='blocks', to='stages.StageTemplate')),
            ],
        ),
        migrations.CreateModel(
            name='StageTemplateBlockTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('content', models.TextField(blank=True, help_text='Content to be rendered as part of :class:`StageDefinition` (connected through :class:`StageTemplate`).', null=True)),
                ('frontend', models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='frontends.Frontend')),
                ('language', models.ForeignKey(help_text='Used to render content', on_delete=django.db.models.deletion.CASCADE, to='languages_plus.Language')),
                ('stage_template_block', models.ForeignKey(help_text='Parental instance', on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='stages.StageTemplateBlock')),
            ],
        ),
    ]
