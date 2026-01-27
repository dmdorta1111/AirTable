#!/usr/bin/env python3
"""Verification script for subtask-3-1."""

import sys
sys.path.insert(0, '.')

try:
    from src.pybase.api.v1.extraction import router, bulk_extract
    from src.pybase.services.bulk_extraction import BulkExtractionService
    print("SUCCESS: All imports work correctly")
    print("✓ bulk_extract function imported")
    print("✓ BulkExtractionService imported")
    sys.exit(0)
except Exception as e:
    print(f"FAILURE: Import error: {e}")
    sys.exit(1)
