# Generated by Django 3.2.11 on 2022-02-03 00:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0070_auto_20220202_2346'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='population',
            name='area_level',
        ),
    ]
