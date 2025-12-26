# Current Status - Nested Serializer Fix

## Problem

When PATCHing NetBox resources with nested fields using `{"id": X}` format, DRF is still validating required fields (like `name` and `slug` for Tenant) even though we're trying to bypass validation for nested serializers.

**Error:**
```json
{"tenant":{"name":["This field cannot be blank."],"slug":["This field cannot be blank."]}}
```

## Attempted Fixes

1. ✅ **Disable validators** - Set `self.validators = []` for nested serializers
2. ✅ **Make fields not required** - Set `field.required = False` and `field.allow_null = True`
3. ✅ **Override `run_validation`** - Skip field-level validation, go straight to `to_internal_value`
4. ✅ **Override `to_internal_value`** - Handle `{"id": X}` directly, bypass `super().to_internal_value()`
5. ✅ **Handle integer IDs** - Support both `{"id": X}` and integer `X` formats

## Current Implementation

In `netbox/netbox/api/serializers/base.py`:

```python
def __init__(self, *args, nested=False, fields=None, **kwargs):
    # ... setup code ...
    if self.nested:
        self.validators = []
        for field_name, field in self.fields.items():
            field.required = False
            field.allow_null = True

def run_validation(self, data=serializers.empty):
    if self.nested:
        if data is serializers.empty:
            return None
        if isinstance(data, dict) and len(data) == 1 and "id" in data:
            queryset = self.Meta.model.objects.all()
            return get_related_object_by_attrs(queryset, data)
        elif isinstance(data, int):
            queryset = self.Meta.model.objects.all()
            return get_related_object_by_attrs(queryset, {"id": data})
        return self.to_internal_value(data)
    return super().run_validation(data)

def to_internal_value(self, data):
    if self.nested:
        # ... handle empty values ...
        if isinstance(data, dict) and len(data) == 1 and "id" in data:
            queryset = self.Meta.model.objects.all()
            return get_related_object_by_attrs(queryset, data)
        elif isinstance(data, int):
            queryset = self.Meta.model.objects.all()
            return get_related_object_by_attrs(queryset, {"id": data})
        queryset = self.Meta.model.objects.all()
        return get_related_object_by_attrs(queryset, data)
    return super().to_internal_value(data)
```

## Issue

DRF is still calling field-level validation on `name` and `slug` fields before our overrides can catch it. This suggests that:

1. DRF might be validating fields in `to_internal_value` before our override runs
2. DRF might be calling field validation in a different code path
3. The validation might be happening at the field level, not the serializer level

## Next Steps

1. **Run the tests** - Execute `test_nested_serializer_patch.py` to see exactly where validation fails
2. **Add debug logging** - Add logging to see which code path DRF is taking
3. **Check DRF source** - Understand exactly how DRF processes nested serializers in PATCH requests
4. **Alternative approach** - Maybe we need to override at the field level, not the serializer level

## Test Coverage

We have comprehensive tests in `netbox/dcim/tests/test_nested_serializer_patch.py`:
- Site: tenant, region, site_group
- Prefix: tenant, site, vlan, role
- VLAN: tenant, site, role
- Device: tenant, site, platform, location, device_type, device_role, primary_ip4, primary_ip6

**Total: 23 test methods** covering all controller use cases.

## Docker Images

- `microscaler/netbox:v4.0.0-fix9` - Latest with all fixes applied
- Deployed to Kubernetes but still showing validation errors

## Branch

- `dcops-controller` - Long-lived branch with all fixes
- `test/nested-serializer-patch-tests` - Branch with comprehensive tests

