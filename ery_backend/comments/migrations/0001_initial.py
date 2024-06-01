# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('assets', '0001_initial'),
        ('datasets', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('reference_type', models.CharField(choices=[('dataset', 'Dataset'), ('image_asset', 'Image Asset'), ('procedure', 'Procedure'), ('module_definition', 'Module Definition'), ('stint_definition', 'Stint Definition'), ('template', 'Template'), ('widget', 'Widget'), ('theme', 'Theme'), ('validator', 'Validator')], max_length=32)),
                ('comment', models.CharField(max_length=2048)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FileStar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('reference_type', models.CharField(choices=[('dataset', 'Dataset'), ('image_asset', 'Image Asset'), ('procedure', 'Procedure'), ('module_definition', 'Module Definition'), ('stint_definition', 'Stint Definition'), ('template', 'Template'), ('widget', 'Widget'), ('theme', 'Theme'), ('validator', 'Validator')], max_length=32)),
                ('dataset', models.ForeignKey(blank=True, help_text=':class:`~ery_backend.users.models.User` uploaded :class:`~ery_backend.datasets.models.Dataset`', null=True, on_delete=django.db.models.deletion.CASCADE, to='datasets.Dataset')),
                ('image_asset', models.ForeignKey(blank=True, help_text=':class:`~ery_backend.users.models.User` uploaded image.', null=True, on_delete=django.db.models.deletion.CASCADE, to='assets.ImageAsset')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]