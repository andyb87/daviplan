import pandas as pd
from io import StringIO
from distutils.util import strtobool
from django.http.request import QueryDict
from django_filters import rest_framework as filters
from django.db.models import Max, Min, Sum, Q
from drf_spectacular.utils import (extend_schema,
                                   OpenApiResponse,
                                   inline_serializer)
import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.core.exceptions import BadRequest, PermissionDenied

from datentool_backend.utils.views import ProtectCascadeMixin, ExcelTemplateMixin
from datentool_backend.utils.permissions import (
    HasAdminAccessOrReadOnly, CanEditBasedata)
from datentool_backend.utils.pop_aggregation import (
    intersect_areas_with_raster, aggregate_population)
from datentool_backend.utils.regionalstatistik import Regionalstatistik
from .models import (Raster,
                     PopulationRaster,
                     Prognosis,
                     Population,
                     PopulationEntry,
                     PopStatistic,
                     PopStatEntry,
                     RasterCellPopulationAgeGender,
                     AreaPopulationAgeGender,
                     AreaCell,
                     Year
                     )
from datentool_backend.demand.constants import RegStatAgeGroups, regstatgenders
from datentool_backend.demand.models import AgeGroup
from rest_framework.response import Response

from datentool_backend.utils.serializers import (MessageSerializer,
                                                 use_intersected_data,
                                                 drop_constraints,
                                                 area_level,
                                                 )

from datentool_backend.population.serializers import (RasterSerializer,
                                                      PopulationRasterSerializer,
                                                      PrognosisSerializer,
                                                      PopulationSerializer,
                                                      PopulationDetailSerializer,
                                                      PopulationEntrySerializer,
                                                      PopStatisticSerializer,
                                                      PopStatEntrySerializer,
                                                      PopulationTemplateSerializer,
                                                      prognosis_id_serializer,
                                                      area_level_id_serializer,
                                                      years_serializer
                          )
from datentool_backend.site.models import SiteSetting
from datentool_backend.area.models import Area, AreaLevel


class RasterViewSet(ProtectCascadeMixin, viewsets.ModelViewSet):
    queryset = Raster.objects.all()
    serializer_class = RasterSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]


class PopulationRasterViewSet(ProtectCascadeMixin, viewsets.ModelViewSet):
    queryset = PopulationRaster.objects.all()
    serializer_class = PopulationRasterSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]


class PrognosisViewSet(ProtectCascadeMixin, viewsets.ModelViewSet):
    queryset = Prognosis.objects.all()
    serializer_class = PrognosisSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]


class PopulationFilter(filters.FilterSet):
    is_prognosis = filters.BooleanFilter(field_name='prognosis',
                                         lookup_expr='isnull', exclude=True)
    class Meta:
        model = Population
        fields = ['is_prognosis']


class PopulationViewSet(viewsets.ModelViewSet):
    queryset = Population.objects.all()
    serializer_class = PopulationSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]
    filterset_class = PopulationFilter

    @extend_schema(description='return the population including the rastercellpopulationagegender_set',
                   responses=PopulationDetailSerializer)
    @action(methods=['GET'], detail=True,
            permission_classes=[HasAdminAccessOrReadOnly | CanEditBasedata])
    def get_details(self, request, **kwargs):
        """
        route to return population with all entries
        """
        instance = self.get_object()
        serializer = PopulationDetailSerializer(instance)
        return Response(serializer.data)

    @extend_schema(description='Disaggregate all Populations',
                   request=inline_serializer(
                       name='DisaggregateAllPopulationsSerializer',
                       fields={
                           'use_intersected_data': use_intersected_data,
                           'drop_constraints': drop_constraints,
                       }
                   ),
                   responses={202: OpenApiResponse(MessageSerializer,
                                                   'Disaggregation successful'),
                              406: OpenApiResponse(MessageSerializer,
                                                   'Disaggregation failed')})
    @action(methods=['POST'], detail=False,
            permission_classes=[HasAdminAccessOrReadOnly | CanEditBasedata])
    def disaggregateall(self, request, **kwargs):
        manager = RasterCellPopulationAgeGender.copymanager
        drop_constraints = bool(strtobool(
            request.data.get('drop_constraints', 'False')))

        with transaction.atomic():
            if drop_constraints:
                manager.drop_constraints()
                manager.drop_indexes()

            #  set new query-params
            old_data = self.request.data
            data = QueryDict(mutable=True)
            data.update(self.request.data)
            data['drop_constraints'] = 'False'
            request._full_data = data

            use_intersected_data = bool(strtobool(
                request.data.get('use_intersected_data', 'False')))
            pop_rasters = PopulationRaster.objects.all()
            for pop_raster in pop_rasters:
                for area_level in AreaLevel.objects.all():
                    areas = Area.objects.filter(area_level=area_level)
                    cells = AreaCell.objects.filter(area__in=areas)
                    if not areas or (cells and use_intersected_data):
                        continue
                    intersect_areas_with_raster(areas, pop_raster=pop_raster)

            data['use_intersected_data'] = 'True'
            request._full_data = data

            for population in Population.objects.all():
                self.disaggregate(request, **{'pk': population.id})

            # restore the data
            request._request.GET = old_data

            if drop_constraints:
                manager.restore_constraints()
                manager.restore_indexes()

        msg = 'Disaggregations of all Populations were successful.'
        return Response({'message': msg,}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(description='Disaggregate Population to rastercells',
                   request=inline_serializer(
                       name='DisaggregatePopulationSerializer',
                       fields={
                           'area_level': area_level,
                           'use_intersected_data': use_intersected_data,
                           'drop_constraints': drop_constraints,
                       }
                   ),
                   responses={202: OpenApiResponse(MessageSerializer, 'Disaggregation successful'),
                              406: OpenApiResponse(MessageSerializer, 'Disaggregation failed')})
    @action(methods=['POST'], detail=True,
            permission_classes=[HasAdminAccessOrReadOnly | CanEditBasedata])
    def disaggregate(self, request, **kwargs):
        """
        route to disaggregate the population to the raster cells
        """
        try:
            population: Population = self.queryset.get(**kwargs)
        except Population.DoesNotExist:
            msg = f'Population for {kwargs} not found'
            return Response({'message': msg,}, status.HTTP_406_NOT_ACCEPTABLE)

        areas = population.populationentry_set.distinct('area_id')\
            .values_list('area_id', flat=True)

        ac = AreaCell.objects.filter(area__in=areas,
                                     cell__popraster=population.popraster)

        # if rastercells are not intersected yet
        if ac and bool(strtobool(request.data.get('use_intersected_data', 'False'))):
            msg = 'use precalculated rastercells\n'
        else:
            intersect_areas_with_raster(Area.objects.filter(id__in=areas),
                                        pop_raster=population.popraster)
            msg = f'{len(areas)} Areas intersected with Rastercells.\n'
            ac = AreaCell.objects.filter(area__in=areas,
                                         cell__popraster=population.popraster)

        # get the intersected data from the database
        df_area_cells = pd.DataFrame.from_records(
            ac.values('cell__cell_id', 'area_id', 'share_cell_of_area'))\
            .rename(columns={'cell__cell_id': 'cell_id', })

        # take the Area population by age_group and gender
        entries = population.populationentry_set
        df_pop = pd.DataFrame.from_records(
            entries.values('area_id', 'gender_id', 'age_group_id', 'value'))

        # left join with the shares of each rastercell
        dd = df_pop.merge(df_area_cells,
                          on='area_id',
                          how='left')\
            .set_index(['cell_id', 'gender_id', 'age_group_id'])

        # areas without rastercells have no cell_id assigned
        cell_ids = dd.index.get_level_values('cell_id')
        has_no_rastercell = pd.isna(cell_ids)
        population_not_located = dd.loc[has_no_rastercell].value.sum()

        if population_not_located:
            area_levels = population.populationentry_set\
                .distinct('area__area_level_id')\
                .values('area__area_level')
            if not len(area_levels) == 1:
                raise BadRequest(
                    f'Areas are not from one AreaLevel but from {area_levels}')
            area_level = area_levels[0]['area__area_level']

            areas_without_rastercells = Area\
                .label_annotated_qs(area_level)\
                .filter(id__in=dd.loc[has_no_rastercell, 'area_id'])\
                .values_list('_label', flat=True)

            msg += f'{population_not_located} Inhabitants not located '\
            f'to rastercells in {list(areas_without_rastercells)}\n'
        else:
            msg += 'all areas have rastercells with inhabitants\n'

        # can work only when rastercells are found
        dd = dd.loc[~has_no_rastercell]

        # population by age_group and gender in each rastercell
        dd.loc[:, 'pop'] = dd['value'] * dd['share_cell_of_area']

        # has to be summed up by rastercell, age_group and gender, because a rastercell
        # might have population from two areas
        df_cellagegender: pd.DataFrame = dd['pop']\
            .groupby(['cell_id', 'gender_id', 'age_group_id'])\
            .sum()\
            .rename('value')\
            .reset_index()

        df_cellagegender['cell_id'] = df_cellagegender['cell_id'].astype('i8')
        df_cellagegender['population_id'] = population.id

        # delete the existing entries
        # updating would leave values for rastercells, that do not exist any more
        rc_exist = RasterCellPopulationAgeGender.objects\
            .filter(population=population)
        rc_exist.delete()

        drop_constraints = bool(strtobool(
            request.data.get('drop_constraints', 'False')))

        with StringIO() as file:
            df_cellagegender.to_csv(file, index=False)
            file.seek(0)
            RasterCellPopulationAgeGender.copymanager.from_csv(
                file,
                drop_constraints=drop_constraints, drop_indexes=drop_constraints,
            )
        msg += f'Disaggregation of Population was successful.\n'
        return Response({'message': msg,}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(description='Aggregate Population from rastercells to area',
                   request=inline_serializer(
                       name='AggregatePopulationAreaSerializer',
                       fields={
                           'area_level': area_level,
                           'use_intersected_data': use_intersected_data,
                           'drop_constraints': drop_constraints
                       }
                   ),
                   responses={202: OpenApiResponse(MessageSerializer, 'Aggregation successful'),
                              406: OpenApiResponse(MessageSerializer, 'Aggregation failed')})
    @action(methods=['POST'], detail=True,
            permission_classes=[HasAdminAccessOrReadOnly | CanEditBasedata])
    def aggregate_from_cell_to_area(self, request, **kwargs):
        """aggregate population from cell to area"""
        try:
            population: Population = self.queryset.get(**kwargs)
        except Population.DoesNotExist:
            msg = f'Population for {kwargs} not found'
            return Response({'message': msg, }, status.HTTP_406_NOT_ACCEPTABLE)

        drop_constraints = bool(strtobool(
            request.data.get('drop_constraints', 'False')))
        area_level = AreaLevel.objects.get(id=request.data.get('area_level'))
        aggregate_population(area_level, population,
                             drop_constraints=drop_constraints)

        return Response({'message': msg,}, status=status.HTTP_202_ACCEPTED)


    @extend_schema(description='Aggregate all Populations',
                   request=inline_serializer(
                       name='AggregateAllPopulationsSerializer',
                       fields={
                           'use_intersected_data': use_intersected_data,
                           'drop_constraints': drop_constraints,
                       }
                   ),
                   responses={202: OpenApiResponse(MessageSerializer,
                                                   'Aggregation successful'),
                              406: OpenApiResponse(MessageSerializer,
                                                   'Aggregation failed')})
    @action(methods=['POST'], detail=False,
            permission_classes=[HasAdminAccessOrReadOnly | CanEditBasedata])
    def aggregateall_from_cell_to_area(self, request, **kwargs):
        manager = AreaPopulationAgeGender.copymanager
        drop_constraints = bool(strtobool(
            request.data.get('drop_constraints', 'False')))

        with transaction.atomic():
            if drop_constraints:
                manager.drop_constraints()
                manager.drop_indexes()

            #  set new query-params
            old_data = self.request.data
            data = QueryDict(mutable=True)
            data.update(self.request.data)
            data['drop_constraints'] = 'False'
            request._full_data = data

            for area_level in AreaLevel.objects.all():
                for population in Population.objects.all():
                    data['area_level'] = area_level.id
                    aggregate_population(area_level, population,
                                         drop_constraints=drop_constraints)
                entries = AreaPopulationAgeGender.objects.filter(
                    area__area_level=area_level)
                summed_values = entries.values(
                    'population__year', 'area', 'population__prognosis')\
                    .annotate(Sum('value'))
                max_value = summed_values.aggregate(
                    Max('value__sum'))['value__sum__max']
                area_level.max_population = max_value
                area_level.population_cache_dirty = False
                area_level.save()

            # restore the data
            request._full_data = old_data

            if drop_constraints:
                manager.restore_constraints()
                manager.restore_indexes()

        msg = 'Aggregations of all Populations were successful.'
        return Response({'message': msg,}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(description='Pull population data in default statistics level '
                   'for all available years from Regionalstatistik GENESIS API. '
                   'ALL EXISTING POPULATION DATA WILL BE DELETED!',
                   request=inline_serializer(
                       name='PullPopulationSerializer',
                       fields={'drop_constraints': drop_constraints,},
                       ),
                   responses={202: OpenApiResponse(MessageSerializer,
                                                   'Pull successful'),
                              406: OpenApiResponse(MessageSerializer,
                                                   'Not Acceptable'),
                              500: OpenApiResponse(MessageSerializer,
                                                   'Pull failed')})
    @action(methods=['POST'], detail=False,
            permission_classes=[HasAdminAccessOrReadOnly | CanEditBasedata])
    def pull_regionalstatistik(self, request, **kwargs):
        CHUNK_SIZE = 10
        age_groups = AgeGroup.objects.all()
        if not RegStatAgeGroups.check(age_groups):
            return Response({'message': 'Die Altersklassen stimmen nicht mit '
                             'denen der Regionalstatistik überein'},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        # ToDo: there is also is_default_pop_level. set is_default_pop_level
        # automatically to the is_statistic_level level on completion
        # or complain here with 406 if they are not the same atm?
        try:
            area_level = AreaLevel.objects.get(is_statistic_level=True)
        except AreaLevel.DoesNotExist:
            msg = 'No AreaLevel for statistics defined'
            return Response({'message': msg, },
                            status=status.HTTP_406_NOT_ACCEPTABLE)

        areas = Area.annotated_qs(area_level).filter(area_level=area_level)

        min_max_years = Year.objects.all().aggregate(Min('year'), Max('year'))
        settings = SiteSetting.load()
        username = settings.regionalstatistik_user or None
        password = settings.regionalstatistik_password or None
        api = Regionalstatistik(start_year=min_max_years['year__min'],
                                end_year=min_max_years['year__max'],
                                username=username,
                                password=password)
        ags_list = areas.values_list('ags', flat=True)
        frames = []
        try:
            chunks = math.ceil(len(ags_list) / CHUNK_SIZE)
            for i in range(0, chunks):
                j = i * CHUNK_SIZE
                ags = ags_list[j:min(j+CHUNK_SIZE, len(ags_list))]
                frames.append(api.query_population(ags=ags))
        except PermissionDenied as e:
            msg = ('Die Datenmenge ist zu groß, um sie ohne Konto bei der '
            'Regionalstatistik abrufen zu können. Bitte benachrichtigen Sie '
            'den/die Toolkoordinator/in, dass ein Konto beantragt und die '
            'Zugangsdaten in den Grundeinstellungen von daviplan eingetragen '
            'werden müssen. Falls dort bereits ein Konto eingetragen ist, '
            'überprüfen Sie bitte die Gültigkeit der Zugangsdaten.')
            return Response({'message': msg, },
                            status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'message': str(e),},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        df_population = pd.concat(frames)
        regstatagegroups = RegStatAgeGroups.as_series()
        area_ids = pd.DataFrame(
            areas.values('id', 'ags')).set_index('ags').loc[:, 'id']
        area_ids.name = 'area_id'

        year_grouped = df_population.groupby('year')
        year2population = {}
        for y, year_group in year_grouped:
            try:
                year = Year.objects.get(year=y)
            except Year.DoesNotExist:
                continue
            # delete existing population and all depending objects
            try:
                population = Population.objects.get(year=year, prognosis=None)
                population.delete()
            except Population.DoesNotExist:
                pass
            # (Re-)Create Population
            population = Population.objects.create(year=year, prognosis=None)
            year2population[year.year] = population.id

        y2p = pd.Series(year2population, name='population_id')
        # add gender_id, agegroup_id, area_id and population_id
        df_population = df_population\
            .merge(regstatgenders, left_on='GES', right_index=True)\
            .merge(regstatagegroups, left_on='ALTX20', right_index=True)\
            .merge(area_ids, left_on='AGS', right_index=True)\
            .merge(y2p, left_on='year', right_index=True)\
            .rename(columns={'inhabitants': 'value', })\
            .loc[:, ['population_id', 'area_id', 'gender_id', 'age_group_id', 'value']]

        drop_constraints = request.data.get('drop_constraints', True)
        if not isinstance(drop_constraints, bool):
            drop_constraints = strtobool(drop_constraints)

        with StringIO() as file:
            df_population.to_csv(file, index=False)
            file.seek(0)
            PopulationEntry.copymanager.from_csv(
                file,
                drop_constraints=drop_constraints, drop_indexes=drop_constraints,
            )

        msg = 'Download of Population from Regionalstatistik successful'
        return Response({'message': msg,}, status=status.HTTP_202_ACCEPTED)


class PopulationEntryViewSet(ExcelTemplateMixin, viewsets.ModelViewSet):
    queryset = PopulationEntry.objects.all()
    serializer_class = PopulationEntrySerializer
    serializer_action_classes = {'create_template': PopulationTemplateSerializer,
                                 'upload_template': PopulationTemplateSerializer,
                                 }
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]
    filter_fields = ['population']

    @extend_schema(description='Upload Population Template',
                   request=inline_serializer(
                       name='PopulationUploadTemplateSerializer',
                       fields={
                           'area_level': area_level_id_serializer,
                           'years': years_serializer,
                           'prognosis': prognosis_id_serializer,
                           'drop_constraints': drop_constraints
                       }
                       ),
                   )
    @action(methods=['POST'], detail=False, permission_classes=[CanEditBasedata])
    def create_template(self, request, **kwargs):
        area_level_id = request.data.get('area_level')
        prognosis_id = request.data.get('prognosis')
        years = request.data.get('years')
        return super().create_template(request,
                                       area_level_id=area_level_id,
                                       years=years,
                                       prognosis_id=prognosis_id,
                                       )


class PopStatisticViewSet(viewsets.ModelViewSet):
    queryset = PopStatistic.objects.all()
    serializer_class = PopStatisticSerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]
    filter_fields = ['year']

    @extend_schema(description='Pull statistics (births, deaths, migration) '
                   'in default statistics level for all available years '
                   'from Regionalstatistik GENESIS API. '
                   'ALL EXISTING STATISTICS DATA WILL BE DELETED!',
                   request=inline_serializer(
                       name='PullPopStatSerializer',
                       fields={'drop_constraints': drop_constraints, },
                   ),
                   responses={202: OpenApiResponse(MessageSerializer,
                                                   'Pull successful'),
                              500: OpenApiResponse(MessageSerializer,
                                                   'Pull failed')})
    @action(methods=['POST'], detail=False,
            permission_classes=[HasAdminAccessOrReadOnly | CanEditBasedata])
    def pull_regionalstatistik(self, request, **kwargs):

        min_max_years = Year.objects.all().aggregate(Min('year'), Max('year'))
        settings = SiteSetting.load()
        username = settings.regionalstatistik_user or None
        password = settings.regionalstatistik_password or None
        api = Regionalstatistik(start_year=min_max_years['year__min'],
                                end_year=min_max_years['year__max'],
                                username=username,
                                password=password)
        try:
            area_level = AreaLevel.objects.get(is_statistic_level=True)
        except AreaLevel.DoesNotExist:
            msg = 'No AreaLevel for statistics defined'
            return Response({'message': msg, },
                            status=status.HTTP_406_NOT_ACCEPTABLE)

        areas = Area.annotated_qs(area_level).filter(area_level=area_level)
        ags = areas.values_list('ags', flat=True)
        try:
            df_births = api.query_births(ags=ags)
            df_deaths = api.query_deaths(ags=ags)
            df_migration = api.query_migration(ags=ags)
        except PermissionDenied as e:
            return Response({'message': str(e), },
                            status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'message': str(e), },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        year_grouped = df_births.groupby('year')
        year2popstatistic = {}
        for y, year_group in year_grouped:
            try:
                year = Year.objects.get(year=y)
            except Year.DoesNotExist:
                continue
            # delete existing popstatistics and all depending objects
            try:
                popstat = PopStatistic.objects.get(year=year)
                popstat.delete()
            except PopStatistic.DoesNotExist:
                pass
            # (Re-)Create PopStatistic
            popstat = PopStatistic.objects.create(year=year)
            year2popstatistic[year.year] = popstat.id

        y2p = pd.Series(year2popstatistic, name='popstatistic_id')

        area_ids = pd.DataFrame(areas.values('id', 'ags')).set_index('ags').loc[:, 'id']
        area_ids.name = 'area_id'

        df_popstat = df_births\
            .merge(df_deaths, on=['year', 'AGS'])\
            .merge(df_migration, on=['year', 'AGS'])\
            .merge(area_ids, left_on='AGS', right_index=True)\
            .merge(y2p, left_on='year', right_index=True)\
            .loc[:, ['popstatistic_id', 'area_id',
                     'births', 'deaths',
                     'immigration', 'emigration']]

        drop_constraints = request.data.get('drop_constraints', True)
        if not isinstance(drop_constraints, bool):
            drop_constraints = strtobool(drop_constraints)


        with StringIO() as file:
            df_popstat.to_csv(file, index=False)
            file.seek(0)
            PopStatEntry.copymanager.from_csv(
                file,
                drop_constraints=drop_constraints, drop_indexes=drop_constraints,
            )
        msg = 'Download of Population Statistics from Regionalstatistik successful'
        return Response({'message': msg, }, status=status.HTTP_202_ACCEPTED)


class PopStatEntryFilter(filters.FilterSet):
    year = filters.NumberFilter(field_name='popstatistic__year__year',
                                lookup_expr='exact')
    class Meta:
        model = PopStatEntry
        fields = ['popstatistic', 'year', 'area']


class PopStatEntryViewSet(viewsets.ModelViewSet):
    queryset = PopStatEntry.objects.all()
    serializer_class = PopStatEntrySerializer
    permission_classes = [HasAdminAccessOrReadOnly | CanEditBasedata]
    filterset_class = PopStatEntryFilter
