# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('widgets', '0001_initial'),
        ('folders', '0005_link_validator'),
    ]

    operations = [
        migrations.AddField(
            model_name='link',
            name='widget',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='widgets.Widget'),
        ),
    ]
