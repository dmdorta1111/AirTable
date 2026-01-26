#!/usr/bin/env python
"""Simple regression test for field validation - tests code directly"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="* 70)
print("FIELD VALIDATION SIMPLE REGRESSION TEST")
print("=" * 70)

# Test 1: Import test
print("\n[TEST 1] Testing imports...")
try:
    import pybase.fields.base
    print("✓ pybase.fields.base imported")
except Exception as e:
    print(f"✗ Failed to import pybase.fields.base: {e}")
    sys.exit(1)

try:
    import pybase.fields.types.text
    print("✓ pybase.fields.types.text imported")
except Exception as e:
    print(f"✗ Failed to import pybase.fields.types.text: {e}")
    sys.exit(1)

# Test 2: Check classes exist
print("\n[TEST 2] Checking classes exist...")
from pybase.fields.base import BaseFieldTypeHandler
from pybase.fields.types.text import TextFieldHandler

print(f"✓ BaseFieldTypeHandler exists: {BaseFieldTypeHandler}")
print(f"✓ TextFieldHandler exists: {TextFieldHandler}")

# Test 3: Check new methods exist
print("\n[TEST 3] Checking new validation helper methods...")
if hasattr(BaseFieldTypeHandler, '_validate_regex'):
    print("✓ BaseFieldTypeHandler has _validate_regex method")
else:
    print("✗ BaseFieldTypeHandler missing _validate_regex method")
    sys.exit(1)

if hasattr(BaseFieldTypeHandler, '_validate_custom'):
    print("✓ BaseFieldTypeHandler has _validate_custom method")
else:
    print("✗ BaseFieldTypeHandler missing _validate_custom method")
    sys.exit(1)

# Test 4: Test backward compatibility
print("\n[TEST 4] Testing backward compatibility...")

# Basic validation without options
result = TextFieldHandler.validate("hello world")
assert result == True, "Basic validation failed"
print("✓ Basic validation without options works")

# None values
result = TextFieldHandler.validate(None)
assert result == True, "None validation failed"
print("✓ None values pass validation")

# Empty options
result = TextFieldHandler.validate("test", {})
assert result == True, "Empty options failed"
print("✓ Empty options dict works")

# Serialization
assert TextFieldHandler.serialize("test") == "test"
assert TextFieldHandler.serialize(None) is None
print("✓ Serialization works")

# Deserialization
assert TextFieldHandler.deserialize("test") == "test"
assert TextFieldHandler.deserialize(None) is None
print("✓ Deserialization works")

# Default
assert TextFieldHandler.default() == ""
print("✓ Default value works")

# Test 5: Test new min_length option
print("\n[TEST 5] Testing new min_length validation option...")

result = TextFieldHandler.validate("hello", {"min_length": 3})
assert result == True
print("✓ min_length passes for valid value")

try:
    TextFieldHandler.validate("hi", {"min_length": 3})
    print("✗ min_length should have rejected short value")
    sys.exit(1)
except ValueError:
    print("✓ min_length rejects too short values")

# Test 6: Test new regex option
print("\n[TEST 6] Testing new regex validation option...")

result = TextFieldHandler.validate("ABC123", {"regex": "^[A-Z]{3}[0-9]{3}$"})
assert result == True
print("✓ regex passes for matching value")

try:
    TextFieldHandler.validate("abc123", {"regex": "^[A-Z]{3}[0-9]{3}$"})
    print("✗ regex should have rejected non-matching value")
    sys.exit(1)
except ValueError:
    print("✓ regex rejects non-matching values")

# Test 7: Test combined validation options
print("\n[TEST 7] Testing combined validation options...")

options = {"min_length": 5, "max_length": 10, "regex": "^[A-Z]+$"}
result = TextFieldHandler.validate("HELLO", options)
assert result == True
print("✓ Combined validation options work together")

# Test None bypasses all validations
result = TextFieldHandler.validate(None, {"min_length": 10, "regex": "^[A-Z]+$"})
assert result == True
print("✓ None bypasses all new validations")

# Test 8: Test base handler helpers
print("\n[TEST 8] Testing base handler helper methods...")

# Test _validate_regex
result = BaseFieldTypeHandler._validate_regex("ABC123", {"regex": "^[A-Z0-9]+$"})
assert result == True
print("✓ _validate_regex works for matching values")

try:
    BaseFieldTypeHandler._validate_regex("abc", {"regex": "^[A-Z]+$"})
    print("✗ _validate_regex should have rejected non-matching value")
    sys.exit(1)
except ValueError:
    print("✓ _validate_regex rejects non-matching values")

# Test _validate_custom with callable
def validate_even(value):
    if value % 2 != 0:
        raise ValueError("Must be even")
    return True

result = BaseFieldTypeHandler._validate_custom(42, {"custom_validator": validate_even})
assert result == True
print("✓ _validate_custom works with callable")

# Test _validate_custom with expression
result = BaseFieldTypeHandler._validate_custom("hello", {"custom_validator": "len(value) >= 3"})
assert result == True
print("✓ _validate_custom works with expression strings")

# Test None bypasses helpers
result = BaseFieldTypeHandler._validate_regex(None, {"regex": "^[A-Z]+$"})
assert result == True
result = BaseFieldTypeHandler._validate_custom(None, {"custom_validator": "len(value) > 100"})
assert result == True
print("✓ None bypasses helper validations")

print("\n" + "=" * 70)
print("✅ ALL REGRESSION TESTS PASSED")
print("=" * 70)
print("\nSummary:")
print("- Existing field behavior preserved (backward compatible)")
print("- New min_length validation option works correctly")
print("- New regex validation option works correctly")
print("- Combined validation options work together")
print("- Base handler helper methods work correctly")
print("- None values correctly bypass all validations")
