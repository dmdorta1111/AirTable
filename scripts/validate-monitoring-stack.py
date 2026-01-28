#!/usr/bin/env python3
"""Validate monitoring stack configuration files."""

import json
import sys
from pathlib import Path

def validate_json_files():
    """Validate all Grafana dashboard JSON files."""
    dashboard_dir = Path("monitoring/grafana-dashboards")
    required_dashboards = [
        "api-performance.json",
        "celery-workers.json", 
        "database-redis.json",
        "overview.json"
    ]
    
    print("Validating Grafana dashboards...")
    for dashboard_file in required_dashboards:
        filepath = dashboard_dir / dashboard_file
        if not filepath.exists():
            print(f"✗ FAIL: {dashboard_file} not found")
            return False
        
        try:
            with open(filepath) as f:
                data = json.load(f)
                # Grafana dashboards should have "panels" key at root level
                if not data.get("panels"):
                    print(f"✗ FAIL: {dashboard_file} missing 'panels' key")
                    return False
            print(f"✓ PASS: {dashboard_file}")
        except json.JSONDecodeError as e:
            print(f"✗ FAIL: {dashboard_file} invalid JSON: {e}")
            return False
    
    return True

def validate_alert_rules():
    """Validate alert rule files exist."""
    alerts_dir = Path("monitoring/alerts")
    required_alerts = [
        "high-error-rate.yml",
        "slow-tasks.yml",
        "resource-exhaustion.yml"
    ]
    
    print("\nValidating alert rules...")
    for alert_file in required_alerts:
        filepath = alerts_dir / alert_file
        if not filepath.exists():
            print(f"✗ FAIL: {alert_file} not found")
            return False
        
        with open(filepath) as f:
            content = f.read()
            if "alert:" not in content:
                print(f"✗ FAIL: {alert_file} missing alert definitions")
                return False
        print(f"✓ PASS: {alert_file}")
    
    return True

def validate_provisioning():
    """Validate Grafana provisioning configs."""
    print("\nValidating Grafana provisioning...")
    
    # Check datasource
    datasource_file = Path("docker/grafana/provisioning/datasources/prometheus.yml")
    if not datasource_file.exists():
        print("✗ FAIL: Prometheus datasource config not found")
        return False
    print("✓ PASS: Prometheus datasource config")
    
    # Check dashboard provider
    provider_file = Path("docker/grafana/provisioning/dashboards/dashboard-provider.yml")
    if not provider_file.exists():
        print("✗ FAIL: Dashboard provider config not found")
        return False
    print("✓ PASS: Dashboard provider config")
    
    return True

def validate_prometheus_config():
    """Validate Prometheus configuration."""
    print("\nValidating Prometheus config...")
    
    prometheus_file = Path("monitoring/prometheus.yml")
    if not prometheus_file.exists():
        print("✗ FAIL: prometheus.yml not found")
        return False
    
    with open(prometheus_file) as f:
        content = f.read()
        if "scrape_configs:" not in content:
            print("✗ FAIL: prometheus.yml missing scrape_configs")
            return False
        if "rule_files:" not in content:
            print("⚠ WARN: prometheus.yml missing rule_files (alerts may not load)")
        else:
            print("✓ PASS: Alert rules configured in prometheus.yml")
    
    print("✓ PASS: Prometheus configuration")
    return True

def main():
    """Run all validations."""
    print("=" * 60)
    print("Monitoring Stack Configuration Validation")
    print("=" * 60)
    print()
    
    all_valid = True
    all_valid &= validate_json_files()
    all_valid &= validate_alert_rules()
    all_valid &= validate_provisioning()
    all_valid &= validate_prometheus_config()
    
    print()
    print("=" * 60)
    if all_valid:
        print("✓ ALL VALIDATIONS PASSED")
        print()
        print("Next steps:")
        print("  1. Start services: docker-compose up -d")
        print("  2. Start workers: docker-compose --profile worker up -d")
        print("  3. Run e2e test: ./scripts/e2e-verification.sh")
        return 0
    else:
        print("✗ SOME VALIDATIONS FAILED")
        print("Please fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
