# Phase 3: CAD/PDF Extraction System
## PyBase Master Plan - Weeks 11-18 (PRIORITY PHASE)

**Duration:** 8 Weeks  
**Status:** ❌ NOT STARTED (January 2026)  
**Team Focus:** Extraction Engineer (Dedicated) + Backend Support  
**Dependencies:** Phase 2 Complete (Field Types System)  
**Priority:** HIGHEST - Core differentiating feature

---

## 📋 Phase Status Overview

**Implementation Status:** ❌ Planned  
**Dependencies:** 🔄 Phase 2 partially completed

### Prerequisites for Starting
- [ ] Complete engineering field types implementation
- [ ] Field validation system
- [ ] File upload API with MinIO storage
- [ ] Background task processing (Celery)

---

## Phase Objectives

1. Build comprehensive PDF table extraction pipeline
2. Implement DXF/DWG parsing for AutoCAD files
3. Add IFC/BIM support for Revit data
4. Create STEP/STP parser for 3D CAD metadata
5. Integrate AI-powered engineering drawing extraction (Werk24)
6. Build custom ML model fallback (YOLOv11 + Donut)
7. Create unified extraction API with preview/review workflow

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTRACTION API GATEWAY                               │
│                    POST /api/v1/extract/{file_type}                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FILE TYPE ROUTER                                     │
│  Detects file type by extension/magic bytes and routes to appropriate       │
│  extractor. Supports: PDF, DXF, DWG, IFC, STEP, STP, IGES, Images          │
└─────────────────────────────────────────────────────────────────────────────┘
          │              │              │              │              │
          ▼              ▼              ▼              ▼              ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ PDF Extractor │ │ DXF Extractor │ │ IFC Extractor │ │STEP Extractor │ │Image Extractor│
│               │ │               │ │               │ │               │ │               │
│ - pdfplumber  │ │ - ezdxf       │ │ - ifcopenshell│ │ - cadquery    │ │ - pytesseract │
│ - tabula-py   │ │ - Title blocks│ │ - Properties  │ │ - pythonocc   │ │ - OCR pipeline│
│ - PyMuPDF     │ │ - Attributes  │ │ - Materials   │ │ - Geometry    │ │               │
│ - Werk24 API  │ │ - Dimensions  │ │ - Quantities  │ │ - Metadata    │ │               │
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
          │              │              │              │              │
          └──────────────┴──────────────┴──────────────┴──────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EXTRACTION RESULT NORMALIZER                             │
│  Converts all extraction outputs to unified ExtractionResult format         │
│  with confidence scores, field mappings, and preview data                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FIELD TYPE MAPPER                                     │
│  Maps extracted data to PyBase field types:                                 │
│  - Auto-detect: text, number, date, dimension, GD&T, thread, material      │
│  - User can override mappings before import                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMPORT ENGINE                                        │
│  Creates PyBase table with detected schema and imports records              │
│  Stores original file as attachment, maintains extraction metadata          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Week-by-Week Breakdown

### Week 11: Extraction Infrastructure & PDF Basics

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 3.11.1 | Create extraction module structure | Critical | 4h | Phase 2 |
| 3.11.2 | Define ExtractionResult data model | Critical | 3h | 3.11.1 |
| 3.11.3 | Implement file type detection | Critical | 3h | 3.11.1 |
| 3.11.4 | Create base Extractor abstract class | Critical | 3h | 3.11.2 |
| 3.11.5 | Implement PDFExtractor with pdfplumber | Critical | 6h | 3.11.4 |
| 3.11.6 | Add tabula-py integration for complex tables | High | 4h | 3.11.5 |
| 3.11.7 | Implement text extraction with PyMuPDF | High | 4h | 3.11.5 |
| 3.11.8 | Create extraction Celery task | High | 3h | 3.11.5 |
| 3.11.9 | Build extraction API endpoint | Critical | 4h | 3.11.8 |
| 3.11.10 | Write PDF extraction tests | Critical | 4h | 3.11.* |

#### Deliverables

- [ ] `POST /api/v1/extract/pdf` - Upload and extract PDF
- [ ] `GET /api/v1/extraction/{id}` - Get extraction results
- [ ] `POST /api/v1/extraction/{id}/import` - Import to table
- [ ] PDF table extraction with confidence scores
- [ ] Text block extraction with positions
- [ ] Hybrid extraction (pdfplumber + tabula)

#### Core Data Models

**app/core/extraction/models.py**
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime


class FileType(str, Enum):
    """Supported file types for extraction"""
    PDF = "pdf"
    DXF = "dxf"
    DWG = "dwg"
    IFC = "ifc"
    STEP = "step"
    STP = "stp"
    IGES = "iges"
    IMAGE = "image"


class ExtractionMethod(str, Enum):
    """Extraction methods/engines"""
    PDFPLUMBER = "pdfplumber"
    TABULA = "tabula"
    PYMUPDF = "pymupdf"
    OCR = "ocr"
    WERK24 = "werk24"
    EZDXF = "ezdxf"
    IFCOPENSHELL = "ifcopenshell"
    CADQUERY = "cadquery"
    YOLO_DONUT = "yolo_donut"
    HYBRID = "hybrid"


class ExtractionStatus(str, Enum):
    """Status of extraction job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW = "review"  # Awaiting user review


@dataclass
class BoundingBox:
    """Bounding box for extracted elements"""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int = 1
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class ExtractedCell:
    """Single cell in extracted table"""
    value: Any
    row: int
    col: int
    bbox: Optional[BoundingBox] = None
    confidence: float = 1.0
    inferred_type: Optional[str] = None  # text, number, date, etc.


@dataclass
class ExtractedTable:
    """Extracted table with metadata"""
    id: str = field(default_factory=lambda: str(uuid4()))
    page_number: int = 1
    table_index: int = 0
    headers: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    cells: List[ExtractedCell] = field(default_factory=list)
    confidence: float = 0.0
    bbox: Optional[BoundingBox] = None
    extraction_method: ExtractionMethod = ExtractionMethod.PDFPLUMBER
    
    @property
    def row_count(self) -> int:
        return len(self.rows)
    
    @property
    def column_count(self) -> int:
        return len(self.headers)


@dataclass
class ExtractedText:
    """Extracted text block"""
    id: str = field(default_factory=lambda: str(uuid4()))
    page_number: int = 1
    text: str = ""
    bbox: Optional[BoundingBox] = None
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    is_title: bool = False


@dataclass
class ExtractedDimension:
    """Extracted engineering dimension"""
    id: str = field(default_factory=lambda: str(uuid4()))
    nominal_value: float = 0.0
    tolerance_upper: Optional[float] = None
    tolerance_lower: Optional[float] = None
    tolerance_type: str = "symmetric"
    unit: str = "mm"
    fit_designation: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    confidence: float = 0.0
    raw_text: str = ""


@dataclass
class ExtractedGDT:
    """Extracted GD&T feature control frame"""
    id: str = field(default_factory=lambda: str(uuid4()))
    symbol: str = ""
    tolerance_value: float = 0.0
    datum_references: List[str] = field(default_factory=list)
    material_modifier: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    confidence: float = 0.0
    raw_text: str = ""


@dataclass
class ExtractedThread:
    """Extracted thread specification"""
    id: str = field(default_factory=lambda: str(uuid4()))
    designation: str = ""
    thread_type: str = "metric"
    major_diameter: Optional[float] = None
    pitch: Optional[float] = None
    thread_class: Optional[str] = None
    internal: bool = False
    bbox: Optional[BoundingBox] = None
    confidence: float = 0.0


@dataclass
class ExtractedTitleBlock:
    """Extracted title block data"""
    drawing_number: Optional[str] = None
    title: Optional[str] = None
    revision: Optional[str] = None
    material: Optional[str] = None
    scale: Optional[str] = None
    date: Optional[str] = None
    author: Optional[str] = None
    approver: Optional[str] = None
    company: Optional[str] = None
    sheet: Optional[str] = None
    tolerance_note: Optional[str] = None
    custom_fields: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class ExtractedBOMItem:
    """Extracted Bill of Materials item"""
    item_number: int = 0
    part_number: str = ""
    description: str = ""
    quantity: int = 1
    material: Optional[str] = None
    weight: Optional[float] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedBOM:
    """Extracted Bill of Materials"""
    items: List[ExtractedBOMItem] = field(default_factory=list)
    table_id: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ExtractionResult:
    """Complete extraction result"""
    id: str = field(default_factory=lambda: str(uuid4()))
    filename: str = ""
    file_type: FileType = FileType.PDF
    page_count: int = 0
    status: ExtractionStatus = ExtractionStatus.PENDING
    
    # Extracted data
    tables: List[ExtractedTable] = field(default_factory=list)
    text_blocks: List[ExtractedText] = field(default_factory=list)
    dimensions: List[ExtractedDimension] = field(default_factory=list)
    gdt_features: List[ExtractedGDT] = field(default_factory=list)
    threads: List[ExtractedThread] = field(default_factory=list)
    title_block: Optional[ExtractedTitleBlock] = None
    bom: Optional[ExtractedBOM] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    extraction_methods: List[ExtractionMethod] = field(default_factory=list)
    overall_confidence: float = 0.0
    processing_time_ms: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type.value,
            "page_count": self.page_count,
            "status": self.status.value,
            "tables": [
                {
                    "id": t.id,
                    "page": t.page_number,
                    "headers": t.headers,
                    "row_count": t.row_count,
                    "confidence": t.confidence,
                }
                for t in self.tables
            ],
            "text_blocks": len(self.text_blocks),
            "dimensions": len(self.dimensions),
            "gdt_features": len(self.gdt_features),
            "threads": len(self.threads),
            "has_title_block": self.title_block is not None,
            "has_bom": self.bom is not None,
            "overall_confidence": self.overall_confidence,
            "processing_time_ms": self.processing_time_ms,
            "errors": self.errors,
            "warnings": self.warnings,
        }
```

---

### Week 12: Advanced PDF & Engineering Drawing Extraction

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 3.12.1 | Implement OCR pipeline with pytesseract | Critical | 6h | 3.11.* |
| 3.12.2 | Integrate Werk24 API client | Critical | 6h | 3.11.* |
| 3.12.3 | Implement dimension extraction | Critical | 6h | 3.12.2 |
| 3.12.4 | Implement GD&T extraction | Critical | 6h | 3.12.2 |
| 3.12.5 | Implement thread specification extraction | High | 4h | 3.12.2 |
| 3.12.6 | Implement surface finish extraction | High | 4h | 3.12.2 |
| 3.12.7 | Implement title block detection | High | 4h | 3.12.2 |
| 3.12.8 | Implement BOM table detection | High | 4h | 3.11.5 |
| 3.12.9 | Create Werk24 fallback for unavailable API | Medium | 4h | 3.12.* |
| 3.12.10 | Write engineering extraction tests | Critical | 4h | 3.12.* |

#### Deliverables

- [ ] OCR pipeline for scanned documents
- [ ] Werk24 integration for engineering drawings
- [ ] Dimension extraction with tolerances
- [ ] GD&T feature control frame extraction
- [ ] Title block automatic detection
- [ ] BOM extraction from drawings

#### Werk24 Integration

**app/core/extraction/werk24_client.py**
```python
import asyncio
from typing import List, Optional
from dataclasses import dataclass
import httpx

from app.config import settings
from app.core.extraction.models import (
    ExtractedDimension,
    ExtractedGDT,
    ExtractedThread,
    ExtractedTitleBlock,
    ExtractionMethod,
)


@dataclass
class Werk24Config:
    """Werk24 API configuration"""
    api_key: str
    endpoint: str = "https://api.werk24.io/v2"
    timeout: int = 120


class Werk24Client:
    """Client for Werk24 engineering drawing extraction API"""
    
    def __init__(self, config: Optional[Werk24Config] = None):
        self.config = config or Werk24Config(
            api_key=settings.werk24_api_key,
        )
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/octet-stream",
            },
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def extract_drawing(
        self, 
        pdf_bytes: bytes,
        extract_metadata: bool = True,
        extract_dimensions: bool = True,
        extract_gdt: bool = True,
        extract_threads: bool = True,
        extract_surface_finish: bool = True,
    ) -> dict:
        """
        Extract engineering data from PDF drawing using Werk24
        
        Returns structured JSON with all extracted features
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with.")
        
        # Build request options
        asks = []
        if extract_metadata:
            asks.append("AskMetaData")
        if extract_dimensions:
            asks.append("AskMeasures")
        if extract_gdt:
            asks.append("AskGDTs")
        if extract_threads:
            asks.append("AskThreads")
        if extract_surface_finish:
            asks.append("AskSurfaceRoughnesses")
        
        # Submit extraction job
        response = await self._client.post(
            f"{self.config.endpoint}/extract",
            content=pdf_bytes,
            params={"asks": ",".join(asks)},
        )
        response.raise_for_status()
        
        job_id = response.json()["job_id"]
        
        # Poll for results
        result = await self._poll_job(job_id)
        
        return result
    
    async def _poll_job(self, job_id: str, max_wait: int = 120) -> dict:
        """Poll for job completion"""
        for _ in range(max_wait):
            response = await self._client.get(
                f"{self.config.endpoint}/jobs/{job_id}"
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data["status"] == "completed":
                return data["result"]
            elif data["status"] == "failed":
                raise Exception(f"Werk24 extraction failed: {data.get('error')}")
            
            await asyncio.sleep(1)
        
        raise TimeoutError("Werk24 extraction timed out")
    
    def parse_dimensions(self, werk24_result: dict) -> List[ExtractedDimension]:
        """Parse Werk24 dimension results to our format"""
        dimensions = []
        
        for measure in werk24_result.get("measures", []):
            dim = ExtractedDimension(
                nominal_value=measure.get("nominal_value", 0),
                tolerance_upper=measure.get("tolerance_upper"),
                tolerance_lower=measure.get("tolerance_lower"),
                tolerance_type=self._map_tolerance_type(measure),
                unit=measure.get("unit", "mm"),
                fit_designation=measure.get("fit"),
                confidence=measure.get("confidence", 0.9),
                raw_text=measure.get("raw_text", ""),
            )
            dimensions.append(dim)
        
        return dimensions
    
    def parse_gdt(self, werk24_result: dict) -> List[ExtractedGDT]:
        """Parse Werk24 GD&T results to our format"""
        gdt_features = []
        
        for gdt in werk24_result.get("gdts", []):
            feature = ExtractedGDT(
                symbol=self._map_gdt_symbol(gdt.get("type")),
                tolerance_value=gdt.get("tolerance", 0),
                datum_references=gdt.get("datums", []),
                material_modifier=gdt.get("modifier"),
                confidence=gdt.get("confidence", 0.9),
                raw_text=gdt.get("raw_text", ""),
            )
            gdt_features.append(feature)
        
        return gdt_features
    
    def parse_threads(self, werk24_result: dict) -> List[ExtractedThread]:
        """Parse Werk24 thread results to our format"""
        threads = []
        
        for thread in werk24_result.get("threads", []):
            t = ExtractedThread(
                designation=thread.get("designation", ""),
                thread_type=self._map_thread_type(thread),
                major_diameter=thread.get("major_diameter"),
                pitch=thread.get("pitch"),
                thread_class=thread.get("class"),
                internal=thread.get("internal", False),
                confidence=thread.get("confidence", 0.9),
            )
            threads.append(t)
        
        return threads
    
    def parse_title_block(self, werk24_result: dict) -> Optional[ExtractedTitleBlock]:
        """Parse Werk24 title block to our format"""
        meta = werk24_result.get("metadata", {})
        
        if not meta:
            return None
        
        return ExtractedTitleBlock(
            drawing_number=meta.get("drawing_number"),
            title=meta.get("title"),
            revision=meta.get("revision"),
            material=meta.get("material"),
            scale=meta.get("scale"),
            date=meta.get("date"),
            author=meta.get("drawn_by"),
            approver=meta.get("approved_by"),
            company=meta.get("company"),
            sheet=meta.get("sheet"),
            tolerance_note=meta.get("general_tolerance"),
            confidence=meta.get("confidence", 0.9),
        )
    
    def _map_tolerance_type(self, measure: dict) -> str:
        """Map Werk24 tolerance type to our format"""
        if measure.get("fit"):
            return "fit"
        upper = measure.get("tolerance_upper")
        lower = measure.get("tolerance_lower")
        if upper and lower and upper == abs(lower):
            return "symmetric"
        return "asymmetric"
    
    def _map_gdt_symbol(self, werk24_type: str) -> str:
        """Map Werk24 GD&T type to our symbol name"""
        mapping = {
            "POSITION": "position",
            "CONCENTRICITY": "concentricity",
            "SYMMETRY": "symmetry",
            "PERPENDICULARITY": "perpendicularity",
            "ANGULARITY": "angularity",
            "PARALLELISM": "parallelism",
            "FLATNESS": "flatness",
            "STRAIGHTNESS": "straightness",
            "CIRCULARITY": "circularity",
            "CYLINDRICITY": "cylindricity",
            "PROFILE_OF_LINE": "profile_line",
            "PROFILE_OF_SURFACE": "profile_surface",
            "CIRCULAR_RUNOUT": "circular_runout",
            "TOTAL_RUNOUT": "total_runout",
        }
        return mapping.get(werk24_type, werk24_type.lower())
    
    def _map_thread_type(self, thread: dict) -> str:
        """Map Werk24 thread type to our format"""
        designation = thread.get("designation", "")
        if designation.startswith("M"):
            return "metric"
        elif "UNC" in designation or "UNF" in designation:
            return "imperial_unified"
        elif "NPT" in designation or "BSP" in designation:
            return "imperial_pipe"
        return "metric"
```

---

### Week 13: DXF/DWG Extraction

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 3.13.1 | Create DXFExtractor base class | Critical | 4h | 3.11.4 |
| 3.13.2 | Implement ezdxf document loading | Critical | 3h | 3.13.1 |
| 3.13.3 | Extract entity layers and organization | Critical | 4h | 3.13.2 |
| 3.13.4 | Extract text entities (TEXT, MTEXT) | Critical | 4h | 3.13.2 |
| 3.13.5 | Extract dimension entities | Critical | 6h | 3.13.2 |
| 3.13.6 | Extract block references and attributes | Critical | 6h | 3.13.2 |
| 3.13.7 | Implement title block detection from blocks | High | 4h | 3.13.6 |
| 3.13.8 | Extract geometric entities (lines, circles, arcs) | Medium | 4h | 3.13.2 |
| 3.13.9 | Implement DWG support via ODA converter | Medium | 6h | 3.13.* |
| 3.13.10 | Write DXF extraction tests | Critical | 4h | 3.13.* |

#### Deliverables

- [ ] `POST /api/v1/extract/dxf` - Extract DXF files
- [ ] Layer extraction with filtering
- [ ] Text entity extraction
- [ ] Dimension entity extraction with values
- [ ] Block attribute extraction
- [ ] Title block from standard blocks
- [ ] DWG support (via conversion)

#### DXF Extractor Implementation

**app/core/extraction/dxf_extractor.py**
```python
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import re

import ezdxf
from ezdxf.document import Drawing
from ezdxf.entities import DXFEntity, Text, MText, Dimension, Insert

from app.core.extraction.base import BaseExtractor
from app.core.extraction.models import (
    ExtractionResult,
    ExtractionStatus,
    ExtractionMethod,
    ExtractedTable,
    ExtractedText,
    ExtractedDimension,
    ExtractedTitleBlock,
    BoundingBox,
    FileType,
)


class DXFExtractor(BaseExtractor):
    """Extractor for DXF/DWG files using ezdxf"""
    
    SUPPORTED_EXTENSIONS = {".dxf", ".DXF"}
    
    # Common title block attribute names
    TITLE_BLOCK_ATTRIBUTES = {
        "drawing_number": ["DRAWING_NO", "DWG_NO", "DRWG_NUM", "DRAWING_NUMBER"],
        "title": ["TITLE", "DRAWING_TITLE", "DWG_TITLE"],
        "revision": ["REV", "REVISION", "REV_NO"],
        "material": ["MATERIAL", "MAT", "MATL"],
        "scale": ["SCALE", "DWG_SCALE"],
        "date": ["DATE", "DWG_DATE", "DRAWN_DATE"],
        "author": ["DRAWN_BY", "DRAFTER", "AUTHOR"],
        "approver": ["APPROVED_BY", "CHECKER", "APPROVED"],
        "company": ["COMPANY", "COMPANY_NAME"],
        "sheet": ["SHEET", "SHEET_NO"],
    }
    
    def __init__(self, source: Union[str, Path, bytes]):
        super().__init__(source)
        self.doc: Optional[Drawing] = None
    
    def _load_document(self) -> Drawing:
        """Load DXF document"""
        if isinstance(self.source, bytes):
            stream = io.BytesIO(self.source)
            return ezdxf.read(stream)
        return ezdxf.readfile(str(self.source))
    
    def extract(self) -> ExtractionResult:
        """Extract all data from DXF file"""
        result = ExtractionResult(
            filename=self.filename,
            file_type=FileType.DXF,
            status=ExtractionStatus.PROCESSING,
        )
        
        try:
            self.doc = self._load_document()
            
            # Get modelspace
            msp = self.doc.modelspace()
            
            # Extract various entity types
            result.text_blocks = self._extract_text_entities(msp)
            result.dimensions = self._extract_dimensions(msp)
            result.title_block = self._extract_title_block(msp)
            result.tables = self._extract_tables_from_text(result.text_blocks)
            
            # Calculate overall confidence
            result.overall_confidence = self._calculate_confidence(result)
            result.extraction_methods = [ExtractionMethod.EZDXF]
            result.status = ExtractionStatus.COMPLETED
            result.page_count = 1  # DXF is single "page"
            
            # Add metadata
            result.metadata = {
                "dxf_version": self.doc.dxfversion,
                "layers": [layer.dxf.name for layer in self.doc.layers],
                "block_count": len(list(self.doc.blocks)),
                "entity_count": len(list(msp)),
            }
            
        except Exception as e:
            result.status = ExtractionStatus.FAILED
            result.errors.append(str(e))
        
        return result
    
    def _extract_text_entities(self, msp) -> List[ExtractedText]:
        """Extract all text entities from modelspace"""
        texts = []
        
        # Extract TEXT entities
        for text in msp.query("TEXT"):
            texts.append(ExtractedText(
                page_number=1,
                text=text.dxf.text,
                bbox=self._get_text_bbox(text),
                font_size=text.dxf.height,
                is_title=text.dxf.height > 5,  # Heuristic for title detection
            ))
        
        # Extract MTEXT entities (multi-line text)
        for mtext in msp.query("MTEXT"):
            texts.append(ExtractedText(
                page_number=1,
                text=self._clean_mtext(mtext.text),
                bbox=self._get_mtext_bbox(mtext),
                font_size=mtext.dxf.char_height,
            ))
        
        return texts
    
    def _extract_dimensions(self, msp) -> List[ExtractedDimension]:
        """Extract dimension entities"""
        dimensions = []
        
        for dim in msp.query("DIMENSION"):
            try:
                # Get dimension measurement
                measurement = dim.get_measurement()
                
                # Parse text override for tolerances
                dim_text = dim.dxf.text or ""
                tolerance_info = self._parse_dimension_text(dim_text, measurement)
                
                dimensions.append(ExtractedDimension(
                    nominal_value=tolerance_info["nominal"],
                    tolerance_upper=tolerance_info.get("upper"),
                    tolerance_lower=tolerance_info.get("lower"),
                    tolerance_type=tolerance_info.get("type", "symmetric"),
                    unit="mm",  # Default, could be read from drawing settings
                    confidence=0.95 if not dim_text else 0.85,
                    raw_text=dim_text or str(measurement),
                ))
            except Exception:
                continue
        
        return dimensions
    
    def _extract_title_block(self, msp) -> Optional[ExtractedTitleBlock]:
        """Extract title block from block references"""
        title_data = {}
        
        # Look for INSERT entities (block references)
        for insert in msp.query("INSERT"):
            block_name = insert.dxf.name.upper()
            
            # Check if this looks like a title block
            if any(tb in block_name for tb in ["TITLE", "BORDER", "FRAME", "A1", "A2", "A3", "A4"]):
                # Extract attributes from this block
                for attrib in insert.attribs:
                    tag = attrib.dxf.tag.upper()
                    value = attrib.dxf.text.strip()
                    
                    if not value:
                        continue
                    
                    # Map to our standard fields
                    for field_name, tags in self.TITLE_BLOCK_ATTRIBUTES.items():
                        if tag in tags:
                            title_data[field_name] = value
                            break
                    else:
                        # Store as custom field if not recognized
                        if "custom_fields" not in title_data:
                            title_data["custom_fields"] = {}
                        title_data["custom_fields"][tag] = value
        
        if not title_data:
            return None
        
        return ExtractedTitleBlock(
            drawing_number=title_data.get("drawing_number"),
            title=title_data.get("title"),
            revision=title_data.get("revision"),
            material=title_data.get("material"),
            scale=title_data.get("scale"),
            date=title_data.get("date"),
            author=title_data.get("author"),
            approver=title_data.get("approver"),
            company=title_data.get("company"),
            sheet=title_data.get("sheet"),
            custom_fields=title_data.get("custom_fields", {}),
            confidence=0.9,
        )
    
    def _extract_tables_from_text(self, texts: List[ExtractedText]) -> List[ExtractedTable]:
        """Try to detect tabular data from text positions"""
        # Group texts by approximate Y position (rows)
        # This is a simplified approach - production would need better table detection
        tables = []
        
        # Sort by position if available
        positioned_texts = [t for t in texts if t.bbox]
        if not positioned_texts:
            return tables
        
        # Group by Y coordinate (with tolerance)
        rows: Dict[int, List[ExtractedText]] = {}
        for text in positioned_texts:
            y_key = int(text.bbox.y0 / 10) * 10  # Round to nearest 10
            if y_key not in rows:
                rows[y_key] = []
            rows[y_key].append(text)
        
        # Find rows with multiple items (potential table rows)
        potential_table_rows = {y: texts for y, texts in rows.items() if len(texts) >= 2}
        
        if len(potential_table_rows) >= 3:
            # Sort rows by Y and columns by X
            sorted_rows = []
            for y in sorted(potential_table_rows.keys(), reverse=True):
                row_texts = sorted(potential_table_rows[y], key=lambda t: t.bbox.x0)
                sorted_rows.append([t.text for t in row_texts])
            
            if sorted_rows:
                tables.append(ExtractedTable(
                    page_number=1,
                    table_index=0,
                    headers=sorted_rows[0] if sorted_rows else [],
                    rows=sorted_rows[1:] if len(sorted_rows) > 1 else [],
                    confidence=0.6,  # Lower confidence for detected tables
                    extraction_method=ExtractionMethod.EZDXF,
                ))
        
        return tables
    
    def _parse_dimension_text(self, text: str, measurement: float) -> Dict[str, Any]:
        """Parse dimension text for tolerances"""
        result = {"nominal": measurement}
        
        if not text or text == "<>":
            return result
        
        # Pattern for symmetric tolerance: 50 ±0.1
        sym_match = re.search(r'([\d.]+)\s*[±]\s*([\d.]+)', text)
        if sym_match:
            result["nominal"] = float(sym_match.group(1))
            tol = float(sym_match.group(2))
            result["upper"] = tol
            result["lower"] = -tol
            result["type"] = "symmetric"
            return result
        
        # Pattern for asymmetric tolerance: 50 +0.1/-0.05
        asym_match = re.search(r'([\d.]+)\s*\+\s*([\d.]+)\s*/\s*-\s*([\d.]+)', text)
        if asym_match:
            result["nominal"] = float(asym_match.group(1))
            result["upper"] = float(asym_match.group(2))
            result["lower"] = -float(asym_match.group(3))
            result["type"] = "asymmetric"
            return result
        
        # Pattern for fit: 50 H7
        fit_match = re.search(r'([\d.]+)\s*([A-Za-z]\d+)', text)
        if fit_match:
            result["nominal"] = float(fit_match.group(1))
            result["fit"] = fit_match.group(2)
            result["type"] = "fit"
            return result
        
        return result
    
    def _get_text_bbox(self, text: Text) -> BoundingBox:
        """Get bounding box for TEXT entity"""
        insert = text.dxf.insert
        height = text.dxf.height
        width = len(text.dxf.text) * height * 0.6  # Approximate
        
        return BoundingBox(
            x0=insert.x,
            y0=insert.y,
            x1=insert.x + width,
            y1=insert.y + height,
            page=1,
        )
    
    def _get_mtext_bbox(self, mtext: MText) -> BoundingBox:
        """Get bounding box for MTEXT entity"""
        insert = mtext.dxf.insert
        height = mtext.dxf.char_height
        width = mtext.dxf.get("width", 100)
        
        return BoundingBox(
            x0=insert.x,
            y0=insert.y,
            x1=insert.x + width,
            y1=insert.y + height,
            page=1,
        )
    
    def _clean_mtext(self, text: str) -> str:
        """Clean MTEXT formatting codes"""
        # Remove common MTEXT formatting codes
        text = re.sub(r'\\[A-Za-z][^;]*;', '', text)
        text = re.sub(r'\{|\}', '', text)
        text = re.sub(r'\\P', '\n', text)
        return text.strip()
    
    def _calculate_confidence(self, result: ExtractionResult) -> float:
        """Calculate overall extraction confidence"""
        scores = []
        
        if result.dimensions:
            scores.append(sum(d.confidence for d in result.dimensions) / len(result.dimensions))
        
        if result.title_block:
            scores.append(result.title_block.confidence)
        
        if result.text_blocks:
            scores.append(0.9)  # Text extraction is generally reliable
        
        return sum(scores) / len(scores) if scores else 0.5
```

---

### Week 14: IFC/BIM Extraction

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 3.14.1 | Create IFCExtractor base class | Critical | 4h | 3.11.4 |
| 3.14.2 | Implement ifcopenshell document loading | Critical | 3h | 3.14.1 |
| 3.14.3 | Extract building elements by type | Critical | 6h | 3.14.2 |
| 3.14.4 | Extract element properties (Psets) | Critical | 6h | 3.14.2 |
| 3.14.5 | Extract quantities (Qtos) | High | 4h | 3.14.2 |
| 3.14.6 | Extract materials and layers | High | 4h | 3.14.2 |
| 3.14.7 | Extract spatial hierarchy | High | 4h | 3.14.2 |
| 3.14.8 | Extract project metadata | Medium | 3h | 3.14.2 |
| 3.14.9 | Create IFC-to-table mapping | Critical | 6h | 3.14.* |
| 3.14.10 | Write IFC extraction tests | Critical | 4h | 3.14.* |

#### Deliverables

- [ ] `POST /api/v1/extract/ifc` - Extract IFC files
- [ ] Building element extraction (walls, doors, windows, etc.)
- [ ] Property set extraction
- [ ] Quantity extraction
- [ ] Material extraction
- [ ] Spatial hierarchy (project → site → building → storey)

#### IFC Extractor Implementation

**app/core/extraction/ifc_extractor.py**
```python
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from collections import defaultdict

import ifcopenshell
import ifcopenshell.util.element as ifc_util
import ifcopenshell.util.unit as ifc_unit

from app.core.extraction.base import BaseExtractor
from app.core.extraction.models import (
    ExtractionResult,
    ExtractionStatus,
    ExtractionMethod,
    ExtractedTable,
    FileType,
)


class IFCExtractor(BaseExtractor):
    """Extractor for IFC/BIM files using ifcopenshell"""
    
    SUPPORTED_EXTENSIONS = {".ifc", ".IFC"}
    
    # IFC element types to extract
    ELEMENT_TYPES = [
        "IfcWall", "IfcWallStandardCase",
        "IfcDoor", "IfcWindow",
        "IfcSlab", "IfcRoof",
        "IfcColumn", "IfcBeam",
        "IfcStair", "IfcRamp",
        "IfcCurtainWall",
        "IfcPlate", "IfcMember",
        "IfcFurnishingElement",
        "IfcBuildingElementProxy",
        "IfcSpace",
        "IfcPipeSegment", "IfcDuctSegment",
        "IfcCableCarrierSegment",
    ]
    
    def __init__(self, source: Union[str, Path, bytes]):
        super().__init__(source)
        self.model: Optional[ifcopenshell.file] = None
    
    def _load_document(self) -> ifcopenshell.file:
        """Load IFC file"""
        if isinstance(self.source, bytes):
            # ifcopenshell needs a file path, so write to temp
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
                f.write(self.source)
                return ifcopenshell.open(f.name)
        return ifcopenshell.open(str(self.source))
    
    def extract(self) -> ExtractionResult:
        """Extract all data from IFC file"""
        result = ExtractionResult(
            filename=self.filename,
            file_type=FileType.IFC,
            status=ExtractionStatus.PROCESSING,
        )
        
        try:
            self.model = self._load_document()
            
            # Extract project metadata
            result.metadata = self._extract_project_metadata()
            
            # Extract elements by type as tables
            result.tables = self._extract_elements_as_tables()
            
            # Extract spatial hierarchy
            spatial_table = self._extract_spatial_hierarchy()
            if spatial_table:
                result.tables.append(spatial_table)
            
            # Extract materials
            materials_table = self._extract_materials()
            if materials_table:
                result.tables.append(materials_table)
            
            result.overall_confidence = 0.95  # IFC extraction is very reliable
            result.extraction_methods = [ExtractionMethod.IFCOPENSHELL]
            result.status = ExtractionStatus.COMPLETED
            result.page_count = 1
            
        except Exception as e:
            result.status = ExtractionStatus.FAILED
            result.errors.append(str(e))
        
        return result
    
    def _extract_project_metadata(self) -> Dict[str, Any]:
        """Extract project-level metadata"""
        metadata = {
            "schema": self.model.schema,
        }
        
        # Get project
        projects = self.model.by_type("IfcProject")
        if projects:
            project = projects[0]
            metadata["project_name"] = project.Name or ""
            metadata["project_description"] = project.Description or ""
            metadata["project_phase"] = project.Phase or ""
        
        # Get units
        try:
            length_unit = ifc_unit.get_project_unit(self.model, "LENGTHUNIT")
            metadata["length_unit"] = str(length_unit) if length_unit else "mm"
        except:
            metadata["length_unit"] = "mm"
        
        # Count elements
        element_counts = {}
        for element_type in self.ELEMENT_TYPES:
            count = len(self.model.by_type(element_type))
            if count > 0:
                element_counts[element_type] = count
        metadata["element_counts"] = element_counts
        
        return metadata
    
    def _extract_elements_as_tables(self) -> List[ExtractedTable]:
        """Extract each element type as a table"""
        tables = []
        
        for element_type in self.ELEMENT_TYPES:
            elements = self.model.by_type(element_type)
            
            if not elements:
                continue
            
            # Collect all unique property names across elements
            all_properties = set()
            element_data = []
            
            for element in elements:
                props = self._get_element_properties(element)
                all_properties.update(props.keys())
                element_data.append(props)
            
            if not element_data:
                continue
            
            # Build table
            headers = ["GlobalId", "Name", "Type"] + sorted(all_properties - {"GlobalId", "Name", "Type"})
            rows = []
            
            for props in element_data:
                row = [props.get(h, "") for h in headers]
                rows.append(row)
            
            tables.append(ExtractedTable(
                page_number=1,
                table_index=len(tables),
                headers=headers,
                rows=rows,
                confidence=0.95,
                extraction_method=ExtractionMethod.IFCOPENSHELL,
            ))
        
        return tables
    
    def _get_element_properties(self, element) -> Dict[str, Any]:
        """Get all properties for an element"""
        props = {
            "GlobalId": element.GlobalId,
            "Name": element.Name or "",
        }
        
        # Get element type
        element_type = ifc_util.get_type(element)
        if element_type:
            props["Type"] = element_type.Name or ""
        else:
            props["Type"] = ""
        
        # Get all property sets
        psets = ifc_util.get_psets(element)
        for pset_name, pset_props in psets.items():
            for prop_name, prop_value in pset_props.items():
                # Prefix with pset name to avoid conflicts
                key = f"{pset_name}.{prop_name}"
                props[key] = self._format_property_value(prop_value)
        
        # Get quantities
        qtos = ifc_util.get_psets(element, qtos_only=True)
        for qto_name, qto_props in qtos.items():
            for prop_name, prop_value in qto_props.items():
                key = f"Qto.{prop_name}"
                props[key] = self._format_property_value(prop_value)
        
        # Get material
        material = ifc_util.get_material(element)
        if material:
            if hasattr(material, "Name"):
                props["Material"] = material.Name or ""
            elif hasattr(material, "MaterialLayers"):
                layers = [l.Material.Name for l in material.MaterialLayers if l.Material]
                props["Material"] = ", ".join(layers)
        
        # Get container (spatial location)
        container = ifc_util.get_container(element)
        if container:
            props["Location"] = container.Name or ""
        
        return props
    
    def _extract_spatial_hierarchy(self) -> Optional[ExtractedTable]:
        """Extract spatial hierarchy as a table"""
        hierarchy = []
        
        # Get all spatial elements
        sites = self.model.by_type("IfcSite")
        buildings = self.model.by_type("IfcBuilding")
        storeys = self.model.by_type("IfcBuildingStorey")
        spaces = self.model.by_type("IfcSpace")
        
        for site in sites:
            hierarchy.append({
                "Level": "Site",
                "Name": site.Name or "",
                "Description": site.Description or "",
                "GlobalId": site.GlobalId,
            })
        
        for building in buildings:
            hierarchy.append({
                "Level": "Building",
                "Name": building.Name or "",
                "Description": building.Description or "",
                "GlobalId": building.GlobalId,
            })
        
        for storey in storeys:
            elevation = storey.Elevation if hasattr(storey, "Elevation") else ""
            hierarchy.append({
                "Level": "Storey",
                "Name": storey.Name or "",
                "Description": storey.Description or "",
                "GlobalId": storey.GlobalId,
                "Elevation": elevation,
            })
        
        for space in spaces:
            hierarchy.append({
                "Level": "Space",
                "Name": space.Name or "",
                "Description": space.Description or "",
                "GlobalId": space.GlobalId,
            })
        
        if not hierarchy:
            return None
        
        headers = ["Level", "Name", "Description", "GlobalId", "Elevation"]
        rows = [[h.get(col, "") for col in headers] for h in hierarchy]
        
        return ExtractedTable(
            page_number=1,
            table_index=0,
            headers=headers,
            rows=rows,
            confidence=0.95,
            extraction_method=ExtractionMethod.IFCOPENSHELL,
        )
    
    def _extract_materials(self) -> Optional[ExtractedTable]:
        """Extract all materials as a table"""
        materials = self.model.by_type("IfcMaterial")
        
        if not materials:
            return None
        
        rows = []
        for mat in materials:
            row = [
                mat.Name or "",
                mat.Description if hasattr(mat, "Description") else "",
                mat.Category if hasattr(mat, "Category") else "",
            ]
            rows.append(row)
        
        return ExtractedTable(
            page_number=1,
            table_index=0,
            headers=["Name", "Description", "Category"],
            rows=rows,
            confidence=0.95,
            extraction_method=ExtractionMethod.IFCOPENSHELL,
        )
    
    def _format_property_value(self, value: Any) -> str:
        """Format property value for display"""
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value)
        return str(value)
```

---

### Weeks 15-16: STEP/STP Extraction & ML Pipeline

#### Tasks (Week 15)

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 3.15.1 | Create STEPExtractor base class | Critical | 4h | 3.11.4 |
| 3.15.2 | Implement cadquery/pythonocc loading | Critical | 4h | 3.15.1 |
| 3.15.3 | Extract part metadata | Critical | 4h | 3.15.2 |
| 3.15.4 | Extract geometric properties | High | 6h | 3.15.2 |
| 3.15.5 | Extract assembly structure | High | 6h | 3.15.2 |
| 3.15.6 | Extract material properties from STEP | Medium | 4h | 3.15.2 |
| 3.15.7 | Generate thumbnail/preview images | Medium | 4h | 3.15.2 |
| 3.15.8 | Write STEP extraction tests | Critical | 4h | 3.15.* |

#### Tasks (Week 16)

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 3.16.1 | Set up YOLOv11 inference pipeline | High | 6h | 3.12.* |
| 3.16.2 | Set up Donut model for text extraction | High | 6h | 3.16.1 |
| 3.16.3 | Create ML fallback for engineering drawings | High | 8h | 3.16.2 |
| 3.16.4 | Implement confidence-based routing | High | 4h | 3.16.3 |
| 3.16.5 | Create training data collection pipeline | Medium | 4h | 3.16.3 |
| 3.16.6 | Write ML extraction tests | High | 4h | 3.16.* |
| 3.16.7 | Benchmark ML vs Werk24 accuracy | Medium | 4h | 3.16.* |

---

### Weeks 17-18: Integration, API, & Testing

#### Tasks (Week 17)

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 3.17.1 | Create unified extraction service | Critical | 6h | 3.11-16.* |
| 3.17.2 | Build extraction preview API | Critical | 4h | 3.17.1 |
| 3.17.3 | Implement field mapping interface | Critical | 6h | 3.17.1 |
| 3.17.4 | Build import workflow API | Critical | 6h | 3.17.3 |
| 3.17.5 | Implement extraction job queue | High | 4h | 3.17.1 |
| 3.17.6 | Add extraction progress tracking | High | 4h | 3.17.5 |
| 3.17.7 | Create extraction webhook notifications | Medium | 3h | 3.17.5 |
| 3.17.8 | Build batch extraction support | Medium | 4h | 3.17.1 |

#### Tasks (Week 18)

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 3.18.1 | End-to-end integration testing | Critical | 8h | 3.17.* |
| 3.18.2 | Performance benchmarking | Critical | 6h | 3.18.1 |
| 3.18.3 | Error handling and edge cases | Critical | 6h | 3.18.1 |
| 3.18.4 | Extraction accuracy validation | Critical | 6h | 3.18.1 |
| 3.18.5 | API documentation | High | 4h | 3.17.* |
| 3.18.6 | Create extraction examples | Medium | 4h | 3.18.5 |
| 3.18.7 | Security review for file uploads | Critical | 4h | 3.17.* |
| 3.18.8 | Production deployment preparation | High | 4h | 3.18.* |

---

## API Endpoints Summary

### Extraction Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/extract` | POST | Upload file and start extraction |
| `/api/v1/extract/pdf` | POST | Extract PDF specifically |
| `/api/v1/extract/dxf` | POST | Extract DXF file |
| `/api/v1/extract/ifc` | POST | Extract IFC/BIM file |
| `/api/v1/extract/step` | POST | Extract STEP/STP file |
| `/api/v1/extract/image` | POST | Extract from image (OCR) |
| `/api/v1/extractions` | GET | List user's extractions |
| `/api/v1/extractions/{id}` | GET | Get extraction result |
| `/api/v1/extractions/{id}/tables` | GET | Get extracted tables |
| `/api/v1/extractions/{id}/tables/{table_id}` | GET | Get specific table data |
| `/api/v1/extractions/{id}/preview` | GET | Get extraction preview |
| `/api/v1/extractions/{id}/import` | POST | Import extraction to PyBase table |
| `/api/v1/extractions/{id}/mapping` | GET | Get suggested field mappings |
| `/api/v1/extractions/{id}/mapping` | PUT | Update field mappings |

### Request/Response Examples

**Extract PDF**
```http
POST /api/v1/extract/pdf
Content-Type: multipart/form-data

file: <binary>
options: {
  "ocr_enabled": true,
  "extract_dimensions": true,
  "extract_gdt": true,
  "use_werk24": true
}
```

**Response**
```json
{
  "id": "ext_abc123",
  "status": "processing",
  "job_id": "job_xyz789",
  "estimated_time_seconds": 30
}
```

**Get Extraction Result**
```http
GET /api/v1/extractions/ext_abc123
```

**Response**
```json
{
  "id": "ext_abc123",
  "filename": "drawing.pdf",
  "file_type": "pdf",
  "status": "completed",
  "page_count": 3,
  "tables": [
    {
      "id": "tbl_001",
      "page": 1,
      "headers": ["Part Number", "Description", "Qty", "Material"],
      "row_count": 15,
      "confidence": 0.92
    }
  ],
  "dimensions_count": 47,
  "gdt_count": 12,
  "threads_count": 8,
  "title_block": {
    "drawing_number": "DWG-001-A",
    "title": "Main Assembly",
    "revision": "C",
    "material": "AISI 304"
  },
  "overall_confidence": 0.89,
  "processing_time_ms": 4523
}
```

---

## Dependencies (requirements-extraction.txt)

```
# PDF Processing
pdfplumber>=0.10.0
tabula-py>=2.9.0
PyMuPDF>=1.23.0
pytesseract>=0.3.10
Pillow>=10.2.0
pdf2image>=1.17.0

# CAD Processing
ezdxf>=1.1.0
ifcopenshell>=0.7.0

# 3D CAD (choose one based on needs)
cadquery>=2.4.0
# OR
# pythonocc-core>=7.7.0  # More powerful but harder to install

# Machine Learning (optional, for custom models)
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0  # YOLOv8/v11
transformers>=4.35.0  # For Donut model

# Data Processing
pandas>=2.2.0
openpyxl>=3.1.0
numpy>=1.26.0

# Image Processing
opencv-python>=4.9.0
scikit-image>=0.22.0

# File Type Detection
python-magic>=0.4.27

# HTTP Client (for Werk24)
httpx>=0.26.0

# Async Support
aiofiles>=23.2.0
```

---

## Phase 3 Acceptance Criteria

### Extraction Coverage

| File Type | Required Features | Status |
|-----------|-------------------|--------|
| PDF | Tables, text, dimensions, GD&T, threads, title block | Required |
| DXF | Text, dimensions, blocks, title block | Required |
| IFC | Elements, properties, materials, hierarchy | Required |
| STEP | Metadata, geometry properties, assembly | Required |
| Images | OCR text extraction | Required |

### Accuracy Targets

| Extraction Type | Target Accuracy | Validation Method |
|-----------------|-----------------|-------------------|
| PDF tables | > 90% | Ground truth comparison |
| Dimensions | > 85% | Manual verification |
| GD&T | > 80% | Manual verification |
| Title blocks | > 90% | Field matching |
| DXF attributes | > 95% | Automated tests |
| IFC properties | > 98% | Automated tests |

### Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| PDF (1 page) | < 5s | p95 latency |
| PDF (10 pages) | < 30s | p95 latency |
| DXF (simple) | < 3s | p95 latency |
| IFC (medium) | < 10s | p95 latency |
| STEP (small) | < 5s | p95 latency |

### Test Coverage

- [ ] Unit tests: > 85% coverage
- [ ] Integration tests: All extractors
- [ ] Accuracy tests: Sample files
- [ ] Performance tests: Benchmarks

---

## Phase 3 Exit Criteria

Before proceeding to Phase 4:

1. [ ] All 5 extractor types implemented
2. [ ] Accuracy targets met for each
3. [ ] API endpoints complete and documented
4. [ ] Import workflow functional
5. [ ] Werk24 integration working (or fallback)
6. [ ] Performance benchmarks met
7. [ ] Security review completed

---

## Dependencies for Phase 4

Phase 3 must deliver:
- Working extraction pipeline for all file types
- Import workflow to PyBase tables
- Engineering field type population

Phase 4 will build views to display and interact with extracted data.

---

*Previous: [Phase 2: Core Database](master-plan-phase-2-core-database.md)*  
*Next: [Phase 4: Views & Data Presentation](master-plan-phase-4-views.md)*
