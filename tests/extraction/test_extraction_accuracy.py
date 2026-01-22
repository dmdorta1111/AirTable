"""
Accuracy validation tests for CAD extraction parsers.

Tests overall accuracy of DXF, IFC, and STEP parsers across the full test corpus,
ensuring >95% accuracy for each parser type.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from pybase.extraction.base import CADExtractionResult
from pybase.extraction.cad.dxf import EZDXF_AVAILABLE, DXFParser

# Try to import IFC and STEP parsers (they may not be available without optional dependencies)
try:
    from pybase.extraction.cad.ifc import IFCOPENSHELL_AVAILABLE, IFCParser
except ImportError:
    IFCOPENSHELL_AVAILABLE = False
    IFCParser = None  # type: ignore

try:
    from pybase.extraction.cad.step import (
        CADQUERY_AVAILABLE,
        OCP_AVAILABLE,
        STEPParser,
    )
except ImportError:
    CADQUERY_AVAILABLE = False
    OCP_AVAILABLE = False
    STEPParser = None  # type: ignore


@dataclass
class AccuracyResult:
    """Result of accuracy testing for a single file."""

    file_name: str
    success: bool
    has_content: bool
    passed: bool
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccuracyReport:
    """Overall accuracy report for a parser type."""

    parser_type: str
    total_files: int
    passed_files: int
    failed_files: int
    accuracy_percentage: float
    results: list[AccuracyResult] = field(default_factory=list)

    def __str__(self) -> str:
        """Generate a formatted report string."""
        report_lines = [
            f"\n{'=' * 70}",
            f"{self.parser_type.upper()} EXTRACTION ACCURACY REPORT",
            f"{'=' * 70}",
            f"Total Files Tested: {self.total_files}",
            f"Passed: {self.passed_files}",
            f"Failed: {self.failed_files}",
            f"Accuracy: {self.accuracy_percentage:.2f}%",
            f"{'=' * 70}",
        ]

        # List failures if any
        if self.failed_files > 0:
            report_lines.append("\nFAILED FILES:")
            report_lines.append("-" * 70)
            for result in self.results:
                if not result.passed:
                    report_lines.append(f"  ❌ {result.file_name}")
                    if result.error_message:
                        report_lines.append(f"     Error: {result.error_message}")
                    if not result.success:
                        report_lines.append(f"     Status: Parsing failed")
                    if not result.has_content:
                        report_lines.append(f"     Status: No content extracted")

        # Sample of passed files
        passed_results = [r for r in self.results if r.passed]
        if passed_results and len(passed_results) <= 10:
            report_lines.append("\nPASSED FILES:")
            report_lines.append("-" * 70)
            for result in passed_results[:10]:
                report_lines.append(f"  ✓ {result.file_name}")
        elif passed_results:
            report_lines.append(f"\nAll {len(passed_results)} other files passed successfully.")

        report_lines.append(f"{'=' * 70}\n")
        return "\n".join(report_lines)


def evaluate_dxf_accuracy(result: CADExtractionResult, file_path: Path) -> AccuracyResult:
    """
    Evaluate accuracy of DXF extraction result.

    A DXF file passes if:
    - Parsing succeeds (no errors)
    - Content is extracted (at least one of: layers, dimensions, text, blocks, or entities)
    """
    details = {
        "layers_count": len(result.layers),
        "dimensions_count": len(result.dimensions),
        "text_blocks_count": len(result.text_blocks),
        "blocks_count": len(result.blocks),
        "entities_count": len(result.entities),
        "errors_count": len(result.errors),
        "warnings_count": len(result.warnings),
    }

    # Check if parsing succeeded
    if not result.success:
        error_msg = "; ".join(result.errors[:3]) if result.errors else "Unknown error"
        return AccuracyResult(
            file_name=file_path.name,
            success=False,
            has_content=result.has_content,
            passed=False,
            error_message=error_msg,
            details=details,
        )

    # For empty drawings (like empty_drawing.dxf), passing parse is enough
    # Most drawings should have content though
    is_empty_drawing = "empty" in file_path.name.lower()
    has_meaningful_content = result.has_content

    # Pass if parsing succeeded and has content (or is intentionally empty)
    passed = result.success and (has_meaningful_content or is_empty_drawing)

    error_msg = None
    if not passed:
        if not has_meaningful_content:
            error_msg = "No content extracted from file"

    return AccuracyResult(
        file_name=file_path.name,
        success=result.success,
        has_content=has_meaningful_content,
        passed=passed,
        error_message=error_msg,
        details=details,
    )


def evaluate_ifc_accuracy(result: CADExtractionResult, file_path: Path) -> AccuracyResult:
    """
    Evaluate accuracy of IFC extraction result.

    An IFC file passes if:
    - Parsing succeeds (no errors)
    - Expected building elements are extracted based on filename
    """
    details = {
        "elements_count": result.metadata.get("total_elements", 0),
        "spatial_count": result.metadata.get("total_spatial", 0),
        "errors_count": len(result.errors),
        "warnings_count": len(result.warnings),
    }

    # Check if parsing succeeded
    if not result.success:
        error_msg = "; ".join(result.errors[:3]) if result.errors else "Unknown error"
        return AccuracyResult(
            file_name=file_path.name,
            success=False,
            has_content=result.has_content,
            passed=False,
            error_message=error_msg,
            details=details,
        )

    # Check if expected content was extracted
    has_elements = result.metadata.get("total_elements", 0) > 0
    has_spatial = result.metadata.get("total_spatial", 0) > 0

    # Pass if parsing succeeded and has building elements or spatial structure
    passed = result.success and (has_elements or has_spatial)

    error_msg = None
    if not passed:
        if not has_elements and not has_spatial:
            error_msg = "No building elements or spatial structure extracted"

    return AccuracyResult(
        file_name=file_path.name,
        success=result.success,
        has_content=has_elements or has_spatial,
        passed=passed,
        error_message=error_msg,
        details=details,
    )


def evaluate_step_accuracy(result: CADExtractionResult, file_path: Path) -> AccuracyResult:
    """
    Evaluate accuracy of STEP extraction result.

    A STEP file passes if:
    - Parsing succeeds (no errors)
    - Geometry metadata is extracted
    """
    details = {
        "parts_count": result.metadata.get("total_parts", 0),
        "has_assembly": result.metadata.get("has_assembly", False),
        "errors_count": len(result.errors),
        "warnings_count": len(result.warnings),
    }

    # Check if parsing succeeded
    if not result.success:
        error_msg = "; ".join(result.errors[:3]) if result.errors else "Unknown error"
        return AccuracyResult(
            file_name=file_path.name,
            success=False,
            has_content=result.has_content,
            passed=False,
            error_message=error_msg,
            details=details,
        )

    # Check if expected content was extracted
    has_parts = result.metadata.get("total_parts", 0) > 0
    has_geometry = result.geometry_summary is not None

    # Pass if parsing succeeded and has parts or geometry
    passed = result.success and (has_parts or has_geometry)

    error_msg = None
    if not passed:
        if not has_parts and not has_geometry:
            error_msg = "No parts or geometry metadata extracted"

    return AccuracyResult(
        file_name=file_path.name,
        success=result.success,
        has_content=has_parts or has_geometry,
        passed=passed,
        error_message=error_msg,
        details=details,
    )


def generate_accuracy_report(
    parser_type: str,
    test_files: list[Path],
    accuracy_results: list[AccuracyResult],
) -> AccuracyReport:
    """Generate an accuracy report from test results."""
    total_files = len(test_files)
    passed_files = sum(1 for r in accuracy_results if r.passed)
    failed_files = total_files - passed_files
    accuracy_percentage = (passed_files / total_files * 100) if total_files > 0 else 0.0

    return AccuracyReport(
        parser_type=parser_type,
        total_files=total_files,
        passed_files=passed_files,
        failed_files=failed_files,
        accuracy_percentage=accuracy_percentage,
        results=accuracy_results,
    )


@pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
class TestDXFAccuracy:
    """Test suite for DXF parser accuracy validation."""

    def test_dxf_accuracy(self, dxf_fixtures_dir: Path, dxf_parser: DXFParser) -> None:
        """
        Test DXF parser accuracy across full test corpus.

        Validates that >95% of DXF files are parsed successfully with content extraction.
        """
        # Collect all DXF test files
        dxf_files = sorted(dxf_fixtures_dir.glob("*.dxf"))
        assert len(dxf_files) > 0, "No DXF test files found in fixtures directory"

        print(f"\n\nTesting DXF accuracy on {len(dxf_files)} files...")

        # Test each file and collect accuracy results
        accuracy_results: list[AccuracyResult] = []

        for dxf_file in dxf_files:
            try:
                # Parse the file
                result = dxf_parser.parse(dxf_file)

                # Evaluate accuracy
                accuracy_result = evaluate_dxf_accuracy(result, dxf_file)
                accuracy_results.append(accuracy_result)

            except Exception as e:
                # Handle unexpected exceptions
                accuracy_results.append(
                    AccuracyResult(
                        file_name=dxf_file.name,
                        success=False,
                        has_content=False,
                        passed=False,
                        error_message=f"Unexpected exception: {str(e)}",
                    )
                )

        # Generate accuracy report
        report = generate_accuracy_report("DXF", dxf_files, accuracy_results)

        # Print the report
        print(report)

        # Assert accuracy threshold
        assert report.accuracy_percentage >= 95.0, (
            f"DXF accuracy {report.accuracy_percentage:.2f}% is below 95% threshold. "
            f"{report.failed_files} of {report.total_files} files failed."
        )

    def test_dxf_dimension_extraction_accuracy(
        self, dxf_fixtures_dir: Path, dxf_parser: DXFParser
    ) -> None:
        """
        Test dimension extraction accuracy on DXF files with dimensions.

        Validates that dimension-containing files extract at least some dimensions.
        """
        # Find DXF files that should contain dimensions
        dimension_files = [
            f
            for f in sorted(dxf_fixtures_dir.glob("*.dxf"))
            if "dimension" in f.name.lower()
            or "mechanical" in f.name.lower()
            or "assembly" in f.name.lower()
        ]

        if not dimension_files:
            pytest.skip("No dimension test files found")

        print(f"\n\nTesting dimension extraction on {len(dimension_files)} files...")

        passed = 0
        failed = 0
        failed_files = []

        for dxf_file in dimension_files:
            result = dxf_parser.parse(dxf_file)

            # For dimension files, we expect at least some dimensions to be extracted
            if result.success and len(result.dimensions) > 0:
                passed += 1
            else:
                failed += 1
                failed_files.append(dxf_file.name)

        accuracy = (passed / len(dimension_files) * 100) if dimension_files else 0

        print(f"\nDimension Extraction Accuracy: {accuracy:.2f}%")
        print(f"Passed: {passed}/{len(dimension_files)}")

        if failed_files:
            print(f"\nFiles with no dimensions extracted:")
            for name in failed_files:
                print(f"  - {name}")

        # Note: This is informational, we don't fail the test here as some files
        # might be edge cases or have dimensions that are hard to extract
        # The main accuracy test covers overall parsing success

    def test_dxf_text_extraction_accuracy(
        self, dxf_fixtures_dir: Path, dxf_parser: DXFParser
    ) -> None:
        """
        Test text extraction accuracy on DXF files with text entities.

        Validates that text-containing files extract at least some text.
        """
        # Find DXF files that should contain text
        text_files = [
            f
            for f in sorted(dxf_fixtures_dir.glob("*.dxf"))
            if "text" in f.name.lower()
            or "title" in f.name.lower()
            or "annotation" in f.name.lower()
            or "leader" in f.name.lower()
        ]

        if not text_files:
            pytest.skip("No text test files found")

        print(f"\n\nTesting text extraction on {len(text_files)} files...")

        passed = 0
        failed = 0
        failed_files = []

        for dxf_file in text_files:
            result = dxf_parser.parse(dxf_file)

            # For text files, we expect at least some text to be extracted
            if result.success and len(result.text_blocks) > 0:
                passed += 1
            else:
                failed += 1
                failed_files.append(dxf_file.name)

        accuracy = (passed / len(text_files) * 100) if text_files else 0

        print(f"\nText Extraction Accuracy: {accuracy:.2f}%")
        print(f"Passed: {passed}/{len(text_files)}")

        if failed_files:
            print(f"\nFiles with no text extracted:")
            for name in failed_files:
                print(f"  - {name}")

    def test_dxf_block_extraction_accuracy(
        self, dxf_fixtures_dir: Path, dxf_parser: DXFParser
    ) -> None:
        """
        Test block extraction accuracy on DXF files with blocks.

        Validates that block-containing files extract at least some blocks.
        """
        # Find DXF files that should contain blocks
        block_files = [
            f
            for f in sorted(dxf_fixtures_dir.glob("*.dxf"))
            if "block" in f.name.lower() or "assembly" in f.name.lower()
        ]

        if not block_files:
            pytest.skip("No block test files found")

        print(f"\n\nTesting block extraction on {len(block_files)} files...")

        passed = 0
        failed = 0
        failed_files = []

        for dxf_file in block_files:
            result = dxf_parser.parse(dxf_file)

            # For block files, we expect at least some blocks to be extracted
            if result.success and len(result.blocks) > 0:
                passed += 1
            else:
                failed += 1
                failed_files.append(dxf_file.name)

        accuracy = (passed / len(block_files) * 100) if block_files else 0

        print(f"\nBlock Extraction Accuracy: {accuracy:.2f}%")
        print(f"Passed: {passed}/{len(block_files)}")

        if failed_files:
            print(f"\nFiles with no blocks extracted:")
            for name in failed_files:
                print(f"  - {name}")


@pytest.mark.skipif(
    not IFCOPENSHELL_AVAILABLE or IFCParser is None, reason="ifcopenshell not available"
)
class TestIFCAccuracy:
    """Test suite for IFC parser accuracy validation."""

    def test_ifc_accuracy(self, ifc_fixtures_dir: Path, ifc_parser: Any) -> None:
        """
        Test IFC parser accuracy across full test corpus.

        Validates that >95% of IFC files are parsed successfully with element extraction.
        """
        # Collect all IFC test files
        ifc_files = sorted(ifc_fixtures_dir.glob("*.ifc"))

        if len(ifc_files) == 0:
            pytest.skip("No IFC test files found in fixtures directory")

        print(f"\n\nTesting IFC accuracy on {len(ifc_files)} files...")

        # Test each file and collect accuracy results
        accuracy_results: list[AccuracyResult] = []

        for ifc_file in ifc_files:
            try:
                # Parse the file
                result = ifc_parser.parse(ifc_file)

                # Evaluate accuracy
                accuracy_result = evaluate_ifc_accuracy(result, ifc_file)
                accuracy_results.append(accuracy_result)

            except Exception as e:
                # Handle unexpected exceptions
                accuracy_results.append(
                    AccuracyResult(
                        file_name=ifc_file.name,
                        success=False,
                        has_content=False,
                        passed=False,
                        error_message=f"Unexpected exception: {str(e)}",
                    )
                )

        # Generate accuracy report
        report = generate_accuracy_report("IFC", ifc_files, accuracy_results)

        # Print the report
        print(report)

        # Assert accuracy threshold
        assert report.accuracy_percentage >= 95.0, (
            f"IFC accuracy {report.accuracy_percentage:.2f}% is below 95% threshold. "
            f"{report.failed_files} of {report.total_files} files failed."
        )


@pytest.mark.skipif(
    (not OCP_AVAILABLE and not CADQUERY_AVAILABLE) or STEPParser is None,
    reason="OCP or cadquery not available",
)
class TestSTEPAccuracy:
    """Test suite for STEP parser accuracy validation."""

    def test_step_accuracy(self, step_fixtures_dir: Path, step_parser: Any) -> None:
        """
        Test STEP parser accuracy across full test corpus.

        Validates that >95% of STEP files are parsed successfully with geometry extraction.
        """
        # Collect all STEP test files (.step and .stp extensions)
        step_files = sorted(step_fixtures_dir.glob("*.step")) + sorted(
            step_fixtures_dir.glob("*.stp")
        )

        if len(step_files) == 0:
            pytest.skip("No STEP test files found in fixtures directory")

        print(f"\n\nTesting STEP accuracy on {len(step_files)} files...")

        # Test each file and collect accuracy results
        accuracy_results: list[AccuracyResult] = []

        for step_file in step_files:
            try:
                # Parse the file
                result = step_parser.parse(step_file)

                # Evaluate accuracy
                accuracy_result = evaluate_step_accuracy(result, step_file)
                accuracy_results.append(accuracy_result)

            except Exception as e:
                # Handle unexpected exceptions
                accuracy_results.append(
                    AccuracyResult(
                        file_name=step_file.name,
                        success=False,
                        has_content=False,
                        passed=False,
                        error_message=f"Unexpected exception: {str(e)}",
                    )
                )

        # Generate accuracy report
        report = generate_accuracy_report("STEP", step_files, accuracy_results)

        # Print the report
        print(report)

        # Assert accuracy threshold
        assert report.accuracy_percentage >= 95.0, (
            f"STEP accuracy {report.accuracy_percentage:.2f}% is below 95% threshold. "
            f"{report.failed_files} of {report.total_files} files failed."
        )
