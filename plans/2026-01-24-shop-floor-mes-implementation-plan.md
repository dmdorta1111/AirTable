# Shop Floor Production Management System - Complete Implementation Plan

> **Version**: 1.0
> **Date**: January 24, 2026
> **Project**: PyBase MES Extension
> **Industry**: Custom Sheet Metal Fabrication (Commercial Kitchen & Doors/Frames)
> **Scale**: 100+ employees, 6 departments

---

## Table of Contents

1. [Phase 1: MES Foundation & Scheduling Engine](#phase-1-mes-foundation--scheduling-engine)
2. [Phase 2: Sigmanest Integration](#phase-2-sigmanest-integration)
3. [Phase 3: IoT Layer & Machine Connectivity](#phase-3-iot-layer--machine-connectivity)
4. [Phase 4: AI Agent Orchestration](#phase-4-ai-agent-orchestration)
5. [Phase 5: Advanced Features](#phase-5-advanced-features)
6. [Phase 6: Enterprise Hardening](#phase-6-enterprise-hardening)
7. [Unresolved Questions](#unresolved-questions)
8. [Risk Assessment](#risk-assessment)

---

# Phase 1: MES Foundation & Scheduling Engine

## 1.1 Overview

Build the core MES data model and finite capacity scheduling engine that will power all production planning.

**Duration**: 4 weeks
**Effort**: 160 person-hours
**Dependencies**: None (builds on existing PyBase)

## 1.2 Scheduling Algorithm Options

### Option A: Google OR-Tools CP-SAT Solver

**Description**: Google's constraint programming solver optimized for scheduling problems.

| Pros | Cons |
|------|------|
| Industry-proven, used by major manufacturers | Learning curve for constraint modeling |
| Excellent performance for job-shop scheduling | May be overkill for simpler use cases |
| Native Python bindings | Requires mathematical modeling expertise |
| Free and open source (Apache 2.0) | Debugging complex constraints is difficult |
| Handles complex constraints (no-overlap, precedence) | |

**Code Example**:
```python
from ortools.sat.python import cp_model

class JobShopScheduler:
    def __init__(self):
        self.model = cp_model.CpModel()
    
    def add_job(self, job_id: str, operations: list[Operation]):
        """Add a job with sequential operations."""
        task_vars = []
        for op in operations:
            start = self.model.NewIntVar(0, horizon, f'{job_id}_{op.id}_start')
            end = self.model.NewIntVar(0, horizon, f'{job_id}_{op.id}_end')
            interval = self.model.NewIntervalVar(
                start, op.duration, end, f'{job_id}_{op.id}_interval'
            )
            task_vars.append((start, end, interval, op.work_center))
        
        # Precedence: operations must complete in order
        for i in range(len(task_vars) - 1):
            self.model.Add(task_vars[i][1] <= task_vars[i+1][0])
        
        return task_vars
    
    def add_machine_constraint(self, machine_id: str, intervals: list):
        """No two operations on same machine at same time."""
        self.model.AddNoOverlap(intervals)
    
    def minimize_makespan(self):
        """Minimize total completion time."""
        all_ends = [t[1] for job in self.jobs for t in job]
        makespan = self.model.NewIntVar(0, horizon, 'makespan')
        self.model.AddMaxEquality(makespan, all_ends)
        self.model.Minimize(makespan)
```

**Recommendation**: ✅ **RECOMMENDED** for finite capacity scheduling

---

### Option B: Priority Dispatch Rules (Custom Implementation)

**Description**: Simple rule-based dispatching (EDD, SPT, CR, SLACK).

| Pros | Cons |
|------|------|
| Very fast execution (O(n log n)) | Suboptimal solutions |
| Easy to understand and maintain | No guarantee of feasibility |
| No external dependencies | Doesn't handle complex constraints well |
| Good for real-time dispatching | Limited optimization capability |

**Code Example**:
```python
from enum import Enum
from dataclasses import dataclass

class DispatchRule(Enum):
    EDD = "earliest_due_date"
    SPT = "shortest_processing_time"
    CR = "critical_ratio"
    SLACK = "minimum_slack"

@dataclass
class DispatchableJob:
    job_id: str
    due_date: datetime
    remaining_time: float
    operation_time: float

class PriorityDispatcher:
    def dispatch(self, jobs: list[DispatchableJob], rule: DispatchRule):
        if rule == DispatchRule.EDD:
            return sorted(jobs, key=lambda j: j.due_date)
        elif rule == DispatchRule.SPT:
            return sorted(jobs, key=lambda j: j.operation_time)
        elif rule == DispatchRule.CR:
            now = datetime.now()
            return sorted(jobs, key=lambda j: 
                (j.due_date - now).total_seconds() / j.remaining_time
            )
        elif rule == DispatchRule.SLACK:
            now = datetime.now()
            return sorted(jobs, key=lambda j:
                (j.due_date - now).total_seconds() - j.remaining_time
            )
```

**Recommendation**: ✅ Use for real-time dispatching at work centers

---

### Option C: Timefold (OptaPy successor)

**Description**: Java-based constraint solver with Python bindings (formerly OptaPy).

| Pros | Cons |
|------|------|
| Designed for enterprise scheduling | Requires JVM runtime |
| Incremental solving for dynamic environments | Heavier than OR-Tools |
| Good documentation for planning problems | Less Python-native feel |
| Supports complex soft constraints | Commercial support costs |

**Recommendation**: ⚠️ Consider only if OR-Tools insufficient

---

### Option D: Hybrid Approach (RECOMMENDED)

**Description**: Combine OR-Tools for planning with dispatch rules for execution.

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID SCHEDULING APPROACH                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐     ┌─────────────────────┐           │
│  │   PLANNING LAYER    │     │   EXECUTION LAYER   │           │
│  │   (OR-Tools CP-SAT) │     │  (Dispatch Rules)   │           │
│  ├─────────────────────┤     ├─────────────────────┤           │
│  │ • Daily/Weekly plan │     │ • Real-time queue   │           │
│  │ • Capacity loading  │────▶│ • Dynamic priority  │           │
│  │ • Constraint solving│     │ • Exception handling│           │
│  │ • Bottleneck detect │     │ • Operator override │           │
│  └─────────────────────┘     └─────────────────────┘           │
│                                                                 │
│  Run: Nightly + on-demand     Run: Every dispatch decision     │
│  Time: 30s-5min               Time: <100ms                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Recommendation**: ✅ **STRONGLY RECOMMENDED** - Best of both worlds

---

## 1.3 Data Model Design

### New Tables

```sql
-- Work Centers (machines/stations)
CREATE TABLE work_centers (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    department VARCHAR(50) NOT NULL,  -- Laser, Punch, Weld, Polish, Assembly, Ship
    machine_type VARCHAR(100),
    capacity_minutes_per_shift INTEGER DEFAULT 480,
    efficiency_factor DECIMAL(3,2) DEFAULT 0.85,
    setup_category VARCHAR(50),  -- For grouping similar setups
    is_bottleneck BOOLEAN DEFAULT FALSE,
    iot_device_id VARCHAR(100),
    sigmanest_machine_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shift Calendars
CREATE TABLE shift_calendars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    work_center_id VARCHAR(50) REFERENCES work_centers(id),
    day_of_week INTEGER,  -- 0=Monday, 6=Sunday
    shift_number INTEGER,  -- 1, 2, 3
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Holiday/Shutdown Calendar
CREATE TABLE calendar_exceptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_center_id VARCHAR(50) REFERENCES work_centers(id),
    exception_date DATE NOT NULL,
    exception_type VARCHAR(20),  -- 'holiday', 'maintenance', 'shutdown'
    description TEXT
);

-- Job Routings (operation sequence for each job)
CREATE TABLE job_routings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL,  -- References records table
    sequence INTEGER NOT NULL,
    operation_code VARCHAR(50) NOT NULL,
    work_center_type VARCHAR(50) NOT NULL,  -- Allows flexible assignment
    preferred_work_center_id VARCHAR(50) REFERENCES work_centers(id),
    setup_minutes DECIMAL(8,2) DEFAULT 0,
    run_minutes_per_unit DECIMAL(8,4) NOT NULL,
    quantity INTEGER NOT NULL,
    total_minutes DECIMAL(10,2) GENERATED ALWAYS AS 
        (setup_minutes + run_minutes_per_unit * quantity) STORED,
    dependencies JSONB DEFAULT '[]',  -- Array of routing IDs that must complete first
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schedule Slots (planned assignments)
CREATE TABLE schedule_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    routing_id UUID REFERENCES job_routings(id) ON DELETE CASCADE,
    work_center_id VARCHAR(50) REFERENCES work_centers(id),
    planned_start TIMESTAMPTZ NOT NULL,
    planned_end TIMESTAMPTZ NOT NULL,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'scheduled',
    -- 'scheduled', 'queued', 'in_progress', 'complete', 'delayed', 'cancelled'
    operator_id UUID,
    delay_reason VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for efficient schedule queries
CREATE INDEX idx_schedule_slots_workc_start 
    ON schedule_slots(work_center_id, planned_start);
CREATE INDEX idx_schedule_slots_status 
    ON schedule_slots(status) WHERE status != 'complete';
```

## 1.4 Implementation Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Create work_centers table + CRUD API | 8 hrs | P0 |
| Create shift_calendars table + API | 6 hrs | P0 |
| Create job_routings table + API | 8 hrs | P0 |
| Create schedule_slots table + API | 8 hrs | P0 |
| Implement OR-Tools scheduler service | 24 hrs | P0 |
| Implement dispatch rules service | 12 hrs | P1 |
| Enhance Gantt view for schedule display | 16 hrs | P0 |
| Department dashboard components | 16 hrs | P1 |
| Schedule conflict detection | 8 hrs | P1 |
| Bottleneck analysis endpoint | 8 hrs | P2 |

**Total Phase 1**: ~114 hours

---

# Phase 2: Sigmanest Integration

## 2.1 Overview

Integrate with Sigmanest CAD/CAM nesting software for bidirectional data flow of jobs, parts, materials, and nest results.

**Duration**: 4 weeks
**Effort**: 140 person-hours
**Dependencies**: Phase 1 complete

## 2.2 Integration Options

### Option A: SimTrans Database Integration

**Description**: Connect directly to SimTrans transaction database for real-time sync.

| Pros | Cons |
|------|------|
| Real-time bidirectional sync | Requires DB access (firewall/VPN) |
| Full data access | Tightly coupled to Sigmanest schema |
| Battle-tested approach | Schema changes can break integration |
| Transaction-based reliability | No official API contract |

**Architecture**:
```
┌─────────────────┐         ┌─────────────────┐
│     PyBase      │         │   SimTrans DB   │
│   PostgreSQL    │◄───────►│  (SQL Server)   │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │    Sync Service           │
         │    (Celery Worker)        │
         │                           │
         ▼                           ▼
┌─────────────────────────────────────────────┐
│           Sigmanest Integration Hub          │
│  ┌─────────────┐  ┌─────────────┐           │
│  │ Outbound    │  │ Inbound     │           │
│  │ - WorkOrders│  │ - NestResults│          │
│  │ - Parts     │  │ - CutTimes   │          │
│  │ - Materials │  │ - Utilization│          │
│  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────┘
```

**SimTrans Key Tables** (based on research):
```sql
-- Work Orders table (outbound from PyBase)
SELECT * FROM dbo.WorkOrders WHERE ProcessFlag = 0;

-- Parts table (outbound from PyBase)
SELECT * FROM dbo.Parts WHERE Status = 'Pending';

-- Nest Results table (inbound to PyBase)
SELECT 
    NestID, SheetID, PartID, 
    Utilization, ScrapPercent,
    CutTime, PierceCount
FROM dbo.NestResults WHERE SyncFlag = 0;

-- Material Inventory (bidirectional)
SELECT 
    MaterialCode, Thickness, 
    SheetWidth, SheetLength,
    QuantityOnHand, Location
FROM dbo.MaterialInventory;
```

**Recommendation**: ✅ **RECOMMENDED** - Most reliable approach

---

### Option B: File-Based Exchange

**Description**: Export/import via XML/CSV files in watched directories.

| Pros | Cons |
|------|------|
| Simple to implement | Not real-time (batch delays) |
| No direct DB coupling | File handling complexity |
| Works with any Sigmanest version | Error handling difficult |
| Firewall-friendly | Manual intervention often needed |

**Recommendation**: ⚠️ Fallback option only

---

### Option C: CADTALK Middleware

**Description**: Use CADTALK's commercial integration platform.

| Pros | Cons |
|------|------|
| Pre-built Sigmanest connector | Significant license cost ($20K-50K) |
| Handles schema changes | Another vendor dependency |
| Professional support | Overkill for single integration |
| ERP adapters included | |

**Recommendation**: ⚠️ Consider if budget allows and multiple ERP integrations needed

---

## 2.3 Data Exchange Specification

### Outbound (PyBase → Sigmanest)

```python
# schemas/sigmanest.py

from pydantic import BaseModel
from datetime import date
from typing import Optional

class SigmanestWorkOrder(BaseModel):
    """Work order pushed to Sigmanest."""
    work_order_id: str
    customer_name: str
    order_date: date
    due_date: date
    priority: int  # 1=Rush, 2=High, 3=Normal, 4=Low
    notes: Optional[str] = None

class SigmanestPart(BaseModel):
    """Part definition for nesting."""
    part_id: str
    work_order_id: str
    part_number: str
    revision: str
    quantity: int
    material_code: str
    thickness: float
    dxf_file_path: str
    grain_direction: Optional[str] = None  # 'X', 'Y', 'NONE'
    
class SigmanestMaterial(BaseModel):
    """Material inventory sync."""
    material_code: str
    description: str
    thickness: float
    sheet_width: float
    sheet_length: float
    quantity: int
    unit_cost: float
    location: str
```

### Inbound (Sigmanest → PyBase)

```python
class NestResult(BaseModel):
    """Nest result from Sigmanest."""
    nest_id: str
    sheet_id: str
    material_code: str
    sheet_width: float
    sheet_length: float
    utilization_percent: float
    scrap_percent: float
    parts_nested: list[NestedPart]
    nc_file_path: str
    machine_id: str
    estimated_cut_time_seconds: int
    pierce_count: int
    cut_length_inches: float
    created_at: datetime

class NestedPart(BaseModel):
    """Individual part placement in nest."""
    part_id: str
    work_order_id: str
    quantity: int
    rotation_degrees: float
    position_x: float
    position_y: float
```

## 2.4 Sync Service Implementation

```python
# src/pybase/integrations/sigmanest/sync_service.py

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from celery import shared_task

class SigmanestSyncService:
    """Bidirectional sync with Sigmanest SimTrans."""
    
    def __init__(self, simtrans_url: str, pybase_session: AsyncSession):
        self.simtrans = SimTransClient(simtrans_url)
        self.db = pybase_session
    
    async def push_work_orders(self):
        """Push new work orders to Sigmanest."""
        # Get jobs ready for nesting
        jobs = await self.db.execute(
            select(Job).where(
                Job.status == 'released',
                Job.sigmanest_synced == False
            )
        )
        
        for job in jobs.scalars():
            work_order = self._map_to_sigmanest_wo(job)
            parts = await self._get_job_parts(job.id)
            
            # Push to SimTrans
            await self.simtrans.insert_work_order(work_order)
            for part in parts:
                await self.simtrans.insert_part(part)
            
            # Mark as synced
            job.sigmanest_synced = True
            job.sigmanest_sync_at = datetime.utcnow()
        
        await self.db.commit()
    
    async def pull_nest_results(self):
        """Pull completed nest results from Sigmanest."""
        results = await self.simtrans.get_new_nest_results()
        
        for result in results:
            # Update job routing with actual times
            for part in result.parts_nested:
                routing = await self.db.get(JobRouting, part.routing_id)
                if routing:
                    routing.actual_cut_time = result.estimated_cut_time
                    routing.nest_utilization = result.utilization_percent
                    routing.nc_file_path = result.nc_file_path
            
            # Create schedule slot for cutting
            slot = ScheduleSlot(
                routing_id=routing.id,
                work_center_id=result.machine_id,
                estimated_duration=result.estimated_cut_time_seconds / 60,
                status='ready'
            )
            self.db.add(slot)
            
            # Mark result as processed
            await self.simtrans.mark_result_processed(result.nest_id)
        
        await self.db.commit()

@shared_task
def sync_sigmanest():
    """Celery task for periodic sync."""
    asyncio.run(SigmanestSyncService().full_sync())
```

## 2.5 Implementation Tasks

| Task | Effort | Priority |
|------|--------|----------|
| SimTrans DB connector (pyodbc/aioodbc) | 12 hrs | P0 |
| Work order outbound sync | 16 hrs | P0 |
| Parts outbound sync | 12 hrs | P0 |
| Nest results inbound sync | 16 hrs | P0 |
| Material inventory bidirectional sync | 12 hrs | P1 |
| NC file management (path resolution) | 8 hrs | P1 |
| Sync status dashboard | 12 hrs | P1 |
| Error handling & retry logic | 12 hrs | P0 |
| Celery beat schedule configuration | 4 hrs | P1 |
| Integration tests with mock SimTrans | 16 hrs | P2 |

**Total Phase 2**: ~120 hours

---

# Phase 3: IoT Layer & Machine Connectivity

## 3.1 Overview

Implement real-time machine monitoring across all departments using industrial IoT protocols.

**Duration**: 4 weeks
**Effort**: 160 person-hours
**Dependencies**: Phase 1 work centers defined

## 3.2 Protocol Selection

### Option A: MTConnect (Laser Cutters)

**Description**: Standard protocol for CNC machine data.

| Pros | Cons |
|------|------|
| Industry standard for CNC | XML-based (verbose) |
| Rich data model for machining | Requires MTConnect agent on machine |
| Free and open source | Not all machines support natively |
| Good for laser/punch/mill | Read-only (no control) |

**Python Implementation**:
```python
# src/pybase/iot/protocols/mtconnect_client.py

import httpx
from xml.etree import ElementTree
from dataclasses import dataclass

@dataclass
class MTConnectDataItem:
    name: str
    value: str | float
    timestamp: datetime
    category: str  # SAMPLE, EVENT, CONDITION

class MTConnectClient:
    """Client for MTConnect Agent."""
    
    def __init__(self, agent_url: str):
        self.agent_url = agent_url
        self.client = httpx.AsyncClient()
    
    async def get_current(self, path: str = "") -> list[MTConnectDataItem]:
        """Get current state of all data items."""
        url = f"{self.agent_url}/current{path}"
        response = await self.client.get(url)
        return self._parse_streams(response.text)
    
    async def stream_samples(self, interval_ms: int = 1000):
        """Stream data items as they change."""
        url = f"{self.agent_url}/sample?interval={interval_ms}"
        async with self.client.stream("GET", url) as response:
            async for chunk in response.aiter_text():
                yield self._parse_streams(chunk)
    
    def _parse_streams(self, xml_text: str) -> list[MTConnectDataItem]:
        root = ElementTree.fromstring(xml_text)
        items = []
        for stream in root.findall(".//DeviceStream"):
            for item in stream.findall(".//*[@dataItemId]"):
                items.append(MTConnectDataItem(
                    name=item.get("dataItemId"),
                    value=self._parse_value(item),
                    timestamp=item.get("timestamp"),
                    category=item.tag
                ))
        return items
```

**Recommendation**: ✅ **RECOMMENDED** for laser cutters and CNC machines

---

### Option B: OPC-UA (Punch Presses, PLCs)

**Description**: Universal industrial communication protocol.

| Pros | Cons |
|------|------|
| Read AND write capability | More complex setup |
| Secure (encryption, auth) | Requires OPC-UA server on machine |
| Hierarchical data model | Learning curve |
| Widely supported by PLCs | |

**Python Implementation (asyncua)**:
```python
# src/pybase/iot/protocols/opcua_client.py

from asyncua import Client, ua
from asyncua.common.subscription import DataChangeNotif

class OPCUAMachineClient:
    """OPC-UA client for industrial machines."""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = Client(endpoint)
        self.subscriptions = {}
    
    async def connect(self):
        await self.client.connect()
        # Get namespace for machine data
        self.ns = await self.client.get_namespace_index(
            "http://opcfoundation.org/UA/Machinery/"
        )
    
    async def subscribe_machine_status(self, callback):
        """Subscribe to machine status changes."""
        handler = StatusHandler(callback)
        subscription = await self.client.create_subscription(
            period=500,  # 500ms update rate
            handler=handler
        )
        
        # Subscribe to standard Machinery nodes
        nodes = [
            await self.client.nodes.root.get_child(
                f"0:Objects/{self.ns}:Machines/{self.ns}:Machine1/{self.ns}:Status"
            ),
            await self.client.nodes.root.get_child(
                f"0:Objects/{self.ns}:Machines/{self.ns}:Machine1/{self.ns}:PartCount"
            ),
        ]
        await subscription.subscribe_data_change(nodes)
    
    async def read_production_data(self) -> dict:
        """Read current production metrics."""
        return {
            "part_count": await self._read_node("PartCount"),
            "cycle_time": await self._read_node("CycleTime"),
            "status": await self._read_node("MachineStatus"),
            "alarm_active": await self._read_node("AlarmActive"),
        }

class StatusHandler:
    def __init__(self, callback):
        self.callback = callback
    
    def datachange_notification(self, node, val, data):
        asyncio.create_task(self.callback(node, val))
```

**Recommendation**: ✅ **RECOMMENDED** for punch presses, PLCs, modern CNC

---

### Option C: MQTT + Sensors (Welding, Polishing, Assembly)

**Description**: Lightweight pub/sub for custom sensors and I/O.

| Pros | Cons |
|------|------|
| Very lightweight | No standard data model |
| Works with any sensor | Requires custom adapters |
| Real-time pub/sub | Less robust than OPC-UA |
| Easy to implement | |

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────┐
│                      MQTT TOPIC STRUCTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  shopfloor/                                                     │
│  ├── laser/                                                     │
│  │   ├── LASER-01/status          → {"state": "running"}       │
│  │   ├── LASER-01/metrics         → {"cut_time": 45.2}         │
│  │   └── LASER-01/alarms          → {"code": "E001"}           │
│  ├── punch/                                                     │
│  │   ├── PUNCH-01/status                                        │
│  │   └── PUNCH-01/metrics                                       │
│  ├── weld/                                                      │
│  │   ├── WELD-01/arc_on           → true/false                 │
│  │   ├── WELD-01/wire_feed        → {"rate": 250}              │
│  │   └── WELD-01/gas_flow         → {"cfh": 35}                │
│  └── assembly/                                                  │
│      ├── ASSY-01/part_scanned     → {"part_id": "..."}         │
│      └── ASSY-01/cycle_complete   → {"job_id": "..."}          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Python Implementation**:
```python
# src/pybase/iot/protocols/mqtt_handler.py

import asyncio
import aiomqtt
from pydantic import BaseModel

class MachineStatus(BaseModel):
    machine_id: str
    state: str  # 'idle', 'running', 'alarm', 'setup', 'offline'
    job_id: str | None
    part_count: int
    cycle_time_seconds: float

class MQTTShopFloorHandler:
    """MQTT handler for shop floor data collection."""
    
    def __init__(self, broker: str, port: int = 1883):
        self.broker = broker
        self.port = port
        self.callbacks = {}
    
    async def connect_and_subscribe(self):
        async with aiomqtt.Client(self.broker, self.port) as client:
            # Subscribe to all shop floor topics
            await client.subscribe("shopfloor/#")
            
            async for message in client.messages:
                topic = str(message.topic)
                payload = message.payload.decode()
                await self._handle_message(topic, payload)
    
    async def _handle_message(self, topic: str, payload: str):
        # Parse topic: shopfloor/{dept}/{machine}/{metric}
        parts = topic.split("/")
        if len(parts) >= 4:
            dept, machine, metric = parts[1], parts[2], parts[3]
            
            # Update machine status in Redis
            await self.redis.hset(
                f"machine:{machine}",
                metric,
                payload
            )
            
            # Store in TimescaleDB for history
            await self.timescale.insert_metric(
                machine_id=machine,
                metric_name=metric,
                value=json.loads(payload),
                timestamp=datetime.utcnow()
            )
```

**Recommendation**: ✅ **RECOMMENDED** for welding, polishing, assembly stations

---

## 3.3 Time-Series Database Selection

### Option A: TimescaleDB (PostgreSQL Extension)

| Pros | Cons |
|------|------|
| Native PostgreSQL (same stack) | Slightly slower than InfluxDB |
| SQL queries | Requires PostgreSQL expertise |
| Continuous aggregates | |
| Compression | |

### Option B: InfluxDB

| Pros | Cons |
|------|------|
| Purpose-built for time-series | Separate database to manage |
| Flux query language | Different query syntax |
| Better raw write performance | |

**Recommendation**: ✅ **TimescaleDB** - Keeps everything in PostgreSQL

**Schema**:
```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Machine metrics hypertable
CREATE TABLE machine_metrics (
    time TIMESTAMPTZ NOT NULL,
    machine_id VARCHAR(50) NOT NULL,
    department VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value_numeric DOUBLE PRECISION,
    value_text VARCHAR(255),
    job_id VARCHAR(50),
    operator_id UUID,
    CONSTRAINT machine_metrics_pkey PRIMARY KEY (time, machine_id, metric_name)
);

-- Convert to hypertable with 1-day chunks
SELECT create_hypertable('machine_metrics', 'time', chunk_time_interval => INTERVAL '1 day');

-- Create continuous aggregate for hourly OEE
CREATE MATERIALIZED VIEW machine_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    machine_id,
    department,
    COUNT(*) FILTER (WHERE metric_name = 'cycle_complete') AS cycles,
    AVG(value_numeric) FILTER (WHERE metric_name = 'cycle_time') AS avg_cycle_time,
    SUM(value_numeric) FILTER (WHERE metric_name = 'downtime_minutes') AS downtime,
    SUM(value_numeric) FILTER (WHERE metric_name = 'good_parts') AS good_parts,
    SUM(value_numeric) FILTER (WHERE metric_name = 'scrap_parts') AS scrap_parts
FROM machine_metrics
GROUP BY bucket, machine_id, department;

-- Retention policy: keep raw data 90 days
SELECT add_retention_policy('machine_metrics', INTERVAL '90 days');

-- Compression after 7 days
SELECT add_compression_policy('machine_metrics', INTERVAL '7 days');
```

## 3.4 Edge Gateway Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       EDGE GATEWAY DESIGN                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Per Department: Industrial PC or Raspberry Pi 4               │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │                   Edge Gateway                         │     │
│  │  ┌─────────────────────────────────────────────────┐  │     │
│  │  │            Protocol Adapters                     │  │     │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐           │  │     │
│  │  │  │MTConnect│ │ OPC-UA  │ │Modbus/IO│           │  │     │
│  │  │  └────┬────┘ └────┬────┘ └────┬────┘           │  │     │
│  │  └───────┼───────────┼───────────┼────────────────┘  │     │
│  │          │           │           │                    │     │
│  │          ▼           ▼           ▼                    │     │
│  │  ┌─────────────────────────────────────────────────┐  │     │
│  │  │         Local Buffer (SQLite/Redis)             │  │     │
│  │  │     Survives network outages up to 24hrs        │  │     │
│  │  └────────────────────┬────────────────────────────┘  │     │
│  │                       │                               │     │
│  │                       ▼                               │     │
│  │  ┌─────────────────────────────────────────────────┐  │     │
│  │  │              MQTT Publisher                      │  │     │
│  │  │      QoS 1 for reliability                      │  │     │
│  │  └─────────────────────────────────────────────────┘  │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3.5 Implementation Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Set up MQTT broker (Mosquitto) | 4 hrs | P0 |
| TimescaleDB setup and schema | 8 hrs | P0 |
| MTConnect client library | 16 hrs | P0 |
| OPC-UA client library | 16 hrs | P0 |
| MQTT handler service | 12 hrs | P0 |
| Edge gateway software (Python) | 24 hrs | P1 |
| Machine status Redis cache | 8 hrs | P0 |
| Real-time WebSocket broadcast | 12 hrs | P1 |
| Department status dashboard | 16 hrs | P1 |
| Alarm handling and notifications | 12 hrs | P2 |

**Total Phase 3**: ~128 hours

---

# Phase 4: AI Agent Orchestration

## 4.1 Overview

Implement multi-agent AI system for intelligent scheduling, dispatching, and production optimization using LangGraph.

**Duration**: 4 weeks
**Effort**: 160 person-hours
**Dependencies**: Phases 1-3 complete

## 4.2 Framework Selection

### Option A: LangGraph (RECOMMENDED)

| Pros | Cons |
|------|------|
| State checkpoints (PostgreSQL) | Newer framework |
| Human-in-the-loop built-in | Documentation evolving |
| Graph-based workflow | Requires LangChain familiarity |
| LangSmith observability | |
| Production-proven | |

### Option B: CrewAI

| Pros | Cons |
|------|------|
| Role-based agent design | Less control over flow |
| Quick prototyping | Weaker state management |
| Good for fixed workflows | No checkpointing |

### Option C: AutoGen (Microsoft)

| Pros | Cons |
|------|------|
| Flexible conversation patterns | Complex setup |
| Good for research | Less production-ready |
| Multi-agent debugging | Heavier resource usage |

**Recommendation**: ✅ **LangGraph** - Best for manufacturing with human oversight

## 4.3 Agent Architecture

```python
# src/pybase/ai_agents/manufacturing_graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import TypedDict, Annotated
from operator import add

class ManufacturingState(TypedDict):
    """State shared across all agents."""
    request: str
    request_type: str  # 'schedule', 'dispatch', 'material', 'quality', 'capacity'
    context: dict
    
    # Scheduling outputs
    schedule_changes: Annotated[list, add]
    conflicts_detected: list
    
    # Material outputs
    material_alerts: list
    reorder_suggestions: list
    
    # Quality outputs
    quality_issues: list
    root_causes: list
    
    # Human interaction
    requires_approval: bool
    approval_reason: str
    approved: bool | None
    
    # Final response
    final_response: str
    actions_taken: Annotated[list, add]

def build_manufacturing_graph():
    """Build the multi-agent manufacturing graph."""
    
    graph = StateGraph(ManufacturingState)
    
    # Add agent nodes
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("scheduler", scheduler_agent)
    graph.add_node("dispatcher", dispatcher_agent)
    graph.add_node("material_optimizer", material_agent)
    graph.add_node("quality_monitor", quality_agent)
    graph.add_node("capacity_planner", capacity_agent)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("execute_actions", action_executor)
    
    # Supervisor routes to specialists
    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_to_specialist,
        {
            "schedule": "scheduler",
            "dispatch": "dispatcher",
            "material": "material_optimizer",
            "quality": "quality_monitor",
            "capacity": "capacity_planner",
            "human": "human_approval",
        }
    )
    
    # All specialists can request human approval
    for agent in ["scheduler", "dispatcher", "material_optimizer", 
                   "quality_monitor", "capacity_planner"]:
        graph.add_conditional_edges(
            agent,
            check_needs_approval,
            {
                "needs_approval": "human_approval",
                "execute": "execute_actions",
                "done": END
            }
        )
    
    # Human approval leads to execution or supervisor
    graph.add_conditional_edges(
        "human_approval",
        handle_approval_result,
        {
            "approved": "execute_actions",
            "rejected": "supervisor",
            "timeout": END
        }
    )
    
    graph.add_edge("execute_actions", END)
    
    # Compile with PostgreSQL checkpointing
    checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
    return graph.compile(checkpointer=checkpointer)
```

## 4.4 Agent Implementations

### Scheduler Agent
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

SCHEDULER_SYSTEM = """You are a production scheduling expert for a sheet metal fabrication shop.
Your job is to analyze scheduling requests and propose optimal job sequences.

Available work centers: {work_centers}
Current schedule load: {schedule_summary}
Pending jobs: {pending_jobs}

Consider:
1. Due dates and customer priorities
2. Setup time optimization (batch similar materials)
3. Bottleneck work centers
4. Sigmanest nest grouping opportunities

Output your recommendations as structured actions."""

async def scheduler_agent(state: ManufacturingState) -> ManufacturingState:
    """Scheduling specialist agent."""
    
    # Load context
    work_centers = await get_work_centers()
    schedule_summary = await get_schedule_summary()
    pending_jobs = await get_pending_jobs()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SCHEDULER_SYSTEM),
        ("human", "{request}")
    ])
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chain = prompt | llm | ScheduleOutputParser()
    
    result = await chain.ainvoke({
        "work_centers": work_centers,
        "schedule_summary": schedule_summary,
        "pending_jobs": pending_jobs,
        "request": state["request"]
    })
    
    # Check if changes affect >3 jobs or require overtime
    requires_approval = (
        len(result.affected_jobs) > 3 or 
        result.requires_overtime or
        result.affects_rush_orders
    )
    
    return {
        **state,
        "schedule_changes": result.changes,
        "conflicts_detected": result.conflicts,
        "requires_approval": requires_approval,
        "approval_reason": result.approval_reason if requires_approval else None
    }
```

### Human-in-the-Loop Node
```python
async def human_approval_node(state: ManufacturingState) -> ManufacturingState:
    """Wait for human approval with timeout."""
    
    # Create approval request in database
    approval_request = await create_approval_request(
        request_type=state["request_type"],
        changes=state["schedule_changes"],
        reason=state["approval_reason"],
        requested_by="ai_scheduler"
    )
    
    # Send notification to supervisors
    await notify_supervisors(
        title=f"AI Scheduling Approval Required",
        body=state["approval_reason"],
        approval_url=f"/approvals/{approval_request.id}"
    )
    
    # This will pause the graph until interrupt_after fires
    # The checkpoint allows resumption after human decision
    return {
        **state,
        "awaiting_approval_id": approval_request.id
    }
```

## 4.5 FastAPI Integration

```python
# src/pybase/api/v1/ai_agents.py

from fastapi import APIRouter, BackgroundTasks
from langgraph.checkpoint.postgres import PostgresSaver

router = APIRouter(prefix="/ai", tags=["AI Agents"])

@router.post("/schedule/optimize")
async def optimize_schedule(
    request: ScheduleOptimizationRequest,
    background_tasks: BackgroundTasks
):
    """Trigger AI-assisted schedule optimization."""
    
    # Create new thread for this conversation
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Run graph asynchronously
    graph = get_manufacturing_graph()
    
    async def run_optimization():
        result = await graph.ainvoke(
            {"request": request.prompt, "request_type": "schedule"},
            config
        )
        # Store result for polling
        await cache.set(f"ai_result:{thread_id}", result, ex=3600)
    
    background_tasks.add_task(run_optimization)
    
    return {"thread_id": thread_id, "status": "processing"}

@router.get("/schedule/{thread_id}/status")
async def get_optimization_status(thread_id: str):
    """Get status of AI optimization."""
    
    graph = get_manufacturing_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    # Get current state from checkpoint
    state = await graph.aget_state(config)
    
    if state.values.get("awaiting_approval_id"):
        return {
            "status": "awaiting_approval",
            "approval_id": state.values["awaiting_approval_id"]
        }
    
    result = await cache.get(f"ai_result:{thread_id}")
    if result:
        return {"status": "complete", "result": result}
    
    return {"status": "processing"}

@router.post("/approvals/{approval_id}/respond")
async def respond_to_approval(
    approval_id: str,
    response: ApprovalResponse
):
    """Human responds to AI approval request."""
    
    approval = await get_approval_request(approval_id)
    thread_id = approval.thread_id
    
    graph = get_manufacturing_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    # Resume graph with approval decision
    await graph.aupdate_state(
        config,
        {"approved": response.approved, "approval_notes": response.notes}
    )
    
    # Continue execution
    result = await graph.ainvoke(None, config)
    
    return {"status": "resumed", "result": result}
```

## 4.6 Implementation Tasks

| Task | Effort | Priority |
|------|--------|----------|
| LangGraph setup with PostgreSQL checkpointer | 8 hrs | P0 |
| Supervisor agent | 12 hrs | P0 |
| Scheduler agent | 16 hrs | P0 |
| Dispatcher agent | 12 hrs | P1 |
| Material optimizer agent | 12 hrs | P1 |
| Quality monitor agent | 12 hrs | P2 |
| Capacity planner agent | 12 hrs | P2 |
| Human approval workflow | 16 hrs | P0 |
| FastAPI endpoints | 12 hrs | P0 |
| WebSocket streaming for results | 8 hrs | P1 |
| LangSmith integration | 8 hrs | P2 |

**Total Phase 4**: ~128 hours

---

# Phase 5: Advanced Features

## 5.1 Overview

Implement OEE dashboards, mobile operator app, and advanced analytics.

**Duration**: 8 weeks
**Effort**: 240 person-hours
**Dependencies**: Phases 1-4 complete

## 5.2 OEE Dashboard

### OEE Calculation
```
OEE = Availability × Performance × Quality

Availability = (Planned Production Time - Downtime) / Planned Production Time
Performance = (Ideal Cycle Time × Total Parts) / Operating Time  
Quality = Good Parts / Total Parts
```

### Industry Benchmarks
| Metric | World Class | Typical | Sheet Metal Target |
|--------|-------------|---------|-------------------|
| OEE | 85%+ | 60% | 75% |
| Availability | 90%+ | 80% | 85% |
| Performance | 95%+ | 85% | 90% |
| Quality | 99%+ | 95% | 98% |

### Dashboard Components (React)
```typescript
// frontend/src/components/oee/OEEDashboard.tsx

import { Card, Metric, AreaChart, DonutChart } from "@tremor/react";
import { useOEEData, useMachineStatus } from "@/hooks/manufacturing";

export function OEEDashboard({ departmentId }: { departmentId: string }) {
  const { oee, trend } = useOEEData(departmentId);
  const machines = useMachineStatus(departmentId);
  
  return (
    <div className="grid grid-cols-12 gap-4">
      {/* OEE Gauges */}
      <Card className="col-span-3">
        <Title>Overall OEE</Title>
        <DonutChart
          data={[
            { name: "OEE", value: oee.overall },
            { name: "Gap", value: 100 - oee.overall }
          ]}
          category="value"
          index="name"
          colors={[oee.overall >= 75 ? "green" : "red", "gray"]}
        />
        <Metric>{oee.overall.toFixed(1)}%</Metric>
      </Card>
      
      {/* Component Metrics */}
      <Card className="col-span-3">
        <Title>Availability</Title>
        <Metric>{oee.availability.toFixed(1)}%</Metric>
        <Text>Target: 85%</Text>
      </Card>
      
      <Card className="col-span-3">
        <Title>Performance</Title>
        <Metric>{oee.performance.toFixed(1)}%</Metric>
        <Text>Target: 90%</Text>
      </Card>
      
      <Card className="col-span-3">
        <Title>Quality</Title>
        <Metric>{oee.quality.toFixed(1)}%</Metric>
        <Text>Target: 98%</Text>
      </Card>
      
      {/* Trend Chart */}
      <Card className="col-span-12">
        <Title>OEE Trend (7 Days)</Title>
        <AreaChart
          data={trend}
          index="date"
          categories={["availability", "performance", "quality", "oee"]}
          colors={["blue", "amber", "green", "purple"]}
        />
      </Card>
      
      {/* Machine Status Grid */}
      <Card className="col-span-12">
        <Title>Machine Status</Title>
        <div className="grid grid-cols-6 gap-2">
          {machines.map(m => (
            <MachineStatusCard key={m.id} machine={m} />
          ))}
        </div>
      </Card>
    </div>
  );
}
```

## 5.3 Mobile Operator App

### Technology Choice

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| React Native | Same codebase, JS expertise | Native module challenges | ✅ RECOMMENDED |
| Flutter | Fast, beautiful UI | Dart learning curve | Consider |
| PWA | No app store, instant updates | Limited device access | Quick MVP |

### Key Features
1. **Barcode/QR Scanning** - Scan job travelers, parts
2. **Work Queue** - See assigned jobs
3. **Time Tracking** - Clock in/out of operations
4. **Issue Reporting** - Log quality issues, downtime
5. **Offline Support** - Works without network

### React Native Implementation
```typescript
// mobile/src/screens/OperatorQueue.tsx

import { useSuspenseQuery } from "@tanstack/react-query";
import { useBarcodeScan } from "@/hooks/useBarcodeScan";

export function OperatorQueue() {
  const { data: queue } = useSuspenseQuery({
    queryKey: ["operator-queue", operatorId],
    queryFn: () => api.getOperatorQueue(operatorId)
  });
  
  const { scan } = useBarcodeScan({
    onScan: async (code) => {
      // Start operation
      await api.startOperation({
        barcode: code,
        operatorId,
        timestamp: new Date()
      });
    }
  });
  
  return (
    <View>
      <Text style={styles.header}>Your Queue</Text>
      <FlatList
        data={queue}
        renderItem={({ item }) => (
          <JobCard 
            job={item}
            onStart={() => scan()}
          />
        )}
      />
      <Button title="Scan Job" onPress={scan} />
    </View>
  );
}
```

## 5.4 Implementation Tasks

| Task | Effort | Priority |
|------|--------|----------|
| OEE calculation service | 16 hrs | P0 |
| OEE dashboard (React/Tremor) | 24 hrs | P0 |
| Machine status grid component | 12 hrs | P0 |
| Department TV display view | 12 hrs | P1 |
| React Native project setup | 8 hrs | P1 |
| Operator queue screen | 16 hrs | P1 |
| Barcode scanning integration | 12 hrs | P1 |
| Time tracking (clock in/out) | 16 hrs | P1 |
| Issue reporting form | 12 hrs | P2 |
| Offline sync (WatermelonDB) | 24 hrs | P2 |
| Push notifications | 12 hrs | P2 |
| Downtime Pareto analysis | 16 hrs | P2 |

**Total Phase 5**: ~180 hours

---

# Phase 6: Enterprise Hardening

## 6.1 Overview

Prepare system for production deployment with high availability, security, and monitoring.

**Duration**: 6 weeks
**Effort**: 200 person-hours
**Dependencies**: Phases 1-5 complete

## 6.2 High Availability Architecture

### PostgreSQL HA with Patroni

```yaml
# docker-compose.ha.yml

services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.9
    environment:
      ETCD_LISTEN_CLIENT_URLS: http://0.0.0.0:2379
      ETCD_ADVERTISE_CLIENT_URLS: http://etcd:2379
    
  patroni1:
    image: patroni:latest
    environment:
      PATRONI_NAME: pg1
      PATRONI_POSTGRESQL_CONNECT_ADDRESS: patroni1:5432
      PATRONI_RESTAPI_CONNECT_ADDRESS: patroni1:8008
      PATRONI_ETCD_URL: http://etcd:2379
      PATRONI_POSTGRESQL_DATA_DIR: /data/pg
    volumes:
      - pg1_data:/data/pg
    
  patroni2:
    image: patroni:latest
    environment:
      PATRONI_NAME: pg2
      PATRONI_POSTGRESQL_CONNECT_ADDRESS: patroni2:5432
      PATRONI_RESTAPI_CONNECT_ADDRESS: patroni2:8008
      PATRONI_ETCD_URL: http://etcd:2379
    volumes:
      - pg2_data:/data/pg
      
  haproxy:
    image: haproxy:2.8
    ports:
      - "5432:5432"
      - "5433:5433"  # Read replicas
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg
```

### Redis Sentinel
```yaml
  redis-master:
    image: redis:7-alpine
    
  redis-replica:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379
    
  redis-sentinel:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./sentinel.conf:/etc/redis/sentinel.conf
```

## 6.3 Kubernetes Deployment

### Helm Chart Structure
```
helm/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── hpa.yaml
│   └── pdb.yaml
```

### Key Manifests
```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pybase-api
spec:
  replicas: {{ .Values.api.replicas }}
  selector:
    matchLabels:
      app: pybase-api
  template:
    spec:
      containers:
        - name: api
          image: "{{ .Values.api.image }}:{{ .Values.api.tag }}"
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: pybase-secrets
                  key: database-url
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5

---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pybase-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pybase-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## 6.4 Security

### RBAC for Manufacturing Roles
```python
# src/pybase/core/permissions.py

from enum import Enum
from typing import Set

class Permission(str, Enum):
    # Scheduling
    SCHEDULE_VIEW = "schedule:view"
    SCHEDULE_EDIT = "schedule:edit"
    SCHEDULE_APPROVE = "schedule:approve"
    
    # Jobs
    JOB_VIEW = "job:view"
    JOB_CREATE = "job:create"
    JOB_RELEASE = "job:release"
    
    # Machines
    MACHINE_VIEW = "machine:view"
    MACHINE_CONFIG = "machine:config"
    
    # Reports
    REPORT_VIEW = "report:view"
    REPORT_EXPORT = "report:export"
    
    # AI Agents
    AI_TRIGGER = "ai:trigger"
    AI_APPROVE = "ai:approve"

ROLE_PERMISSIONS: dict[str, Set[Permission]] = {
    "operator": {
        Permission.SCHEDULE_VIEW,
        Permission.JOB_VIEW,
        Permission.MACHINE_VIEW,
    },
    "supervisor": {
        Permission.SCHEDULE_VIEW,
        Permission.SCHEDULE_EDIT,
        Permission.JOB_VIEW,
        Permission.JOB_CREATE,
        Permission.MACHINE_VIEW,
        Permission.REPORT_VIEW,
        Permission.AI_TRIGGER,
    },
    "production_manager": {
        Permission.SCHEDULE_VIEW,
        Permission.SCHEDULE_EDIT,
        Permission.SCHEDULE_APPROVE,
        Permission.JOB_VIEW,
        Permission.JOB_CREATE,
        Permission.JOB_RELEASE,
        Permission.MACHINE_VIEW,
        Permission.MACHINE_CONFIG,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.AI_TRIGGER,
        Permission.AI_APPROVE,
    },
    "admin": set(Permission),
}
```

### IT/OT Network Segmentation
```
┌─────────────────────────────────────────────────────────────────┐
│                    NETWORK ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  CORPORATE NETWORK (IT)                  │   │
│  │    Users, ERP, Office Apps                               │   │
│  │    VLAN 10 - 10.10.0.0/16                               │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│                    ┌──────┴──────┐                             │
│                    │  FIREWALL   │                             │
│                    │  (pfSense)  │                             │
│                    └──────┬──────┘                             │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────────────┐   │
│  │                    DMZ NETWORK                           │   │
│  │    PyBase API, Databases, MQTT Broker                    │   │
│  │    VLAN 20 - 10.20.0.0/16                               │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│                    ┌──────┴──────┐                             │
│                    │  FIREWALL   │                             │
│                    │  (OT Rules) │                             │
│                    └──────┬──────┘                             │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────────────┐   │
│  │                  SHOP FLOOR NETWORK (OT)                 │   │
│  │    Machines, PLCs, Edge Gateways                         │   │
│  │    VLAN 30 - 10.30.0.0/16                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 6.5 Monitoring & Observability

### Prometheus + Grafana Stack
```yaml
# monitoring/docker-compose.yml

services:
  prometheus:
    image: prom/prometheus:v2.48.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.2.0
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
      
  loki:
    image: grafana/loki:2.9.2
    volumes:
      - loki_data:/loki
      
  promtail:
    image: grafana/promtail:2.9.2
    volumes:
      - /var/log:/var/log:ro
      - ./promtail.yml:/etc/promtail/config.yml
```

### Application Metrics (OpenTelemetry)
```python
# src/pybase/core/telemetry.py

from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider

# Create meter
meter = metrics.get_meter("pybase")

# Define metrics
jobs_scheduled = meter.create_counter(
    "jobs_scheduled_total",
    description="Total jobs scheduled"
)

schedule_latency = meter.create_histogram(
    "schedule_latency_seconds",
    description="Time to generate schedule"
)

machine_status_gauge = meter.create_observable_gauge(
    "machine_status",
    callbacks=[collect_machine_status],
    description="Current machine status"
)

oee_gauge = meter.create_observable_gauge(
    "oee_percent",
    callbacks=[collect_oee_metrics],
    description="Current OEE by department"
)
```

## 6.6 Implementation Tasks

| Task | Effort | Priority |
|------|--------|----------|
| PostgreSQL HA with Patroni | 24 hrs | P0 |
| Redis Sentinel configuration | 8 hrs | P0 |
| Kubernetes Helm chart | 24 hrs | P0 |
| HPA and PDB configuration | 8 hrs | P1 |
| RBAC implementation | 16 hrs | P0 |
| Network segmentation docs | 8 hrs | P1 |
| Prometheus setup | 12 hrs | P0 |
| Grafana dashboards | 16 hrs | P0 |
| OpenTelemetry integration | 12 hrs | P1 |
| Loki log aggregation | 8 hrs | P1 |
| Alerting rules | 12 hrs | P1 |
| Disaster recovery runbook | 16 hrs | P2 |
| Security audit checklist | 12 hrs | P2 |
| Load testing (k6) | 16 hrs | P2 |

**Total Phase 6**: ~192 hours

---

# Unresolved Questions

## Critical (Must Answer Before Phase 1)

| # | Question | Impact | Who to Ask |
|---|----------|--------|------------|
| 1 | What version of Sigmanest is installed? | SimTrans schema varies by version | IT/Engineering |
| 2 | Do laser machines have MTConnect enabled? | Determines IoT approach | Machine vendor |
| 3 | What ERP system handles sales orders? | Order import integration | Finance/IT |
| 4 | How many shifts per day? Fixed or variable? | Calendar/capacity design | Production Manager |

## Important (Answer Before Phase 2)

| # | Question | Impact | Who to Ask |
|---|----------|--------|------------|
| 5 | Which department is the biggest bottleneck? | Priority for IoT instrumentation | Production Manager |
| 6 | Is cloud AI (OpenAI API) acceptable? | Self-hosted LLM alternative | IT Security |
| 7 | What is the network topology (IT/OT separation)? | Edge gateway deployment | IT |
| 8 | Are there existing scheduling tools to migrate from? | Data migration needs | Production |

## Nice to Know

| # | Question | Impact | Who to Ask |
|---|----------|--------|------------|
| 9 | Target OEE improvement goals? | Success metrics | Management |
| 10 | Mobile device policy (BYOD vs company)? | App deployment strategy | IT |
| 11 | Existing barcode/labeling system? | Integration requirements | Warehouse |
| 12 | VIP customers requiring special handling? | Scheduling priority rules | Sales |

---

# Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Sigmanest schema changes break integration | Medium | High | Version-pinned adapters, automated tests |
| Machine connectivity issues (old equipment) | High | Medium | Start with 1 machine, gradual rollout |
| AI hallucination in scheduling decisions | Medium | High | Human approval gates, conservative limits |
| User adoption resistance | Medium | Medium | Phased rollout, champion users, training |
| Performance degradation at scale | Low | High | Load testing, caching, query optimization |
| Network latency to shop floor | Medium | Medium | Edge buffering, offline capabilities |
| Security breach via IoT | Low | Critical | Network segmentation, minimal attack surface |
| Scope creep | High | Medium | Strict phase boundaries, change control |

---

# Timeline Summary

| Phase | Duration | Effort | Key Deliverable |
|-------|----------|--------|-----------------|
| 1: MES Foundation | 4 weeks | 114 hrs | Finite capacity scheduler |
| 2: Sigmanest | 4 weeks | 120 hrs | Bidirectional job sync |
| 3: IoT Layer | 4 weeks | 128 hrs | Real-time machine status |
| 4: AI Agents | 4 weeks | 128 hrs | Intelligent scheduling assistant |
| 5: Advanced | 8 weeks | 180 hrs | OEE dashboards, mobile app |
| 6: Hardening | 6 weeks | 192 hrs | Production-ready deployment |
| **TOTAL** | **30 weeks** | **862 hrs** | Complete MES solution |

---

# Recommended Technology Stack Summary

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Backend** | FastAPI (Python 3.11+) | Existing, async-native |
| **Database** | PostgreSQL 15+ | Existing, JSONB flexibility |
| **Time-Series** | TimescaleDB | PostgreSQL extension, single stack |
| **Cache/Pub-Sub** | Redis 7+ | Existing, real-time presence |
| **Task Queue** | Celery + Redis | Existing, background jobs |
| **Scheduling** | Google OR-Tools CP-SAT | Best-in-class constraint solver |
| **IoT Broker** | Mosquitto MQTT | Lightweight, proven |
| **OPC-UA** | asyncua (Python) | Async-native, well-maintained |
| **MTConnect** | Custom HTTP client | Simple, XML parsing |
| **AI Framework** | LangGraph | Checkpoints, human-in-loop |
| **LLM** | GPT-4o / Claude 3.5 | Best reasoning capability |
| **Frontend** | React 18 + TypeScript | Existing |
| **Charts** | Tremor / Recharts | Modern, React-native |
| **Mobile** | React Native | JS expertise, code sharing |
| **Container** | Docker + Kubernetes | Standard enterprise |
| **Monitoring** | Prometheus + Grafana | Industry standard |
| **Logging** | Loki + Promtail | Grafana ecosystem |

---

*Document generated: January 24, 2026*
*Next review: Before Phase 1 kickoff*
