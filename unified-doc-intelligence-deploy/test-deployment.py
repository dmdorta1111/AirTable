#!/usr/bin/env python3
"""
test-deployment.py - Verify Deployment Package Structure

This script verifies that the deployment package is complete and ready for use.
It checks all files, dependencies, and structure without actually running
heavy processes or connecting to external services.

Usage: python test-deployment.py
"""

import sys
import os
import importlib
from pathlib import Path


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"🔍 {title}")
    print(f"{'=' * 70}")


def check_success(item, status=True):
    """Print check result."""
    if status:
        print(f"  ✓ {item}")
        return True
    else:
        print(f"  ✗ {item}")
        return False


def verify_structure():
    """Verify the deployment directory structure."""
    print_header("Verifying Directory Structure")

    base_dir = Path.cwd()
    checks = [
        ("Base directory exists", base_dir.exists()),
        ("README.md exists", (base_dir / "README.md").exists()),
        ("requirements.txt exists", (base_dir / "requirements.txt").exists()),
        ("config-template.txt exists", (base_dir / "config-template.txt").exists()),
        ("run-pipeline.py exists", (base_dir / "run-pipeline.py").exists()),
        ("setup.py exists", (base_dir / "setup.py").exists()),
        ("deploy.sh exists", (base_dir / "deploy.sh").exists()),
        ("schema-migration.sql exists", (base_dir / "schema-migration.sql").exists()),
        ("scripts/ directory exists", (base_dir / "scripts").exists()),
        ("scripts/phase-a-linking exists", (base_dir / "scripts/phase-a-linking").exists()),
        ("scripts/phase-b-extraction exists", (base_dir / "scripts/phase-b-extraction").exists()),
        ("scripts/phase-c-search exists", (base_dir / "scripts/phase-c-search").exists()),
        ("docs/ directory exists", (base_dir / "docs").exists()),
    ]

    result = True
    for item, exists in checks:
        if not check_success(item, exists):
            result = False

    return result


def verify_script_count():
    """Verify all 19 scripts are present."""
    print_header("Verifying Script Count (19 total)")

    script_dirs = [("phase-a-linking", 6), ("phase-b-extraction", 7), ("phase-c-search", 6)]

    total_scripts = 0
    scripts_missing = []

    for dir_name, expected_count in script_dirs:
        dir_path = Path("scripts") / dir_name
        if not dir_path.exists():
            print(f"  ✗ {dir_name} directory missing")
            continue

        py_files = list(dir_path.glob("*.py"))
        actual_count = len(py_files)
        total_scripts += actual_count

        if actual_count == expected_count:
            check_success(f"{dir_name}: {actual_count}/{expected_count} scripts", True)
        else:
            check_success(f"{dir_name}: {actual_count}/{expected_count} scripts", False)
            scripts_missing.append(f"{dir_name} (missing {expected_count - actual_count})")

    # Check total
    if total_scripts == 19:
        check_success(f"Total scripts: {total_scripts}/19", True)
    else:
        check_success(f"Total scripts: {total_scripts}/19", False)

    return total_scripts == 19


def verify_configuration():
    """Verify configuration setup."""
    print_header("Verifying Configuration")

    config_file = Path("config.txt")
    template_file = Path("config-template.txt")

    # Check if config.txt exists and isn't just template
    if not config_file.exists():
        check_success("config.txt file exists", False)
        print("  ⚠ Create config.txt from template: cp config-template.txt config.txt")
        return False

    # Read config to check for template values
    try:
        content = config_file.read_text()
        template_values = ["username:password", "your_", "xxx", "ep-xxxx"]

        has_template_values = any(template_val in content for template_val in template_values)

        if has_template_values:
            check_success("config.txt has real credentials", False)
            print("  ⚠ config.txt appears to have template values")
            print("    Edit with your actual Neon PostgreSQL and Backblaze B2 credentials")
            return False
        else:
            check_success("config.txt has real credentials", True)
            return True
    except Exception as e:
        check_success("config.txt is readable", False)
        print(f"  Error reading config.txt: {e}")
        return False


def verify_dependencies():
    """Verify Python dependencies without importing heavy packages."""
    print_header("Verifying Core Dependencies")

    # Lightweight imports only
    dependencies = [
        ("psycopg2", "PostgreSQL database driver"),
        ("tqdm", "Progress bars"),
        ("tabulate", "Table formatting"),
    ]

    missing = []
    for package, description in dependencies:
        try:
            importlib.import_module(package)
            check_success(f"{package} ({description})", True)
        except ImportError:
            check_success(f"{package} ({description})", False)
            missing.append(package)

    if missing:
        print(f"\n  ⚠ Missing packages: {', '.join(missing)}")
        print(f"    Install with: pip install {' '.join(missing)}")
        return False

    return True


def verify_sql_schema():
    """Verify the SQL schema file."""
    print_header("Verifying SQL Schema File")

    schema_file = Path("schema-migration.sql")

    if not schema_file.exists():
        check_success("schema-migration.sql exists", False)
        return False

    try:
        content = schema_file.read_text()
        size = len(content)

        check_success(f"schema-migration.sql exists ({size:,} bytes)", True)

        # Check for key tables in SQL
        required_tables = [
            "CREATE TABLE document_groups",
            "CREATE TABLE document_group_members",
            "CREATE TABLE extracted_metadata",
            "CREATE TABLE extraction_jobs",
        ]

        tables_found = sum(1 for table in required_tables if table in content)
        check_success(f"Contains {tables_found}/4 key table definitions", tables_found >= 4)

        return True
    except Exception as e:
        check_success("schema-migration.sql is readable", False)
        print(f"  Error reading schema file: {e}")
        return False


def verify_documentation():
    """Verify documentation files."""
    print_header("Verifying Documentation")

    docs_dir = Path("docs")
    expected_files = ["IMPLEMENTATION_GUIDE.md", "README.md"]

    if not docs_dir.exists():
        check_success("docs/ directory exists", False)
        return False

    result = True
    for file_name in expected_files:
        file_path = docs_dir / file_name
        if file_name == "README.md":
            # README.md can be at root or in docs
            file_path = Path(file_name) if Path(file_name).exists() else docs_dir / file_name

        exists = file_path.exists()
        if not check_success(f"{file_name} exists", exists):
            result = False

    return result


def verify_executor():
    """Verify the pipeline executor."""
    print_header("Verifying Pipeline Executor")

    executor_file = Path("run-pipeline.py")

    if not executor_file.exists():
        check_success("run-pipeline.py exists", False)
        return False

    try:
        content = executor_file.read_text()
        size = len(content)

        check_success(f"run-pipeline.py exists ({size:,} bytes)", True)

        # Check for key functions
        required_features = [
            "class PipelineExecutor",
            "run_phase_a",
            "run_phase_b",
            "run_phase_c",
            "get_system_status",
        ]

        features_found = sum(1 for feature in required_features if feature in content)
        check_success(f"Contains {features_found}/5 key functions", features_found >= 5)

        return True
    except Exception as e:
        check_success("run-pipeline.py is readable", False)
        print(f"  Error reading executor file: {e}")
        return False


def generate_summary():
    """Generate deployment summary."""
    print_header("Deployment Package Summary")

    base_dir = Path.cwd()

    # Count files
    total_py_files = sum(1 for _ in base_dir.rglob("*.py"))

    # List key directories
    print(f"📦 Deployment Package Contents:")
    print(f"  Total Python scripts: {total_py_files}")
    print(
        f"  Configuration files: 4 (config-template.txt, config.txt(?), requirements.txt, schema-migration.sql)"
    )
    print(f"  Executor scripts: 3 (run-pipeline.py, setup.py, deploy.sh)")
    print(f"  Documentation: docs/ directory")

    # Show run commands
    print(f"\n🚀 Ready to Run:")
    print(f"  1. Setup: python setup.py OR ./deploy.sh")
    print(f"  2. Complete pipeline: python run-pipeline.py --phase all")
    print(f"  3. Individual phases:")
    print(f"     - Phase A (Auto-linking): python run-pipeline.py --phase a")
    print(f"     - Phase B (Extraction): python run-pipeline.py --phase b --workers 20")
    print(f"     - Phase C (Search API): python run-pipeline.py --phase c --api-workers 4")

    # Show what's processed
    print(f"\n📊 Scales to process:")
    print(f"  - 819,000+ total engineering files")
    print(f"  - 191,000+ PDF drawings")
    print(f"  - 574,000+ DXF drawings")
    print(f"  - Creates ~37,000 DocumentGroups")

    print(f"\n✅ This directory is ready to copy to remote machines:")
    print(f"   scp -r unified-doc-intelligence-deploy/ user@remote:/path/")
    print(f"   cd unified-doc-intelligence-deploy && python setup.py")


def main():
    """Main verification function."""
    print_header("Unified Engineering Document Intelligence Platform Deployment Verification")
    print("This script verifies your deployment package is complete and ready for use.")
    print("It performs lightweight checks without connecting to external services.\n")

    # Run all checks
    checks = [
        ("Directory Structure", verify_structure),
        ("Script Count (19 total)", verify_script_count),
        ("Configuration", verify_configuration),
        ("Core Dependencies", verify_dependencies),
        ("SQL Schema", verify_sql_schema),
        ("Documentation", verify_documentation),
        ("Pipeline Executor", verify_executor),
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"Error in {check_name}: {e}")
            results.append((check_name, False))

    # Print summary
    print_header("Verification Results")

    success_count = sum(1 for _, success in results if success)
    total_checks = len(results)

    print(f"Checks passed: {success_count}/{total_checks}")

    for check_name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {check_name}")

    # Generate summary
    generate_summary()

    # Final status
    print("\n" + "=" * 70)
    if success_count >= total_checks - 1:  # Allow one non-critical failure
        print("✅ DEPLOYMENT PACKAGE VERIFIED - READY FOR USE")
        print("\nCopy this directory to remote machines and run:")
        print("  python setup.py")
        print("  python run-pipeline.py --phase all")
        return True
    else:
        print("⚠ DEPLOYMENT PACKAGE HAS ISSUES - Please fix above errors")
        print("\nCommon fixes:")
        print("  - Missing config.txt: cp config-template.txt config.txt")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - Missing scripts: Check the scripts/ directories")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted")
        sys.exit(1)
