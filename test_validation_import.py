"""Test script to verify ValidationService can be imported."""
import sys
import ast

# Verify the file has valid Python syntax
with open('src/pybase/services/validation.py', 'r') as f:
    code = f.read()
    try:
        ast.parse(code)
        print("✓ Syntax is valid")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        sys.exit(1)

# Check that the class is defined
if 'class ValidationService' in code:
    print("✓ ValidationService class is defined")
else:
    print("✗ ValidationService class not found")
    sys.exit(1)

# Check for required methods
required_methods = [
    'validate_record_data',
    '_check_unique_constraint',
    '_values_equal',
    'validate_field_update',
]

for method in required_methods:
    if f'def {method}' in code:
        print(f"✓ Method {method} is defined")
    else:
        print(f"✗ Method {method} not found")
        sys.exit(1)

print("\n✓ All checks passed!")
print("OK")
