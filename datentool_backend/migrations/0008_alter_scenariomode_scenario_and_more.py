# Generated by Django 4.1 on 2022-08-31 12:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0007_modevariant_is_default'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scenariomode',
            name='scenario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.scenario'),
        ),
        migrations.AlterField(
            model_name='scenarioservice',
            name='scenario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.scenario'),
        ),
        migrations.AlterField(
            model_name='scenarioservice',
            name='service',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.service'),
        ),
    ]
