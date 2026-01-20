# PDF to DXF Batch Conversion - Requirements Analysis Plan

> **Goal:** Gather all information needed to design a batch conversion pipeline for 100k+ PDF files from Backblaze to DXF format

## Quick Start

### 1. Install Dependencies

```bash
pip install psycopg2-binary b2sdk pymupdf ezdxf python-dotenv tabulate requests
```

### 2. Configure Credentials

Copy `config-template.txt` to `config.txt` and fill in your credentials:

```bash
cp config-template.txt config.txt
# Edit config.txt with your Neon and Backblaze credentials
```

### 3. Run Analysis Scripts (in order)

```bash
cd plans/260119-0935-pdf-to-dxf-analysis

# Step 1: Analyze Neon database structure
python 01-analyze-neon-database.py

# Step 2: Analyze Backblaze storage
python 02-analyze-backblaze-storage.py

# Step 3: Download and analyze sample PDFs
python 03-download-and-analyze-samples.py

# Step 4: Test PDF to DXF conversion
python 04-test-pdf-to-dxf-conversion.py

# Step 5: Generate requirements report
python 05-generate-requirements-report.py
```

### 4. Share Results

Share the generated `output/REQUIREMENTS-REPORT.md` file for implementation planning.

---

## What Each Script Does

| Script | Purpose | Output |
|--------|---------|--------|
| `01-analyze-neon-database.py` | Discovers tables, schemas, PDF-related columns, embeddings | `output/neon-analysis.json` |
| `02-analyze-backblaze-storage.py` | Scans bucket, counts PDFs, analyzes size distribution | `output/backblaze-analysis.json` |
| `03-download-and-analyze-samples.py` | Downloads 10 sample PDFs, determines vector/raster type | `output/pdf-analysis.json` |
| `04-test-pdf-to-dxf-conversion.py` | Tests PyMuPDF+ezdxf conversion on samples | `output/conversion-tests.json` |
| `05-generate-requirements-report.py` | Consolidates all data into final report | `output/REQUIREMENTS-REPORT.md` |

---

## Information Gathered

### From Neon Database
- Table schemas containing PDF references
- Total record count
- Embedding dimensions
- File path/URL structure
- Metadata columns

### From Backblaze Storage
- Total file count and sizes
- PDF file distribution
- Folder organization
- Sample file paths

### From PDF Analysis
- Vector vs Raster content ratio
- Page count distribution
- CAD origin detection
- Estimated DXF quality

### From Conversion Tests
- Success rate
- Processing time per file
- Entity counts
- Error patterns

---

## Estimated Time: 30-60 minutes

## Output Location

All results saved to `output/` directory within this plan folder.
