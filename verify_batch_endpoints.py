#!/usr/bin/env python3
"""Verify batch endpoints exist in records router."""

import sys
import ast

# Read the records.py file and check for endpoint definitions
with open('./src/pybase/api/v1/records.py', 'r') as f:
    content = f.read()

# Check for batch endpoint function definitions
required_endpoints = [
    'batch_create_records',
    'batch_update_records',
    'batch_delete_records'
]

required_routes = [
    '/batch/create',
    '/batch/update',
    '/batch/delete'
]

print("Checking for endpoint functions...")
for endpoint in required_endpoints:
    if f'async def {endpoint}' in content:
        print(f"  ✓ Found function: {endpoint}")
    else:
        print(f"  ✗ Missing function: {endpoint}")
        sys.exit(1)

print("\nChecking for route decorators...")
for route in required_routes:
    if f'"{route}"' in content or f"'{route}'" in content:
        print(f"  ✓ Found route: {route}")
    else:
        print(f"  ✗ Missing route: {route}")
        sys.exit(1)

print("\nChecking for schema imports...")
required_imports = [
    'BatchRecordCreate',
    'BatchRecordUpdate',
    'BatchRecordDelete',
    'BatchOperationResponse'
]

for imp in required_imports:
    if imp in content:
        print(f"  ✓ Found import: {imp}")
    else:
        print(f"  ✗ Missing import: {imp}")
        sys.exit(1)

print("\n✓ All batch endpoints verified successfully!")
print("OK")
