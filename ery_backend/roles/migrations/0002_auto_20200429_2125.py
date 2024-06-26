# Generated by Django 2.2.11 on 2020-04-29 21:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('roles', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='roleassignment',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.Group'),
        ),
        migrations.AddField(
            model_name='roleassignment',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='roles.Role'),
        ),
        migrations.AddField(
            model_name='roleassignment',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='role',
            name='parents',
            field=models.ManyToManyField(through='roles.RoleParent', to='roles.Role'),
        ),
        migrations.AddField(
            model_name='role',
            name='privileges',
            field=models.ManyToManyField(blank=True, to='roles.Privilege'),
        ),
    ]
