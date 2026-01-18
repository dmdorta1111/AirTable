#!/usr/bin/env python3
"""
Check Phase 3 extraction dependencies installation status.
"""

import importlib
import subprocess
import sys

# Phase 3 extraction dependencies from pyproject.toml
EXTRACTION_DEPS = {
    "pdfplumber": "pdfplumber",
    "tabula-py": "tabula",
    "PyMuPDF": "fitz",  # PyMuPDF is imported as 'fitz'
    "pytesseract": "pytesseract",
    "ezdxf": "ezdxf",
    "ifcopenshell": "ifcopenshell",
    "opencv-python": "cv2",
    "Pillow": "PIL",
}


def check_dependency(package_name, import_name=None):
    """Check if a dependency is installed."""
    import_name = import_name or package_name
    try:
        importlib.import_module(import_name)
        return True, f"✅ {package_name} ({import_name})"
    except ImportError as e:
        return False, f"❌ {package_name} ({import_name}) - {e}"


def main():
    print("🔍 Checking Phase 3 CAD/PDF Extraction Dependencies")
    print("=" * 60)

    results = []
    missing = []

    for package, import_name in EXTRACTION_DEPS.items():
        ok, msg = check_dependency(package, import_name)
        results.append(msg)
        if not ok:
            missing.append(package)

    print("\n".join(results))

    if missing:
        print(f"\n⚠️  Missing {len(missing)} extraction dependencies:")
        for dep in missing:
            print(f"   - {dep}")

        print("\nInstall missing dependencies with:")
        print("pip install " + " ".join(sorted(missing)))

        # Offer to install
        response = input("\nInstall missing dependencies now? (y/N): ").strip().lower()
        if response == "y":
            print("Installing missing extraction dependencies...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + sorted(missing))
                print("✅ Installation complete")
            except subprocess.CalledProcessError as e:
                print(f"❌ Installation failed: {e}")
                return 1
    else:
        print("\n✅ All Phase 3 extraction dependencies are installed!")

        # Additional checks for specialized CAD processing
        print("\n🔧 Additional CAD processing checks:")

        # Check for optional ML/AI dependencies
        ml_deps = {
            "transformers": "transformers",
            "torch": "torch",
            "onnxruntime": "onnxruntime",
        }

        for dep, name in ml_deps.items():
            ok, msg = check_dependency(dep, name)
            print(f"  {msg}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
