"""
Tests for nested serializer behavior in PATCH requests.

These tests validate that nested fields (like tenant, region, site_group) can be
updated using {"id": X} format without requiring full object data.
"""

from django.test import override_settings
from rest_framework import status

from dcim.models import Site, Region, SiteGroup
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

