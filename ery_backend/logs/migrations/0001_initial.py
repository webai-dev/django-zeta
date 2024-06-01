# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('log_type', models.CharField(choices=[('debug', 'Info not needed for regular operation, but useful in development.'), ('info', "Info that's helpful during regular operation."), ('warning', 'Info that could be problematic, but is non-urgent.'), ('error', 'Info that is important and likely requires prompt attention.'), ('critical', "I don't find myself using this in practice, but if you need one higher than error, here it is")], default='info', max_length=64)),
                ('message', models.TextField()),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
