I've gathered comprehensive research on PDF/CAD extraction for engineering drawings. Let me compile this into a summary with recommendations for enhancing PyBase's field types.

Based on my research, here's what I've found for drastically enhancing field type capture from customer CAD drawings:

---

## Research Summary: CAD/Engineering Drawing Extraction for PyBase

### Specialized Content in Engineering Drawings

**Title Block Data:**
- Drawing ID, designation, material, general tolerances
- Revision info, part numbers, vendor info
- Preparation records, approval signatures

**Geometric Dimensioning & Tolerancing (GD&T):**
- Feature control frames, datum references
- Tolerance specifications (ISO 2768, ASME Y14.5)
- 14+ geometric tolerance types

**Dimensions & Measurements:**
- Linear/angular dimensions with ± tolerances
- Limits and fits (H7/G6, etc.)
- Theoretically exact dimensions

**Technical Annotations:**
- Surface roughness (Ra, Rz values)
- Threads (metric M10x1.5, imperial 1/4-20 UNC)
- Chamfers, radii, holes, bores, counterbores

**Bill of Materials (BOM):**
- Item numbers, part numbers, quantities
- Material specifications, descriptions
- Assembly relationships

---

### Python Libraries & Tools

**1. Werk24 (Commercial API - werk24.io)** ⭐ Best for PDF/scanned drawings
```python
from werk24 import Werk24Client, AskMetaData, AskFeatures

async with Werk24Client() as client:
    async for msg in client.read_drawing(pdf_bytes, [AskMetaData(), AskFeatures()]):
        print(msg.payload_dict)
```
- 95%+ accuracy for PMI extraction
- Returns structured JSON with confidence scores
- Extracts: title blocks, dimensions, tolerances, GD&T, threads, chamfers, radii, surface roughness
- Supports ISO and ASME/ANSI standards
- Multi-language (German, English, French, Spanish, Japanese, etc.)

**2. ezdxf (Open Source - DXF/DWG parsing)**
```python
import ezdxf
doc = ezdxf.readfile("drawing.dxf")
msp = doc.modelspace()

# Query blocks and attributes
for block_ref in msp.query('INSERT[name=="TITLE_BLOCK"]'):
    title = block_ref.get_attrib_text("TITLE")
    material = block_ref.get_attrib_text("MATERIAL")
    
# Extract all text entities
for text in msp.query('TEXT'):
    print(text.dxf.text, text.dxf.insert)
```
- Read/write DXF R12 through R2018
- Extract blocks, attributes, layers, text
- Query syntax for filtering entities

**3. IfcOpenShell (Open Source - IFC/BIM for Revit)**
```python
import ifcopenshell
import ifcopenshell.util.element as util

model = ifcopenshell.open("building.ifc")
walls = model.by_type("IfcWall")

for wall in walls:
    psets = util.get_psets(wall)  # All properties
    wall_type = util.get_type(wall)
    container = util.get_container(wall)  # Location
```
- Supports IFC2X3, IFC4, IFC4x3
- Extract properties, quantities, materials
- Query elements by type, relationships

**4. PythonOCC / CadQuery (STEP/STP files)**
```python
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Extend.TopologyUtils import TopologyExplorer

reader = STEPControl_Reader()
reader.ReadFile('part.stp')
reader.TransferRoots()
shape = reader.OneShape()

# Traverse topology
explorer = TopologyExplorer(shape)
for face in explorer.faces():
    # Extract face geometry
```
- Read STEP, IGES, BREP formats
- Extract vertices, edges, faces, solids
- Geometric analysis capabilities

**5. Deep Learning Approach (YOLOv11 + Donut)**
- Research paper arXiv 2505.01530
- 94.77% precision, 97.3% F1 score
- Categories: GD&T, General Tolerances, Measures, Materials, Notes, Radii, Surface Roughness, Threads, Title Blocks

---

### Enhanced Field Types for PyBase

Based on engineering drawing requirements, here are recommended new field types:

```python
# Engineering-Specific Fields
class DimensionField:
    """Stores nominal value, tolerance, units, fit designation"""
    nominal_value: Decimal
    tolerance_upper: Decimal | None
    tolerance_lower: Decimal | None
    tolerance_type: str  # 'symmetric', 'asymmetric', 'limits', 'fit'
    fit_designation: str | None  # 'H7', 'g6', etc.
    unit: str  # 'mm', 'inch'

class GDTField:
    """Geometric tolerance with feature control frame data"""
    symbol: str  # 'position', 'perpendicularity', 'flatness', etc.
    tolerance_value: Decimal
    datum_references: list[str]  # ['A', 'B', 'C']
    material_modifier: str | None  # 'MMC', 'LMC', 'RFS'

class ThreadField:
    """Thread specification"""
    designation: str  # 'M10x1.5', '1/4-20 UNC'
    thread_type: str  # 'metric', 'imperial_unified', 'imperial_pipe'
    major_diameter: Decimal
    pitch: Decimal
    thread_class: str | None  # '6H', '2A', etc.

class SurfaceFinishField:
    """Surface roughness values"""
    ra_value: Decimal | None
    rz_value: Decimal | None
    unit: str  # 'μm', 'μin'
    process: str | None  # 'ground', 'milled', etc.

class MaterialField:
    """Material specification"""
    designation: str  # 'AISI 304', '6061-T6'
    standard: str | None  # 'ASTM', 'DIN', 'JIS'
    grade: str | None
    
class DrawingReferenceField:
    """Drawing reference metadata"""
    drawing_number: str
    revision: str
    sheet: int | None
    
class BOMItemField:
    """Bill of materials entry"""
    item_number: int
    part_number: str
    description: str
    quantity: int
    material: str | None
    
class RevisionHistoryField:
    """Revision tracking"""
    revision: str
    date: datetime
    description: str
    author: str | None
```

---

### Implementation Recommendations

**Hybrid Extraction Strategy:**
1. **For PDFs/scanned drawings:** Use Werk24 API (commercial) or custom YOLOv11+Donut model
2. **For native DXF/DWG:** Use ezdxf library
3. **For IFC (Revit/BIM):** Use ifcopenshell
4. **For STEP/STP:** Use pythonocc-core or cadquery

**Dependencies to Add:**
```
werk24>=2.3.0        # Commercial API for PDF extraction
ezdxf>=1.4.0         # DXF/DWG parsing
ifcopenshell>=0.8.0  # IFC/BIM parsing
cadquery>=2.4.0      # STEP parsing (easier than pythonocc)
opencv-python        # Image preprocessing
```

**Extraction Workflow:**
1. Upload CAD file or PDF
2. Auto-detect file type
3. Route to appropriate extractor
4. Present extracted data for review/editing
5. Map to PyBase table schema
6. Store original file as attachment
7. Create records with extracted data

Would you like me to start implementing any of these components for PyBase, or dive deeper into any specific area?