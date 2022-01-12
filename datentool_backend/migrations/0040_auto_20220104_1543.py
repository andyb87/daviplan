# Generated by Django 3.2.6 on 2022-01-04 14:43

import datentool_backend.base
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0039_alter_mapsymbol_symbol'),
    ]

    operations = [
        migrations.CreateModel(
            name='CutOffTime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
                ('infrastructure', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.infrastructure')),
                ('mode_variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.modevariant')),
            ],
        ),
        migrations.CreateModel(
            name='MatrixCellPlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
                ('cell', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='cell_place', to='datentool_backend.rastercell')),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='place_cell', to='datentool_backend.place')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='datentool_backend.modevariant')),
            ],
        ),
        migrations.CreateModel(
            name='MatrixCellStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
                ('cell', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='cell_stop', to='datentool_backend.rastercell')),
            ],
        ),
        migrations.CreateModel(
            name='MatrixPlaceStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='place_stop', to='datentool_backend.place')),
            ],
        ),
        migrations.CreateModel(
            name='MatrixStopStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='Stop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('geom', django.contrib.gis.db.models.fields.PointField(geography=True, srid=4326)),
            ],
            bases=(datentool_backend.base.NamedModel, models.Model),
        ),
        migrations.DeleteModel(
            name='ReachabilityMatrix',
        ),
        migrations.AddField(
            model_name='matrixstopstop',
            name='from_stop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='from_stop', to='datentool_backend.stop'),
        ),
        migrations.AddField(
            model_name='matrixstopstop',
            name='to_stop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='to_stop', to='datentool_backend.stop'),
        ),
        migrations.AddField(
            model_name='matrixstopstop',
            name='variant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='datentool_backend.modevariant'),
        ),
        migrations.AddField(
            model_name='matrixplacestop',
            name='stop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='stop_place', to='datentool_backend.stop'),
        ),
        migrations.AddField(
            model_name='matrixplacestop',
            name='variant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='datentool_backend.modevariant'),
        ),
        migrations.AddField(
            model_name='matrixcellstop',
            name='stop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='stop_cell', to='datentool_backend.stop'),
        ),
        migrations.AddField(
            model_name='matrixcellstop',
            name='variant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='datentool_backend.modevariant'),
        ),
        migrations.AddField(
            model_name='modevariant',
            name='cutoff_time',
            field=models.ManyToManyField(through='datentool_backend.CutOffTime', to='datentool_backend.Infrastructure'),
        ),
    ]
