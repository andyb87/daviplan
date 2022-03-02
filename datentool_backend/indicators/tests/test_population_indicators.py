import pandas as pd
import numpy as np
import numpy.testing as nptest

import unittest
from test_plus import APITestCase

from datentool_backend.api_test import LoginTestCase

from datentool_backend.area.factories import AreaLevelFactory

from datentool_backend.indicators.compute import (
    ComputeIndicator,
    ComputePopulationAreaIndicator,
    ComputePopulationDetailAreaIndicator,
    DemandAreaIndicator,
    )

from .setup_testdata import CreateInfrastructureTestdataMixin
from datentool_backend.demand.models import AgeGroup, Gender
from datentool_backend.area.models import Area, AreaAttribute, AreaLevel
from datentool_backend.population.models import (Population,
                                                 RasterCellPopulation,
                                                 PopulationEntry,
                                                 PopulationAreaLevel, )


class TestAreaIndicatorAPI(CreateInfrastructureTestdataMixin,
                           LoginTestCase,
                           APITestCase):
    """Test to get an area indicator"""
    url_key = "areaindicators"

    #@property
    #def query_params(self):
        #return {'indicator': self.indicator.pk,
                #'area_level': self.area1.area_level.pk, }

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.profile.can_edit_basedata = True
        cls.profile.save()

        cls.create_areas()
        cls.create_years_gender_agegroups()
        cls.create_raster_population()
        cls.create_scenario()
        cls.create_population()
        cls.create_infrastructure_services()
        cls.create_demandrates()

    def test_intersect_areas_and_disaggregate(self):
        """Test intersect areas and disaggregate population"""
        population: Population = self.population

        area_level3 = AreaLevelFactory()
        # disaggregate the population, but no areas in arealevel
        response = self.get('populations-intersectareaswithcells',
                            pk=population.pk,
                            data={'area_level': area_level3.pk,
                                  'drop_constraints': False, })
        self.assert_http_202_accepted(response)
        self.assertEqual(response.data.get('message'), 'No areas available')

        # disaggregate the population and use precalculated rastercells
        response = self.get('populations-intersectareaswithcells',
                            pk=population.pk,
                            data={'drop_constraints': False,})
        self.assert_http_202_accepted(response)
        print(response.data.get('message'))

        # disaggregate the population and use precalculated rastercells
        response = self.get('populations-disaggregate', pk=population.pk,
                            data={'use_intersected_data': True,
                                  'drop_constraints': False, })
        self.assert_http_202_accepted(response)
        print(response.data.get('message'))

        unknown_population = max(Population.objects.all().values_list('id', flat=True)) + 1
        response = self.get('populations-intersectareaswithcells',
                            pk=unknown_population,
                            data={'drop_constraints': False,})
        self.assert_http_406_not_acceptable(response)

    def test_disaggregate_population(self):
        """Test if the population is correctly Disaggregated to RasterCells"""
        population: Population = self.population

        # disaggregate the population
        response = self.get('populations-disaggregate', pk=-1,
                            data={'drop_constraints': False, })
        self.assert_http_406_not_acceptable(response)

        # disaggregate the population
        response = self.get('populations-disaggregate', pk=population.pk,
                            data={'drop_constraints': False, })
        self.assert_http_202_accepted(response)
        print(response.data.get('message'))
        # do again to check updates
        response = self.get('populations-disaggregate', pk=population.pk,
                            data={'drop_constraints': False, })
        self.assert_http_202_accepted(response)

        # get disaggregated population
        response = self.get_check_200(url='populations-get-details',
                                      pk=population.pk)
        df = pd.DataFrame.from_records(response.data['rastercellpopulationagegender_set'])

        # compare to population entry
        popentries = PopulationEntry.objects.filter(population=population)
        df_popentries = pd.DataFrame.from_records(
            popentries.values('area', 'gender', 'age_group', 'value'))

        # check by gender
        expected = df_popentries[['gender', 'value']].groupby('gender').sum()
        actual = df[['gender', 'value']].groupby('gender').sum()
        pd.testing.assert_frame_equal(actual, expected)

        # check by age_group
        expected = df_popentries[['age_group', 'value']].groupby('age_group').sum()
        actual = df[['age_group', 'value']].groupby('age_group').sum()
        pd.testing.assert_frame_equal(actual, expected)

        # check by cell
        actual = df[['cell', 'value']].groupby('cell').sum()

        # disaggregate the population
        response = self.get('populations-disaggregateall',
                            data={'drop_constraints': False, })
        self.assert_http_202_accepted(response)
        print(response.data.get('message'))

    def test_area_without_rasterpopulation(self):
        """
        Test what happens, if there is population in an area,
        but no rastercells with values to distribute
        """
        #delete the existing cellcodes in area3
        cellcodes_area3 = [f'100mN{n:05}E{e:05}'
                           for n, e in
                           [(30226, 42482), (30227, 42483)]]
        rcp = RasterCellPopulation.objects.filter(cell__cellcode__in=cellcodes_area3)
        rcp.delete()

        #add a population entries in area3
        area3 = AreaAttribute.objects.get(field__name='gen', str_value='area3').area
        age_group = AgeGroup.objects.first()
        gender = Gender.objects.first()
        PopulationEntry.objects.create(population=self.population,
                                       area=area3,
                                       age_group=age_group,
                                       gender=gender,
                                       value=444)
        gender = Gender.objects.last()
        PopulationEntry.objects.create(population=self.population,
                                       area=area3,
                                       age_group=age_group,
                                       gender=gender,
                                       value=555)

        # Disaggregate the population
        response = self.get('populations-disaggregate', pk=self.population.pk,
                            data={'drop_constraints': False,})
        self.assert_http_202_accepted(response)
        # there should be a message about the not distributed inhabitants
        self.assertIn('999.0 Inhabitants not located to rastercells',
                      response.data.get('message'))
        self.assertIn('area3', response.data.get('message'))

        # get disaggregated population
        response = self.get_check_200(url='populations-get-details',
                                      pk=self.population.pk)
        df = pd.DataFrame.from_records(response.data['rastercellpopulationagegender_set'])

        # compare to population entry
        popentries = PopulationEntry.objects.filter(population=self.population)
        df_popentries = pd.DataFrame.from_records(
            popentries.values('area', 'gender', 'age_group', 'value'))

        # check results by gender, ignore population in area3
        expected = df_popentries.loc[df_popentries.area != area3.id]\
            [['gender', 'value']]\
            .groupby('gender')\
            .sum()
        actual = df[['gender', 'value']].groupby('gender').sum()
        pd.testing.assert_frame_equal(actual, expected)

        # Delete area2+3 with its population
        aa2_and_3 = AreaAttribute.objects.filter(field__name='gen',
                                                 str_value__in=['area2', 'area3'])
        area_2_and_3 = Area.objects.filter(id__in=aa2_and_3.values('area'))
        area_2_and_3.delete()

        # Disaggregate the population
        response = self.get('populations-disaggregate', pk=self.population.pk,
                            data={'drop_constraints': False,})
        self.assert_http_202_accepted(response)

        # get disaggregated population
        response = self.get_check_200(url = 'populations-get-details',
                                      pk=self.population.pk)
        df = pd.DataFrame.from_records(response.data['rastercellpopulationagegender_set'])

        # compare to population entry
        popentries = PopulationEntry.objects.filter(population=self.population)
        df_popentries = pd.DataFrame.from_records(
            popentries.values('area', 'gender', 'age_group', 'value'))

        # check by gender
        expected = df_popentries[['gender', 'value']].groupby('gender').sum()
        actual = df[['gender', 'value']].groupby('gender').sum()
        pd.testing.assert_frame_equal(actual, expected)

    def prepare_population(self):
        """prepare the population for the tests"""
        populations = Population.objects.all()
        for population in populations:
            self.get('populations-disaggregate', pk=population.pk,
                     data={'use_intersected_data': True,
                           'drop_constraints': False, })
            self.get('populations-intersectareaswithcells', pk=population.pk,
                     data={'area_level': self.area_level2.pk,
                     'use_intersected_data': True,
                     'drop_constraints': False, })
            self.get('populations-intersectareaswithcells', pk=population.pk,
                     data={'area_level': self.area_level3.pk,
                     'use_intersected_data': True,
                     'drop_constraints': False, })
            self.get('populations-intersectareaswithcells', pk=population.pk,
                     data={'area_level': self.area_level4.pk,
                     'use_intersected_data': True,
                     'drop_constraints': False, })

    def aggregate_population(self):
        """aggregate populations to all arealevels"""
        self.get('populations-aggregateall-from-cell-to-area',
                 data={'use_intersected_data': True,
                       'drop_constraints': False, })

    def prepare_indicator(self,
                          indicator_class: ComputeIndicator,
                          indicator_name: str) -> int:
        """create a compute indicator, if not yet exists"""

        response = self.get('indicators-list', data={
            'indicatortype_classname': indicator_class.__name__})

        if not response.data:
            response = self.get('indicatortypes-list', data={
                'classname': indicator_class.__name__})
            indicatortype_id = response.data[0]['id']

            response = self.post('indicators-list', data={
                'indicator_type': indicatortype_id,
                'name': 'MyComputePopAreaIndicator',
            })
        indicator_id = response.data['id']
        return indicator_id

    def test_aggregate_population_to_area(self):
        """Test the aggregation of population to areas of an area level"""
        self.prepare_population()
        indicator_id = self.prepare_indicator(ComputePopulationAreaIndicator,
                                              'MyComputePopAreaIndicator')

        query_params = {'indicator': indicator_id,
                        'area_level': self.area_level2.pk, }

        response = self.get_check_200(self.url_key + '-aggregate-population', data=query_params)
        df = pd.DataFrame(response.data).set_index('label')
        print(df)
        expected = pd.Series([357.213304, 867.698150],
                             index=['district1', 'district2'])

        pd.testing.assert_series_equal(df.value, expected, check_names=False)
        # Test if sum of large area equals all input areas

        # area_level1
        query_params = {'indicator': indicator_id,
                        'area_level': self.obj.pk, }

        response = self.get_check_200(self.url_key+'-aggregate-population', data=query_params)
        # Test if input data matches
        df = pd.DataFrame(response.data).set_index('label')
        print(df)
        expected = pd.Series([715.617852, 1404.382148, np.nan],
                             index=['area1', 'area2', 'area3'])

        pd.testing.assert_series_equal(df.value, expected, check_names=False)

        query_params = {'indicator': indicator_id,
                        'area_level': self.obj.pk,
                        'gender': self.genders[0].pk,
                        }

        response = self.get_check_200(self.url_key + '-aggregate-population', data=query_params)
        df = pd.DataFrame(response.data).set_index('label')
        print(df)
        expected = pd.Series([327.502507, 692.497493, np.nan],
                             index=['area1', 'area2', 'area3'])

        pd.testing.assert_series_equal(df.value, expected, check_names=False)

        query_params = {'indicator': indicator_id,
                        'area_level': self.obj.pk,
                        'age_group': self.age_groups.values_list('id', flat=True)[:2],
                        }

        response = self.get_check_200(self.url_key + '-aggregate-population', data=query_params)
        df = pd.DataFrame(response.data).set_index('label')
        print(df)
        expected = pd.Series([499.771245, 970.228755, np.nan],
                             index=['area1', 'area2', 'area3'])

        pd.testing.assert_series_equal(df.value, expected, check_names=False)

        query_params = {'indicator': indicator_id,
                        'area_level': self.obj.pk,
                        'area': [self.area1.pk, self.area3.pk],
                        }

        response = self.get_check_200(self.url_key + '-aggregate-population', data=query_params)
        df = pd.DataFrame(response.data).set_index('label')
        print(df)
        expected = pd.Series([715.617852, np.nan],
                             index=['area1', 'area3'])

        pd.testing.assert_series_equal(df.value, expected, check_names=False)

        #  do the pre-aggregation of the population to areas
        self.aggregate_population()
        #  the results should stay the same
        response = self.get_check_200(self.url_key + '-aggregate-population', data=query_params)
        df = pd.DataFrame(response.data).set_index('label')
        print(df)
        expected = pd.Series([715.617852, np.nan],
                             index=['area1', 'area3'])

        pd.testing.assert_series_equal(df.value, expected, check_names=False)

    def test_get_population_by_year_agegroup_gender(self):
        """Test to get the population by year, agegroup, and gender"""
        self.prepare_population()
        indicator_id = self.prepare_indicator(ComputePopulationDetailAreaIndicator,
                                              'MyComputePopDetailIndicator')

        query_params = {'indicator': indicator_id,
                        'area': self.area1.pk, }

        response = self.get_check_200('populationindicators-population-details', data=query_params)
        df_calclualted_from_rastercells = pd.DataFrame(response.data)
        print(df_calclualted_from_rastercells)
        # Test if sum of large area equals all input areas

        # area_level2
        query_params = {'indicator': indicator_id,
                        'area': self.district1.pk, }

        response = self.get_check_200('populationindicators-population-details', data=query_params)
        # Test if input data matches
        df_calclualted_from_rastercells = pd.DataFrame(response.data)
        print(df_calclualted_from_rastercells)

        # area_level2 and prognosis
        query_params = {'indicator': indicator_id,
                        'area': self.district1.pk,
                        'prognosis': self.prognosis.pk, }

        response = self.get_check_200('populationindicators-population-details', data=query_params)
        # Test if input data matches
        df_calclualted_from_rastercells = pd.DataFrame(response.data)
        print(df_calclualted_from_rastercells)

        #  do the pre-aggregation of the population to areas
        self.aggregate_population()

        #  the results should stay the same
        query_params = {'indicator': indicator_id,
                        'area': self.district1.pk,
                        'prognosis': self.prognosis.pk,}

        response = self.get_check_200('populationindicators-population-details', data=query_params)
        df_calclualted_from_areas = pd.DataFrame(response.data)

        pd.testing.assert_frame_equal(df_calclualted_from_areas,
                                      df_calclualted_from_rastercells)



    def test_demand_per_area(self):
        """Test the demand for services of an area level"""
        self.prepare_population()
        indicator_id = self.prepare_indicator(DemandAreaIndicator,
                                              'MyDemandAreaIndicator')

        query_params = {'indicator': indicator_id,
                        'area_level': self.area_level2.pk,
                        'service': self.service1.pk,
                        'year': 2022,
                        }

        response = self.get_check_200(self.url_key + '-demand', data=query_params)
        default_values = pd.DataFrame(response.data)
        print(default_values)

        query_params = {'indicator': indicator_id,
                        'area_level': self.area_level2.pk,
                        'service': self.service1.pk,
                        'scenario': self.scenario.pk,
                        'year': 2022,
                        }

        response = self.get_check_200(self.url_key + '-demand', data=query_params)
        scenario_values = pd.DataFrame(response.data)
        print(scenario_values)
        diff = scenario_values.value / default_values.value
        # in the scenario, the demand rate ist half as high as in the default scenario
        nptest.assert_allclose(diff, 0.5)

        query_params = {'indicator': indicator_id,
                        'area_level': self.area_level2.pk,
                        'service': self.service1.pk,
                        'scenario': self.scenario.pk,
                        'year': 2024,
                        }

        response = self.get_check_200(self.url_key + '-demand', data=query_params)
        values_2024 = pd.DataFrame(response.data)
        print(values_2024)
        diff = values_2024.value / scenario_values.value
        # in 2024, the demand rate increased by 20%, and the population also by 20%
        nptest.assert_allclose(diff, 1.2*1.2)

        query_params = {'indicator': indicator_id,
                        'area_level': self.area_level2.pk,
                        'service': self.service2.pk,
                        'year': 2022,
                        }

        response = self.get_check_200(self.url_key + '-demand', data=query_params)
        values_service2 = pd.DataFrame(response.data)
        print(values_service2)

        query_params = {'indicator': indicator_id,
                        'area_level': self.area1.area_level_id,
                        'service': self.service2.pk,
                        'year': 2022,
                        }

        response = self.get_check_200(self.url_key + '-demand', data=query_params)
        values_service2_arealevel1 = pd.DataFrame(response.data)
        print(values_service2_arealevel1)

        query_params = {'indicator': indicator_id,
                        'area_level': self.area_level3.pk,
                        'service': self.service2.pk,
                        'year': 2022,
                        }

        response = self.get_check_200(self.url_key + '-demand', data=query_params)
        values_service2_country = pd.DataFrame(response.data)
        print(values_service2_country)

        query_params = {'indicator': indicator_id,
                        'area_level': self.area_level4.pk,
                        'service': self.service2.pk,
                        'year': 2022,
                        }

        response = self.get_check_200(self.url_key + '-demand', data=query_params)
        values_service2_quadrants = pd.DataFrame(response.data)
        print(values_service2_quadrants)
        # the demand of the whole country should be the sum of the quadrants
        nptest.assert_almost_equal(values_service2_country.value.sum(),
                                   values_service2_quadrants.value.sum())

    def test_max_population_in_arealevel(self):
        """test the maximum population per area level"""
        area_level: AreaLevel = self.obj
        self.assertTrue(area_level.population_cache_dirty)
        self.assertTrue(self.area_level2.population_cache_dirty)
        self.prepare_population()
        self.assertTrue(area_level.population_cache_dirty)
        self.assertTrue(self.area_level2.population_cache_dirty)

        self.aggregate_population()

        area_level1 = AreaLevel.objects.get(pk=area_level.pk)
        self.assertFalse(area_level1.population_cache_dirty)
        self.assertAlmostEqual(area_level1.max_population, 738.060767, places=4)

        area_level2 = AreaLevel.objects.get(pk=self.area_level2.pk)
        self.assertFalse(area_level2.population_cache_dirty)
        self.assertAlmostEqual(area_level2.max_population, 447.3054248, places=4)

        area_level3 = AreaLevel.objects.get(pk=self.area_level3.pk)
        self.assertFalse(area_level3.population_cache_dirty)
        self.assertAlmostEqual(area_level3.max_population, 1105, places=4)

        area_level4 = AreaLevel.objects.get(pk=self.area_level4.pk)
        self.assertFalse(area_level4.population_cache_dirty)
        self.assertAlmostEqual(area_level4.max_population, 908.31255, places=4)

    @unittest.skip('Not Implemented yet')
    def test_invalidation_of_precalculated_area_population(self):
        """test, if the precalculated area population is invalidated correctly"""
        self.prepare_population()
        self.aggregate_population()
        area_level4 = AreaLevel.objects.get(pk=self.area_level4.pk)

        # deletion of an area should make the cached stuff invalid
        area = area_level4.areas.first()
        area.delete()

        self.assertTrue(area_level4.population_cache_dirty)

        populations_al = PopulationAreaLevel.objects.filter(area_level=area_level4)
        for population_al in populations_al:
            self.assertFalse(population_al.up_to_date)

