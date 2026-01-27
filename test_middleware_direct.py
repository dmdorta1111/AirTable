#!/usr/bin/env python
"""Direct verification of Prometheus middleware module."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the module directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "prometheus_middleware",
    "src/pybase/middleware/prometheus_middleware.py"
)
module = importlib.util.module_from_spec(spec)

# Check if the file exists and is valid
print("Checking if PrometheusMiddleware class exists...")
print("File exists:", os.path.exists("src/pybase/middleware/prometheus_middleware.py"))

with open("src/pybase/middleware/prometheus_middleware.py", "r") as f:
    content = f.read()
    if "class PrometheusMiddleware" in content:
        print("PrometheusMiddleware class found: OK")
        print("\nAll checks passed!")
    else:
        print("PrometheusMiddleware class NOT found")
        sys.exit(1)
