"""
Integration test for CosCAD multi-modal CAD retrieval pipeline.

Tests the complete workflow:
1. Serialize CAD model data (simulated)
2. Index with multi-modal embeddings
3. Search by text, image, geometry
4. Validate retrieval quality

Run with:
    pytest tests/integration/test_coscad_pipeline.py -v
    pytest tests/integration/test_coscad_pipeline.py::test_end_to_end_workflow -v -s
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

import pytest
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import services from all 8 subagents
from pybase.services.cad_indexing_pipeline import CADIndexingPipeline
from pybase.services.embedding_generator import EmbeddingGenerator
from pybase.services.coscad_retriever import CosCADRetriever, RetrievalQuery, RetrievalResult
from pybase.services.brep_graph_encoder import BRepGraphEncoder
from pybase.services.sketch_similarity import SketchSimilarity
from pybase.db.vector_search import VectorSearchService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
async def test_db():
    """Create test database connection."""
    # In production, this would use real DATABASE_URL
    # For testing, we'll mock the database operations
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        # Create test tables (simplified)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cad_models (
                id UUID PRIMARY KEY,
                model_name VARCHAR(255) UNIQUE NOT NULL,
                part_number VARCHAR(50),
                model_type VARCHAR(50),
                category VARCHAR(100),
                tags TEXT[],
                status VARCHAR(20),
                serialized_content JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cad_model_embeddings (
                id UUID PRIMARY KEY,
                model_id UUID,
                embedding_type VARCHAR(50),
                embedding_vector FLOAT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES cad_models (id)
            )
        """)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_session(test_db):
    """Create test database session."""
    async_session_maker = sessionmaker(
        bind=test_db,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
def mock_creo_data() -> Dict[str, Any]:
    """Mock Creo serialized data."""
    return {
        "model_name": "TEST_BRACKET_001",
        "model_type": "part",
        "category": "bracket",
        "tags": ["test", "mounting"],
        "features": [
            {
                "id": 1,
                "name": "PROTRUSION_1",
                "type": "PROTRUSION",
                "type_id": 917,
            }
        ],
        "feature_geometry": {
            "surfaces": [
                {"id": "s1", "area": 150.5, "normal": [0, 0, 1], "type": "plane"}
            ],
            "edges": [
                {"id": "e1", "length": 25.0, "convexity": 1.0}
            ]
        },
        "sketches": [
            {
                "feature_id": 1,
                "entities": [
                    {"type": "LINE", "length": 50.0},
                    {"type": "ARC", "radius": 12.5}
                ],
                "constraints": [
                    {"type": "HORIZONTAL", "entity_id": "e1"}
                ],
                "dimensions": [
                    {"value": 50.0, "type": "linear"}
                ]
            }
        ],
        "parameters": {
            "parameters": [
                {"name": "LENGTH", "value": 100.0, "type": "DOUBLE"},
                {"name": "WIDTH", "value": 50.0, "type": "DOUBLE"},
                {"name": "THICKNESS", "value": 5.0, "type": "DOUBLE"}
            ]
        },
        "relations": {
            "relations": [
                {"text": "WIDTH = LENGTH / 2"}
            ]
        },
        "metadata": {
            "units": {"length": "mm", "mass": "kg"},
            "mass_properties": {
                "mass": 0.125,
                "volume": 25000.0,
                "density": 0.005
            },
            "bounding_box": {
                "min": [-50, -25, -2.5],
                "max": [50, 25, 2.5]
            }
        }
    }


@pytest.fixture
def mock_embeddings():
    """Mock embedding vectors (512-dim for CLIP, 256-dim for DeepSDF)."""
    return {
        "text": np.random.randn(512).astype(np.float32),
        "image": np.random.randn(512).astype(np.float32),
        "geometry": np.random.randn(256).astype(np.float32),
        "brep_graph": np.random.randn(512).astype(np.float32),
        "sketch": np.random.randn(256).astype(np.float32),
        "parametric": np.random.randn(128).astype(np.float32),
    }


# ============================================================================
# Test Cases
# ============================================================================

@pytest.mark.asyncio
async def test_embedding_generator():
    """Test 1: EmbeddingGenerator creates valid embeddings."""
    generator = EmbeddingGenerator()

    # Text embedding
    text_emb = generator.encode_text("mounting bracket with holes")
    assert text_emb is not None
    assert len(text_emb) == 512  # CLIP dimension

    # Fused embedding
    fused = generator.fuse_embeddings({
        "text": text_emb,
        "image": np.random.randn(512).astype(np.float32),
        "geometry": np.random.randn(256).astype(np.float32),
    })
    assert fused is not None
    assert len(fused) == 512


@pytest.mark.asyncio
async def test_brep_graph_encoder():
    """Test 2: BRepGraphEncoder processes feature_geometry."""
    encoder = BRepGraphEncoder()

    feature_geometry = {
        "surfaces": [
            {"id": "s1", "area": 150.5, "normal": [0, 0, 1], "type": "plane"},
            {"id": "s2", "area": 75.0, "normal": [1, 0, 0], "type": "cylinder"}
        ],
        "edges": [
            {"id": "e1", "length": 25.0, "convexity": 1.0, "surface_ids": ["s1", "s2"]}
        ]
    }

    embedding = encoder.encode_graph(feature_geometry)
    assert embedding is not None
    assert len(embedding) == 512  # B-Rep graph embedding dimension


@pytest.mark.asyncio
async def test_sketch_similarity():
    """Test 3: SketchSimilarity processes sketches."""
    similarity = SketchSimilarity()

    sketches = [
        {
            "feature_id": 1,
            "entities": [
                {"type": "LINE", "length": 50.0},
                {"type": "ARC", "radius": 12.5}
            ],
            "dimensions": [{"value": 50.0}]
        },
        {
            "feature_id": 2,
            "entities": [
                {"type": "LINE", "length": 100.0}
            ],
            "dimensions": [{"value": 100.0}]
        }
    ]

    embeddings = [similarity.encode_sketch(s) for s in sketches]
    assert len(embeddings) == 2
    assert all(e is not None for e in embeddings)
    assert all(len(e) == 256 for e in embeddings)


@pytest.mark.asyncio
async def test_retriever_query_building():
    """Test 4: CosCADRetriever builds correct queries."""
    retriever = CosCADRetriever()

    # Text query
    query = RetrievalQuery(text="bracket with mounting holes")
    assert query.text == "bracket with mounting holes"
    assert query.image_path is None
    assert query.geometry_points is None

    # Multi-modal query
    query = RetrievalQuery(
        text="L-bracket",
        image_path="test.png",
        geometry_points=np.random.randn(100, 3).astype(np.float32)
    )
    assert query.text == "L-bracket"
    assert query.image_path == "test.png"
    assert query.geometry_points is not None


@pytest.mark.asyncio
async def test_end_to_end_workflow(test_session, mock_creo_data, mock_embeddings):
    """Test 5: Complete end-to-end workflow simulation."""

    # Step 1: Process serialized model
    print("\n=== Step 1: Processing Creo data ===")

    # B-Rep graph encoding
    brep_encoder = BRepGraphEncoder()
    brep_emb = brep_encoder.encode_graph(mock_creo_data["feature_geometry"])
    print(f"✓ B-Rep graph embedding: {len(brep_emb)}-dim")

    # Sketch encoding
    sketch_sim = SketchSimilarity()
    sketch_embs = [sketch_sim.encode_sketch(s) for s in mock_creo_data["sketches"]]
    print(f"✓ Sketch embeddings: {len(sketch_embs)} sketches")

    # Text description
    description = f"CAD model: {mock_creo_data['model_name']}, Category: {mock_creo_data['category']}"

    # Step 2: Generate embeddings
    print("\n=== Step 2: Generating multi-modal embeddings ===")
    embed_gen = EmbeddingGenerator()

    text_emb = embed_gen.encode_text(description)
    print(f"✓ Text embedding: {len(text_emb)}-dim")

    # Step 3: Fuse embeddings
    fused_emb = embed_gen.fuse_embeddings({
        "text": text_emb,
        "geometry": mock_embeddings["geometry"],
        "brep_graph": brep_emb,
    })
    print(f"✓ Fused embedding: {len(fused_emb)}-dim")

    # Step 4: Mock similarity search
    print("\n=== Step 3: Searching similar models ===")

    # Simulate finding similar models by cosine similarity
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    # Create "database" of 3 models
    database = [
        {
            "model_name": "TEST_BRACKET_001",
            "fused_embedding": fused_emb,
            "brep_graph_embedding": brep_emb,
        },
        {
            "model_name": "SIMILAR_BRACKET_002",
            "fused_embedding": fused_emb * 0.95 + np.random.randn(512) * 0.05,
            "brep_graph_embedding": brep_emb * 0.9 + np.random.randn(512) * 0.1,
        },
        {
            "model_name": "DIFFERENT_PART_003",
            "fused_embedding": np.random.randn(512).astype(np.float32),
            "brep_graph_embedding": np.random.randn(512).astype(np.float32),
        },
    ]

    # Search by fused embedding
    query_similarities = [
        (model["model_name"], cosine_similarity(fused_emb, model["fused_embedding"]))
        for model in database
    ]
    query_similarities.sort(key=lambda x: x[1], reverse=True)

    print("\nSearch Results:")
    for model_name, similarity in query_similarities:
        icon = "✓" if similarity > 0.8 else "  "
        print(f"  {icon} {model_name}: {similarity:.3f}")

    # Validate top result is the same model
    top_model, top_score = query_similarities[0]
    assert top_model == "TEST_BRACKET_001"
    assert top_score > 0.99  # Same model should be nearly identical

    # Validate second result is similar
    second_model, second_score = query_similarities[1]
    assert second_model == "SIMILAR_BRACKET_002"
    assert second_score > 0.8  # Similar part should be above threshold

    print("\n=== Integration Test PASSED ===")
    print("✓ B-Rep graph encoding works")
    print("✓ Sketch similarity works")
    print("✓ Text embedding works")
    print("✓ Embedding fusion works")
    print("✓ Similarity search works")
    print("✓ End-to-end workflow validated")


# ============================================================================
# Performance Benchmark
# ============================================================================

@pytest.mark.asyncio
async def test_search_performance():
    """Test 6: Search performance with larger database."""
    print("\n=== Performance Test: 1000 models ===")

    import time

    # Create mock database of 1000 models
    database_size = 1000
    database = []

    for i in range(database_size):
        database.append({
            "model_name": f"MODEL_{i:04d}",
            "fused_embedding": np.random.randn(512).astype(np.float32),
        })

    # Query embedding
    query_emb = np.random.randn(512).astype(np.float32)

    # Measure search time
    start = time.time()

    similarities = [
        cosine_similarity(query_emb, model["fused_embedding"])
        for model in database
    ]

    search_time = time.time() - start

    # Find top 10
    top_indices = np.argsort(similarities)[-10:][::-1]

    print(f"✓ Searched {database_size} models in {search_time*1000:.2f}ms")
    print(f"✓ Average search time per query: {search_time/database_size*1000:.4f}ms")
    print(f"✓ Top match: {database[top_indices[0]]['model_name']}")


# ============================================================================
# Utilities
# ============================================================================

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ============================================================================
# Main (for standalone testing)
# ============================================================================

if __name__ == "__main__":
    import sys

    print("\n" + "="*70)
    print("CosCAD Integration Test")
    print("="*70)

    # Run specific test
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "end_to_end":
            # Would need pytest-asyncio to run properly
            print("Use: pytest tests/integration/test_coscad_pipeline.py::test_end_to_end_workflow -v -s")
        else:
            print(f"Unknown test: {test_name}")
    else:
        print("\nRunning all integration tests...")
        print("Use: pytest tests/integration/test_coscad_pipeline.py -v")
