#!/usr/bin/env python3
"""Verify BulkExtractionService refactoring."""
import sys
sys.path.insert(0, 'src')

from pybase.services.bulk_extraction import BulkExtractionService

# Check that class exists and has the right signature
import inspect
sig = inspect.signature(BulkExtractionService.__init__)
params = list(sig.parameters.keys())

# Should have 'self', 'db', 'job_id'
assert 'db' in params, f"Missing 'db' parameter in __init__. Got: {params}"
assert 'job_id' in params, f"Missing 'job_id' parameter in __init__. Got: {params}"

print("BulkExtractionService refactored")
