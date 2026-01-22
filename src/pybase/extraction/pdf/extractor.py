"""Main PDF extractor for PyBase.

Coordinates extraction of tables, text, and other content from PDF files.
"""

from pathlib import Path
from typing import Any, BinaryIO
import re

from pybase.extraction.base import (
    ExtractionResult,
    ExtractedTable,
    ExtractedDimension,
    ExtractedText,
    ExtractedTitleBlock,
)

# Optional dependencies
try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    PdfReader = None

try:
    from pybase.extraction.pdf.ocr import OCRExtractor

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    OCRExtractor = None


class PDFExtractor:
    """
    Main PDF extraction class.

    Extracts tables, text, dimensions, and metadata from PDF documents.
    Uses pdfplumber for table extraction and pypdf for text/metadata.
    Optionally uses OCR (Tesseract) for scanned PDFs.

    Example:
        # Standard extraction
        extractor = PDFExtractor()
        result = extractor.extract("drawing.pdf", extract_tables=True)
        for table in result.tables:
            print(table.to_records())

        # With OCR for scanned PDFs
        extractor = PDFExtractor(enable_ocr=True)
        result = extractor.extract("scanned.pdf", extract_tables=True)
    """

    def __init__(
        self,
        enable_ocr: bool = False,
        ocr_language: str = "eng",
        tesseract_cmd: str | None = None,
    ):
        """
        Initialize PDF extractor.

        Args:
            enable_ocr: Enable OCR for scanned PDFs (default False)
            ocr_language: OCR language code (e.g., "eng", "deu", "fra")
            tesseract_cmd: Path to tesseract executable (auto-detected if None)
        """
        if not PDFPLUMBER_AVAILABLE and not PYPDF_AVAILABLE:
            raise ImportError(
                "PDF extraction requires pdfplumber or pypdf. "
                "Install with: pip install pdfplumber pypdf"
            )

        self.enable_ocr = enable_ocr
        self.ocr_extractor = None

        if enable_ocr:
            if not OCR_AVAILABLE:
                raise ImportError(
                    "OCR extraction requires pytesseract, Pillow, and pdf2image. "
                    "Install with: pip install pytesseract Pillow pdf2image"
                )
            try:
                self.ocr_extractor = OCRExtractor(
                    tesseract_cmd=tesseract_cmd,
                    language=ocr_language,
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize OCR: {str(e)}")

    def extract(
        self,
        file_path: str | Path | BinaryIO,
        extract_tables: bool = True,
        extract_text: bool = True,
        extract_dimensions: bool = False,
        extract_title_block: bool = False,
        pages: list[int] | None = None,
        use_ocr: bool | None = None,
    ) -> ExtractionResult:
        """
        Extract content from a PDF file.

        Args:
            file_path: Path to PDF file or file-like object
            extract_tables: Whether to extract tables
            extract_text: Whether to extract text blocks
            extract_dimensions: Whether to extract dimension callouts
            extract_title_block: Whether to extract title block info
            pages: Specific pages to extract (1-indexed), or None for all
            use_ocr: Force OCR usage (None=auto-detect scanned PDFs, True=always, False=never)

        Returns:
            ExtractionResult with extracted content
        """
        if isinstance(file_path, (str, Path)):
            source_file = str(file_path)
        else:
            source_file = getattr(file_path, "name", "uploaded_file.pdf")

        result = ExtractionResult(
            source_file=source_file,
            source_type="pdf",
        )

        try:
            # Determine if we should use OCR
            should_use_ocr = False
            if use_ocr is True:
                should_use_ocr = True
            elif use_ocr is None and self.enable_ocr:
                # Auto-detect if PDF is scanned
                should_use_ocr = self.is_scanned(file_path)

            # Try standard extraction first if not forcing OCR
            if not should_use_ocr or use_ocr is None:
                if PDFPLUMBER_AVAILABLE:
                    self._extract_with_pdfplumber(
                        file_path,
                        result,
                        extract_tables,
                        extract_text,
                        extract_dimensions,
                        extract_title_block,
                        pages,
                    )
                elif PYPDF_AVAILABLE:
                    self._extract_with_pypdf(file_path, result, extract_text, pages)
                    if extract_tables:
                        result.warnings.append("Table extraction requires pdfplumber")

            # Use OCR if enabled and needed
            if self.enable_ocr and self.ocr_extractor:
                # Use OCR if forced, or if auto-detect says scanned, or if no tables found
                need_ocr = (
                    should_use_ocr
                    or (use_ocr is None and extract_tables and len(result.tables) == 0)
                )

                if need_ocr:
                    self._extract_with_ocr(
                        file_path,
                        result,
                        extract_tables,
                        extract_text,
                        pages,
                    )

        except Exception as e:
            result.errors.append(f"PDF extraction failed: {str(e)}")

        return result

    def _extract_with_pdfplumber(
        self,
        file_path: str | Path | BinaryIO,
        result: ExtractionResult,
        extract_tables: bool,
        extract_text: bool,
        extract_dimensions: bool,
        extract_title_block: bool,
        pages: list[int] | None,
    ) -> None:
        """Extract using pdfplumber library."""
        with pdfplumber.open(file_path) as pdf:
            result.metadata["num_pages"] = len(pdf.pages)
            result.metadata["pdf_info"] = pdf.metadata or {}

            pages_to_process = pages if pages else range(1, len(pdf.pages) + 1)

            for page_num in pages_to_process:
                if page_num < 1 or page_num > len(pdf.pages):
                    result.warnings.append(f"Page {page_num} out of range")
                    continue

                page = pdf.pages[page_num - 1]  # 0-indexed

                # Extract tables
                if extract_tables:
                    tables = page.extract_tables()
                    for table_data in tables:
                        if table_data and len(table_data) > 0:
                            # First row as headers if it looks like headers
                            headers = table_data[0] if table_data else []
                            rows = table_data[1:] if len(table_data) > 1 else []

                            # Clean up None values
                            headers = [h or "" for h in headers]
                            rows = [[c or "" for c in row] for row in rows]

                            result.tables.append(
                                ExtractedTable(
                                    headers=headers,
                                    rows=rows,
                                    page=page_num,
                                )
                            )

                # Extract text
                if extract_text:
                    text = page.extract_text()
                    if text:
                        result.text_blocks.append(
                            ExtractedText(
                                text=text,
                                page=page_num,
                            )
                        )

                # Extract dimensions (pattern matching on text)
                if extract_dimensions:
                    text = page.extract_text() or ""
                    dims = self._extract_dimensions_from_text(text, page_num)
                    result.dimensions.extend(dims)

            # Extract title block from last page (common location)
            if extract_title_block and pdf.pages:
                last_page = pdf.pages[-1]
                text = last_page.extract_text() or ""
                result.title_block = self._extract_title_block(text)

    def _extract_with_pypdf(
        self,
        file_path: str | Path | BinaryIO,
        result: ExtractionResult,
        extract_text: bool,
        pages: list[int] | None,
    ) -> None:
        """Extract using pypdf library (text only)."""
        if isinstance(file_path, (str, Path)):
            reader = PdfReader(str(file_path))
        else:
            reader = PdfReader(file_path)

        result.metadata["num_pages"] = len(reader.pages)
        if reader.metadata:
            result.metadata["pdf_info"] = {k: str(v) for k, v in reader.metadata.items() if v}

        pages_to_process = pages if pages else range(1, len(reader.pages) + 1)

        for page_num in pages_to_process:
            if page_num < 1 or page_num > len(reader.pages):
                result.warnings.append(f"Page {page_num} out of range")
                continue

            page = reader.pages[page_num - 1]

            if extract_text:
                text = page.extract_text()
                if text:
                    result.text_blocks.append(
                        ExtractedText(
                            text=text,
                            page=page_num,
                        )
                    )

    def _extract_with_ocr(
        self,
        file_path: str | Path | BinaryIO,
        result: ExtractionResult,
        extract_tables: bool,
        extract_text: bool,
        pages: list[int] | None,
    ) -> None:
        """Extract using OCR for scanned PDFs."""
        if not self.ocr_extractor:
            result.warnings.append("OCR extractor not available")
            return

        try:
            # OCR requires a file path, not BinaryIO
            if not isinstance(file_path, (str, Path)):
                result.warnings.append("OCR extraction requires a file path, not a file object")
                return

            # Extract tables with OCR
            if extract_tables:
                ocr_tables = self.ocr_extractor.extract_tables_ocr(
                    file_path,
                    pages=pages,
                )
                # Merge with existing tables or replace if none found
                if ocr_tables:
                    if len(result.tables) == 0:
                        result.tables = ocr_tables
                        result.metadata["ocr_tables"] = True
                    else:
                        # Add OCR tables that weren't already found
                        result.tables.extend(ocr_tables)
                        result.metadata["ocr_tables_supplemental"] = True

            # Extract text with OCR
            if extract_text:
                ocr_text = self.ocr_extractor.extract_text(
                    file_path,
                    pages=pages,
                )
                # Merge with existing text or replace if none found
                if ocr_text:
                    if len(result.text_blocks) == 0:
                        result.text_blocks = ocr_text
                        result.metadata["ocr_text"] = True
                    else:
                        # Add OCR text blocks that weren't already found
                        result.text_blocks.extend(ocr_text)
                        result.metadata["ocr_text_supplemental"] = True

        except Exception as e:
            result.errors.append(f"OCR extraction failed: {str(e)}")

    def _extract_dimensions_from_text(self, text: str, page: int) -> list[ExtractedDimension]:
        """
        Extract dimension callouts from text using regex patterns.

        Patterns matched:
        - 10.5 mm, 10.5mm, 10.5 MM
        - 10.5 ±0.1 mm
        - 10.5 +0.2/-0.1 mm
        - Ø10.5 mm (diameter)
        - R5 mm (radius)
        """
        dimensions = []

        # Pattern: value ±tolerance unit
        symmetric_pattern = r'(\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)\s*(mm|cm|m|in|inch|inches|")?'
        for match in re.finditer(symmetric_pattern, text, re.IGNORECASE):
            dimensions.append(
                ExtractedDimension(
                    value=float(match.group(1)),
                    tolerance_plus=float(match.group(2)),
                    tolerance_minus=float(match.group(2)),
                    unit=self._normalize_unit(match.group(3)),
                    page=page,
                )
            )

        # Pattern: value +tol/-tol unit
        asymmetric_pattern = (
            r'(\d+\.?\d*)\s*\+(\d+\.?\d*)\s*/\s*-(\d+\.?\d*)\s*(mm|cm|m|in|inch|inches|")?'
        )
        for match in re.finditer(asymmetric_pattern, text, re.IGNORECASE):
            dimensions.append(
                ExtractedDimension(
                    value=float(match.group(1)),
                    tolerance_plus=float(match.group(2)),
                    tolerance_minus=float(match.group(3)),
                    unit=self._normalize_unit(match.group(4)),
                    page=page,
                )
            )

        # Pattern: Ø value (diameter)
        diameter_pattern = r'[ØⲪ]\s*(\d+\.?\d*)\s*(mm|cm|m|in|inch|inches|")?'
        for match in re.finditer(diameter_pattern, text, re.IGNORECASE):
            dimensions.append(
                ExtractedDimension(
                    value=float(match.group(1)),
                    unit=self._normalize_unit(match.group(2)),
                    dimension_type="diameter",
                    page=page,
                )
            )

        # Pattern: R value (radius)
        radius_pattern = r'R\s*(\d+\.?\d*)\s*(mm|cm|m|in|inch|inches|")?'
        for match in re.finditer(radius_pattern, text):
            dimensions.append(
                ExtractedDimension(
                    value=float(match.group(1)),
                    unit=self._normalize_unit(match.group(2)),
                    dimension_type="radius",
                    page=page,
                )
            )

        # Pattern: simple value with unit (less specific, lower confidence)
        simple_pattern = r"(\d+\.?\d*)\s*(mm|cm|m)\b"
        for match in re.finditer(simple_pattern, text, re.IGNORECASE):
            dim = ExtractedDimension(
                value=float(match.group(1)),
                unit=self._normalize_unit(match.group(2)),
                page=page,
                confidence=0.7,  # Lower confidence for simple matches
            )
            # Avoid duplicates
            if not any(d.value == dim.value and d.unit == dim.unit for d in dimensions):
                dimensions.append(dim)

        return dimensions

    def _normalize_unit(self, unit: str | None) -> str:
        """Normalize unit string."""
        if not unit:
            return "mm"
        unit = unit.lower().strip()
        unit_map = {
            '"': "in",
            "inch": "in",
            "inches": "in",
            "millimeter": "mm",
            "millimeters": "mm",
            "centimeter": "cm",
            "centimeters": "cm",
            "meter": "m",
            "meters": "m",
        }
        return unit_map.get(unit, unit)

    def _extract_title_block(self, text: str) -> ExtractedTitleBlock | None:
        """
        Extract title block information from text.

        Looks for common patterns like:
        - DRAWING NO: XXX
        - TITLE: XXX
        - REV: X
        - DATE: XX/XX/XXXX
        - SCALE: 1:1
        """
        title_block = ExtractedTitleBlock()
        found_any = False

        # Drawing number patterns
        patterns = {
            "drawing_number": [
                r"(?:DRAWING\s*(?:NO|NUMBER|#)?|DWG\s*(?:NO|#)?|PART\s*(?:NO|NUMBER|#)?)[:\s]*([A-Z0-9\-_]+)",
                r"(?:NO|NUMBER)[:\s]*([A-Z0-9\-_]{4,})",
            ],
            "title": [
                r"(?:TITLE|DESCRIPTION)[:\s]*([^\n]+)",
            ],
            "revision": [
                r"(?:REV|REVISION)[:\s]*([A-Z0-9]+)",
            ],
            "date": [
                r"(?:DATE)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
                r"(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",
            ],
            "scale": [
                r"(?:SCALE)[:\s]*([\d:]+|NTS|NONE)",
            ],
            "material": [
                r"(?:MATERIAL|MAT\'L)[:\s]*([^\n]+)",
            ],
            "author": [
                r"(?:DRAWN\s*BY|AUTHOR|DESIGNER)[:\s]*([^\n]+)",
            ],
            "sheet": [
                r"(?:SHEET|SHT)[:\s]*(\d+\s*(?:OF|/)\s*\d+|\d+)",
            ],
        }

        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        setattr(title_block, field, value)
                        found_any = True
                        break

        return title_block if found_any else None

    def get_page_count(self, file_path: str | Path | BinaryIO) -> int:
        """Get the number of pages in a PDF."""
        if PDFPLUMBER_AVAILABLE:
            with pdfplumber.open(file_path) as pdf:
                return len(pdf.pages)
        elif PYPDF_AVAILABLE:
            if isinstance(file_path, (str, Path)):
                reader = PdfReader(str(file_path))
            else:
                reader = PdfReader(file_path)
            return len(reader.pages)
        return 0

    def get_metadata(self, file_path: str | Path | BinaryIO) -> dict[str, Any]:
        """Get PDF metadata without full extraction."""
        if PDFPLUMBER_AVAILABLE:
            with pdfplumber.open(file_path) as pdf:
                return {
                    "num_pages": len(pdf.pages),
                    "info": pdf.metadata or {},
                }
        elif PYPDF_AVAILABLE:
            if isinstance(file_path, (str, Path)):
                reader = PdfReader(str(file_path))
            else:
                reader = PdfReader(file_path)
            return {
                "num_pages": len(reader.pages),
                "info": {k: str(v) for k, v in (reader.metadata or {}).items()},
            }
        return {}

    def is_scanned(
        self,
        file_path: str | Path | BinaryIO,
        sample_pages: int = 3,
        min_text_threshold: int = 50,
    ) -> bool:
        """
        Check if a PDF appears to be scanned (image-based).

        Samples the first few pages and checks for extractable text.
        PDFs with minimal text are likely scanned images requiring OCR.

        Args:
            file_path: Path to PDF file or file-like object
            sample_pages: Number of pages to sample (default 3)
            min_text_threshold: Minimum text length to consider page as text-based

        Returns:
            True if PDF appears to be scanned (minimal extractable text)
        """
        try:
            if PDFPLUMBER_AVAILABLE:
                with pdfplumber.open(file_path) as pdf:
                    pages_to_check = min(sample_pages, len(pdf.pages))
                    for i in range(pages_to_check):
                        text = pdf.pages[i].extract_text()
                        if text and len(text.strip()) > min_text_threshold:
                            return False  # Has extractable text
                    return True  # No significant text found, likely scanned
            elif PYPDF_AVAILABLE:
                if isinstance(file_path, (str, Path)):
                    reader = PdfReader(str(file_path))
                else:
                    reader = PdfReader(file_path)
                pages_to_check = min(sample_pages, len(reader.pages))
                for i in range(pages_to_check):
                    text = reader.pages[i].extract_text()
                    if text and len(text.strip()) > min_text_threshold:
                        return False  # Has extractable text
                return True  # No significant text found, likely scanned
            return False  # Can't determine, assume not scanned
        except Exception:
            return False  # On error, assume not scanned
