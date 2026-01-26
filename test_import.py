#!/usr/bin/env python
"""Quick test script to verify field imports"""
import sys
sys.path.insert(0, './src')

try:
    from pybase.fields.types.text import TextFieldHandler
    print("✓ TextFieldHandler imported successfully")
except Exception as e:
    print(f"✗ Failed to import TextFieldHandler: {e}")
    sys.exit(1)

try:
    from pybase.fields.base import BaseFieldTypeHandler
    print("✓ BaseFieldTypeHandler imported successfully")
except Exception as e:
    print(f"✗ Failed to import BaseFieldTypeHandler: {e}")
    sys.exit(1)

# Test basic validation
try:
    handler = TextFieldHandler()
    result = handler.validate("test", {"min_length": 2})
    print(f"✓ Basic validation works: {result}")
except Exception as e:
    print(f"✗ Basic validation failed: {e}")
    sys.exit(1)

print("\nAll imports and basic tests passed!")
