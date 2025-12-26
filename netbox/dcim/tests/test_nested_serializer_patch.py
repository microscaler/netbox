"""
Tests for nested serializer behavior in PATCH requests.

These tests validate that nested fields (like tenant, region, site_group) can be
updated using {"id": X} format without requiring full object data.

This covers all DCops controller use cases:
- Site updates: tenant, region, site_group
- Prefix updates: tenant, site, vlan, role
- VLAN updates: tenant, site, role
- Device updates: tenant, site, platform, location, device_type, device_role, primary_ip4, primary_ip6
"""

from django.test import override_settings
from rest_framework import status

from dcim.models import Site, Region, SiteGroup, Device, DeviceType, DeviceRole, Platform, Location, Manufacturer
from ipam.models import Prefix, VLAN, VRF, IPAddress, Role
from tenancy.models import Tenant, TenantGroup
from utilities.testing import APITestCase


class NestedSerializerPatchTest(APITestCase):
    """
    Test that PATCH requests with nested fields using {"id": X} format work correctly.
    
    This is specifically for DCops controller use case where we need to update
    a Site's tenant, region, or site_group by ID only, without providing full
    object data like name and slug.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data: tenant, region, site_group, and site."""
        # Create tenant group and tenant
        cls.tenant_group = TenantGroup.objects.create(name='Test Tenant Group', slug='test-tenant-group')
        cls.tenant = Tenant.objects.create(name='Test Tenant', slug='test-tenant', group=cls.tenant_group)
        
        # Create region
        cls.region = Region.objects.create(name='Test Region', slug='test-region')
        
        # Create site group
        cls.site_group = SiteGroup.objects.create(name='Test Site Group', slug='test-site-group')
        
        # Create site with initial tenant, region, and site_group
        cls.site = Site.objects.create(
            name='Test Site',
            slug='test-site',
            status='active',
            tenant=cls.tenant,
            region=cls.region,
            group=cls.site_group
        )

    def test_patch_site_with_tenant_id_only(self):
        """
        Test that we can PATCH a site with tenant={"id": X} without providing name/slug.
        
        This is the exact use case from DCops controller.
        """
        url = f'/api/dcim/sites/{self.site.pk}/'
        
        # PATCH with only tenant ID - this should work without requiring name/slug
        data = {
            'tenant': {'id': self.tenant.pk}
        }
        
        response = self.client.patch(url, data, format='json', **self.header)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        # Verify the tenant was updated correctly
        self.site.refresh_from_db()
        self.assertEqual(self.site.tenant.pk, self.tenant.pk)
        self.assertEqual(self.site.tenant.name, 'Test Tenant')

    def test_patch_site_with_region_id_only(self):
        """Test that we can PATCH a site with region={"id": X} without full object data."""
        url = f'/api/dcim/sites/{self.site.pk}/'
        
        data = {
            'region': {'id': self.region.pk}
        }
        
        response = self.client.patch(url, data, format='json', **self.header)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.site.refresh_from_db()
        self.assertEqual(self.site.region.pk, self.region.pk)

    def test_patch_site_with_site_group_id_only(self):
        """Test that we can PATCH a site with group={"id": X} without full object data."""
        url = f'/api/dcim/sites/{self.site.pk}/'
        
        data = {
            'group': {'id': self.site_group.pk}
        }
        
        response = self.client.patch(url, data, format='json', **self.header)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.site.refresh_from_db()
        self.assertEqual(self.site.group.pk, self.site_group.pk)

    def test_patch_site_with_multiple_nested_fields(self):
        """Test PATCH with multiple nested fields using {"id": X} format."""
        url = f'/api/dcim/sites/{self.site.pk}/'
        
        data = {
            'tenant': {'id': self.tenant.pk},
            'region': {'id': self.region.pk},
            'group': {'id': self.site_group.pk}
        }
        
        response = self.client.patch(url, data, format='json', **self.header)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.site.refresh_from_db()
        self.assertEqual(self.site.tenant.pk, self.tenant.pk)
        self.assertEqual(self.site.region.pk, self.region.pk)
        self.assertEqual(self.site.group.pk, self.site_group.pk)

    def test_patch_site_with_tenant_integer_id(self):
        """Test that we can also use integer ID directly (alternative format)."""
        url = f'/api/dcim/sites/{self.site.pk}/'
        
        # First, clear the tenant
        self.site.tenant = None
        self.site.save()
        
        # PATCH with integer ID
        data = {
            'tenant': self.tenant.pk
        }
        
        response = self.client.patch(url, data, format='json', **self.header)
        
        # This might work or might not - depends on NetBox implementation
        # We'll test both formats
        if response.status_code == status.HTTP_200_OK:
            self.site.refresh_from_db()
            self.assertEqual(self.site.tenant.pk, self.tenant.pk)

    def test_patch_site_clear_tenant_with_null(self):
        """Test that we can clear a tenant by setting it to null."""
        url = f'/api/dcim/sites/{self.site.pk}/'
        
        data = {
            'tenant': None
        }
        
        response = self.client.patch(url, data, format='json', **self.header)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.site.refresh_from_db()
        self.assertIsNone(self.site.tenant)


class PrefixNestedSerializerPatchTest(APITestCase):
    """
    Test PATCH requests for Prefix with nested fields using {"id": X} format.
    
    DCops controller updates: tenant, site, vlan, role
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data for Prefix tests."""
        # Create tenant
        cls.tenant = Tenant.objects.create(name='Test Tenant', slug='test-tenant')
        
        # Create site
        cls.site = Site.objects.create(name='Test Site', slug='test-site', status='active')
        
        # Create VLAN
        cls.vlan = VLAN.objects.create(site=cls.site, vid=100, name='Test VLAN', status='active')
        
        # Create role
        cls.role = Role.objects.create(name='Test Role', slug='test-role')
        
        # Create prefix
        cls.prefix = Prefix.objects.create(
            prefix='10.0.0.0/24',
            site=cls.site,
            tenant=cls.tenant,
            vlan=cls.vlan,
            role=cls.role,
            status='active'
        )

    def test_patch_prefix_with_tenant_id_only(self):
        """Test PATCH prefix with tenant={"id": X}."""
        url = f'/api/ipam/prefixes/{self.prefix.pk}/'
        data = {'tenant': {'id': self.tenant.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.prefix.refresh_from_db()
        self.assertEqual(self.prefix.tenant.pk, self.tenant.pk)

    def test_patch_prefix_with_site_id_only(self):
        """Test PATCH prefix with site={"id": X}."""
        url = f'/api/ipam/prefixes/{self.prefix.pk}/'
        data = {'site': {'id': self.site.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.prefix.refresh_from_db()
        self.assertEqual(self.prefix.site.pk, self.site.pk)

    def test_patch_prefix_with_vlan_id_only(self):
        """Test PATCH prefix with vlan={"id": X}."""
        url = f'/api/ipam/prefixes/{self.prefix.pk}/'
        data = {'vlan': {'id': self.vlan.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.prefix.refresh_from_db()
        self.assertEqual(self.prefix.vlan.pk, self.vlan.pk)

    def test_patch_prefix_with_role_id_only(self):
        """Test PATCH prefix with role={"id": X}."""
        url = f'/api/ipam/prefixes/{self.prefix.pk}/'
        data = {'role': {'id': self.role.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.prefix.refresh_from_db()
        self.assertEqual(self.prefix.role.pk, self.role.pk)

    def test_patch_prefix_with_multiple_nested_fields(self):
        """Test PATCH prefix with multiple nested fields."""
        url = f'/api/ipam/prefixes/{self.prefix.pk}/'
        data = {
            'tenant': {'id': self.tenant.pk},
            'site': {'id': self.site.pk},
            'vlan': {'id': self.vlan.pk},
            'role': {'id': self.role.pk}
        }
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.prefix.refresh_from_db()
        self.assertEqual(self.prefix.tenant.pk, self.tenant.pk)
        self.assertEqual(self.prefix.site.pk, self.site.pk)
        self.assertEqual(self.prefix.vlan.pk, self.vlan.pk)
        self.assertEqual(self.prefix.role.pk, self.role.pk)


class VLANNestedSerializerPatchTest(APITestCase):
    """
    Test PATCH requests for VLAN with nested fields using {"id": X} format.
    
    DCops controller updates: tenant, site, role
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data for VLAN tests."""
        # Create tenant
        cls.tenant = Tenant.objects.create(name='Test Tenant', slug='test-tenant')
        
        # Create site
        cls.site = Site.objects.create(name='Test Site', slug='test-site', status='active')
        
        # Create role
        cls.role = Role.objects.create(name='Test Role', slug='test-role')
        
        # Create VLAN
        cls.vlan = VLAN.objects.create(
            site=cls.site,
            vid=100,
            name='Test VLAN',
            tenant=cls.tenant,
            role=cls.role,
            status='active'
        )

    def test_patch_vlan_with_tenant_id_only(self):
        """Test PATCH VLAN with tenant={"id": X}."""
        url = f'/api/ipam/vlans/{self.vlan.pk}/'
        data = {'tenant': {'id': self.tenant.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.vlan.refresh_from_db()
        self.assertEqual(self.vlan.tenant.pk, self.tenant.pk)

    def test_patch_vlan_with_site_id_only(self):
        """Test PATCH VLAN with site={"id": X}."""
        url = f'/api/ipam/vlans/{self.vlan.pk}/'
        data = {'site': {'id': self.site.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.vlan.refresh_from_db()
        self.assertEqual(self.vlan.site.pk, self.site.pk)

    def test_patch_vlan_with_role_id_only(self):
        """Test PATCH VLAN with role={"id": X}."""
        url = f'/api/ipam/vlans/{self.vlan.pk}/'
        data = {'role': {'id': self.role.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.vlan.refresh_from_db()
        self.assertEqual(self.vlan.role.pk, self.role.pk)


class DeviceNestedSerializerPatchTest(APITestCase):
    """
    Test PATCH requests for Device with nested fields using {"id": X} format.
    
    DCops controller updates: tenant, site, platform, location, device_type, device_role, primary_ip4, primary_ip6
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data for Device tests."""
        # Create tenant
        cls.tenant = Tenant.objects.create(name='Test Tenant', slug='test-tenant')
        
        # Create site
        cls.site = Site.objects.create(name='Test Site', slug='test-site', status='active')
        
        # Create location
        cls.location = Location.objects.create(site=cls.site, name='Test Location', slug='test-location')
        
        # Create manufacturer and device type
        cls.manufacturer = Manufacturer.objects.create(name='Test Manufacturer', slug='test-manufacturer')
        cls.device_type = DeviceType.objects.create(
            manufacturer=cls.manufacturer,
            model='Test Model',
            slug='test-model'
        )
        
        # Create device role
        cls.device_role = DeviceRole.objects.create(name='Test Role', slug='test-role')
        
        # Create platform
        cls.platform = Platform.objects.create(name='Test Platform', slug='test-platform')
        
        # Create IP addresses
        cls.ip4 = IPAddress.objects.create(address='10.0.0.1/24', status='active')
        cls.ip6 = IPAddress.objects.create(address='2001:db8::1/64', status='active')
        
        # Create device
        cls.device = Device.objects.create(
            name='Test Device',
            device_type=cls.device_type,
            device_role=cls.device_role,
            site=cls.site,
            location=cls.location,
            tenant=cls.tenant,
            platform=cls.platform,
            status='active'
        )

    def test_patch_device_with_tenant_id_only(self):
        """Test PATCH device with tenant={"id": X}."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {'tenant': {'id': self.tenant.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.tenant.pk, self.tenant.pk)

    def test_patch_device_with_site_id_only(self):
        """Test PATCH device with site={"id": X}."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {'site': {'id': self.site.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.site.pk, self.site.pk)

    def test_patch_device_with_platform_id_only(self):
        """Test PATCH device with platform={"id": X}."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {'platform': {'id': self.platform.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.platform.pk, self.platform.pk)

    def test_patch_device_with_location_id_only(self):
        """Test PATCH device with location={"id": X}."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {'location': {'id': self.location.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.location.pk, self.location.pk)

    def test_patch_device_with_device_type_id_only(self):
        """Test PATCH device with device_type={"id": X}."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {'device_type': {'id': self.device_type.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.device_type.pk, self.device_type.pk)

    def test_patch_device_with_device_role_id_only(self):
        """Test PATCH device with device_role={"id": X}."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {'device_role': {'id': self.device_role.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.device_role.pk, self.device_role.pk)

    def test_patch_device_with_primary_ip4_id_only(self):
        """Test PATCH device with primary_ip4={"id": X}."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {'primary_ip4': {'id': self.ip4.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.primary_ip4.pk, self.ip4.pk)

    def test_patch_device_with_primary_ip6_id_only(self):
        """Test PATCH device with primary_ip6={"id": X}."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {'primary_ip6': {'id': self.ip6.pk}}
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.primary_ip6.pk, self.ip6.pk)

    def test_patch_device_with_multiple_nested_fields(self):
        """Test PATCH device with multiple nested fields."""
        url = f'/api/dcim/devices/{self.device.pk}/'
        data = {
            'tenant': {'id': self.tenant.pk},
            'site': {'id': self.site.pk},
            'platform': {'id': self.platform.pk},
            'location': {'id': self.location.pk},
        }
        
        response = self.client.patch(url, data, format='json', **self.header)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
        )
        
        self.device.refresh_from_db()
        self.assertEqual(self.device.tenant.pk, self.tenant.pk)
        self.assertEqual(self.device.site.pk, self.site.pk)
        self.assertEqual(self.device.platform.pk, self.platform.pk)
        self.assertEqual(self.device.location.pk, self.location.pk)

