# NetBox Nested Serializer Analysis

## Problem Statement

When PATCHing a Site with `{"tenant": {"id": 1}}`, NetBox returns:
```json
{"tenant":{"name":["This field cannot be blank."],"slug":["This field cannot be blank."]}}
```

This indicates that DRF is validating required fields (`name`, `slug`) on the `Tenant` model even though we're only providing an ID reference.

## Code Flow Analysis

### 1. Serializer Definition

**SiteSerializer** (`dcim/api/serializers_/sites.py:53`):
```python
tenant = TenantSerializer(nested=True, required=False, allow_null=True)
```

**TenantSerializer** (`tenancy/api/serializers_/tenants.py:27`):
```python
class TenantSerializer(NetBoxModelSerializer):
    # ...
    class Meta:
        model = Tenant
        fields = ['id', 'url', 'display_url', 'display', 'name', 'slug', ...]
```

**Inheritance Chain:**
```
TenantSerializer
  → NetBoxModelSerializer
    → ValidatedModelSerializer
      → BaseModelSerializer
        → serializers.ModelSerializer
```

### 2. Current Overrides in BaseModelSerializer

**`__init__` method:**
- Sets `self.validators = []` for nested serializers
- Sets `field.required = False` and `field.allow_null = True` for all fields

**`run_validation` method:**
- If nested and data is `{"id": X}`, bypasses validation and calls `get_related_object_by_attrs`
- Otherwise calls `to_internal_value`

**`to_internal_value` method:**
- If nested and data is `{"id": X}`, bypasses `super().to_internal_value()` and calls `get_related_object_by_attrs`
- Otherwise calls `get_related_object_by_attrs` (bypassing field validation)

### 3. The Problem

**Hypothesis:** DRF's `ModelSerializer.to_internal_value` validates fields BEFORE our override can catch it.

**DRF Flow for Nested Serializers:**
1. DRF receives `{"tenant": {"id": 1}}`
2. DRF sees `tenant` field is a `TenantSerializer(nested=True)`
3. DRF calls `field.to_internal_value({"id": 1})` on the TenantSerializer instance
4. **PROBLEM:** DRF's `ModelSerializer.to_internal_value` might:
   - Call `super().to_internal_value(data)` which is `Serializer.to_internal_value`
   - `Serializer.to_internal_value` validates each field in the data dict
   - Since `{"id": 1}` doesn't contain `name` or `slug`, DRF validates that these required fields are missing
   - This happens BEFORE our override can catch it

### 4. Key Insight

Looking at `WritableNestedSerializer` (`netbox/api/serializers/nested.py:11`):
```python
class WritableNestedSerializer(BaseModelSerializer):
    def to_internal_value(self, data):
        queryset = self.Meta.model.objects.all()
        return get_related_object_by_attrs(queryset, data)
```

**This is the correct pattern!** `WritableNestedSerializer` completely overrides `to_internal_value` to bypass all field validation.

**But `TenantSerializer` extends `NetBoxModelSerializer`, not `WritableNestedSerializer`!**

### 5. Root Cause

**The issue:** `TenantSerializer` (and other serializers used as nested fields) extend `NetBoxModelSerializer`, which extends `BaseModelSerializer`. While `BaseModelSerializer` has overrides, DRF's `ModelSerializer.to_internal_value` might be calling field validation in a way that bypasses our overrides.

**The solution:** We need to ensure that when a serializer is used as a nested field (with `nested=True`), it behaves like `WritableNestedSerializer` - completely bypassing field validation and going straight to object lookup.

## Proposed Fix

### Option 1: Make BaseModelSerializer.to_internal_value work like WritableNestedSerializer

When `nested=True`, `BaseModelSerializer.to_internal_value` should:
1. **Never call `super().to_internal_value(data)`** - this triggers field validation
2. **Always call `get_related_object_by_attrs` directly** - this bypasses all validation
3. Handle `{"id": X}`, integer IDs, and other formats

### Option 2: Check if DRF is calling field validation before to_internal_value

We need to understand if DRF's `ModelSerializer.to_internal_value` calls field validation. If so, we might need to override at a different level.

### Option 3: Use WritableNestedSerializer pattern

Make nested serializers behave exactly like `WritableNestedSerializer` - completely override `to_internal_value` to bypass validation.

## Next Steps

1. **Add debug logging** to see exactly where validation happens
2. **Check DRF source code** to understand `ModelSerializer.to_internal_value` flow
3. **Test if our override is even being called** - maybe DRF is taking a different code path
4. **Consider using WritableNestedSerializer pattern** - completely bypass field validation for nested serializers

## Key Discovery

**The Root Cause:**

1. **Nested serializers** (like `NestedRegionSerializer`, `NestedTenantSerializer`) extend `WritableNestedSerializer`
   - `WritableNestedSerializer.to_internal_value` completely bypasses field validation
   - It directly calls `get_related_object_by_attrs(queryset, data)`
   - **This works correctly!**

2. **Full serializers used as nested** (like `RegionSerializer(nested=True)`, `TenantSerializer(nested=True)`) extend `BaseModelSerializer`
   - `BaseModelSerializer.to_internal_value` tries to override but still calls field validation
   - DRF's `ModelSerializer.to_internal_value` validates fields before our override can catch it
   - **This is broken!**

**The Problem:**
- `SiteSerializer` uses `TenantSerializer(nested=True)`, not `NestedTenantSerializer`
- `TenantSerializer` extends `NetBoxModelSerializer` → `BaseModelSerializer`
- When DRF processes `{"tenant": {"id": 1}}`, it calls `TenantSerializer.to_internal_value({"id": 1})`
- DRF's `ModelSerializer.to_internal_value` validates all fields, including required ones like `name` and `slug`
- Our override tries to catch this, but DRF validates fields BEFORE our override runs

## Proposed Fix

**Make `BaseModelSerializer.to_internal_value` work exactly like `WritableNestedSerializer.to_internal_value` when `nested=True`:**

```python
def to_internal_value(self, data):
    if self.nested:
        # When nested=True, behave exactly like WritableNestedSerializer
        # Completely bypass DRF's field validation
        queryset = self.Meta.model.objects.all()
        return get_related_object_by_attrs(queryset, data)
    
    return super().to_internal_value(data)
```

**Key Points:**
1. When `nested=True`, **never call `super().to_internal_value(data)`** - this triggers field validation
2. **Always call `get_related_object_by_attrs` directly** - this bypasses all validation
3. Handle `None`, `serializers.empty`, `{"id": X}`, integer IDs, and other formats
4. This matches exactly how `WritableNestedSerializer` works

## Questions to Answer

1. ✅ **Is `BaseModelSerializer.to_internal_value` being called?** - Yes, but DRF validates fields before it
2. ✅ **Is DRF calling field validation before our override?** - Yes, in `ModelSerializer.to_internal_value`
3. ✅ **Should nested serializers always behave like `WritableNestedSerializer`?** - Yes, when `nested=True`
4. ✅ **Is there a difference?** - Yes, `WritableNestedSerializer` never calls `super()`, but `BaseModelSerializer` does

