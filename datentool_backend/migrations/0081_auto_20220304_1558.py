# Generated by Django 3.2.4 on 2022-03-04 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0080_auto_20220303_1617'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scenario',
            name='modevariants',
        ),
        migrations.RemoveField(
            model_name='scenariomode',
            name='mode',
        ),
        migrations.AlterField(
            model_name='modevariant',
            name='mode',
            field=models.IntegerField(choices=[(1, 'zu Fuß'), (2, 'Fahrrad'), (3, 'Auto'), (4, 'ÖPNV')]),
        ),
        migrations.DeleteModel(
            name='Mode',
        ),
    ]
