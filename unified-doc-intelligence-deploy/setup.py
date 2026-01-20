#!/usr/bin/env python3
"""
setup.py - Unified Engineering Document Intelligence Platform Setup

This script sets up the deployment environment by:
1. Installing all Python dependencies
2. Creating required directories
3. Helping configure the system
4. Verifying the installation

Usage: python setup.py
"""

import sys
import os
import subprocess
import platform
from pathlib import Path


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"📦 {title}")
    print("=" * 70)


def check_python_version():
    """Check Python version requirements."""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python version: {sys.version}")

    if version.major == 3 and version.minor >= 8:
        print("✓ Python 3.8+ detected - OK")
        return True
    else:
        print(f"✗ Python 3.8+ required, found {version.major}.{version.minor}")
        return False


def create_directories():
    """Create required directories."""
    print_header("Creating Directory Structure")

    dirs = ["output", "logs", "temp"]

    for dir_name in dirs:
        path = Path(dir_name)
        if not path.exists():
            path.mkdir(exist_ok=True, parents=True)
            print(f"✓ Created directory: {path}")
        else:
            print(f"✓ Directory exists: {path}")


def install_dependencies():
    """Install Python dependencies from requirements.txt."""
    print_header("Installing Dependencies")

    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("✗ requirements.txt not found!")
        return False

    print(f"Found requirements.txt with {len(req_file.read_text().splitlines())} packages")

    # Try to install with pip
    try:
        print("Installing packages with pip...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✓ All dependencies installed successfully!")
            return True
        else:
            print("✗ Installation failed:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"✗ Installation error: {e}")
        return False


def check_configuration():
    """Check and help configure the system."""
    print_header("Configuration Check")

    config_template = Path("config-template.txt")
    config_file = Path("config.txt")

    if not config_template.exists():
        print("✗ config-template.txt not found!")
        return False

    if not config_file.exists():
        print("✗ config.txt not found - you need to create it")
        print("\n📋 To configure the system:")
        print("1. Copy the template: cp config-template.txt config.txt")
        print("2. Edit config.txt with your credentials:")
        print("   - NEON_DATABASE_URL: Your Neon PostgreSQL connection string")
        print("   - B2_APPLICATION_KEY_ID: Your Backblaze B2 key ID")
        print("   - B2_APPLICATION_KEY: Your Backblaze B2 application key")
        print("   - B2_BUCKET_NAME: (default: EmjacDB)")
        return False

    # Read config to check if it's still using template values
    config_content = config_file.read_text()
    if "username:password" in config_content or "your_" in config_content:
        print("⚠ Warning: config.txt appears to have template values")
        print("Please update with your actual credentials")
        return False

    print("✓ config.txt found and appears to be configured")
    return True


def verify_packages():
    """Verify critical packages are installed."""
    print_header("Verifying Critical Packages")

    packages = [
        "psycopg2",
        "tqdm",
        "tabulate",
        "PyMuPDF",  # fitz
        "ezdxf",
        "b2sdk",
        "fastapi",
        "uvicorn",
        "pydantic",
    ]

    missing = []
    import_error = False

    for package in packages:
        try:
            # Special handling for PyMuPDF (imported as fitz)
            if package == "PyMuPDF":
                import fitz
            elif package == "b2sdk":
                from b2sdk.v2 import InMemoryAccountInfo, B2Api
            else:
                __import__(package)
            print(f"✓ {package}")
        except ImportError as e:
            print(f"✗ {package} - {e}")
            missing.append(package)
            import_error = True

    if import_error:
        print(f"\n⚠ Missing packages: {', '.join(missing)}")
        print("Try installing with: pip install " + " ".join(missing))
        return False

    print("✓ All critical packages installed")
    return True


def fix_script_paths():
    """Update script paths for the new directory structure."""
    print_header("Fixing Script Path References")

    script_dirs = [
        "scripts/phase-a-linking",
        "scripts/phase-b-extraction",
        "scripts/phase-c-search",
    ]
    changes_made = 0

    for script_dir in script_dirs:
        dir_path = Path(script_dir)
        if not dir_path.exists():
            print(f"✗ Script directory not found: {script_dir}")
            continue

        py_files = list(dir_path.glob("*.py"))
        print(f"Checking {len(py_files)} files in {script_dir}")

        for py_file in py_files:
            content = py_file.read_text()
            original_content = content

            # Fix relative path references
            # Change paths that assume parent.parent structure
            content = content.replace(
                "SCRIPT_DIR = Path(__file__).parent",
                "# Fixed by setup.py\nSCRIPT_DIR = Path(__file__).parent\nPROJECT_DIR = Path(__file__).parent.parent.parent",
            )

            # Fix CONFIG_FILE path
            content = content.replace(
                'CONFIG_FILE = PLAN_DIR / "config.txt"', 'CONFIG_FILE = PROJECT_DIR / "config.txt"'
            )

            # Fix SCHEMA_FILE path
            content = content.replace(
                'SCHEMA_FILE = PLAN_DIR / "output" / "schema-migration.sql"',
                'SCHEMA_FILE = PROJECT_DIR / "schema-migration.sql"',
            )

            # Fix OUTPUT_DIR path
            content = content.replace(
                'OUTPUT_DIR = PLAN_DIR / "output"', 'OUTPUT_DIR = PROJECT_DIR / "output"'
            )

            # If we made changes, write them back
            if content != original_content:
                py_file.write_text(content)
                changes_made += 1
                print(f"  ✓ Updated paths in: {py_file.name}")

    if changes_made > 0:
        print(f"\n✓ Updated {changes_made} script files with correct paths")
    else:
        print("✓ Script paths already correct")

    return True


def create_sample_config():
    """Create a sample config file if needed."""
    config_template = Path("config-template.txt")
    config_file = Path("config.txt")

    if not config_file.exists() and config_template.exists():
        print_header("Creating Sample Configuration")

        sample_config = config_template.read_text()
        # Add a note at the top
        sample_config = (
            "# Auto-generated by setup.py\n# Fill in your actual credentials below\n\n"
            + sample_config
        )

        config_file.write_text(sample_config)
        print(f"✓ Created config.txt from template")
        print("⚠ IMPORTANT: You MUST edit config.txt with your actual credentials")
        return True

    return False


def main():
    """Main setup function."""
    print_header("Unified Engineering Document Intelligence Platform Setup")
    print("This script will prepare the deployment environment.")

    # Check we're in the right directory
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")

    # Check for required files
    required_files = ["README.md", "config-template.txt", "requirements.txt"]
    missing_files = []

    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)

    if missing_files:
        print(f"✗ Missing required files: {', '.join(missing_files)}")
        print("Please run this script from the deployment directory")
        return False

    # Run setup steps
    steps = [
        ("Check Python version", check_python_version),
        ("Create directories", create_directories),
        ("Create sample config", create_sample_config),
        ("Install dependencies", install_dependencies),
        ("Verify packages", verify_packages),
        ("Fix script paths", fix_script_paths),
        ("Check configuration", check_configuration),
    ]

    results = []
    for step_name, step_func in steps:
        try:
            print(f"\n▶ Step: {step_name}")
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"✗ Error in {step_name}: {e}")
            results.append((step_name, False))

    # Print summary
    print_header("Setup Summary")

    success_count = sum(1 for _, success in results if success)
    total_steps = len(results)

    print(f"Completed {success_count}/{total_steps} steps successfully")

    for step_name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {step_name}")

    if success_count >= total_steps - 1:  # Allow one failure (like config check)
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit config.txt with your actual credentials")
        print("2. Run the pipeline: python run-pipeline.py --phase a")
        print("3. Or test a single script: python scripts/phase-a-linking/A1-migrate-schema.py")
        return True
    else:
        print("\n⚠ Setup encountered issues")
        print("Please check the errors above and try again")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        sys.exit(1)
