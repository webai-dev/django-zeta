# Generated by Django 2.2.11 on 2020-04-30 01:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('validators', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='validator',
            options={'ordering': ('name',)},
        ),
        migrations.AlterModelOptions(
            name='validatortranslation',
            options={'ordering': ('created',)},
        ),
    ]
