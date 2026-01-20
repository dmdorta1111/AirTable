#!/usr/bin/env python3
"""
C6-search-api-server.py
FastAPI server exposing all search endpoints for the Engineering Document Intelligence Platform.

Usage:
    # Start server (development)
    uvicorn C6-search-api-server:app --reload --host 0.0.0.0 --port 8080

    # Start server (production)
    uvicorn C6-search-api-server:app --host 0.0.0.0 --port 8080 --workers 4

API Documentation:
    - Swagger UI: http://localhost:8080/docs
    - ReDoc: http://localhost:8080/redoc
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from typing import Optional, List, Any
from contextlib import asynccontextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PLAN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PLAN_DIR / "config.txt"

# Global connection pool
db_pool: Optional[ThreadedConnectionPool] = None


# ============================================================================
# Configuration
# ============================================================================


def load_config():
    """Load configuration from config.txt file."""
    if not CONFIG_FILE.exists():
        logger.error(f"Config file not found: {CONFIG_FILE}")
        logger.info("Please copy config-template.txt to config.txt and fill in your credentials")
        sys.exit(1)

    config = {}
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


# ============================================================================
# Database Connection Pool
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and cleanup resources."""
    global db_pool

    # Startup
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    logger.info("Initializing database connection pool...")
    db_pool = ThreadedConnectionPool(minconn=2, maxconn=10, dsn=db_url)
    logger.info("Database connection pool ready")

    yield

    # Shutdown
    if db_pool:
        db_pool.closeall()
        logger.info("Database connections closed")


def get_db_connection():
    """Get a database connection from the pool."""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database pool not initialized")

    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)


# ============================================================================
# Pydantic Models
# ============================================================================


class DocumentGroup(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    project_code: Optional[str] = None
    item_number: Optional[str] = None


class FileInfo(BaseModel):
    id: int
    type: Optional[str] = None
    path: Optional[str] = None
    filename: Optional[str] = None
    match_details: Optional[List[dict]] = None


class SearchResult(BaseModel):
    document_group: Optional[DocumentGroup] = None
    files: List[FileInfo] = []
    match: Optional[dict] = None


class PaginationInfo(BaseModel):
    limit: int
    offset: int
    total: int


class DimensionSearchResponse(BaseModel):
    query: dict
    pagination: PaginationInfo
    result_count: int
    results: List[dict]


class ParameterSearchResponse(BaseModel):
    query: dict
    pagination: PaginationInfo
    result_count: int
    results: List[dict]


class MaterialSearchResponse(BaseModel):
    query: dict
    pagination: PaginationInfo
    result_count: int
    results: List[dict]


class ProjectSearchResponse(BaseModel):
    query: dict
    pagination: PaginationInfo
    result_count: int
    results: List[dict]
    statistics: Optional[dict] = None


class FulltextSearchResponse(BaseModel):
    query: dict
    pagination: PaginationInfo
    result_count: int
    results: List[dict]
    counts_by_scope: dict


class DocumentGroupDetail(BaseModel):
    document_group: dict
    files: List[dict]
    extraction_summary: Optional[dict] = None


# ============================================================================
# Utility Functions
# ============================================================================


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def process_rows(rows):
    """Process database rows to convert Decimal to float."""
    result = []
    for row in rows:
        processed = {}
        for key, value in row.items():
            processed[key] = decimal_to_float(value)
        result.append(processed)
    return result


# ============================================================================
# Search Functions (imported from CLI scripts logic)
# ============================================================================


def search_dimensions_db(
    conn,
    value=None,
    tolerance=None,
    min_val=None,
    max_val=None,
    unit=None,
    label=None,
    dimension_type=None,
    limit=100,
    offset=0,
):
    """Search extracted_dimensions table."""
    conditions = []
    params = []

    if value is not None:
        if tolerance is not None:
            conditions.append("ed.value BETWEEN %s AND %s")
            params.extend([value - tolerance, value + tolerance])
        else:
            conditions.append("ed.value = %s")
            params.append(value)

    if min_val is not None:
        conditions.append("ed.value >= %s")
        params.append(min_val)
    if max_val is not None:
        conditions.append("ed.value <= %s")
        params.append(max_val)

    if unit:
        conditions.append("LOWER(ed.unit) = LOWER(%s)")
        params.append(unit)

    if label:
        label_pattern = label.replace("*", "%") if "*" in label else f"%{label}%"
        conditions.append("ed.label ILIKE %s")
        params.append(label_pattern)

    if dimension_type:
        conditions.append("ed.dimension_type = %s::dimension_type")
        params.append(dimension_type)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    query = f"""
        WITH matching_dimensions AS (
            SELECT 
                ed.id AS dimension_id, ed.value, ed.unit, ed.tolerance_plus, ed.tolerance_minus,
                ed.tolerance_type, ed.label, ed.dimension_type, ed.layer, ed.source_page,
                ed.cloud_file_id, em.id AS metadata_id
            FROM extracted_dimensions ed
            JOIN extracted_metadata em ON ed.metadata_id = em.id
            WHERE {where_clause}
            ORDER BY ed.value LIMIT %s OFFSET %s
        ),
        dimension_files AS (
            SELECT DISTINCT md.*, cf."ID" AS file_id, cf."Type" AS file_type,
                cf."FullPath" AS file_path, cf."Filename" AS filename, cf.document_group_id,
                dg.id AS group_id, dg.name AS group_name, dg.project_code, dg.item_number
            FROM matching_dimensions md
            JOIN "CloudFiles" cf ON md.cloud_file_id = cf."ID"
            LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
        )
        SELECT * FROM dimension_files ORDER BY group_id NULLS LAST, file_id
    """
    params.extend([limit, offset])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = process_rows(cur.fetchall())

        count_query = f"""
            SELECT COUNT(*) FROM extracted_dimensions ed
            JOIN extracted_metadata em ON ed.metadata_id = em.id WHERE {where_clause}
        """
        cur.execute(count_query, params[:-2])
        total = cur.fetchone()["count"]

    # Group results
    groups = {}
    for row in rows:
        group_id = row["group_id"] or f"ungrouped_{row['file_id']}"
        if group_id not in groups:
            groups[group_id] = {
                "document_group": {
                    "id": row["group_id"],
                    "name": row["group_name"],
                    "project_code": row["project_code"],
                    "item_number": row["item_number"],
                }
                if row["group_id"]
                else None,
                "files": {},
                "matches": [],
            }

        file_id = row["file_id"]
        if file_id not in groups[group_id]["files"]:
            groups[group_id]["files"][file_id] = {
                "id": file_id,
                "type": row["file_type"],
                "path": row["file_path"],
                "filename": row["filename"],
                "match_details": [],
            }

        match_detail = {
            "dimension_id": row["dimension_id"],
            "value": row["value"],
            "unit": row["unit"],
            "label": row["label"],
            "dimension_type": row["dimension_type"],
            "layer": row["layer"],
            "page": row["source_page"],
        }
        if row["tolerance_plus"] or row["tolerance_minus"]:
            match_detail["tolerance"] = {
                "plus": row["tolerance_plus"],
                "minus": row["tolerance_minus"],
                "type": row["tolerance_type"],
            }
        groups[group_id]["files"][file_id]["match_details"].append(match_detail)

    results = []
    for group_data in groups.values():
        group_data["files"] = list(group_data["files"].values())
        results.append(group_data)

    return {
        "query": {
            "type": "dimension",
            "value": value,
            "tolerance": tolerance,
            "min": min_val,
            "max": max_val,
            "unit": unit,
            "label": label,
            "dimension_type": dimension_type,
        },
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "result_count": len(results),
        "results": results,
    }


def search_parameters_db(
    conn,
    name=None,
    value=None,
    numeric_min=None,
    numeric_max=None,
    category=None,
    designated_only=False,
    limit=100,
    offset=0,
):
    """Search extracted_parameters table."""
    conditions = []
    params = []

    if name:
        name_pattern = name.replace("*", "%") if "*" in name else name
        if "*" in name or "%" in name:
            conditions.append("ep.name ILIKE %s")
        else:
            conditions.append("LOWER(ep.name) = LOWER(%s)")
        params.append(name_pattern)

    if value:
        value_pattern = value.replace("*", "%") if "*" in value else f"%{value}%"
        conditions.append("ep.value ILIKE %s")
        params.append(value_pattern)

    if numeric_min is not None:
        conditions.append("ep.value_numeric >= %s")
        params.append(numeric_min)
    if numeric_max is not None:
        conditions.append("ep.value_numeric <= %s")
        params.append(numeric_max)

    if category:
        conditions.append("LOWER(ep.category) = LOWER(%s)")
        params.append(category)

    if designated_only:
        conditions.append("ep.is_designated = TRUE")

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    query = f"""
        WITH matching_params AS (
            SELECT ep.id AS param_id, ep.name, ep.value, ep.value_numeric, ep.value_type,
                ep.category, ep.is_designated, ep.units, em.id AS metadata_id, em.cloud_file_id
            FROM extracted_parameters ep
            JOIN extracted_metadata em ON ep.metadata_id = em.id
            WHERE {where_clause}
            ORDER BY ep.name, ep.value LIMIT %s OFFSET %s
        ),
        param_files AS (
            SELECT mp.*, cf."ID" AS file_id, cf."Type" AS file_type, cf."FullPath" AS file_path,
                cf."Filename" AS filename, cf.document_group_id, dg.id AS group_id,
                dg.name AS group_name, dg.project_code, dg.item_number
            FROM matching_params mp
            LEFT JOIN "CloudFiles" cf ON mp.cloud_file_id = cf."ID"
            LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
        )
        SELECT * FROM param_files ORDER BY group_id NULLS LAST, file_id NULLS LAST
    """
    params.extend([limit, offset])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = process_rows(cur.fetchall())

        count_query = f"""
            SELECT COUNT(*) FROM extracted_parameters ep
            JOIN extracted_metadata em ON ep.metadata_id = em.id WHERE {where_clause}
        """
        cur.execute(count_query, params[:-2])
        total = cur.fetchone()["count"]

    groups = {}
    for row in rows:
        group_id = row["group_id"] or f"ungrouped_{row['file_id'] or 'none'}"
        if group_id not in groups:
            groups[group_id] = {
                "document_group": {
                    "id": row["group_id"],
                    "name": row["group_name"],
                    "project_code": row["project_code"],
                    "item_number": row["item_number"],
                }
                if row["group_id"]
                else None,
                "files": {},
                "parameters": [],
            }

        file_id = row["file_id"]
        if file_id and file_id not in groups[group_id]["files"]:
            groups[group_id]["files"][file_id] = {
                "id": file_id,
                "type": row["file_type"],
                "path": row["file_path"],
                "filename": row["filename"],
                "match_details": [],
            }

        param_match = {
            "param_id": row["param_id"],
            "name": row["name"],
            "value": row["value"],
            "value_numeric": row["value_numeric"],
            "value_type": row["value_type"],
            "category": row["category"],
            "is_designated": row["is_designated"],
            "units": row["units"],
        }
        if file_id and file_id in groups[group_id]["files"]:
            groups[group_id]["files"][file_id]["match_details"].append(param_match)
        groups[group_id]["parameters"].append(param_match)

    results = []
    for group_data in groups.values():
        group_data["files"] = list(group_data["files"].values())
        results.append(group_data)

    return {
        "query": {
            "type": "parameter",
            "name": name,
            "value": value,
            "numeric_min": numeric_min,
            "numeric_max": numeric_max,
            "category": category,
            "designated_only": designated_only,
        },
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "result_count": len(results),
        "results": results,
    }


def search_materials_db(
    conn,
    material=None,
    spec=None,
    finish=None,
    thickness_min=None,
    thickness_max=None,
    similarity_threshold=0.3,
    limit=100,
    offset=0,
):
    """Search extracted_materials table with fuzzy matching."""
    conditions = []
    params = []

    if material:
        if "*" in material or "%" in material:
            pattern = material.replace("*", "%")
            conditions.append("emat.material_name ILIKE %s")
            params.append(pattern)
        else:
            conditions.append(
                f"(emat.material_name ILIKE %s OR similarity(emat.material_name, %s) > %s)"
            )
            params.extend([f"%{material}%", material, similarity_threshold])

    if spec:
        spec_pattern = spec.replace("*", "%") if "*" in spec else f"%{spec}%"
        conditions.append("emat.material_spec ILIKE %s")
        params.append(spec_pattern)

    if finish:
        conditions.append("emat.finish ILIKE %s")
        params.append(f"%{finish}%")

    if thickness_min is not None:
        conditions.append("emat.thickness >= %s")
        params.append(thickness_min)
    if thickness_max is not None:
        conditions.append("emat.thickness <= %s")
        params.append(thickness_max)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    query = f"""
        WITH matching_materials AS (
            SELECT emat.id AS material_id, emat.material_name, emat.material_spec, emat.finish,
                emat.thickness, emat.thickness_unit, emat.properties, 1.0 AS similarity_score,
                em.id AS metadata_id, em.cloud_file_id
            FROM extracted_materials emat
            JOIN extracted_metadata em ON emat.metadata_id = em.id
            WHERE {where_clause}
            ORDER BY emat.material_name LIMIT %s OFFSET %s
        ),
        material_files AS (
            SELECT mm.*, cf."ID" AS file_id, cf."Type" AS file_type, cf."FullPath" AS file_path,
                cf."Filename" AS filename, cf.document_group_id, dg.id AS group_id,
                dg.name AS group_name, dg.project_code, dg.item_number
            FROM matching_materials mm
            LEFT JOIN "CloudFiles" cf ON mm.cloud_file_id = cf."ID"
            LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
        )
        SELECT * FROM material_files ORDER BY group_id NULLS LAST
    """
    params.extend([limit, offset])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = process_rows(cur.fetchall())

        count_query = f"""
            SELECT COUNT(*) FROM extracted_materials emat
            JOIN extracted_metadata em ON emat.metadata_id = em.id WHERE {where_clause}
        """
        cur.execute(count_query, params[:-2])
        total = cur.fetchone()["count"]

    groups = {}
    for row in rows:
        group_id = row["group_id"] or f"ungrouped_{row['file_id']}"
        if group_id not in groups:
            groups[group_id] = {
                "document_group": {
                    "id": row["group_id"],
                    "name": row["group_name"],
                    "project_code": row["project_code"],
                    "item_number": row["item_number"],
                }
                if row["group_id"]
                else None,
                "files": {},
                "materials": [],
            }

        file_id = row["file_id"]
        if file_id and file_id not in groups[group_id]["files"]:
            groups[group_id]["files"][file_id] = {
                "id": file_id,
                "type": row["file_type"],
                "path": row["file_path"],
                "filename": row["filename"],
                "match_details": [],
            }

        material_match = {
            "material_id": row["material_id"],
            "material_name": row["material_name"],
            "material_spec": row["material_spec"],
            "finish": row["finish"],
            "thickness": row["thickness"],
            "thickness_unit": row["thickness_unit"],
            "properties": row["properties"],
            "similarity_score": row["similarity_score"],
        }
        if file_id and file_id in groups[group_id]["files"]:
            groups[group_id]["files"][file_id]["match_details"].append(material_match)
        groups[group_id]["materials"].append(material_match)

    results = []
    for group_data in groups.values():
        group_data["files"] = list(group_data["files"].values())
        results.append(group_data)

    return {
        "query": {
            "type": "material",
            "material": material,
            "spec": spec,
            "finish": finish,
            "thickness_min": thickness_min,
            "thickness_max": thickness_max,
            "similarity_threshold": similarity_threshold,
        },
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "result_count": len(results),
        "results": results,
    }


def search_projects_db(conn, code, include_stats=False, limit=100, offset=0):
    """Search by project code."""
    if "*" in code or "%" in code:
        code_pattern = code.replace("*", "%")
        code_condition = "dg.project_code ILIKE %s"
        code_param = code_pattern
    else:
        code_condition = "dg.project_code = %s"
        code_param = code

    query = f"""
        WITH matching_groups AS (
            SELECT dg.id, dg.name, dg.project_code, dg.item_number, dg.description,
                dg.linking_method, dg.linking_confidence, dg.needs_review, dg.created_at
            FROM document_groups dg WHERE {code_condition}
            ORDER BY dg.name LIMIT %s OFFSET %s
        ),
        group_members AS (
            SELECT mg.*, dgm.id AS member_id, dgm.role, dgm.is_primary, dgm.cloud_file_id,
                cf."ID" AS file_id, cf."Type" AS file_type, cf."FullPath" AS file_path,
                cf."Filename" AS filename, cf."Size" AS file_size, cf.extraction_status
            FROM matching_groups mg
            JOIN document_group_members dgm ON mg.id = dgm.group_id
            LEFT JOIN "CloudFiles" cf ON dgm.cloud_file_id = cf."ID"
        )
        SELECT * FROM group_members ORDER BY id, role, filename
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, [code_param, limit, offset])
        rows = process_rows(cur.fetchall())

        count_query = f"SELECT COUNT(DISTINCT id) FROM document_groups dg WHERE {code_condition}"
        cur.execute(count_query, [code_param])
        total_groups = cur.fetchone()["count"]

        stats = None
        if include_stats:
            stats_query = f"""
                SELECT COUNT(DISTINCT dg.id) AS group_count, COUNT(DISTINCT cf."ID") AS file_count,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf."Type" = 'pdf') AS pdf_count,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf."Type" = 'dxf') AS dxf_count,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf."Type" IN ('prt', 'asm')) AS cad_count,
                    SUM(cf."Size") AS total_size,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf.extraction_status = 'completed') AS extracted_count,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf.extraction_status = 'pending') AS pending_count
                FROM document_groups dg
                LEFT JOIN document_group_members dgm ON dg.id = dgm.group_id
                LEFT JOIN "CloudFiles" cf ON dgm.cloud_file_id = cf."ID"
                WHERE {code_condition}
            """
            cur.execute(stats_query, [code_param])
            stats_row = cur.fetchone()
            stats = {
                "group_count": stats_row["group_count"],
                "file_count": stats_row["file_count"],
                "by_type": {
                    "pdf": stats_row["pdf_count"],
                    "dxf": stats_row["dxf_count"],
                    "cad": stats_row["cad_count"],
                },
                "total_size_bytes": decimal_to_float(stats_row["total_size"]),
                "extraction": {
                    "completed": stats_row["extracted_count"],
                    "pending": stats_row["pending_count"],
                },
            }

    groups = {}
    for row in rows:
        group_id = row["id"]
        if group_id not in groups:
            groups[group_id] = {
                "document_group": {
                    "id": row["id"],
                    "name": row["name"],
                    "project_code": row["project_code"],
                    "item_number": row["item_number"],
                    "description": row["description"],
                    "linking_method": row["linking_method"],
                    "linking_confidence": row["linking_confidence"],
                    "needs_review": row["needs_review"],
                    "created_at": row["created_at"],
                },
                "files": [],
                "primary_file": None,
            }

        if row["file_id"]:
            file_info = {
                "id": row["file_id"],
                "type": row["file_type"],
                "path": row["file_path"],
                "filename": row["filename"],
                "size": row["file_size"],
                "role": row["role"],
                "extraction_status": row["extraction_status"],
            }
            groups[group_id]["files"].append(file_info)
            if row["is_primary"]:
                groups[group_id]["primary_file"] = file_info

    results = list(groups.values())
    response = {
        "query": {"type": "project", "code": code},
        "pagination": {"limit": limit, "offset": offset, "total": total_groups},
        "result_count": len(results),
        "results": results,
    }
    if stats:
        response["statistics"] = stats

    return response


def search_fulltext_db(conn, query_text, scope="all", limit=100, offset=0):
    """Full-text search across extracted data."""
    # Prepare tsquery
    if " | " in query_text:
        terms = [t.strip() for t in query_text.split("|")]
        ts_query = " | ".join(f"'{t}':*" for t in terms if t)
    else:
        terms = query_text.split()
        ts_query = " & ".join(f"'{t}':*" for t in terms if t)

    results_by_scope = {}
    total_matches = 0

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if scope in ("all", "materials"):
            cur.execute(
                """
                SELECT emat.id AS match_id, 'material' AS match_type, emat.material_name AS matched_text,
                    ts_rank(to_tsvector('english', COALESCE(emat.material_name, '') || ' ' || COALESCE(emat.material_spec, '')),
                        to_tsquery('english', %s)) AS rank,
                    emat.material_name, emat.material_spec, emat.finish, em.cloud_file_id,
                    cf."ID" AS file_id, cf."Type" AS file_type, cf."FullPath" AS file_path, cf."Filename" AS filename,
                    dg.id AS group_id, dg.name AS group_name, dg.project_code, dg.item_number
                FROM extracted_materials emat
                JOIN extracted_metadata em ON emat.metadata_id = em.id
                LEFT JOIN "CloudFiles" cf ON em.cloud_file_id = cf."ID"
                LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
                WHERE to_tsvector('english', COALESCE(emat.material_name, '') || ' ' || COALESCE(emat.material_spec, ''))
                      @@ to_tsquery('english', %s)
                ORDER BY rank DESC LIMIT %s OFFSET %s
            """,
                [ts_query, ts_query, limit, offset],
            )
            results_by_scope["materials"] = process_rows(cur.fetchall())

            cur.execute(
                """
                SELECT COUNT(*) FROM extracted_materials emat
                WHERE to_tsvector('english', COALESCE(material_name, '') || ' ' || COALESCE(material_spec, ''))
                      @@ to_tsquery('english', %s)
            """,
                [ts_query],
            )
            total_matches += cur.fetchone()["count"]

        if scope in ("all", "parameters"):
            cur.execute(
                """
                SELECT ep.id AS match_id, 'parameter' AS match_type, ep.name || '=' || ep.value AS matched_text,
                    ts_rank(to_tsvector('english', ep.name || ' ' || ep.value), to_tsquery('english', %s)) AS rank,
                    ep.name AS param_name, ep.value AS param_value, ep.category, em.cloud_file_id,
                    cf."ID" AS file_id, cf."Type" AS file_type, cf."FullPath" AS file_path, cf."Filename" AS filename,
                    dg.id AS group_id, dg.name AS group_name, dg.project_code, dg.item_number
                FROM extracted_parameters ep
                JOIN extracted_metadata em ON ep.metadata_id = em.id
                LEFT JOIN "CloudFiles" cf ON em.cloud_file_id = cf."ID"
                LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
                WHERE to_tsvector('english', ep.name || ' ' || ep.value) @@ to_tsquery('english', %s)
                ORDER BY rank DESC LIMIT %s OFFSET %s
            """,
                [ts_query, ts_query, limit, offset],
            )
            results_by_scope["parameters"] = process_rows(cur.fetchall())

            cur.execute(
                """
                SELECT COUNT(*) FROM extracted_parameters ep
                WHERE to_tsvector('english', name || ' ' || value) @@ to_tsquery('english', %s)
            """,
                [ts_query],
            )
            total_matches += cur.fetchone()["count"]

        if scope in ("all", "dimensions"):
            cur.execute(
                """
                SELECT ed.id AS match_id, 'dimension' AS match_type, ed.label AS matched_text,
                    ts_rank(to_tsvector('english', COALESCE(ed.label, '')), to_tsquery('english', %s)) AS rank,
                    ed.value, ed.unit, ed.label, ed.dimension_type, em.cloud_file_id,
                    cf."ID" AS file_id, cf."Type" AS file_type, cf."FullPath" AS file_path, cf."Filename" AS filename,
                    dg.id AS group_id, dg.name AS group_name, dg.project_code, dg.item_number
                FROM extracted_dimensions ed
                JOIN extracted_metadata em ON ed.metadata_id = em.id
                LEFT JOIN "CloudFiles" cf ON em.cloud_file_id = cf."ID"
                LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
                WHERE ed.label IS NOT NULL AND to_tsvector('english', ed.label) @@ to_tsquery('english', %s)
                ORDER BY rank DESC LIMIT %s OFFSET %s
            """,
                [ts_query, ts_query, limit, offset],
            )
            results_by_scope["dimensions"] = process_rows(cur.fetchall())

            cur.execute(
                """
                SELECT COUNT(*) FROM extracted_dimensions ed
                WHERE label IS NOT NULL AND to_tsvector('english', label) @@ to_tsquery('english', %s)
            """,
                [ts_query],
            )
            total_matches += cur.fetchone()["count"]

    all_matches = []
    for scope_name, matches in results_by_scope.items():
        for match in matches:
            all_matches.append(
                {
                    "match_type": scope_name,
                    "match_id": match["match_id"],
                    "matched_text": match["matched_text"],
                    "relevance_score": float(match["rank"]) if match["rank"] else 0,
                    "document_group": {
                        "id": match["group_id"],
                        "name": match["group_name"],
                        "project_code": match["project_code"],
                        "item_number": match["item_number"],
                    }
                    if match["group_id"]
                    else None,
                    "file": {
                        "id": match["file_id"],
                        "type": match["file_type"],
                        "path": match["file_path"],
                        "filename": match["filename"],
                    }
                    if match["file_id"]
                    else None,
                    "match_details": {
                        k: v
                        for k, v in match.items()
                        if k
                        not in (
                            "match_id",
                            "match_type",
                            "matched_text",
                            "rank",
                            "group_id",
                            "group_name",
                            "project_code",
                            "item_number",
                            "file_id",
                            "file_type",
                            "file_path",
                            "filename",
                            "cloud_file_id",
                        )
                    },
                }
            )

    all_matches.sort(key=lambda x: x["relevance_score"], reverse=True)

    return {
        "query": {"type": "fulltext", "text": query_text, "tsquery": ts_query, "scope": scope},
        "pagination": {"limit": limit, "offset": offset, "total": total_matches},
        "result_count": len(all_matches),
        "results": all_matches,
        "counts_by_scope": {
            scope_name: len(matches) for scope_name, matches in results_by_scope.items()
        },
    }


def get_document_group_detail(conn, group_id: int):
    """Get full details of a DocumentGroup with all members."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get group info
        cur.execute(
            """
            SELECT id, name, project_code, item_number, description, linking_method,
                linking_confidence, needs_review, created_at, updated_at
            FROM document_groups WHERE id = %s
        """,
            [group_id],
        )
        group = cur.fetchone()

        if not group:
            return None

        # Get members
        cur.execute(
            """
            SELECT dgm.id AS member_id, dgm.role, dgm.is_primary, dgm.created_at AS member_created_at,
                cf."ID" AS file_id, cf."Type" AS file_type, cf."FullPath" AS file_path,
                cf."Filename" AS filename, cf."Size" AS file_size, cf.extraction_status
            FROM document_group_members dgm
            LEFT JOIN "CloudFiles" cf ON dgm.cloud_file_id = cf."ID"
            WHERE dgm.group_id = %s
            ORDER BY dgm.is_primary DESC, dgm.role, cf."Filename"
        """,
            [group_id],
        )
        members = process_rows(cur.fetchall())

        # Get extraction summary
        cur.execute(
            """
            SELECT COUNT(DISTINCT em.id) AS extracted_files,
                SUM(em.dimension_count) AS total_dimensions,
                SUM(em.parameter_count) AS total_parameters,
                SUM(CASE WHEN em.has_bom THEN 1 ELSE 0 END) AS files_with_bom
            FROM document_group_members dgm
            JOIN extracted_metadata em ON dgm.cloud_file_id = em.cloud_file_id
            WHERE dgm.group_id = %s
        """,
            [group_id],
        )
        summary = cur.fetchone()

    return {
        "document_group": process_rows([group])[0],
        "files": members,
        "extraction_summary": {
            "extracted_files": summary["extracted_files"],
            "total_dimensions": decimal_to_float(summary["total_dimensions"]),
            "total_parameters": decimal_to_float(summary["total_parameters"]),
            "files_with_bom": summary["files_with_bom"],
        },
    }


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Engineering Document Search API",
    description="""
    Search API for the Unified Engineering Document Intelligence Platform.
    
    Provides specialized search endpoints for:
    - **Dimensions**: Search by value, tolerance, unit, or label
    - **Parameters**: Search CAD parameters by name, value, or category
    - **Materials**: Fuzzy search for material specifications
    - **Projects**: Find all documents for a project code
    - **Full-text**: Search across all extracted data
    
    All endpoints return results grouped by DocumentGroup with associated files.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/", tags=["Health"])
async def root():
    """API health check."""
    return {"status": "healthy", "service": "Engineering Document Search API", "version": "1.0.0"}


@app.get("/api/search/dimensions", response_model=DimensionSearchResponse, tags=["Search"])
async def search_dimensions(
    value: Optional[float] = Query(None, description="Exact dimension value to search"),
    tolerance: Optional[float] = Query(None, description="Tolerance around value (+/-)"),
    min: Optional[float] = Query(None, alias="min", description="Minimum dimension value"),
    max: Optional[float] = Query(None, alias="max", description="Maximum dimension value"),
    unit: Optional[str] = Query(None, description="Unit filter (mm, in, deg, etc.)"),
    label: Optional[str] = Query(None, description="Label pattern (supports * wildcards)"),
    type: Optional[str] = Query(None, alias="type", description="Dimension type filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    conn=Depends(get_db_connection),
):
    """Search for dimensions across extracted documents."""
    if value is None and min is None and max is None and label is None:
        raise HTTPException(status_code=400, detail="At least one search criterion required")

    return search_dimensions_db(
        conn,
        value=value,
        tolerance=tolerance,
        min_val=min,
        max_val=max,
        unit=unit,
        label=label,
        dimension_type=type,
        limit=limit,
        offset=offset,
    )


@app.get("/api/search/parameters", response_model=ParameterSearchResponse, tags=["Search"])
async def search_parameters(
    name: Optional[str] = Query(None, description="Parameter name (supports * wildcards)"),
    value: Optional[str] = Query(None, description="Parameter value (supports * wildcards)"),
    numeric_min: Optional[float] = Query(None, description="Minimum numeric value"),
    numeric_max: Optional[float] = Query(None, description="Maximum numeric value"),
    category: Optional[str] = Query(None, description="Category filter"),
    designated: bool = Query(False, description="Show only designated parameters"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    conn=Depends(get_db_connection),
):
    """Search for CAD parameters across extracted documents."""
    if not any(
        [name, value, numeric_min is not None, numeric_max is not None, category, designated]
    ):
        raise HTTPException(status_code=400, detail="At least one search criterion required")

    return search_parameters_db(
        conn,
        name=name,
        value=value,
        numeric_min=numeric_min,
        numeric_max=numeric_max,
        category=category,
        designated_only=designated,
        limit=limit,
        offset=offset,
    )


@app.get("/api/search/materials", response_model=MaterialSearchResponse, tags=["Search"])
async def search_materials(
    material: Optional[str] = Query(None, description="Material name (fuzzy match)"),
    spec: Optional[str] = Query(None, description="Material specification"),
    finish: Optional[str] = Query(None, description="Surface finish"),
    thickness_min: Optional[float] = Query(None, description="Minimum thickness"),
    thickness_max: Optional[float] = Query(None, description="Maximum thickness"),
    threshold: float = Query(0.3, ge=0, le=1, description="Similarity threshold"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    conn=Depends(get_db_connection),
):
    """Search for materials with fuzzy matching."""
    if not any([material, spec, finish, thickness_min is not None, thickness_max is not None]):
        raise HTTPException(status_code=400, detail="At least one search criterion required")

    return search_materials_db(
        conn,
        material=material,
        spec=spec,
        finish=finish,
        thickness_min=thickness_min,
        thickness_max=thickness_max,
        similarity_threshold=threshold,
        limit=limit,
        offset=offset,
    )


@app.get("/api/search/projects", response_model=ProjectSearchResponse, tags=["Search"])
async def search_projects(
    code: str = Query(..., description="Project code (supports * wildcards)"),
    stats: bool = Query(False, description="Include file statistics"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    conn=Depends(get_db_connection),
):
    """Search by project code to find all DocumentGroups and files."""
    return search_projects_db(conn, code=code, include_stats=stats, limit=limit, offset=offset)


@app.get("/api/search/fulltext", response_model=FulltextSearchResponse, tags=["Search"])
async def search_fulltext(
    q: str = Query(..., description="Search query (use | for OR)"),
    scope: str = Query(
        "all",
        description="Search scope",
        enum=["all", "materials", "parameters", "dimensions", "bom"],
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per scope"),
    offset: int = Query(0, ge=0, description="Result offset"),
    conn=Depends(get_db_connection),
):
    """Full-text search across all extracted data."""
    return search_fulltext_db(conn, query_text=q, scope=scope, limit=limit, offset=offset)


@app.get("/api/groups/{group_id}", response_model=DocumentGroupDetail, tags=["Documents"])
async def get_document_group(group_id: int, conn=Depends(get_db_connection)):
    """Get full details of a DocumentGroup with all members."""
    result = get_document_group_detail(conn, group_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"DocumentGroup {group_id} not found")
    return result


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
