# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('folders', '0004_auto_20200429_2125'),
        ('validators', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='link',
            name='validator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='validators.Validator'),
        ),
    ]