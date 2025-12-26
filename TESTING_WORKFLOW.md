# Testing Workflow for NetBox Nested Serializer Fixes

## Problem

Previously, we were fixing NetBox code, building Docker images, deploying, and testing from the Rust controller - a very slow feedback loop (10-15 minutes per iteration).

## Solution

Add unit tests directly in NetBox that validate our specific use case, then fix the code until tests pass. This provides:
- **Fast feedback** (seconds instead of minutes)
- **Confidence** that fixes work before deploying
- **Regression prevention** for future changes

## Test File

`netbox/dcim/tests/test_nested_serializer_patch.py` contains tests for:
- PATCH site with `tenant={"id": X}` (our primary use case)
- PATCH site with `region={"id": X}`
- PATCH site with `group={"id": X}`
- PATCH with multiple nested fields
- Clearing nested fields with null

## Running Tests

### Option 1: Using NetBox's test infrastructure (recommended)

If you have a NetBox development environment set up:

```bash
cd /path/to/netbox
python3 netbox/manage.py test dcim.tests.test_nested_serializer_patch
```

### Option 2: Using Docker (if development env not available)

You'll need to set up a test database and configuration. This is more complex but possible.

### Option 3: Manual API testing (current fallback)

Use curl or the Rust client to test directly against a running NetBox instance, but this is slower.

## Workflow

1. **Write/Update Tests**: Add tests in `test_nested_serializer_patch.py` for the specific behavior needed
2. **Run Tests**: Execute tests to see what fails
3. **Fix Code**: Update `netbox/netbox/api/serializers/base.py` until tests pass
4. **Iterate**: Repeat steps 2-3 until all tests pass
5. **Deploy**: Build Docker image and deploy
6. **Verify**: Confirm from Rust controller that it works (should be quick since tests already passed)

## Current Status

- ✅ Tests created in `test_nested_serializer_patch.py`
- ⏳ Need to run tests to identify failures
- ⏳ Fix code until tests pass
- ⏳ Deploy and verify from Rust controller

## Next Steps

1. Set up NetBox test environment or find way to run tests
2. Run `test_patch_site_with_tenant_id_only` - this should currently fail
3. Fix `base.py` until test passes
4. Run all tests to ensure nothing broke
5. Merge to `dcops-controller` branch
6. Build and deploy new image
7. Verify from Rust controller (should work immediately)

