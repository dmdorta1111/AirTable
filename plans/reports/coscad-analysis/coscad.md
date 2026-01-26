I'll search for information about Coscad CAD retrieval and then look at your existing setup.Let me search for your existing airbase clone project and Creo serialization setup:Now let me search for more specific information about your current database schema:Excellent! Now I have a clear picture of your setup. Let me synthesize what I found about CosCAD and integrate it with your existing architecture.

## Understanding CosCAD

CosCAD is a novel framework for CAD model retrieval and pose alignment from a single image that leverages cross-modal contrastive learning to integrate image, CAD model, and text features into a shared representation space. It uses Tri-Indexed Quantized Graph Search, which accelerates CAD retrieval using LSH buckets, HNSW graphs, and Product Quantization (PQ) for efficient retrieval at scale.

The key techniques from CosCAD that apply to your airbase clone:

1. **Cross-modal embeddings** - Aligning image, text, and 3D geometry in the same vector space
2. **Tri-indexed search** - LSH → HNSW → PQ for fast retrieval
3. **SLIP-based encoding** - Using pre-trained vision-language models

## Integration Architecture for Your Creo Genome System

Here's how to integrate CosCAD-style retrieval into your Neon PostgreSQL + pgvector setup:

```sql
-- ============================================================================
-- COSCAD-INSPIRED SCHEMA EXTENSIONS FOR YOUR EXISTING GENOME DATABASE
-- ============================================================================

-- Enable required extensions (you likely have these already)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;  -- For spatial queries on bounding boxes

-- ============================================================================
-- MULTIMODAL EMBEDDINGS TABLE
-- Store aligned embeddings from different modalities
-- ============================================================================

CREATE TABLE model_multimodal_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_genome_id UUID REFERENCES model_genomes(genome_id) ON DELETE CASCADE,
    
    -- Cross-modal embeddings (aligned to same space via contrastive learning)
    geometry_embedding VECTOR(512),      -- From 3D encoder (PointNet++/DGCNN)
    text_embedding VECTOR(512),          -- From CLIP/SLIP text encoder
    image_embedding VECTOR(512),         -- From rendered views
    fused_embedding VECTOR(512),         -- Combined query embedding
    
    -- LSH buckets for coarse filtering (CosCAD's Tri-Index step 1)
    lsh_bucket_1 INT,
    lsh_bucket_2 INT, 
    lsh_bucket_3 INT,
    lsh_bucket_4 INT,
    
    -- Product quantization codes (CosCAD's Tri-Index step 3)
    pq_codes BYTEA,  -- Compressed feature representation
    
    -- Metadata for retrieval
    category_label TEXT,  -- For category-conditioned retrieval
    rendered_views JSONB,  -- URLs/paths to pre-rendered view images
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(model_genome_id)
);

-- ============================================================================
-- HNSW INDEXES FOR FAST ANN SEARCH (CosCAD's Tri-Index step 2)
-- ============================================================================

-- Index for text-to-CAD retrieval
CREATE INDEX idx_multimodal_text_hnsw 
ON model_multimodal_embeddings 
USING hnsw (text_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 100);

-- Index for image-to-CAD retrieval
CREATE INDEX idx_multimodal_image_hnsw 
ON model_multimodal_embeddings 
USING hnsw (image_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 100);

-- Index for geometry-to-geometry retrieval (find similar parts)
CREATE INDEX idx_multimodal_geometry_hnsw 
ON model_multimodal_embeddings 
USING hnsw (geometry_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 100);

-- Index for fused cross-modal queries
CREATE INDEX idx_multimodal_fused_hnsw 
ON model_multimodal_embeddings 
USING hnsw (fused_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 100);

-- ============================================================================
-- LSH BUCKET INDEX FOR COARSE FILTERING
-- ============================================================================

CREATE INDEX idx_lsh_buckets 
ON model_multimodal_embeddings (lsh_bucket_1, lsh_bucket_2, lsh_bucket_3, lsh_bucket_4);

-- ============================================================================
-- SPATIAL INDEXES USING POSTGIS
-- For bounding box queries and spatial similarity
-- ============================================================================

-- Add PostGIS geometry columns to model_genomes
ALTER TABLE model_genomes 
ADD COLUMN IF NOT EXISTS bbox_3d geometry(PolygonZ, 0);  -- 3D bounding box

ALTER TABLE model_genomes 
ADD COLUMN IF NOT EXISTS centroid_3d geometry(PointZ, 0);  -- Centroid point

-- Populate from existing bounding_box JSONB
UPDATE model_genomes 
SET bbox_3d = ST_MakeBox3D(
    ST_MakePoint(
        (bounding_box->'min'->>0)::float,
        (bounding_box->'min'->>1)::float,
        (bounding_box->'min'->>2)::float
    ),
    ST_MakePoint(
        (bounding_box->'max'->>0)::float,
        (bounding_box->'max'->>1)::float,
        (bounding_box->'max'->>2)::float
    )
)
WHERE bounding_box IS NOT NULL;

-- Spatial index for bounding box queries
CREATE INDEX idx_model_bbox_gist 
ON model_genomes USING GIST (bbox_3d);

-- ============================================================================
-- VIEW RENDERING CACHE
-- Pre-rendered 2D views for image-based retrieval
-- ============================================================================

CREATE TABLE model_rendered_views (
    view_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_genome_id UUID REFERENCES model_genomes(genome_id) ON DELETE CASCADE,
    
    view_type TEXT NOT NULL,  -- 'front', 'top', 'iso', 'canonical_0', etc.
    view_angle JSONB,         -- {azimuth: 45, elevation: 30}
    
    -- Storage reference (Backblaze B2)
    b2_bucket TEXT,
    b2_key TEXT,
    
    -- View embedding for retrieval
    view_embedding VECTOR(512),
    
    -- Metadata
    resolution INT[],  -- [width, height]
    render_settings JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_view_embedding_hnsw 
ON model_rendered_views 
USING hnsw (view_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

Now here's the Python service to integrate with your existing gRPC architecture:

```python
# cad_retrieval/coscad_retriever.py
"""
CosCAD-inspired multimodal CAD retrieval for Creo genome database.
Integrates with existing Neon PostgreSQL + pgvector setup.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np
import asyncpg
from sentence_transformers import SentenceTransformer
import torch
import torch.nn.functional as F

# Optional: For 3D geometry encoding
try:
    from pytorch3d.structures import Pointclouds
    HAS_PYTORCH3D = True
except ImportError:
    HAS_PYTORCH3D = False


@dataclass
class RetrievalQuery:
    """Cross-modal query for CAD retrieval."""
    text: Optional[str] = None
    image_path: Optional[str] = None
    image_embedding: Optional[np.ndarray] = None
    geometry_points: Optional[np.ndarray] = None  # Nx3 point cloud
    category_filter: Optional[str] = None
    bbox_filter: Optional[dict] = None  # {min: [x,y,z], max: [x,y,z]}
    
    
@dataclass
class RetrievalResult:
    """Retrieved CAD model with similarity scores."""
    genome_id: str
    model_name: str
    category: str
    similarity_score: float
    text_similarity: Optional[float] = None
    image_similarity: Optional[float] = None
    geometry_similarity: Optional[float] = None
    bounding_box: Optional[dict] = None
    

class CosCADRetriever:
    """
    CosCAD-inspired multimodal retrieval system.
    
    Uses:
    - CLIP/SLIP for text and image encoding
    - PointNet++ or DGCNN for geometry encoding
    - Tri-indexed search: LSH -> HNSW -> PQ
    - pgvector for ANN search
    - PostGIS for spatial filtering
    """
    
    def __init__(
        self,
        database_url: str,
        text_model: str = "sentence-transformers/clip-ViT-B-32",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.database_url = database_url
        self.device = device
        self.pool: Optional[asyncpg.Pool] = None
        
        # Load encoders
        self.text_encoder = SentenceTransformer(text_model)
        self.text_encoder.to(device)
        
        # Image encoder (CLIP)
        self._init_image_encoder()
        
        # 3D geometry encoder (optional)
        self.geometry_encoder = None
        if HAS_PYTORCH3D:
            self._init_geometry_encoder()
    
    def _init_image_encoder(self):
        """Initialize CLIP image encoder."""
        import clip
        self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=self.device)
        
    def _init_geometry_encoder(self):
        """Initialize PointNet++ for 3D geometry encoding."""
        # Simplified - in production you'd load a pre-trained encoder
        # trained with contrastive loss against CLIP embeddings
        pass
        
    async def initialize(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        
    async def close(self):
        """Close database connections."""
        if self.pool:
            await self.pool.close()
            
    # =========================================================================
    # ENCODING METHODS
    # =========================================================================
    
    def encode_text(self, text: str) -> np.ndarray:
        """Encode text query to embedding."""
        embedding = self.text_encoder.encode(text, normalize_embeddings=True)
        return embedding.astype(np.float32)
    
    def encode_image(self, image_path: str) -> np.ndarray:
        """Encode image to embedding using CLIP."""
        from PIL import Image
        image = Image.open(image_path)
        image_input = self.clip_preprocess(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            image_features = self.clip_model.encode_image(image_input)
            image_features = F.normalize(image_features, dim=-1)
            
        return image_features.cpu().numpy().flatten().astype(np.float32)
    
    def encode_geometry(self, points: np.ndarray) -> np.ndarray:
        """Encode 3D point cloud to embedding."""
        if not HAS_PYTORCH3D or self.geometry_encoder is None:
            raise RuntimeError("Geometry encoder not available")
            
        # Normalize point cloud to unit sphere
        centroid = points.mean(axis=0)
        points_centered = points - centroid
        scale = np.max(np.linalg.norm(points_centered, axis=1))
        points_normalized = points_centered / scale
        
        # Encode with PointNet++
        points_tensor = torch.from_numpy(points_normalized).float().unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            geometry_features = self.geometry_encoder(points_tensor)
            geometry_features = F.normalize(geometry_features, dim=-1)
            
        return geometry_features.cpu().numpy().flatten().astype(np.float32)
    
    def compute_lsh_buckets(self, embedding: np.ndarray, num_buckets: int = 4) -> List[int]:
        """Compute LSH bucket indices for coarse filtering."""
        # Simple LSH using random hyperplanes
        # In production, use pre-computed hyperplanes stored in DB
        np.random.seed(42)  # Deterministic for consistency
        hyperplanes = np.random.randn(num_buckets, embedding.shape[0])
        
        buckets = []
        for hp in hyperplanes:
            bucket = int(np.dot(embedding, hp) > 0)
            buckets.append(bucket)
            
        return buckets
    
    # =========================================================================
    # RETRIEVAL METHODS
    # =========================================================================
    
    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int = 10,
        use_lsh_filter: bool = True,
        rerank: bool = True
    ) -> List[RetrievalResult]:
        """
        Cross-modal CAD retrieval using CosCAD-style tri-indexed search.
        
        Pipeline:
        1. Encode query modalities
        2. (Optional) LSH bucket filtering for coarse pruning
        3. HNSW search via pgvector
        4. (Optional) Reranking with fused scores
        5. (Optional) Spatial filtering with PostGIS
        """
        # Step 1: Encode query modalities
        embeddings = {}
        
        if query.text:
            embeddings['text'] = self.encode_text(query.text)
            
        if query.image_path:
            embeddings['image'] = self.encode_image(query.image_path)
        elif query.image_embedding is not None:
            embeddings['image'] = query.image_embedding
            
        if query.geometry_points is not None and HAS_PYTORCH3D:
            embeddings['geometry'] = self.encode_geometry(query.geometry_points)
        
        if not embeddings:
            raise ValueError("Query must have at least one modality")
        
        # Step 2: Fuse embeddings for query
        fused_query = self._fuse_embeddings(embeddings)
        
        # Step 3: Retrieve candidates
        candidates = await self._retrieve_candidates(
            fused_query,
            embeddings,
            query.category_filter,
            query.bbox_filter,
            top_k=top_k * 3 if rerank else top_k,  # Over-retrieve for reranking
            use_lsh_filter=use_lsh_filter
        )
        
        # Step 4: Rerank with per-modality scores
        if rerank and len(embeddings) > 1:
            candidates = await self._rerank_candidates(candidates, embeddings, top_k)
        else:
            candidates = candidates[:top_k]
            
        return candidates
    
    def _fuse_embeddings(self, embeddings: dict) -> np.ndarray:
        """Fuse multiple modality embeddings into single query vector."""
        # Simple average fusion - can use learned weights
        stacked = np.stack(list(embeddings.values()))
        fused = np.mean(stacked, axis=0)
        fused = fused / np.linalg.norm(fused)  # Normalize
        return fused
    
    async def _retrieve_candidates(
        self,
        fused_query: np.ndarray,
        modality_embeddings: dict,
        category_filter: Optional[str],
        bbox_filter: Optional[dict],
        top_k: int,
        use_lsh_filter: bool
    ) -> List[RetrievalResult]:
        """Retrieve candidates using pgvector HNSW search."""
        
        # Build query
        query_parts = []
        params = [fused_query.tolist()]
        param_idx = 2
        
        # Base query with HNSW search
        base_query = """
            SELECT 
                mg.genome_id,
                mg.model_name,
                mg.category,
                mg.bounding_box,
                mme.fused_embedding <=> $1::vector AS distance,
                mme.text_embedding,
                mme.image_embedding,
                mme.geometry_embedding
            FROM model_multimodal_embeddings mme
            JOIN model_genomes mg ON mg.genome_id = mme.model_genome_id
        """
        
        where_clauses = []
        
        # Optional LSH bucket filter
        if use_lsh_filter:
            buckets = self.compute_lsh_buckets(fused_query)
            where_clauses.append(f"""
                (mme.lsh_bucket_1 = ${param_idx} OR mme.lsh_bucket_2 = ${param_idx + 1})
            """)
            params.extend(buckets[:2])
            param_idx += 2
        
        # Optional category filter
        if category_filter:
            where_clauses.append(f"mg.category = ${param_idx}")
            params.append(category_filter)
            param_idx += 1
            
        # Optional bounding box filter (PostGIS)
        if bbox_filter:
            where_clauses.append(f"""
                ST_3DIntersects(
                    mg.bbox_3d,
                    ST_MakeBox3D(
                        ST_MakePoint(${param_idx}, ${param_idx + 1}, ${param_idx + 2}),
                        ST_MakePoint(${param_idx + 3}, ${param_idx + 4}, ${param_idx + 5})
                    )
                )
            """)
            params.extend(bbox_filter['min'] + bbox_filter['max'])
            param_idx += 6
        
        # Combine query
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
            
        base_query += f"""
            ORDER BY mme.fused_embedding <=> $1::vector
            LIMIT ${param_idx}
        """
        params.append(top_k)
        
        # Execute query
        async with self.pool.acquire() as conn:
            # Set HNSW search parameters
            await conn.execute("SET hnsw.ef_search = 100")
            
            rows = await conn.fetch(base_query, *params)
        
        # Convert to results
        results = []
        for row in rows:
            result = RetrievalResult(
                genome_id=str(row['genome_id']),
                model_name=row['model_name'],
                category=row['category'],
                similarity_score=1.0 - row['distance'],  # Convert distance to similarity
                bounding_box=row['bounding_box']
            )
            
            # Compute per-modality similarities
            if 'text' in modality_embeddings and row['text_embedding']:
                text_emb = np.array(row['text_embedding'])
                result.text_similarity = float(np.dot(modality_embeddings['text'], text_emb))
                
            if 'image' in modality_embeddings and row['image_embedding']:
                image_emb = np.array(row['image_embedding'])
                result.image_similarity = float(np.dot(modality_embeddings['image'], image_emb))
                
            if 'geometry' in modality_embeddings and row['geometry_embedding']:
                geom_emb = np.array(row['geometry_embedding'])
                result.geometry_similarity = float(np.dot(modality_embeddings['geometry'], geom_emb))
            
            results.append(result)
            
        return results
    
    async def _rerank_candidates(
        self,
        candidates: List[RetrievalResult],
        modality_embeddings: dict,
        top_k: int
    ) -> List[RetrievalResult]:
        """Rerank candidates using weighted combination of modality scores."""
        # Compute combined scores
        for candidate in candidates:
            scores = []
            weights = []
            
            if candidate.text_similarity is not None:
                scores.append(candidate.text_similarity)
                weights.append(1.0)
                
            if candidate.image_similarity is not None:
                scores.append(candidate.image_similarity)
                weights.append(1.2)  # Slightly weight image similarity higher
                
            if candidate.geometry_similarity is not None:
                scores.append(candidate.geometry_similarity)
                weights.append(1.5)  # Weight geometry similarity highest
            
            if scores:
                candidate.similarity_score = np.average(scores, weights=weights)
        
        # Sort by combined score
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return candidates[:top_k]
    
    # =========================================================================
    # INDEXING METHODS
    # =========================================================================
    
    async def index_model(
        self,
        genome_id: str,
        description: Optional[str] = None,
        rendered_views: Optional[List[str]] = None,
        point_cloud: Optional[np.ndarray] = None
    ):
        """
        Index a CAD model for multimodal retrieval.
        
        Generates embeddings from available modalities and stores them.
        """
        embeddings = {}
        
        # Text embedding from description
        if description:
            embeddings['text'] = self.encode_text(description)
        
        # Image embeddings from rendered views
        if rendered_views:
            view_embeddings = []
            for view_path in rendered_views:
                view_emb = self.encode_image(view_path)
                view_embeddings.append(view_emb)
            # Average view embeddings
            embeddings['image'] = np.mean(view_embeddings, axis=0)
            embeddings['image'] = embeddings['image'] / np.linalg.norm(embeddings['image'])
        
        # Geometry embedding from point cloud
        if point_cloud is not None and HAS_PYTORCH3D:
            embeddings['geometry'] = self.encode_geometry(point_cloud)
        
        # Fuse embeddings
        if embeddings:
            fused = self._fuse_embeddings(embeddings)
            lsh_buckets = self.compute_lsh_buckets(fused)
        else:
            return  # Nothing to index
        
        # Store in database
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO model_multimodal_embeddings (
                    model_genome_id,
                    text_embedding,
                    image_embedding,
                    geometry_embedding,
                    fused_embedding,
                    lsh_bucket_1,
                    lsh_bucket_2,
                    lsh_bucket_3,
                    lsh_bucket_4
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (model_genome_id) 
                DO UPDATE SET
                    text_embedding = EXCLUDED.text_embedding,
                    image_embedding = EXCLUDED.image_embedding,
                    geometry_embedding = EXCLUDED.geometry_embedding,
                    fused_embedding = EXCLUDED.fused_embedding,
                    lsh_bucket_1 = EXCLUDED.lsh_bucket_1,
                    lsh_bucket_2 = EXCLUDED.lsh_bucket_2,
                    lsh_bucket_3 = EXCLUDED.lsh_bucket_3,
                    lsh_bucket_4 = EXCLUDED.lsh_bucket_4
            """,
                genome_id,
                embeddings.get('text', None),
                embeddings.get('image', None),
                embeddings.get('geometry', None),
                fused.tolist(),
                *lsh_buckets
            )


# =========================================================================
# INTEGRATION WITH YOUR EXISTING GRPC SERVICE
# =========================================================================

class CADRetrievalService:
    """
    gRPC service wrapper for CosCAD retrieval.
    Integrates with your existing Creo automation pipeline.
    """
    
    def __init__(self, retriever: CosCADRetriever):
        self.retriever = retriever
        
    async def find_similar_models(
        self,
        request  # Your protobuf request type
    ):
        """Find similar CAD models based on text, image, or geometry query."""
        query = RetrievalQuery(
            text=request.text_query if request.HasField('text_query') else None,
            image_path=request.image_path if request.HasField('image_path') else None,
            category_filter=request.category if request.HasField('category') else None
        )
        
        results = await self.retriever.retrieve(query, top_k=request.top_k or 10)
        
        # Convert to protobuf response
        # ... your response building logic
        
    async def index_new_model(
        self,
        request  # Your protobuf request type
    ):
        """Index a newly extracted model genome."""
        await self.retriever.index_model(
            genome_id=request.genome_id,
            description=request.description,
            rendered_views=list(request.rendered_view_paths),
            point_cloud=np.array(request.point_cloud) if request.point_cloud else None
        )
```

## Usage Example

```python
# Example integration with your existing workflow
import asyncio
from cad_retrieval.coscad_retriever import CosCADRetriever, RetrievalQuery

async def main():
    # Initialize retriever
    retriever = CosCADRetriever(
        database_url="postgres://user:pass@ep-xxx-pooler.region.aws.neon.tech/creo_genomes?sslmode=require"
    )
    await retriever.initialize()
    
    try:
        # Example 1: Text-to-CAD retrieval
        query = RetrievalQuery(
            text="4-door reach-in refrigerator cabinet with top-mount compressor",
            category_filter="cabinet"
        )
        results = await retriever.retrieve(query, top_k=5)
        
        print("Text search results:")
        for r in results:
            print(f"  {r.model_name}: {r.similarity_score:.3f}")
        
        # Example 2: Image-to-CAD retrieval  
        query = RetrievalQuery(
            image_path="/path/to/reference_photo.jpg"
        )
        results = await retriever.retrieve(query, top_k=5)
        
        print("\nImage search results:")
        for r in results:
            print(f"  {r.model_name}: {r.similarity_score:.3f}")
        
        # Example 3: Combined query (CosCAD's strength)
        query = RetrievalQuery(
            text="bracket with mounting holes",
            image_path="/path/to/sketch.png",
            bbox_filter={
                "min": [-50, -50, -10],
                "max": [50, 50, 10]
            }
        )
        results = await retriever.retrieve(query, top_k=5, rerank=True)
        
        print("\nCross-modal search results:")
        for r in results:
            print(f"  {r.model_name}: combined={r.similarity_score:.3f}, "
                  f"text={r.text_similarity:.3f}, image={r.image_similarity:.3f}")
                  
    finally:
        await retriever.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Integration Points with Your Existing System

1. **After genome extraction** → Call `retriever.index_model()` to make it searchable
2. **Before SmartAssembly execution** → Use retrieval to find similar templates
3. **In your gRPC service** → Add a `FindSimilarModels` RPC method
4. **With your RAG pipeline** → Use retrieval results as context for LLM

Would you like me to detail the 3D geometry encoder training setup, the view rendering pipeline for indexing, or the integration with your existing Pro/TOOLKIT extraction?