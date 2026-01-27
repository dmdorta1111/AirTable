#!/usr/bin/env python3
"""Standalone script to verify security module changes."""

import ast
import sys

def check_verify_token_is_async():
    """Check that verify_token is now async."""
    with open("src/pybase/core/security.py", "r") as f:
        content = f.read()

    # Parse the file
    tree = ast.parse(content)

    # Find verify_token function
    for node in ast.walk(tree):
        if (isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef)) and node.name == "verify_token":
            if isinstance(node, ast.AsyncFunctionDef):
                print("✓ verify_token is now async")
                return True
            else:
                print("✗ verify_token is not async")
                return False

    print("✗ verify_token not found")
    return False

def check_redis_import():
    """Check that RedisSessionStore is imported."""
    with open("src/pybase/core/security.py", "r") as f:
        content = f.read()

    if "from pybase.core.session_store import RedisSessionStore" in content:
        print("✓ RedisSessionStore is imported")
        return True
    else:
        print("✗ RedisSessionStore not imported")
        return False

def check_blacklist_logic():
    """Check that blacklist checking logic is present."""
    with open("src/pybase/core/security.py", "r") as f:
        content = f.read()

    checks = [
        ("is_token_blacklisted", "is_token_blacklisted method call"),
        ("session_store", "session_store instance"),
        ("if payload.jti:", "JTI check"),
        ("if is_blacklisted:", "blacklist result check"),
    ]

    all_found = True
    for check_str, desc in checks:
        if check_str in content:
            print(f"✓ Found {desc}")
        else:
            print(f"✗ Missing {desc}")
            all_found = False

    return all_found

def check_await_calls():
    """Check that verify_token calls are properly awaited."""
    files_to_check = [
        ("src/pybase/api/deps.py", "await verify_token"),
        ("src/pybase/api/v1/auth.py", "await verify_token"),
        ("src/pybase/api/v1/realtime.py", "await verify_token"),
    ]

    all_found = True
    for filepath, expected in files_to_check:
        with open(filepath, "r") as f:
            content = f.read()
            if expected in content:
                print(f"✓ {filepath} has await verify_token")
            else:
                print(f"✗ {filepath} missing await")
                all_found = False

    return all_found

def main():
    """Run all checks."""
    print("=== Verifying Security Module Changes ===\n")

    print("1. Checking verify_token is async:")
    check1 = check_verify_token_is_async()
    print()

    print("2. Checking RedisSessionStore import:")
    check2 = check_redis_import()
    print()

    print("3. Checking blacklist logic:")
    check3 = check_blacklist_logic()
    print()

    print("4. Checking await calls in dependent files:")
    check4 = check_await_calls()
    print()

    print("=== Summary ===")
    if all([check1, check2, check3, check4]):
        print("✓ All checks passed!")
        return 0
    else:
        print("✗ Some checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
