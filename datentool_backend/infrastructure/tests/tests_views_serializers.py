from typing import Tuple, Set
from collections import OrderedDict
import json
from rest_framework import status
from unittest import skip
from django.test import TestCase
from test_plus import APITestCase
from datentool_backend.api_test import (BasicModelTest,
                                        WriteOnlyWithCanEditBaseDataTest,
                                        WriteOnlyWithAdminAccessTest)
from datentool_backend.area.tests import _TestAPI, _TestPermissions
from datentool_backend.user.factories import ProfileFactory

from datentool_backend.infrastructure.factories import (
    InfrastructureFactory,
    ServiceFactory,
    CapacityFactory,
    FClassFactory,
    PlaceFieldFactory,
    PlaceFactory,
    FieldTypeFactory,
    ScenarioCapacityFactory,
    ScenarioPlaceFactory,
)
from datentool_backend.infrastructure.models import (
    Profile,
    Infrastructure,
    Place,
    Capacity,
    FieldTypes,
    FClass,
    Service,
    PlaceField,
    ScenarioCapacity,
    ScenarioPlace,
    InfrastructureAccess,
)
from datentool_backend.area.serializers import InternalWFSLayerSerializer


from faker import Faker

faker = Faker('de-DE')


class TestInfrastructure(TestCase):

    def test_service(self):
        service = ServiceFactory()
        print(service.quota_type)

    def test_infrastructure(self):
        """"""
        profiles = [ProfileFactory() for i in range(3)]
        infrastructure = InfrastructureFactory(editable_by=profiles[:2],
                                               accessible_by=profiles[1:])
        self.assertQuerysetEqual(infrastructure.editable_by.all(),
                                 profiles[:2], ordered=False)
        self.assertQuerysetEqual(infrastructure.accessible_by.all(),
                                 profiles[1:], ordered=False)

    def test_capacity(self):
        """"""
        infrastructure = InfrastructureFactory()
        capacity = CapacityFactory(place__infrastructure=infrastructure,
                                   service__infrastructure=infrastructure)
        print(capacity)
        print(capacity.place)

    def test_fclass(self):
        """"""
        fclass = FClassFactory()
        print(fclass)

    def test_place_field(self):
        """"""
        place_field = PlaceFieldFactory()
        print(place_field)


class TestInfrastructureAPI(WriteOnlyWithAdminAccessTest,
                            _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "infrastructures"
    factory = InfrastructureFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        infrastructure: Infrastructure = cls.obj
        editable_by = list(infrastructure.editable_by.all().values_list(flat=True))
        accessible_by = [{'profile': p, 'allow_sensitive_data': True}
                         for p in
                         infrastructure.accessible_by.all().values_list(flat=True)]
        layer_data = InternalWFSLayerSerializer(infrastructure.layer).data
        del(layer_data['group'])
        del(layer_data['id'])

        data = dict(name=faker.word(),
                    description=faker.word(),
                    editable_by=editable_by,
                    accessible_by=accessible_by,
                    layer=layer_data)
        cls.post_data = data
        cls.put_data = data
        #  for patch, test if different value for allow_sensitive_data is passed
        cls.patch_data = data.copy()
        accessible_by = [{'profile': p, 'allow_sensitive_data': False}
                         for p in
                         infrastructure.accessible_by.all().values_list(flat=True)]
        cls.patch_data['accessible_by'] = accessible_by

    def test_patch_empty_editable_by(self):
        """Test the patch with an empty list"""
        patch_data2 = self.patch_data.copy()
        patch_data2['editable_by'] = []
        patch_data2['accessible_by'] = []
        self.patch_data = patch_data2
        super().test_put_patch()

    @skip('is replaced by test_can_patch_symbol')
    def test_can_edit_basedata(self):
        pass

    def test_admin_access(self):
        """write permission if user has admin_access"""
        super().admin_access()

    def test_can_patch_layer(self):
        """
        user, who can_edit_basedata has permission
        to patch the layer with its symbol
        """
        profile = self.profile
        permission_basedata = profile.can_edit_basedata
        permission_admin = profile.admin_access

        # Testprofile, with permission to edit basedata
        profile.can_edit_basedata = True
        profile.admin_access = False
        profile.save()

        # test post
        url = self.url_key + '-list'

        response = self.post(url, **self.url_pks, data=self.post_data,
                             extra={'format': 'json'})
        self.response_403(msg=response.content)

        # test put
        url = self.url_key + '-detail'
        kwargs = self.kwargs
        formatjson = dict(format='json')

        response = self.put(url, **kwargs,
                            data=self.put_data,
                            extra=formatjson)
        self.response_403(msg=response.content)

        # check status code for patch
        self.patch_data = {'layer': {
            'name': 'test', 'symbol': {'symbol': 'line'}}}
        response = self.patch(url, **kwargs,
                              data=self.patch_data, extra=formatjson)
        self.response_200(msg=response.content)

        # Other fields should not be edited
        self.patch_data['description'] = 'A new description'
        response = self.patch(url, **kwargs,
                              data=self.patch_data, extra=formatjson)
        self.response_403(msg=response.content)

        # Testprofile, without permission to edit basedata
        profile.can_edit_basedata = False
        profile.save()

        # test post
        url = self.url_key + '-list'
        response = self.post(url, **self.url_pks, data=self.post_data,
                             extra={'format': 'json'})
        self.response_403(msg=response.content)

        # test put_patch
        url = self.url_key + '-detail'
        kwargs = self.kwargs
        formatjson = dict(format='json')

        # check status code for put
        response = self.put(url, **kwargs,
                            data=self.put_data,
                            extra=formatjson)
        self.response_403(msg=response.content)

        # check status code for patch
        self.patch_data = {'layer': {
            'name': 'test', 'symbol': {'symbol': 'line'}}}

        response = self.patch(url, **kwargs,
                              data=self.patch_data, extra=formatjson)
        self.response_403(msg=response.content)

        profile.admin_access = permission_admin
        profile.can_edit_basedata = permission_basedata
        profile.save()


class TestServiceAPI(WriteOnlyWithCanEditBaseDataTest,
                     _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "services"
    factory = ServiceFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        service: Service = cls.obj
        infrastructure = service.infrastructure.pk
        editable_by = list(service.editable_by.all().values_list(flat=True))
        #quota_id = service.pk

        data = dict(name=faker.word(),
                    description=faker.word(),
                    infrastructure=infrastructure,
                    editable_by=editable_by,
                    capacity_singular_unit=faker.word(),
                    capacity_plural_unit=faker.word(),
                    has_capacity=True,
                    demand_singular_unit=faker.word(),
                    demand_plural_unit=faker.word(),
                    # quota_id=quota_id,
                    quota_type=faker.word())
        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data


class TestPlaceAPI(WriteOnlyWithCanEditBaseDataTest,
                   _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "places"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj = PlaceFactory(attributes=faker.json(
            num_rows=1, data_columns={'age': 'pyint', 'surname': 'name'}))

        place: Place = cls.obj
        infrastructure = place.infrastructure.pk

        ft_age = FieldTypeFactory(field_type=FieldTypes.NUMBER)
        field1 = PlaceFieldFactory(
            attribute='age',
            infrastructure=place.infrastructure,
            field_type=ft_age,
            sensitive=False,
        )

        ft_name = FieldTypeFactory(field_type=FieldTypes.STRING)
        field2 = PlaceFieldFactory(
            attribute='surname',
            infrastructure=place.infrastructure,
            field_type=ft_name,
            sensitive=False,
        )

        geom = place.geom.ewkt

        properties = OrderedDict(
            name=faker.word(),
            infrastructure=infrastructure,
            attributes=faker.json(num_rows=1,
                                  data_columns={'age': 'pyint', 'surname': 'name'}),
        )
        geojson = {
            'type': 'Feature',
            'geometry': geom,
            'properties': properties,
        }

        cls.post_data = geojson
        geojson_putpatch = geojson.copy()
        geojson_putpatch['id'] = place.id

        cls.put_data = geojson_putpatch
        cls.patch_data = geojson_putpatch

    def test_sensitive_data(self):
        """Test if sensitive data is correctly shown"""
        pr1 = ProfileFactory()
        pr2 = ProfileFactory()
        place: Place = self.obj
        attributes = {'harmless': 123, 'very_secret': 456, }
        place.attributes = json.dumps(attributes)
        place.save()
        infr: Infrastructure = place.infrastructure
        infr.accessible_by.set([pr1, pr2])
        infr.save()

        i1 = InfrastructureAccess.objects.get(infrastructure=infr, profile=pr1)
        i1.allow_sensitive_data = False
        i1.save()

        i2 = InfrastructureAccess.objects.get(infrastructure=infr, profile=pr2)
        i2.allow_sensitive_data = True
        i2.save()

        field_type = FieldTypeFactory(field_type=FieldTypes.NUMBER)
        field1 = PlaceFieldFactory(attribute='harmless', sensitive=False,
                                   field_type=field_type,
                                   infrastructure=infr)
        field2 = PlaceFieldFactory(attribute='very_secret', sensitive=True,
                                   field_type=field_type,
                                   infrastructure=infr)

        self.client.logout()
        self.client.force_login(pr1.user)
        response = self.get(self.url_key + '-detail', **self.kwargs)
        attrs = json.loads(response.data['properties']['attributes'])
        self.assertDictEqual(attrs, {'harmless': 123})

        self.client.logout()
        self.client.force_login(pr2.user)
        response = self.get(self.url_key + '-detail', **self.kwargs)
        attrs = json.loads(response.data['properties']['attributes'])
        self.assertDictEqual(attrs, attributes)

        self.client.logout()
        self.client.force_login(self.profile.user)

    def setup_place(self) -> Tuple[Profile, Place]:
        pr1 = ProfileFactory(can_edit_basedata=True)
        place: Place = self.obj
        attributes = {'int_field': 123,
                      'text_field': 'ABC',
                      'class_field': 'Category_1', }
        place.attributes = json.dumps(attributes)
        place.save()
        infr: Infrastructure = place.infrastructure
        infr.accessible_by.set([pr1])
        infr.save()

        field1 = PlaceFieldFactory(attribute='int_field', sensitive=False,
                                   field_type__field_type=FieldTypes.NUMBER,
                                   infrastructure=infr)
        field2 = PlaceFieldFactory(attribute='text_field', sensitive=False,
                                   field_type__field_type=FieldTypes.STRING,
                                   infrastructure=infr)
        field3 = PlaceFieldFactory(
            attribute='class_field',
            sensitive=False,
            field_type__field_type=FieldTypes.CLASSIFICATION,
            infrastructure=infr)

        fclass1 = FClassFactory(classification=field3.field_type,
                                order=1,
                                value='Category_1')
        fclass2 = FClassFactory(classification=field3.field_type,
                                order=2,
                                value='Category_2')
        return pr1, place

    def test_update_attributes(self):
        """Test update of attributes"""
        pr1, place = self.setup_place()

        patch_data = {'name': 'NewName',
                      'attributes': {'int_field': 456,
                                     'text_field': 'DEF',
                                     'class_field': 'Category_2', }
                      }

        response = self.patch(self.url_key + '-update-attributes', pk=place.pk,
                              data=patch_data, extra=dict(format='json'))
        self.response_403(msg=response.content)

        self.client.logout()
        self.client.force_login(pr1.user)

        response = self.patch(self.url_key + '-update-attributes', pk=place.pk,
                              data=patch_data, extra=dict(format='json'))
        self.response_200(msg=response.content)

        # check the results returned by the view
        attrs = json.loads(response.data['attributes'])
        self.compare_data(attrs, patch_data)

        # check if the changed data is really in the database
        response = self.get_check_200(self.url_key + '-detail', pk=place.pk)
        attrs = json.loads(response.data['properties']['attributes'])
        self.compare_data(attrs, patch_data)

        # patch only one value
        patch_data = {'attributes': {'int_field': 678, }}
        response = self.patch(self.url_key + '-update-attributes', pk=place.pk,
                              data=patch_data, extra=dict(format='json'))
        self.response_200(msg=response.content)

        expected = {'attributes': {'int_field': 678,
                                   'text_field': 'DEF',
                                   'class_field': 'Category_2', }
                    }
        # check the results returned by the view
        attrs = json.loads(response.data['attributes'])
        self.compare_data(attrs, expected)

        # check if the changed data is really in the database
        response = self.get_check_200(self.url_key + '-detail', pk=place.pk)
        attrs = json.loads(response.data['properties']['attributes'])
        self.compare_data(attrs, expected)

        patch_data = {'attributes': {'integer_field': 456, }}
        response = self.patch(self.url_key + '-update-attributes', pk=place.pk,
                              data=patch_data, extra=dict(format='json'))
        self.response_400(msg=response.content)

        patch_data = {'attributes': {'int_field': '456', }}
        response = self.patch(self.url_key + '-update-attributes', pk=place.pk,
                              data=patch_data, extra=dict(format='json'))
        self.response_400(msg=response.content)

        patch_data = {'attributes': {'text_field': 12.3, }}
        response = self.patch(self.url_key + '-update-attributes', pk=place.pk,
                              data=patch_data, extra=dict(format='json'))
        self.response_400(msg=response.content)

        patch_data = {'attributes': {'class_field': 'Category_7', }}
        response = self.patch(self.url_key + '-update-attributes', pk=place.pk,
                              data=patch_data, extra=dict(format='json'))
        self.response_400(msg=response.content)

        patch_data = {'attributes': {'class_field': 'Category_1', }}
        response = self.patch(self.url_key + '-update-attributes', pk=place.pk,
                              data=patch_data, extra=dict(format='json'))
        self.response_200(msg=response.content)

        expected = {'attributes': {'int_field': 678,
                                   'text_field': 'DEF',
                                   'class_field': 'Category_1', }
                    }

        attrs = json.loads(response.data['attributes'])
        self.compare_data(attrs, patch_data)

    def test_delete_placefield_and_fclass(self):
        """
        Test, if the deletion of a PlaceField
        and a FClass cascades to the Place Attributes
        """
        profile, place1 = self.setup_place()
        self.client.logout()
        self.client.force_login(profile.user)

        attributes2 = {'int_field': 789,
                       'class_field': 'Category_2', }
        place2 = PlaceFactory(infrastructure=place1.infrastructure,
                              attributes=json.dumps(attributes2))

        place_fields = PlaceField.objects.filter(
            infrastructure=place1.infrastructure,
            attribute__in=['int_field', 'text_field', 'class_field'])

        for place_field in place_fields:
            # deleting the place field should fail,
            # if there are attributes of this place_field
            response = self.delete('placefields-detail', pk=place_field.pk)
            self.response_403(msg=response.content)

        field_name = 'int_field'
        int_field = PlaceField.objects.get(attribute=field_name,
                                           infrastructure=place1.infrastructure)

        # deleting the place field should cascadedly delete the attribute
        # from the place attributes
        response = self.delete('placefields-detail',
                               pk=int_field.pk,
                               data=dict(override_protection=True))
        self.response_204(msg=response.content)

        place_attributes = Place.objects.filter(
            infrastructure=place1.infrastructure).values_list('attributes',
                                                              flat=True)
        for attr in place_attributes:
            attr_dict = json.loads(attr)
            msg = f'{field_name} should be removed from the place attributes {attr_dict}'
            self.assertFalse(field_name in attr_dict, msg)

        field_name = 'text_field'
        text_field = PlaceField.objects.get(attribute=field_name,
                                            infrastructure=place1.infrastructure)
        # remove the text_field from place1, so there is no text_field defined
        attributes = {'class_field': 'Category_1', }
        place1.attributes = json.dumps(attributes)
        place1.save()

        # it should delete the text_field even without override_protection,
        # because it is not referenced any more
        response = self.delete('placefields-detail',
                               pk=text_field.pk,
                               data=dict(override_protection=False))
        self.response_204(msg=response.content)

        field_name = 'class_field'
        class_field = PlaceField.objects.get(attribute=field_name,
                                             infrastructure=place1.infrastructure)
        # deleting a FClass category should fail,
        # if there are attributes using this category
        fclass1 = FClass.objects.get(classification=class_field.field_type, value='Category_1')
        response = self.delete('fclasses-detail',
                               pk=fclass1.pk,
                               data=dict(override_protection=False))
        self.response_403(msg=response.content)

        # deleting a FClass category should work with override_protection,
        response = self.delete('fclasses-detail',
                               pk=fclass1.pk,
                               data=dict(override_protection=True))
        self.response_204(msg=response.content)

        # the attribute should have been removed now in place1
        place_attributes = Place.objects.get(pk=place1.pk).attributes
        attr_dict = json.loads(place_attributes)
        msg = f'{field_name} should be removed from the place attributes {attr_dict}'
        self.assertFalse(field_name in attr_dict, msg)

        #  create a new Category_3
        fclass3 = FClassFactory(classification=class_field.field_type,
                                order=1,
                                value='Category_3')

        # this is not used, so it should be deleted also without override_protection
        response = self.delete('fclasses-detail',
                               pk=fclass3.pk,
                               data=dict(override_protection=False))
        self.response_204(msg=response.content)

    def test_get_capacity_for_service(self):
        """get filtered queryset for service"""
        place1: Place = self.obj
        place2 = PlaceFactory(infrastructure=place1.infrastructure)
        service1 = ServiceFactory(infrastructure=place1.infrastructure)
        service2 = ServiceFactory(infrastructure=place1.infrastructure)
        service3 = ServiceFactory(infrastructure=place1.infrastructure)

        place1.service_capacity.set([service1, service2])
        place2.service_capacity.set([service3, service2])

        #  default capacity has from_year=0 and capacity=0
        # add two more capacities
        cap_s3_p2 = CapacityFactory(service=service3, place=place2,
                                    from_year=2023, capacity=123)
        cap_s3_p2 = CapacityFactory(service=service3, place=place2,
                                    from_year=2021, capacity=55)
        capacities_s3_p2 = Capacity.objects.filter(place=place2,
                                                   service=service3)

        #  test if the correct places which offer a service are returned
        self.check_place_with_capacity(service1, {place1.id})
        self.check_place_with_capacity(service2, {place1.id, place2.id})
        self.check_place_with_capacity(service3, {place2.id})

        year_expected = {2020: 0,
                         2021: 55,
                         2022: 55,
                         2023: 123,
                         2024: 123,
                         }

        #  test if the correct capacity is returned for different years
        for year, expected in year_expected.items():
            response = self.get(self.url_key + '-detail', pk=place2.pk,
                                data=dict(service=service3.id, year=year))
            capacity = response.data['properties']['capacity']
            self.assertListEqual([c['capacity'] for c in capacity], [expected])

        #  without the year
        response = self.get(self.url_key + '-detail', pk=place2.pk,
                            data=dict(service=service3.id))
        capacity = response.data['properties']['capacity']
        self.assertListEqual([c['capacity'] for c in capacity], [0])

        #  this should fail, because there is no service3 offered at place1
        response = self.get(self.url_key + '-detail', pk=place1.pk,
                            data=dict(service=service3.id, year=2024))
        self.response_404(response)

    def check_place_with_capacity(self, service: Service,
                                  place_ids: Set[int],
                                  year: int = None):
        response = self.get(self.url_key + '-list',
                            data=dict(service=service.id))
        self.response_200(msg=response.content)
        self.assertSetEqual({p['id'] for p in response.data['features']},
                            place_ids)
        feature_capacities = [f['properties']['capacity']
                              for f in response.data['features']]
        for fc in feature_capacities:
            assert all((c['service'] == service.id for c in fc))

# class TestScenarioPlaceAPI(_TestAPI, BasicModelTest, APITestCase):
    #"""Test to post, put and patch data"""
    #url_key = "scenarioplaces"
    #factory = ScenarioPlaceFactory

    # @classmethod
    # def setUpTestData(cls):
        # super().setUpTestData()
        #scenarioplace: ScenarioPlace = cls.obj
        #infrastructure = scenarioplace.infrastructure.pk
        #geom = scenarioplace.geom.ewkt
        #scenario = scenarioplace.scenario.pk
        #status_quo = scenarioplace.status_quo.pk

        # properties = OrderedDict(
            # name=faker.word(),
            # infrastructure=infrastructure,
            # attributes=faker.json(),
            # scenario=scenario,
            # status_quo=status_quo
        # )
        # geojson = {
            # 'type': 'Feature',
            # 'geometry': geom,
            # 'properties': properties,
        # }

        #cls.post_data = geojson
        #geojson_putpatch = geojson.copy()
        #geojson_putpatch['id'] = scenarioplace.id

        #cls.put_data = geojson_putpatch
        #cls.patch_data = geojson_putpatch


class TestCapacityAPI(WriteOnlyWithCanEditBaseDataTest,
                      _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "capacities"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        infrastructure = InfrastructureFactory()
        capacity = CapacityFactory(place__infrastructure=infrastructure,
                                   service__infrastructure=infrastructure)

        cls.obj = capacity
        place = capacity.place.pk
        service = capacity.service.pk

        data = dict(place=place, service=service,
                    capacity=faker.pyfloat(positive=True), from_year=faker.year())
        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data


class TestScenarioCapacityAPI(_TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "scenariocapacities"
    factory = ScenarioCapacityFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        scenariocapacity: ScenarioCapacity = cls.obj
        place = scenariocapacity.place.pk
        service = scenariocapacity.service.pk
        scenario = scenariocapacity.scenario.pk
        status_quo = scenariocapacity.status_quo.pk

        data = dict(place=place, service=service,
                    capacity=faker.pyfloat(positive=True), from_year=faker.year(),
                    scenario=scenario, status_quo=status_quo)
        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data


class TestFieldTypeNUMSTRAPI(WriteOnlyWithCanEditBaseDataTest,
                             _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "fieldtypes"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj = FieldTypeFactory(field_type=FieldTypes.NUMBER)
        data = dict(field_type=FieldTypes.NUMBER,
                    name=faker.word(),
                    )
        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data


class TestFieldTypeCLAAPI(WriteOnlyWithCanEditBaseDataTest,
                          _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "fieldtypes"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj = FieldTypeFactory(field_type=FieldTypes.CLASSIFICATION)

        fclass_set = [{'order': 1, 'value': faker.word(), },
                      {'order': 2, 'value': faker.word(), },
                      ]

        data = dict(field_type=FieldTypes.CLASSIFICATION,
                    name=faker.word(),
                    classification=fclass_set,
                    )

        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data

    def test_patch_fclass_with_deletion(self):
        """test also, if deletion works"""
        self.profile.can_edit_basedata = True
        self.profile.save()

        field_typ = FieldTypeFactory(field_type=FieldTypes.CLASSIFICATION)
        fclass1 = FClassFactory(classification=field_typ, order=7, value='7')
        fclass2 = FClassFactory(classification=field_typ, order=42, value='42')

        self.assertEqual(field_typ.fclass_set.count(), 2)

        url = self.url_key + '-detail'
        kwargs = {**self.url_pks, 'pk': field_typ.pk, }
        formatjson = dict(format='json')

        # patch the fclass-set with new data

        fclass_set = [{'order': 42, 'value': '422', },
                      {'order': 2, 'value': '2', },
                      {'order': 3, 'value': '3', },
                      ]

        patch_data = dict(classification=fclass_set)
        # check status code for patch
        response = self.patch(url, **kwargs,
                              data=patch_data, extra=formatjson)
        self.response_200(msg=response.content)

        # test if fclasses are correctly updated, added and deleted
        new_fclass_set = field_typ.fclass_set.all()
        self.assertEqual(len(new_fclass_set), 3)
        # check if the 7 is deleted
        self.assertQuerysetEqual(new_fclass_set.filter(order=7), [])
        self.assertEqual(new_fclass_set.get(order=42).value, '422')
        self.assertEqual(new_fclass_set.get(order=2).value, '2')
        self.assertEqual(new_fclass_set.get(order=3).value, '3')

        self.profile.can_edit_basedata = False
        self.profile.save()


class TestFClassAPI(WriteOnlyWithCanEditBaseDataTest,
                    _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "fclasses"
    factory = FClassFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        fclass: FClass = cls.obj
        classification = fclass.classification.pk
        data = dict(classification_id=classification,
                    order=faker.unique.pyint(max_value=100),
                    value=faker.unique.word())
        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data


class TestPlaceFieldAPI(WriteOnlyWithCanEditBaseDataTest,
                        _TestPermissions, _TestAPI, BasicModelTest, APITestCase):
    """Test to post, put and patch data"""
    url_key = "placefields"
    factory = PlaceFieldFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        placefield: PlaceField = cls.obj
        infrastructure = placefield.infrastructure.pk
        field_type = placefield.field_type.pk
        data = dict(attribute=faker.unique.word(),
                    unit=faker.word(),
                    infrastructure=infrastructure,
                    field_type=field_type,
                    sensitive=True)
        cls.post_data = data
        cls.put_data = data
        cls.patch_data = data.copy()
        cls.patch_data['sensitive'] = False
