# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('procedures', '0001_initial'),
        ('comments', '0001_initial'),
        ('modules', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='filestar',
            name='module_definition',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='modules.ModuleDefinition'),
        ),
        migrations.AddField(
            model_name='filestar',
            name='procedure',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='procedures.Procedure'),
        ),
    ]
