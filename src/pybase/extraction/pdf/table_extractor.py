"""Table extraction from PDF documents.

Specialized extractor for tables with advanced detection and parsing.
"""

from pathlib import Path
from typing import Any, BinaryIO

from pybase.extraction.base import ExtractedTable

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
    ) -> list[ExtractedTable]:
        """
        Extract all tables from a PDF.

        Args:
            file_path: Path to PDF file
            pages: Page numbers (1-indexed) or "all"
            table_settings: Engine-specific settings for table detection

        Returns:
            List of ExtractedTable objects
        """
        file_path = Path(file_path)

        if self.engine == "auto":
            if PDFPLUMBER_AVAILABLE:
                return self._extract_with_pdfplumber(file_path, pages, table_settings)
            elif CAMELOT_AVAILABLE:
                return self._extract_with_camelot(file_path, pages, table_settings)
        elif self.engine == "pdfplumber":
            return self._extract_with_pdfplumber(file_path, pages, table_settings)
        elif self.engine == "camelot":
            return self._extract_with_camelot(file_path, pages, table_settings)

        return []

    def _extract_with_pdfplumber(
        self,
        file_path: Path,
        pages: list[int] | str,
        settings: dict[str, Any] | None,
    ) -> list[ExtractedTable]:
        """Extract tables using pdfplumber."""
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

                # Apply table settings if provided
                table_settings = {
                    "vertical_strategy": settings.get("vertical_strategy", "lines"),
                    "horizontal_strategy": settings.get("horizontal_strategy", "lines"),
                    "snap_tolerance": settings.get("snap_tolerance", 3),
                    "join_tolerance": settings.get("join_tolerance", 3),
                }

                # Find tables on page
                found_tables = page.find_tables(table_settings)

                for table in found_tables:
                    data = table.extract()
                    if data and len(data) > 0:
                        # Get bounding box
                        bbox = table.bbox if hasattr(table, "bbox") else None

                        # Detect headers
                        headers, rows = self._detect_headers(data)

                        tables.append(
                            ExtractedTable(
                                headers=headers,
                                rows=rows,
                                page=page_num,
                                bbox=bbox,
                            )
                        )

        return tables

    def _extract_with_camelot(
        self,
        file_path: Path,
        pages: list[int] | str,
        settings: dict[str, Any] | None,
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

            tables.append(
                ExtractedTable(
                    headers=headers,
                    rows=rows,
                    page=ct.page,
                    confidence=ct.accuracy / 100 if hasattr(ct, "accuracy") else 1.0,
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

    def _detect_headers(self, data: list[list[Any]]) -> tuple[list[str], list[list[Any]]]:
        """
        Detect if first row is headers.

        Heuristics:
        - First row is all strings
        - First row values are unique
        - First row values don't look like data (not numeric)
        """
        if not data or len(data) < 2:
            if data:
                return [str(c) for c in data[0]], []
            return [], []

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
    ) -> ExtractedTable | None:
        """
        Extract a specific table from a known location.

        Args:
            file_path: Path to PDF file
            page: Page number (1-indexed)
            bbox: Bounding box (x1, y1, x2, y2) or None for first table on page

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
                return ExtractedTable(
                    headers=headers,
                    rows=rows,
                    page=page,
                    bbox=bbox,
                )

        return None
