# Unified Engineering Document Intelligence Platform
## DEPLOYMENT PACKAGE - Complete System in One Directory

This directory contains everything needed to run the Unified Engineering Document Intelligence Platform on any remote machine. 

## 📦 What's Included

```
unified-doc-intelligence-deploy/
├── README.md (this file)
├── DEPLOYMENT_GUIDE.md (complete setup instructions)
├── requirements.txt (all Python dependencies)
├── config-template.txt (configuration template)
├── setup.py (Python installation script)
├── deploy.sh (Bash deployment script - cross-platform)
├── run-pipeline.py (complete executor for all 3 phases)
├── scripts/
│   ├── phase-a-linking/
│   │   ├── A1-migrate-schema.py
│   │   ├── A2-link-by-basename.py
│   │   ├── A3-link-by-folder.py
│   │   ├── A4-extract-project-codes.py
│   │   ├── A5-flag-review-queue.py
│   │   └── A6-generate-link-report.py
│   ├── phase-b-extraction/
│   │   ├── B1-create-extraction-tables.py
│   │   ├── B2-queue-extraction-jobs.py
│   │   ├── B3-pdf-extraction-worker.py
│   │   ├── B4-dxf-extraction-worker.py
│   │   ├── B5-index-dimensions.py
│   │   ├── B6-index-materials.py
│   │   └── B7-extraction-report.py
│   └── phase-c-search/
│       ├── C1-search-dimensions.py
│       ├── C2-search-parameters.py
│       ├── C3-search-materials.py
│       ├── C4-search-projects.py
│       ├── C5-search-fulltext.py
│       └── C6-search-api-server.py
├── docs/
│   ├── IMPLEMENTATION_GUIDE.md (complete execution guide)
│   └── API_GUIDE.md (search API documentation)
└── output/ (created during execution)
```

## 🚀 Quick Start

### 1. Copy to Remote Machine
```bash
# Copy this entire directory to your remote machine
scp -r unified-doc-intelligence-deploy/ user@remote-machine:/path/to/destination/
```

### 2. Configure Settings
```bash
cd unified-doc-intelligence-deploy
# Edit config-template.txt with your credentials
cp config-template.txt config.txt
nano config.txt  # Add your Neon PostgreSQL and Backblaze B2 credentials
```

### 3. Install Dependencies
```bash
# Method 1: Using Python script
python setup.py

# Method 2: Using bash script (cross-platform)
chmod +x deploy.sh
./deploy.sh

# Method 3: Manual installation
pip install -r requirements.txt
```

### 4. Run Complete Pipeline
```bash
# Execute the entire 3-phase pipeline
python run-pipeline.py --phase all

# Or run phases individually
python run-pipeline.py --phase a        # Auto-linking only
python run-pipeline.py --phase b        # PDF/DXF extraction only
python run-pipeline.py --phase c        # Search API only
```

## 📊 System Overview

The platform processes **819,000+ engineering files** with:

**Phase A: Auto-Linking (2-3 hours)**
- Links related files (PDF, DXF, CAD) into DocumentGroups
- 3 linking strategies: basename (95% confidence), folder (80%), project codes (70%)
- Creates ~37,000 DocumentGroups from ~819,000 individual files

**Phase B: PDF/DXF Extraction (6-8 hours)**
- Extracts metadata from **191,000+ PDF** and **574,000+ DXF** files
- 50 parallel workers for high throughput
- Extracts dimensions, materials, parameters, BOM items

**Phase C: Search API (4-6 hours)**
- FastAPI server with 6 specialized search endpoints
- Dimensions, parameters, materials, projects, full-text search
- Returns linked DocumentGroups with all related files

## 🔧 Technical Requirements

- **Python 3.8+** (tested with Python 3.11)
- **PostgreSQL 12+** (Neon PostgreSQL recommended)
- **Network access** to Backblaze B2 storage (EmjacDB bucket)
- **Disk space:** ~2GB for scripts, dependencies, temporary files
- **Memory:** 4GB+ for parallel extraction

## 📈 Performance Expectations

| Phase | Files | Duration | Parallel Workers |
|-------|-------|----------|------------------|
| A (Linking) | 819K | 2-3 hours | Single process |
| B (Extraction) | 765K | 6-8 hours | 50 workers |
| C (Search API) | Live | Continuous | 4 API workers |

## 🛠️ Deployment Options

### Single Machine Deployment
```bash
# Full system on one machine
python run-pipeline.py --workers 50 --api-workers 4
```

### Distributed Processing (Recommended for 765K+ files)
```bash
# Machine 1: PDF extraction workers
python scripts/phase-b-extraction/B3-pdf-extraction-worker.py --workers 20

# Machine 2: DXF extraction workers  
python scripts/phase-b-extraction/B4-dxf-extraction-worker.py --workers 20

# Machine 3: Search API server
uvicorn scripts/phase-c-search/C6-search-api-server:app --host 0.0.0.0 --port 8080 --workers 4
```

### Cloud Deployment
- All machines connect to same **Neon PostgreSQL** instance
- All workers access same **Backblaze B2** bucket (`EmjacDB`)
- Shared `extraction_jobs` table coordinates distributed processing

## 🔍 Search API Endpoints

Once deployed, access the API at `http://localhost:8080`:
- `GET /api/search/dimensions` - Search by dimension value, tolerance, unit
- `GET /api/search/parameters` - Search engineering parameters (weight, pressure, etc.)
- `GET /api/search/materials` - Fuzzy material search
- `GET /api/search/projects` - Find all files for a project code
- `GET /api/search/fulltext` - Full-text search across all extracted data
- `GET /docs` - Interactive Swagger UI documentation
- `GET /redoc` - Alternative API documentation

## 🗄️ Database Schema

The platform creates 8 new tables in your PostgreSQL database:

| Table | Purpose | Size Estimate |
|-------|---------|---------------|
| `document_groups` | Logical grouping of related files | ~37K rows |
| `document_group_members` | File-to-group mapping | ~2.3M rows |
| `extraction_jobs` | Coordination of distributed extraction | ~765K rows |
| `extracted_metadata` | General file metadata | ~765K rows |
| `extracted_dimensions` | Dimension/tolerance search index | ~2M rows |
| `extracted_parameters` | Parameter search index | ~5M rows |
| `extracted_materials` | Material search index | ~200K rows |
| `extracted_bom_items` | BOM component search index | ~1M rows |

## 📝 Maintenance & Monitoring

### Check System Health
```bash
python run-pipeline.py --status

# Monitor extraction progress
SELECT extraction_status, COUNT(*) FROM extracted_metadata GROUP BY 1;

# Check document group statistics
SELECT * FROM v_document_groups_summary;
```

### Troubleshooting
- **Database connectivity**: Verify `NEON_DATABASE_URL` in config.txt
- **B2 storage access**: Verify `B2_APPLICATION_KEY_ID` and `B2_APPLICATION_KEY`
- **Performance issues**: Reduce worker count with `--workers 10` flag
- **Extraction failures**: Check `output/extraction-errors.log`

## 📚 Additional Documentation

- `docs/IMPLEMENTATION_GUIDE.md` - Complete execution instructions
- `docs/API_GUIDE.md` - Search API reference
- Interactive Swagger UI at `http://localhost:8080/docs`

## 📄 License & Support

This deployment package is part of the **Unified Engineering Document Intelligence Platform**.

For support or questions:
1. Check the `docs/` directory for detailed guides
2. Review error logs in `output/` directory
3. Use the status monitoring commands

---

*Deployment Package v1.0 - Unified Engineering Document Intelligence Platform*  
*Package Date: 2026-01-20*  
*Total Files: 19 Python scripts + 5 configuration/docs*  
*Ready for distributed processing across any number of machines*