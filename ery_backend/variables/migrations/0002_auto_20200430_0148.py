# Generated by Django 2.2.11 on 2020-04-30 01:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('variables', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='variablechoiceitem',
            options={'ordering': ('created',)},
        ),
        migrations.AlterModelOptions(
            name='variablechoiceitemtranslation',
            options={'ordering': ('created',)},
        ),
        migrations.AlterModelOptions(
            name='variabledefinition',
            options={'ordering': ('name',)},
        ),
    ]
