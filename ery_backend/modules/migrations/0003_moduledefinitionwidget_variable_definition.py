# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('variables', '0001_initial'),
        ('modules', '0002_auto_20200429_2125'),
    ]

    operations = [
        migrations.AddField(
            model_name='moduledefinitionwidget',
            name='variable_definition',
            field=models.ForeignKey(blank=True, help_text='Model used to store user input captured via model instance', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='widgets', to='variables.VariableDefinition'),
        ),
    ]
