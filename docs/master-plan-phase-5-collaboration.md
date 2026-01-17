# Phase 5: Real-time & Collaboration
## PyBase Master Plan - Weeks 24-27

**Duration:** 4 Weeks  
**Status:** ❌ NOT STARTED (January 2026)  
**Team Focus:** Backend Lead + Full-Stack Engineer  
**Dependencies:** Phase 4 Complete (Views System)

---

## 📋 Phase Status Overview

**Implementation Status:** ❌ Planned  
**Dependencies:** ❌ Phase 3-4 not started

---

## Phase Objectives

1. Implement WebSocket infrastructure for real-time updates
2. Build presence awareness (who's viewing/editing)
3. Create comments and mentions system
4. Implement activity log and audit trail
5. Build notification system

---

## Week-by-Week Breakdown

### Week 24: WebSocket Infrastructure

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 5.24.1 | Set up WebSocket endpoint in FastAPI | Critical | 4h | Phase 4 |
| 5.24.2 | Create ConnectionManager class | Critical | 4h | 5.24.1 |
| 5.24.3 | Implement room-based subscriptions | Critical | 6h | 5.24.2 |
| 5.24.4 | Set up Redis PubSub for scaling | Critical | 6h | 5.24.2 |
| 5.24.5 | Create message type handlers | High | 4h | 5.24.3 |
| 5.24.6 | Implement authentication for WS | Critical | 4h | 5.24.1 |
| 5.24.7 | Build reconnection handling | High | 4h | 5.24.3 |
| 5.24.8 | Write WebSocket tests | High | 4h | 5.24.* |

#### Message Types

```python
class WSMessageType(str, Enum):
    # Subscriptions
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    
    # Records
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    
    # Fields
    FIELD_CREATED = "field_created"
    FIELD_UPDATED = "field_updated"
    FIELD_DELETED = "field_deleted"
    
    # Views
    VIEW_UPDATED = "view_updated"
    
    # Presence
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_CURSOR = "user_cursor"
    
    # Cell Editing
    CELL_LOCK = "cell_lock"
    CELL_UNLOCK = "cell_unlock"
    CELL_EDIT = "cell_edit"
    
    # System
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
```

---

### Week 25: Real-time Updates & Presence

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 5.25.1 | Broadcast record CRUD events | Critical | 6h | 5.24.* |
| 5.25.2 | Broadcast field changes | High | 4h | 5.24.* |
| 5.25.3 | Implement optimistic locking | High | 6h | 5.25.1 |
| 5.25.4 | Build presence tracking | High | 4h | 5.24.* |
| 5.25.5 | Implement cursor sharing | Medium | 4h | 5.25.4 |
| 5.25.6 | Build cell-level locking | High | 6h | 5.25.3 |
| 5.25.7 | Create conflict resolution | High | 6h | 5.25.6 |
| 5.25.8 | Write real-time tests | High | 4h | 5.25.* |

---

### Week 26: Comments & Mentions

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 5.26.1 | Create Comment model | Critical | 3h | Phase 2 |
| 5.26.2 | Build comment CRUD service | Critical | 4h | 5.26.1 |
| 5.26.3 | Create comment API endpoints | Critical | 4h | 5.26.2 |
| 5.26.4 | Implement threaded comments | High | 4h | 5.26.2 |
| 5.26.5 | Build mention parsing (@user) | High | 4h | 5.26.2 |
| 5.26.6 | Create mention notifications | High | 4h | 5.26.5 |
| 5.26.7 | Broadcast comment events | High | 3h | 5.25.1 |
| 5.26.8 | Build rich text support | Medium | 4h | 5.26.2 |
| 5.26.9 | Write comment tests | High | 4h | 5.26.* |

---

### Week 27: Activity Log & Notifications

#### Tasks

| ID | Task | Priority | Estimate | Dependencies |
|----|------|----------|----------|--------------|
| 5.27.1 | Create ActivityLog model | Critical | 3h | Phase 2 |
| 5.27.2 | Implement change tracking | Critical | 6h | 5.27.1 |
| 5.27.3 | Build activity API endpoints | High | 4h | 5.27.2 |
| 5.27.4 | Create Notification model | High | 3h | Phase 2 |
| 5.27.5 | Build notification service | High | 4h | 5.27.4 |
| 5.27.6 | Create notification API | High | 4h | 5.27.5 |
| 5.27.7 | Implement email notifications | Medium | 4h | 5.27.5 |
| 5.27.8 | Build notification preferences | Medium | 3h | 5.27.5 |
| 5.27.9 | Integration testing | Critical | 6h | 5.24-27.* |
| 5.27.10 | Performance testing | High | 4h | 5.27.9 |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ws` | WebSocket | Real-time connection |
| `/api/v1/records/{id}/comments` | GET | List comments |
| `/api/v1/records/{id}/comments` | POST | Add comment |
| `/api/v1/comments/{id}` | PATCH | Update comment |
| `/api/v1/comments/{id}` | DELETE | Delete comment |
| `/api/v1/tables/{id}/activity` | GET | Get activity log |
| `/api/v1/notifications` | GET | Get notifications |
| `/api/v1/notifications/read` | POST | Mark as read |

---

## Phase 5 Exit Criteria

1. [ ] WebSocket infrastructure stable
2. [ ] Real-time record updates working
3. [ ] Presence awareness implemented
4. [ ] Comments with mentions working
5. [ ] Activity log capturing changes
6. [ ] Notifications delivered
7. [ ] Load test: 100 concurrent users

---

*Previous: [Phase 4: Views](master-plan-phase-4-views.md)*  
*Next: [Phase 6: Automations](master-plan-phase-6-automations.md)*
