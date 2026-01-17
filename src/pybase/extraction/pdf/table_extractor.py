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
