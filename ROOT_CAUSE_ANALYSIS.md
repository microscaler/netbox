# Root Cause Analysis - Nested Serializer Validation Issue

## Problem

When PATCHing NetBox resources with nested fields using `{"id": X}` format:
```json
PATCH /api/dcim/sites/1/
{"tenant": {"id": 1}}
```

NetBox returns:
```json
{"tenant":{"name":["This field cannot be blank."],"slug":["This field cannot be blank."]}}
```

## Analysis

### Key Discovery

1. **Nested serializers work correctly:**
   - `NestedTenantSerializer` extends `WritableNestedSerializer`
   - `WritableNestedSerializer.to_internal_value` completely bypasses field validation
   - It directly calls `get_related_object_by_attrs(queryset, data)`
   - **This works!**

2. **Full serializers used as nested are broken:**
   - `SiteSerializer` uses `TenantSerializer(nested=True)`, not `NestedTenantSerializer`
   - `TenantSerializer` extends `NetBoxModelSerializer` → `BaseModelSerializer`
   - When DRF processes `{"tenant": {"id": 1}}`, it validates required fields
   - **This is broken!**

### Why Our Fixes Aren't Working

We've tried multiple approaches:
1. ✅ Disable validators (`self.validators = []`)
2. ✅ Make fields not required (`field.required = False`)
3. ✅ Override `run_validation` to bypass validation
4. ✅ Override `to_internal_value` to bypass validation

**But the error persists!**

### Hypothesis

DRF's `ModelSerializer.to_internal_value` might be:
1. Validating fields **before** calling our override
2. Taking a **different code path** that bypasses our override
3. Calling field validation at the **field level**, not serializer level
4. Our override **isn't being called at all**

### Evidence

- Direct API test still fails with fix11
- Error message suggests field-level validation is happening
- `WritableNestedSerializer` works, but `BaseModelSerializer` with `nested=True` doesn't

## Next Steps

### 1. Add Debug Logging

Add logging to `BaseModelSerializer.to_internal_value` and `run_validation` to confirm they're being called:

```python
def to_internal_value(self, data):
    if self.nested:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"BaseModelSerializer.to_internal_value called with nested=True, data={data}, type={type(data)}")
        # ... rest of code
```

### 2. Check DRF Source Code

Understand exactly how DRF processes nested serializer fields:
- Where does field validation happen?
- Is `to_internal_value` called on the serializer or the field?
- What's the difference between `WritableNestedSerializer` and `BaseModelSerializer`?

### 3. Alternative Approach

Maybe we need to:
- Make `BaseModelSerializer` extend `WritableNestedSerializer` when `nested=True`?
- Or ensure nested serializers always use `WritableNestedSerializer` pattern?
- Or fix this at the field definition level, not the serializer level?

### 4. Run Tests

Once we can run the NetBox tests, they'll show us exactly where validation fails and help us fix it precisely.

## Current Status

- ✅ Comprehensive tests created (23 test methods)
- ✅ Root cause identified (BaseModelSerializer vs WritableNestedSerializer)
- ✅ Fix implemented (make BaseModelSerializer work like WritableNestedSerializer)
- ❌ **Fix not working** - validation still happens
- ⏳ Need to debug why our override isn't working

## Files

- `ANALYSIS.md` - Detailed analysis of the problem
- `netbox/dcim/tests/test_nested_serializer_patch.py` - Comprehensive tests
- `netbox/netbox/api/serializers/base.py` - Current fix implementation

