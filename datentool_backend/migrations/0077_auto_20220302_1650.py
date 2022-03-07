# Generated by Django 3.2.11 on 2022-03-02 15:50

import datentool_backend.utils.protect_cascade
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0076_convert_area_placeattributes'),
    ]

    operations = [
        migrations.AddField(
            model_name='arealevel',
            name='max_population',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='arealevel',
            name='population_cache_dirty',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='PopulationAreaLevel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('up_to_date', models.BooleanField(default=False)),
                ('area_level', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, to='datentool_backend.arealevel')),
                ('population', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, to='datentool_backend.population')),
            ],
        ),
        migrations.CreateModel(
            name='AreaPopulationAgeGender',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField()),
                ('age_group', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, to='datentool_backend.agegroup')),
                ('area', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, to='datentool_backend.area')),
                ('gender', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, to='datentool_backend.gender')),
                ('population', models.ForeignKey(null=True, on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, to='datentool_backend.population')),
            ],
        ),
        migrations.AddField(
            model_name='population',
            name='arealevels',
            field=models.ManyToManyField(through='datentool_backend.PopulationAreaLevel', to='datentool_backend.AreaLevel'),
        ),
    ]
