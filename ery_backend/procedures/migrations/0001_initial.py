# Generated by Django 2.2.11 on 2020-04-29 21:25

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Procedure',
            fields=[
                ('eryfile_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='base.EryFile')),
                ('code', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=('base.eryfile', models.Model),
        ),
        migrations.CreateModel(
            name='ProcedureArgument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(help_text='Name of the model instance.', max_length=512)),
                ('comment', models.TextField(blank=True, help_text='Comment documenting the purpose of this model instance.', null=True)),
                ('order', models.PositiveIntegerField(default=0, help_text='Order of arguments in :class:`~ery_backend.procedures.models.Procedure` call')),
                ('default', django.contrib.postgres.fields.jsonb.JSONField(blank=True, help_text='Default value for argument', null=True)),
                ('procedure', models.ForeignKey(help_text='Parental instance', on_delete=django.db.models.deletion.CASCADE, related_name='arguments', to='procedures.Procedure')),
            ],
            options={
                'ordering': ('order',),
                'unique_together': {('procedure', 'order'), ('procedure', 'name')},
            },
        ),
    ]
