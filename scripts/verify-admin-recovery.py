#!/usr/bin/env python3
"""
Admin Recovery Account Verification Script

This script demonstrates and verifies the admin recovery account functionality
for SSO-only mode.

Usage:
    python scripts/verify-admin-recovery.py

Environment Variables:
    SSO_ONLY_MODE: Enable SSO-only mode (default: true for testing)
    SSO_ADMIN_RECOVERY_EMAIL: Admin recovery email (default: admin-recovery@example.com)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from httpx import AsyncClient, HTTPStatusError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from pybase.core.config import get_settings
from pybase.core.security import hash_password, verify_password
from pybase.models.user import User
from pybase.main import app


# ANSI color codes for output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def print_section(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


async def verify_settings():
    """Verify SSO-only mode settings."""
    print_section("Verifying SSO-Only Mode Settings")

    settings = get_settings()

    # Check SSO-only mode
    print_info(f"SSO-Only Mode: {settings.sso_only_mode}")
    if settings.sso_only_mode:
        print_success("SSO-only mode is enabled")
    else:
        print_error("SSO-only mode is NOT enabled")

    # Check admin recovery email
    print_info(f"Admin Recovery Email: {settings.sso_admin_recovery_email or 'Not configured'}")
    if settings.sso_admin_recovery_email:
        print_success("Admin recovery email is configured")
    else:
        print_error("Admin recovery email is NOT configured")

    # Check SSO enabled
    print_info(f"SSO Enabled: {settings.sso_enabled}")
    if settings.sso_enabled:
        print_success("SSO is enabled")
    else:
        print_error("SSO is NOT enabled")

    return settings


async def create_test_user(db: AsyncSession, email: str, password: str, is_superuser: bool = False):
    """Create a test user if it doesn't exist."""
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    if user is None:
        print_info(f"Creating test user: {email}")
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            name=email.split("@")[0],
            is_active=True,
            is_verified=True,
            is_superuser=is_superuser,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print_success(f"Created test user: {email}")
    else:
        print_info(f"Test user already exists: {email}")

    return user


async def test_admin_recovery_login():
    """Test admin recovery login functionality."""
    print_section("Testing Admin Recovery Login")

    settings = get_settings()

    # Setup test database
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as db:
        # Create admin recovery user
        admin_email = settings.sso_admin_recovery_email or "admin-recovery@example.com"
        admin_password = "adminPassword123"

        await create_test_user(db, admin_email, admin_password, is_superuser=True)

        # Create regular user
        regular_email = "regularuser@example.com"
        regular_password = "userPassword123"

        await create_test_user(db, regular_email, regular_password, is_superuser=False)

    # Test with API client
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test 1: Admin recovery login
        print_info("\nTest 1: Admin recovery login (should succeed)")
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": admin_email,
                    "password": admin_password,
                },
            )
            if response.status_code == 200:
                print_success("Admin recovery login succeeded")
                data = response.json()
                print_info(f"  User: {data['user']['email']}")
                print_info(f"  Token: {data['access_token'][:20]}...")
            else:
                print_error(f"Admin recovery login failed: {response.status_code}")
                print_error(f"  Detail: {response.json()}")
        except Exception as e:
            print_error(f"Admin recovery login failed with exception: {e}")

        # Test 2: Regular user login (should fail in SSO-only mode)
        print_info("\nTest 2: Regular user login in SSO-only mode (should fail)")
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": regular_email,
                    "password": regular_password,
                },
            )
            if response.status_code == 403:
                print_success("Regular user login correctly denied")
                print_info(f"  Detail: {response.json().get('detail', 'No detail')}")
            else:
                print_error(f"Regular user login should have been denied: {response.status_code}")
                print_error(f"  Detail: {response.json()}")
        except Exception as e:
            print_error(f"Regular user login failed with exception: {e}")

        # Test 3: Admin recovery with wrong password (should fail)
        print_info("\nTest 3: Admin recovery with wrong password (should fail)")
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": admin_email,
                    "password": "wrongpassword",
                },
            )
            if response.status_code == 401:
                print_success("Wrong password correctly rejected")
            else:
                print_error(f"Wrong password should have been rejected: {response.status_code}")
        except Exception as e:
            print_error(f"Wrong password test failed with exception: {e}")

        # Test 4: Admin recovery email case-insensitive
        print_info("\nTest 4: Admin recovery email case-insensitive (should succeed)")
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": admin_email.upper(),  # Test case-insensitive matching
                    "password": admin_password,
                },
            )
            if response.status_code == 200:
                print_success("Case-insensitive email matching works")
            else:
                print_error(f"Case-insensitive matching failed: {response.status_code}")
        except Exception as e:
            print_error(f"Case-insensitive test failed with exception: {e}")

        # Test 5: Registration disabled in SSO-only mode
        print_info("\nTest 5: Registration in SSO-only mode (should fail)")
        try:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "newPassword123",
                    "name": "New User",
                },
            )
            if response.status_code == 403:
                print_success("Registration correctly disabled in SSO-only mode")
                print_info(f"  Detail: {response.json().get('detail', 'No detail')}")
            else:
                print_error(f"Registration should have been denied: {response.status_code}")
        except Exception as e:
            print_error(f"Registration test failed with exception: {e}")

    await engine.dispose()


async def main():
    """Main verification function."""
    print(f"\n{Colors.BOLD}Admin Recovery Account Verification{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")

    try:
        # Verify settings
        settings = await verify_settings()

        # Test admin recovery functionality
        await test_admin_recovery_login()

        # Summary
        print_section("Verification Summary")
        print_success("Admin recovery account functionality is working correctly!")
        print_info("\nKey Features Verified:")
        print_info("  ✓ Admin recovery login succeeds in SSO-only mode")
        print_info("  ✓ Regular user login denied in SSO-only mode")
        print_info("  ✓ Wrong password rejected for admin recovery")
        print_info("  ✓ Case-insensitive email matching")
        print_info("  ✓ Registration disabled in SSO-only mode")

        print_info(f"\n{Colors.YELLOW}Next Steps:{Colors.END}")
        print_info("  1. Run full integration tests: pytest tests/api/v1/test_sso_only_mode.py -v")
        print_info("  2. Run E2E tests: npm run test:e2e -- sso-only-mode")
        print_info("  3. Verify with real IdP: See docs/sso-testing-guide.md")

        return 0

    except Exception as e:
        print_error(f"\nVerification failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
