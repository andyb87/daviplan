from django.test import TestCase
from test_plus import APITestCase
from datentool_backend.api_test import (BasicModelTest,
                                        WriteOnlyWithCanEditBaseDataTest)
from datentool_backend.area.tests import _TestAPI, _TestPermissions

from .factories import DemandRateSetFactory, DemandRateFactory, ScenarioDemandRateFactory
from .models import DemandRate, DemandRateSet, ScenarioDemandRate

from faker import Faker

faker = Faker('de-DE')


class TestDemand(TestCase):
    def test_demand_rate_set(self):
        demand_rate_set = DemandRateSetFactory()
        demand_rate = DemandRateFactory(demand_rate_set=demand_rate_set)
        print(demand_rate)


class TestDemandRateSetAPI(WriteOnlyWithCanEditBaseDataTest,
                           _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "demandratesets"
    factory = DemandRateSetFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        demandrateset: DemandRateSet = cls.obj
        service = demandrateset.service.pk

        data = dict(name=faker.word(), is_default=faker.pybool(), service=service)
        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data


class TestDemandRateAPI(WriteOnlyWithCanEditBaseDataTest,
                        _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "demandrates"
    factory = DemandRateFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        demandrate: DemandRate = cls.obj
        year = demandrate.year.pk
        age_group = demandrate.age_group.pk
        demand_rate_set = demandrate.demand_rate_set.pk

        data = dict(year=year, age_group=age_group,
                    demand_rate_set=demand_rate_set)
        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data


#class TestScenarioDemandRateAPI(_TestAPI, BasicModelTest, APITestCase):
    #"""Test to post, put and patch data"""
    #url_key = "scenariodemandrates"
    #factory = ScenarioDemandRateFactory

    #@classmethod
    #def setUpTestData(cls):
        #super().setUpTestData()
        #scenariodemandrate: ScenarioDemandRate= cls.obj
        #year = scenariodemandrate.year.pk
        #age_group = scenariodemandrate.age_group.pk
        #demand_rate_set = scenariodemandrate.demand_rate_set.pk
        #scenario = scenariodemandrate.scenario.pk

        #data = dict(year=year, age_group=age_group,
                    #demand_rate_set=demand_rate_set, value=faker.pyfloat(),
                    #scenario = scenario)
        #cls.post_data = data
        #cls.put_data = data
        #cls.patch_data = data
