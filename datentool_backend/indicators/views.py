from django.http.request import QueryDict
from django.views.generic import DetailView
from django.core.exceptions import BadRequest
from rest_framework import viewsets
from vectortiles.postgis.views import MVTView, BaseVectorTileView

from datentool_backend.utils.views import ProtectCascadeMixin
from datentool_backend.utils.permissions import (
    HasAdminAccessOrReadOnly, CanEditBasedata)

from datentool_backend.area.models import AreaLevel
from .models import (Stop,
                     Router,
                     Indicator,
                     IndicatorType,
                     )
from .compute import ComputeIndicator
from .serializers import (StopSerializer,
                          RouterSerializer,
                          IndicatorTypeSerializer,
                          IndicatorSerializer,
                          AreaIndicatorSerializer,
                          )


class StopViewSet(ProtectCascadeMixin, viewsets.ModelViewSet):
    queryset = Stop.objects.all()
    serializer_class = StopSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]


class RouterViewSet(viewsets.ModelViewSet):
    queryset = Router.objects.all()
    serializer_class = RouterSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]


class IndicatorTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IndicatorType.objects.all()
    serializer_class = IndicatorTypeSerializer


class IndicatorViewSet(viewsets.ModelViewSet):
    queryset = Indicator.objects.all()
    serializer_class = IndicatorSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]


class AreaIndicatorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AreaIndicatorSerializer

    def get_queryset(self):
        #  filter the capacity returned for the specific service
        indicator_id = self.request.query_params.get('indicator')
        if indicator_id is None:
            raise BadRequest('indicator_id is required as query_param')

        classname = Indicator.objects.get(pk=indicator_id).indicator_type.classname
        compute_class: ComputeIndicator = IndicatorType._indicator_classes[classname]
        qs = compute_class(self.request.query_params).compute()
        return qs


class AreaLevelIndicatorTileView(MVTView, DetailView):
    model = AreaLevel
    vector_tile_fields = ('id', 'area_level', 'label', 'value')

    def get_vector_tile_layer_name(self) -> str:
        """The name of the area-level"""
        return self.get_object().name

    def get_vector_tile_queryset(self):
        """Calculate the indicators for each area of the area-level"""
        query_params = QueryDict(mutable=True)
        query_params.update(self.request.GET)
        # set the area_level as query_param
        query_params['area_level'] = self.object.pk

        # an indicator_id is required
        indicator_id = query_params.get('indicator')
        if indicator_id is None:
            raise BadRequest('indicator_id is required as query_param')

        # get the IndicatorCompute-class
        classname = Indicator.objects.get(pk=indicator_id).indicator_type.classname
        compute_class: ComputeIndicator = IndicatorType._indicator_classes[classname]
        # and compute the queryset for the areas
        areas = compute_class(query_params).compute()
        return areas

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return BaseVectorTileView.get(self, request=request, z=kwargs.get('z'),
                                      x=kwargs.get('x'), y=kwargs.get('y'))

