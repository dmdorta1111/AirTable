# Shop Floor Production Management System - Deep Research Brainstorm

> **Date**: January 24, 2026
> **Project**: PyBase Extension for Sheet Metal Fabrication
> **Industry**: Commercial Kitchen Equipment & Doors/Frames Manufacturing
> **Scale**: 100+ shop floor employees, multi-department operations

---

## Executive Summary

This report analyzes building an enterprise-level shop floor production management system (MES) within PyBase for a custom sheet metal fabricator. The solution integrates Sigmanest CAD/CAM nesting, IoT machine monitoring, AI-driven scheduling, and multi-agent orchestration across 6 departments: Laser, Punch, Welding, Polishing, Assembly, and Shipping.

---

## 1. Current PyBase Foundation Analysis

### Existing Capabilities (Highly Relevant)
| Feature | Readiness | Application to MES |
|---------|-----------|-------------------|
| 30+ Field Types | ✅ Complete | Job tracking, material specs, dimensions |
| Engineering Fields | ✅ Complete | Dimension tolerances, GD&T, thread specs |
| CAD/PDF Extraction | ✅ Complete | Auto-parse drawings to jobs |
| Gantt/Timeline Views | ✅ Complete | Production scheduling visualization |
| Kanban View | ✅ Complete | Department work queues |
| Real-time Collaboration | ✅ Complete | Shop floor updates |
| Automations (11 triggers, 12 actions) | ✅ Complete | Job state transitions, alerts |
| Webhooks | ✅ Complete | External system integration |
| WebSocket Presence | ✅ Complete | Operator status tracking |

### Gaps to Address
1. **No finite capacity scheduling engine** - Core MES requirement
2. **No IoT/machine integration layer** - Need OPC-UA/MTConnect adapters
3. **No time-series data storage** - For machine metrics
4. **No AI/ML scheduling optimization** - Currently manual
5. **No Sigmanest integration** - Critical for nesting workflow
6. **No department-level views** - Need role-based dashboards

---

## 2. Proposed System Architecture

### 2.1 High-Level Architecture (ISA-95 Aligned)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LEVEL 4: ENTERPRISE (ERP)                        │
│            Sales Orders • Customer Data • Finance • Procurement         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │ REST/Webhooks
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 3: MES (PyBase Extended)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐   │
│  │  Job Mgmt   │  │ Scheduling  │  │  Material   │  │   Quality     │   │
│  │  & Routing  │  │   Engine    │  │  Tracking   │  │   Control     │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐   │
│  │  Sigmanest  │  │    IoT      │  │  AI Agent   │  │   Reporting   │   │
│  │ Integration │  │  Gateway    │  │Orchestrator │  │  & Analytics  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                    │               │               │
        ┌───────────┘               │               └───────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────────┐        ┌──────────────┐
│   Sigmanest   │         │   IoT Edge Layer  │        │   AI Agents  │
│  SimTrans DB  │         │   OPC-UA/MQTT     │        │   LangGraph  │
└───────────────┘         └───────────────────┘        └──────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 2: SHOP FLOOR CONTROL                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │  Laser  │  │  Punch  │  │ Welding │  │ Polish  │  │Assembly │       │
│  │ Station │  │ Station │  │ Station │  │ Station │  │ Station │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LEVEL 1: MACHINE SENSORS                           │
│        PLC Data • Part Counts • Cycle Times • Status • Alarms           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA FLOW OVERVIEW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ORDERS ──► NESTING ──► SCHEDULING ──► PRODUCTION ──► SHIPPING         │
│     │          │            │              │             │              │
│     ▼          ▼            ▼              ▼             ▼              │
│  PyBase   Sigmanest    AI Scheduler    IoT Capture   Completion         │
│  Tables   SimTrans     LangGraph       TimescaleDB   Webhooks           │
│                                                                         │
│  ◄──────────────── FEEDBACK LOOP (Real-time) ───────────────────►      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Sigmanest Integration Strategy

### 3.1 Available Integration Methods (Research Findings)

| Method | Description | Best For |
|--------|-------------|----------|
| **SimTrans** | Database transaction manager | Real-time bidirectional sync |
| **SigmaMRP** | Built-in MRP module | Order/inventory management |
| **Direct DB** | PostgreSQL/SQL Server access | Custom integrations |
| **File Export** | NC files, reports | Machine programs |

### 3.2 SimTrans Integration Architecture

SimTrans acts as the middleware bridge between PyBase and Sigmanest:

```
PyBase (Orders/Jobs)
        │
        ▼ [REST API]
┌───────────────────┐
│  Integration Hub  │  (FastAPI Service)
│   - Job Sync      │
│   - Part Import   │
│   - Nest Status   │
└───────────────────┘
        │
        ▼ [Database Polling/Triggers]
┌───────────────────┐
│     SimTrans      │  (Transaction Tables)
│   - WorkOrders    │
│   - Parts         │
│   - Materials     │
│   - NestResults   │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│    SigmaNEST      │  (CAD/CAM Nesting)
│   - Auto-nest     │
│   - NC Output     │
│   - Material Calc │
└───────────────────┘
```

### 3.3 Data Exchange Objects

**PyBase → Sigmanest:**
- Work Orders (job_id, customer, due_date, priority)
- Parts (part_number, quantity, material, thickness)
- Material Inventory (sheet sizes, quantities, locations)

**Sigmanest → PyBase:**
- Nest Results (utilization %, scrap, sheet assignments)
- NC Programs (file paths, machine assignments)
- Estimated Cut Times (for scheduling)
- Material Consumption (actual vs planned)

### 3.4 Implementation Approach

```python
# src/pybase/integrations/sigmanest/
├── __init__.py
├── config.py           # Connection settings
├── simtrans_client.py  # SimTrans DB adapter
├── sync_service.py     # Bidirectional sync logic
├── models.py           # Sigmanest data models
└── tasks.py            # Celery background sync
```

**Key Considerations:**
- Poll SimTrans every 30-60 seconds for changes
- Use database triggers for real-time updates if available
- Cache nest results in Redis for fast lookup
- Queue NC file generation in Celery workers

---

## 4. IoT Integration Layer

### 4.1 Protocol Selection

| Machine Type | Recommended Protocol | Data Available |
|--------------|---------------------|----------------|
| Laser Cutters | **MTConnect** | Cycle time, part count, alarms, feedrate |
| Punch Presses | **OPC-UA** | Stroke count, tool wear, part complete |
| Welding Stations | **MQTT + Sensors** | Arc time, wire feed, gas flow |
| Polishing | **MQTT + I/O** | Cycle complete, operator input |
| Assembly | **Barcode/RFID** | Part tracking, completion |

### 4.2 Edge Computing Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SHOP FLOOR (Per Department)                 │
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ Machine │  │ Machine │  │ Machine │  │ Sensors │            │
│  │   A     │  │   B     │  │   C     │  │  (I/O)  │            │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
│       │            │            │            │                  │
│       └──────────┬─┴────────────┴────────────┘                  │
│                  ▼                                              │
│         ┌───────────────┐                                       │
│         │  Edge Gateway │  (Node-RED / Python)                  │
│         │  - Protocol   │                                       │
│         │    Adapters   │                                       │
│         │  - Buffering  │                                       │
│         │  - Filtering  │                                       │
│         └───────┬───────┘                                       │
│                 │                                               │
└─────────────────┼───────────────────────────────────────────────┘
                  │ MQTT
                  ▼
         ┌───────────────┐
         │  MQTT Broker  │  (Mosquitto/EMQX)
         │   (Central)   │
         └───────┬───────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│TimescaleDB│ │  PyBase  │ │  Alerts  │
│ (Metrics) │ │(Status)  │ │ (PagerD) │
└──────────┘ └──────────┘ └──────────┘
```

### 4.3 Data Model for Machine Telemetry

```sql
-- TimescaleDB hypertable for machine metrics
CREATE TABLE machine_metrics (
    time            TIMESTAMPTZ NOT NULL,
    machine_id      TEXT NOT NULL,
    department      TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    value           DOUBLE PRECISION,
    unit            TEXT,
    job_id          TEXT,
    part_id         TEXT
);

SELECT create_hypertable('machine_metrics', 'time');

-- Continuous aggregate for hourly rollups
CREATE MATERIALIZED VIEW machine_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS hour,
    machine_id,
    metric_name,
    AVG(value) as avg_value,
    MAX(value) as max_value,
    COUNT(*) as sample_count
FROM machine_metrics
GROUP BY hour, machine_id, metric_name;
```

### 4.4 Implementation Files

```python
# src/pybase/iot/
├── __init__.py
├── protocols/
│   ├── mtconnect_adapter.py    # MTConnect XML parser
│   ├── opcua_client.py         # OPC-UA subscription
│   └── mqtt_handler.py         # MQTT message processor
├── edge/
│   ├── gateway.py              # Edge gateway logic
│   └── buffer.py               # Offline buffering
├── models.py                   # Telemetry Pydantic models
└── services/
    ├── machine_status.py       # Real-time status tracking
    └── analytics.py            # Metric aggregation
```

---

## 5. Finite Capacity Scheduling Engine

### 5.1 Scheduling Algorithm Selection

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Genetic Algorithm** | Good for complex constraints | Slow convergence | Production planning |
| **Priority Dispatch Rules** | Fast, simple | Suboptimal | Real-time dispatch |
| **Constraint Programming** | Optimal for small problems | Doesn't scale | Bottleneck stations |
| **Reinforcement Learning** | Learns from data, adaptive | Needs training data | Long-term goal |
| **Hybrid (Rules + RL)** | Best of both | Complex setup | **Recommended** |

### 5.2 Multi-Stage Scheduling Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULING PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. STRATEGIC (Weekly)                                          │
│     └─► Capacity Planning → Load Balancing → Resource Alloc    │
│                                                                 │
│  2. TACTICAL (Daily)                                            │
│     └─► Job Sequencing → Route Optimization → Shift Planning   │
│                                                                 │
│  3. OPERATIONAL (Real-time)                                     │
│     └─► Dynamic Dispatch → Exception Handling → Rescheduling   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Core Scheduling Data Model

```python
# New PyBase tables for scheduling
class WorkCenter(Base):
    """Machine/station with capacity"""
    id: str  # e.g., "LASER-01"
    department: str  # "Laser", "Punch", etc.
    capacity_hours_per_day: float
    efficiency_factor: float  # 0.85 typical
    skills: List[str]  # Operations it can perform
    calendar_id: str  # Shift/holiday calendar

class Operation(Base):
    """Single step in job routing"""
    id: str
    job_id: str
    sequence: int
    work_center_type: str  # "Laser", "Punch", etc.
    setup_time_minutes: float
    run_time_per_unit_minutes: float
    dependencies: List[str]  # Previous operation IDs

class Schedule(Base):
    """Scheduled operation assignment"""
    id: str
    operation_id: str
    work_center_id: str
    planned_start: datetime
    planned_end: datetime
    actual_start: datetime | None
    actual_end: datetime | None
    status: str  # "scheduled", "in_progress", "complete", "delayed"
```

### 5.4 Scheduling Algorithm (Hybrid Approach)

```python
class FiniteCapacityScheduler:
    """
    Multi-department finite capacity scheduler.
    Uses forward scheduling with priority rules.
    """
    
    def schedule_jobs(self, jobs: List[Job], horizon_days: int = 14):
        """
        Main scheduling algorithm:
        1. Sort jobs by priority (due date, customer tier, rush flag)
        2. For each job, schedule operations in sequence
        3. Find earliest available slot on capable work center
        4. Handle department transitions and buffers
        5. Detect and flag deadline conflicts
        """
        # Step 1: Priority ordering
        sorted_jobs = self._priority_sort(jobs)
        
        # Step 2: Load work center calendars
        calendars = self._load_calendars(horizon_days)
        
        # Step 3: Forward schedule each job
        for job in sorted_jobs:
            for operation in job.operations:
                slot = self._find_earliest_slot(
                    operation=operation,
                    calendars=calendars,
                    after=job.release_date
                )
                self._book_slot(operation, slot, calendars)
        
        # Step 4: Identify bottlenecks
        bottlenecks = self._analyze_bottlenecks(calendars)
        
        return ScheduleResult(
            schedule=calendars,
            bottlenecks=bottlenecks,
            on_time_rate=self._calculate_otr(jobs)
        )
```

---

## 6. Multi-Agent AI Orchestration

### 6.1 Framework Selection: LangGraph

**Why LangGraph over CrewAI/AutoGen:**
- **State Checkpoints**: Critical for manufacturing (prevents runaway loops)
- **Human-in-the-Loop**: Supervisors can intervene on critical decisions
- **Graph-based Workflows**: Maps naturally to manufacturing processes
- **LangSmith Integration**: Full observability and debugging
- **Enterprise Support**: Production-ready with circuit breakers

### 6.2 Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI AGENT ORCHESTRATOR                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              SUPERVISOR AGENT (LangGraph Hub)            │   │
│  │  - Receives requests from PyBase API                     │   │
│  │  - Routes to specialist agents                           │   │
│  │  - Aggregates results                                    │   │
│  │  - Escalates to humans when needed                       │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │                                       │
│    ┌────────────────────┼────────────────────┐                  │
│    ▼                    ▼                    ▼                  │
│  ┌──────────┐    ┌──────────────┐    ┌────────────┐            │
│  │ Scheduler│    │  Material    │    │  Quality   │            │
│  │  Agent   │    │ Optimizer    │    │  Monitor   │            │
│  ├──────────┤    ├──────────────┤    ├────────────┤            │
│  │ - Job    │    │ - Inventory  │    │ - Defect   │            │
│  │   Priority    │    tracking  │    │   detection│            │
│  │ - Bottleneck  │ - Sheet opt  │    │ - Root     │            │
│  │   detection   │ - Scrap min  │    │   cause    │            │
│  │ - Resequence  │ - Reorder    │    │ - Suggest  │            │
│  └──────────┘    └──────────────┘    └────────────┘            │
│                                                                 │
│    ┌────────────────────┬────────────────────┐                  │
│    ▼                    ▼                    ▼                  │
│  ┌──────────┐    ┌──────────────┐    ┌────────────┐            │
│  │ Dispatch │    │   Capacity   │    │  Customer  │            │
│  │  Agent   │    │   Planner    │    │  Liaison   │            │
│  ├──────────┤    ├──────────────┤    ├────────────┤            │
│  │ - Next   │    │ - Forecast   │    │ - ETA      │            │
│  │   job    │    │   workload   │    │   updates  │            │
│  │ - Machine│    │ - Overtime   │    │ - Rush     │            │
│  │   assign │    │   recommend  │    │   handling │            │
│  └──────────┘    └──────────────┘    └────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 LangGraph Implementation

```python
# src/pybase/ai_agents/
├── __init__.py
├── graph.py              # Main LangGraph definition
├── state.py              # State schema
├── agents/
│   ├── supervisor.py     # Orchestrator agent
│   ├── scheduler.py      # Scheduling specialist
│   ├── material.py       # Material optimization
│   ├── quality.py        # Quality monitoring
│   ├── dispatch.py       # Real-time dispatch
│   ├── capacity.py       # Capacity planning
│   └── customer.py       # Customer communication
├── tools/
│   ├── sigmanest.py      # Sigmanest API tools
│   ├── schedule_db.py    # Schedule CRUD tools
│   ├── machine_status.py # IoT query tools
│   └── notifications.py  # Alert tools
└── memory/
    ├── checkpointer.py   # PostgreSQL checkpointer
    └── knowledge.py      # Manufacturing knowledge base
```

### 6.4 Example Agent Workflow

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

class ManufacturingState(TypedDict):
    request: str
    context: dict
    schedule_changes: list
    material_status: dict
    quality_issues: list
    final_response: str
    human_approval_needed: bool

def build_manufacturing_graph():
    graph = StateGraph(ManufacturingState)
    
    # Define nodes
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("scheduler", scheduler_agent)
    graph.add_node("material", material_agent)
    graph.add_node("quality", quality_agent)
    graph.add_node("human_review", human_approval_node)
    
    # Define edges
    graph.add_edge("supervisor", "route_to_specialist")
    graph.add_conditional_edges(
        "route_to_specialist",
        route_decision,
        {
            "scheduling": "scheduler",
            "material": "material",
            "quality": "quality",
            "complex": "human_review"
        }
    )
    
    # Compile with checkpointing
    checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
    return graph.compile(checkpointer=checkpointer)
```

### 6.5 Human-in-the-Loop Scenarios

| Scenario | Trigger | Human Action |
|----------|---------|--------------|
| Rush order conflicts | >3 jobs affected | Approve priority override |
| Overtime required | >2 hours/department | Approve OT budget |
| Quality hold | Critical defect | Release/scrap decision |
| Material shortage | Stock < safety level | Approve substitution |
| Customer escalation | VIP account | Review response |

---

## 7. Department-Specific Features

### 7.1 Laser Department
- **Sigmanest Direct**: NC program queue, nest efficiency tracking
- **IoT Metrics**: Piercing count, cut length, gas consumption
- **Scheduling**: Batch by material/thickness for setup reduction
- **AI Optimization**: Predict maintenance from cut quality degradation

### 7.2 Punch Department
- **Tool Library**: Tool life tracking, auto-reorder triggers
- **IoT Metrics**: Stroke count, tonnage, tool changes
- **Scheduling**: Group by tool setup to minimize changeovers
- **AI Optimization**: Suggest tool consolidation across jobs

### 7.3 Welding Department
- **WPS Tracking**: Procedure compliance, welder certification
- **IoT Metrics**: Arc-on time, wire consumption, gas flow
- **Scheduling**: Balance welder workload, skill matching
- **AI Optimization**: Predict weld defects from parameter drift

### 7.4 Polishing Department
- **Surface Quality**: Pass/fail tracking, rework rates
- **IoT Metrics**: Cycle time, consumable usage
- **Scheduling**: Priority queue by customer finish specs
- **AI Optimization**: Route complex finishes to skilled operators

### 7.5 Assembly Department
- **BOM Tracking**: Kit completeness, missing parts alerts
- **Barcode/RFID**: Part tracking, work instruction display
- **Scheduling**: Level assembly queue, avoid starvation
- **AI Optimization**: Predict bottlenecks from upstream delays

### 7.6 Shipping Department
- **Packing Lists**: Auto-generate from completed jobs
- **Carrier Integration**: Rate shopping, label printing
- **Scheduling**: Dock scheduling, truck loading optimization
- **AI Optimization**: Consolidate shipments by customer/region

---

## 8. Data Architecture

### 8.1 Database Strategy

```
┌───────────────────────────────────────────────────────────────┐
│                     DATA ARCHITECTURE                          │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────┐     ┌─────────────────────┐          │
│  │     PostgreSQL      │     │    TimescaleDB      │          │
│  │    (Transactional)  │     │    (Time-Series)    │          │
│  ├─────────────────────┤     ├─────────────────────┤          │
│  │ - Jobs/Orders       │     │ - Machine Metrics   │          │
│  │ - Schedules         │     │ - Cycle Times       │          │
│  │ - Work Centers      │     │ - OEE Data          │          │
│  │ - Materials         │     │ - Quality Events    │          │
│  │ - Users/Roles       │     │ - Alarms/Events     │          │
│  │ - Audit Logs        │     │                     │          │
│  └─────────────────────┘     └─────────────────────┘          │
│           │                           │                        │
│           └───────────┬───────────────┘                        │
│                       ▼                                        │
│              ┌─────────────────┐                               │
│              │      Redis      │                               │
│              │   (Real-time)   │                               │
│              ├─────────────────┤                               │
│              │ - Machine Status│                               │
│              │ - Active Jobs   │                               │
│              │ - Presence      │                               │
│              │ - Pub/Sub       │                               │
│              └─────────────────┘                               │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

### 8.2 New Tables for MES

```sql
-- Work Centers (machines/stations)
CREATE TABLE work_centers (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200),
    department VARCHAR(50),
    machine_type VARCHAR(100),
    capacity_hours_per_shift DECIMAL(5,2),
    efficiency_factor DECIMAL(3,2) DEFAULT 0.85,
    is_active BOOLEAN DEFAULT TRUE,
    iot_device_id VARCHAR(100),
    sigmanest_machine_id VARCHAR(100),
    metadata JSONB
);

-- Job Routings
CREATE TABLE job_routings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES records(id),
    sequence INTEGER,
    operation_code VARCHAR(50),
    work_center_type VARCHAR(50),
    setup_minutes DECIMAL(8,2),
    run_minutes_per_unit DECIMAL(8,4),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schedule Slots
CREATE TABLE schedule_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    routing_id UUID REFERENCES job_routings(id),
    work_center_id VARCHAR(50) REFERENCES work_centers(id),
    planned_start TIMESTAMPTZ,
    planned_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'scheduled',
    operator_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Material Inventory
CREATE TABLE material_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_code VARCHAR(100),
    thickness DECIMAL(6,3),
    sheet_width DECIMAL(8,2),
    sheet_length DECIMAL(8,2),
    quantity INTEGER,
    location VARCHAR(100),
    heat_lot VARCHAR(100),
    cost_per_unit DECIMAL(10,4),
    last_counted_at TIMESTAMPTZ,
    sigmanest_material_id VARCHAR(100)
);

-- Sigmanest Sync Log
CREATE TABLE sigmanest_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sync_type VARCHAR(50),
    direction VARCHAR(10), -- 'inbound' or 'outbound'
    record_count INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Weeks 1-4)
**Focus**: Core MES data model and basic scheduling

| Task | Effort | Dependencies |
|------|--------|--------------|
| Work center table + API | 3 days | None |
| Job routing model | 3 days | None |
| Basic forward scheduler | 5 days | Routing model |
| Gantt view enhancements | 4 days | Scheduler |
| Department dashboards | 3 days | Work centers |

**Deliverable**: Basic finite capacity schedule visible in Gantt view

### Phase 2: Sigmanest Integration (Weeks 5-8)
**Focus**: Connect nesting workflow

| Task | Effort | Dependencies |
|------|--------|--------------|
| SimTrans DB connector | 3 days | None |
| Work order sync (outbound) | 4 days | Connector |
| Nest results sync (inbound) | 4 days | Connector |
| Material inventory sync | 3 days | Connector |
| NC file management | 3 days | Results sync |

**Deliverable**: Jobs flow to Sigmanest, nest results return automatically

### Phase 3: IoT Layer (Weeks 9-12)
**Focus**: Real-time machine connectivity

| Task | Effort | Dependencies |
|------|--------|--------------|
| MQTT broker setup | 2 days | None |
| Edge gateway design | 3 days | None |
| MTConnect adapter (laser) | 4 days | Gateway |
| OPC-UA adapter (punch) | 4 days | Gateway |
| TimescaleDB setup | 2 days | None |
| Machine status service | 3 days | Adapters |

**Deliverable**: Live machine status on department dashboards

### Phase 4: AI Agent Core (Weeks 13-16)
**Focus**: Basic AI scheduling assistance

| Task | Effort | Dependencies |
|------|--------|--------------|
| LangGraph setup | 2 days | None |
| Scheduler agent | 5 days | Phase 1 complete |
| Dispatch agent | 4 days | IoT layer |
| Supervisor orchestrator | 4 days | Agents |
| Human approval flow | 3 days | Supervisor |

**Deliverable**: AI-assisted scheduling recommendations with human approval

### Phase 5: Advanced Features (Weeks 17-24)
**Focus**: Full MES functionality

| Task | Effort | Dependencies |
|------|--------|--------------|
| Material optimization agent | 5 days | Phase 2 |
| Quality monitoring agent | 4 days | Phase 3 |
| Capacity planning agent | 4 days | Phase 4 |
| Customer ETA agent | 3 days | Phase 4 |
| OEE dashboards | 4 days | Phase 3 |
| Mobile operator app | 10 days | Phase 1-4 |

**Deliverable**: Full AI-powered MES with operator mobile interface

### Phase 6: Enterprise Hardening (Weeks 25-30)
**Focus**: Production readiness

| Task | Effort | Dependencies |
|------|--------|--------------|
| Load testing | 3 days | All phases |
| HA configuration | 5 days | All phases |
| Disaster recovery | 3 days | HA |
| Security audit | 4 days | All phases |
| User training docs | 5 days | All phases |
| Go-live support | 10 days | All above |

---

## 10. Technology Stack Summary

### Backend (Python)
- **FastAPI**: API layer (existing)
- **SQLAlchemy 2.0**: ORM (existing)
- **Celery + Redis**: Background jobs (existing)
- **LangGraph**: AI agent orchestration (new)
- **asyncpg**: PostgreSQL async driver (existing)
- **opcua-asyncio**: OPC-UA client (new)
- **paho-mqtt**: MQTT client (new)

### Database
- **PostgreSQL 15+**: Primary transactional (existing)
- **TimescaleDB**: Time-series extension (new)
- **Redis 7+**: Caching, pub/sub (existing)

### IoT
- **MQTT (Mosquitto/EMQX)**: Message broker (new)
- **Node-RED**: Edge gateway (optional)
- **MTConnect Agent**: Laser machine adapter (new)

### Frontend
- **React 18 + TypeScript**: UI (existing)
- **TanStack Query**: Data fetching (existing)
- **Tailwind + shadcn/ui**: Styling (existing)
- **React Native**: Mobile app (new, optional)

### Infrastructure
- **Docker Compose**: Development (existing)
- **Kubernetes**: Production (planned)
- **Prometheus + Grafana**: Monitoring (new)
- **LangSmith**: AI observability (new)

---

## 11. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Sigmanest API limitations | Medium | High | Early POC, fallback to file exchange |
| Machine connectivity issues | High | Medium | Start with 1 machine, expand |
| AI hallucination in scheduling | Medium | High | Human approval gates, guardrails |
| User adoption resistance | Medium | Medium | Phased rollout, training |
| Performance at scale | Low | High | Load testing, caching strategy |
| Integration complexity | High | Medium | Modular design, clear interfaces |

---

## 12. Success Metrics

| Metric | Current (Est.) | Target | Measurement |
|--------|----------------|--------|-------------|
| Schedule accuracy | 60% | 90% | Jobs completed by planned date |
| Material utilization | 75% | 85% | Sigmanest nest reports |
| Machine utilization | 55% | 75% | IoT uptime data |
| Lead time | 3 weeks | 2 weeks | Order to ship tracking |
| On-time delivery | 70% | 95% | Shipping vs. promise date |
| Scheduling time | 4 hrs/day | 30 min/day | User activity logs |

---

## 13. Unresolved Questions

1. **Sigmanest Version**: What version of Sigmanest is in use? SimTrans availability?
2. **Machine Interfaces**: Do laser/punch machines have MTConnect/OPC-UA enabled?
3. **ERP System**: What ERP is used for sales orders? Integration requirements?
4. **Shift Patterns**: How many shifts? Fixed or variable schedules?
5. **Current Pain Points**: Which department has biggest scheduling bottleneck?
6. **Budget Constraints**: Is cloud AI (LangGraph Cloud) acceptable, or on-prem only?
7. **Data Sensitivity**: Any restrictions on sending job data to external AI services?
8. **Existing Tools**: Are there any existing scheduling tools to migrate from?

---

## 14. Recommended Next Steps

1. **Discovery Session**: Meet with production manager to answer unresolved questions
2. **Sigmanest POC**: Build minimal SimTrans connector, validate data flow
3. **IoT Pilot**: Instrument one laser machine with MTConnect
4. **Scheduling Core**: Implement basic finite capacity scheduler in PyBase
5. **Create Detailed Plan**: Use `/plan:hard` with this context for implementation roadmap

---

**Would you like to proceed with creating a detailed implementation plan?**
