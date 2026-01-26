Based on my comprehensive research, here's a gap analysis of technologies you might be missing in your CAD extraction, model matching, and feature reconstruction stack:

---

## **TECHNOLOGY GAP ANALYSIS**

### **What You Have (from the CosCAD implementation):**
- ✅ Point cloud encoders (PointNet++, DGCNN)
- ✅ Multi-view rendering pipeline
- ✅ CLIP-based text/image embeddings
- ✅ Contrastive learning for cross-modal alignment
- ✅ HNSW + LSH indexing for retrieval
- ✅ Genome extraction from Creo (features, parameters, relations)
- ✅ pgvector for embedding storage

---

### **CRITICAL GAPS TO ADDRESS:**

#### **1. B-Rep Native Encoders (HIGH PRIORITY)**
Your current stack uses point clouds, but state-of-the-art works directly on B-Rep topology:

| Technology | What It Does | Why You Need It |
|------------|--------------|-----------------|
| **BRepNet** | Topological message passing on coedges | Preserves exact CAD topology, no discretization loss |
| **UV-Net** | UV-grid sampling + GNN on face adjacency graph | Better surface geometry encoding |
| **AAGNet** | Attributed Adjacency Graph with extended attributes | Multi-task machining feature recognition |
| **BRepGAT** | Graph attention on B-Rep for face segmentation | Better handling of intersecting features |

**Implementation suggestion:** Extract B-Rep graph directly from Pro/TOOLKIT (you already have face/edge/loop traversal) → Build face adjacency graph → Use UV-Net or BRepNet encoder alongside your DGCNN.

---

#### **2. 2D Drawing → 3D Reconstruction (HIGH PRIORITY)**
You're missing the **drawing digitization pipeline**:

| Technology | What It Does |
|------------|--------------|
| **Drawing2CAD** | SVG/vector drawings → CAD command sequences |
| **CAD2Program** | 2D orthographic views → parametric model scripts (VLM-based) |
| **GD&T Extraction** | YOLOv11-OBB + Donut transformer for PMI extraction |
| **Img2CAD** | Single image → CAD via VLM-assisted factorization |

**Your gap:** No pipeline to extract information from legacy 2D drawings (DXF/DWG raster scans) and reconstruct 3D models.

---

#### **3. Generative CAD / Text-to-CAD (MEDIUM PRIORITY)**
The field has moved to LLM-based CAD generation:

| Technology | Capability |
|------------|------------|
| **Text2CAD** | Natural language → parametric CAD sequences |
| **CAD-MLLM** | Multimodal (text + image + point cloud) → CAD |
| **CAD-Recode** | Point cloud → executable CadQuery Python code |
| **CAD-GPT** | Image/text → CAD with spatial reasoning |
| **CADmium** | Code LLM fine-tuned for CAD generation |

**Your gap:** No text-to-CAD or sketch-to-CAD generation capability for rapid prototyping.

---

#### **4. Assembly Constraint Prediction (MEDIUM PRIORITY)**
Missing automatic mating/joint inference:

| Technology | What It Does |
|------------|--------------|
| **AutoMate** | SB-GCN for predicting mates between B-Rep parts |
| **JoinABLe** | Joint axis + pose prediction for assembly |
| **Multi-part GCN** | Kinematic constraint prediction |

**Your gap:** Given two parts from your genome database, you can't automatically suggest how they mate together.

---

#### **5. Sketch Constraint Generation (LOWER PRIORITY)**
For SmartAssembly sketch automation:

| Technology | What It Does |
|------------|--------------|
| **SketchGen** | Transformer-based constraint generation |
| **SketchGraphs** | 15M sketch dataset with constraint graphs |
| **Constraint Alignment** | RLHF-style training with solver feedback |

**Your gap:** When generating new sketches, you can't auto-infer geometric constraints (perpendicular, coincident, tangent, etc.)

---

#### **6. GD&T / PMI Extraction (LOWER PRIORITY for 3D, HIGH for 2D)**
Extracting manufacturing information from drawings:

| Technology | What It Does |
|------------|--------------|
| **YOLOv11-OBB** | Rotated bounding box detection for GD&T symbols |
| **Donut Transformer** | Structured JSON output from detected regions |
| **Vision-Language Parser** | Fine-tuned VLM for engineering annotation parsing |

---

### **RECOMMENDED IMPLEMENTATION ROADMAP:**

```
Phase 1 (Immediate Value):
├── Add B-Rep encoder (UV-Net style) to genome extraction
├── Store face adjacency graph in PostgreSQL
└── Dual encoding: Point cloud + B-Rep graph

Phase 2 (Drawing Pipeline):
├── 2D Drawing digitization (YOLOv7 + OCR for DXF/PDF)
├── GD&T symbol extraction
└── Drawing2CAD for legacy drawing reconstruction

Phase 3 (Generative):
├── Text-to-CAD using fine-tuned LLM
├── Assembly constraint suggestion
└── Sketch constraint auto-generation

Phase 4 (Advanced):
├── CAD-MLLM integration for multimodal queries
├── Reinforcement learning for constraint alignment
└── Online learning for new feature types
```

---

### **QUICK WIN IMPLEMENTATIONS:**

**1. B-Rep Graph Extraction** (add to your existing Pro/TOOLKIT pipeline):
```python
# Extend genome extraction to include face adjacency graph
class BRepGraphExtractor:
    """Extract UV-Net style graph from Pro/TOOLKIT traversal"""
    
    def extract_face_adjacency_graph(self, model_handle) -> Dict:
        faces = []
        edges = []
        adjacency = []
        
        # For each face, sample UV grid
        for face in self.traverse_faces(model_handle):
            uv_grid = self.sample_uv_grid(face, resolution=10)
            face_type = self.get_surface_type(face)  # plane, cylinder, etc.
            faces.append({
                'id': face.id,
                'uv_grid': uv_grid,  # 10x10x3 position grid
                'type': face_type,
                'area': face.area,
                'centroid': face.centroid
            })
        
        # Build adjacency from shared edges
        for edge in self.traverse_edges(model_handle):
            adjacent_faces = self.get_adjacent_faces(edge)
            if len(adjacent_faces) == 2:
                adjacency.append({
                    'edge_id': edge.id,
                    'face1': adjacent_faces[0].id,
                    'face2': adjacent_faces[1].id,
                    'convexity': self.get_edge_convexity(edge),
                    'length': edge.length
                })
        
        return {'faces': faces, 'edges': edges, 'adjacency': adjacency}
```

**2. Database Schema Extension:**
```sql
-- Add B-Rep graph storage
CREATE TABLE model_brep_graphs (
    genome_id UUID REFERENCES model_genomes(id),
    face_graph JSONB,           -- Face nodes with UV grids
    edge_graph JSONB,           -- Edge attributes
    adjacency_list JSONB,       -- Face adjacency
    brep_embedding VECTOR(512), -- UV-Net/BRepNet embedding
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- GD&T annotations (for drawing extraction)
CREATE TABLE drawing_annotations (
    id UUID PRIMARY KEY,
    drawing_id UUID,
    annotation_type VARCHAR(50),  -- 'gdt', 'dimension', 'note', 'surface_finish'
    bounding_box JSONB,           -- Rotated OBB
    parsed_value JSONB,           -- Structured extraction
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

Would you like me to implement any of these specific gaps? The B-Rep encoder integration would give you the biggest immediate improvement in retrieval quality, while the 2D drawing pipeline would unlock a whole new input modality for your system.