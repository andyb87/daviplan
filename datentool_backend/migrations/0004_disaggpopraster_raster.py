# Generated by Django 3.2.4 on 2021-08-17 07:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0003_auto_20210817_0935'),
    ]

    operations = [
        migrations.AddField(
            model_name='disaggpopraster',
            name='raster',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, to='datentool_backend.raster'),
        ),
    ]
