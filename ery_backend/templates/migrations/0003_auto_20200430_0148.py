# Generated by Django 2.2.11 on 2020-04-30 01:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('templates', '0002_auto_20200429_2125'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='templateblock',
            options={'ordering': ('created',)},
        ),
        migrations.AlterModelOptions(
            name='templateblocktranslation',
            options={'ordering': ('created',)},
        ),
    ]
