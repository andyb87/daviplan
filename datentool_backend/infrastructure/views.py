from django.db.models import Prefetch, Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view

from datentool_backend.utils.views import ProtectCascadeMixin
from datentool_backend.utils.permissions import (
    HasAdminAccessOrReadOnly, CanEditBasedata,)

from .permissions import CanEditScenarioPermission

from datentool_backend.user.models import InfrastructureAccess

from .models import (Scenario,
                     Place,
                     Capacity,
                     PlaceField,
                     PlaceAttribute,
                     )

from .serializers import (ScenarioSerializer,
                          PlaceSerializer,
                          CapacitySerializer,
                          PlaceFieldSerializer,
                          )


class ScenarioViewSet(ProtectCascadeMixin, viewsets.ModelViewSet):
    queryset = Scenario.objects.all()
    serializer_class = ScenarioSerializer
    permission_classes = [CanEditScenarioPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        condition_user_in_user = Q(planning_process__users__in=[self.request.user.profile])
        condition_owner_in_user = Q(planning_process__owner=self.request.user.profile)

        return qs.filter(condition_user_in_user | condition_owner_in_user)


capacity_params = [
    OpenApiParameter(name='service', type={'type': 'array', 'items': {'type': 'integer'}},
                     description='pkeys of the services', required=False),
    OpenApiParameter(name='year', type=int,
                     description='get capacities for this year', required=False),
    OpenApiParameter(name='scenario', type=int, required=False,
                     description='get capacities for the scenario with this pkey'),
]


@extend_schema_view(list=extend_schema(description='List Places',
                                       parameters=capacity_params),
                    retrieve=extend_schema(description='Get Place with id',
                                           parameters=capacity_params),)
class PlaceViewSet(ProtectCascadeMixin, viewsets.ModelViewSet):

    serializer_class = PlaceSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]
    filter_fields = ['infrastructure']

    def create(self, request, *args, **kwargs):
        """use the annotated version"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        #replace the created instance with an annotated instance
        serializer.instance = self.get_queryset().get(pk=serializer.instance.pk)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        try:
            profile = self.request.user.profile
        except AttributeError:
            # no profile yet
            return Place.objects.none()
        accessible_infrastructure = InfrastructureAccess.objects.filter(profile=profile)

        query_params = self.request.query_params
        service_ids = query_params.getlist('service')
        year = query_params.get('year', 0)
        scenario = query_params.get('scenario')

        current_capacities = Capacity.filter_queryset(Capacity.objects,
                                                      service_ids=service_ids,
                                                      scenario_id=scenario,
                                                      year=year)

        queryset = Place.objects.select_related('infrastructure')\
            .prefetch_related(
                Prefetch('infrastructure__infrastructureaccess_set',
                         queryset=accessible_infrastructure,
                         to_attr='users_infra_access'),
                Prefetch('capacity_set',
                         queryset=current_capacities,
                         to_attr='current_capacities'),
                Prefetch('placeattribute_set',
                         queryset=PlaceAttribute.objects.select_related('field'))
                )
        service = self.request.query_params.get('service')
        if service:
            queryset = queryset.filter(service_capacity=service).distinct()
        return queryset


@extend_schema_view(list=extend_schema(description='List capacities',
                                       parameters=capacity_params),
                    retrieve=extend_schema(description='Get capacities for id',
                                           parameters=capacity_params),
                                        )
class CapacityViewSet(ProtectCascadeMixin, viewsets.ModelViewSet):
    queryset = Capacity.objects.all()
    serializer_class = CapacitySerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]


class PlaceFieldViewSet(ProtectCascadeMixin, viewsets.ModelViewSet):
    queryset = PlaceField.objects.all()
    serializer_class = PlaceFieldSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]

