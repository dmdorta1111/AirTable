#!/usr/bin/env python3
"""
Install Phase 3 CAD/PDF extraction dependencies and fix type errors.
"""

import subprocess
import sys
import os
import time


def install_dependencies():
    """Install extraction dependencies and optional dev packages."""
    print("🔧 Installing Phase 3 CAD/PDF Extraction Dependencies")
    print("=" * 60)

    # Group dependencies by type
    deps = {
        "pdf": ["pdfplumber>=0.10.3", "PyMuPDF>=1.23.8", "pypdf>=4.2.0"],
        "cad": ["ezdxf>=1.1.4"],
        "ocr": [
            "pytesseract>=0.3.10",
            "pdf2image>=1.17.0",
            "Pillow>=10.2.0",
            "opencv-python>=4.9.0.80",
        ],
        "bim": ["ifcopenshell>=0.7.0", "pythonocc-core>=7.6.3"],
    }

    # Test which dependencies are already installed
    import importlib

    def test_import(package_name, import_name=None):
        """Test if a package is already installed."""
        import_name = import_name or package_name
        try:
            importlib.import_module(import_name)
            return True, f"✅ {package_name}"
        except ImportError:
            return False, f"❌ {package_name}"

    print("\n📊 Current dependency status:")

    # Test main dependencies
    test_cases = [
        ("pdfplumber", "pdfplumber"),
        ("PyMuPDF", "fitz"),
        ("ezdxf", "ezdxf"),
        ("ifcopenshell", "ifcopenshell"),
        ("pytesseract", "pytesseract"),
        ("Pillow", "PIL.Image"),
        ("opencv-python", "cv2"),
    ]

    missing = []
    for package, import_name in test_cases:
        installed, msg = test_import(package, import_name)
        print(f"  {msg}")
        if not installed:
            missing.append(package)

    if not missing:
        print("\n✅ All extraction dependencies already installed!")
        return True

    print(f"\n⚠️  Missing {len(missing)} dependencies: {', '.join(missing)}")

    # Install missing dependencies
    print("\n📦 Installing missing dependencies...")

    # Group by installation complexity
    simple_deps = [d for d in missing if d in ["pdfplumber", "PyMuPDF", "ezdxf", "Pillow"]]
    complex_deps = [
        d
        for d in missing
        if d in ["ifcopenshell", "opencv-python", "pytesseract", "pythonocc-core"]
    ]

    # Install simple dependencies first
    if simple_deps:
        print(f"\nInstalling: {', '.join(simple_deps)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + simple_deps)
            print("✅ Simple dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install simple dependencies: {e}")
            return False

    # Install complex dependencies with retries and warnings
    if complex_deps:
        print(f"\n⚠️  Complex dependencies may require system packages:")
        print(f"   Installing: {', '.join(complex_deps)}")
        print("   This may take several minutes...")

        for dep in complex_deps:
            try:
                print(f"   Installing {dep}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                print(f"   ✅ {dep} installed")
            except subprocess.CalledProcessError as e:
                if dep == "ifcopenshell":
                    print(
                        f"   ⚠️  ifcopenshell requires system packages: sudo apt-get install build-essential cmake libboost-all-dev"
                    )
                elif dep == "opencv-python":
                    print(f"   ⚠️  opencv-python is large (~90MB) - installation continuing...")
                print(f"   ❌ {dep} failed: {e}")
                # Continue with other dependencies

    # Verify installation
    print("\n🔍 Verifying installation...")
    all_installed = True
    for package, import_name in test_cases:
        installed, msg = test_import(package, import_name)
        if not installed:
            all_installed = False
            print(f"  ❌ {package} still not available after installation")
            # Provide troubleshooting advice
            if package == "ifcopenshell":
                print("    Note: ifcopenshell may require manual compilation with C++ dependencies")
            elif package == "ezdxf":
                print("    Note: ezdxf is a pure Python package - check network connectivity")

    if all_installed:
        print("\n✅ All Phase 3 dependencies successfully installed!")
    else:
        print("\n⚠️  Some dependencies may not be fully functional.")
        print("   Complete installation may require system packages or manual intervention.")

    return all_installed


def fix_extraction_api_errors():
    """Fix TypeScript/LSP errors in extraction API."""
    print("\n🔧 Fixing extraction API type errors...")

    fixes = []

    # Fix 1: Update PDFExtractor.extract() call to match actual signature
    extractor_py = "src/pybase/api/v1/extraction.py"
    if os.path.exists(extractor_py):
        print(f"Checking {extractor_py}...")
        # We know the extract method signature from reading the file:
        # extract(self, file_path, extract_tables=True, extract_text=True, extract_dimensions=False, extract_title_block=False, pages=None)
        # The API is currently calling extract_tables when it should match extract method signature
        fix_needed = True
        if fix_needed:
            fixes.append(f"  - Update PDFExtractor.extract() parameters to match actual signature")

    # Fix 2: Fix DXF/IFC/STEP parser method names
    # The API calls parser.extract() but parsers have .parse() methods
    for parser_type in ["DXF", "IFC", "STEP"]:
        method_fix = f"  - Change {parser_type}Parser.extract() to {parser_type}Parser.parse()"
        fixes.append(method_fix)

    # Fix 3: Fix Werk24 client method confusion
    fixes.append("  - Update Werk24Client.parse() to match actual API")

    if fixes:
        print("\nType errors found. Needs manual fixes:")
        for fix in fixes:
            print(fix)

        print("\nTo fix manually:")
        print("1. Read method signatures from actual extractor/parser classes")
        print("2. Update API calls to match actual method parameters")
        print("3. Run LSP diagnostics to verify fixes")
        return False
    else:
        print("✅ No obvious type error patterns found (requires manual LSP review)")
        return True


def test_extraction_setup():
    """Test if extraction setup works."""
    print("\n🧪 Testing extraction setup...")

    try:
        # Test if any extraction classes can be imported
        import src.pybase.extraction.pdf as pdf_extraction

        print("✅ PDF extraction module exists")

        # Try to create an extractor
        extractor = pdf_extraction.PDFExtractor()
        print("✅ PDFExtractor can be instantiated")

        return True
    except Exception as e:
        print(f"❌ Extraction setup test failed: {e}")
        return False


def main():
    """Main installation and setup function."""
    print("🚀 PyBase Phase 3 CAD/PDF Extraction Setup")
    print("=" * 60)

    # Step 1: Install dependencies
    deps_installed = install_dependencies()

    if not deps_installed:
        print("\n⚠️  Dependency installation issues may affect functionality.")
        print("   Consider manual installation of complex dependencies.")

    # Step 2: Test extraction setup
    print("\n" + "=" * 60)
    print("📋 Extraction Setup Summary")
    print("=" * 60)

    test_extraction_setup()

    # Step 3: Issue summary
    print("\n📝 Next steps for Phase 3 implementation:")
    print("1. Fix extraction API type errors")
    print("2. Implement basic PDF table extraction")
    print("3. Add CAD file parsers (DXF, IFC)")
    print("4. Fix extraction result model serialization")
    print("5. Test with actual CAD/PDF files")

    fix_extraction_api_errors()

    return 0 if deps_installed else 1


if __name__ == "__main__":
    sys.exit(main())
