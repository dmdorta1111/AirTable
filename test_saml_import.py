#!/usr/bin/env python3
"""Test script to verify SAMLService imports correctly."""

import sys
sys.path.insert(0, 'src')

try:
    from pybase.services.saml_service import SAMLService
    print("SAMLService imported successfully")
    sys.exit(0)
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)
