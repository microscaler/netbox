# NetBox Test Coverage for DCops Controller

## Overview

This document tracks the comprehensive test coverage we've added for all DCops controller use cases involving nested serializer fields in PATCH requests.

## Test File

`netbox/dcim/tests/test_nested_serializer_patch.py`

## Test Classes

### 1. `NestedSerializerPatchTest` - Site Updates
Tests for Site PATCH operations with nested fields:
- ✅ `test_patch_site_with_tenant_id_only` - **PRIMARY USE CASE** (currently failing)
- ✅ `test_patch_site_with_region_id_only`
- ✅ `test_patch_site_with_site_group_id_only`
- ✅ `test_patch_site_with_multiple_nested_fields`
- ✅ `test_patch_site_with_tenant_integer_id` (alternative format)
- ✅ `test_patch_site_clear_tenant_with_null`

**Nested Fields Tested:**
- `tenant` (Tenant)
- `region` (Region)
- `group` (SiteGroup)

### 2. `PrefixNestedSerializerPatchTest` - Prefix Updates
Tests for Prefix PATCH operations with nested fields:
- ✅ `test_patch_prefix_with_tenant_id_only`
- ✅ `test_patch_prefix_with_site_id_only`
- ✅ `test_patch_prefix_with_vlan_id_only`
- ✅ `test_patch_prefix_with_role_id_only`
- ✅ `test_patch_prefix_with_multiple_nested_fields`

**Nested Fields Tested:**
- `tenant` (Tenant)
- `site` (Site)
- `vlan` (VLAN)
- `role` (Role)

### 3. `VLANNestedSerializerPatchTest` - VLAN Updates
Tests for VLAN PATCH operations with nested fields:
- ✅ `test_patch_vlan_with_tenant_id_only`
- ✅ `test_patch_vlan_with_site_id_only`
- ✅ `test_patch_vlan_with_role_id_only`

**Nested Fields Tested:**
- `tenant` (Tenant)
- `site` (Site)
- `role` (Role)

### 4. `DeviceNestedSerializerPatchTest` - Device Updates
Tests for Device PATCH operations with nested fields:
- ✅ `test_patch_device_with_tenant_id_only`
- ✅ `test_patch_device_with_site_id_only`
- ✅ `test_patch_device_with_platform_id_only`
- ✅ `test_patch_device_with_location_id_only`
- ✅ `test_patch_device_with_device_type_id_only`
- ✅ `test_patch_device_with_device_role_id_only`
- ✅ `test_patch_device_with_primary_ip4_id_only`
- ✅ `test_patch_device_with_primary_ip6_id_only`
- ✅ `test_patch_device_with_multiple_nested_fields`

**Nested Fields Tested:**
- `tenant` (Tenant)
- `site` (Site)
- `platform` (Platform)
- `location` (Location)
- `device_type` (DeviceType)
- `device_role` (DeviceRole)
- `primary_ip4` (IPAddress)
- `primary_ip6` (IPAddress)

## Current Status

### Tests Created
- ✅ All test classes and methods created
- ✅ Test data setup complete
- ✅ Tests cover all controller update methods

### Tests Status
- ⏳ **Not yet run** - Need to set up test environment
- ⏳ Expected to fail with current NetBox code (validation errors)

### Known Issues (from Controller Logs)
1. **Site.tenant** - `{"name":["This field cannot be blank."],"slug":["This field cannot be blank."]}`
   - This is the primary error we're seeing
   - Test: `test_patch_site_with_tenant_id_only`

## Next Steps

1. **Set up test environment** - Configure NetBox test database
2. **Run tests** - Execute all test classes to see failures
3. **Fix NetBox code** - Update `base.py` until all tests pass
4. **Verify** - Run tests again to confirm fixes
5. **Deploy** - Build Docker image and deploy
6. **Validate from Rust** - Confirm controller works (should be quick since tests passed)

## Test Format

All tests follow this pattern:
```python
def test_patch_X_with_Y_id_only(self):
    """Test PATCH X with Y={"id": X}."""
    url = f'/api/.../{self.obj.pk}/'
    data = {'Y': {'id': self.y.pk}}
    
    response = self.client.patch(url, data, format='json', **self.header)
    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
        f"Expected 200 OK, got {response.status_code}. Response: {response.data}"
    )
    
    self.obj.refresh_from_db()
    self.assertEqual(self.obj.Y.pk, self.y.pk)
```

## Running Tests

Once test environment is set up:
```bash
# Run all nested serializer tests
python3 netbox/manage.py test dcim.tests.test_nested_serializer_patch

# Run specific test class
python3 netbox/manage.py test dcim.tests.test_nested_serializer_patch.NestedSerializerPatchTest

# Run specific test
python3 netbox/manage.py test dcim.tests.test_nested_serializer_patch.NestedSerializerPatchTest.test_patch_site_with_tenant_id_only
```

## Expected Failures

All tests are expected to fail initially with validation errors like:
- `{"tenant":{"name":["This field cannot be blank."],"slug":["This field cannot be blank."]}}`

This confirms the tests are correctly identifying the issues we need to fix.

