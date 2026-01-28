I'll dive deep into the sync service implementation and data models for the Sigmanest integration.

---

## Sync Service Implementation

### Core Architecture

The sync service operates as a **bidirectional bridge** between PyBase and Sigmanest's SimTrans database:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYNC SERVICE ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         ┌─────────────┐         ┌───────────┐ │
│  │   PyBase    │         │    Sync     │         │ SimTrans  │ │
│  │ PostgreSQL  │◄───────►│   Service   │◄───────►│ SQL Server│ │
│  └─────────────┘         └──────┬──────┘         └───────────┘ │
│                                 │                               │
│                          ┌──────┴──────┐                        │
│                          │    Redis    │                        │
│                          │   (Cache)   │                        │
│                          └─────────────┘                        │
│                                                                 │
│  OUTBOUND (Every 30s):           INBOUND (Every 60s):          │
│  • New work orders               • Nest results                 │
│  • Part definitions              • Cut time estimates           │
│  • Material inventory            • Material consumption         │
│                                  • NC file paths                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Data Models (Pydantic Schemas)

#### Outbound Models (PyBase → Sigmanest)

```python
# src/pybase/integrations/sigmanest/models.py

from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional, List
from enum import Enum
from decimal import Decimal


# ============================================================
# ENUMS
# ============================================================

class Priority(int, Enum):
    """Job priority levels."""
    RUSH = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class GrainDirection(str, Enum):
    """Material grain direction requirements."""
    X = "X"
    Y = "Y"
    NONE = "NONE"


class SyncDirection(str, Enum):
    """Sync operation direction."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class SyncStatus(str, Enum):
    """Sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# ============================================================
# OUTBOUND MODELS (PyBase → Sigmanest)
# ============================================================

class SigmanestWorkOrder(BaseModel):
    """
    Work order pushed to Sigmanest SimTrans.
    Maps to dbo.WorkOrders table.
    """
    model_config = ConfigDict(from_attributes=True)
    
    work_order_id: str = Field(
        ..., 
        max_length=50,
        description="Unique work order identifier from PyBase"
    )
    customer_id: str = Field(
        ..., 
        max_length=50,
        description="Customer account number"
    )
    customer_name: str = Field(
        ..., 
        max_length=200,
        description="Customer display name"
    )
    order_date: date = Field(
        ...,
        description="Date order was placed"
    )
    due_date: date = Field(
        ...,
        description="Required delivery date"
    )
    priority: Priority = Field(
        default=Priority.NORMAL,
        description="Production priority level"
    )
    ship_date: Optional[date] = Field(
        default=None,
        description="Planned ship date"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Special instructions"
    )
    po_number: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Customer PO reference"
    )
    
    # Sync tracking
    pybase_job_id: str = Field(
        ...,
        description="Original PyBase record ID"
    )
    

class SigmanestPart(BaseModel):
    """
    Part definition for nesting.
    Maps to dbo.Parts table.
    """
    model_config = ConfigDict(from_attributes=True)
    
    part_id: str = Field(
        ...,
        max_length=50,
        description="Unique part identifier"
    )
    work_order_id: str = Field(
        ...,
        max_length=50,
        description="Parent work order ID"
    )
    part_number: str = Field(
        ...,
        max_length=100,
        description="Part number from engineering"
    )
    revision: str = Field(
        default="A",
        max_length=10,
        description="Drawing revision"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Part description"
    )
    quantity: int = Field(
        ...,
        gt=0,
        description="Quantity required"
    )
    
    # Material specifications
    material_code: str = Field(
        ...,
        max_length=50,
        description="Material type code (e.g., 304SS, 16GA-CRS)"
    )
    thickness: Decimal = Field(
        ...,
        gt=0,
        decimal_places=4,
        description="Material thickness in inches"
    )
    
    # Geometry
    dxf_file_path: str = Field(
        ...,
        description="Path to DXF file for nesting"
    )
    grain_direction: GrainDirection = Field(
        default=GrainDirection.NONE,
        description="Required grain orientation"
    )
    mirror_allowed: bool = Field(
        default=True,
        description="Can part be mirrored during nesting"
    )
    rotate_allowed: bool = Field(
        default=True,
        description="Can part be rotated during nesting"
    )
    rotation_increment: int = Field(
        default=90,
        description="Allowed rotation increment in degrees"
    )
    
    # Nesting hints
    nest_priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority within nest (1=highest)"
    )
    cluster_quantity: Optional[int] = Field(
        default=None,
        description="Preferred cluster size for common cut"
    )
    
    # Tracking
    pybase_routing_id: str = Field(
        ...,
        description="PyBase job routing record ID"
    )


class SigmanestMaterial(BaseModel):
    """
    Material inventory record for bidirectional sync.
    Maps to dbo.MaterialInventory table.
    """
    model_config = ConfigDict(from_attributes=True)
    
    material_code: str = Field(
        ...,
        max_length=50,
        description="Unique material identifier"
    )
    description: str = Field(
        ...,
        max_length=200,
        description="Material description"
    )
    material_type: str = Field(
        ...,
        max_length=50,
        description="Base material (Steel, Stainless, Aluminum)"
    )
    grade: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Material grade (304, 316, 5052)"
    )
    thickness: Decimal = Field(
        ...,
        gt=0,
        decimal_places=4,
        description="Thickness in inches"
    )
    
    # Sheet dimensions
    sheet_width: Decimal = Field(
        ...,
        gt=0,
        description="Sheet width in inches"
    )
    sheet_length: Decimal = Field(
        ...,
        gt=0,
        description="Sheet length in inches"
    )
    
    # Inventory
    quantity_on_hand: int = Field(
        default=0,
        ge=0,
        description="Current stock count"
    )
    quantity_allocated: int = Field(
        default=0,
        ge=0,
        description="Quantity reserved for orders"
    )
    quantity_available: int = Field(
        default=0,
        ge=0,
        description="Quantity available for nesting"
    )
    reorder_point: int = Field(
        default=0,
        ge=0,
        description="Minimum stock level trigger"
    )
    
    # Location & costing
    location: str = Field(
        default="MAIN",
        max_length=50,
        description="Warehouse location code"
    )
    unit_cost: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        decimal_places=4,
        description="Cost per sheet"
    )
    
    # Traceability
    heat_lot: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Mill heat/lot number"
    )
    
    # Sigmanest reference
    sigmanest_material_id: Optional[str] = Field(
        default=None,
        description="Sigmanest internal ID"
    )
```

#### Inbound Models (Sigmanest → PyBase)

```python
# ============================================================
# INBOUND MODELS (Sigmanest → PyBase)
# ============================================================

class NestedPart(BaseModel):
    """
    Individual part placement within a nest.
    """
    part_id: str = Field(
        ...,
        description="Reference to original part"
    )
    work_order_id: str = Field(
        ...,
        description="Parent work order"
    )
    quantity: int = Field(
        ...,
        gt=0,
        description="Quantity nested on this sheet"
    )
    
    # Placement coordinates (inches from sheet origin)
    position_x: Decimal = Field(
        ...,
        description="X position on sheet"
    )
    position_y: Decimal = Field(
        ...,
        description="Y position on sheet"
    )
    rotation_degrees: Decimal = Field(
        default=Decimal("0"),
        description="Rotation angle"
    )
    is_mirrored: bool = Field(
        default=False,
        description="Part was mirrored"
    )


class NestResult(BaseModel):
    """
    Completed nest result from Sigmanest.
    Maps to dbo.NestResults table.
    """
    model_config = ConfigDict(from_attributes=True)
    
    nest_id: str = Field(
        ...,
        description="Unique nest identifier"
    )
    nest_name: str = Field(
        ...,
        description="Descriptive nest name"
    )
    created_at: datetime = Field(
        ...,
        description="When nest was created"
    )
    
    # Sheet information
    sheet_id: str = Field(
        ...,
        description="Sheet inventory reference"
    )
    material_code: str = Field(
        ...,
        description="Material used"
    )
    thickness: Decimal = Field(
        ...,
        description="Material thickness"
    )
    sheet_width: Decimal = Field(
        ...,
        description="Sheet width used"
    )
    sheet_length: Decimal = Field(
        ...,
        description="Sheet length used"
    )
    
    # Efficiency metrics
    utilization_percent: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Material utilization percentage"
    )
    scrap_percent: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Scrap percentage"
    )
    parts_area_sq_in: Decimal = Field(
        ...,
        description="Total area of nested parts"
    )
    sheet_area_sq_in: Decimal = Field(
        ...,
        description="Total sheet area"
    )
    
    # NC program details
    nc_file_path: str = Field(
        ...,
        description="Path to generated NC file"
    )
    nc_file_name: str = Field(
        ...,
        description="NC file name"
    )
    machine_id: str = Field(
        ...,
        description="Target machine for cutting"
    )
    post_processor: str = Field(
        ...,
        description="NC post processor used"
    )
    
    # Time estimates
    estimated_cut_time_seconds: int = Field(
        ...,
        ge=0,
        description="Estimated cutting time"
    )
    estimated_rapid_time_seconds: int = Field(
        default=0,
        ge=0,
        description="Estimated rapid traverse time"
    )
    total_cycle_time_seconds: int = Field(
        ...,
        ge=0,
        description="Total estimated cycle time"
    )
    
    # Cutting metrics
    pierce_count: int = Field(
        ...,
        ge=0,
        description="Number of pierces"
    )
    cut_length_inches: Decimal = Field(
        ...,
        ge=0,
        description="Total cut length"
    )
    rapid_length_inches: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Total rapid traverse length"
    )
    
    # Parts included
    parts_nested: List[NestedPart] = Field(
        default_factory=list,
        description="Parts placed on this nest"
    )
    total_parts_count: int = Field(
        ...,
        ge=0,
        description="Total number of parts"
    )
    unique_parts_count: int = Field(
        ...,
        ge=0,
        description="Number of unique part types"
    )
    
    # Status
    is_released: bool = Field(
        default=False,
        description="Released to production"
    )
    released_at: Optional[datetime] = Field(
        default=None,
        description="When released"
    )
    released_by: Optional[str] = Field(
        default=None,
        description="User who released"
    )


class MaterialConsumption(BaseModel):
    """
    Actual material usage after cutting.
    """
    nest_id: str = Field(
        ...,
        description="Reference to nest"
    )
    material_code: str = Field(
        ...,
        description="Material consumed"
    )
    sheets_planned: int = Field(
        ...,
        description="Sheets originally planned"
    )
    sheets_actual: int = Field(
        ...,
        description="Sheets actually used"
    )
    scrap_weight_lbs: Optional[Decimal] = Field(
        default=None,
        description="Actual scrap weight"
    )
    remnant_created: bool = Field(
        default=False,
        description="Usable remnant saved"
    )
    remnant_dimensions: Optional[str] = Field(
        default=None,
        description="Remnant size if created"
    )
    recorded_at: datetime = Field(
        ...,
        description="When consumption was recorded"
    )


# ============================================================
# SYNC TRACKING MODELS
# ============================================================

class SyncLogEntry(BaseModel):
    """
    Log entry for sync operations.
    """
    id: str
    sync_type: str = Field(
        ...,
        description="Type: work_orders, parts, materials, nest_results"
    )
    direction: SyncDirection
    status: SyncStatus
    records_processed: int = Field(default=0)
    records_succeeded: int = Field(default=0)
    records_failed: int = Field(default=0)
    error_message: Optional[str] = None
    error_details: Optional[dict] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class SyncState(BaseModel):
    """
    Current state of sync for a record.
    """
    pybase_id: str
    sigmanest_id: Optional[str] = None
    entity_type: str  # work_order, part, material
    last_synced_at: Optional[datetime] = None
    sync_status: SyncStatus = SyncStatus.PENDING
    sync_hash: Optional[str] = None  # Hash of last synced data
    retry_count: int = 0
    last_error: Optional[str] = None
```

---

### SimTrans Database Client

```python
# src/pybase/integrations/sigmanest/simtrans_client.py

import asyncio
from typing import List, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
import aioodbc
from loguru import logger

from .models import (
    SigmanestWorkOrder,
    SigmanestPart,
    SigmanestMaterial,
    NestResult,
    NestedPart,
    MaterialConsumption,
)
from pybase.core.config import settings


class SimTransConnectionError(Exception):
    """Failed to connect to SimTrans database."""
    pass


class SimTransQueryError(Exception):
    """Query execution failed."""
    pass


class SimTransClient:
    """
    Async client for Sigmanest SimTrans database.
    
    SimTrans uses SQL Server with specific transaction tables
    for bidirectional data exchange.
    """
    
    def __init__(
        self,
        server: str = None,
        database: str = None,
        username: str = None,
        password: str = None,
        driver: str = "ODBC Driver 17 for SQL Server"
    ):
        self.server = server or settings.SIGMANEST_SERVER
        self.database = database or settings.SIGMANEST_DATABASE
        self.username = username or settings.SIGMANEST_USERNAME
        self.password = password or settings.SIGMANEST_PASSWORD
        self.driver = driver
        
        self._pool: Optional[aioodbc.Pool] = None
        self._connection_string = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            "TrustServerCertificate=yes;"
        )
    
    async def connect(self) -> None:
        """Initialize connection pool."""
        try:
            self._pool = await aioodbc.create_pool(
                dsn=self._connection_string,
                minsize=2,
                maxsize=10,
                autocommit=False
            )
            logger.info(f"Connected to SimTrans: {self.server}/{self.database}")
        except Exception as e:
            logger.error(f"SimTrans connection failed: {e}")
            raise SimTransConnectionError(str(e))
    
    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            logger.info("SimTrans connection closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool with automatic cleanup."""
        if not self._pool:
            await self.connect()
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    yield cursor
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    raise SimTransQueryError(str(e))
    
    # ================================================================
    # OUTBOUND OPERATIONS (PyBase → Sigmanest)
    # ================================================================
    
    async def insert_work_order(self, work_order: SigmanestWorkOrder) -> bool:
        """
        Insert work order into SimTrans for Sigmanest processing.
        
        SimTrans picks up records with ProcessFlag = 0.
        """
        query = """
            INSERT INTO dbo.WorkOrders (
                WorkOrderID, CustomerID, CustomerName,
                OrderDate, DueDate, ShipDate,
                Priority, Notes, PONumber,
                SourceSystem, SourceID,
                ProcessFlag, CreatedDate
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                'PYBASE', ?,
                0, GETDATE()
            )
        """
        
        async with self.get_connection() as cursor:
            await cursor.execute(
                query,
                (
                    work_order.work_order_id,
                    work_order.customer_id,
                    work_order.customer_name,
                    work_order.order_date,
                    work_order.due_date,
                    work_order.ship_date,
                    work_order.priority.value,
                    work_order.notes,
                    work_order.po_number,
                    work_order.pybase_job_id,
                )
            )
            logger.info(f"Inserted work order: {work_order.work_order_id}")
            return True
    
    async def insert_part(self, part: SigmanestPart) -> bool:
        """
        Insert part into SimTrans for nesting.
        """
        query = """
            INSERT INTO dbo.Parts (
                PartID, WorkOrderID, PartNumber, Revision,
                Description, Quantity,
                MaterialCode, Thickness,
                DXFFilePath, GrainDirection,
                MirrorAllowed, RotateAllowed, RotationIncrement,
                NestPriority, ClusterQty,
                SourceSystem, SourceID,
                Status, CreatedDate
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                'PYBASE', ?,
                'Pending', GETDATE()
            )
        """
        
        async with self.get_connection() as cursor:
            await cursor.execute(
                query,
                (
                    part.part_id,
                    part.work_order_id,
                    part.part_number,
                    part.revision,
                    part.description,
                    part.quantity,
                    part.material_code,
                    float(part.thickness),
                    part.dxf_file_path,
                    part.grain_direction.value,
                    part.mirror_allowed,
                    part.rotate_allowed,
                    part.rotation_increment,
                    part.nest_priority,
                    part.cluster_quantity,
                    part.pybase_routing_id,
                )
            )
            logger.info(f"Inserted part: {part.part_id}")
            return True
    
    async def upsert_material(self, material: SigmanestMaterial) -> bool:
        """
        Upsert material inventory to SimTrans.
        Uses MERGE for insert-or-update behavior.
        """
        query = """
            MERGE dbo.MaterialInventory AS target
            USING (SELECT ? AS MaterialCode) AS source
            ON target.MaterialCode = source.MaterialCode
            WHEN MATCHED THEN
                UPDATE SET
                    Description = ?,
                    MaterialType = ?,
                    Grade = ?,
                    Thickness = ?,
                    SheetWidth = ?,
                    SheetLength = ?,
                    QuantityOnHand = ?,
                    QuantityAllocated = ?,
                    ReorderPoint = ?,
                    Location = ?,
                    UnitCost = ?,
                    HeatLot = ?,
                    ModifiedDate = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (
                    MaterialCode, Description, MaterialType, Grade,
                    Thickness, SheetWidth, SheetLength,
                    QuantityOnHand, QuantityAllocated, ReorderPoint,
                    Location, UnitCost, HeatLot,
                    CreatedDate
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    GETDATE()
                );
        """
        
        params = (
            material.material_code,
            # UPDATE params
            material.description,
            material.material_type,
            material.grade,
            float(material.thickness),
            float(material.sheet_width),
            float(material.sheet_length),
            material.quantity_on_hand,
            material.quantity_allocated,
            material.reorder_point,
            material.location,
            float(material.unit_cost),
            material.heat_lot,
            # INSERT params
            material.material_code,
            material.description,
            material.material_type,
            material.grade,
            float(material.thickness),
            float(material.sheet_width),
            float(material.sheet_length),
            material.quantity_on_hand,
            material.quantity_allocated,
            material.reorder_point,
            material.location,
            float(material.unit_cost),
            material.heat_lot,
        )
        
        async with self.get_connection() as cursor:
            await cursor.execute(query, params)
            logger.info(f"Upserted material: {material.material_code}")
            return True
    
    # ================================================================
    # INBOUND OPERATIONS (Sigmanest → PyBase)
    # ================================================================
    
    async def get_new_nest_results(self) -> List[NestResult]:
        """
        Fetch nest results that haven't been synced to PyBase.
        
        SimTrans marks processed results with SyncFlag = 1.
        """
        query = """
            SELECT 
                n.NestID, n.NestName, n.CreatedDate,
                n.SheetID, n.MaterialCode, n.Thickness,
                n.SheetWidth, n.SheetLength,
                n.Utilization, n.ScrapPercent,
                n.PartsArea, n.SheetArea,
                n.NCFilePath, n.NCFileName,
                n.MachineID, n.PostProcessor,
                n.EstCutTime, n.EstRapidTime, n.TotalCycleTime,
                n.PierceCount, n.CutLength, n.RapidLength,
                n.TotalParts, n.UniqueParts,
                n.IsReleased, n.ReleasedDate, n.ReleasedBy
            FROM dbo.NestResults n
            WHERE n.SyncFlag = 0
              AND n.Status = 'Complete'
            ORDER BY n.CreatedDate ASC
        """
        
        results = []
        async with self.get_connection() as cursor:
            await cursor.execute(query)
            rows = await cursor.fetchall()
            
            for row in rows:
                # Fetch nested parts for this nest
                parts = await self._get_nested_parts(cursor, row.NestID)
                
                result = NestResult(
                    nest_id=row.NestID,
                    nest_name=row.NestName,
                    created_at=row.CreatedDate,
                    sheet_id=row.SheetID,
                    material_code=row.MaterialCode,
                    thickness=row.Thickness,
                    sheet_width=row.SheetWidth,
                    sheet_length=row.SheetLength,
                    utilization_percent=row.Utilization,
                    scrap_percent=row.ScrapPercent,
                    parts_area_sq_in=row.PartsArea,
                    sheet_area_sq_in=row.SheetArea,
                    nc_file_path=row.NCFilePath,
                    nc_file_name=row.NCFileName,
                    machine_id=row.MachineID,
                    post_processor=row.PostProcessor,
                    estimated_cut_time_seconds=row.EstCutTime,
                    estimated_rapid_time_seconds=row.EstRapidTime or 0,
                    total_cycle_time_seconds=row.TotalCycleTime,
                    pierce_count=row.PierceCount,
                    cut_length_inches=row.CutLength,
                    rapid_length_inches=row.RapidLength or 0,
                    parts_nested=parts,
                    total_parts_count=row.TotalParts,
                    unique_parts_count=row.UniqueParts,
                    is_released=row.IsReleased,
                    released_at=row.ReleasedDate,
                    released_by=row.ReleasedBy,
                )
                results.append(result)
        
        logger.info(f"Retrieved {len(results)} new nest results")
        return results
    
    async def _get_nested_parts(
        self, 
        cursor, 
        nest_id: str
    ) -> List[NestedPart]:
        """Fetch parts placed on a specific nest."""
        query = """
            SELECT 
                PartID, WorkOrderID, Quantity,
                PositionX, PositionY, Rotation, IsMirrored
            FROM dbo.NestParts
            WHERE NestID = ?
        """
        
        await cursor.execute(query, (nest_id,))
        rows = await cursor.fetchall()
        
        return [
            NestedPart(
                part_id=row.PartID,
                work_order_id=row.WorkOrderID,
                quantity=row.Quantity,
                position_x=row.PositionX,
                position_y=row.PositionY,
                rotation_degrees=row.Rotation,
                is_mirrored=row.IsMirrored,
            )
            for row in rows
        ]
    
    async def mark_nest_result_synced(self, nest_id: str) -> bool:
        """Mark nest result as synced to PyBase."""
        query = """
            UPDATE dbo.NestResults
            SET SyncFlag = 1,
                SyncDate = GETDATE(),
                SyncTarget = 'PYBASE'
            WHERE NestID = ?
        """
        
        async with self.get_connection() as cursor:
            await cursor.execute(query, (nest_id,))
            logger.debug(f"Marked nest {nest_id} as synced")
            return True
    
    async def get_material_consumption(
        self,
        since: datetime = None
    ) -> List[MaterialConsumption]:
        """
        Fetch material consumption records for inventory updates.
        """
        query = """
            SELECT
                NestID, MaterialCode,
                SheetsPlanned, SheetsActual,
                ScrapWeight, RemnantCreated, RemnantDimensions,
                RecordedDate
            FROM dbo.MaterialConsumption
            WHERE SyncFlag = 0
            {date_filter}
            ORDER BY RecordedDate ASC
        """
        
        date_filter = ""
        params = []
        if since:
            date_filter = "AND RecordedDate > ?"
            params.append(since)
        
        query = query.format(date_filter=date_filter)
        
        async with self.get_connection() as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            
            return [
                MaterialConsumption(
                    nest_id=row.NestID,
                    material_code=row.MaterialCode,
                    sheets_planned=row.SheetsPlanned,
                    sheets_actual=row.SheetsActual,
                    scrap_weight_lbs=row.ScrapWeight,
                    remnant_created=row.RemnantCreated,
                    remnant_dimensions=row.RemnantDimensions,
                    recorded_at=row.RecordedDate,
                )
                for row in rows
            ]
    
    # ================================================================
    # HEALTH CHECK
    # ================================================================
    
    async def health_check(self) -> dict:
        """Verify connectivity and return status."""
        try:
            async with self.get_connection() as cursor:
                await cursor.execute("SELECT @@VERSION AS Version")
                row = await cursor.fetchone()
                
                # Check pending counts
                await cursor.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM dbo.WorkOrders WHERE ProcessFlag = 0) AS PendingWorkOrders,
                        (SELECT COUNT(*) FROM dbo.Parts WHERE Status = 'Pending') AS PendingParts,
                        (SELECT COUNT(*) FROM dbo.NestResults WHERE SyncFlag = 0) AS UnprocessedNests
                """)
                counts = await cursor.fetchone()
                
                return {
                    "status": "healthy",
                    "server_version": row.Version[:50] + "...",
                    "pending_work_orders": counts.PendingWorkOrders,
                    "pending_parts": counts.PendingParts,
                    "unprocessed_nests": counts.UnprocessedNests,
                    "checked_at": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat(),
            }
```

---

### Sync Service Implementation

```python
# src/pybase/integrations/sigmanest/sync_service.py

import asyncio
import hashlib
import json
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from redis.asyncio import Redis

from .simtrans_client import SimTransClient
from .models import (
    SigmanestWorkOrder,
    SigmanestPart,
    SigmanestMaterial,
    NestResult,
    SyncLogEntry,
    SyncStatus,
    SyncDirection,
)
from pybase.models.job import Job, JobRouting
from pybase.models.material import MaterialInventory
from pybase.models.schedule import ScheduleSlot
from pybase.core.database import get_async_session


class SigmanestSyncService:
    """
    Bidirectional sync service between PyBase and Sigmanest.
    
    Handles:
    - Outbound: Jobs/Parts/Materials → Sigmanest for nesting
    - Inbound: Nest results/Cut times → PyBase for scheduling
    
    Uses Redis for:
    - Sync state caching
    - Deduplication
    - Rate limiting
    """
    
    def __init__(
        self,
        simtrans: SimTransClient = None,
        redis: Redis = None,
        db_session: AsyncSession = None,
    ):
        self.simtrans = simtrans or SimTransClient()
        self.redis = redis
        self.db = db_session
        
        # Sync configuration
        self.outbound_batch_size = 50
        self.inbound_batch_size = 100
        self.retry_max_attempts = 3
        self.retry_delay_seconds = 30
    
    async def initialize(self) -> None:
        """Initialize connections."""
        await self.simtrans.connect()
        logger.info("SigmanestSyncService initialized")
    
    async def shutdown(self) -> None:
        """Cleanup connections."""
        await self.simtrans.disconnect()
    
    # ================================================================
    # FULL SYNC ORCHESTRATION
    # ================================================================
    
    async def full_sync(self) -> dict:
        """
        Execute complete bidirectional sync.
        
        Order matters:
        1. Push materials first (needed for nesting)
        2. Push work orders
        3. Push parts (depends on work orders)
        4. Pull nest results
        5. Pull material consumption
        """
        sync_id = f"sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        results = {
            "sync_id": sync_id,
            "started_at": datetime.utcnow().isoformat(),
            "operations": {},
        }
        
        try:
            # Outbound sync
            results["operations"]["materials"] = await self.push_materials()
            results["operations"]["work_orders"] = await self.push_work_orders()
            results["operations"]["parts"] = await self.push_parts()
            
            # Inbound sync
            results["operations"]["nest_results"] = await self.pull_nest_results()
            results["operations"]["consumption"] = await self.pull_material_consumption()
            
            results["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
        
        results["completed_at"] = datetime.utcnow().isoformat()
        
        # Store sync log
        await self._log_sync(results)
        
        return results
    
    # ================================================================
    # OUTBOUND OPERATIONS
    # ================================================================
    
    async def push_work_orders(self) -> dict:
        """
        Push released jobs to Sigmanest as work orders.
        
        Selection criteria:
        - Status = 'released'
        - Not already synced (sigmanest_synced = False)
        - Has parts requiring nesting
        """
        log = SyncLogEntry(
            id=f"wo_{datetime.utcnow().timestamp()}",
            sync_type="work_orders",
            direction=SyncDirection.OUTBOUND,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        
        try:
            # Get jobs ready for nesting
            result = await self.db.execute(
                select(Job)
                .where(
                    Job.status == "released",
                    Job.sigmanest_synced == False,
                    Job.requires_nesting == True,
                )
                .order_by(Job.due_date.asc())
                .limit(self.outbound_batch_size)
            )
            jobs = result.scalars().all()
            
            log.records_processed = len(jobs)
            
            for job in jobs:
                try:
                    # Check if already synced (dedup via Redis)
                    cache_key = f"sigmanest:wo:{job.id}"
                    if await self.redis.exists(cache_key):
                        logger.debug(f"Skipping already synced job: {job.id}")
                        continue
                    
                    # Map to Sigmanest model
                    work_order = self._map_job_to_work_order(job)
                    
                    # Push to SimTrans
                    await self.simtrans.insert_work_order(work_order)
                    
                    # Update job record
                    job.sigmanest_synced = True
                    job.sigmanest_sync_at = datetime.utcnow()
                    job.sigmanest_work_order_id = work_order.work_order_id
                    
                    # Cache to prevent re-sync
                    await self.redis.setex(
                        cache_key,
                        timedelta(days=7),
                        work_order.work_order_id
                    )
                    
                    log.records_succeeded += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync job {job.id}: {e}")
                    log.records_failed += 1
                    
                    # Record failure for retry
                    await self._record_sync_failure(
                        entity_type="work_order",
                        entity_id=str(job.id),
                        error=str(e)
                    )
            
            await self.db.commit()
            log.status = SyncStatus.COMPLETED
            
        except Exception as e:
            log.status = SyncStatus.FAILED
            log.error_message = str(e)
            await self.db.rollback()
        
        log.completed_at = datetime.utcnow()
        log.duration_seconds = (
            log.completed_at - log.started_at
        ).total_seconds()
        
        return log.model_dump()
    
    async def push_parts(self) -> dict:
        """
        Push part definitions for synced work orders.
        """
        log = SyncLogEntry(
            id=f"parts_{datetime.utcnow().timestamp()}",
            sync_type="parts",
            direction=SyncDirection.OUTBOUND,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        
        try:
            # Get routings for synced jobs that need nesting
            result = await self.db.execute(
                select(JobRouting)
                .join(Job, JobRouting.job_id == Job.id)
                .where(
                    Job.sigmanest_synced == True,
                    JobRouting.operation_code == "LASER",  # Only laser ops need nesting
                    JobRouting.sigmanest_synced == False,
                )
                .limit(self.outbound_batch_size)
            )
            routings = result.scalars().all()
            
            log.records_processed = len(routings)
            
            for routing in routings:
                try:
                    # Get parent job for work order reference
                    job = await self.db.get(Job, routing.job_id)
                    
                    # Map to Sigmanest part
                    part = self._map_routing_to_part(routing, job)
                    
                    # Push to SimTrans
                    await self.simtrans.insert_part(part)
                    
                    # Update routing
                    routing.sigmanest_synced = True
                    routing.sigmanest_sync_at = datetime.utcnow()
                    routing.sigmanest_part_id = part.part_id
                    
                    log.records_succeeded += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync routing {routing.id}: {e}")
                    log.records_failed += 1
            
            await self.db.commit()
            log.status = SyncStatus.COMPLETED
            
        except Exception as e:
            log.status = SyncStatus.FAILED
            log.error_message = str(e)
            await self.db.rollback()
        
        log.completed_at = datetime.utcnow()
        return log.model_dump()
    
    async def push_materials(self) -> dict:
        """
        Sync material inventory to Sigmanest.
        Only pushes materials that have changed.
        """
        log = SyncLogEntry(
            id=f"mat_{datetime.utcnow().timestamp()}",
            sync_type="materials",
            direction=SyncDirection.OUTBOUND,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        
        try:
            result = await self.db.execute(
                select(MaterialInventory)
                .where(MaterialInventory.is_active == True)
            )
            materials = result.scalars().all()
            
            log.records_processed = len(materials)
            
            for material in materials:
                try:
                    # Check if material changed (compare hash)
                    current_hash = self._compute_hash(material)
                    cache_key = f"sigmanest:mat_hash:{material.material_code}"
                    cached_hash = await self.redis.get(cache_key)
                    
                    if cached_hash and cached_hash.decode() == current_hash:
                        # No changes, skip
                        continue
                    
                    # Map and push
                    sig_material = self._map_material(material)
                    await self.simtrans.upsert_material(sig_material)
                    
                    # Update hash cache
                    await self.redis.setex(
                        cache_key,
                        timedelta(hours=24),
                        current_hash
                    )
                    
                    log.records_succeeded += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync material {material.material_code}: {e}")
                    log.records_failed += 1
            
            log.status = SyncStatus.COMPLETED
            
        except Exception as e:
            log.status = SyncStatus.FAILED
            log.error_message = str(e)
        
        log.completed_at = datetime.utcnow()
        return log.model_dump()
    
    # ================================================================
    # INBOUND OPERATIONS
    # ================================================================
    
    async def pull_nest_results(self) -> dict:
        """
        Pull completed nest results from Sigmanest.
        Updates job routings with actual cut times and creates schedule slots.
        """
        log = SyncLogEntry(
            id=f"nest_{datetime.utcnow().timestamp()}",
            sync_type="nest_results",
            direction=SyncDirection.INBOUND,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        
        try:
            # Get new nest results
            nest_results = await self.simtrans.get_new_nest_results()
            log.records_processed = len(nest_results)
            
            for nest in nest_results:
                try:
                    await self._process_nest_result(nest)
                    
                    # Mark as synced in SimTrans
                    await self.simtrans.mark_nest_result_synced(nest.nest_id)
                    
                    # Cache nest data for quick lookup
                    await self._cache_nest_result(nest)
                    
                    log.records_succeeded += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process nest {nest.nest_id}: {e}")
                    log.records_failed += 1
            
            await self.db.commit()
            log.status = SyncStatus.COMPLETED
            
        except Exception as e:
            log.status = SyncStatus.FAILED
            log.error_message = str(e)
            await self.db.rollback()
        
        log.completed_at = datetime.utcnow()
        return log.model_dump()
    
    async def _process_nest_result(self, nest: NestResult) -> None:
        """
        Process a single nest result:
        1. Update routing with actual cut time
        2. Store nest utilization metrics
        3. Create/update schedule slot
        4. Link NC file path
        """
        for nested_part in nest.parts_nested:
            # Find corresponding routing
            result = await self.db.execute(
                select(JobRouting)
                .where(JobRouting.sigmanest_part_id == nested_part.part_id)
            )
            routing = result.scalar_one_or_none()
            
            if not routing:
                logger.warning(f"No routing found for part {nested_part.part_id}")
                continue
            
            # Update routing with nest data
            routing.nest_id = nest.nest_id
            routing.nest_utilization = float(nest.utilization_percent)
            routing.actual_cut_time_seconds = nest.estimated_cut_time_seconds
            routing.nc_file_path = nest.nc_file_path
            routing.nest_synced_at = datetime.utcnow()
            
            # Calculate per-part time (proportional by quantity)
            total_parts = sum(p.quantity for p in nest.parts_nested)
            part_proportion = nested_part.quantity / total_parts
            routing.estimated_run_minutes = (
                (nest.total_cycle_time_seconds * part_proportion) / 60
            )
            
            # Create or update schedule slot
            existing_slot = await self.db.execute(
                select(ScheduleSlot)
                .where(
                    ScheduleSlot.routing_id == routing.id,
                    ScheduleSlot.status.in_(["scheduled", "ready"])
                )
            )
            slot = existing_slot.scalar_one_or_none()
            
            if slot:
                # Update existing slot with actual duration
                slot.estimated_duration_minutes = routing.estimated_run_minutes
                slot.work_center_id = nest.machine_id
                slot.status = "ready"
                slot.nc_file_path = nest.nc_file_path
            else:
                # Create new slot
                slot = ScheduleSlot(
                    routing_id=routing.id,
                    work_center_id=nest.machine_id,
                    estimated_duration_minutes=routing.estimated_run_minutes,
                    status="ready",
                    nc_file_path=nest.nc_file_path,
                )
                self.db.add(slot)
            
            logger.info(
                f"Updated routing {routing.id} with nest {nest.nest_id}, "
                f"cut time: {routing.estimated_run_minutes:.1f} min"
            )
    
    async def pull_material_consumption(self) -> dict:
        """
        Pull actual material consumption to update inventory.
        """
        log = SyncLogEntry(
            id=f"cons_{datetime.utcnow().timestamp()}",
            sync_type="material_consumption",
            direction=SyncDirection.INBOUND,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        
        try:
            # Get last sync time
            last_sync = await self.redis.get("sigmanest:last_consumption_sync")
            since = datetime.fromisoformat(last_sync.decode()) if last_sync else None
            
            consumptions = await self.simtrans.get_material_consumption(since)
            log.records_processed = len(consumptions)
            
            for consumption in consumptions:
                try:
                    # Update material inventory
                    result = await self.db.execute(
                        select(MaterialInventory)
                        .where(MaterialInventory.material_code == consumption.material_code)
                    )
                    material = result.scalar_one_or_none()
                    
                    if material:
                        # Decrement stock
                        material.quantity_on_hand -= consumption.sheets_actual
                        material.quantity_allocated -= consumption.sheets_planned
                        
                        # Check reorder point
                        if material.quantity_on_hand <= material.reorder_point:
                            await self._trigger_reorder_alert(material)
                        
                        log.records_succeeded += 1
                    else:
                        logger.warning(
                            f"Material not found: {consumption.material_code}"
                        )
                        log.records_failed += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process consumption: {e}")
                    log.records_failed += 1
            
            await self.db.commit()
            
            # Update last sync time
            await self.redis.set(
                "sigmanest:last_consumption_sync",
                datetime.utcnow().isoformat()
            )
            
            log.status = SyncStatus.COMPLETED
            
        except Exception as e:
            log.status = SyncStatus.FAILED
            log.error_message = str(e)
            await self.db.rollback()
        
        log.completed_at = datetime.utcnow()
        return log.model_dump()
    
    # ================================================================
    # MAPPING FUNCTIONS
    # ================================================================
    
    def _map_job_to_work_order(self, job: Job) -> SigmanestWorkOrder:
        """Map PyBase Job to Sigmanest WorkOrder."""
        return SigmanestWorkOrder(
            work_order_id=f"WO-{job.job_number}",
            customer_id=job.customer_id or "UNKNOWN",
            customer_name=job.customer_name or "Unknown Customer",
            order_date=job.created_at.date(),
            due_date=job.due_date,
            ship_date=job.ship_date,
            priority=self._map_priority(job.priority),
            notes=job.production_notes,
            po_number=job.po_number,
            pybase_job_id=str(job.id),
        )
    
    def _map_routing_to_part(
        self, 
        routing: JobRouting, 
        job: Job
    ) -> SigmanestPart:
        """Map PyBase JobRouting to Sigmanest Part."""
        return SigmanestPart(
            part_id=f"P-{routing.id}",
            work_order_id=f"WO-{job.job_number}",
            part_number=routing.part_number,
            revision=routing.revision or "A",
            description=routing.description,
            quantity=routing.quantity,
            material_code=routing.material_code,
            thickness=routing.thickness,
            dxf_file_path=routing.dxf_file_path,
            grain_direction=self._map_grain(routing.grain_direction),
            mirror_allowed=routing.mirror_allowed,
            rotate_allowed=routing.rotate_allowed,
            nest_priority=routing.nest_priority or 5,
            pybase_routing_id=str(routing.id),
        )
    
    def _map_material(
        self, 
        material: MaterialInventory
    ) -> SigmanestMaterial:
        """Map PyBase Material to Sigmanest Material."""
        return SigmanestMaterial(
            material_code=material.material_code,
            description=material.description,
            material_type=material.material_type,
            grade=material.grade,
            thickness=material.thickness,
            sheet_width=material.sheet_width,
            sheet_length=material.sheet_length,
            quantity_on_hand=material.quantity_on_hand,
            quantity_allocated=material.quantity_allocated,
            quantity_available=material.quantity_on_hand - material.quantity_allocated,
            reorder_point=material.reorder_point,
            location=material.location or "MAIN",
            unit_cost=material.unit_cost or 0,
            heat_lot=material.heat_lot,
            sigmanest_material_id=material.sigmanest_id,
        )
    
    @staticmethod
    def _map_priority(priority: str) -> "Priority":
        """Map PyBase priority string to Sigmanest Priority enum."""
        from .models import Priority
        mapping = {
            "rush": Priority.RUSH,
            "high": Priority.HIGH,
            "normal": Priority.NORMAL,
            "low": Priority.LOW,
        }
        return mapping.get(priority.lower(), Priority.NORMAL)
    
    @staticmethod
    def _map_grain(grain: str) -> "GrainDirection":
        """Map grain direction string to enum."""
        from .models import GrainDirection
        if grain and grain.upper() in ("X", "Y"):
            return GrainDirection(grain.upper())
        return GrainDirection.NONE
    
    # ================================================================
    # UTILITY FUNCTIONS
    # ================================================================
    
    @staticmethod
    def _compute_hash(obj) -> str:
        """Compute hash of object for change detection."""
        data = json.dumps(obj.__dict__, default=str, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()
    
    async def _cache_nest_result(self, nest: NestResult) -> None:
        """Cache nest result for quick lookup."""
        cache_key = f"sigmanest:nest:{nest.nest_id}"
        await self.redis.setex(
            cache_key,
            timedelta(days=30),
            nest.model_dump_json()
        )
    
    async def _record_sync_failure(
        self,
        entity_type: str,
        entity_id: str,
        error: str
    ) -> None:
        """Record sync failure for retry processing."""
        failure_key = f"sigmanest:failures:{entity_type}:{entity_id}"
        await self.redis.hset(
            failure_key,
            mapping={
                "error": error,
                "attempts": 1,
                "first_failure": datetime.utcnow().isoformat(),
                "last_failure": datetime.utcnow().isoformat(),
            }
        )
        await self.redis.expire(failure_key, timedelta(days=7))
    
    async def _trigger_reorder_alert(
        self, 
        material: MaterialInventory
    ) -> None:
        """Trigger alert when material hits reorder point."""
        logger.warning(
            f"Material {material.material_code} at reorder point: "
            f"{material.quantity_on_hand} <= {material.reorder_point}"
        )
        # TODO: Publish to notification service
        await self.redis.publish(
            "alerts:material_reorder",
            json.dumps({
                "material_code": material.material_code,
                "quantity_on_hand": material.quantity_on_hand,
                "reorder_point": material.reorder_point,
            })
        )
    
    async def _log_sync(self, results: dict) -> None:
        """Store sync results for monitoring."""
        log_key = f"sigmanest:sync_log:{results['sync_id']}"
        await self.redis.setex(
            log_key,
            timedelta(days=30),
            json.dumps(results)
        )
```

---

### Celery Tasks for Background Sync

```python
# src/pybase/integrations/sigmanest/tasks.py

from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio

from .sync_service import SigmanestSyncService
from pybase.core.database import get_async_session
from pybase.core.redis import get_redis

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def sync_sigmanest_full(self):
    """
    Full bidirectional sync with Sigmanest.
    Scheduled every 5 minutes via Celery Beat.
    """
    async def _run():
        async with get_async_session() as db:
            redis = await get_redis()
            service = SigmanestSyncService(db_session=db, redis=redis)
            
            try:
                await service.initialize()
                result = await service.full_sync()
                logger.info(f"Sync completed: {result['sync_id']}")
                return result
            finally:
                await service.shutdown()
    
    return asyncio.run(_run())


@shared_task(bind=True)
def sync_sigmanest_outbound(self):
    """
    Outbound-only sync (PyBase → Sigmanest).
    Use when prioritizing pushing new jobs.
    """
    async def _run():
        async with get_async_session() as db:
            redis = await get_redis()
            service = SigmanestSyncService(db_session=db, redis=redis)
            
            try:
                await service.initialize()
                results = {
                    "materials": await service.push_materials(),
                    "work_orders": await service.push_work_orders(),
                    "parts": await service.push_parts(),
                }
                return results
            finally:
                await service.shutdown()
    
    return asyncio.run(_run())


@shared_task(bind=True)
def sync_sigmanest_inbound(self):
    """
    Inbound-only sync (Sigmanest → PyBase).
    Use for pulling nest results more frequently.
    """
    async def _run():
        async with get_async_session() as db:
            redis = await get_redis()
            service = SigmanestSyncService(db_session=db, redis=redis)
            
            try:
                await service.initialize()
                results = {
                    "nest_results": await service.pull_nest_results(),
                    "consumption": await service.pull_material_consumption(),
                }
                return results
            finally:
                await service.shutdown()
    
    return asyncio.run(_run())


@shared_task(bind=True)
def retry_failed_syncs(self):
    """
    Retry previously failed sync operations.
    Scheduled every 15 minutes.
    """
    async def _run():
        redis = await get_redis()
        
        # Find failed syncs
        pattern = "sigmanest:failures:*"
        failed_keys = await redis.keys(pattern)
        
        retried = 0
        for key in failed_keys:
            failure_data = await redis.hgetall(key)
            attempts = int(failure_data.get(b"attempts", 0))
            
            if attempts < 3:  # Max retry attempts
                # Parse entity type and ID from key
                _, _, entity_type, entity_id = key.decode().split(":")
                
                # Re-queue appropriate sync
                if entity_type == "work_order":
                    sync_sigmanest_outbound.delay()
                elif entity_type == "nest_result":
                    sync_sigmanest_inbound.delay()
                
                # Increment attempt counter
                await redis.hincrby(key, "attempts", 1)
                retried += 1
        
        return {"retried_count": retried}
    
    return asyncio.run(_run())
```

---

### Celery Beat Schedule

```python
# src/pybase/celery_config.py

from celery.schedules import crontab

beat_schedule = {
    # Full sync every 5 minutes
    "sigmanest-full-sync": {
        "task": "pybase.integrations.sigmanest.tasks.sync_sigmanest_full",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "sigmanest"},
    },
    
    # More frequent inbound sync for nest results (every 2 minutes)
    "sigmanest-inbound-sync": {
        "task": "pybase.integrations.sigmanest.tasks.sync_sigmanest_inbound",
        "schedule": crontab(minute="*/2"),
        "options": {"queue": "sigmanest"},
    },
    
    # Retry failed syncs every 15 minutes
    "sigmanest-retry-failures": {
        "task": "pybase.integrations.sigmanest.tasks.retry_failed_syncs",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "sigmanest"},
    },
}
```

---

### Key Implementation Notes

| Aspect | Implementation Detail |
|--------|----------------------|
| **Deduplication** | Redis hash caching prevents duplicate syncs |
| **Change Detection** | MD5 hash comparison for materials |
| **Error Handling** | Failed syncs recorded in Redis with retry counter |
| **Transaction Safety** | Database rollback on failure |
| **Rate Limiting** | Batch sizes (50 outbound, 100 inbound) |
| **Monitoring** | Sync logs stored in Redis for 30 days |
| **Async** | Full async/await with aioodbc and asyncio |

---

Would you like me to expand on any specific part—the error handling strategy, the Redis caching patterns, or the API endpoints for manual sync triggers?