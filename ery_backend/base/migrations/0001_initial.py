# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('keywords', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EryFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('slug', models.CharField(max_length=621, unique=True)),
                ('comment', models.TextField(blank=True, help_text='Comment documenting the purpose of this model instance.', null=True)),
                ('state', models.CharField(choices=[('prealpha', 'Pre-alpha'), ('alpha', 'Alpha'), ('beta', 'Beta'), ('release', 'Release'), ('archived', 'Archived'), ('deleted', 'Deleted')], default='prealpha', max_length=18)),
                ('name', models.CharField(help_text='Name of instance', max_length=512)),
                ('published', models.BooleanField(default=False, help_text='Publically viewable')),
                ('keywords', models.ManyToManyField(blank=True, help_text=':class:`~ery_backend.keywords.models.Keyword` objects for indexing.', related_name='_eryfile_keywords_+', to='keywords.Keyword')),
            ],
            options={
                'ordering': ('created',),
                'abstract': False,
            },
        ),
    ]
