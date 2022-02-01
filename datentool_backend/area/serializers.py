from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from datentool_backend.utils.geometry_fields import MultiPolygonGeometrySRIDField
from datetime import date as dt_date
from django.urls import reverse

from .models import (MapSymbol, LayerGroup, WMSLayer,
                     Source, AreaLevel, Area)


class MapSymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapSymbol
        fields =  ('symbol', 'fill_color', 'stroke_color')


class LayerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayerGroup
        fields = ('id', 'name', 'order', 'external')


class WMSLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WMSLayer
        fields = ('id', 'name', 'group', 'layer_name', 'order', 'url',
                  'description', 'active')
        optional_fields = ('description', 'active')


class SourceSerializer(serializers.ModelSerializer):
    date = serializers.DateField(format='%d.%m.%Y',
                                 input_formats=['%d.%m.%Y', 'iso-8601'])
    class Meta:
        model = Source
        fields = ('source_type', 'date', 'id_field', 'url', 'layer')


class AreaLevelSerializer(serializers.ModelSerializer):
    source = SourceSerializer(allow_null=True, required=False)
    symbol = MapSymbolSerializer(allow_null=True, required=False)
    area_count = serializers.IntegerField(source='area_set.count',
                                          read_only=True)
    tile_url = serializers.SerializerMethodField()

    class Meta:
        model = AreaLevel
        fields = ('id', 'name', 'order', 'source', 'symbol', 'is_active',
                  'is_preset', 'area_count', 'tile_url', 'label_field')
        read_only_fields = ('is_preset', )

    def get_tile_url(self, obj):
        # x,y,z have to be passed to reverse
        url = reverse('layer-tile', kwargs={'pk': obj.id, 'z': 0,
                                            'x': 0, 'y': 0})
        # split off trailing x,y,z
        url = url.split('/0/0/0')[0]
        # incl. host
        url = self.context['request'].build_absolute_uri(url)
        # add generic x,y,z specs
        url += '/{z}/{x}/{y}/'
        return url

    def create(self, validated_data):
        symbol_data = validated_data.pop('symbol', {})
        if not 'symbol' in symbol_data:
            symbol_data['symbol'] = 'line'
        symbol = MapSymbol.objects.create(**symbol_data) \
            if symbol_data else None
        source_data = validated_data.pop('source', {})
        date = source_data.pop('date', dt_date.today())
        source = Source.objects.create(date=date, **source_data)

        instance = AreaLevel.objects.create(
            symbol=symbol, source=source, **validated_data)

        return instance

    def update(self, instance, validated_data):
        # symbol is nullable
        update_symbol = 'symbol' in validated_data
        symbol_data = validated_data.pop('symbol', None)
        # source is nullable
        update_source = 'source' in validated_data
        source_data = validated_data.pop('source', None)

        instance = super().update(instance, validated_data)
        if update_symbol:
            symbol = instance.symbol
            if symbol_data:
                if not symbol:
                    if not 'symbol' in symbol_data:
                        symbol_data['symbol'] = 'line'
                    symbol = MapSymbol.objects.create(**symbol_data)
                    instance.symbol = symbol
                else:
                    for k, v in symbol_data.items():
                        setattr(symbol, k, v)
                    symbol.save()
            # symbol passed but is None -> intention to set it to null
            else:
                symbol.delete()
                instance.symbol = None

        if update_source:
            source = instance.source
            if source_data:
                date = source_data.pop('date', dt_date.today())
                if not source:
                    source = Source.objects.create(date=date, **source_data)
                    instance.source = source
                else:
                    for k, v in source_data.items():
                        setattr(source,  k, v)
                    source.save()
            # source passed but is None -> intention to set it to null
            else:
                source.delete()
                instance.source = None

        instance.save()
        return instance


class AreaSerializer(GeoFeatureModelSerializer):
    geom = MultiPolygonGeometrySRIDField(srid=3857)
    class Meta:
        model = Area
        geo_field = 'geom'
        fields = ('id', 'area_level', 'attributes')
