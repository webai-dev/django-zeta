# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('templates', '0001_initial'),
        ('comments', '0003_filestar_stint_definition'),
        ('themes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='filestar',
            name='template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='templates.Template'),
        ),
        migrations.AddField(
            model_name='filestar',
            name='theme',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='themes.Theme'),
        ),
    ]