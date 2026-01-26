"""
Creo Genome Extractor Service.

Extends existing Creo gRPC extraction to include:
- B-Rep topology (face adjacency graphs with UV grids)
- Point cloud extraction from tessellation
- DeepSDF training data (multi-resolution SDF sampling)

Integrates with existing D2-creo-extraction-worker.py workflow.
"""

import asyncio
import json
import logging
import struct
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from pybase.core.logging import get_logger

logger = get_logger(__name__)


class CreoFileType(Enum):
    """Creo file types."""
    PART = "prt"
    ASSEMBLY = "asm"
    DRAWING = "drw"


@dataclass
class BRepFace:
    """Single face in B-Rep topology."""
    face_id: int
    surface_type: str  # plane, cylinder, cone, sphere, torus, spline, nurbs
    area: float
    normal: list[float]  # Average normal vector
    centroid: list[float]  # Face center point
    uv_bounds: dict[str, float]  # {u_min, u_max, v_min, v_max}
    neighboring_faces: list[int]  # Adjacent face IDs
    edge_count: int
    convexity: list[str]  # "convex", "concave", "tangent" per edge


@dataclass
class BRepGraph:
    """Face adjacency graph for B-Rep topology."""
    nodes: list[BRepFace]
    edges: list[dict]  # {face_1, face_2, convexity, length, curve_type}

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "nodes": [
                {
                    "face_id": f.face_id,
                    "surface_type": f.surface_type,
                    "area": f.area,
                    "normal": f.normal,
                    "centroid": f.centroid,
                    "uv_bounds": f.uv_bounds,
                    "neighboring_faces": f.neighboring_faces,
                    "edge_count": f.edge_count,
                    "convexity": f.convexity,
                }
                for f in self.nodes
            ],
            "edges": self.edges,
            "num_faces": len(self.nodes),
            "num_edges": len(self.edges),
        }


@dataclass
class PointCloudData:
    """Point cloud extracted from Creo tessellation."""
    points: list[list[float]]  # Nx3 array
    normals: list[list[float]] | None = None  # Nx3 array, optional
    colors: list[list[int]] | None = None  # Nx3 array, optional

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "points": self.points,
            "normals": self.normals,
            "colors": self.colors,
            "count": len(self.points),
        }


@dataclass
class SDFSample:
    """Single signed distance field sample."""
    position: list[float]  # [x, y, z]
    sdf_value: float  # Positive outside, negative inside
    normal: list[float] | None = None  # Surface normal at closest point


@dataclass
class DeepSDFTrainingData:
    """Training data for DeepSDF implicit representation."""
    surface_samples: list[SDFSample]  # Points on surface (sdf=0)
    near_surface_samples: list[SDFSample]  # Points near surface
    volume_samples: list[SDFSample]  # Uniform volume samples
    bounding_box: dict[str, list[float]]  # {min: [x,y,z], max: [x,y,z]}

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "surface_samples": [
                {
                    "position": s.position,
                    "sdf_value": s.sdf_value,
                    "normal": s.normal,
                }
                for s in self.surface_samples
            ],
            "near_surface_samples": [
                {
                    "position": s.position,
                    "sdf_value": s.sdf_value,
                }
                for s in self.near_surface_samples
            ],
            "volume_samples": [
                {
                    "position": s.position,
                    "sdf_value": s.sdf_value,
                }
                for s in self.volume_samples
            ],
            "bounding_box": self.bounding_box,
            "num_surface": len(self.surface_samples),
            "num_near_surface": len(self.near_surface_samples),
            "num_volume": len(self.volume_samples),
        }


@dataclass
class CreoGenomeExtractionResult:
    """Complete genome extraction result."""
    file_name: str
    file_type: str
    extracted_at: str

    # B-Rep genome
    brep_graph: BRepGraph | None = None
    face_count: int = 0
    edge_count: int = 0
    vertex_count: int = 0

    # Point cloud
    point_cloud: PointCloudData | None = None

    # DeepSDF training data
    deepsdf_data: DeepSDFTrainingData | None = None

    # Mass properties
    mass_properties: dict | None = None

    # BOM (for assemblies)
    bom: list[dict] | None = None

    # Feature tree
    feature_tree: list[dict] | None = None

    # Errors
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "extracted_at": self.extracted_at,
            "face_count": self.face_count,
            "edge_count": self.edge_count,
            "vertex_count": self.vertex_count,
        }

        if self.brep_graph:
            result["brep_graph"] = self.brep_graph.to_dict()

        if self.point_cloud:
            result["point_cloud"] = self.point_cloud.to_dict()

        if self.deepsdf_data:
            result["deepsdf_data"] = self.deepsdf_data.to_dict()

        if self.mass_properties:
            result["mass_properties"] = self.mass_properties

        if self.bom:
            result["bom"] = self.bom

        if self.feature_tree:
            result["feature_tree"] = self.feature_tree

        if self.errors:
            result["errors"] = self.errors

        if self.warnings:
            result["warnings"] = self.warnings

        return result


class CreoGenomeExtractor:
    """
    Extract geometric genome from Creo CAD models via gRPC.

    This service extends the existing D2-creo-extraction-worker.py
    to add B-Rep topology, point clouds, and DeepSDF training data.

    Usage:
        extractor = CreoGenomeExtractor(creo_grpc_address="localhost:50051")
        result = await extractor.extract_file("/path/to/model.prt")
    """

    def __init__(
        self,
        creo_grpc_address: str = "localhost:50051",
        creo_timeout_sec: int = 300,
    ):
        """
        Initialize extractor.

        Args:
            creo_grpc_address: gRPC server address for Creo service
            creo_timeout_sec: Timeout for Creo operations
        """
        self.creo_address = creo_grpc_address
        self.creo_timeout = creo_timeout_sec
        self._grpc_client: Any = None

    async def _get_grpc_client(self) -> Any:
        """
        Get or create gRPC client for Creo.

        This is a placeholder - actual implementation depends on
        your gRPC proto definitions for Creo service.
        """
        if self._grpc_client is None:
            # TODO: Import actual gRPC client
            # from your_creo_proto_pb2_grpc import CreoServiceStub
            # from your_creo_proto_pb2 import ExtractRequest
            # import grpc
            # channel = grpc.aio.insecure_channel(self.creo_address)
            # self._grpc_client = CreoServiceStub(channel)
            pass
        return self._grpc_client

    async def extract_file(
        self,
        file_path: str,
        extract_brep_graph: bool = True,
        extract_point_cloud: bool = True,
        extract_deepsdf: bool = False,
        point_cloud_size: int = 2048,
    ) -> CreoGenomeExtractionResult:
        """
        Extract genome from Creo CAD file.

        Args:
            file_path: Path to .prt or .asm file
            extract_brep_graph: Extract face adjacency graph
            extract_point_cloud: Extract point cloud from tessellation
            extract_deepsdf: Generate DeepSDF training samples
            point_cloud_size: Number of points in point cloud

        Returns:
            CreoGenomeExtractionResult with extracted data
        """
        path = Path(file_path)
        file_type = path.suffix.lstrip(".").lower()

        result = CreoGenomeExtractionResult(
            file_name=path.name,
            file_type=file_type,
            extracted_at=datetime.now(timezone.utc).isoformat(),
        )

        # Detect file type
        if file_type == "prt":
            creo_type = CreoFileType.PART
        elif file_type == "asm":
            creo_type = CreoFileType.ASSEMBLY
        else:
            result.errors.append(f"Unsupported file type: {file_type}")
            return result

        try:
            # Get gRPC client
            client = await self._get_grpc_client()

            # Check if this is using existing JSON data or live extraction
            # For now, we'll implement the parsing logic for extracted data

            # Step 1: Extract B-Rep topology
            if extract_brep_graph:
                try:
                    result.brep_graph = await self._extract_brep_graph(
                        file_path, client
                    )
                    result.face_count = len(result.brep_graph.nodes)
                    result.edge_count = result.brep_graph.num_edges
                    result.warnings.append(
                        f"B-Rep graph: {result.face_count} faces, "
                        f"{result.edge_count} edges"
                    )
                except Exception as e:
                    result.errors.append(f"B-Rep extraction failed: {e}")
                    logger.warning(f"B-Rep extraction failed: {e}")

            # Step 2: Extract point cloud
            if extract_point_cloud:
                try:
                    result.point_cloud = await self._extract_point_cloud(
                        file_path, client, point_cloud_size
                    )
                    result.warnings.append(
                        f"Point cloud: {result.point_cloud.count} points"
                    )
                except Exception as e:
                    result.errors.append(f"Point cloud extraction failed: {e}")
                    logger.warning(f"Point cloud extraction failed: {e}")

            # Step 3: Generate DeepSDF training data
            if extract_deepsdf:
                try:
                    result.deepsdf_data = await self._generate_deepsdf_data(
                        file_path, client, result.point_cloud
                    )
                    result.warnings.append(
                        f"DeepSDF data: {result.deepsdf_data.num_surface} surface, "
                        f"{result.deepsdf_data.num_near_surface} near-surface, "
                        f"{result.deepsdf_data.num_volume} volume samples"
                    )
                except Exception as e:
                    result.errors.append(f"DeepSDF generation failed: {e}")
                    logger.warning(f"DeepSDF generation failed: {e}")

            # Step 4: Extract mass properties
            try:
                result.mass_properties = await self._extract_mass_properties(
                    file_path, client
                )
            except Exception as e:
                result.warnings.append(f"Mass properties extraction failed: {e}")

            # Step 5: Extract BOM for assemblies
            if creo_type == CreoFileType.ASSEMBLY:
                try:
                    result.bom = await self._extract_bom(file_path, client)
                except Exception as e:
                    result.warnings.append(f"BOM extraction failed: {e}")

        except Exception as e:
            result.errors.append(f"Extraction failed: {e}")
            logger.error(f"Creo extraction failed for {file_path}: {e}")

        return result

    async def _extract_brep_graph(
        self, file_path: str, client: Any
    ) -> BRepGraph:
        """
        Extract face adjacency graph from Creo model.

        Uses Pro/TOOLKIT API to traverse B-Rep topology:
        1. Get all surfaces (faces)
        2. For each face, get neighboring faces via shared edges
        3. Classify edge convexity (convex/concave/tangent)
        4. Extract UV bounds for each surface
        """
        # Placeholder: Call actual gRPC service
        # request = ExtractBRepRequest(file_path=file_path)
        # response = await client.ExtractBRep(request, timeout=self.creo_timeout)

        # For now, return empty graph
        # When gRPC is available, parse response.brep_data

        nodes: list[BRepFace] = []
        edges: list[dict] = []

        return BRepGraph(nodes=nodes, edges=edges)

    async def _extract_point_cloud(
        self, file_path: str, client: Any, num_points: int
    ) -> PointCloudData:
        """
        Extract point cloud from Creo tessellation.

        Steps:
        1. Request tessellation data from Creo (STL or custom format)
        2. Parse vertices from triangles
        3. Sample to target number of points
        4. Normalize to unit sphere
        5. Optionally compute normals
        """
        # Placeholder: Call actual gRPC service
        # request = ExtractTessellationRequest(file_path=file_path)
        # response = await client.ExtractTessellation(request, timeout=self.creo_timeout)

        # When tessellation data is available:
        # points = self._parse_tessellation(response.tessellation_data)

        # For now, return empty point cloud
        return PointCloudData(points=[])

    def _parse_stl_tessellation(self, stl_data: bytes) -> np.ndarray:
        """
        Parse STL binary tessellation data into point cloud.

        Args:
            stl_data: Binary STL data

        Returns:
            Nx3 numpy array of vertices
        """
        buffer = memoryview(stl_data)

        # Skip 80-byte header
        if len(buffer) < 84:
            return np.array([], dtype=np.float32).reshape(0, 3)

        # Read triangle count
        num_triangles = struct.unpack('<I', buffer[80:84])[0]

        vertices = []
        offset = 84
        triangle_size = 50  # 12 normal + 12*3 vertices + 2 attribute

        for _ in range(min(num_triangles, 100000)):  # Safety limit
            if offset + triangle_size > len(buffer):
                break

            # Skip normal (12 bytes)
            # Read 3 vertices (12 bytes each)
            for _ in range(3):
                x = struct.unpack('<f', buffer[offset:offset+4])[0]
                y = struct.unpack('<f', buffer[offset+4:offset+8])[0]
                z = struct.unpack('<f', buffer[offset+8:offset+12])[0]
                vertices.append([x, y, z])
                offset += 12

            # Skip attribute (2 bytes)
            offset += 2

        if not vertices:
            return np.array([], dtype=np.float32).reshape(0, 3)

        # Remove duplicates
        points = np.unique(np.array(vertices, dtype=np.float32), axis=0)

        return points

    def _normalize_point_cloud(
        self, points: np.ndarray, target_size: int
    ) -> list[list[float]]:
        """
        Normalize point cloud to unit sphere.

        Args:
            points: Nx3 array of vertices
            target_size: Target number of points

        Returns:
            List of points (Nx3)
        """
        if len(points) == 0:
            return []

        # Center the points
        centroid = points.mean(axis=0)
        points = points - centroid

        # Scale to unit sphere
        max_dist = np.max(np.linalg.norm(points, axis=1))
        if max_dist > 0:
            points = points / max_dist

        # Sample to target size
        if len(points) > target_size:
            indices = np.random.choice(len(points), target_size, replace=False)
            points = points[indices]
        elif len(points) < target_size:
            # Upsample with jitter
            shortage = target_size - len(points)
            indices = np.random.choice(len(points), shortage, replace=True)
            jitter = np.random.normal(0, 0.01, (shortage, 3))
            extra = points[indices] + jitter
            points = np.vstack([points, extra])

        return points.tolist()

    async def _generate_deepsdf_data(
        self,
        file_path: str,
        client: Any,
        point_cloud: PointCloudData | None,
        num_surface: int = 10000,
        num_near_surface: int = 50000,
        num_volume: int = 100000,
    ) -> DeepSDFTrainingData:
        """
        Generate DeepSDF training data.

        Sampling strategy from CosCAD:
        1. Surface samples: Points on mesh surface (SDF=0)
        2. Near-surface: Uniform samples in band around surface
        3. Volume: Uniform samples in bounding box

        Note: Requires Creo geometric kernel for SDF computation.
        This is a placeholder - actual implementation needs Creo API
        for ray-surface intersection.
        """
        # Placeholder implementation

        # When Creo API available for SDF computation:
        # 1. Sample points on surface via tessellation
        # 2. For near-surface: offset along normals
        # 3. For volume: random points in bbox
        # 4. Query Creo kernel for exact SDF values

        surface_samples: list[SDFSample] = []
        near_surface_samples: list[SDFSample] = []
        volume_samples: list[SDFSample] = []

        bounding_box = {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]}

        return DeepSDFTrainingData(
            surface_samples=surface_samples,
            near_surface_samples=near_surface_samples,
            volume_samples=volume_samples,
            bounding_box=bounding_box,
        )

    async def _extract_mass_properties(
        self, file_path: str, client: Any
    ) -> dict:
        """Extract mass properties from Creo model."""
        # Placeholder: Call actual gRPC service
        return {
            "mass": 0.0,
            "volume": 0.0,
            "density": 0.0,
            "surface_area": 0.0,
            "center_of_gravity": [0.0, 0.0, 0.0],
            "inertia_tensor": [[0.0] * 3 for _ in range(3)],
        }

    async def _extract_bom(self, file_path: str, client: Any) -> list[dict]:
        """Extract bill of materials from Creo assembly."""
        # Placeholder: Call actual gRPC service
        return []

    async def extract_from_json(
        self,
        json_path: str,
    ) -> CreoGenomeExtractionResult:
        """
        Parse existing Creo extraction JSON and enhance with new fields.

        This allows processing of JSON files created by
        D3-creo-json-importer.py workflow.

        Args:
            json_path: Path to existing Creo extraction JSON

        Returns:
            Enhanced extraction result
        """
        path = Path(json_path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return CreoGenomeExtractionResult(
                file_name=path.name,
                file_type="json",
                extracted_at=datetime.now(timezone.utc).isoformat(),
                errors=[f"Failed to parse JSON: {e}"],
            )

        result = CreoGenomeExtractionResult(
            file_name=data.get("filename", path.name),
            file_type=data.get("file_type", "unknown"),
            extracted_at=data.get(
                "extraction_timestamp",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Parse existing data
        if "parameters" in data:
            result.feature_tree = [{"params": data["parameters"]}]

        if "bom" in data and data["bom"]:
            result.bom = data["bom"]

        if "mass_properties" in data:
            result.mass_properties = data["mass_properties"]

        # Check for enhanced format (v4.0-geometry)
        if "features" in data and isinstance(data["features"], list):
            result.feature_tree = data["features"]

            # Extract B-Rep graph from features
            brep_nodes = self._extract_brep_from_features(data["features"])
            if brep_nodes:
                result.brep_graph = BRepGraph(nodes=brep_nodes, edges=[])
                result.face_count = len(brep_nodes)

        # Check for point cloud data
        if "point_cloud" in data:
            pc_data = data["point_cloud"]
            result.point_cloud = PointCloudData(
                points=pc_data.get("points", []),
                normals=pc_data.get("normals"),
            )

        return result

    def _extract_brep_from_features(
        self, features: list[dict]
    ) -> list[BRepFace]:
        """
        Extract B-Rep faces from feature geometry.

        Parses the enhanced Creo JSON format to extract
        surface topology from feature_geometry.surfaces.
        """
        faces: list[BRepFace] = []
        face_id = 0

        for feature in features:
            geometry = feature.get("feature_geometry", {})
            surfaces = geometry.get("surfaces", [])

            for surf in surfaces:
                face_id += 1

                # Parse surface data
                surf_type = surf.get("surface_type", "unknown")
                area = surf.get("area", 0.0)
                normal = surf.get("normal", [0, 0, 1])
                centroid = surf.get("centroid", [0, 0, 0])
                uv_bounds = surf.get("uv_bounds", {})
                edge_count = surf.get("edge_count", 0)

                face = BRepFace(
                    face_id=face_id,
                    surface_type=surf_type,
                    area=area,
                    normal=normal,
                    centroid=centroid,
                    uv_bounds=uv_bounds,
                    neighboring_faces=[],
                    edge_count=edge_count,
                    convexity=[],
                )
                faces.append(face)

        return faces

    @staticmethod
    def compress_genome(data: dict) -> bytes:
        """
        Compress genome data for storage.

        Args:
            data: Genome dictionary

        Returns:
            Compressed bytes
        """
        json_str = json.dumps(data, separators=(',', ':'))
        return zlib.compress(json_str.encode('utf-8'))

    @staticmethod
    def decompress_genome(data: bytes) -> dict:
        """
        Decompress genome data.

        Args:
            data: Compressed bytes

        Returns:
            Genome dictionary
        """
        json_str = zlib.decompress(data).decode('utf-8')
        return json.loads(json_str)


# ============================================================================
# INTEGRATION FUNCTIONS FOR D2-WORKKER
# ============================================================================

async def extract_with_creo_enhanced(
    local_file_path: str,
    job_type: str,
    extractor: CreoGenomeExtractor | None = None,
) -> dict:
    """
    Enhanced Creo extraction for D2-worker integration.

    This function replaces the placeholder extract_with_creo()
    in D2-creo-extraction-worker.py

    Args:
        local_file_path: Path to downloaded .prt or .asm file
        job_type: 'creo_part' or 'creo_asm'
        extractor: Optional pre-configured extractor

    Returns:
        dict: Extraction result compatible with existing schema
    """
    if extractor is None:
        extractor = CreoGenomeExtractor()

    try:
        result = await extractor.extract_file(
            local_file_path,
            extract_brep_graph=True,
            extract_point_cloud=True,
            extract_deepsdf=False,  # Disabled for speed
        )

        # Convert to existing D2 schema
        return {
            "status": "completed" if not result.errors else "partial",
            "filename": result.file_name,
            "file_type": result.file_type,
            "extraction_timestamp": result.extracted_at,
            "parameters": [],  # Would need additional extraction
            "bom": result.bom if result.bom else [] if job_type == "creo_asm" else None,
            "mass_properties": result.mass_properties,
            "feature_tree": result.feature_tree,
            "references": [],
            # New fields
            "brep_graph": result.brep_graph.to_dict() if result.brep_graph else None,
            "point_cloud": result.point_cloud.to_dict() if result.point_cloud else None,
            "deepsdf_data": result.deepsdf_data.to_dict() if result.deepsdf_data else None,
            "face_count": result.face_count,
            "edge_count": result.edge_count,
            "vertex_count": result.vertex_count,
            "errors": result.errors,
            "warnings": result.warnings,
        }

    except Exception as e:
        logger.error(f"Enhanced Creo extraction failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "filename": Path(local_file_path).name,
            "file_type": job_type,
        }


# ============================================================================
# PROTO DEFINITION (for reference)
# ============================================================================

"""
Example gRPC proto definition for Creo service:

syntax = "proto3";

package creo;

service CreoExtractionService {
  rpc ExtractBRep(ExtractBRepRequest) returns (ExtractBRepResponse);
  rpc ExtractTessellation(ExtractTessellationRequest) returns (ExtractTessellationResponse);
  rpc ComputeSDF(ComputeSDFRequest) returns (ComputeSDFResponse);
  rpc GetMassProperties(GetMassPropertiesRequest) returns (GetMassPropertiesResponse);
}

message ExtractBRepRequest {
  string file_path = 1;
}

message ExtractBRepResponse {
  repeated Face faces = 1;
  repeated Edge edges = 2;
}

message Face {
  int32 face_id = 1;
  string surface_type = 2;
  float area = 3;
  repeated float normal = 4;
  repeated float centroid = 5;
  UVBounds uv_bounds = 6;
  repeated int32 neighboring_faces = 7;
  repeated string convexity = 8;
}

message Edge {
  int32 face_1 = 1;
  int32 face_2 = 2;
  string convexity = 3;
  float length = 4;
  string curve_type = 5;
}

message UVBounds {
  float u_min = 1;
  float u_max = 2;
  float v_min = 3;
  float v_max = 4;
}

message ExtractTessellationRequest {
  string file_path = 1;
  int32 quality = 2;  // 1-10
}

message ExtractTessellationResponse {
  bytes stl_data = 1;  // Binary STL
  repeated float vertices = 2;  // Flattened Nx3 array
  repeated float normals = 3;  // Flattened Nx3 array
}

message ComputeSDFRequest {
  string file_path = 1;
  repeated Point3D query_points = 2;
}

message ComputeSDFResponse {
  repeated float sdf_values = 1;
  repeated Point3D normals = 2;
}

message Point3D {
  float x = 1;
  float y = 2;
  float z = 3;
}
"""
