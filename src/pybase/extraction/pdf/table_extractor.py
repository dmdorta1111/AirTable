"""Table extraction from PDF documents.

Specialized extractor for tables with advanced detection and parsing.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, BinaryIO

from pybase.extraction.base import ExtractedTable

# Import type inference with try/except for optional dependency
try:
    from pybase.extraction.pdf.type_inference import infer_column_types
    TYPE_INFERENCE_AVAILABLE = True
except ImportError:
    TYPE_INFERENCE_AVAILABLE = False
    infer_column_types = None

# Optional dependencies
try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

try:
    import camelot

    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    camelot = None


class TableExtractor:
    """
    Specialized table extraction from PDF documents.

    Uses pdfplumber by default, with optional camelot support
    for more complex table layouts.

    Example:
        extractor = TableExtractor()
        tables = extractor.extract_tables("document.pdf")
        for table in tables:
            records = table.to_records()
    """

    def __init__(self, engine: str = "auto"):
        """
        Initialize table extractor.

        Args:
            engine: Extraction engine - "pdfplumber", "camelot", or "auto"
        """
        self.engine = engine

        if not PDFPLUMBER_AVAILABLE and not CAMELOT_AVAILABLE:
            raise ImportError(
                "Table extraction requires pdfplumber or camelot. "
                "Install with: pip install pdfplumber camelot-py[cv]"
            )

    def extract_tables(
        self,
        file_path: str | Path,
        pages: list[int] | str = "all",
        table_settings: dict[str, Any] | None = None,
        infer_types: bool = False,
    ) -> list[ExtractedTable]:
        """
        Extract all tables from a PDF.

        Args:
            file_path: Path to PDF file
            pages: Page numbers (1-indexed) or "all"
            table_settings: Engine-specific settings for table detection
            infer_types: Whether to infer column data types (default: False)

        Returns:
            List of ExtractedTable objects
        """
        file_path = Path(file_path)

        if self.engine == "auto":
            if PDFPLUMBER_AVAILABLE:
                return self._extract_with_pdfplumber(file_path, pages, table_settings, infer_types)
            elif CAMELOT_AVAILABLE:
                return self._extract_with_camelot(file_path, pages, table_settings, infer_types)
        elif self.engine == "pdfplumber":
            return self._extract_with_pdfplumber(file_path, pages, table_settings, infer_types)
        elif self.engine == "camelot":
            return self._extract_with_camelot(file_path, pages, table_settings, infer_types)

        return []

    def _detect_tables_adaptive(
        self,
        page: Any,
        settings: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Detect tables using adaptive multi-strategy approach.

        Tries multiple detection strategies and returns results with confidence scores:
        1. Line-based detection (works well for bordered tables)
        2. Text-alignment detection (works for tables without borders)
        3. Hybrid approach combining both strategies

        Optimization: Early termination when high-confidence tables are found.

        Args:
            page: pdfplumber page object
            settings: Detection settings from user

        Returns:
            List of dictionaries with 'table' and 'confidence' keys
        """
        all_results = []

        # Strategy 1: Line-based detection (default, best for bordered tables)
        line_settings = {
            "vertical_strategy": settings.get("vertical_strategy", "lines"),
            "horizontal_strategy": settings.get("horizontal_strategy", "lines"),
            "snap_tolerance": settings.get("snap_tolerance", 3),
            "join_tolerance": settings.get("join_tolerance", 3),
            "edge_min_length": settings.get("edge_min_length", 3),
            "min_words_vertical": settings.get("min_words_vertical", 3),
            "min_words_horizontal": settings.get("min_words_horizontal", 1),
        }

        try:
            line_tables = page.find_tables(line_settings)
            for table in line_tables:
                confidence = self._calculate_boundary_confidence(table, page, strategy="lines")
                all_results.append({"table": table, "confidence": confidence, "strategy": "lines"})

                # Early termination: If we found a very high confidence table, skip other strategies
                if confidence > 0.92:
                    return all_results
        except Exception:
            pass

        # Early termination: If we have multiple high-confidence tables, no need for fallback
        if len(all_results) >= 2 and all(r["confidence"] >= 0.85 for r in all_results):
            return all_results

        # Strategy 2: Text-alignment detection (fallback for borderless tables)
        # Only try if line-based found few or low-confidence tables
        if len(all_results) == 0 or all(r["confidence"] < 0.7 for r in all_results):
            text_settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "snap_tolerance": settings.get("snap_tolerance", 3),
                "join_tolerance": settings.get("join_tolerance", 3),
                "text_tolerance": settings.get("text_tolerance", 3),
                "text_x_tolerance": settings.get("text_x_tolerance", 3),
                "text_y_tolerance": settings.get("text_y_tolerance", 3),
            }

            try:
                text_tables = page.find_tables(text_settings)
                for table in text_tables:
                    confidence = self._calculate_boundary_confidence(table, page, strategy="text")
                    all_results.append({"table": table, "confidence": confidence, "strategy": "text"})
            except Exception:
                pass

        # Strategy 3: Hybrid approach (lines + text)
        # Skip if we already have good results from previous strategies
        if len(all_results) < 2 or any(0.5 < r["confidence"] < 0.9 for r in all_results):
            # Skip hybrid if we already have high-confidence results
            if not (len(all_results) > 0 and max(r["confidence"] for r in all_results) > 0.88):
                hybrid_settings = {
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "text",
                    "snap_tolerance": settings.get("snap_tolerance", 3),
                    "join_tolerance": settings.get("join_tolerance", 3),
                }

                try:
                    hybrid_tables = page.find_tables(hybrid_settings)
                    for table in hybrid_tables:
                        confidence = self._calculate_boundary_confidence(table, page, strategy="hybrid")
                        all_results.append({"table": table, "confidence": confidence, "strategy": "hybrid"})
                except Exception:
                    pass

        # Deduplicate tables that are very similar (overlapping bboxes)
        unique_results = self._deduplicate_tables(all_results)

        # Sort by confidence and return
        unique_results.sort(key=lambda x: x["confidence"], reverse=True)

        return unique_results

    def _deduplicate_tables(
        self,
        table_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Remove duplicate tables detected by different strategies.

        Tables are considered duplicates if their bounding boxes overlap significantly
        (>70% intersection over union).

        Optimization: Sort by confidence first, early termination, reduce comparisons.

        Args:
            table_results: List of table detection results

        Returns:
            Deduplicated list of table results
        """
        if not table_results:
            return []

        # Optimization: Sort by confidence (descending) to keep best results
        sorted_results = sorted(table_results, key=lambda x: x["confidence"], reverse=True)

        unique = []
        iou_threshold = 0.7

        for result in sorted_results:
            table = result["table"]
            if not hasattr(table, "bbox") or not table.bbox:
                unique.append(result)
                continue

            bbox1 = table.bbox
            is_duplicate = False

            # Only compare with already accepted unique tables
            for existing in unique:
                existing_table = existing["table"]
                if not hasattr(existing_table, "bbox") or not existing_table.bbox:
                    continue

                bbox2 = existing_table.bbox

                # Calculate intersection over union (IoU)
                iou = self._calculate_bbox_iou(bbox1, bbox2)

                # If >70% overlap, consider duplicate
                if iou > iou_threshold:
                    is_duplicate = True
                    # Since sorted by confidence, existing always has higher or equal confidence
                    break

            if not is_duplicate:
                unique.append(result)

        return unique

    @staticmethod
    def _calculate_bbox_iou(
        bbox1: tuple[float, float, float, float],
        bbox2: tuple[float, float, float, float],
    ) -> float:
        """
        Calculate Intersection over Union (IoU) for two bounding boxes.

        Optimized: Static method, early termination, reduced operations.

        Args:
            bbox1: First bbox (x1, y1, x2, y2)
            bbox2: Second bbox (x1, y1, x2, y2)

        Returns:
            IoU score between 0 and 1
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Early termination: check if boxes can possibly intersect
        if x2_1 < x1_2 or x2_2 < x1_1 or y2_1 < y1_2 or y2_2 < y1_1:
            return 0.0

        # Calculate intersection bounds
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)

        # Calculate areas
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        bbox1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        bbox2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = bbox1_area + bbox2_area - intersection_area

        # Avoid division by zero
        return intersection_area / union_area if union_area > 0 else 0.0

    def _calculate_boundary_confidence(
        self,
        table_obj: Any,
        page: Any,
        strategy: str = "lines",
        cached_data: list[list[Any]] | None = None,
    ) -> float:
        """
        Calculate confidence score for detected table boundaries.

        Factors considered:
        - Presence of clear cell boundaries (lines or consistent spacing)
        - Row/column alignment consistency
        - Table size (too small might be false positive)
        - Cell content density
        - Edge detection quality

        Optimization: Accepts cached_data to avoid redundant extraction.

        Args:
            table_obj: pdfplumber table object
            page: pdfplumber page object
            strategy: Detection strategy used ("lines", "text", "hybrid")
            cached_data: Pre-extracted table data to avoid re-extraction

        Returns:
            Confidence score between 0 and 1
        """
        # Use cached data if available, otherwise extract
        if cached_data is not None:
            data = cached_data
        else:
            try:
                data = table_obj.extract()
                if not data or len(data) == 0:
                    return 0.0
            except Exception:
                return 0.0

        # Factor 1: Table size validation (0.0 - 0.25)
        num_rows = len(data)
        num_cols = len(data[0]) if data else 0

        # Quick reject for invalid tables
        if num_rows < 1 or num_cols < 1:
            return 0.0

        total_cells = num_rows * num_cols

        if num_rows >= 2 and num_cols >= 2:
            # Good size table
            size_score = min(0.25, total_cells / 100)
        elif num_rows >= 1 and num_cols >= 3:
            # Acceptable size
            size_score = 0.15
        else:
            # Too small, likely false positive
            size_score = 0.0

        # Factor 2: Content density (0.0 - 0.25)
        # Optimized: count in single pass
        non_empty_cells = 0
        for row in data:
            for cell in row:
                if cell is not None and str(cell).strip():
                    non_empty_cells += 1

        density = non_empty_cells / total_cells if total_cells > 0 else 0
        # Sweet spot is 30-90% filled
        if 0.3 <= density <= 0.9:
            density_score = 0.25
        elif 0.1 <= density < 0.3 or 0.9 < density <= 1.0:
            density_score = 0.15
        else:
            density_score = 0.05

        # Factor 3: Row consistency (0.0 - 0.25)
        # Optimized: single pass with min/max
        max_cols = num_cols
        min_cols = num_cols
        for row in data[1:]:  # Skip first row since we already have it
            row_len = len(row)
            if row_len > max_cols:
                max_cols = row_len
            if row_len < min_cols:
                min_cols = row_len

        if max_cols == min_cols:
            consistency_score = 0.25
        elif max_cols - min_cols <= 2:
            consistency_score = 0.15
        else:
            consistency_score = 0.05

        # Factor 4: Strategy-specific confidence (0.0 - 0.25)
        # Line-based is most reliable, text-based less so
        if strategy == "lines":
            # Check if table has visible borders
            if hasattr(table_obj, "cells") and table_obj.cells:
                strategy_score = 0.25
            else:
                strategy_score = 0.15
        elif strategy == "text":
            # Text alignment is less reliable
            strategy_score = 0.15
        elif strategy == "hybrid":
            strategy_score = 0.20
        else:
            strategy_score = 0.10

        # Sum all factors
        confidence = size_score + density_score + consistency_score + strategy_score

        # Ensure confidence is between 0 and 1
        return min(1.0, max(0.0, confidence))

    def _validate_table_boundaries(
        self,
        table_obj: Any,
        data: list[list[Any]],
        density: float | None = None,
    ) -> bool:
        """
        Validate that detected table boundaries are reasonable.

        Filters out false positives by checking:
        - Minimum table size (at least 2 rows or 3 columns)
        - Maximum empty cell ratio
        - Reasonable bounding box dimensions

        Optimization: Accepts pre-computed density to avoid recalculation.

        Args:
            table_obj: pdfplumber table object
            data: Extracted table data
            density: Pre-computed content density (0-1)

        Returns:
            True if table appears valid, False otherwise
        """
        if not data or len(data) == 0:
            return False

        # Check minimum size
        num_rows = len(data)
        num_cols = len(data[0]) if data else 0

        # Must have at least 2 rows (header + data) OR at least 3 columns
        if num_rows < 2 and num_cols < 3:
            return False

        # Check density (use pre-computed if available)
        if density is None:
            # Calculate density
            non_empty_cells = sum(
                1 for row in data for cell in row
                if cell is not None and str(cell).strip()
            )
            total_cells = num_rows * num_cols if num_cols > 0 else 0
            density = non_empty_cells / total_cells if total_cells > 0 else 0

        # Reject if less than 5% filled (too sparse)
        if density < 0.05:
            return False

        # Check bounding box dimensions if available
        if hasattr(table_obj, "bbox") and table_obj.bbox:
            x1, y1, x2, y2 = table_obj.bbox
            width = x2 - x1
            height = y2 - y1

            # Reject unreasonably small tables (likely noise)
            if width < 50 or height < 20:
                return False

            # Reject unreasonably large tables (likely page-spanning artifacts)
            if width > 1000 or height > 1500:
                return False

        return True

    def _refine_table_boundaries(
        self,
        table_obj: Any,
        page: Any,
        bbox: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float]:
        """
        Refine table boundaries for improved accuracy.

        Adjusts bounding box to:
        - Trim excessive whitespace
        - Align to text baselines
        - Snap to visible lines when present

        Args:
            table_obj: pdfplumber table object
            page: pdfplumber page object
            bbox: Initial bounding box (x1, y1, x2, y2)

        Returns:
            Refined bounding box (x1, y1, x2, y2)
        """
        x1, y1, x2, y2 = bbox

        # Get all text within the table area
        try:
            cropped = page.crop(bbox)
            chars = cropped.chars

            if chars:
                # Find actual content boundaries
                char_x1 = min(c["x0"] for c in chars)
                char_y1 = min(c["top"] for c in chars)
                char_x2 = max(c["x1"] for c in chars)
                char_y2 = max(c["bottom"] for c in chars)

                # Add small padding (5 points) around text
                padding = 5
                refined_x1 = max(x1, char_x1 - padding)
                refined_y1 = max(y1, char_y1 - padding)
                refined_x2 = min(x2, char_x2 + padding)
                refined_y2 = min(y2, char_y2 + padding)

                # Only use refined boundaries if they're reasonable
                # (not shrinking by more than 30%)
                width_ratio = (refined_x2 - refined_x1) / (x2 - x1) if x2 != x1 else 1
                height_ratio = (refined_y2 - refined_y1) / (y2 - y1) if y2 != y1 else 1

                if width_ratio > 0.7 and height_ratio > 0.7:
                    return (refined_x1, refined_y1, refined_x2, refined_y2)

        except Exception:
            pass

        # If refinement fails or produces bad results, return original
        return bbox

    def _extract_with_pdfplumber(
        self,
        file_path: Path,
        pages: list[int] | str,
        settings: dict[str, Any] | None,
        infer_types: bool = False,
    ) -> list[ExtractedTable]:
        """
        Extract tables using pdfplumber with adaptive boundary detection.

        Optimization: Reduced redundant data extractions, cached computations.
        """
        tables = []
        settings = settings or {}

        with pdfplumber.open(file_path) as pdf:
            if pages == "all":
                pages_to_process = range(len(pdf.pages))
            else:
                pages_to_process = [p - 1 for p in pages]  # Convert to 0-indexed

            for page_idx in pages_to_process:
                if page_idx < 0 or page_idx >= len(pdf.pages):
                    continue

                page = pdf.pages[page_idx]
                page_num = page_idx + 1

                # Use adaptive detection with multiple strategies
                found_tables = self._detect_tables_adaptive(page, settings)

                for table_info in found_tables:
                    table = table_info["table"]
                    confidence = table_info["confidence"]

                    # Extract data once and reuse
                    try:
                        data = table.extract()
                    except Exception:
                        continue

                    if not data or len(data) == 0:
                        continue

                    # Validate table boundaries (no need to pass density since confidence already computed it)
                    if not self._validate_table_boundaries(table, data):
                        continue

                    # Get bounding box (refinement is expensive, only do for low confidence tables)
                    bbox = table.bbox if hasattr(table, "bbox") else None
                    if bbox and confidence < 0.8:
                        # Only refine boundaries for lower confidence tables
                        bbox = self._refine_table_boundaries(table, page, bbox)

                    # Detect headers with multi-row support
                    headers, rows = self._detect_headers(data, table_obj=table)

                    # Infer column types if requested
                    column_types = []
                    if infer_types and headers and rows and TYPE_INFERENCE_AVAILABLE:
                        column_types = infer_column_types(headers, rows)

                    tables.append(
                        ExtractedTable(
                            headers=headers,
                            rows=rows,
                            page=page_num,
                            bbox=bbox,
                            confidence=confidence,
                            column_types=column_types,
                        )
                    )

        return tables

    def _extract_with_camelot(
        self,
        file_path: Path,
        pages: list[int] | str,
        settings: dict[str, Any] | None,
        infer_types: bool = False,
    ) -> list[ExtractedTable]:
        """Extract tables using camelot."""
        if not CAMELOT_AVAILABLE:
            raise ImportError("Camelot not available")

        tables = []
        settings = settings or {}

        # Convert pages format for camelot
        if pages == "all":
            pages_str = "all"
        else:
            pages_str = ",".join(str(p) for p in pages)

        # Camelot extraction
        flavor = settings.get("flavor", "lattice")  # lattice or stream
        camelot_tables = camelot.read_pdf(
            str(file_path),
            pages=pages_str,
            flavor=flavor,
        )

        for ct in camelot_tables:
            df = ct.df
            if df.empty:
                continue

            # Convert dataframe to our format
            data = [df.columns.tolist()] + df.values.tolist()
            headers, rows = self._detect_headers(data)

            # Infer column types if requested
            column_types = []
            if infer_types and headers and rows and TYPE_INFERENCE_AVAILABLE:
                column_types = infer_column_types(headers, rows)

            tables.append(
                ExtractedTable(
                    headers=headers,
                    rows=rows,
                    page=ct.page,
                    confidence=ct.accuracy / 100 if hasattr(ct, "accuracy") else 1.0,
                    column_types=column_types,
                )
            )

        return tables

    def _detect_merged_cells(
        self, table_obj: Any, data: list[list[Any]]
    ) -> list[dict[str, Any]]:
        """
        Detect merged cells in a table by analyzing cell structure.

        Uses pdfplumber's table.cells API to identify cells that span
        multiple rows or columns based on bounding box analysis.

        Args:
            table_obj: pdfplumber table object with cells attribute
            data: Extracted table data for validation

        Returns:
            List of merged cell information dictionaries with:
                - row_start: Starting row index (0-based)
                - row_end: Ending row index (exclusive)
                - col_start: Starting column index (0-based)
                - col_end: Ending column index (exclusive)
                - value: Cell content
                - bbox: Bounding box (x1, y1, x2, y2)
        """
        merged_cells = []

        if not hasattr(table_obj, "cells") or not table_obj.cells:
            return merged_cells

        cells = table_obj.cells
        if not cells:
            return merged_cells

        # Build a grid map to track cell positions
        # Calculate average cell dimensions to detect spans
        cell_heights = []
        cell_widths = []

        for cell in cells:
            if not cell:
                continue
            x1, y1, x2, y2 = cell
            cell_widths.append(x2 - x1)
            cell_heights.append(y2 - y1)

        if not cell_heights or not cell_widths:
            return merged_cells

        # Calculate median dimensions (more robust than mean for merged cells)
        cell_widths_sorted = sorted(cell_widths)
        cell_heights_sorted = sorted(cell_heights)
        median_width = cell_widths_sorted[len(cell_widths_sorted) // 2]
        median_height = cell_heights_sorted[len(cell_heights_sorted) // 2]

        # Detect cells that are significantly larger than median (merged cells)
        # Use 1.5x threshold to account for minor variations
        width_threshold = median_width * 1.5
        height_threshold = median_height * 1.5

        # Group cells by row (using y-coordinate)
        rows_by_y = {}
        for cell in cells:
            if not cell:
                continue
            x1, y1, x2, y2 = cell
            # Group by top y-coordinate (with small tolerance)
            row_key = round(y1, 1)
            if row_key not in rows_by_y:
                rows_by_y[row_key] = []
            rows_by_y[row_key].append(cell)

        # Sort rows by y-coordinate
        sorted_rows = sorted(rows_by_y.items(), key=lambda x: x[0])

        # Analyze each cell for merging
        for row_idx, (_, row_cells) in enumerate(sorted_rows):
            # Sort cells in row by x-coordinate
            row_cells_sorted = sorted(row_cells, key=lambda c: c[0])

            for col_idx, cell in enumerate(row_cells_sorted):
                x1, y1, x2, y2 = cell
                width = x2 - x1
                height = y2 - y1

                # Detect horizontal merge (spans multiple columns)
                col_span = round(width / median_width) if median_width > 0 else 1
                # Detect vertical merge (spans multiple rows)
                row_span = round(height / median_height) if median_height > 0 else 1

                # Only record if cell spans more than 1 row or column
                if col_span > 1 or row_span > 1:
                    # Try to get cell value from data
                    cell_value = ""
                    if row_idx < len(data) and col_idx < len(data[row_idx]):
                        cell_value = data[row_idx][col_idx]

                    merged_cells.append(
                        {
                            "row_start": row_idx,
                            "row_end": row_idx + row_span,
                            "col_start": col_idx,
                            "col_end": col_idx + col_span,
                            "value": str(cell_value) if cell_value else "",
                            "bbox": cell,
                        }
                    )

        return merged_cells

    def _detect_multirow_headers(
        self,
        data: list[list[Any]],
        table_obj: Any = None,
        max_header_rows: int = 3,
    ) -> tuple[list[str], int]:
        """
        Detect multi-row spanning headers in table data.

        Analyzes first few rows to identify hierarchical or multi-level headers
        common in engineering BOMs and specification tables.

        Args:
            data: Extracted table data
            table_obj: pdfplumber table object for merged cell detection
            max_header_rows: Maximum number of rows to consider as headers (default: 3)

        Returns:
            Tuple of (combined_headers, header_row_count):
                - combined_headers: List of header strings combining multi-row structure
                - header_row_count: Number of rows identified as headers

        Example:
            Input rows:
                ["Category A", "", "Category B", ""]
                ["Item 1", "Item 2", "Item 3", "Item 4"]
            Output:
                ["Category A - Item 1", "Category A - Item 2",
                 "Category B - Item 3", "Category B - Item 4"], 2
        """
        if not data or len(data) < 2:
            return [], 0

        # Get merged cell information if available
        merged_cells = []
        if table_obj is not None:
            merged_cells = self._detect_merged_cells(table_obj, data)

        # Determine how many rows are headers by analyzing content patterns
        header_row_count = 1
        max_rows_to_check = min(max_header_rows, len(data) - 1)

        for row_idx in range(max_rows_to_check):
            current_row = data[row_idx]
            next_row = data[row_idx + 1] if row_idx + 1 < len(data) else []

            # Check if current row has header characteristics
            is_header_row = self._is_header_row(current_row, next_row)

            if is_header_row and row_idx < max_rows_to_check:
                header_row_count = row_idx + 1
            else:
                break

        # If only one header row detected, return simple headers
        if header_row_count == 1:
            return [], 0

        # Build combined headers from multi-row structure
        num_cols = len(data[0]) if data else 0
        combined_headers = []

        # Create column-spanning map from merged cells
        col_spans = {}  # Maps (row, col) to span width
        for merged in merged_cells:
            if merged["row_start"] < header_row_count:
                for col in range(merged["col_start"], merged["col_end"]):
                    col_spans[(merged["row_start"], col)] = {
                        "span": merged["col_end"] - merged["col_start"],
                        "value": merged["value"],
                    }

        # Build header for each column
        for col_idx in range(num_cols):
            header_parts = []

            for row_idx in range(header_row_count):
                if row_idx >= len(data):
                    break

                row = data[row_idx]
                if col_idx >= len(row):
                    continue

                # Check if this cell is part of a merged/spanning cell
                cell_key = (row_idx, col_idx)
                if cell_key in col_spans:
                    span_info = col_spans[cell_key]
                    # Only add the value once (at the start of the span)
                    if span_info["value"] and span_info["value"].strip():
                        # Check if this is the first column in the span
                        is_span_start = True
                        for check_col in range(col_idx):
                            if (row_idx, check_col) in col_spans:
                                if col_spans[(row_idx, check_col)]["value"] == span_info["value"]:
                                    is_span_start = False
                                    break

                        if is_span_start:
                            header_parts.append(str(span_info["value"]).strip())
                else:
                    # Regular cell
                    cell_value = row[col_idx]
                    if cell_value and str(cell_value).strip():
                        header_parts.append(str(cell_value).strip())

            # Combine header parts with separator
            if header_parts:
                combined_header = " - ".join(header_parts)
                combined_headers.append(combined_header)
            else:
                combined_headers.append(f"Column_{col_idx}")

        return combined_headers, header_row_count

    def _is_header_row(self, row: list[Any], next_row: list[Any] | None = None) -> bool:
        """
        Determine if a row is likely a header row.

        Uses heuristics:
        - Contains mostly string values
        - Not all numeric
        - Different pattern from next row (if headers, next row might be data)
        - Contains common header keywords

        Args:
            row: Row to check
            next_row: Following row for comparison

        Returns:
            True if row appears to be a header row
        """
        if not row:
            return False

        non_empty_values = [v for v in row if v is not None and str(v).strip()]
        if not non_empty_values:
            return False

        # Check for numeric-only rows (likely data, not headers)
        numeric_count = 0
        string_count = 0

        for val in non_empty_values:
            val_str = str(val).strip()
            try:
                # Try to parse as number
                float(val_str.replace(",", "").replace("$", ""))
                numeric_count += 1
            except ValueError:
                string_count += 1

        # If mostly numeric, probably not a header
        if numeric_count > 0 and numeric_count >= string_count:
            return False

        # Check for common header keywords
        header_keywords = [
            "item", "part", "qty", "quantity", "description", "number", "no",
            "material", "finish", "revision", "rev", "size", "type", "category",
            "name", "value", "unit", "specification", "spec", "drawing"
        ]

        keyword_matches = 0
        for val in non_empty_values:
            val_lower = str(val).lower()
            if any(keyword in val_lower for keyword in header_keywords):
                keyword_matches += 1

        # If multiple keyword matches, likely a header
        if keyword_matches >= 2:
            return True

        # If mostly strings and not all cells are empty, could be header
        if string_count >= len(non_empty_values) * 0.7:
            return True

        return False

    def _detect_headers(
        self,
        data: list[list[Any]],
        table_obj: Any = None,
        detect_multirow: bool = True,
    ) -> tuple[list[str], list[list[Any]]]:
        """
        Detect table headers with support for multi-row spanning headers.

        Heuristics:
        - First row is all strings
        - First row values are unique
        - First row values don't look like data (not numeric)
        - Multi-row header detection for complex tables

        Args:
            data: Extracted table data
            table_obj: pdfplumber table object for merged cell analysis
            detect_multirow: Enable multi-row header detection (default: True)

        Returns:
            Tuple of (headers, data_rows)
        """
        if not data or len(data) < 2:
            if data:
                return [str(c) for c in data[0]], []
            return [], []

        # Try multi-row header detection first if enabled
        if detect_multirow and len(data) >= 3:
            multirow_headers, header_row_count = self._detect_multirow_headers(
                data, table_obj
            )
            if header_row_count > 1 and multirow_headers:
                # Multi-row headers detected
                rows = [[str(c) if c else "" for c in row] for row in data[header_row_count:]]
                return multirow_headers, rows

        # Fall back to simple single-row header detection
        first_row = data[0]
        second_row = data[1] if len(data) > 1 else []

        # Check if first row looks like headers
        first_row_is_headers = True

        # Check if all values in first row are strings and non-empty
        for val in first_row:
            if val is None or val == "":
                continue
            # If it looks numeric, probably not a header
            try:
                float(str(val).replace(",", "").replace("$", ""))
                # It's numeric - check if second row is also numeric
                # If both are numeric, first row is not headers
                if second_row:
                    try:
                        float(
                            str(second_row[first_row.index(val)]).replace(",", "").replace("$", "")
                        )
                        first_row_is_headers = False
                        break
                    except (ValueError, IndexError):
                        pass
            except ValueError:
                pass

        # Check uniqueness of first row
        non_empty = [v for v in first_row if v]
        if len(non_empty) != len(set(non_empty)):
            first_row_is_headers = False

        if first_row_is_headers:
            headers = [str(h) if h else f"Column_{i}" for i, h in enumerate(first_row)]
            rows = [[str(c) if c else "" for c in row] for row in data[1:]]
        else:
            headers = [f"Column_{i}" for i in range(len(first_row))]
            rows = [[str(c) if c else "" for c in row] for row in data]

        return headers, rows

    def extract_specific_table(
        self,
        file_path: str | Path,
        page: int,
        bbox: tuple[float, float, float, float] | None = None,
        infer_types: bool = False,
    ) -> ExtractedTable | None:
        """
        Extract a specific table from a known location.

        Args:
            file_path: Path to PDF file
            page: Page number (1-indexed)
            bbox: Bounding box (x1, y1, x2, y2) or None for first table on page
            infer_types: Whether to infer column data types (default: False)

        Returns:
            ExtractedTable or None if not found
        """
        if not PDFPLUMBER_AVAILABLE:
            return None

        with pdfplumber.open(file_path) as pdf:
            if page < 1 or page > len(pdf.pages):
                return None

            pdf_page = pdf.pages[page - 1]

            if bbox:
                # Crop to specific area
                cropped = pdf_page.crop(bbox)
                tables = cropped.extract_tables()
            else:
                tables = pdf_page.extract_tables()

            if tables:
                headers, rows = self._detect_headers(tables[0])

                # Infer column types if requested
                column_types = []
                if infer_types and headers and rows and TYPE_INFERENCE_AVAILABLE:
                    column_types = infer_column_types(headers, rows)

                return ExtractedTable(
                    headers=headers,
                    rows=rows,
                    page=page,
                    bbox=bbox,
                    column_types=column_types,
                )

        return None
