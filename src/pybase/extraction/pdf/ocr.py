"""OCR extraction for scanned PDF documents.

Uses Tesseract OCR for text extraction from image-based PDFs.
"""

from pathlib import Path
from typing import Any, BinaryIO
import tempfile
import os

from pybase.extraction.base import ExtractedText, ExtractedTable

# Optional dependencies
try:
    import pytesseract
    from PIL import Image

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    Image = None

try:
    import pdf2image

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    pdf2image = None


class OCRExtractor:
    """
    OCR extraction for scanned PDF documents.

    Uses Tesseract OCR to extract text from image-based PDFs.
    Requires tesseract to be installed on the system.

    Example:
        extractor = OCRExtractor()
        text_blocks = extractor.extract_text("scanned_document.pdf")
    """

    def __init__(
        self,
        tesseract_cmd: str | None = None,
        language: str = "eng",
    ):
        """
        Initialize OCR extractor.

        Args:
            tesseract_cmd: Path to tesseract executable (auto-detected if None)
            language: OCR language code (e.g., "eng", "deu", "fra")
        """
        if not TESSERACT_AVAILABLE:
            raise ImportError(
                "OCR extraction requires pytesseract and Pillow. "
                "Install with: pip install pytesseract Pillow"
            )

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("PDF OCR requires pdf2image. Install with: pip install pdf2image")

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        self.language = language
        self._verify_tesseract()

    def _verify_tesseract(self) -> None:
        """Verify tesseract is available."""
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            raise RuntimeError(
                "Tesseract not found. Please install tesseract-ocr:\n"
                "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
                "  Linux: sudo apt install tesseract-ocr\n"
                "  Mac: brew install tesseract"
            )

    def extract_text(
        self,
        file_path: str | Path,
        pages: list[int] | None = None,
        dpi: int = 300,
    ) -> list[ExtractedText]:
        """
        Extract text from scanned PDF using OCR.

        Args:
            file_path: Path to PDF file
            pages: Specific pages (1-indexed) or None for all
            dpi: Resolution for PDF to image conversion

        Returns:
            List of ExtractedText objects
        """
        file_path = Path(file_path)
        text_blocks = []

        # Convert PDF to images
        if pages:
            first_page = min(pages)
            last_page = max(pages)
        else:
            first_page = None
            last_page = None

        images = pdf2image.convert_from_path(
            file_path,
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
        )

        # Determine actual page numbers
        if pages:
            page_numbers = pages
        else:
            page_numbers = list(range(1, len(images) + 1))

        for img, page_num in zip(images, page_numbers):
            # Run OCR
            ocr_result = pytesseract.image_to_data(
                img,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )

            # Combine text with confidence
            full_text = pytesseract.image_to_string(img, lang=self.language)

            if full_text.strip():
                # Calculate average confidence
                confidences = [
                    c for c in ocr_result["conf"] if isinstance(c, (int, float)) and c > 0
                ]
                avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.5

                text_blocks.append(
                    ExtractedText(
                        text=full_text.strip(),
                        page=page_num,
                        confidence=avg_confidence,
                    )
                )

        return text_blocks

    def extract_text_with_boxes(
        self,
        file_path: str | Path,
        pages: list[int] | None = None,
        dpi: int = 300,
        min_confidence: float = 0.5,
    ) -> list[ExtractedText]:
        """
        Extract text with bounding box information.

        Args:
            file_path: Path to PDF file
            pages: Specific pages (1-indexed) or None for all
            dpi: Resolution for PDF to image conversion
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            List of ExtractedText objects with bbox
        """
        file_path = Path(file_path)
        text_blocks = []

        if pages:
            first_page = min(pages)
            last_page = max(pages)
        else:
            first_page = None
            last_page = None

        images = pdf2image.convert_from_path(
            file_path,
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
        )

        if pages:
            page_numbers = pages
        else:
            page_numbers = list(range(1, len(images) + 1))

        for img, page_num in zip(images, page_numbers):
            img_width, img_height = img.size

            # Get detailed OCR results
            ocr_data = pytesseract.image_to_data(
                img,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )

            # Group by block
            current_block = None
            current_text = []
            current_bbox = None
            current_conf = []

            for i in range(len(ocr_data["text"])):
                text = ocr_data["text"][i]
                conf = ocr_data["conf"][i]
                block_num = ocr_data["block_num"][i]

                if not text.strip():
                    continue

                # Confidence as 0-1
                if isinstance(conf, (int, float)):
                    conf = conf / 100
                else:
                    conf = 0.5

                if conf < min_confidence:
                    continue

                x = ocr_data["left"][i]
                y = ocr_data["top"][i]
                w = ocr_data["width"][i]
                h = ocr_data["height"][i]

                # Normalize bbox to 0-1 coordinates
                bbox = (
                    x / img_width,
                    y / img_height,
                    (x + w) / img_width,
                    (y + h) / img_height,
                )

                if block_num != current_block:
                    # Save previous block
                    if current_text:
                        avg_conf = sum(current_conf) / len(current_conf)
                        text_blocks.append(
                            ExtractedText(
                                text=" ".join(current_text),
                                page=page_num,
                                confidence=avg_conf,
                                bbox=current_bbox,
                            )
                        )

                    current_block = block_num
                    current_text = [text]
                    current_bbox = bbox
                    current_conf = [conf]
                else:
                    current_text.append(text)
                    current_conf.append(conf)
                    # Expand bbox
                    if current_bbox:
                        current_bbox = (
                            min(current_bbox[0], bbox[0]),
                            min(current_bbox[1], bbox[1]),
                            max(current_bbox[2], bbox[2]),
                            max(current_bbox[3], bbox[3]),
                        )

            # Save last block
            if current_text:
                avg_conf = sum(current_conf) / len(current_conf)
                text_blocks.append(
                    ExtractedText(
                        text=" ".join(current_text),
                        page=page_num,
                        confidence=avg_conf,
                        bbox=current_bbox,
                    )
                )

        return text_blocks

    def extract_tables_ocr(
        self,
        file_path: str | Path,
        pages: list[int] | None = None,
        dpi: int = 300,
    ) -> list[ExtractedTable]:
        """
        Extract tables from scanned PDF using OCR.

        This is a basic implementation that detects table-like structures.
        For better results on scanned tables, consider using specialized
        table detection libraries.

        Args:
            file_path: Path to PDF file
            pages: Specific pages (1-indexed) or None for all
            dpi: Resolution for conversion

        Returns:
            List of ExtractedTable objects
        """
        # Use tesseract's TSV output for structured data
        file_path = Path(file_path)
        tables = []

        if pages:
            first_page = min(pages)
            last_page = max(pages)
        else:
            first_page = None
            last_page = None

        images = pdf2image.convert_from_path(
            file_path,
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
        )

        if pages:
            page_numbers = pages
        else:
            page_numbers = list(range(1, len(images) + 1))

        for img, page_num in zip(images, page_numbers):
            # Get TSV output
            tsv_data = pytesseract.image_to_data(
                img,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )

            # Group text by line (par_num, line_num)
            lines: dict[tuple[int, int, int], list[str]] = {}

            for i in range(len(tsv_data["text"])):
                text = tsv_data["text"][i]
                if not text.strip():
                    continue

                block = tsv_data["block_num"][i]
                par = tsv_data["par_num"][i]
                line = tsv_data["line_num"][i]

                key = (block, par, line)
                if key not in lines:
                    lines[key] = []
                lines[key].append(text.strip())

            # Detect table-like structures (multiple columns per line)
            # Group consecutive lines with similar column counts
            sorted_lines = sorted(lines.items())

            table_rows = []
            for key, words in sorted_lines:
                if len(words) >= 2:  # At least 2 columns
                    table_rows.append(words)

            # If we have multiple rows with consistent column count, it's a table
            if len(table_rows) >= 2:
                col_counts = [len(row) for row in table_rows]
                most_common_cols = max(set(col_counts), key=col_counts.count)

                # Filter to rows with the most common column count
                filtered_rows = [row for row in table_rows if len(row) == most_common_cols]

                if len(filtered_rows) >= 2:
                    # First row as headers
                    headers = filtered_rows[0]
                    rows = filtered_rows[1:]

                    tables.append(
                        ExtractedTable(
                            headers=headers,
                            rows=rows,
                            page=page_num,
                            confidence=0.6,  # Lower confidence for OCR tables
                        )
                    )

        return tables

    def is_scanned_pdf(self, file_path: str | Path) -> bool:
        """
        Check if a PDF appears to be scanned (image-based).

        Args:
            file_path: Path to PDF file

        Returns:
            True if PDF appears to be scanned
        """
        try:
            # Try to extract text with pdfplumber
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:3]:  # Check first 3 pages
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:
                        return False  # Has extractable text
            return True  # No text found, likely scanned
        except ImportError:
            # Can't determine, assume not scanned
            return False
        except Exception:
            return False
