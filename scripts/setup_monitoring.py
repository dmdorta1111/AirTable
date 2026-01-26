"""
Setup script for monitoring dependencies.

Installs:
- streamlit (dashboard)
- Additional monitoring packages
"""

import subprocess
import sys
from pathlib import Path


def run_command(args: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Installing: {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(args)}\n")

    try:
        result = subprocess.run(
            args,
            check=True,
            capture_output=False,
        )
        print(f"✓ {description} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {description}: {e}")
        return False


def main() -> int:
    """Install monitoring dependencies."""
    print("=" * 60)
    print("Serialization Pipeline Monitoring Setup")
    print("=" * 60)

    packages = [
        # Dashboard
        (["pip", "install", "-U", "streamlit"], "Streamlit"),
        (["pip", "install", "-U", "plotly"], "Plotly"),

        # Additional monitoring (optional)
        (["pip", "install", "-U", "psutil"], "System utilities"),

        # Existing dependencies (ensure present)
        (["pip", "install", "-U", "sqlalchemy"], "SQLAlchemy"),
        (["pip", "install", "-U", "psycopg2-binary"], "PostgreSQL adapter"),
    ]

    success_count = 0

    for args, description in packages:
        if run_command(args, description):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Setup complete: {success_count}/{len(packages)} packages installed")
    print(f"{'='*60}\n")

    # Print usage instructions
    print("\n" + "=" * 60)
    print("USAGE")
    print("=" * 60)
    print("\n1. Run the dashboard:")
    print("   streamlit run scripts/serialization_dashboard.py")
    print("\n2. Set environment variables (optional):")
    print("   - DATABASE_URL: PostgreSQL connection string")
    print("   - SMTP_HOST: Email server for alerts")
    print("   - ALERT_TO_EMAILS: Comma-separated recipient emails")
    print("\n3. Dashboard will be available at: http://localhost:8501")
    print("\n" + "=" * 60)

    return 0 if success_count == len(packages) else 1


if __name__ == "__main__":
    sys.exit(main())
