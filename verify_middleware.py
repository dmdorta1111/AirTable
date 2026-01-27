#!/usr/bin/env python
"""Verification script for Prometheus middleware."""

import sys
sys.path.insert(0, 'src')

from pybase.middleware.prometheus_middleware import PrometheusMiddleware

print('OK')
