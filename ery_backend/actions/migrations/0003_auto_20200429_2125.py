# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('syncs', '0001_initial'),
        ('actions', '0002_actionstep_condition'),
    ]

    operations = [
        migrations.AddField(
            model_name='actionstep',
            name='era',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='setting_action_steps', to='syncs.Era'),
        ),
        migrations.AddField(
            model_name='actionstep',
            name='subaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='super_actions', to='actions.Action'),
        ),
    ]
