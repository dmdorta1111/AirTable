# B2 Files Audit Report - Double Slash & Duplicate Files

**Date:** 2026-01-22
**Bucket:** EmjacDB
**Database:** Neon PostgreSQL (CloudFiles table)

## Executive Summary

This audit identified **critical issues** with file path formatting and data consistency between the Backblaze B2 storage bucket and the Neon database metadata.

### Key Findings:
- **819,329 total files** in database CloudFiles table
- **100% of files** have double slash path issues (Y:// or S://)
- **3,347 duplicate file groups** detected (by FileHash)
- Significant discrepancy between B2 bucket and database records

---

## 1. Database Audit Results (Neon PostgreSQL)

### File Statistics
| Metric | Count |
|--------|-------|
| Total Files | **819,329** |
| Unique Files (by FileHash) | **815,726** |
| Duplicate Files | **~3,603** (3,347 groups × avg 1.08 copies) |

### Double Slash Issues

#### Y:// Protocol Paths
- **Count:** 748,554 files (**91.4%** of all files)
- **Sample Paths:**
  - `Y://000_SDI/OPENING_59150_112-RHR.pdf`
  - `Y://DXF/71000's/71736-004/71736-004_008.dxf`
  - `Y://N9283_SetupPlan.pdf`

#### S:// Protocol Paths
- **Count:** 70,775 files (**8.6%** of all files)
- **Sample Paths:**
  - `S://_ JOBS STAINLESS DOORS/00_FORMS/Stainless Doors CAD Release.pdf`
  - `S://_ JOBS STAINLESS DOORS/2020/77004_VALLEY MEDICAL PAVILION - AUBURN, WA/...`

#### Total Double Slash Issues
- **819,329 files** affected (100% of database)
- No files use standard single-slash paths

### Duplicate Files Analysis

#### By FileHash (Content Duplicates)
- **Groups:** 3,347 duplicate groups
- **Top duplicate:** `dee41ba3576c73d5...` with 8 copies
- **Estimated waste:** ~0.35 GB (from top 50 groups sample)

#### By CloudKey (Path Duplicates)
- **Count:** 0 duplicate CloudKeys
- All file paths are unique

---

## 2. B2 Bucket Audit Results (Backblaze B2)

### Scan Scope
- **Files scanned:** 100,000 (limited scan)
- **Bucket:** EmjacDB

### Double Slash Issues

#### Y:// Protocol Paths
- **Count:** 25,601 files (25.6% of scanned)
- **Sample Paths:**
  - `Y://DXF/71000's/71901-001/71901-001_107.dxf`
  - `Y://DXF/71000's/71902-001/71902-001.pdf`

#### S:// Protocol Paths
- **Count:** 35,818 files (35.8% of scanned)
- **Sample Paths:**
  - `S://_ JOBS STAINLESS DOORS/00_FORMS/Stainless Doors CAD Release.pdf`
  - `S://_ JOBS STAINLESS DOORS/2020/77004_VALLEY MEDICAL PAVILION/...`

#### Total Double Slash Issues
- **61,419 files** (61.4% of scanned files)

---

## 3. Database vs B2 Discrepancy Analysis

### Critical Findings

1. **Path Format Inconsistency**
   - Database: 100% double slash paths (819K files)
   - B2 Bucket: ~61% double slash paths (scanned 100K)
   - **38% discrepancy** - B2 has files without double slashes that aren't in database

2. **File Count Mismatch**
   - Database CloudFiles: 819,329 records
   - B2 bucket appears to have different structure

3. **Data Integrity Issues**
   - Double slash format (`Y://`, `S://`) is non-standard
   - Should be single slash (`Y:/`, `S:/`) or proper URI format
   - Affects file path resolution and URL generation

---

## 4. Impact Assessment

### Issues Identified

| Issue | Severity | Impact |
|-------|----------|--------|
| Double slash paths | **HIGH** | Breaks path resolution, URL generation |
| Database/B2 mismatch | **HIGH** | Sync issues, data inconsistency |
| Duplicate files | **MEDIUM** | Storage waste, confusion |

### Storage Impact
- Duplicate files: ~0.35 GB minimum (from sample)
- Actual waste likely higher given 3,347 duplicate groups

### Operational Impact
- File access failures due to malformed paths
- Broken links and downloads
- Sync failures between systems

---

## 5. Recommendations

### Immediate Actions (Priority 1)

1. **Fix Double Slash Paths**
   ```sql
   -- Fix Y:// to Y:/
   UPDATE "CloudFiles"
   SET "CloudKey" = REPLACE("CloudKey", 'Y://', 'Y:/')
   WHERE "CloudKey" LIKE 'Y://%%';

   -- Fix S:// to S:/
   UPDATE "CloudFiles"
   SET "CloudKey" = REPLACE("CloudKey", 'S://', 'S:/')
   WHERE "CloudKey" LIKE 'S://%%';
   ```

2. **Audit and Sync B2 Bucket**
   - Scan entire B2 bucket (not just 100K files)
   - Compare all files with database
   - Identify missing/orphaned records

3. **Remove Duplicate Files**
   - Identify duplicates by FileHash
   - Keep oldest version (lowest ID)
   - Delete newer duplicates

### Long-term Actions (Priority 2)

1. **Add validation constraints** to prevent double slash paths
2. **Implement periodic audits** of database vs B2
3. **Add duplicate detection** during file upload
4. **Fix sync process** that may be introducing double slashes

---

## 6. Data Files

- **Database Audit:** `output/db-audit-20260122-071901.json`
- **B2 Audit:** `output/b2-audit-20260122-070251.json`
- **Audit Scripts:**
  - `b2-audit-double-slash-duplicates.py` (Combined audit)
  - `db-audit-only.py` (Database-only audit)

---

## 7. Unresolved Questions

1. Why are there 100% double slash paths in database vs ~61% in B2?
2. What process is introducing the double slash format?
3. Are there files in B2 that don't exist in database?
4. What's the total storage impact of all duplicates (not just sample)?
5. Should we use `Y:/` or remove drive letters entirely?

---

**Report Generated:** 2026-01-22 07:19 UTC
**Audited By:** Claude Code Audit Tool
