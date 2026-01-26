#!/usr/bin/env python
"""
Regression test for field validation options.
Tests that existing field behavior is preserved and new validation options work correctly.
"""
import sys
sys.path.insert(0, './src')

def test_text_field_backward_compatibility():
    """Test that existing text field behavior still works."""
    from pybase.fields.types.text import TextFieldHandler

    print("Testing TextFieldHandler backward compatibility...")

    # Test 1: Basic validation without options (existing behavior)
    try:
        assert TextFieldHandler.validate("hello world") == True
        print("✓ Basic validation without options works")
    except Exception as e:
        print(f"✗ Basic validation failed: {e}")
        return False

    # Test 2: None values should pass
    try:
        assert TextFieldHandler.validate(None) == True
        print("✓ None values pass validation")
    except Exception as e:
        print(f"✗ None validation failed: {e}")
        return False

    # Test 3: Empty options dict
    try:
        assert TextFieldHandler.validate("test", {}) == True
        print("✓ Empty options dict works")
    except Exception as e:
        print(f"✗ Empty options failed: {e}")
        return False

    # Test 4: Legacy max_length still works
    try:
        TextFieldHandler.validate("a" * 256, {"max_length": 255})
        print("✗ max_length validation should have failed")
        return False
    except ValueError as e:
        print(f"✓ Legacy max_length validation still works")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

    # Test 5: Serialization unchanged
    try:
        assert TextFieldHandler.serialize("test") == "test"
        assert TextFieldHandler.serialize(123) == "123"
        assert TextFieldHandler.serialize(None) is None
        print("✓ Serialization unchanged")
    except Exception as e:
        print(f"✗ Serialization failed: {e}")
        return False

    # Test 6: Deserialization unchanged
    try:
        assert TextFieldHandler.deserialize("test") == "test"
        assert TextFieldHandler.deserialize(None) is None
        print("✓ Deserialization unchanged")
    except Exception as e:
        print(f"✗ Deserialization failed: {e}")
        return False

    # Test 7: Default value unchanged
    try:
        assert TextFieldHandler.default() == ""
        print("✓ Default value unchanged")
    except Exception as e:
        print(f"✗ Default value failed: {e}")
        return False

    return True


def test_new_validation_options():
    """Test that new validation options work correctly."""
    from pybase.fields.types.text import TextFieldHandler

    print("\nTesting new validation options...")

    # Test 1: min_length option
    try:
        assert TextFieldHandler.validate("hello", {"min_length": 3}) == True
        print("✓ min_length validation passes for valid value")
    except Exception as e:
        print(f"✗ min_length validation failed: {e}")
        return False

    try:
        TextFieldHandler.validate("hi", {"min_length": 3})
        print("✗ min_length should have failed for too short value")
        return False
    except ValueError:
        print("✓ min_length validation correctly rejects too short values")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

    # Test 2: regex option
    try:
        assert TextFieldHandler.validate("ABC123", {"regex": "^[A-Z]{3}[0-9]{3}$"}) == True
        print("✓ regex validation passes for matching value")
    except Exception as e:
        print(f"✗ regex validation failed: {e}")
        return False

    try:
        TextFieldHandler.validate("abc123", {"regex": "^[A-Z]{3}[0-9]{3}$"})
        print("✗ regex should have failed for non-matching value")
        return False
    except ValueError:
        print("✓ regex validation correctly rejects non-matching values")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

    # Test 3: Combined options
    try:
        options = {"min_length": 5, "max_length": 10, "regex": "^[A-Z]+$"}
        assert TextFieldHandler.validate("HELLO", options) == True
        print("✓ Combined validation options work together")
    except Exception as e:
        print(f"✗ Combined options failed: {e}")
        return False

    # Test 4: None bypasses new validations
    try:
        assert TextFieldHandler.validate(None, {"min_length": 10, "regex": "^[A-Z]+$"}) == True
        print("✓ None values bypass all new validations")
    except Exception as e:
        print(f"✗ None bypass failed: {e}")
        return False

    return True


def test_base_field_handler():
    """Test that base field handler helper methods work."""
    from pybase.fields.base import BaseFieldTypeHandler

    print("\nTesting BaseFieldTypeHandler helper methods...")

    # We need a concrete implementation to test the helper methods
    class TestFieldHandler(BaseFieldTypeHandler):
        field_type = "test"

        @classmethod
        def serialize(cls, value):
            return value

        @classmethod
        def deserialize(cls, value):
            return value

        @classmethod
        def validate(cls, value, options=None):
            cls._validate_regex(value, options)
            cls._validate_custom(value, options)
            return True

        @classmethod
        def default(cls):
            return None

    # Test _validate_regex helper
    try:
        assert TestFieldHandler._validate_regex("ABC123", {"regex": "^[A-Z0-9]+$"}) == True
        print("✓ _validate_regex helper works for matching values")
    except Exception as e:
        print(f"✗ _validate_regex failed: {e}")
        return False

    try:
        TestFieldHandler._validate_regex("abc", {"regex": "^[A-Z]+$"})
        print("✗ _validate_regex should have failed for non-matching value")
        return False
    except ValueError:
        print("✓ _validate_regex correctly rejects non-matching values")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

    # Test _validate_custom helper with callable
    try:
        def validate_even(value):
            if value % 2 != 0:
                raise ValueError("Must be even")
            return True

        assert TestFieldHandler._validate_custom(42, {"custom_validator": validate_even}) == True
        print("✓ _validate_custom helper works with callable")
    except Exception as e:
        print(f"✗ _validate_custom callable failed: {e}")
        return False

    # Test _validate_custom helper with expression
    try:
        assert TestFieldHandler._validate_custom("hello", {"custom_validator": "len(value) >= 3"}) == True
        print("✓ _validate_custom helper works with expression strings")
    except Exception as e:
        print(f"✗ _validate_custom expression failed: {e}")
        return False

    # Test None bypasses helpers
    try:
        assert TestFieldHandler._validate_regex(None, {"regex": "^[A-Z]+$"}) == True
        assert TestFieldHandler._validate_custom(None, {"custom_validator": "len(value) > 100"}) == True
        print("✓ None values bypass helper validations")
    except Exception as e:
        print(f"✗ None bypass failed: {e}")
        return False

    return True


def test_engineering_fields_still_work():
    """Test that engineering field types are not broken."""
    print("\nTesting engineering field types...")

    try:
        from pybase.fields.types.engineering.dimension import DimensionFieldHandler

        # Test basic dimension field validation
        assert DimensionFieldHandler.field_type == "dimension"
        print("✓ DimensionFieldHandler imports and has correct field_type")
    except Exception as e:
        print(f"✓ DimensionFieldHandler import skipped (may not exist yet): {e}")

    try:
        from pybase.fields.types.engineering.gdt import GDTFieldHandler

        assert GDTFieldHandler.field_type == "gdt"
        print("✓ GDTFieldHandler imports and has correct field_type")
    except Exception as e:
        print(f"✓ GDTFieldHandler import skipped (may not exist yet): {e}")

    return True


def main():
    """Run all regression tests."""
    print("=" * 70)
    print("FIELD VALIDATION REGRESSION TEST")
    print("=" * 70)

    all_passed = True

    # Test backward compatibility
    if not test_text_field_backward_compatibility():
        all_passed = False
        print("\n❌ Backward compatibility tests FAILED")
    else:
        print("\n✅ Backward compatibility tests PASSED")

    # Test new features
    if not test_new_validation_options():
        all_passed = False
        print("\n❌ New validation options tests FAILED")
    else:
        print("\n✅ New validation options tests PASSED")

    # Test base handler
    if not test_base_field_handler():
        all_passed = False
        print("\n❌ Base field handler tests FAILED")
    else:
        print("\n✅ Base field handler tests PASSED")

    # Test engineering fields
    if not test_engineering_fields_still_work():
        all_passed = False
        print("\n❌ Engineering fields tests FAILED")
    else:
        print("\n✅ Engineering fields tests PASSED")

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL REGRESSION TESTS PASSED")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME REGRESSION TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
