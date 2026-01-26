# PyBase API Reference

> API Version: v1  
> Base URL: `http://localhost:8000/api/v1`

## Authentication

PyBase supports two authentication methods:

### JWT Bearer Token
```bash
curl -H "Authorization: Bearer <access_token>" ...
```

### API Key
```bash
curl -H "X-API-Key: <api_key>" ...
```

---

## Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

---

### Authentication (`/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login, get tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout, revoke tokens |

#### Register
```bash
POST /auth/register
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

#### Login
```bash
POST /auth/login
{
  "email": "user@example.com",
  "password": "securepassword"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### Users (`/users`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me` | Get current user |
| PATCH | `/users/me` | Update current user |
| GET | `/users/me/api-keys` | List API keys |
| POST | `/users/me/api-keys` | Create API key |
| DELETE | `/users/me/api-keys/{id}` | Delete API key |

---

### Workspaces (`/workspaces`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/workspaces` | List workspaces |
| POST | `/workspaces` | Create workspace |
| GET | `/workspaces/{id}` | Get workspace |
| PATCH | `/workspaces/{id}` | Update workspace |
| DELETE | `/workspaces/{id}` | Delete workspace |
| GET | `/workspaces/{id}/members` | List members |
| POST | `/workspaces/{id}/members` | Add member |

---

### Bases (`/bases`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/bases` | List bases |
| POST | `/bases` | Create base |
| GET | `/bases/{id}` | Get base |
| PATCH | `/bases/{id}` | Update base |
| DELETE | `/bases/{id}` | Delete base |
| POST | `/bases/{id}/duplicate` | Duplicate base |

---

### Tables (`/tables`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tables?base_id={id}` | List tables in base |
| POST | `/tables` | Create table |
| GET | `/tables/{id}` | Get table with fields |
| PATCH | `/tables/{id}` | Update table |
| DELETE | `/tables/{id}` | Delete table |

---

### Fields (`/fields`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/fields?table_id={id}` | List fields |
| POST | `/fields` | Create field |
| GET | `/fields/{id}` | Get field |
| PATCH | `/fields/{id}` | Update field |
| DELETE | `/fields/{id}` | Delete field |
| POST | `/fields/reorder` | Reorder fields |

#### Field Types

| Type | Description | Options |
|------|-------------|---------|
| `text` | Single line text | `max_length` |
| `long_text` | Multi-line text | `enable_rich_text` |
| `number` | Numeric value | `precision`, `allow_negative` |
| `currency` | Money value | `currency_symbol`, `precision` |
| `percent` | Percentage | `precision` |
| `checkbox` | Boolean | - |
| `date` | Date only | `date_format`, `include_time` |
| `datetime` | Date and time | `time_format`, `timezone` |
| `duration` | Time duration | `duration_format` |
| `single_select` | Single choice | `choices: [{name, color}]` |
| `multi_select` | Multiple choices | `choices: [{name, color}]` |
| `linked_record` | Relation | `linked_table_id`, `allow_multiple` |
| `lookup` | Cross-table lookup | `linked_field_id`, `lookup_field_id` |
| `rollup` | Aggregation | `linked_field_id`, `rollup_field_id`, `function` |
| `formula` | Calculated | `formula` |
| `attachment` | Files | `allowed_types`, `max_size` |
| `url` | URL | - |
| `email` | Email address | - |
| `phone` | Phone number | - |
| `user` | User reference | `allow_multiple` |
| `rating` | Star rating | `max`, `icon` |
| `barcode` | Barcode | `format` |
| `autonumber` | Auto-increment | `prefix` |
| `dimension` | Engineering dimension | `unit`, `tolerance_type` |
| `gdt` | GD&T symbol | - |
| `thread` | Thread spec | `standard` |
| `material` | Material | - |

---

### Records (`/records`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/records?table_id={id}` | List records |
| POST | `/records` | Create record |
| GET | `/records/{id}` | Get record |
| PATCH | `/records/{id}` | Update record |
| DELETE | `/records/{id}` | Delete record |
| POST | `/records/batch` | Batch create |
| PATCH | `/records/batch` | Batch update |
| DELETE | `/records/batch` | Batch delete |

#### Create Record
```bash
POST /records
{
  "table_id": "uuid",
  "fields": {
    "Name": "Widget A",
    "Price": 29.99,
    "In Stock": true
  }
}
```

#### Query Records
```bash
GET /records?table_id={id}&filter={"Name": {"$contains": "Widget"}}&sort=[{"field": "Price", "direction": "desc"}]&limit=100&offset=0
```

---

### Views (`/views`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/views?table_id={id}` | List views |
| POST | `/views` | Create view |
| GET | `/views/{id}` | Get view |
| PATCH | `/views/{id}` | Update view |
| DELETE | `/views/{id}` | Delete view |
| POST | `/views/{id}/duplicate` | Duplicate view |
| POST | `/views/reorder` | Reorder views |
| POST | `/views/{id}/data` | Get filtered data |

#### View Types

| Type | Description | Config |
|------|-------------|--------|
| `grid` | Spreadsheet | `row_height`, `frozen_columns` |
| `kanban` | Board | `group_field_id`, `stack_field_id` |
| `calendar` | Calendar | `date_field_id`, `end_date_field_id` |
| `gallery` | Cards | `cover_field_id`, `card_fields` |
| `form` | Input form | `fields`, `submit_text` |
| `gantt` | Timeline | `start_field_id`, `end_field_id`, `dependency_field_id` |
| `timeline` | Horizontal | `date_field_id`, `group_field_id` |

---

### Extraction (`/extraction`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/extraction/pdf` | Extract from PDF |
| POST | `/extraction/dxf` | Extract from DXF/DWG |
| POST | `/extraction/ifc` | Extract from IFC |
| POST | `/extraction/step` | Extract from STEP |
| POST | `/extraction/werk24` | Extract via Werk24 API |
| GET | `/extraction/jobs/{id}` | Get job status |
| POST | `/extraction/import/preview` | Preview import |
| POST | `/extraction/import/execute` | Execute import |

#### Extract from PDF
```bash
POST /extraction/pdf
Content-Type: multipart/form-data

file: <pdf_file>
extract_tables: true
extract_text: true
extract_metadata: true
ocr_enabled: false
```

---

### Real-time (`/realtime`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| WebSocket | `/realtime/ws?token={jwt}` | WebSocket connection |
| GET | `/realtime/stats` | Connection statistics |
| GET | `/realtime/presence/{channel}` | Channel presence |
| GET | `/realtime/presence/{channel}/focus` | Cell focus info |
| POST | `/realtime/broadcast/{channel}` | Broadcast message |

#### WebSocket Protocol

Connect: `ws://host/api/v1/realtime/ws?token=<jwt>`

**Client -> Server Messages:**

```json
// Ping
{"type": "ping"}

// Subscribe to channel
{"type": "subscribe", "payload": {"channel": "table:uuid"}}

// Unsubscribe
{"type": "unsubscribe", "payload": {"channel": "table:uuid"}}

// Cell focus
{"type": "cell.focus", "payload": {"table_id": "...", "view_id": "...", "record_id": "...", "field_id": "..."}}

// Cell blur
{"type": "cell.blur", "payload": {"table_id": "...", "view_id": "...", "record_id": "...", "field_id": "..."}}

// Cursor move
{"type": "cursor.move", "payload": {"table_id": "...", "view_id": "...", "position": {...}}}
```

**Server -> Client Events:**

- `connect` - Connection established
- `pong` - Ping response
- `subscribed` / `unsubscribed` - Subscription confirmations
- `presence.join` / `presence.leave` - User presence
- `presence.state` - Full presence state
- `cell.focus` / `cell.blur` - Cell editing
- `record.created` / `record.updated` / `record.deleted` - Data changes
- `field.created` / `field.updated` / `field.deleted` - Schema changes

---

### Automations (`/automations`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/automations?table_id={id}` | List automations |
| POST | `/automations` | Create automation |
| GET | `/automations/{id}` | Get automation |
| PATCH | `/automations/{id}` | Update automation |
| DELETE | `/automations/{id}` | Delete automation |
| POST | `/automations/{id}/actions` | Add action |
| PATCH | `/automations/{id}/actions/{action_id}` | Update action |
| DELETE | `/automations/{id}/actions/{action_id}` | Delete action |
| POST | `/automations/{id}/actions/reorder` | Reorder actions |
| POST | `/automations/{id}/trigger` | Manually trigger |
| POST | `/automations/{id}/pause` | Pause automation |
| POST | `/automations/{id}/resume` | Resume automation |
| GET | `/automations/{id}/runs` | Get run history |
| GET | `/automations/{id}/runs/{run_id}` | Get run details |

#### Trigger Types

| Type | Description | Config |
|------|-------------|--------|
| `record_created` | When record is created | `table_id` |
| `record_updated` | When record is updated | `table_id`, `field_ids` (optional) |
| `record_deleted` | When record is deleted | `table_id` |
| `record_matches_conditions` | When record matches filter | `table_id`, `conditions` |
| `field_changed` | When specific field changes | `table_id`, `field_id` |
| `form_submitted` | When form is submitted | `view_id` |
| `scheduled` | Recurring schedule | `cron_expression`, `timezone` |
| `at_scheduled_time` | One-time schedule | `datetime`, `timezone` |
| `webhook_received` | External webhook | `webhook_id` |
| `button_clicked` | Manual button click | `button_id` |

#### Action Types

| Type | Description | Config |
|------|-------------|--------|
| `create_record` | Create a new record | `table_id`, `fields` |
| `update_record` | Update existing record | `record_id`, `fields` |
| `delete_record` | Delete a record | `record_id` |
| `send_email` | Send email | `to`, `subject`, `body` |
| `send_slack_message` | Send Slack message | `webhook_url`, `message` |
| `send_webhook` | Call external API | `url`, `method`, `headers`, `body` |
| `link_records` | Link records | `source_record`, `target_record`, `field_id` |
| `unlink_records` | Unlink records | `source_record`, `target_record`, `field_id` |
| `run_script` | Run custom script | `script`, `language` |
| `conditional` | If/else branching | `condition`, `then_actions`, `else_actions` |
| `loop` | Iterate over records | `records`, `actions` |
| `delay` | Wait before next action | `seconds` |

#### Create Automation
```bash
POST /automations
{
  "name": "Notify on new record",
  "description": "Send email when record created",
  "table_id": "uuid",
  "trigger_type": "record_created",
  "trigger_config": {},
  "is_enabled": true,
  "actions": [
    {
      "type": "send_email",
      "config": {
        "to": "{{trigger.record.Email}}",
        "subject": "Welcome!",
        "body": "Hello {{trigger.record.Name}}"
      },
      "order": 1
    }
  ]
}
```

#### Template Variables

Actions support template variables:
- `{{trigger.record.FieldName}}` - Access trigger record field
- `{{trigger.previous_record.FieldName}}` - Previous value (on update)
- `{{trigger.user.name}}` - User who triggered
- `{{now}}` - Current timestamp

---

### Data Integrity (`/constraints`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/constraints?table_id={id}` | List unique constraints |
| GET | `/constraints?field_id={id}` | List constraints for field |
| POST | `/constraints` | Create unique constraint |
| GET | `/constraints/{id}` | Get constraint |
| PATCH | `/constraints/{id}` | Update constraint |
| DELETE | `/constraints/{id}` | Delete constraint |
| GET | `/fields/{id}/constraint` | Get constraint by field |

#### Create Unique Constraint
```bash
POST /constraints
{
  "field_id": "uuid",
  "case_sensitive": true,
  "error_message": "This value must be unique"
}

# Response
{
  "id": "uuid",
  "field_id": "uuid",
  "case_sensitive": true,
  "status": "active",
  "error_message": "This value must be unique",
  "created_by": "uuid",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Update Constraint
```bash
PATCH /constraints/{id}
{
  "status": "disabled",
  "case_sensitive": false,
  "error_message": "Custom error message"
}
```

**Constraint Status Values:**
- `active` - Constraint is enforced
- `disabled` - Constraint is not enforced
- `pending` - Constraint is being created

#### Constraint Enforcement

Unique constraints are automatically enforced during record creation and updates:

```bash
POST /records
{
  "table_id": "uuid",
  "fields": {
    "Email": "duplicate@example.com"
  }
}

# Response (409 Conflict) if unique constraint violated
{
  "detail": "A record with this value already exists",
  "code": "DUPLICATE_VALUE",
  "field": "Email",
  "value": "duplicate@example.com"
}
```

---

### Field Validation

PyBase enforces data integrity through comprehensive field validation:

#### Required Fields

Fields marked as `required: true` must have a non-null, non-empty value:

```bash
POST /records
{
  "table_id": "uuid",
  "fields": {
    "Name": "",  # Required field - empty string
    "Email": null  # Required field - null value
  }
}

# Response (422 Validation Error)
{
  "detail": "Validation failed",
  "code": "VALIDATION_ERROR",
  "errors": [
    {
      "loc": ["Name"],
      "msg": "Field is required",
      "type": "value_error.required"
    },
    {
      "loc": ["Email"],
      "msg": "Field is required",
      "type": "value_error.required"
    }
  ]
}
```

#### Data Type Validation

Each field type enforces specific validation rules:

| Type | Validation Rules |
|------|------------------|
| `text` | Max length, string format |
| `number` | Numeric value, precision, range |
| `email` | Valid email format |
| `url` | Valid URL format |
| `phone` | Valid phone format |
| `date` / `datetime` | Valid date/time format |
| `currency` | Numeric with precision |
| `percent` | Numeric 0-100 (or 0-1) |
| `single_select` | Must match defined choices |
| `multi_select` | Array of valid choices |
| `rating` | Within min/max range |

---

### Transaction Management

PyBase ensures ACID properties with automatic transaction management:

#### Automatic Rollback

All multi-record operations support automatic rollback on errors:

**Batch Create - All or Nothing:**
```bash
POST /records/batch
{
  "table_id": "uuid",
  "records": [
    {"fields": {"Name": "Record 1", "Email": "valid@example.com"}},
    {"fields": {"Name": "Record 2", "Email": "duplicate@example.com"}},  # Violates unique constraint
    {"fields": {"Name": "Record 3", "Email": "another@example.com"}}
  ]
}

# Response (409 Conflict) - NO records created
{
  "detail": "A record with this value already exists",
  "code": "DUPLICATE_VALUE",
  "field": "Email",
  "index": 1  # Index of failing record
}

# Database state: Zero new records (transaction rolled back)
```

**Batch Update - All or Nothing:**
```bash
PATCH /records/batch
{
  "table_id": "uuid",
  "updates": [
    {"record_id": "uuid1", "fields": {"Status": "Active"}},
    {"record_id": "uuid2", "fields": {"Email": null}}  # Violates required field
  ]
}

# Response (422 Validation Error) - NO records updated
{
  "detail": "Field is required",
  "code": "REQUIRED_FIELD",
  "field": "Email",
  "record_id": "uuid2"
}

# Database state: All records unchanged (transaction rolled back)
```

**Batch Delete - All or Nothing:**
```bash
DELETE /records/batch
{
  "table_id": "uuid",
  "record_ids": ["uuid1", "uuid2", "uuid3"]
}

# If any delete fails (permission, foreign key constraint, etc.)
# Response: Error with details
# Database state: All records remain (transaction rolled back)
```

#### Transaction Isolation

- **Read Committed**: Default isolation level
- **Atomic Operations**: All operations in a transaction succeed or all fail
- **Consistent State**: Database never left in partial state
- **No Silent Failures**: All errors surfaced to client with details

#### Nested Operations

Operations that touch multiple resources (field + record, multiple tables) use shared transactions:

```bash
# Example: Delete field with cascade
DELETE /fields/{id}

# If this fails:
# 1. Field is NOT deleted
# 2. All related data intact
# 3. Transaction fully rolled back
# 4. Error response returned
```

---

### Data Integrity Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `DUPLICATE_VALUE` | 409 | Unique constraint violated |
| `REQUIRED_FIELD` | 422 | Required field missing or empty |
| `VALIDATION_ERROR` | 422 | Field value validation failed |
| `FOREIGN_KEY_VIOLATION` | 409 | Referenced record doesn't exist |
| `CONSTRAINT_DISABLED` | 423 | Constraint is currently disabled |
| `CONSTRAINT_PENDING` | 423 | Constraint creation in progress |

---

### Webhooks (`/webhooks`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/webhooks?table_id={id}` | List webhooks |
| POST | `/webhooks` | Create webhook |
| GET | `/webhooks/{id}` | Get webhook |
| PATCH | `/webhooks/{id}` | Update webhook |
| DELETE | `/webhooks/{id}` | Delete webhook |
| POST | `/webhooks/{id}/test` | Test outgoing webhook |
| POST | `/webhooks/{id}/regenerate-token` | Regenerate incoming token |
| POST | `/webhooks/incoming/{token}` | Receive incoming webhook |

#### Webhook Types

| Type | Description |
|------|-------------|
| `incoming` | Receive data from external systems |
| `outgoing` | Send data to external systems on events |

#### Create Outgoing Webhook
```bash
POST /webhooks
{
  "name": "Notify external system",
  "table_id": "uuid",
  "type": "outgoing",
  "url": "https://api.example.com/webhook",
  "events": ["record.created", "record.updated"],
  "headers": {"X-API-Key": "secret"},
  "is_enabled": true
}
```

#### Create Incoming Webhook
```bash
POST /webhooks
{
  "name": "Receive from Zapier",
  "table_id": "uuid",
  "type": "incoming",
  "field_mappings": {
    "external_name": "Name",
    "external_email": "Email"
  }
}

# Response includes token
{
  "id": "uuid",
  "token": "whk_abc123...",
  "url": "https://api.pybase.com/api/v1/webhooks/incoming/whk_abc123..."
}
```

#### Incoming Webhook Payload
```bash
POST /webhooks/incoming/{token}
{
  "external_name": "John Doe",
  "external_email": "john@example.com"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"
}
```

| Status | Description |
|--------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing/invalid auth |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Invalid data |
| 500 | Server Error - Internal error |

---

## Pagination

List endpoints support pagination:

```bash
GET /records?table_id={id}&limit=100&offset=0

# Response
{
  "items": [...],
  "total": 1000,
  "limit": 100,
  "offset": 0
}
```

---

## Filtering

Records support advanced filtering:

```json
{
  "AND": [
    {"field": "Status", "operator": "eq", "value": "Active"},
    {"field": "Price", "operator": "gt", "value": 100}
  ]
}
```

**Operators:** `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `contains`, `not_contains`, `starts_with`, `ends_with`, `is_empty`, `is_not_empty`

---

## Rate Limiting

- 1000 requests/minute per user
- 100 requests/minute for unauthenticated
- WebSocket: 100 messages/minute per connection
