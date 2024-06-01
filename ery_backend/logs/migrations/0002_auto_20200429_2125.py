# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('syncs', '0001_initial'),
        ('logs', '0001_initial'),
        ('hands', '0001_initial'),
        ('modules', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='log',
            name='era',
            field=models.ForeignKey(blank=True, help_text='Relevant instance', null=True, on_delete=django.db.models.deletion.SET_NULL, to='syncs.Era'),
        ),
        migrations.AddField(
            model_name='log',
            name='hand',
            field=models.ForeignKey(blank=True, help_text='Relevant instance', null=True, on_delete=django.db.models.deletion.SET_NULL, to='hands.Hand'),
        ),
        migrations.AddField(
            model_name='log',
            name='module',
            field=models.ForeignKey(blank=True, help_text='Relevant instance', null=True, on_delete=django.db.models.deletion.SET_NULL, to='modules.Module'),
        ),
    ]