from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from datentool_backend.utils.geometry_fields import GeometrySRIDField

from .models import (Stop, Router, Indicator, IndicatorType, IndicatorTypeField)
from datentool_backend.area.models import Area
from datentool_backend.area.serializers import FieldTypeSerializer


class StopSerializer(GeoFeatureModelSerializer):
    geom = GeometrySRIDField(srid=3857)

    class Meta:
        model = Stop
        geo_field = 'geom'
        fields = ('id', 'name')


class RouterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Router
        fields = ('id', 'name', 'osm_file', 'tiff_file', 'gtfs_file',
                  'build_date', 'buffer')


class IndicatorTypeFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorTypeField
        fields = ('id', 'indicator_type', 'field_type', 'label')


class IndicatorTypeSerializer(serializers.ModelSerializer):
    parameters = FieldTypeSerializer(many=True)
    class Meta:
        model = IndicatorType
        fields = ('id', 'name', 'classname', 'description', 'parameters', 'category')


class IndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = ('id', 'indicator_type', 'name', 'parameters', 'service')


class AreaIndicatorSerializer(serializers.ModelSerializer):
    label = serializers.CharField()
    value = serializers.FloatField()
    class Meta:
        model = Area
        fields = ('id', 'label', 'value')


class PopulationIndicatorSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    gender = serializers.IntegerField()
    agegroup = serializers.IntegerField()
    value = serializers.FloatField()
