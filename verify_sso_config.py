#!/usr/bin/env python
"""Verification script for SSO configuration settings."""

import sys
sys.path.insert(0, 'src')

try:
    from pybase.core.config import Settings

    # Create settings instance
    settings = Settings()

    # Verify SSO settings exist
    checks = [
        ('sso_enabled', hasattr(settings, 'sso_enabled')),
        ('saml_enabled', hasattr(settings, 'saml_enabled')),
        ('oidc_enabled', hasattr(settings, 'oidc_enabled')),
        ('sso_only_mode', hasattr(settings, 'sso_only_mode')),
        ('sso_jit_provisioning', hasattr(settings, 'sso_jit_provisioning')),
        ('saml_idp_metadata_url', hasattr(settings, 'saml_idp_metadata_url')),
        ('oidc_client_id', hasattr(settings, 'oidc_client_id')),
    ]

    all_passed = True
    for attr_name, exists in checks:
        status = "✓" if exists else "✗"
        print(f"{status} {attr_name}: {exists}")
        if not exists:
            all_passed = False

    # Test values
    print(f"\nDefault values:")
    print(f"  sso_enabled: {settings.sso_enabled}")
    print(f"  sso_only_mode: {settings.sso_only_mode}")
    print(f"  sso_jit_provisioning: {settings.sso_jit_provisioning}")

    # Test property methods
    print(f"\nProperty methods:")
    print(f"  saml_enabled: {settings.saml_enabled}")
    print(f"  oidc_enabled: {settings.oidc_enabled}")

    if all_passed:
        print("\n✓ All SSO configuration settings are present!")
        sys.exit(0)
    else:
        print("\n✗ Some SSO configuration settings are missing!")
        sys.exit(1)

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
