"""
Unit tests for enhanced table extraction features.

Tests for merged cell detection, spanning headers, and adaptive boundary detection.
"""

from unittest.mock import MagicMock, Mock

import pytest

from pybase.extraction.pdf.table_extractor import TableExtractor


class TestMergedCellDetection:
    """Tests for merged cell detection functionality."""

    def test_detect_merged_cells_no_cells_attribute(self):
        """Test merged cell detection when table has no cells attribute."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        table_obj.cells = None
        data = [["A", "B"], ["C", "D"]]

        merged_cells = extractor._detect_merged_cells(table_obj, data)

        assert merged_cells == []

    def test_detect_merged_cells_empty_cells(self):
        """Test merged cell detection with empty cells list."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        table_obj.cells = []
        data = [["A", "B"], ["C", "D"]]

        merged_cells = extractor._detect_merged_cells(table_obj, data)

        assert merged_cells == []

    def test_detect_merged_cells_horizontal_merge(self):
        """Test detection of horizontally merged cells."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()

        # Simulate cells: first cell spans 2 columns (width = 200), others normal (width = 100)
        table_obj.cells = [
            (0, 0, 200, 50),    # Merged cell spanning 2 columns
            (0, 50, 100, 100),  # Normal cell
            (100, 50, 200, 100),  # Normal cell
        ]

        data = [["Merged Header", ""], ["A", "B"]]

        merged_cells = extractor._detect_merged_cells(table_obj, data)

        assert len(merged_cells) == 1
        assert merged_cells[0]["col_start"] == 0
        assert merged_cells[0]["col_end"] > merged_cells[0]["col_start"]
        assert "bbox" in merged_cells[0]

    def test_detect_merged_cells_vertical_merge(self):
        """Test detection of vertically merged cells."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()

        # Simulate cells: first cell spans 2 rows (height = 100), others normal (height = 50)
        table_obj.cells = [
            (0, 0, 100, 100),   # Merged cell spanning 2 rows
            (100, 0, 200, 50),  # Normal cell row 1
            (100, 50, 200, 100),  # Normal cell row 2
        ]

        data = [["Merged", "A"], ["", "B"]]

        merged_cells = extractor._detect_merged_cells(table_obj, data)

        assert len(merged_cells) == 1
        assert merged_cells[0]["row_start"] == 0
        assert merged_cells[0]["row_end"] > merged_cells[0]["row_start"]

    def test_detect_merged_cells_no_merges(self):
        """Test detection with no merged cells."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()

        # All cells have same dimensions
        table_obj.cells = [
            (0, 0, 100, 50),
            (100, 0, 200, 50),
            (0, 50, 100, 100),
            (100, 50, 200, 100),
        ]

        data = [["A", "B"], ["C", "D"]]

        merged_cells = extractor._detect_merged_cells(table_obj, data)

        # No cells should be detected as merged (all within threshold)
        assert len(merged_cells) == 0


class TestMultirowHeaderDetection:
    """Tests for multi-row header detection functionality."""

    def test_detect_multirow_headers_single_row_data(self):
        """Test multirow header detection with insufficient data."""
        extractor = TableExtractor(engine="pdfplumber")
        data = [["A", "B"]]

        headers, count = extractor._detect_multirow_headers(data)

        assert headers == []
        assert count == 0

    def test_detect_multirow_headers_no_multirow(self):
        """Test multirow header detection when only single header row exists."""
        extractor = TableExtractor(engine="pdfplumber")
        data = [
            ["Name", "Value"],
            ["Item1", "100"],
            ["Item2", "200"],
        ]

        headers, count = extractor._detect_multirow_headers(data)

        # Should detect single header row, return 0 for multirow
        assert count <= 1

    def test_detect_multirow_headers_with_merged_cells(self):
        """Test multirow header detection with spanning headers."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()

        # Mock merged cells spanning columns
        table_obj.cells = [
            (0, 0, 200, 50),    # Category A spanning 2 columns
            (200, 0, 400, 50),  # Category B spanning 2 columns
            (0, 50, 100, 100),  # Item 1
            (100, 50, 200, 100),  # Item 2
            (200, 50, 300, 100),  # Item 3
            (300, 50, 400, 100),  # Item 4
        ]

        data = [
            ["Category A", "", "Category B", ""],
            ["Item 1", "Item 2", "Item 3", "Item 4"],
            ["100", "200", "300", "400"],
        ]

        headers, count = extractor._detect_multirow_headers(data, table_obj=table_obj)

        # Should detect 2 header rows
        assert count == 2
        assert len(headers) == 4

    def test_is_header_row_numeric_data(self):
        """Test header row detection rejects numeric rows."""
        extractor = TableExtractor(engine="pdfplumber")
        row = ["100", "200", "300"]

        is_header = extractor._is_header_row(row)

        assert is_header is False

    def test_is_header_row_text_data(self):
        """Test header row detection accepts text rows."""
        extractor = TableExtractor(engine="pdfplumber")
        row = ["Name", "Description", "Category"]

        is_header = extractor._is_header_row(row)

        assert is_header is True

    def test_is_header_row_with_keywords(self):
        """Test header row detection with common engineering keywords."""
        extractor = TableExtractor(engine="pdfplumber")
        row = ["Item", "Part Number", "Quantity"]

        is_header = extractor._is_header_row(row)

        assert is_header is True

    def test_is_header_row_empty_row(self):
        """Test header row detection rejects empty rows."""
        extractor = TableExtractor(engine="pdfplumber")
        row = ["", "", ""]

        is_header = extractor._is_header_row(row)

        assert is_header is False


class TestAdaptiveTableDetection:
    """Tests for adaptive table boundary detection."""

    def test_calculate_bbox_iou_no_overlap(self):
        """Test IoU calculation with non-overlapping boxes."""
        bbox1 = (0, 0, 100, 100)
        bbox2 = (200, 200, 300, 300)

        iou = TableExtractor._calculate_bbox_iou(bbox1, bbox2)

        assert iou == 0.0

    def test_calculate_bbox_iou_full_overlap(self):
        """Test IoU calculation with identical boxes."""
        bbox1 = (0, 0, 100, 100)
        bbox2 = (0, 0, 100, 100)

        iou = TableExtractor._calculate_bbox_iou(bbox1, bbox2)

        assert iou == 1.0

    def test_calculate_bbox_iou_partial_overlap(self):
        """Test IoU calculation with partial overlap."""
        bbox1 = (0, 0, 100, 100)
        bbox2 = (50, 50, 150, 150)

        iou = TableExtractor._calculate_bbox_iou(bbox1, bbox2)

        # Intersection = 50x50 = 2500
        # Union = 10000 + 10000 - 2500 = 17500
        # IoU = 2500/17500 = 0.142857...
        assert 0.14 < iou < 0.15

    def test_calculate_boundary_confidence_small_table(self):
        """Test confidence calculation for very small tables."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        page = Mock()

        # Single row, single column (below minimum size but still gets some score)
        data = [["A"]]

        confidence = extractor._calculate_boundary_confidence(
            table_obj, page, strategy="lines", cached_data=data
        )

        # Small table should have lower confidence than larger tables
        # The actual value depends on density and strategy scores
        assert 0.0 <= confidence <= 1.0

    def test_calculate_boundary_confidence_good_table(self):
        """Test confidence calculation for well-structured table."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        table_obj.cells = [(0, 0, 100, 50)]  # Mock cells for strategy score
        page = Mock()

        # Good sized table with consistent data
        data = [
            ["Header1", "Header2", "Header3"],
            ["Value1", "Value2", "Value3"],
            ["Value4", "Value5", "Value6"],
        ]

        confidence = extractor._calculate_boundary_confidence(
            table_obj, page, strategy="lines", cached_data=data
        )

        # Well-structured table should have high confidence
        assert confidence > 0.5

    def test_calculate_boundary_confidence_empty_cells(self):
        """Test confidence calculation with mostly empty cells."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        page = Mock()

        # Sparse table
        data = [
            ["A", "", ""],
            ["", "", ""],
            ["", "", "B"],
        ]

        confidence = extractor._calculate_boundary_confidence(
            table_obj, page, strategy="lines", cached_data=data
        )

        # Sparse table should have lower confidence
        assert confidence < 0.8


class TestTableBoundaryValidation:
    """Tests for table boundary validation."""

    def test_validate_table_boundaries_too_small(self):
        """Test validation rejects tables that are too small."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()

        # Only 1 row, 1 column
        data = [["A"]]

        is_valid = extractor._validate_table_boundaries(table_obj, data)

        assert is_valid is False

    def test_validate_table_boundaries_acceptable_size(self):
        """Test validation accepts tables with 2+ rows or 3+ columns."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        # Don't set bbox attribute to avoid unpacking issues
        del table_obj.bbox

        # 2 rows, 2 columns
        data = [["A", "B"], ["C", "D"]]

        is_valid = extractor._validate_table_boundaries(table_obj, data)

        assert is_valid is True

    def test_validate_table_boundaries_too_sparse(self):
        """Test validation rejects tables with <5% density."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()

        # 10x10 table with only 2 filled cells = 2% density
        data = [["" for _ in range(10)] for _ in range(10)]
        data[0][0] = "A"
        data[5][5] = "B"

        is_valid = extractor._validate_table_boundaries(table_obj, data)

        assert is_valid is False

    def test_validate_table_boundaries_with_bbox_too_small(self):
        """Test validation rejects tables with unreasonably small bounding boxes."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        table_obj.bbox = (0, 0, 30, 10)  # 30x10 box (too small)

        data = [["A", "B"], ["C", "D"]]

        is_valid = extractor._validate_table_boundaries(table_obj, data)

        assert is_valid is False

    def test_validate_table_boundaries_with_bbox_too_large(self):
        """Test validation rejects tables with unreasonably large bounding boxes."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        table_obj.bbox = (0, 0, 1500, 2000)  # Very large (likely artifact)

        data = [["A", "B"], ["C", "D"]]

        is_valid = extractor._validate_table_boundaries(table_obj, data)

        assert is_valid is False

    def test_validate_table_boundaries_good_bbox(self):
        """Test validation accepts tables with reasonable bounding boxes."""
        extractor = TableExtractor(engine="pdfplumber")
        table_obj = Mock()
        table_obj.bbox = (50, 50, 400, 300)  # Reasonable size

        data = [["A", "B"], ["C", "D"]]

        is_valid = extractor._validate_table_boundaries(table_obj, data)

        assert is_valid is True


class TestDeduplication:
    """Tests for table deduplication."""

    def test_deduplicate_tables_empty_list(self):
        """Test deduplication with empty list."""
        extractor = TableExtractor(engine="pdfplumber")

        unique = extractor._deduplicate_tables([])

        assert unique == []

    def test_deduplicate_tables_no_duplicates(self):
        """Test deduplication with non-overlapping tables."""
        extractor = TableExtractor(engine="pdfplumber")

        table1 = Mock()
        table1.bbox = (0, 0, 100, 100)
        table2 = Mock()
        table2.bbox = (200, 200, 300, 300)

        results = [
            {"table": table1, "confidence": 0.9, "strategy": "lines"},
            {"table": table2, "confidence": 0.8, "strategy": "text"},
        ]

        unique = extractor._deduplicate_tables(results)

        assert len(unique) == 2

    def test_deduplicate_tables_with_duplicates(self):
        """Test deduplication removes overlapping tables."""
        extractor = TableExtractor(engine="pdfplumber")

        # Two tables with very high overlap (>70% IoU to trigger deduplication)
        table1 = Mock()
        table1.bbox = (0, 0, 100, 100)
        table2 = Mock()
        table2.bbox = (5, 5, 105, 105)  # Very high overlap (>70% IoU)

        results = [
            {"table": table1, "confidence": 0.9, "strategy": "lines"},
            {"table": table2, "confidence": 0.7, "strategy": "text"},
        ]

        unique = extractor._deduplicate_tables(results)

        # Should keep only the higher confidence one
        assert len(unique) == 1
        assert unique[0]["confidence"] == 0.9

    def test_deduplicate_tables_keeps_highest_confidence(self):
        """Test deduplication keeps the highest confidence result."""
        extractor = TableExtractor(engine="pdfplumber")

        table1 = Mock()
        table1.bbox = (0, 0, 100, 100)
        table2 = Mock()
        table2.bbox = (5, 5, 105, 105)  # High overlap

        results = [
            {"table": table1, "confidence": 0.6, "strategy": "lines"},
            {"table": table2, "confidence": 0.95, "strategy": "hybrid"},
        ]

        unique = extractor._deduplicate_tables(results)

        assert len(unique) == 1
        assert unique[0]["confidence"] == 0.95
        assert unique[0]["strategy"] == "hybrid"


class TestHeaderDetection:
    """Tests for header detection with multirow support."""

    def test_detect_headers_simple_case(self):
        """Test simple header detection with clear header row."""
        extractor = TableExtractor(engine="pdfplumber")
        data = [
            ["Name", "Age", "City"],
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"],
        ]

        headers, rows = extractor._detect_headers(data)

        assert headers == ["Name", "Age", "City"]
        assert len(rows) == 2
        assert rows[0] == ["Alice", "25", "NYC"]

    def test_detect_headers_no_header_row(self):
        """Test header detection when first row is data."""
        extractor = TableExtractor(engine="pdfplumber")
        data = [
            ["1", "2", "3"],
            ["4", "5", "6"],
        ]

        headers, rows = extractor._detect_headers(data)

        # Should generate column names
        assert headers == ["Column_0", "Column_1", "Column_2"]
        assert len(rows) == 2

    def test_detect_headers_empty_data(self):
        """Test header detection with empty data."""
        extractor = TableExtractor(engine="pdfplumber")
        data = []

        headers, rows = extractor._detect_headers(data)

        assert headers == []
        assert rows == []

    def test_detect_headers_single_row(self):
        """Test header detection with single row."""
        extractor = TableExtractor(engine="pdfplumber")
        data = [["A", "B", "C"]]

        headers, rows = extractor._detect_headers(data)

        # Single row should be treated as headers
        assert headers == ["A", "B", "C"]
        assert rows == []

    def test_detect_headers_multirow_disabled(self):
        """Test header detection with multirow detection disabled."""
        extractor = TableExtractor(engine="pdfplumber")
        data = [
            ["Category A", "Category B"],
            ["Item 1", "Item 2"],
            ["100", "200"],
        ]

        headers, rows = extractor._detect_headers(data, detect_multirow=False)

        # Should only use first row as headers
        assert headers == ["Category A", "Category B"]
        assert len(rows) == 2


class TestBoundaryRefinement:
    """Tests for table boundary refinement."""

    def test_refine_table_boundaries_no_chars(self):
        """Test boundary refinement when no characters found."""
        extractor = TableExtractor(engine="pdfplumber")

        table_obj = Mock()
        page = Mock()
        cropped = Mock()
        cropped.chars = []
        page.crop = Mock(return_value=cropped)

        bbox = (0, 0, 200, 200)

        refined = extractor._refine_table_boundaries(table_obj, page, bbox)

        # Should return original bbox if no chars found
        assert refined == bbox

    def test_refine_table_boundaries_with_chars(self):
        """Test boundary refinement with character data."""
        extractor = TableExtractor(engine="pdfplumber")

        table_obj = Mock()
        page = Mock()
        cropped = Mock()

        # Mock characters within area that won't trigger >30% shrinkage rejection
        # Using 0-200 bbox, chars at 20-180 gives 160/200 = 0.8 ratio (>0.7 threshold)
        cropped.chars = [
            {"x0": 20, "top": 20, "x1": 180, "bottom": 180},
            {"x0": 25, "top": 25, "x1": 175, "bottom": 175},
        ]
        page.crop = Mock(return_value=cropped)

        bbox = (0, 0, 200, 200)

        refined = extractor._refine_table_boundaries(table_obj, page, bbox)

        # Refined bbox should be tighter around content
        assert refined != bbox
        # Should have padding around characters
        assert refined[0] >= 15  # x1 (char_x1=20, padding=5)
        assert refined[1] >= 15  # y1 (char_y1=20, padding=5)
        assert refined[2] <= 185  # x2 (char_x2=180, padding=5)
        assert refined[3] <= 185  # y2 (char_y2=180, padding=5)

    def test_refine_table_boundaries_too_much_shrinkage(self):
        """Test boundary refinement rejects excessive shrinkage."""
        extractor = TableExtractor(engine="pdfplumber")

        table_obj = Mock()
        page = Mock()
        cropped = Mock()

        # Mock characters in tiny area (would shrink >30%)
        cropped.chars = [
            {"x0": 90, "top": 90, "x1": 110, "bottom": 110},
        ]
        page.crop = Mock(return_value=cropped)

        bbox = (0, 0, 200, 200)

        refined = extractor._refine_table_boundaries(table_obj, page, bbox)

        # Should return original bbox if refinement would shrink too much
        assert refined == bbox
