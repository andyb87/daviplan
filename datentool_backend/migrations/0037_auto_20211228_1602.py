# Generated by Django 3.2 on 2021-12-28 15:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datentool_backend', '0036_auto_20211221_1549'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='infrastructure',
            name='symbol',
        ),
        migrations.AlterField(
            model_name='infrastructure',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='infrastructure',
            name='layer',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.internalwfslayer'),
        ),
        migrations.AlterField(
            model_name='internalwfslayer',
            name='symbol',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datentool_backend.mapsymbol'),
        ),
        migrations.AlterField(
            model_name='mapsymbol',
            name='fill_color',
            field=models.CharField(default='#FFFFFF', max_length=9),
        ),
        migrations.AlterField(
            model_name='mapsymbol',
            name='stroke_color',
            field=models.CharField(default='#000000', max_length=9),
        ),
        migrations.AlterField(
            model_name='mapsymbol',
            name='symbol',
            field=models.PositiveSmallIntegerField(choices=[(1, 'line'), (2, 'circle'), (3, 'square'), (4, 'star')], default=2),
        ),
        migrations.DeleteModel(
            name='SymbolForm',
        ),
    ]
