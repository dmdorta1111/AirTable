#!/usr/bin/env python3
"""Verification script for Chart model."""
import sys
sys.path.insert(0, 'src')

try:
    from pybase.models.chart import Chart, ChartType, AggregationType
    print('OK')
    print(f'ChartType enum: {list(ChartType)}')
    print(f'AggregationType enum: {list(AggregationType)}')
    print(f'Chart table name: {Chart.__tablename__}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
