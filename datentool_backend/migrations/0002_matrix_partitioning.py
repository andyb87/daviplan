# Generated by Django 4.1.7 on 2023-02-23 16:20

import datentool_backend.base
import datentool_backend.indicators.models
import datentool_backend.modes.models
import datentool_backend.utils.protect_cascade
from django.db import migrations, models
import django.db.models.deletion
from django.contrib.postgres.fields import ArrayField
import psqlextra.backend.migrations.operations.add_default_partition
import psqlextra.backend.migrations.operations.create_partitioned_model
import psqlextra.models.partitioned
import psqlextra.types


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0001_squashed_0031_projectsetting_project_net_date'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MatrixCellPlace',
        ),
        migrations.DeleteModel(
            name='MatrixStopStop',
        ),
        migrations.DeleteModel(
            name='MatrixPlaceStop',
        ),
        migrations.DeleteModel(
            name='MatrixCellStop',
        ),

        psqlextra.backend.migrations.operations.create_partitioned_model.PostgresCreatePartitionedModel(
            name='MatrixCellPlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
                ('access_variant', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mcp_access_variant', to='datentool_backend.modevariant')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.modevariant')),
                ('cell', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, related_name='cell_place', to='datentool_backend.rastercell')),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='place_cell', to='datentool_backend.place')),
                ('partition_id', ArrayField(models.IntegerField(), size=2, help_text='Partition key using (variant, place__infrastructure_id)')),
            ],
            partitioning_options={
                'method': psqlextra.types.PostgresPartitioningMethod['LIST'],
                'key': ['partition_id'],
            },
            bases=(datentool_backend.indicators.models.MatrixMixin, datentool_backend.base.DatentoolModelMixin, psqlextra.models.partitioned.PostgresPartitionedModel),
        ),
        psqlextra.backend.migrations.operations.add_default_partition.PostgresAddDefaultPartition(
            model_name='MatrixCellPlace',
            name='default',
        ),
        psqlextra.backend.migrations.operations.create_partitioned_model.PostgresCreatePartitionedModel(
            name='MatrixStopStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
                ('from_stop', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, related_name='from_stop', to='datentool_backend.stop')),
                ('to_stop', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, related_name='to_stop', to='datentool_backend.stop')),
                ('variant_id', models.IntegerField()),
            ],
            partitioning_options={
                'method': psqlextra.types.PostgresPartitioningMethod['LIST'],
                'key': ['variant_id'],
            },
            bases=(datentool_backend.indicators.models.MatrixMixin, psqlextra.models.partitioned.PostgresPartitionedModel),
        ),
        psqlextra.backend.migrations.operations.create_partitioned_model.PostgresCreatePartitionedModel(
            name='MatrixPlaceStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
                ('access_variant', models.ForeignKey(default=datentool_backend.modes.models.get_default_access_variant, on_delete=django.db.models.deletion.CASCADE, related_name='mps_access_variant', to='datentool_backend.modevariant')),
                ('place', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, related_name='place_stop', to='datentool_backend.place')),
                ('stop', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, related_name='stop_place', to='datentool_backend.stop')),
                ('partition_id', ArrayField(models.IntegerField(), size=2, help_text='Partition key using (stop__variant_id, place__infrastructure_id)')),
            ],
            partitioning_options={
                'method': psqlextra.types.PostgresPartitioningMethod['LIST'],
                'key': ['partition_id'],
            },
            bases=(datentool_backend.indicators.models.MatrixMixin, psqlextra.models.partitioned.PostgresPartitionedModel),
        ),
        psqlextra.backend.migrations.operations.create_partitioned_model.PostgresCreatePartitionedModel(
            name='MatrixCellStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.FloatField()),
                ('access_variant', models.ForeignKey(default=datentool_backend.modes.models.get_default_access_variant, on_delete=django.db.models.deletion.CASCADE, related_name='mcs_access_variant', to='datentool_backend.modevariant')),
                ('cell', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, related_name='cell_stop', to='datentool_backend.rastercell')),
                ('stop', models.ForeignKey(on_delete=datentool_backend.utils.protect_cascade.PROTECT_CASCADE, related_name='stop_cell', to='datentool_backend.stop')),
                ('transit_variant_id', models.IntegerField()),
            ],
            partitioning_options={
                'method': psqlextra.types.PostgresPartitioningMethod['LIST'],
                'key': ['transit_variant_id'],
            },
            bases=(datentool_backend.indicators.models.MatrixMixin, datentool_backend.base.DatentoolModelMixin, psqlextra.models.partitioned.PostgresPartitionedModel),
        ),
        migrations.AlterUniqueTogether(
            name='matrixstopstop',
            unique_together={('variant_id', 'from_stop', 'to_stop')},
        ),
        migrations.AlterUniqueTogether(
            name='matrixplacestop',
            unique_together={('partition_id', 'access_variant', 'place', 'stop')},
        ),
        migrations.AlterUniqueTogether(
            name='matrixcellstop',
            unique_together={('transit_variant_id', 'access_variant', 'cell', 'stop')},
        ),
        migrations.AddConstraint(
            model_name='matrixcellplace',
            constraint=models.UniqueConstraint(fields=('partition_id', 'access_variant', 'cell', 'place'), name='variant_accessvariant_cell_place_uniq'),
        ),
        migrations.AddConstraint(
            model_name='matrixcellplace',
            constraint=models.UniqueConstraint(condition=models.Q(('access_variant__isnull', True)), fields=('partition_id', 'cell', 'place'), name='variant_noaccessvariant_cell_place_uniq'),
        ),
    ]
