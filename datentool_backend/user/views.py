from rest_framework import viewsets, permissions
from django.db.models import Q
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from datentool_backend.utils.views import (HasAdminAccessPermission,
                                           HasAdminAccessOrReadOnly)
from .serializers import (UserSerializer, PlanningProcessSerializer,
                          ScenarioSerializer)
from .models import PlanningProcess, Scenario


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [HasAdminAccessOrReadOnly]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')

        if pk == "current":
            return self.request.user

        return super().get_object()


class CanCreateProcessPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ('GET'):
            return True
        else:
            return request.user.profile.can_create_process

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET'):
            owner = obj.owner
            return request.user.profile == owner
        else:
            return request.user.profile.can_create_process


class PlanningProcessViewSet(viewsets.ModelViewSet):
    queryset = PlanningProcess.objects.all()
    serializer_class = PlanningProcessSerializer
    permission_classes = [permissions.IsAuthenticated & CanCreateProcessPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user.profile)


class ScenarioViewSet(viewsets.ModelViewSet): # +UserPassesTestMixin
    queryset = Scenario.objects.all()
    serializer_class = ScenarioSerializer

    #def test_func(self):
        #if self.request.method in ('GET'):
            #return True
        #else:
            #if self.detail:
                #scenario = self.get_object()
                #owner = scenario.owner
                #owner_is_user = self.request.user.profile == owner
                #allow_shared_change = scenario.planning_process.allow_shared_change
                #user_in_users = self.request.user.profile in scenario.planning_process.users
                #return owner_is_user or (allow_shared_change and user_in_users)

            #else:
                #owner_is_user = len(self.get_queryset()) > 0



            #return self.request.user.profile.can_create_process

    #def get_queryset(self):
        #qs = super().get_queryset()
        #condition = Q(planning_process__owner=self.request.user.profile) | \
            #Q(planning_process__users__contains=self.request.user.profile)
        #return qs.filter(condition)
