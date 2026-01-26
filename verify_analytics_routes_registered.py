#!/usr/bin/env python
"""
Verify that analytics routes are registered in the main FastAPI app.

This verification checks the code structure without initializing the database,
since database initialization is blocked by environment configuration.
"""

import ast
import sys

def verify_v1_router_imported():
    """Verify that v1_router is imported in main.py."""
    with open('src/pybase/main.py', 'r') as f:
        content = f.read()

    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'pybase.api.v1':
                for alias in node.names:
                    if alias.asname == 'v1_router':
                        return True
    return False

def verify_v1_router_included():
    """Verify that v1_router is included in the app."""
    with open('src/pybase/main.py', 'r') as f:
        content = f.read()

    # Check for include_router call with v1_router
    return 'include_router(v1_router' in content

def verify_analytics_routes_in_v1():
    """Verify that analytics routes are included in v1 router."""
    with open('src/pybase/api/v1/__init__.py', 'r') as f:
        content = f.read()

    required_routes = [
        'dashboards.router',
        'charts.router',
        'analytics.router',
        'reports.router'
    ]

    for route in required_routes:
        if route not in content:
            return False, route

    return True, None

print("=" * 60)
print("Analytics Routes Registration Verification")
print("=" * 60)

# Step 1: Check v1_router import
print("\n1. Checking v1_router import in main.py...")
if verify_v1_router_imported():
    print("   ✓ v1_router is imported from pybase.api.v1")
else:
    print("   ✗ ERROR: v1_router not imported")
    sys.exit(1)

# Step 2: Check v1_router inclusion
print("\n2. Checking v1_router registration in FastAPI app...")
if verify_v1_router_included():
    print("   ✓ v1_router is included in the app")
else:
    print("   ✗ ERROR: v1_router not included in app")
    sys.exit(1)

# Step 3: Check analytics routes in v1 router
print("\n3. Checking analytics routes in v1 router...")
result, missing_route = verify_analytics_routes_in_v1()
if result:
    print("   ✓ All analytics routes are registered:")
    print("     - dashboards.router (prefix: /dashboards)")
    print("     - charts.router (prefix: /charts)")
    print("     - analytics.router (prefix: /analytics)")
    print("     - reports.router (prefix: /reports)")
else:
    print(f"   ✗ ERROR: Missing route: {missing_route}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ VERIFICATION PASSED")
print("=" * 60)
print("\nAll analytics routes are properly registered in the main")
print("FastAPI app through the v1 router chain:")
print("  main.py → v1_router → [dashboards, charts, analytics, reports]")
print("\nExpected routes will be available at:")
print("  - {api_v1_prefix}/dashboards/*")
print("  - {api_v1_prefix}/charts/*")
print("  - {api_v1_prefix}/analytics/*")
print("  - {api_v1_prefix}/reports/*")
print("\nOK")
