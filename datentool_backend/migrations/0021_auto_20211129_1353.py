# Generated by Django 3.2.8 on 2021-11-29 12:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0020_alter_service_editable_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='populationentry',
            name='age',
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='disaggpopraster',
            name='genders',
            field=models.ManyToManyField(blank=True, to='datentool_backend.Gender'),
        ),
        migrations.AlterField(
            model_name='population',
            name='genders',
            field=models.ManyToManyField(blank=True, to='datentool_backend.Gender'),
        ),
        migrations.AlterField(
            model_name='prognosis',
            name='years',
            field=models.ManyToManyField(blank=True, to='datentool_backend.Year'),
        ),
    ]
