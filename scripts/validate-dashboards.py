#!/usr/bin/env python3
"""
Validate Grafana dashboard JSON files for subtask-6-2.

This script validates that:
1. All dashboard JSON files are syntactically valid
2. Each dashboard has the required structure
3. Dashboard queries reference the correct Prometheus metrics
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


# Expected metrics based on our implementation
EXPECTED_METRICS = [
    "http_requests_total",
    "http_request_duration_seconds",
    "extraction_task_duration_seconds",
    "extraction_task_total",
    "search_task_duration_seconds",
    "search_task_total",
    "websocket_connections",
    "db_query_duration_seconds",
    "cache_operations_total",
]


def validate_json_file(filepath: Path) -> Dict[str, Any]:
    """Validate a single dashboard JSON file."""
    print(f"\nValidating: {filepath.name}")
    print("-" * 60)

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"valid": False, "error": f"Failed to read file: {e}"}

    # Check if it's wrapped (has "dashboard" key) or direct format
    if "dashboard" in data:
        dashboard = data["dashboard"]
    elif "panels" in data and "title" in data:
        # Direct format - this is the dashboard itself
        dashboard = data
    else:
        return {"valid": False, "error": "Invalid dashboard format - missing required structure"}

    # Check required dashboard fields
    required_fields = ["title", "panels", "uid"]
    missing_fields = [f for f in required_fields if f not in dashboard]
    if missing_fields:
        return {"valid": False, "error": f"Missing required fields: {missing_fields}"}

    print(f"✓ Title: {dashboard['title']}")
    print(f"✓ UID: {dashboard.get('uid', 'N/A')}")
    print(f"✓ Panels: {len(dashboard.get('panels', []))}")

    # Validate panels
    panels = dashboard.get("panels", [])
    if not panels:
        return {"valid": False, "error": "No panels defined"}

    metrics_found = set()

    for i, panel in enumerate(panels):
        # Check if panel has targets
        targets = panel.get("targets", [])
        if not targets:
            print(f"  ⚠ Panel {i+1} ({panel.get('title', 'Untitled')}): No targets defined")
            continue

        for target in targets:
            # Extract metric name from queries
            expr = target.get("expr", "")
            for metric in EXPECTED_METRICS:
                if metric in expr:
                    metrics_found.add(metric)

    print(f"✓ Metrics referenced: {len(metrics_found)} unique metrics")
    if metrics_found:
        for metric in sorted(metrics_found):
            print(f"  - {metric}")

    # Check for templating (variables)
    templating = dashboard.get("templating", {})
    variables = templating.get("list", [])
    if variables:
        print(f"✓ Template variables: {len(variables)}")

    return {
        "valid": True,
        "title": dashboard["title"],
        "uid": dashboard.get("uid"),
        "panel_count": len(panels),
        "metrics_found": list(metrics_found),
    }


def main():
    """Main validation function."""
    print("=" * 60)
    print("Grafana Dashboard Validation")
    print("=" * 60)

    dashboards_dir = Path("monitoring/grafana-dashboards")
    if not dashboards_dir.exists():
        print(f"\n✗ Error: Directory '{dashboards_dir}' not found")
        sys.exit(1)

    dashboard_files = list(dashboards_dir.glob("*.json"))
    if not dashboard_files:
        print(f"\n✗ Error: No JSON files found in '{dashboards_dir}'")
        sys.exit(1)

    print(f"\nFound {len(dashboard_files)} dashboard file(s)\n")

    results = []
    all_metrics = set()

    for filepath in sorted(dashboard_files):
        result = validate_json_file(filepath)
        results.append((filepath.name, result))
        if result.get("valid"):
            all_metrics.update(result.get("metrics_found", []))

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    valid_count = sum(1 for _, r in results if r.get("valid"))
    total_count = len(results)

    print(f"\nValid dashboards: {valid_count}/{total_count}")

    if valid_count == total_count:
        print("✓ All dashboards are valid!")
    else:
        print("✗ Some dashboards have errors:")
        for name, result in results:
            if not result.get("valid"):
                print(f"  - {name}: {result.get('error', 'Unknown error')}")

    print(f"\nTotal unique metrics referenced: {len(all_metrics)}")
    for metric in sorted(all_metrics):
        print(f"  - {metric}")

    # Check for missing expected metrics
    missing_metrics = set(EXPECTED_METRICS) - all_metrics
    if missing_metrics:
        print(f"\n⚠ Warning: Some expected metrics are not used in any dashboard:")
        for metric in sorted(missing_metrics):
            print(f"  - {metric}")

    print("\n" + "=" * 60)

    # Exit with appropriate code
    sys.exit(0 if valid_count == total_count else 1)


if __name__ == "__main__":
    main()
