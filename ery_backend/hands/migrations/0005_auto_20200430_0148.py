# Generated by Django 2.2.11 on 2020-04-30 01:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hands', '0004_auto_20200429_2125'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='hand',
            options={'ordering': ('created',)},
        ),
    ]
