# Generated by Django 3.2.12 on 2022-04-04 16:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0092_auto_20220401_1327'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='source',
            name='id_field',
        ),
    ]
