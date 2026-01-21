# PyBase Field Types Reference

> Complete documentation for all 30+ field types with configuration options, validation rules, and examples

## Overview

PyBase supports a comprehensive set of field types designed for flexible data management, from basic text and numbers to specialized engineering data. Each field type has unique configuration options, validation rules, and serialization behavior.

This document provides in-depth documentation for:
- **Standard Fields**: Text, numeric, temporal, and choice-based data
- **Relational Fields**: Cross-table linking, lookups, and aggregations
- **Engineering Fields**: Dimensions, GD&T, threads, materials, and surface finishes
- **System Fields**: Auto-managed metadata (created/modified time and user tracking)

### Field Type Categories

| Category | Field Types | Use Cases |
|----------|-------------|-----------|
| **Text** | `text`, `long_text`, `email`, `phone`, `url` | Contact info, descriptions, identifiers |
| **Numeric** | `number`, `currency`, `percent`, `autonumber`, `rating` | Quantities, prices, scores, IDs |
| **Temporal** | `date`, `datetime`, `time`, `duration` | Timestamps, schedules, time tracking |
| **Choice** | `checkbox`, `single_select`, `multi_select`, `status` | Categorical data, workflows |
| **Relational** | `link`, `lookup`, `rollup` | Cross-table relationships, aggregations |
| **Computed** | `formula` | Calculated values from other fields |
| **Attachment** | `attachment` | Files, images, documents |
| **Engineering** | `dimension`, `gdt`, `thread`, `material`, `surface_finish` | Technical specifications, CAD data |
| **System** | `created_time`, `last_modified_time`, `created_by`, `last_modified_by` | Audit trails, metadata |

---

## Quick Reference

### Field Configuration Summary

| Field Type | Key Options | Example Use Case |
|------------|-------------|------------------|
| `text` | `max_length` | Product names, descriptions |
| `long_text` | `enable_rich_text`, `max_length` | Detailed descriptions, notes |
| `email` | `allow_multiple` | Contact emails, user accounts |
| `phone` | `default_country_code`, `format` | Phone numbers, support lines |
| `url` | `allowed_protocols`, `require_protocol` | Website links, documentation |
| `number` | `precision`, `allow_negative` | Quantities, measurements |
| `currency` | `currency_symbol`, `precision` | Prices, budgets, costs |
| `percent` | `precision` | Completion rates, efficiency |
| `autonumber` | `prefix` | Record IDs, invoice numbers |
| `rating` | `max`, `icon` | Product ratings, priority scores |
| `date` | `date_format`, `include_time` | Deadlines, birthdays |
| `datetime` | `time_format`, `timezone` | Event timestamps, logs |
| `time` | `time_format` | Working hours, schedules |
| `duration` | `duration_format` | Task duration, time spent |
| `checkbox` | - | Boolean flags, toggles |
| `single_select` | `choices: [{name, color}]` | Status, category, type |
| `multi_select` | `choices: [{name, color}]` | Tags, features, attributes |
| `status` | `choices: [{name, color}]` | Workflow states |
| `link` | `linked_table_id`, `allow_multiple` | Related records |
| `lookup` | `linked_field_id`, `lookup_field_id` | Pull data from linked records |
| `rollup` | `linked_field_id`, `rollup_field_id`, `function` | Aggregate linked data |
| `formula` | `formula` | Computed calculations |
| `attachment` | `allowed_types`, `max_size` | Files, images, PDFs |
| `dimension` | `unit`, `tolerance_type`, `precision` | Engineering dimensions |
| `gdt` | `symbol_types`, `datums` | Geometric tolerancing |
| `thread` | `standard` | Fastener specifications |
| `material` | `properties` | Material specifications |
| `surface_finish` | `roughness_type` | Surface quality (Ra, Rz) |
| `created_time` | - (read-only) | Record creation timestamp |
| `last_modified_time` | - (read-only) | Record update timestamp |
| `created_by` | - (read-only) | Record creator |
| `last_modified_by` | - (read-only) | Last modifier |

---

## Table of Contents

- [Text Fields](#text-fields)
  - [Text](#text)
  - [Long Text](#long-text)
  - [Email](#email)
  - [Phone](#phone)
  - [URL](#url)
- [Numeric Fields](#numeric-fields)
  - [Number](#number)
  - [Currency](#currency)
  - [Percent](#percent)
  - [Autonumber](#autonumber)
  - [Rating](#rating)
- [Temporal Fields](#temporal-fields)
  - [Date](#date)
  - [DateTime](#datetime)
  - [Time](#time)
  - [Duration](#duration)
- [Choice Fields](#choice-fields)
  - [Checkbox](#checkbox)
  - [Single Select](#single-select)
  - [Multi Select](#multi-select)
  - [Status](#status)
- [Relational Fields](#relational-fields)
  - [Link (Linked Record)](#link-linked-record)
  - [Lookup](#lookup)
  - [Rollup](#rollup)
- [Computed Fields](#computed-fields)
  - [Formula](#formula)
- [Attachment Fields](#attachment-fields)
  - [Attachment](#attachment)
- [Engineering Fields](#engineering-fields)
  - [Dimension](#dimension)
  - [GD&T (Geometric Dimensioning & Tolerancing)](#gdt-geometric-dimensioning--tolerancing)
  - [Thread](#thread)
  - [Material](#material)
  - [Surface Finish](#surface-finish)
- [System Fields](#system-fields)
  - [Created Time](#created-time)
  - [Last Modified Time](#last-modified-time)
  - [Created By](#created-by)
  - [Last Modified By](#last-modified-by)
- [API Usage Examples](#api-usage-examples)

---

## Text Fields

Text fields store string-based data with various validation and formatting rules. PyBase supports single-line text, multi-line text, and specialized text fields for emails, phone numbers, and URLs.

### Text

**Field Type:** `text`

Single-line text field for short strings like names, titles, SKUs, and identifiers.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_length` | integer | `255` | Maximum character length (1-65535) |

#### Validation Rules

- Must be a string value
- Length must not exceed `max_length`
- Stored and returned as-is (no transformations)
- Empty strings are allowed
- `null` values are converted to empty string `""`

#### Default Value

Empty string `""`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Product Name",
  "type": "text",
  "options": {
    "max_length": 100
  }
}
```

**Record Value:**
```json
{
  "fields": {
    "Product Name": "Precision Ball Bearing 608-2RS"
  }
}
```

#### Use Cases

- Product names and SKUs
- Short descriptions and titles
- Identifiers and reference codes
- Names (first, last, company)
- Categories and tags

---

### Long Text

**Field Type:** `long_text`

Multi-line text field for longer content like descriptions, notes, and comments. Supports optional rich text formatting.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enable_rich_text` | boolean | `false` | Enable rich text formatting (Markdown/HTML) |
| `max_length` | integer | `10000` | Maximum character length |

#### Validation Rules

- Accepts multi-line string content
- Length must not exceed `max_length`
- When `enable_rich_text` is true, supports Markdown or HTML formatting
- Line breaks are preserved
- Empty strings are allowed

#### Default Value

Empty string `""`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Description",
  "type": "long_text",
  "options": {
    "enable_rich_text": true,
    "max_length": 5000
  }
}
```

**Record Value (Plain Text):**
```json
{
  "fields": {
    "Description": "This is a multi-line description.\nLine 2 of the description.\nLine 3 with more details."
  }
}
```

**Record Value (Rich Text):**
```json
{
  "fields": {
    "Description": "## Product Overview\n\n**Features:**\n- High precision\n- Corrosion resistant\n- ISO certified"
  }
}
```

#### Use Cases

- Product descriptions
- Meeting notes and comments
- Project documentation
- Detailed specifications
- Instructions and procedures

---

### Email

**Field Type:** `email`

Email address field with RFC 5322 validation. Automatically normalizes email addresses to lowercase.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allow_multiple` | boolean | `false` | Allow multiple comma-separated email addresses |

#### Validation Rules

- Must match email format: `user@domain.tld`
- Automatically converted to lowercase for storage
- Valid email pattern: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}`
- When `allow_multiple` is true, accepts comma-separated list
- Empty strings and `null` are allowed

#### Default Value

`null`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Contact Email",
  "type": "email",
  "options": {
    "allow_multiple": false
  }
}
```

**Record Value (Single Email):**
```json
{
  "fields": {
    "Contact Email": "john.doe@example.com"
  }
}
```

**Record Value (Multiple Emails):**
```json
{
  "name": "CC Recipients",
  "type": "email",
  "options": {
    "allow_multiple": true
  }
}
```

```json
{
  "fields": {
    "CC Recipients": ["alice@example.com", "bob@example.com"]
  }
}
```

#### Use Cases

- Contact email addresses
- User account emails
- Support and notification emails
- CC/BCC recipient lists
- Email distribution groups

---

### Phone

**Field Type:** `phone`

Phone number field with flexible format support. Validates minimum digit requirements and normalizes storage format.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `default_country_code` | string | `null` | Default country code (e.g., "+1") |
| `format` | string | `null` | Display format style |

#### Validation Rules

- Accepts various formats: `(555) 123-4567`, `555-123-4567`, `+1-555-123-4567`
- Minimum 7 digits required
- Maximum 15 digits allowed (per E.164 standard)
- Allows spaces, hyphens, parentheses, dots, and `+` for country codes
- Stored in normalized format (digits and `+` only)
- Empty strings and `null` are allowed

#### Default Value

`null`

#### Formatting

US phone numbers (10 digits) are automatically formatted as `(555) 123-4567`
International numbers (11 digits starting with 1) formatted as `+1 (555) 123-4567`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Phone Number",
  "type": "phone",
  "options": {
    "default_country_code": "+1"
  }
}
```

**Record Value (Various Formats):**
```json
{
  "fields": {
    "Phone Number": "+1-555-123-4567"
  }
}
```

```json
{
  "fields": {
    "Phone Number": "(555) 123-4567"
  }
}
```

```json
{
  "fields": {
    "Phone Number": "555.123.4567"
  }
}
```

All three examples above are stored as: `+15551234567`

#### Use Cases

- Contact phone numbers
- Support hotlines
- Emergency contacts
- Mobile and landline numbers
- International phone numbers

---

### URL

**Field Type:** `url`

URL field with protocol and domain validation. Automatically adds `https://` protocol if missing.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allowed_protocols` | array | `["http", "https"]` | List of allowed URL protocols |
| `require_protocol` | boolean | `true` | Require protocol in URL (e.g., `https://`) |

#### Validation Rules

- Must be a valid URL with protocol and domain
- Allowed protocols: `http`, `https` (configurable)
- Domain must be valid (supports localhost and IP addresses)
- If protocol is missing and `require_protocol` is false, `https://` is automatically added
- Empty strings and `null` are allowed

#### Default Value

`null`

#### Auto-Correction

If a URL is entered without a protocol (e.g., `example.com`), it will be automatically prefixed with `https://` during serialization.

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Website",
  "type": "url",
  "options": {
    "allowed_protocols": ["http", "https"],
    "require_protocol": false
  }
}
```

**Record Value:**
```json
{
  "fields": {
    "Website": "https://www.example.com/docs"
  }
}
```

**Auto-Corrected Input:**
```json
// Input:
{
  "fields": {
    "Website": "example.com"
  }
}

// Stored as:
{
  "fields": {
    "Website": "https://example.com"
  }
}
```

#### Use Cases

- Company websites
- Documentation links
- Product URLs
- External resource links
- API endpoint URLs
- Repository links (GitHub, GitLab)

---

## Numeric Fields

Numeric fields store and validate numeric data including integers, decimals, monetary values, percentages, auto-incrementing IDs, and ratings. Each type provides specialized formatting, validation, and display options.

### Number

**Field Type:** `number`

General-purpose numeric field for storing integers and floating-point values. Supports precision control, range validation, and positive/negative constraints.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `min_value` | float | `null` | Minimum allowed value (inclusive) |
| `max_value` | float | `null` | Maximum allowed value (inclusive) |
| `precision` | integer | `null` | Number of decimal places to enforce |

#### Validation Rules

- Must be a numeric value (integer or float)
- Automatically converts to `float` for storage
- Value must be >= `min_value` if specified
- Value must be <= `max_value` if specified
- If `precision` is set, value must not exceed specified decimal places
- `null` values are allowed

#### Default Value

`0.0`

#### Storage Format

All numeric values are stored as `float` in the database for consistency, even if entered as integers.

#### JSON Examples

**Field Definition (Basic):**
```json
{
  "name": "Quantity",
  "type": "number",
  "options": {}
}
```

**Field Definition (With Constraints):**
```json
{
  "name": "Temperature",
  "type": "number",
  "options": {
    "min_value": -273.15,
    "max_value": 1000.0,
    "precision": 2
  }
}
```

**Record Value:**
```json
{
  "fields": {
    "Quantity": 42,
    "Temperature": 25.75
  }
}
```

#### Use Cases

- Inventory quantities
- Measurements and dimensions
- Weights and volumes
- Counts and tallies
- Scientific values
- Generic numeric data

---

### Currency

**Field Type:** `currency`

Monetary value field with multi-currency support, precision control, and locale-aware formatting. Stores raw numeric values with currency metadata for display.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `currency_code` | string | `"USD"` | ISO 4217 currency code (USD, EUR, GBP, etc.) |
| `precision` | integer | `2` | Number of decimal places |
| `symbol_position` | string | `"prefix"` | Symbol position: `"prefix"` or `"suffix"` |
| `allow_negative` | boolean | `true` | Allow negative values (credits/refunds) |
| `min_value` | float | `null` | Minimum allowed value |
| `max_value` | float | `null` | Maximum allowed value |

#### Supported Currencies

Built-in support for 12+ currencies with automatic symbol mapping:

| Currency Code | Symbol | Example Display |
|---------------|--------|-----------------|
| `USD` | `$` | `$1,234.56` |
| `EUR` | `€` | `€1.234,56` |
| `GBP` | `£` | `£1,234.56` |
| `JPY` | `¥` | `¥1,235` |
| `CNY` | `¥` | `¥1,234.56` |
| `KRW` | `₩` | `₩1,235` |
| `INR` | `₹` | `₹1,234.56` |
| `BRL` | `R$` | `R$1.234,56` |
| `CAD` | `CA$` | `CA$1,234.56` |
| `AUD` | `A$` | `A$1,234.56` |
| `CHF` | `CHF` | `CHF 1,234.56` |
| `MXN` | `MX$` | `MX$1,234.56` |

#### Validation Rules

- Must be a numeric value (integer or float)
- Stored as `float` in database
- If `allow_negative` is `false`, rejects values < 0
- Value must be >= `min_value` if specified
- Value must be <= `max_value` if specified
- Precision validation ensures value doesn't exceed decimal places
- `null` values are allowed

#### Default Value

`0.0`

#### Display Formatting

The `format_display()` method provides locale-aware formatting:
- Adds currency symbol based on `currency_code`
- Positions symbol according to `symbol_position`
- Formats with thousand separators and decimal precision
- Handles negative values with leading minus sign

#### JSON Examples

**Field Definition (USD):**
```json
{
  "name": "Unit Price",
  "type": "currency",
  "options": {
    "currency_code": "USD",
    "precision": 2,
    "symbol_position": "prefix",
    "allow_negative": false,
    "min_value": 0
  }
}
```

**Field Definition (EUR):**
```json
{
  "name": "Budget",
  "type": "currency",
  "options": {
    "currency_code": "EUR",
    "precision": 2,
    "allow_negative": true
  }
}
```

**Record Value:**
```json
{
  "fields": {
    "Unit Price": 1299.99,
    "Budget": 50000.00
  }
}
```

**Formatted Display Examples:**
```json
// $1,299.99 (USD prefix)
// €50.000,00 (EUR suffix in some locales)
// ₹1,299.99 (INR prefix)
```

#### Use Cases

- Product pricing
- Order totals and subtotals
- Budgets and cost tracking
- Invoice amounts
- Financial transactions
- Salary and compensation
- Multi-currency e-commerce

---

### Percent

**Field Type:** `percent`

Percentage field that stores values as decimals (0.5 = 50%) with automatic conversion and display formatting. Ideal for rates, completion tracking, and efficiency metrics.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `precision` | integer | `2` | Decimal places for display (e.g., 50.25%) |
| `min_value` | float | `null` | Minimum value as decimal (0 = 0%, 1 = 100%) |
| `max_value` | float | `null` | Maximum value as decimal (1 = 100%, 2 = 200%) |
| `allow_negative` | boolean | `true` | Allow negative percentages |

#### Storage Format

**Critical:** Percentages are stored as decimal values in the database:
- `50%` is stored as `0.5`
- `100%` is stored as `1.0`
- `150%` is stored as `1.5`

#### Automatic Conversion

The field handler intelligently converts input values:
- If input > 1 (e.g., `50`), assumes percentage → converts to `0.5`
- If input ≤ 1 (e.g., `0.5`), assumes already decimal → stores as-is
- This allows flexible input while maintaining consistent storage

#### Validation Rules

- Must be a numeric value
- Automatically normalizes to decimal for validation
- If `allow_negative` is `false`, rejects values < 0
- Value must be >= `min_value` if specified (as decimal)
- Value must be <= `max_value` if specified (as decimal)
- `null` values are allowed

#### Default Value

`0.0` (represents 0%)

#### Display Formatting

The `format_display()` method converts decimal to percentage:
- Multiplies value by 100
- Formats with specified precision
- Appends `%` symbol
- Example: `0.7525` → `"75.25%"` (precision=2)

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Completion Rate",
  "type": "percent",
  "options": {
    "precision": 2,
    "min_value": 0,
    "max_value": 1,
    "allow_negative": false
  }
}
```

**Field Definition (Efficiency - Can Exceed 100%):**
```json
{
  "name": "Efficiency",
  "type": "percent",
  "options": {
    "precision": 1,
    "max_value": 2.0
  }
}
```

**Record Value (Input as Percentage):**
```json
{
  "fields": {
    "Completion Rate": 85.5
  }
}
// Stored as: 0.855
// Displayed as: "85.50%"
```

**Record Value (Input as Decimal):**
```json
{
  "fields": {
    "Completion Rate": 0.855
  }
}
// Stored as: 0.855
// Displayed as: "85.50%"
```

#### Use Cases

- Task completion percentages
- Project progress tracking
- Test scores and grades
- Discount rates
- Tax rates
- Commission percentages
- Manufacturing efficiency
- Quality metrics (yield, defect rates)
- Growth rates and margins

---

### Autonumber

**Field Type:** `autonumber`

Auto-incrementing numeric field that generates unique sequential identifiers. System-managed and typically read-only for users, ideal for record IDs, invoice numbers, and tracking codes.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `prefix` | string | `""` | Text prefix for display (e.g., `"INV-"`) |
| `start_value` | integer | `1` | Starting number for sequence |
| `padding` | integer | `4` | Zero-padding width (e.g., 4 → `0001`) |

#### Storage Format

Stores the raw integer value in the database. Formatting (prefix and padding) is applied during display only.

**Example:**
- **Stored:** `42`
- **Displayed:** `"INV-0042"` (with prefix="INV-", padding=4)

#### Generation Behavior

- **System-Managed:** Values are automatically generated when records are created
- **Sequential:** Increments from `start_value` by 1 for each new record
- **Unique:** Each record gets a unique number within the table
- **Immutable:** Once assigned, the value does not change
- **Read-Only:** Typically not user-editable (managed by the system)

#### Validation Rules

- Must be a non-negative integer
- Can extract number from formatted string (e.g., `"INV-0042"` → `42`)
- Automatically generated values start from `start_value`
- Manual assignments (if allowed) must be positive integers
- `null` is allowed (indicates value not yet assigned)

#### Default Value

`null` (assigned by system on record creation)

#### Display Formatting

The `format_display()` method creates formatted strings:
```python
format_display(42, {"prefix": "INV-", "padding": 4})
# Returns: "INV-0042"

format_display(7, {"prefix": "PO-", "padding": 6})
# Returns: "PO-000007"

format_display(123, {"prefix": "", "padding": 3})
# Returns: "123" (no padding applied since value exceeds padding width)
```

#### Next Value Generation

The `generate_next()` method calculates the next autonumber:
```python
# First record
generate_next(None, {"start_value": 100})
# Returns: 100

# Subsequent records
generate_next(142, {})
# Returns: 143
```

#### JSON Examples

**Field Definition (Invoice Numbers):**
```json
{
  "name": "Invoice Number",
  "type": "autonumber",
  "options": {
    "prefix": "INV-",
    "start_value": 1000,
    "padding": 5
  }
}
```

**Field Definition (Purchase Orders):**
```json
{
  "name": "PO Number",
  "type": "autonumber",
  "options": {
    "prefix": "PO-",
    "start_value": 1,
    "padding": 4
  }
}
```

**Field Definition (Simple Counter):**
```json
{
  "name": "Record ID",
  "type": "autonumber",
  "options": {
    "prefix": "",
    "start_value": 1,
    "padding": 6
  }
}
```

**Record Value:**
```json
{
  "fields": {
    "Invoice Number": 1042
  }
}
// Displayed as: "INV-01042"
```

**API Response (with formatting):**
```json
{
  "id": "rec_abc123",
  "fields": {
    "Invoice Number": {
      "value": 1042,
      "formatted": "INV-01042"
    }
  }
}
```

#### Use Cases

- Invoice numbers and billing IDs
- Purchase order numbers
- Customer/Account IDs
- Ticket and case numbers
- Serial numbers for manufactured goods
- Batch/Lot numbers
- Work order numbers
- Sequential reference codes
- Shipment tracking numbers

#### Implementation Notes

- The backend must track the current maximum value per table
- Concurrent record creation requires proper locking to prevent duplicate numbers
- Deleted records do not free up their autonumbers (gaps are expected)
- Autonumber sequences are per-table, not global

---

### Rating

**Field Type:** `rating`

Visual rating field for scoring and ranking using customizable icons (stars, hearts, circles). Supports whole and half-increment ratings with configurable maximum values.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_rating` | integer | `5` | Maximum rating value (typically 5 or 10) |
| `icon` | string | `"star"` | Icon style: `"star"`, `"heart"`, `"circle"` |
| `allow_half` | boolean | `false` | Allow half-increment ratings (e.g., 3.5) |

#### Icon Styles

| Icon Type | Filled | Empty | Half | Example Display (3.5/5) |
|-----------|--------|-------|------|-------------------------|
| `star` | ★ | ☆ | ⯪ | ★★★⯪☆ |
| `heart` | ♥ | ♡ | ♡ | ♥♥♥♡♡ |
| `circle` | ● | ○ | ◐ | ●●●◐○ |

#### Validation Rules

- Must be a numeric value (float)
- Value must be >= 0
- Value must be <= `max_rating`
- If `allow_half` is `true`: value must be a multiple of 0.5 (e.g., 0, 0.5, 1.0, 1.5, ...)
- If `allow_half` is `false`: value must be a whole number (integer)
- `null` values are allowed (represents "not rated")

#### Default Value

`null` (no rating)

#### Storage Format

Stored as `float` in database to support half-ratings. Whole ratings are stored as `1.0`, `2.0`, etc.

#### Display Formatting

The `format_display()` method creates visual icon representations:

```python
# 5-star rating (full stars)
format_display(4, {"max_rating": 5, "icon": "star"})
# Returns: "★★★★☆"

# Half-star rating
format_display(3.5, {"max_rating": 5, "icon": "star", "allow_half": true})
# Returns: "★★★⯪☆"

# Heart rating
format_display(2, {"max_rating": 5, "icon": "heart"})
# Returns: "♥♥♡♡♡"

# Circle rating (10-point scale)
format_display(7, {"max_rating": 10, "icon": "circle"})
# Returns: "●●●●●●●○○○"
```

#### JSON Examples

**Field Definition (5-Star Product Rating):**
```json
{
  "name": "Product Rating",
  "type": "rating",
  "options": {
    "max_rating": 5,
    "icon": "star",
    "allow_half": false
  }
}
```

**Field Definition (Priority Score with Half-Values):**
```json
{
  "name": "Priority",
  "type": "rating",
  "options": {
    "max_rating": 5,
    "icon": "circle",
    "allow_half": true
  }
}
```

**Field Definition (10-Point Scale):**
```json
{
  "name": "Quality Score",
  "type": "rating",
  "options": {
    "max_rating": 10,
    "icon": "star",
    "allow_half": false
  }
}
```

**Record Value (Whole Rating):**
```json
{
  "fields": {
    "Product Rating": 4
  }
}
// Displayed as: ★★★★☆
```

**Record Value (Half Rating):**
```json
{
  "fields": {
    "Priority": 3.5
  }
}
// Displayed as: ●●●◐○
```

**Record Value (Not Rated):**
```json
{
  "fields": {
    "Product Rating": null
  }
}
// Displayed as: (empty or "Not Rated")
```

#### Use Cases

- Product and service ratings
- Customer satisfaction scores
- Priority levels
- Quality ratings
- Difficulty levels
- User reviews
- Task importance
- Performance evaluations
- Recommendation scores
- Risk assessments

#### UI Considerations

- Clicking on icons should set the rating to that value
- Visual feedback on hover for interactive rating selection
- Display average ratings for aggregated views
- Support read-only mode for displaying ratings without editing
- Mobile-friendly touch targets for icon selection

---

## Temporal Fields

_Documentation for date and time field types will be added in subsequent subtasks._

---

## Choice Fields

_Documentation for choice-based field types will be added in subsequent subtasks._

---

## Relational Fields

_Documentation for relational field types will be added in subsequent subtasks._

---

## Computed Fields

_Documentation for computed field types will be added in subsequent subtasks._

---

## Attachment Fields

_Documentation for attachment field types will be added in subsequent subtasks._

---

## Engineering Fields

_Documentation for engineering-specific field types will be added in subsequent subtasks._

---

## System Fields

_Documentation for system-managed field types will be added in subsequent subtasks._

---

## API Usage Examples

_API usage examples and field creation snippets will be added in subsequent subtasks._

---

## See Also

- [API Reference](./api.md) - Complete API endpoint documentation
- [Project Overview](./project-overview-pdr.md) - Product requirements and architecture
- [README](../README.md) - Getting started guide
