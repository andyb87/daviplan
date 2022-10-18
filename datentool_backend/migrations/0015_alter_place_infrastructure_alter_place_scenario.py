# Generated by Django 4.1.2 on 2022-10-14 15:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0014_alter_logentry_user_processstate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='place',
            name='infrastructure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.infrastructure'),
        ),
        migrations.AlterField(
            model_name='place',
            name='scenario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.scenario'),
        ),
    ]
