# Generated by Django 3.2.4 on 2022-01-20 15:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0054_auto_20220120_1125'),
    ]

    operations = [
        migrations.AddField(
            model_name='arealevel',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='arealevel',
            name='is_preset',
            field=models.BooleanField(default=False),
        ),
    ]
