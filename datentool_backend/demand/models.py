from django.db import models
from datentool_backend.base import NamedModel
from datentool_backend.population.models import (AgeGroup, Year)
from datentool_backend.infrastructure.models import (Service)
from datentool_backend.user.models import Scenario
from datentool_backend.utils.protect_cascade import PROTECT_CASCADE
from datentool_backend.base import NamedModel, DatentoolModelMixin


class DemandRateSet(DatentoolModelMixin, NamedModel, models.Model):
    """ set of demand """
    name = models.TextField()
    is_default = models.BooleanField()
    service = models.ForeignKey(Service, on_delete=PROTECT_CASCADE)


class DemandRate(models.Model):
    """ demand rate """
    year = models.ForeignKey(Year, on_delete=PROTECT_CASCADE)
    age_group = models.ForeignKey(AgeGroup, on_delete=PROTECT_CASCADE)
    demand_rate_set = models.ForeignKey(DemandRateSet, on_delete=PROTECT_CASCADE)
    value = models.FloatField(null=True)


class ScenarioDemandRate(DemandRate):
    scenario = models.ForeignKey(Scenario, on_delete=PROTECT_CASCADE)
