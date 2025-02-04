from datentool_backend.indicators.compute.base import (register_indicator,
                                                       ServiceIndicator,
                                                       ModeParameter,
                                                       ResultSerializer)
from datentool_backend.indicators.compute.population import PopulationIndicatorMixin
from datentool_backend.indicators.compute.reachabilities import ModeVariantMixin

from datentool_backend.indicators.models import MatrixCellPlace
from datentool_backend.infrastructure.models import Service
from datentool_backend.places.models import Place


@register_indicator()
class AveragePlaceReachability(ModeVariantMixin, PopulationIndicatorMixin, ServiceIndicator):
    '''Mittlere Wegezeit der Nachfragenden aus allen Gebietseinheiten, für
    welche die betreffende Einrichtung mit einem bestimmten Verkehrsmittel die
    am schnellsten erreichbar ist'''
    title = 'Mittlere Wegezeit zur Einrichtung'
    params = (ModeParameter(), )
    representation = 'colorramp'
    colormap_name = 'OrRd'
    result_serializer = ResultSerializer.PLACE
    unit = 'Minuten'

    @property
    def description(self):
        pre = ('Mittlere Wegezeit, mit der '
               f'{self.service.facility_article} angezeigte '
               f'{self.service.facility_singular_unit} ')
        if self.service.direction_way_relationship == Service.WayRelationship.TO:
            ersiees = ('er' if self.service.facility_article == 'der'
                       else 'es' if self.service.facility_article == 'das'
                       else 'sie')
            return pre + (
                f'erreicht wird (sofern {ersiees} '
                f'{self.service.facility_article} '
                'am besten erreichbare ist)')
        ihrihm = ('ihm' if self.service.facility_article
                   in ['der', 'das'] else 'ihr')
        return pre + (
            f'die {self.service.demand_plural_unit} '
            f'erreicht, die von {ihrihm} aus am besten erreichbar sind')

    def compute(self):
        service_id = self.data.get('service')
        year = self.data.get('year', 0)
        scenario_id = self.data.get('scenario')
        mode = self.data.get('mode')
        variant = self.get_mode_variant(mode, scenario_id)
        if not variant:
            return []

        service = Service.objects.get(id=service_id)
        partition_id = [variant.id, service.infrastructure_id]

        places = self.get_places_with_capacities(service_id, year, scenario_id)
        cells_places = MatrixCellPlace.objects.filter(variant=variant,
                                                      place__in=places,
                                                      partition_id=partition_id)
        q_cp, p_cp = cells_places.query.sql_with_params()

        q_demand, p_demand = self.get_cell_demand(scenario_id, service_id)
        if not p_demand:
            return []

        query = f'''SELECT
        c."place_id" AS id,
        CASE WHEN sum(d."value") = 0
        THEN NULL
        ELSE sum(c."minutes" * d."value") / sum(d."value")
        END AS value
        FROM (
        SELECT
        cp."cell_id",
        cp."place_id",
        cp."minutes",
        row_number() OVER(PARTITION BY cp."cell_id" ORDER BY cp."minutes" ASC) AS rn
        FROM
        ({q_cp}) cp
        ) c,
        ({q_demand}) d
        WHERE c.rn = 1
        AND c."cell_id" = d."cell_id"
        GROUP BY c."place_id"
        '''
        params = p_cp + p_demand
        places_with_average_minutes = Place.objects.raw(query, params)
        return places_with_average_minutes
