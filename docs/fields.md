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

Temporal fields handle date and time data with support for various formats, timezones, and duration tracking. PyBase provides specialized field types for dates, date-times, times, and durations with flexible formatting and validation options.

### Date

**Field Type:** `date`

Calendar date field for storing dates without time information. Stores and validates dates in ISO 8601 format (YYYY-MM-DD) with optional min/max date constraints.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `min_date` | string | `null` | Minimum allowed date (ISO format: YYYY-MM-DD) |
| `max_date` | string | `null` | Maximum allowed date (ISO format: YYYY-MM-DD) |

#### Storage Format

Dates are stored in ISO 8601 format: `YYYY-MM-DD`
- Example: `"2024-03-15"`

#### Validation Rules

- Accepts Python `date` objects, `datetime` objects, or ISO format strings
- If `datetime` is provided, extracts date portion only (time is discarded)
- Validates against `min_date` constraint if specified
- Validates against `max_date` constraint if specified
- Invalid date formats raise `ValueError`
- `null` values are allowed

#### Default Value

`null`

#### Auto-Conversion

The field handler automatically converts various input formats:
- **Python `date` object:** Converted to ISO string
- **Python `datetime` object:** Date portion extracted, time discarded
- **ISO string:** Validated and normalized
- **Invalid formats:** Raises `ValueError`

#### JSON Examples

**Field Definition (Basic):**
```json
{
  "name": "Due Date",
  "type": "date",
  "options": {}
}
```

**Field Definition (With Constraints):**
```json
{
  "name": "Project Start Date",
  "type": "date",
  "options": {
    "min_date": "2024-01-01",
    "max_date": "2024-12-31"
  }
}
```

**Record Value:**
```json
{
  "fields": {
    "Due Date": "2024-06-15"
  }
}
```

**Input Variations (all stored as "2024-06-15"):**
```json
// ISO string
{
  "fields": {
    "Due Date": "2024-06-15"
  }
}

// Python date object (in API)
from datetime import date
{
  "fields": {
    "Due Date": date(2024, 6, 15)
  }
}

// Python datetime object (time discarded)
from datetime import datetime
{
  "fields": {
    "Due Date": datetime(2024, 6, 15, 14, 30)  // Stored as "2024-06-15"
  }
}
```

#### Use Cases

- Project deadlines and milestones
- Birthdays and anniversaries
- Start and end dates
- Delivery dates
- Expiration dates
- Historical dates
- Event scheduling (date-only)
- Contract dates
- Manufacturing dates

---

### DateTime

**Field Type:** `datetime`

Date and time field with timezone support. Stores precise timestamps in ISO 8601 format with timezone information. Supports flexible time formatting options for display.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `include_time` | boolean | `true` | Whether to display time portion |
| `time_format` | string | `"24h"` | Time format: `"12h"` or `"24h"` |
| `timezone` | string | `"UTC"` | Default timezone name (e.g., "UTC", "America/New_York") |
| `date_format` | string | `null` | Optional strftime format for date display |
| `min_date` | string | `null` | Minimum allowed datetime (ISO format) |
| `max_date` | string | `null` | Maximum allowed datetime (ISO format) |

#### Storage Format

Stored in ISO 8601 format with timezone: `YYYY-MM-DDTHH:MM:SS+TZ`
- Example: `"2024-03-15T14:30:00+00:00"`
- All datetimes are timezone-aware
- Naive datetimes are automatically converted to UTC

#### Timezone Handling

**Critical:** All datetimes are stored with timezone information:
- **Timezone-aware inputs:** Stored as-is with their timezone
- **Naive inputs (no timezone):** Automatically assigned UTC timezone
- **"Z" suffix:** Converted to "+00:00" for consistency
- **Display:** Can be converted to user's preferred timezone in UI

#### Validation Rules

- Accepts Python `datetime` objects or ISO 8601 strings
- Naive datetimes (without timezone) are converted to UTC
- Validates against `min_date` constraint if specified
- Validates against `max_date` constraint if specified
- Invalid datetime formats raise `ValueError`
- `null` values are allowed

#### Default Value

`null`

#### Display Formatting

The `format_display()` method provides flexible formatting:

**24-hour format with time:**
```python
format_display("2024-03-15T14:30:00+00:00", {"time_format": "24h", "include_time": True})
# Returns: "2024-03-15 14:30"
```

**12-hour format with time:**
```python
format_display("2024-03-15T14:30:00+00:00", {"time_format": "12h", "include_time": True})
# Returns: "2024-03-15 02:30 PM"
```

**Date only (time hidden):**
```python
format_display("2024-03-15T14:30:00+00:00", {"include_time": False})
# Returns: "2024-03-15"
```

#### JSON Examples

**Field Definition (Basic Timestamp):**
```json
{
  "name": "Event Time",
  "type": "datetime",
  "options": {
    "include_time": true,
    "time_format": "24h",
    "timezone": "UTC"
  }
}
```

**Field Definition (12-Hour Format):**
```json
{
  "name": "Appointment",
  "type": "datetime",
  "options": {
    "include_time": true,
    "time_format": "12h",
    "timezone": "America/New_York"
  }
}
```

**Field Definition (Date-Only Display):**
```json
{
  "name": "Published Date",
  "type": "datetime",
  "options": {
    "include_time": false
  }
}
```

**Field Definition (With Constraints):**
```json
{
  "name": "Meeting Time",
  "type": "datetime",
  "options": {
    "time_format": "12h",
    "min_date": "2024-01-01T00:00:00+00:00",
    "max_date": "2024-12-31T23:59:59+00:00"
  }
}
```

**Record Value (ISO 8601):**
```json
{
  "fields": {
    "Event Time": "2024-06-15T14:30:00+00:00"
  }
}
```

**Record Value (Alternative Formats):**
```json
// With Z suffix (converted to +00:00)
{
  "fields": {
    "Event Time": "2024-06-15T14:30:00Z"
  }
}
// Stored as: "2024-06-15T14:30:00+00:00"

// Naive datetime (converted to UTC)
{
  "fields": {
    "Event Time": "2024-06-15T14:30:00"
  }
}
// Stored as: "2024-06-15T14:30:00+00:00"

// With timezone offset
{
  "fields": {
    "Event Time": "2024-06-15T10:30:00-04:00"
  }
}
// Stored as: "2024-06-15T10:30:00-04:00"
```

#### Use Cases

- Event timestamps and schedules
- Log entries and audit trails
- Meeting and appointment times
- Creation and modification timestamps
- Time-sensitive notifications
- Booking and reservation times
- International event coordination
- System activity logs
- Transaction timestamps
- Delivery time windows

#### Implementation Notes

- Always use timezone-aware datetimes in application code
- Convert to user's local timezone in UI/frontend
- Store all times in UTC for consistency (recommended)
- Use `min_date` and `max_date` for scheduling constraints
- Consider daylight saving time when working with specific timezones

---

### Time

**Field Type:** `time`

Time-of-day field for storing hours, minutes, and seconds without date information. Supports multiple input formats and flexible display options with 12-hour or 24-hour formatting.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `time_format` | string | `"24h"` | Display format: `"12h"` or `"24h"` |
| `include_seconds` | boolean | `false` | Whether to display seconds in formatted output |

#### Storage Format

Stored as HH:MM:SS string in 24-hour format:
- Example: `"14:30:00"`
- Always includes seconds for storage consistency
- Display formatting controlled by `include_seconds` option

#### Accepted Input Formats

The field handler accepts multiple time formats:

| Format | Example | Description |
|--------|---------|-------------|
| `HH:MM:SS` | `"14:30:00"` | 24-hour with seconds |
| `HH:MM` | `"14:30"` | 24-hour without seconds |
| `I:MM:SS AM/PM` | `"02:30:00 PM"` | 12-hour with seconds |
| `I:MM AM/PM` | `"02:30 PM"` | 12-hour without seconds |
| `I:MM:SSAM/PM` | `"02:30:00PM"` | 12-hour (no space) |
| `I:MM AM/PM` | `"2:30 PM"` | 12-hour single-digit hour |

All formats are normalized to `HH:MM:SS` for storage.

#### Validation Rules

- Accepts Python `time` objects or time strings
- Parses multiple common time formats (see table above)
- Invalid time formats raise `ValueError`
- Hours must be 0-23 (24-hour) or 1-12 (12-hour with AM/PM)
- Minutes and seconds must be 0-59
- `null` values are allowed

#### Default Value

`null`

#### Display Formatting

The `format_display()` method provides flexible time formatting:

**24-hour format without seconds:**
```python
format_display("14:30:00", {"time_format": "24h", "include_seconds": False})
# Returns: "14:30"
```

**24-hour format with seconds:**
```python
format_display("14:30:45", {"time_format": "24h", "include_seconds": True})
# Returns: "14:30:45"
```

**12-hour format without seconds:**
```python
format_display("14:30:00", {"time_format": "12h", "include_seconds": False})
# Returns: "2:30 PM"
```

**12-hour format with seconds:**
```python
format_display("14:30:45", {"time_format": "12h", "include_seconds": True})
# Returns: "2:30:45 PM"
```

**Leading zero removed in 12-hour format:**
```python
format_display("09:15:00", {"time_format": "12h"})
# Returns: "9:15 AM" (not "09:15 AM")
```

#### JSON Examples

**Field Definition (24-Hour Format):**
```json
{
  "name": "Work Start Time",
  "type": "time",
  "options": {
    "time_format": "24h",
    "include_seconds": false
  }
}
```

**Field Definition (12-Hour Format):**
```json
{
  "name": "Meeting Time",
  "type": "time",
  "options": {
    "time_format": "12h",
    "include_seconds": false
  }
}
```

**Field Definition (With Seconds):**
```json
{
  "name": "Precise Time",
  "type": "time",
  "options": {
    "time_format": "24h",
    "include_seconds": true
  }
}
```

**Record Value (24-Hour):**
```json
{
  "fields": {
    "Work Start Time": "09:00:00"
  }
}
// Displayed as: "09:00" (if include_seconds=false)
// Displayed as: "9:00 AM" (if time_format="12h")
```

**Record Value (Input Variations):**
```json
// All of these inputs are stored as "14:30:00"

// 24-hour with seconds
{
  "fields": {
    "Meeting Time": "14:30:00"
  }
}

// 24-hour without seconds
{
  "fields": {
    "Meeting Time": "14:30"
  }
}

// 12-hour format
{
  "fields": {
    "Meeting Time": "2:30 PM"
  }
}

// 12-hour with seconds
{
  "fields": {
    "Meeting Time": "02:30:00 PM"
  }
}

// 12-hour no space
{
  "fields": {
    "Meeting Time": "2:30PM"
  }
}
```

#### Use Cases

- Business hours and operating times
- Shift start/end times
- Meeting and appointment times
- Daily schedules and routines
- Time-of-day triggers
- Alarm and reminder times
- Service availability windows
- Recurring event times
- Time tracking and timesheets
- Clock-in/clock-out times

#### Implementation Notes

- Store time separately from date for recurring schedules
- Combine with date field for full datetime when needed
- Use `time_format` based on user locale preferences
- `include_seconds` typically false for user-facing times
- Consider timezone implications when combining time with dates

---

### Duration

**Field Type:** `duration`

Duration field for storing time spans and elapsed time. Stores durations as total seconds with flexible input parsing and multiple display format options.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `format` | string | `"h:mm:ss"` | Display format: `"h:mm"`, `"h:mm:ss"`, or `"compact"` |
| `max_duration` | integer | `null` | Maximum duration in seconds |

#### Storage Format

**Critical:** Durations are stored as **total seconds** (integer):
- `2h 30m` → stored as `9000` seconds
- `1:45:30` → stored as `6330` seconds
- `30m` → stored as `1800` seconds

This allows for easy calculations and aggregations.

#### Accepted Input Formats

The field handler accepts multiple duration formats:

| Format | Examples | Stored As (seconds) |
|--------|----------|---------------------|
| **Human Format** | `"2h 30m 15s"`, `"2h30m15s"`, `"2 hours 30 minutes"` | `9015` |
| **Colon Format** | `"2:30:15"`, `"2:30"` | `9015`, `9000` |
| **Single Units** | `"2h"`, `"30m"`, `"45s"` | `7200`, `1800`, `45` |
| **Seconds Only** | `"3600"`, `3600` | `3600` |
| **Mixed** | `"1h 15s"`, `"2h30m"` | `3615`, `9000` |

#### Parsing Rules

**Human format patterns:**
- Hours: `h`, `hour`, `hours` (case-insensitive)
- Minutes: `m`, `min`, `minute`, `minutes`
- Seconds: `s`, `sec`, `second`, `seconds`
- Spaces are optional: `"2h30m"` or `"2h 30m"` both work

**Colon format:**
- `H:MM` → hours and minutes (e.g., `"2:30"` = 2h 30m)
- `H:MM:SS` → hours, minutes, seconds (e.g., `"2:30:15"`)

**Plain numbers:**
- Assumed to be seconds (e.g., `"3600"` = 1 hour)

#### Validation Rules

- Must be a positive integer (seconds), float, or parseable string
- Duration cannot be negative
- If `max_duration` is set, value must not exceed it
- Invalid formats raise `ValueError`
- Empty string converts to `0`
- `null` values are allowed

#### Default Value

`0` (zero duration)

#### Display Formatting

The `format_display()` method supports three format styles:

**Format: `"h:mm:ss"` (default)**
```python
format_display(9015, {"format": "h:mm:ss"})
# Returns: "2:30:15"

format_display(3600, {"format": "h:mm:ss"})
# Returns: "1:00:00"
```

**Format: `"h:mm"`**
```python
format_display(9000, {"format": "h:mm"})
# Returns: "2:30"

format_display(7200, {"format": "h:mm"})
# Returns: "2:00"
```

**Format: `"compact"`**
```python
format_display(9015, {"format": "compact"})
# Returns: "2h 30m 15s"

format_display(7200, {"format": "compact"})
# Returns: "2h"

format_display(90, {"format": "compact"})
# Returns: "1m 30s"

format_display(45, {"format": "compact"})
# Returns: "45s"
```

The compact format omits zero values for cleaner display.

#### JSON Examples

**Field Definition (Hours and Minutes):**
```json
{
  "name": "Task Duration",
  "type": "duration",
  "options": {
    "format": "h:mm"
  }
}
```

**Field Definition (Full Precision):**
```json
{
  "name": "Elapsed Time",
  "type": "duration",
  "options": {
    "format": "h:mm:ss"
  }
}
```

**Field Definition (Compact Display):**
```json
{
  "name": "Time Spent",
  "type": "duration",
  "options": {
    "format": "compact"
  }
}
```

**Field Definition (With Maximum):**
```json
{
  "name": "Meeting Duration",
  "type": "duration",
  "options": {
    "format": "h:mm",
    "max_duration": 28800
  }
}
```
// max_duration: 28800 = 8 hours

**Record Value (Stored as Seconds):**
```json
{
  "fields": {
    "Task Duration": 9000
  }
}
// Displayed as: "2:30" (format="h:mm")
// Displayed as: "2:30:00" (format="h:mm:ss")
// Displayed as: "2h 30m" (format="compact")
```

**Input Variations (all stored as 9000 seconds):**
```json
// Human format
{
  "fields": {
    "Task Duration": "2h 30m"
  }
}

// Colon format
{
  "fields": {
    "Task Duration": "2:30"
  }
}

// Seconds
{
  "fields": {
    "Task Duration": 9000
  }
}

// Mixed format
{
  "fields": {
    "Task Duration": "2 hours 30 minutes"
  }
}
```

**API Response (with formatting):**
```json
{
  "id": "rec_abc123",
  "fields": {
    "Task Duration": {
      "value": 9000,
      "formatted": "2h 30m"
    }
  }
}
```

#### Use Cases

- Task and project time tracking
- Time spent on activities
- Elapsed time measurements
- Work hour logging
- Video/audio duration
- Cooking and preparation times
- Service level agreement (SLA) timers
- Manufacturing cycle times
- Meeting and event durations
- Exercise and workout tracking

#### Implementation Notes

- Storing as seconds enables easy aggregation (SUM, AVG, etc.)
- Can be combined with timestamps for time range calculations
- Use `max_duration` to enforce reasonable limits (e.g., max 24 hours)
- Consider precision needs when choosing display format
- Compact format ideal for variable-length durations
- Colon format familiar to users from time displays

#### Calculations Example

```python
# Calculating total time from multiple durations
durations = [3600, 5400, 7200]  # 1h, 1h30m, 2h
total_seconds = sum(durations)  # 16200 seconds
# Display: "4:30:00" or "4h 30m"

# Average duration
avg_seconds = total_seconds / len(durations)  # 5400 seconds
# Display: "1:30:00" or "1h 30m"
```

---

## Choice Fields

Choice fields provide categorical data selection with predefined options. PyBase supports simple boolean checkboxes, single-choice dropdowns, multi-choice tags, and workflow-oriented status fields with grouping.

### Checkbox

**Field Type:** `checkbox`

Simple boolean field for true/false values, displayed as a checkbox toggle. Values are normalized to boolean (`true` or `false`).

#### Configuration Options

Checkbox fields have no configuration options.

#### Validation Rules

- Accepts boolean values (`true`, `false`)
- Accepts integer values (`0`, `1`) - converted to boolean
- Accepts string values - converted to boolean (truthy/falsy)
- `null` values are converted to `false`
- Non-boolean values are coerced to boolean

#### Default Value

`false`

#### Storage Format

Stored as boolean in database:
- `true` → checkbox checked
- `false` → checkbox unchecked
- `null` → converted to `false`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Is Active",
  "type": "checkbox",
  "options": {}
}
```

**Record Value:**
```json
{
  "fields": {
    "Is Active": true
  }
}
```

**Input Variations (all stored as boolean):**
```json
// Boolean input
{
  "fields": {
    "Is Active": true
  }
}

// Integer input (0 = false, non-zero = true)
{
  "fields": {
    "Is Active": 1
  }
}
// Stored as: true

// String input
{
  "fields": {
    "Is Active": "yes"
  }
}
// Stored as: true

// Null input
{
  "fields": {
    "Is Active": null
  }
}
// Stored as: false
```

#### Use Cases

- Feature flags and toggles
- Active/inactive status
- Yes/no questions
- Boolean attributes (published, archived, featured)
- Consent and agreement tracking
- Completion markers
- Visibility toggles
- Enable/disable settings
- Binary conditions

---

### Single Select

**Field Type:** `single_select`

Dropdown field for selecting one option from a predefined list. Each option has a name, unique ID, and color for visual differentiation. Supports dynamic option creation.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `choices` | array | `[]` | List of choice objects: `[{id, name, color}]` |
| `allow_new` | boolean | `true` | Allow creating new options on-the-fly |

#### Choice Object Structure

Each choice in the `choices` array has:

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique identifier (UUID) |
| `name` | string | Display name for the option |
| `color` | string | Color identifier for UI rendering |

#### Supported Colors

Built-in color palette for choices:
- `blue`, `cyan`, `teal`, `green`, `yellow`
- `orange`, `red`, `pink`, `purple`, `gray`

Colors are used for visual badges/pills in the UI.

#### Validation Rules

- Must be a string value matching an option `name`
- If value not in `choices` and `allow_new` is `false`, validation fails
- If value not in `choices` and `allow_new` is `true`, value is accepted (new choice may be auto-created)
- `null` values are allowed (no selection)
- Empty string treated as `null`

#### Default Value

`null` (no selection)

#### Dynamic Choice Management

**Adding Choices:**
Use `add_choice()` helper method to add new options:
- Auto-generates UUID for choice ID
- Auto-assigns color from default palette if not specified
- Prevents duplicate choice names

**Removing Choices:**
Use `remove_choice()` helper method to remove options by name.

**Getting Choice Color:**
Use `get_choice_color()` to retrieve the color for a specific choice name.

#### JSON Examples

**Field Definition (Basic):**
```json
{
  "name": "Priority",
  "type": "single_select",
  "options": {
    "choices": [
      {"id": "pri-1", "name": "Low", "color": "green"},
      {"id": "pri-2", "name": "Medium", "color": "yellow"},
      {"id": "pri-3", "name": "High", "color": "orange"},
      {"id": "pri-4", "name": "Critical", "color": "red"}
    ],
    "allow_new": false
  }
}
```

**Field Definition (With Dynamic Options):**
```json
{
  "name": "Category",
  "type": "single_select",
  "options": {
    "choices": [
      {"id": "cat-1", "name": "Hardware", "color": "blue"},
      {"id": "cat-2", "name": "Software", "color": "purple"}
    ],
    "allow_new": true
  }
}
```

**Record Value:**
```json
{
  "fields": {
    "Priority": "High"
  }
}
```

**Record Value (No Selection):**
```json
{
  "fields": {
    "Priority": null
  }
}
```

**API Response (with color):**
```json
{
  "id": "rec_abc123",
  "fields": {
    "Priority": {
      "value": "High",
      "color": "orange"
    }
  }
}
```

#### Use Cases

- Priority levels (Low, Medium, High, Critical)
- Status categories
- Product categories and types
- Project phases
- Department selection
- Assignment categories
- Risk levels
- Severity ratings
- Customer segments
- Document types

#### Implementation Notes

- Store selected value as option `name` (not ID)
- Choice IDs are for internal reference and order tracking
- When `allow_new` is true, consider auto-creating choice in `choices` array
- Colors should be consistent across the application
- Validate choice names are unique within a field
- Consider maximum number of choices for UI performance

---

### Multi Select

**Field Type:** `multi_select`

Tag-style field for selecting multiple options from a predefined list. Extends single select with array-based value storage and multiple selection support.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `choices` | array | `[]` | List of choice objects: `[{id, name, color}]` |
| `allow_new` | boolean | `true` | Allow creating new options on-the-fly |
| `max_selections` | integer | `null` | Maximum number of options that can be selected |

#### Choice Object Structure

Same as single select:

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique identifier (UUID) |
| `name` | string | Display name for the option |
| `color` | string | Color identifier for UI rendering |

#### Supported Colors

Same color palette as single select:
- `blue`, `cyan`, `teal`, `green`, `yellow`
- `orange`, `red`, `pink`, `purple`, `gray`

#### Validation Rules

- Must be an array of string values
- Accepts single string value (auto-converted to array)
- Each value must match an option `name` in `choices` (if `allow_new` is false)
- If `max_selections` is set, array length must not exceed limit
- All values must be unique (no duplicates in selection)
- All array items must be strings
- Empty array `[]` is valid (no selections)
- `null` is converted to empty array `[]`

#### Default Value

`[]` (empty array - no selections)

#### Storage Format

Stored as JSON array of strings:
- Example: `["Hardware", "Software", "Networking"]`
- Order is preserved
- Empty selections stored as `[]`

#### Serialization Behavior

The field handler normalizes various input formats:
- **String input:** `"Hardware"` → `["Hardware"]`
- **Array input:** `["Hardware", "Software"]` → `["Hardware", "Software"]`
- **Null input:** `null` → `[]`

#### Display Formatting

The `format_display()` method creates comma-separated strings:
```python
format_display(["Hardware", "Software", "Networking"])
# Returns: "Hardware, Software, Networking"

format_display([])
# Returns: ""
```

#### JSON Examples

**Field Definition (Basic Tags):**
```json
{
  "name": "Tags",
  "type": "multi_select",
  "options": {
    "choices": [
      {"id": "tag-1", "name": "Hardware", "color": "blue"},
      {"id": "tag-2", "name": "Software", "color": "purple"},
      {"id": "tag-3", "name": "Networking", "color": "teal"},
      {"id": "tag-4", "name": "Security", "color": "red"}
    ],
    "allow_new": true
  }
}
```

**Field Definition (With Selection Limit):**
```json
{
  "name": "Skills",
  "type": "multi_select",
  "options": {
    "choices": [
      {"id": "skill-1", "name": "Python", "color": "blue"},
      {"id": "skill-2", "name": "JavaScript", "color": "yellow"},
      {"id": "skill-3", "name": "SQL", "color": "green"},
      {"id": "skill-4", "name": "React", "color": "cyan"}
    ],
    "allow_new": false,
    "max_selections": 3
  }
}
```

**Record Value (Multiple Selections):**
```json
{
  "fields": {
    "Tags": ["Hardware", "Software"]
  }
}
```

**Record Value (Single Selection):**
```json
{
  "fields": {
    "Tags": ["Hardware"]
  }
}
```

**Record Value (No Selections):**
```json
{
  "fields": {
    "Tags": []
  }
}
```

**Input Variations:**
```json
// Array input (standard)
{
  "fields": {
    "Tags": ["Hardware", "Software"]
  }
}

// Single string input (auto-converted to array)
{
  "fields": {
    "Tags": "Hardware"
  }
}
// Stored as: ["Hardware"]

// Null input (converted to empty array)
{
  "fields": {
    "Tags": null
  }
}
// Stored as: []
```

**API Response (with colors):**
```json
{
  "id": "rec_abc123",
  "fields": {
    "Tags": {
      "value": ["Hardware", "Software"],
      "choices": [
        {"name": "Hardware", "color": "blue"},
        {"name": "Software", "color": "purple"}
      ],
      "formatted": "Hardware, Software"
    }
  }
}
```

#### Use Cases

- Product tags and labels
- Feature lists
- Skills and competencies
- Technologies used in projects
- Document categories
- Customer interests
- Material properties
- Applicable standards
- Required certifications
- Keywords and search tags
- Permissions and roles
- Attributes and characteristics

#### Implementation Notes

- Inherit functionality from single select handler
- Preserve selection order for consistency
- Validate uniqueness within selections
- Use `max_selections` to prevent overwhelming UI with too many tags
- Consider search/filter functionality for large choice lists
- Display as badges or pills with color coding
- Support drag-and-drop reordering if order matters
- Auto-create new choices when `allow_new` is true

---

### Status

**Field Type:** `status`

Specialized single-select field for workflow management with status grouping. Each status belongs to a group (`todo`, `in_progress`, `complete`) enabling workflow automation and progress tracking.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `statuses` | array | `DEFAULT_STATUSES` | List of status objects: `[{id, name, color, group}]` |
| `allow_new` | boolean | `false` | Allow creating new statuses (typically disabled for workflow control) |

#### Status Object Structure

Each status has:

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique identifier (UUID) |
| `name` | string | Display name (e.g., "In Progress") |
| `color` | string | Color identifier for UI rendering |
| `group` | string | Workflow group: `"todo"`, `"in_progress"`, `"complete"` |

#### Status Groups

Three workflow groups organize statuses:

| Group | Meaning | Default Color | Example Statuses |
|-------|---------|---------------|------------------|
| `todo` | Not started | `gray` | To Do, Backlog, Planned |
| `in_progress` | Active work | `yellow` | In Progress, Working On, In Review |
| `complete` | Finished | `green` | Done, Completed, Shipped |

Groups enable workflow automation:
- Filter by completion state
- Track progress percentages
- Trigger automations on status group changes
- Kanban board column mapping

#### Default Statuses

If no statuses are configured, the field uses:

```json
[
  {"id": "todo", "name": "To Do", "color": "gray", "group": "todo"},
  {"id": "in_progress", "name": "In Progress", "color": "yellow", "group": "in_progress"},
  {"id": "done", "name": "Done", "color": "green", "group": "complete"}
]
```

#### Validation Rules

- Must be a string value matching a status `name`
- If value not in `statuses` and `allow_new` is `false`, validation fails (default behavior)
- If value not in `statuses` and `allow_new` is `true`, value is accepted
- `null` values are allowed (no status set)
- Empty string treated as `null`

#### Default Value

`null` (no status set)

#### Status Management Methods

**Adding Status:**
```python
add_status(options, name="In Review", group="in_progress", color="orange")
# Adds new status to the statuses list
```

**Getting Status Group:**
```python
get_status_group(options, "In Progress")
# Returns: "in_progress"
```

**Getting Statuses by Group:**
```python
get_statuses_by_group(options, "complete")
# Returns: [{"id": "done", "name": "Done", "color": "green", "group": "complete"}]
```

**Checking Status State:**
```python
is_complete(options, "Done")        # Returns: True
is_in_progress(options, "To Do")    # Returns: False
is_todo(options, "Backlog")         # Returns: True
```

#### JSON Examples

**Field Definition (Default Workflow):**
```json
{
  "name": "Status",
  "type": "status",
  "options": {
    "statuses": [
      {"id": "todo", "name": "To Do", "color": "gray", "group": "todo"},
      {"id": "in_progress", "name": "In Progress", "color": "yellow", "group": "in_progress"},
      {"id": "done", "name": "Done", "color": "green", "group": "complete"}
    ],
    "allow_new": false
  }
}
```

**Field Definition (Custom Workflow):**
```json
{
  "name": "Task Status",
  "type": "status",
  "options": {
    "statuses": [
      {"id": "s1", "name": "Backlog", "color": "gray", "group": "todo"},
      {"id": "s2", "name": "To Do", "color": "blue", "group": "todo"},
      {"id": "s3", "name": "In Progress", "color": "yellow", "group": "in_progress"},
      {"id": "s4", "name": "In Review", "color": "orange", "group": "in_progress"},
      {"id": "s5", "name": "Done", "color": "green", "group": "complete"},
      {"id": "s6", "name": "Archived", "color": "gray", "group": "complete"}
    ],
    "allow_new": false
  }
}
```

**Field Definition (Development Workflow):**
```json
{
  "name": "Dev Status",
  "type": "status",
  "options": {
    "statuses": [
      {"id": "dev1", "name": "Planned", "color": "gray", "group": "todo"},
      {"id": "dev2", "name": "Design", "color": "purple", "group": "in_progress"},
      {"id": "dev3", "name": "Development", "color": "blue", "group": "in_progress"},
      {"id": "dev4", "name": "Testing", "color": "orange", "group": "in_progress"},
      {"id": "dev5", "name": "Deployed", "color": "green", "group": "complete"}
    ],
    "allow_new": false
  }
}
```

**Record Value:**
```json
{
  "fields": {
    "Status": "In Progress"
  }
}
```

**Record Value (No Status):**
```json
{
  "fields": {
    "Status": null
  }
}
```

**API Response (with group and color):**
```json
{
  "id": "rec_abc123",
  "fields": {
    "Status": {
      "value": "In Progress",
      "color": "yellow",
      "group": "in_progress"
    }
  }
}
```

#### Use Cases

- Task and project status tracking
- Work item workflows
- Order and fulfillment status
- Support ticket states
- Review and approval processes
- Manufacturing stages
- Content publishing workflow
- Quality control steps
- Development lifecycle tracking
- Customer onboarding stages
- Lead qualification stages
- Kanban board columns

#### Workflow Automation Examples

**Progress Calculation:**
```python
# Calculate completion percentage
total_records = 100
complete_records = count_records_where(status_group="complete")
progress = (complete_records / total_records) * 100
```

**Status Transition Rules:**
```python
# Enforce workflow transitions
if current_status.group == "todo":
    allowed_next = get_statuses_by_group("in_progress")
elif current_status.group == "in_progress":
    allowed_next = get_statuses_by_group("complete") + get_statuses_by_group("todo")
```

**Automation Trigger:**
```python
# When status changes to "complete" group, send notification
if is_complete(options, new_status):
    send_completion_notification()
```

#### Implementation Notes

- Status groups enable powerful workflow automation
- `allow_new` defaults to `false` to maintain workflow integrity
- Status order in the array determines display order in UI
- Default color based on group if not specified:
  - `todo` → gray
  - `in_progress` → yellow
  - `complete` → green
- Consider status transition validation to enforce linear workflows
- Use groups for Kanban board column mapping
- Track status change history for audit trails
- Support bulk status updates for batch operations

#### UI Considerations

- Display as dropdown or button group
- Color-code status badges by group
- Kanban view: group cards by status group
- Progress indicators based on group distribution
- Status timeline/history view
- Quick status change shortcuts
- Drag-and-drop between status columns
- Workflow visualization showing valid transitions

---

## Relational Fields

Relational fields create connections between records across tables, enabling relational data modeling. PyBase supports three types of relational fields: **Link** (record references), **Lookup** (pulling data from linked records), and **Rollup** (aggregating data from linked records).

### Link (Linked Record)

**Field Type:** `link`

Link fields create relationships between records in different tables, enabling one-to-many and many-to-many relationships. They support bidirectional linking where changes in one table automatically update the linked table.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `linked_table_id` | string (UUID) | **required** | UUID of the table to link to |
| `inverse_field_id` | string (UUID) | `null` | UUID of the inverse link field (auto-created for bidirectional) |
| `is_symmetric` | boolean | `true` | Whether changes should update the linked table |
| `allow_multiple` | boolean | `true` | Whether to allow linking to multiple records |
| `limit` | integer | `null` | Maximum number of linked records |

#### Relationship Types

**One-to-Many:**
```json
{
  "options": {
    "linked_table_id": "table-uuid",
    "allow_multiple": false
  }
}
```
Example: Each order links to one customer (customer can have many orders)

**Many-to-Many:**
```json
{
  "options": {
    "linked_table_id": "table-uuid",
    "allow_multiple": true
  }
}
```
Example: Products can have many categories, categories can have many products

**Bidirectional (Symmetric):**
```json
{
  "options": {
    "linked_table_id": "table-uuid",
    "is_symmetric": true,
    "inverse_field_id": "inverse-field-uuid"
  }
}
```
When a link is created in Table A, the inverse link is automatically created in Table B

#### Storage Format

Stored as JSON array of UUID strings:
```json
["rec_abc123", "rec_def456", "rec_ghi789"]
```

#### Validation Rules

- `linked_table_id` must be specified in options (required)
- Each linked record must be a valid UUID
- If `allow_multiple` is `false`, only one record can be linked
- If `limit` is set, number of links must not exceed limit
- Invalid UUID formats raise `ValueError`
- Accepts UUID objects, strings, or dict format `{"id": "uuid", "name": "..."}`
- Empty arrays `[]` and `null` are allowed

#### Default Value

`null` (no linked records)

#### Display Formatting

The `format_display()` method shows link counts:
```python
format_display(["rec_abc123", "rec_def456", "rec_ghi789"])
# Returns: "3 linked records"

format_display(["rec_abc123"])
# Returns: "1 linked record"

format_display([])
# Returns: ""
```

**Note:** Actual record names/titles should be resolved by the application layer using the linked record UUIDs.

#### Inverse Field Creation

The `create_inverse_field_options()` method generates configuration for bidirectional links:
```python
# In Table A: Links to Table B
link_options_a = {
    "linked_table_id": "table-b-uuid",
    "is_symmetric": True
}

# In Table B: Auto-generated inverse link to Table A
inverse_options = create_inverse_field_options(
    source_table_id="table-a-uuid",
    source_field_id="field-a-uuid"
)
# Returns:
# {
#     "linked_table_id": "table-a-uuid",
#     "inverse_field_id": "field-a-uuid",
#     "is_symmetric": True
# }
```

#### JSON Examples

**Field Definition (Simple Link):**
```json
{
  "name": "Related Products",
  "type": "link",
  "options": {
    "linked_table_id": "tbl_products_456",
    "allow_multiple": true
  }
}
```

**Field Definition (Single Link with Limit):**
```json
{
  "name": "Assigned User",
  "type": "link",
  "options": {
    "linked_table_id": "tbl_users_123",
    "allow_multiple": false
  }
}
```

**Field Definition (Bidirectional Link):**
```json
{
  "name": "Components",
  "type": "link",
  "options": {
    "linked_table_id": "tbl_parts_789",
    "allow_multiple": true,
    "is_symmetric": true,
    "inverse_field_id": "fld_assemblies_101",
    "limit": 10
  }
}
```

**Record Value (Multiple Links):**
```json
{
  "fields": {
    "Related Products": [
      "rec_product_001",
      "rec_product_002",
      "rec_product_003"
    ]
  }
}
```

**Record Value (Single Link):**
```json
{
  "fields": {
    "Assigned User": ["rec_user_abc123"]
  }
}
```

**Record Value (No Links):**
```json
{
  "fields": {
    "Related Products": []
  }
}
```

**Input Variations:**
```json
// UUID strings (standard)
{
  "fields": {
    "Related Products": ["rec_abc123", "rec_def456"]
  }
}

// UUID objects (converted to strings)
{
  "fields": {
    "Related Products": [
      UUID("rec_abc123"),
      UUID("rec_def456")
    ]
  }
}

// Dict format with ID and metadata
{
  "fields": {
    "Related Products": [
      {"id": "rec_abc123", "name": "Product A"},
      {"id": "rec_def456", "name": "Product B"}
    ]
  }
}
// Stored as: ["rec_abc123", "rec_def456"]

// Single value (auto-converted to array)
{
  "fields": {
    "Assigned User": "rec_user_abc123"
  }
}
// Stored as: ["rec_user_abc123"]
```

**API Response (with linked record details):**
```json
{
  "id": "rec_main_001",
  "fields": {
    "Related Products": {
      "value": ["rec_product_001", "rec_product_002"],
      "linked_records": [
        {
          "id": "rec_product_001",
          "primary_field": "Ball Bearing 608-2RS"
        },
        {
          "id": "rec_product_002",
          "primary_field": "Shaft Coupling 5mm"
        }
      ],
      "formatted": "2 linked records"
    }
  }
}
```

#### Use Cases

- **Product Management:** Product → Components, Product → Categories
- **Customer Relations:** Customer → Orders, Customer → Support Tickets
- **Project Management:** Project → Tasks, Task → Assignees
- **Inventory:** Assembly → Parts, Location → Items
- **Engineering:** Drawing → Revisions, Part → Assemblies
- **Document Management:** Document → Attachments, Folder → Files
- **CRM:** Company → Contacts, Deal → Activities
- **E-commerce:** Order → Line Items, Product → Variants

#### Implementation Notes

**Bidirectional Sync:**
When `is_symmetric` is true, the system must:
1. Create/update link in source record
2. Automatically create/update inverse link in target record(s)
3. Handle cascading deletions appropriately

**Performance Considerations:**
- Index `linked_table_id` for fast lookups
- Consider pagination for records with many links
- Implement lazy loading for linked record details
- Cache linked record metadata

**Data Integrity:**
- Validate linked records exist in target table
- Handle orphaned links when records are deleted
- Implement referential integrity constraints
- Consider cascade vs. restrict delete behavior

**UI Considerations:**
- Display linked record primary field (name/title)
- Enable inline record creation
- Support search and filter in link picker
- Show link count badges
- Enable bulk linking/unlinking

---

### Lookup

**Field Type:** `lookup`

Lookup fields are computed read-only fields that pull values from linked records. They automatically retrieve data from related tables through link field relationships, creating denormalized views of relational data.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `link_field_id` | string (UUID) | **required** | UUID of the link field to look up through |
| `lookup_field_id` | string (UUID) | **required** | UUID of the field to retrieve from linked records |
| `result_type` | string | `null` | Type of the looked-up field (for display formatting) |

#### Field Characteristics

- **Computed:** Values are calculated, not stored directly
- **Read-Only:** Cannot be edited manually
- **Auto-Update:** Changes in source data automatically update lookup values
- **Multi-Value:** Returns array of values (one per linked record)

#### How Lookup Fields Work

1. **Link Field:** Specifies which link field to traverse
2. **Lookup Field:** Specifies which field to extract from linked records
3. **Computation:** For each linked record, extract the lookup field value
4. **Result:** Return array of extracted values

**Example Flow:**
```
Table A (Orders) → Link Field "Customer" → Table B (Customers)
Lookup Field: Customer.Email

Order Record:
  Customer Link: [rec_cust_001]

Customer Record (rec_cust_001):
  Email: "john@example.com"

Lookup Result:
  Customer Email: ["john@example.com"]
```

#### Storage Format

**Critical:** Lookup fields are computed and don't store data directly. When serialized for caching or API responses, they store the computed values as a list:

```json
["value1", "value2", "value3"]
```

#### Validation Rules

- Configuration validation only (values are computed)
- `link_field_id` must be specified (required)
- `lookup_field_id` must be specified (required)
- Link field must exist in the same table
- Lookup field must exist in the linked table
- Actual values are not validated (they're computed from source)

#### Default Value

`null` (no computed values)

#### Computation Method

The `compute()` method extracts values from linked records:

```python
# Linked records from the link field
linked_records = [
    {"id": "rec_001", "fields": {"Name": "Product A", "Price": 99.99}},
    {"id": "rec_002", "fields": {"Name": "Product B", "Price": 149.99}}
]

# Lookup the "Price" field
result = compute(linked_records, lookup_field_id="Price")
# Returns: [99.99, 149.99]
```

#### Display Formatting

The `format_display()` method creates comma-separated strings:

```python
format_display([99.99, 149.99])
# Returns: "99.99, 149.99"

format_display(["Product A", "Product B", "Product C"])
# Returns: "Product A, Product B, Product C"

format_display([])
# Returns: ""
```

#### JSON Examples

**Field Definition (Simple Lookup):**
```json
{
  "name": "Customer Email",
  "type": "lookup",
  "options": {
    "link_field_id": "fld_customer_link",
    "lookup_field_id": "fld_email"
  }
}
```

**Field Definition (With Result Type):**
```json
{
  "name": "Product Prices",
  "type": "lookup",
  "options": {
    "link_field_id": "fld_products_link",
    "lookup_field_id": "fld_price",
    "result_type": "currency"
  }
}
```

**Field Definition (Engineering Use Case):**
```json
{
  "name": "Component Materials",
  "type": "lookup",
  "options": {
    "link_field_id": "fld_components_link",
    "lookup_field_id": "fld_material"
  }
}
```

**Record Value (Computed):**
```json
{
  "fields": {
    "Customer Email": ["john@example.com"]
  }
}
```

**Record Value (Multiple Linked Records):**
```json
{
  "fields": {
    "Product Prices": [99.99, 149.99, 79.99]
  }
}
```

**Record Value (No Links):**
```json
{
  "fields": {
    "Customer Email": []
  }
}
```

**API Response (with computation details):**
```json
{
  "id": "rec_order_001",
  "fields": {
    "Customer Email": {
      "value": ["john@example.com"],
      "formatted": "john@example.com",
      "computed": true,
      "link_field": "Customer",
      "lookup_field": "Email"
    }
  }
}
```

**Full Example - Order → Customer Lookup:**

*Table: Orders*
```json
{
  "name": "Orders",
  "fields": [
    {
      "name": "Order ID",
      "type": "autonumber"
    },
    {
      "name": "Customer",
      "type": "link",
      "options": {
        "linked_table_id": "tbl_customers"
      }
    },
    {
      "name": "Customer Email",
      "type": "lookup",
      "options": {
        "link_field_id": "fld_customer_link",
        "lookup_field_id": "fld_email"
      }
    },
    {
      "name": "Customer Phone",
      "type": "lookup",
      "options": {
        "link_field_id": "fld_customer_link",
        "lookup_field_id": "fld_phone"
      }
    }
  ]
}
```

*Order Record:*
```json
{
  "id": "rec_order_001",
  "fields": {
    "Order ID": 1001,
    "Customer": ["rec_cust_abc"],
    "Customer Email": ["john.doe@example.com"],
    "Customer Phone": ["+1-555-123-4567"]
  }
}
```

#### Use Cases

- **Contact Information:** Order → Customer Email, Order → Customer Phone
- **Product Details:** Line Item → Product Name, Line Item → Product SKU
- **Project Data:** Task → Project Name, Task → Project Manager
- **Engineering:** Assembly → Component Specifications, Part → Material Properties
- **Inventory:** Item → Location Name, Item → Warehouse Address
- **Pricing:** Quote Line → Product Price, Quote Line → Product Category
- **References:** Document → Author Name, Support Ticket → Customer Company

#### Common Lookup Patterns

**1. Contact Details from Relations:**
```json
// Lookup customer email through order
{
  "link_field_id": "customer_link",
  "lookup_field_id": "email"
}
```

**2. Nested Product Information:**
```json
// Lookup product category through order line items
{
  "link_field_id": "line_items_link",
  "lookup_field_id": "product_category"
}
```

**3. Engineering Specifications:**
```json
// Lookup material specs through component links
{
  "link_field_id": "components_link",
  "lookup_field_id": "material_grade"
}
```

#### Implementation Notes

**Computation Timing:**
- Compute on read (lazy evaluation)
- Cache computed values with invalidation
- Recompute when source data changes
- Consider batch computation for performance

**Performance Optimization:**
- Eager load linked records to avoid N+1 queries
- Cache lookup results with proper invalidation
- Index fields commonly used in lookups
- Limit depth of nested lookups

**Data Consistency:**
- Lookup values reflect current state of linked records
- Changes in source records immediately affect lookups
- Deleting linked records removes values from lookup
- Handle null/missing fields gracefully

**UI Considerations:**
- Display as read-only field
- Show field type icon (computed/lookup indicator)
- Format based on `result_type` option
- Link to source records for drill-down
- Support filtering and sorting on lookup values

**Limitations:**
- Cannot lookup from lookup fields (no chaining)
- One-level deep only (use rollup for aggregations)
- Read-only (cannot edit source through lookup)
- Performance impact with many linked records

---

### Rollup

**Field Type:** `rollup`

Rollup fields aggregate values from linked records using various aggregation functions (sum, average, count, etc.). They are computed read-only fields that provide statistical summaries and calculations across related records.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `link_field_id` | string (UUID) | **required** | UUID of the link field to roll up through |
| `rollup_field_id` | string (UUID) | **required** | UUID of the field to aggregate from linked records |
| `aggregation` | string | **required** | Aggregation function to apply (see table below) |

#### Supported Aggregation Functions

| Function | Description | Input Types | Output Type | Example Use Case |
|----------|-------------|-------------|-------------|------------------|
| `sum` | Sum of numeric values | number, currency, percent | number | Total order value, sum of quantities |
| `avg`, `average` | Average of numeric values | number, currency, percent | number | Average rating, mean price |
| `min` | Minimum value | number, date, datetime | same as input | Earliest date, lowest price |
| `max` | Maximum value | number, date, datetime | same as input | Latest date, highest price |
| `count` | Count of linked records | any | integer | Number of orders, item count |
| `counta` | Count of non-empty values | any | integer | Count filled fields |
| `countall` | Count including empty values | any | integer | Total record count |
| `empty` | Count of empty values | any | integer | Missing data count |
| `percent_empty` | Percentage of empty values | any | percent | Data completeness metric |
| `percent_filled` | Percentage of non-empty values | any | percent | Fill rate metric |
| `array_unique` | Unique values as array | any | array | Distinct categories, unique tags |
| `array_compact` | Non-empty values as array | any | array | All filled values |
| `array_join` | Concatenated string | text, any | string | Combined labels, CSV export |
| `and` | Logical AND of boolean values | checkbox, boolean | boolean | All conditions met |
| `or` | Logical OR of boolean values | checkbox, boolean | boolean | Any condition met |
| `xor` | Logical XOR of boolean values | checkbox, boolean | boolean | Exclusive condition |
| `earliest` | Earliest date/datetime | date, datetime | date/datetime | First occurrence, start date |
| `latest` | Latest date/datetime | date, datetime | date/datetime | Most recent, end date |
| `range` | Difference between max and min | number, date | number/duration | Value spread, time span |

#### Field Characteristics

- **Computed:** Values are calculated, not stored
- **Read-Only:** Cannot be edited manually
- **Auto-Update:** Recalculates when source data changes
- **Aggregated:** Single value computed from multiple linked records

#### How Rollup Fields Work

1. **Link Field:** Specifies which link field to traverse
2. **Rollup Field:** Specifies which field to aggregate from linked records
3. **Aggregation Function:** Defines how to combine values
4. **Computation:** Apply aggregation to extracted values
5. **Result:** Return single aggregated value

**Example Flow:**
```
Table A (Projects) → Link Field "Tasks" → Table B (Tasks)
Rollup Field: Tasks.Duration
Aggregation: SUM

Project Record:
  Tasks Link: [rec_task_001, rec_task_002, rec_task_003]

Task Records:
  rec_task_001: Duration = 3600 (1 hour)
  rec_task_002: Duration = 7200 (2 hours)
  rec_task_003: Duration = 5400 (1.5 hours)

Rollup Result:
  Total Duration: 16200 seconds (4.5 hours)
```

#### Storage Format

Rollup fields are computed and don't store data directly. When serialized for caching, the format depends on the aggregation function:

- **Numeric aggregations:** `number` (e.g., `42.5`)
- **Count functions:** `integer` (e.g., `15`)
- **Array functions:** `array` (e.g., `["value1", "value2"]`)
- **Boolean functions:** `boolean` (e.g., `true`)
- **Date functions:** `ISO string` (e.g., `"2024-06-15"`)

#### Validation Rules

- Configuration validation only (values are computed)
- `link_field_id` must be specified (required)
- `rollup_field_id` must be specified (required)
- `aggregation` must be one of the supported functions (required)
- Invalid aggregation function raises `ValueError`
- Actual values are not validated (they're computed from source)

#### Default Value

`null` (no computed value)

#### Computation Method

The `compute()` method applies aggregation to extracted values:

```python
# Values from linked records
values = [100, 250, 175, 300]

# Sum aggregation
result = compute(values, "sum")
# Returns: 825

# Average aggregation
result = compute(values, "avg")
# Returns: 206.25

# Count aggregation
result = compute(values, "count")
# Returns: 4

# Array unique
values = ["Hardware", "Software", "Hardware", "Networking"]
result = compute(values, "array_unique")
# Returns: ["Hardware", "Software", "Networking"]
```

#### Display Formatting

The `format_display()` method varies by aggregation result type:

```python
# Numeric results
format_display(825.50)
# Returns: "825.50"

# Percentage results
format_display(0.75, {"aggregation": "percent_filled"})
# Returns: "75.00%"

# Array results
format_display(["Hardware", "Software"], {"aggregation": "array_unique"})
# Returns: "Hardware, Software"

# Boolean results
format_display(True, {"aggregation": "and"})
# Returns: "true"
```

#### JSON Examples

**Field Definition (Sum):**
```json
{
  "name": "Total Order Value",
  "type": "rollup",
  "options": {
    "link_field_id": "fld_line_items_link",
    "rollup_field_id": "fld_price",
    "aggregation": "sum"
  }
}
```

**Field Definition (Average):**
```json
{
  "name": "Average Rating",
  "type": "rollup",
  "options": {
    "link_field_id": "fld_reviews_link",
    "rollup_field_id": "fld_rating",
    "aggregation": "avg"
  }
}
```

**Field Definition (Count):**
```json
{
  "name": "Number of Tasks",
  "type": "rollup",
  "options": {
    "link_field_id": "fld_tasks_link",
    "rollup_field_id": "fld_task_id",
    "aggregation": "count"
  }
}
```

**Field Definition (Earliest Date):**
```json
{
  "name": "First Order Date",
  "type": "rollup",
  "options": {
    "link_field_id": "fld_orders_link",
    "rollup_field_id": "fld_order_date",
    "aggregation": "earliest"
  }
}
```

**Field Definition (Array Join):**
```json
{
  "name": "All Categories",
  "type": "rollup",
  "options": {
    "link_field_id": "fld_products_link",
    "rollup_field_id": "fld_category",
    "aggregation": "array_join"
  }
}
```

**Field Definition (Percent Filled):**
```json
{
  "name": "Data Completeness",
  "type": "rollup",
  "options": {
    "link_field_id": "fld_components_link",
    "rollup_field_id": "fld_specification",
    "aggregation": "percent_filled"
  }
}
```

**Record Value (Numeric Aggregation):**
```json
{
  "fields": {
    "Total Order Value": 1547.50
  }
}
```

**Record Value (Count):**
```json
{
  "fields": {
    "Number of Tasks": 12
  }
}
```

**Record Value (Array):**
```json
{
  "fields": {
    "All Categories": ["Hardware", "Software", "Networking"]
  }
}
```

**Record Value (No Links):**
```json
{
  "fields": {
    "Total Order Value": null
  }
}
```

**API Response (with computation details):**
```json
{
  "id": "rec_project_001",
  "fields": {
    "Total Order Value": {
      "value": 1547.50,
      "formatted": "$1,547.50",
      "computed": true,
      "aggregation": "sum",
      "link_field": "Line Items",
      "rollup_field": "Price",
      "record_count": 5
    }
  }
}
```

**Full Example - Project Task Rollups:**

*Table: Projects*
```json
{
  "name": "Projects",
  "fields": [
    {
      "name": "Project Name",
      "type": "text"
    },
    {
      "name": "Tasks",
      "type": "link",
      "options": {
        "linked_table_id": "tbl_tasks",
        "allow_multiple": true
      }
    },
    {
      "name": "Total Hours",
      "type": "rollup",
      "options": {
        "link_field_id": "fld_tasks_link",
        "rollup_field_id": "fld_duration",
        "aggregation": "sum"
      }
    },
    {
      "name": "Task Count",
      "type": "rollup",
      "options": {
        "link_field_id": "fld_tasks_link",
        "rollup_field_id": "fld_task_id",
        "aggregation": "count"
      }
    },
    {
      "name": "Completion Rate",
      "type": "rollup",
      "options": {
        "link_field_id": "fld_tasks_link",
        "rollup_field_id": "fld_completed",
        "aggregation": "percent_filled"
      }
    },
    {
      "name": "Latest Activity",
      "type": "rollup",
      "options": {
        "link_field_id": "fld_tasks_link",
        "rollup_field_id": "fld_updated_at",
        "aggregation": "latest"
      }
    }
  ]
}
```

*Project Record:*
```json
{
  "id": "rec_proj_001",
  "fields": {
    "Project Name": "Website Redesign",
    "Tasks": ["rec_task_001", "rec_task_002", "rec_task_003"],
    "Total Hours": 16200,
    "Task Count": 3,
    "Completion Rate": 0.67,
    "Latest Activity": "2024-06-15T14:30:00Z"
  }
}
```

#### Use Cases by Aggregation Type

**Numeric Aggregations (sum, avg, min, max):**
- Financial totals: Order totals, budget sums, revenue calculations
- Inventory: Total quantity, average cost, min/max stock levels
- Engineering: Sum of dimensions, average tolerances, weight totals
- Project management: Total hours, average duration, budget tracking

**Count Functions (count, counta, countall, empty):**
- Relationship counts: Number of orders, tasks, line items
- Data quality: Missing field counts, completion tracking
- Inventory: Item counts, SKU totals
- Support: Ticket counts, issue tracking

**Percentage Functions (percent_empty, percent_filled):**
- Data completeness: Field fill rates, data quality metrics
- Progress tracking: Task completion percentages
- Quality control: Defect rates, pass/fail ratios

**Array Functions (array_unique, array_compact, array_join):**
- Category aggregation: All product types, unique tags
- Engineering: Material lists, specification summaries
- Reporting: Combined values, comma-separated exports
- Analytics: Distinct value analysis

**Boolean Functions (and, or, xor):**
- Conditional logic: All tasks complete, any task blocked
- Feature flags: All features enabled, any active flag
- Quality checks: All tests passed, any failures

**Date Functions (earliest, latest, range):**
- Timeline tracking: Project start/end dates, milestones
- History: First order date, last activity
- Duration calculation: Time spans, date ranges
- Scheduling: Deadline tracking, date boundaries

#### Common Rollup Patterns

**1. Financial Summaries:**
```json
{
  "aggregation": "sum",
  "link_field_id": "line_items",
  "rollup_field_id": "price"
}
```

**2. Progress Tracking:**
```json
{
  "aggregation": "percent_filled",
  "link_field_id": "tasks",
  "rollup_field_id": "completed"
}
```

**3. Data Quality Metrics:**
```json
{
  "aggregation": "percent_empty",
  "link_field_id": "components",
  "rollup_field_id": "specification"
}
```

**4. Timeline Analysis:**
```json
{
  "aggregation": "range",
  "link_field_id": "events",
  "rollup_field_id": "event_date"
}
```

#### Implementation Notes

**Computation Performance:**
- Compute on read with caching
- Batch compute multiple rollups together
- Invalidate cache when source data changes
- Index fields commonly used in rollups
- Consider materialized views for heavy aggregations

**Data Type Handling:**
- Validate aggregation function matches field type
- Handle null/empty values gracefully
- Convert types as needed (e.g., Decimal to float)
- Parse date strings for date aggregations

**Special Aggregation Logic:**

**array_join with separator:**
```python
compute(values, "array_join", {"separator": ", "})
# Default separator: ", "
# Custom separator: " | " or " • "
```

**range calculation:**
```python
# For numbers: max - min
values = [10, 25, 15, 30]
compute(values, "range")
# Returns: 20 (30 - 10)

# For dates: days between earliest and latest
values = ["2024-01-01", "2024-01-15"]
compute(values, "range")
# Returns: 14 (days)
```

**percent_filled calculation:**
```python
values = [100, None, 250, None, 175]
non_empty = 3
total = 5
result = non_empty / total  # 0.6 (60%)
```

**UI Considerations:**
- Display as read-only with computed indicator
- Show aggregation function in field header/tooltip
- Format based on result type (currency, percent, etc.)
- Provide drill-down to source records
- Support sorting and filtering on rollup values
- Display record count for context
- Show "Recalculating..." state during updates

**Error Handling:**
- Handle empty linked record sets (return null or 0)
- Manage type mismatches gracefully
- Validate aggregation function exists
- Handle edge cases (division by zero, etc.)
- Provide meaningful error messages

**Limitations:**
- Cannot roll up from rollup fields (no chaining)
- One-level deep only
- Read-only (cannot edit source through rollup)
- Performance impact with large linked record sets
- Some aggregations require specific field types

---

## Computed Fields

Computed fields automatically calculate their values based on expressions that reference other fields in the same record. They are read-only and recalculate whenever referenced fields change.

### Formula

**Field Type:** `formula`

Formula fields evaluate expressions to compute values dynamically. They support field references, arithmetic operations, conditional logic, and a rich library of built-in functions for text manipulation, mathematical calculations, date/time operations, and more.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `formula` | string | (required) | The formula expression to evaluate |
| `result_type` | string | `"auto"` | Expected result type: `"auto"`, `"text"`, `"number"`, `"date"`, `"datetime"`, `"boolean"` |
| `precision` | integer | `2` | Decimal places for numeric results (0-10) |
| `date_format` | string | `"%Y-%m-%d"` | Python strftime format for date/datetime results |

#### Validation Rules

- Formula expression must be syntactically valid
- `result_type` must be one of: `"auto"`, `"text"`, `"number"`, `"date"`, `"datetime"`, `"boolean"`
- Formula is validated at field creation/update time
- Values are computed dynamically and cannot be manually set
- Formula fields are read-only from the API
- Invalid formulas return `null` without raising errors (safe mode)

#### Default Value

`null` (formulas are computed on-demand)

#### Storage Format

Formula results are cached in their natural type (string, float, datetime, etc.) and serialized to JSON:
- **Numbers**: Stored as `float` or `int`
- **Text**: Stored as `string`
- **Dates**: Stored as ISO 8601 strings (`"2024-03-15"`)
- **DateTimes**: Stored as ISO 8601 strings with timezone (`"2024-03-15T14:30:00Z"`)
- **Booleans**: Stored as `true` or `false`
- **Arrays**: Stored as JSON arrays

#### Field References

Reference other fields in the same record using curly braces:

```
{Field Name}         # Single-word field
{First Name}         # Multi-word field
{Unit Price}         # Field with spaces
```

#### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `+` | Addition / String concatenation | `{Quantity} + 10` |
| `-` | Subtraction | `{Total} - {Discount}` |
| `*` | Multiplication | `{Price} * {Quantity}` |
| `/` | Division | `{Total} / {Count}` |
| `^` | Exponentiation | `{Base} ^ 2` |
| `=` | Equal to | `{Status} = "Done"` |
| `!=` | Not equal to | `{Priority} != "Low"` |
| `<` | Less than | `{Score} < 50` |
| `<=` | Less than or equal | `{Age} <= 18` |
| `>` | Greater than | `{Total} > 1000` |
| `>=` | Greater than or equal | `{Rating} >= 4` |
| `&` | String concatenation | `{First Name} & " " & {Last Name}` |

#### Available Functions

**Text Functions:**
- `CONCAT(text1, text2, ...)` - Concatenate multiple text values
- `LEFT(text, count)` - Extract leftmost characters
- `RIGHT(text, count)` - Extract rightmost characters
- `MID(text, start, count)` - Extract substring from middle (1-indexed)
- `LEN(text)` - Length of text
- `TRIM(text)` - Remove leading/trailing whitespace
- `LOWER(text)` - Convert to lowercase
- `UPPER(text)` - Convert to uppercase
- `PROPER(text)` - Convert to title case
- `SUBSTITUTE(text, old, new, [count])` - Replace text occurrences
- `REPLACE(text, start, count, replacement)` - Replace characters at position
- `REPT(text, count)` - Repeat text N times
- `FIND(search_text, text, [start])` - Find substring (case-sensitive, 1-indexed)
- `SEARCH(search_text, text, [start])` - Find substring (case-insensitive, 1-indexed)
- `REGEX_MATCH(text, pattern)` - Test if text matches regex
- `REGEX_EXTRACT(text, pattern)` - Extract first regex match
- `REGEX_REPLACE(text, pattern, replacement)` - Replace using regex
- `VALUE(text)` - Convert text to number

**Numeric Functions:**
- `SUM(num1, num2, ...)` - Sum of all arguments
- `AVG(num1, num2, ...)` / `AVERAGE(...)` - Average of arguments
- `MIN(num1, num2, ...)` - Minimum value
- `MAX(num1, num2, ...)` - Maximum value
- `COUNT(val1, val2, ...)` - Count non-null values
- `COUNTA(val1, val2, ...)` - Count non-blank values
- `COUNTBLANK(val1, val2, ...)` - Count blank values
- `ROUND(number, [decimals])` - Round to N decimal places
- `ROUNDUP(number, [decimals])` - Round up
- `ROUNDDOWN(number, [decimals])` - Round down
- `CEILING(number, [significance])` - Round up to nearest multiple
- `FLOOR(number, [significance])` - Round down to nearest multiple
- `ABS(number)` - Absolute value
- `SQRT(number)` - Square root
- `POWER(base, exponent)` - Exponentiation
- `EXP(number)` - e raised to power
- `LOG(number, [base])` - Logarithm (default base 10)
- `LN(number)` - Natural logarithm (base e)
- `MOD(number, divisor)` - Remainder after division
- `INT(number)` - Round down to integer
- `EVEN(number)` - Round up to nearest even integer
- `ODD(number)` - Round up to nearest odd integer

**Logical Functions:**
- `IF(condition, value_if_true, value_if_false)` - Conditional expression
- `IFS(condition1, value1, condition2, value2, ...)` - Multiple conditions
- `SWITCH(expression, case1, value1, case2, value2, ..., [default])` - Switch/case logic
- `AND(condition1, condition2, ...)` - Logical AND
- `OR(condition1, condition2, ...)` - Logical OR
- `NOT(condition)` - Logical NOT
- `XOR(condition1, condition2, ...)` - Exclusive OR
- `BLANK()` - Return blank value (null)
- `ERROR(message)` - Return error
- `ISERROR(value)` - Check if value is error
- `ISBLANK(value)` - Check if value is blank/null
- `ISNUMBER(value)` - Check if value is numeric
- `ISTEXT(value)` - Check if value is text

**Date/Time Functions:**
- `TODAY()` - Current date (no time component)
- `NOW()` - Current date and time
- `YEAR(date)` - Extract year from date
- `MONTH(date)` - Extract month (1-12)
- `DAY(date)` - Extract day of month (1-31)
- `HOUR(datetime)` - Extract hour (0-23)
- `MINUTE(datetime)` - Extract minute (0-59)
- `SECOND(datetime)` - Extract second (0-59)
- `WEEKDAY(date, [start_day])` - Day of week (0-6, Sunday=0)
- `WEEKNUM(date, [mode])` - Week number of year
- `DATEADD(date, count, unit)` - Add time to date (units: 'years', 'months', 'days', 'hours', 'minutes', 'seconds')
- `DATEDIFF(date1, date2, unit)` - Difference between dates
- `DATETIME_FORMAT(datetime, format)` - Format date/time as string
- `DATETIME_PARSE(text, format)` - Parse date/time from string
- `WORKDAY(start_date, num_days, [holidays])` - Calculate workday (excluding weekends)
- `EOMONTH(start_date, months)` - End of month after N months

**Array Functions:**
- `ARRAYCOMPACT(array)` - Remove null/blank values from array
- `ARRAYFLATTEN(array)` - Flatten nested arrays
- `ARRAYUNIQUE(array)` - Remove duplicate values
- `ARRAYJOIN(array, [separator])` - Join array elements into text

#### JSON Examples

**Field Definition (Simple Calculation):**
```json
{
  "name": "Total Price",
  "type": "formula",
  "options": {
    "formula": "{Unit Price} * {Quantity}",
    "result_type": "number",
    "precision": 2
  }
}
```

**Field Definition (Conditional Logic):**
```json
{
  "name": "Discount Eligible",
  "type": "formula",
  "options": {
    "formula": "IF({Total} > 1000, \"Yes\", \"No\")",
    "result_type": "text"
  }
}
```

**Field Definition (Text Concatenation):**
```json
{
  "name": "Full Name",
  "type": "formula",
  "options": {
    "formula": "{First Name} & \" \" & {Last Name}",
    "result_type": "text"
  }
}
```

**Field Definition (Date Calculation):**
```json
{
  "name": "Days Until Due",
  "type": "formula",
  "options": {
    "formula": "DATEDIFF({Due Date}, TODAY(), 'days')",
    "result_type": "number",
    "precision": 0
  }
}
```

**Field Definition (Complex Multi-Function):**
```json
{
  "name": "Status Summary",
  "type": "formula",
  "options": {
    "formula": "UPPER({Status}) & \" - \" & ROUND({Completion} * 100, 0) & \"%\"",
    "result_type": "text"
  }
}
```

**Record Value (Computed Result):**
```json
{
  "fields": {
    "Unit Price": 29.99,
    "Quantity": 5,
    "Total Price": 149.95
  }
}
```

**API Response:**
```json
{
  "id": "rec_abc123",
  "fields": {
    "Unit Price": 29.99,
    "Quantity": 5,
    "Total Price": {
      "value": 149.95,
      "formula": "{Unit Price} * {Quantity}",
      "formatted": "149.95"
    }
  }
}
```

#### Use Cases

- **Calculations**: Totals, subtotals, tax calculations, discounts
- **Text Manipulation**: Full names, formatted addresses, SKU generation
- **Conditional Logic**: Status indicators, eligibility checks, categorization
- **Date Math**: Age calculations, days until deadline, project duration
- **Aggregations**: Combined with lookup fields for cross-table calculations
- **Formatting**: Display formatting, unit conversions, data transformation
- **Validation Indicators**: Flag records based on business rules
- **Computed Metadata**: Auto-generated descriptions, labels, tags

#### Implementation Notes

- Formula fields are **read-only** from the API (cannot be manually set)
- Formulas are **evaluated lazily** when records are retrieved
- Formula results are **cached** to improve performance
- Cache is **invalidated** when referenced fields change
- Circular references are **detected and prevented** during validation
- Field references use the **field name**, not the field ID
- Formulas support **nested function calls** with unlimited depth
- Division by zero returns `null` (safe mode)
- Invalid formulas during evaluation return `null` instead of errors
- Formula parsing results are **cached** globally for performance
- Reference non-existent fields return `null`

#### Formula Syntax Examples

**Arithmetic:**
```
{Unit Price} * {Quantity} * (1 + {Tax Rate})
({Price} - {Cost}) / {Cost} * 100
ROUND({Value} / 1000, 2)
```

**Text Manipulation:**
```
UPPER({First Name}) & " " & UPPER({Last Name})
LEFT({SKU}, 3) & "-" & RIGHT({SKU}, 4)
CONCAT({Street}, ", ", {City}, ", ", {State}, " ", {ZIP})
```

**Conditional Logic:**
```
IF({Stock} < {Reorder Point}, "Order Now", "Sufficient")
IF({Score} >= 90, "A", IF({Score} >= 80, "B", IF({Score} >= 70, "C", "F")))
SWITCH({Priority}, "High", "🔴", "Medium", "🟡", "Low", "🟢", "⚪")
```

**Date Calculations:**
```
DATEDIFF({Due Date}, TODAY(), 'days')
DATEADD({Start Date}, {Duration}, 'days')
IF(DATEDIFF({Due Date}, TODAY(), 'days') < 0, "Overdue", "On Track")
DATETIME_FORMAT({Created Time}, "%B %d, %Y")
```

**Aggregation with Arrays:**
```
SUM({Linked Records->Amount})
AVG({Linked Records->Rating})
ARRAYUNIQUE({Tags})
ARRAYJOIN({Categories}, " | ")
```

---

## Attachment Fields

Attachment fields store file uploads with metadata including filename, size, MIME type, and optional thumbnails. They support validation for file types and size limits.

### Attachment

**Field Type:** `attachment`

File attachment field for uploading documents, images, PDFs, CAD files, and other file types. Supports multiple files per field with configurable restrictions on file types and sizes.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allowed_types` | array | `[]` (all types allowed) | List of allowed MIME type patterns (e.g., `["image/*", "application/pdf"]`) |
| `max_size_mb` | number | `10` | Maximum file size in megabytes (per file) |
| `max_files` | integer | `null` (unlimited) | Maximum number of files allowed in the field |

#### MIME Type Patterns

| Pattern | Description | Examples |
|---------|-------------|----------|
| `*/*` | All file types | Any file |
| `image/*` | All images | PNG, JPEG, GIF, SVG, WebP |
| `video/*` | All videos | MP4, MOV, AVI, WebM |
| `audio/*` | All audio | MP3, WAV, OGG |
| `text/*` | Text files | Plain text, CSV, HTML |
| `application/pdf` | PDF documents | PDF files only |
| `application/zip` | ZIP archives | ZIP files only |
| `application/vnd.ms-excel` | Excel files | XLS, XLSX |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Excel XLSX | XLSX files only |

#### Validation Rules

- Value must be an array of attachment objects or `null`/empty array
- Each attachment must be an object with a `filename` property
- If `max_files` is set, array length must not exceed limit
- If `max_size_mb` is set, each file's `size` (in bytes) must not exceed `max_size_mb * 1024 * 1024`
- If `allowed_types` is set, each file's `mime_type` must match at least one pattern
- MIME type matching supports wildcards (e.g., `image/*` matches `image/png`, `image/jpeg`, etc.)
- Empty arrays and `null` values are allowed

#### Default Value

`[]` (empty array)

#### Storage Format

Attachments are stored as JSON arrays of attachment objects with the following structure:

```json
{
  "id": "uuid-string",
  "filename": "drawing.pdf",
  "url": "https://s3.amazonaws.com/bucket/path/to/file.pdf",
  "size": 1024000,
  "mime_type": "application/pdf",
  "thumbnails": {
    "small": {
      "url": "https://s3.amazonaws.com/bucket/path/to/thumb_small.jpg",
      "width": 100,
      "height": 100
    },
    "large": {
      "url": "https://s3.amazonaws.com/bucket/path/to/thumb_large.jpg",
      "width": 500,
      "height": 500
    }
  }
}
```

**Attachment Object Properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | string (UUID) | Yes | Unique identifier for the attachment |
| `filename` | string | Yes | Original filename with extension |
| `url` | string (URL) | Yes | Direct download URL to the file |
| `size` | integer | Yes | File size in bytes |
| `mime_type` | string | Yes | MIME type of the file |
| `thumbnails` | object | No | Thumbnail URLs for image/video files (optional) |

**Thumbnail Object (optional):**
- `small`: Object with `url`, `width`, `height` for small preview (typically 100x100)
- `large`: Object with `url`, `width`, `height` for large preview (typically 500x500)

#### Display Formatting

The `format_display()` method creates user-friendly text summaries:

```python
# Single file
format_display([{"filename": "drawing.pdf", ...}])
# Returns: "drawing.pdf"

# Multiple files
format_display([{...}, {...}, {...}])
# Returns: "3 attachments"

# Empty
format_display([])
# Returns: ""
```

#### JSON Examples

**Field Definition (Images Only, Max 5MB):**
```json
{
  "name": "Product Photos",
  "type": "attachment",
  "options": {
    "allowed_types": ["image/*"],
    "max_size_mb": 5,
    "max_files": 10
  }
}
```

**Field Definition (CAD/PDF Files):**
```json
{
  "name": "Engineering Drawings",
  "type": "attachment",
  "options": {
    "allowed_types": [
      "application/pdf",
      "application/dxf",
      "application/dwg",
      "model/step",
      "model/iges"
    ],
    "max_size_mb": 50,
    "max_files": null
  }
}
```

**Field Definition (Documents with Large Limit):**
```json
{
  "name": "Project Documents",
  "type": "attachment",
  "options": {
    "allowed_types": [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ],
    "max_size_mb": 25,
    "max_files": 20
  }
}
```

**Field Definition (Any File Type):**
```json
{
  "name": "Attachments",
  "type": "attachment",
  "options": {
    "allowed_types": [],
    "max_size_mb": 10,
    "max_files": null
  }
}
```

**Record Value (Single Attachment):**
```json
{
  "fields": {
    "Product Photos": [
      {
        "id": "att_xyz789",
        "filename": "product-front.jpg",
        "url": "https://cdn.pybase.io/files/product-front.jpg",
        "size": 245680,
        "mime_type": "image/jpeg",
        "thumbnails": {
          "small": {
            "url": "https://cdn.pybase.io/thumbs/product-front_small.jpg",
            "width": 100,
            "height": 100
          },
          "large": {
            "url": "https://cdn.pybase.io/thumbs/product-front_large.jpg",
            "width": 500,
            "height": 500
          }
        }
      }
    ]
  }
}
```

**Record Value (Multiple Attachments):**
```json
{
  "fields": {
    "Engineering Drawings": [
      {
        "id": "att_abc123",
        "filename": "assembly.pdf",
        "url": "https://cdn.pybase.io/files/assembly.pdf",
        "size": 1024000,
        "mime_type": "application/pdf",
        "thumbnails": {}
      },
      {
        "id": "att_def456",
        "filename": "part-001.dxf",
        "url": "https://cdn.pybase.io/files/part-001.dxf",
        "size": 512000,
        "mime_type": "application/dxf",
        "thumbnails": {}
      }
    ]
  }
}
```

**API Response (with formatted display):**
```json
{
  "id": "rec_abc123",
  "fields": {
    "Engineering Drawings": {
      "value": [
        {
          "id": "att_abc123",
          "filename": "assembly.pdf",
          "url": "https://cdn.pybase.io/files/assembly.pdf",
          "size": 1024000,
          "mime_type": "application/pdf",
          "thumbnails": {}
        },
        {
          "id": "att_def456",
          "filename": "part-001.dxf",
          "url": "https://cdn.pybase.io/files/part-001.dxf",
          "size": 512000,
          "mime_type": "application/dxf",
          "thumbnails": {}
        }
      ],
      "formatted": "2 attachments"
    }
  }
}
```

#### Use Cases

- **Product Images**: Product photos, screenshots, marketing materials
- **Engineering Drawings**: CAD files (DXF, DWG, STEP), technical drawings, schematics
- **Documentation**: PDF manuals, specifications, datasheets, reports
- **Media Files**: Videos, audio recordings, presentations
- **Data Files**: Excel spreadsheets, CSV data, JSON exports
- **Archive Files**: ZIP archives, backup files, compressed data
- **Source Code**: Code files, configuration files, scripts
- **Certificates**: Quality certificates, compliance documents, test reports
- **Contracts**: Legal documents, agreements, invoices
- **CAD Extraction**: Uploaded CAD/PDF files for automatic data extraction

#### Implementation Notes

- **File Upload Flow**:
  1. Client requests pre-signed upload URL from backend
  2. Client uploads file directly to cloud storage (S3, Azure Blob, etc.)
  3. Client includes returned URL and metadata in record creation/update
  4. Backend validates file metadata and creates attachment object

- **Thumbnail Generation**:
  - Thumbnails are generated asynchronously for image and video files
  - PDF first pages can also be thumbnailed for preview
  - Thumbnail generation should happen after upload confirmation

- **Storage Considerations**:
  - Files should be stored in cloud object storage (S3, GCS, Azure Blob)
  - Use pre-signed URLs with expiration for secure access
  - Implement virus scanning for uploaded files
  - Consider CDN distribution for frequently accessed files

- **File Validation**:
  - MIME type validation happens server-side (don't trust client)
  - File size limits prevent storage abuse
  - Scan uploaded files for malware/viruses
  - Validate file extensions match MIME types

- **Deletion Handling**:
  - Deleted attachments should be marked for cleanup
  - Implement background job to remove orphaned files
  - Consider retention policies for compliance

- **Performance**:
  - Thumbnail URLs are cached in attachment object
  - Lazy-load full-size images in UI
  - Use responsive image formats (WebP, AVIF) for thumbnails

---

## Engineering Fields

Engineering fields provide specialized data types for technical and manufacturing applications. These fields support industry-standard formats and validation for dimensions, geometric tolerancing, thread specifications, materials, and surface finishes.

### Dimension

**Field Type:** `dimension`

Handles engineering dimensions with values, tolerances, and units. Supports symmetric, asymmetric, and limit tolerances per engineering drawing standards.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `unit` | string | `"mm"` | Default unit (mm, in, m, cm, ft, μm, mil) |
| `precision` | integer | `3` | Decimal places for display |
| `tolerance_type` | string | `"symmetric"` | Tolerance format: `symmetric`, `asymmetric`, `limits` |

#### Validation Rules

- Value must be numeric
- Tolerances must be non-negative
- Supported units: `mm`, `cm`, `m`, `in`, `ft`, `μm`, `mil`
- Precision must be between 0 and 8 decimal places
- Accepts dict, numeric, or string formats
- String parsing supports formats like `"10.5 ±0.1 mm"`, `"10.5 +0.2/-0.1 mm"`, `"10.4 - 10.6 mm"`

#### Default Value

`null`

#### Storage Format

```json
{
  "value": 10.5,
  "tolerance_plus": 0.1,
  "tolerance_minus": 0.1,
  "unit": "mm"
}
```

#### Display Formats

- **Symmetric:** `10.5 ±0.1 mm`
- **Asymmetric:** `10.5 +0.2/-0.1 mm`
- **Limits:** `10.4 - 10.6 mm`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Shaft Diameter",
  "type": "dimension",
  "options": {
    "unit": "mm",
    "precision": 3,
    "tolerance_type": "symmetric"
  }
}
```

**Record Value (Dict Format):**
```json
{
  "fields": {
    "Shaft Diameter": {
      "value": 25.0,
      "tolerance_plus": 0.05,
      "tolerance_minus": 0.05,
      "unit": "mm"
    }
  }
}
```

**Record Value (String Format):**
```json
{
  "fields": {
    "Shaft Diameter": "25.0 ±0.05 mm"
  }
}
```

**Record Value (Asymmetric Tolerance):**
```json
{
  "fields": {
    "Hole Diameter": {
      "value": 10.0,
      "tolerance_plus": 0.2,
      "tolerance_minus": 0.1,
      "unit": "mm"
    }
  }
}
```

**Record Value (Numeric Only):**
```json
{
  "fields": {
    "Length": 100.5
  }
}
```

#### Unit Conversions

The dimension field supports automatic conversion between units using these conversion factors to mm:

| Unit | Name | To mm |
|------|------|-------|
| `mm` | Millimeter | 1.0 |
| `cm` | Centimeter | 10.0 |
| `m` | Meter | 1000.0 |
| `in` | Inch | 25.4 |
| `ft` | Foot | 304.8 |
| `μm` | Micrometer | 0.001 |
| `mil` | Thousandth inch | 0.0254 |

#### Use Cases

- Mechanical part dimensions
- CAD drawing annotations
- Tolerance specifications
- Manufacturing tolerances
- Quality control measurements
- Engineering change orders
- Bill of materials (BOM) dimensions

---

### GD&T (Geometric Dimensioning & Tolerancing)

**Field Type:** `gdt`

Handles geometric tolerancing specifications per ASME Y14.5 and ISO 1101 standards. Supports all 14 geometric characteristic symbols with datum references and material condition modifiers.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allowed_types` | array | all types | Restrict to specific GD&T types |
| `require_datums` | boolean | `true` | Require datum references for applicable types |

#### Validation Rules

- Type must be one of 14 standard GD&T characteristics
- Tolerance value must be positive
- Material condition must be `MMC`, `LMC`, or `RFS`
- Datum references required for orientation, location, and runout tolerances (unless `require_datums` is false)
- Form tolerances (straightness, flatness, circularity, cylindricity) do not require datums
- Supports diameter zone indicators and multiple datum references

#### Default Value

`null`

#### Supported GD&T Types

**Form Tolerances (no datum required):**
- `straightness` (⏤)
- `flatness` (⏥)
- `circularity` (○)
- `cylindricity` (⌭)

**Orientation Tolerances (datum required):**
- `perpendicularity` (⟂)
- `parallelism` (∥)
- `angularity` (∠)

**Location Tolerances (datum required):**
- `position` (⌖)
- `concentricity` (◎)
- `symmetry` (⌯)

**Runout Tolerances (datum required):**
- `circular_runout` (↗)
- `total_runout` (⌰)

**Profile Tolerances:**
- `profile_line` (⌒)
- `profile_surface` (⌓)

#### Material Conditions

- `MMC` (Ⓜ) - Maximum Material Condition
- `LMC` (Ⓛ) - Least Material Condition
- `RFS` - Regardless of Feature Size (default, no symbol)

#### Storage Format

```json
{
  "type": "position",
  "tolerance": 0.05,
  "diameter_zone": true,
  "material_condition": "MMC",
  "datums": ["A", "B", "C"],
  "datum_modifiers": {
    "A": "RFS",
    "B": "MMC"
  }
}
```

#### Display Format

`⌖ ⌀0.05 Ⓜ | A | B Ⓜ | C`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Position Tolerance",
  "type": "gdt",
  "options": {
    "allowed_types": ["position", "perpendicularity", "parallelism"],
    "require_datums": true
  }
}
```

**Record Value (Position with Datums):**
```json
{
  "fields": {
    "Position Tolerance": {
      "type": "position",
      "tolerance": 0.05,
      "diameter_zone": true,
      "material_condition": "MMC",
      "datums": ["A", "B", "C"]
    }
  }
}
```

**Record Value (Flatness - No Datum):**
```json
{
  "fields": {
    "Surface Flatness": {
      "type": "flatness",
      "tolerance": 0.02,
      "diameter_zone": false,
      "material_condition": "RFS",
      "datums": []
    }
  }
}
```

**Record Value (Perpendicularity with Datum Modifiers):**
```json
{
  "fields": {
    "Hole Perpendicularity": {
      "type": "perpendicularity",
      "tolerance": 0.1,
      "diameter_zone": true,
      "material_condition": "MMC",
      "datums": ["A"],
      "datum_modifiers": {
        "A": "RFS"
      }
    }
  }
}
```

**Record Value (String Format):**
```json
{
  "fields": {
    "Custom Callout": "⌖ ⌀0.05 Ⓜ | A | B | C"
  }
}
```

#### Use Cases

- Engineering drawings and blueprints
- Quality control inspection plans
- CAD model annotations
- Manufacturing specifications
- Precision part tolerancing
- GD&T training and documentation
- Inspection reports and CMM programs

---

### Thread

**Field Type:** `thread`

Handles thread specifications for fasteners and threaded features. Supports metric (ISO), unified (UNC/UNF/UNEF), and pipe thread standards with class/fit designations.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `standards` | array | all | Allowed thread standards (metric, unc, unf, unef, bsp, npt, acme, buttress) |
| `default_standard` | string | `"metric"` | Default standard to assume |

#### Validation Rules

- Standard must be one of the supported thread standards
- Size is required
- Metric threads require pitch (defaults to coarse pitch if not specified)
- Unified threads (UNC/UNF/UNEF) require TPI (threads per inch)
- Thread class/fit must be appropriate for standard (e.g., 6g/6H for metric, 2A/2B for unified)
- Supports internal/external designation
- Supports left-hand thread indicator

#### Default Value

`null`

#### Supported Thread Standards

| Standard | Full Name |
|----------|-----------|
| `metric` | ISO Metric (M) |
| `unc` | Unified Coarse (UNC) |
| `unf` | Unified Fine (UNF) |
| `unef` | Unified Extra Fine (UNEF) |
| `bsp` | British Standard Pipe (BSP) |
| `npt` | National Pipe Thread (NPT) |
| `acme` | ACME |
| `buttress` | Buttress |

#### Storage Format

```json
{
  "standard": "metric",
  "size": 8,
  "pitch": 1.25,
  "tpi": null,
  "class": "6g",
  "internal": false,
  "left_hand": false
}
```

#### Display Formats

- **Metric external:** `M8x1.25-6g`
- **Metric internal:** `M8x1.25-6H`
- **Unified external:** `1/4-20 UNC-2A`
- **Unified internal:** `1/4-20 UNC-2B`
- **Left-hand:** `M10x1.5-6g LH`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Thread Specification",
  "type": "thread",
  "options": {
    "standards": ["metric", "unc", "unf"],
    "default_standard": "metric"
  }
}
```

**Record Value (Metric External Thread):**
```json
{
  "fields": {
    "Thread Specification": {
      "standard": "metric",
      "size": 8,
      "pitch": 1.25,
      "class": "6g",
      "internal": false,
      "left_hand": false
    }
  }
}
```

**Record Value (Metric Internal Thread):**
```json
{
  "fields": {
    "Tapped Hole": {
      "standard": "metric",
      "size": 10,
      "pitch": 1.5,
      "class": "6H",
      "internal": true,
      "left_hand": false
    }
  }
}
```

**Record Value (Unified Coarse Thread):**
```json
{
  "fields": {
    "Bolt Thread": {
      "standard": "unc",
      "size": 0.25,
      "tpi": 20,
      "class": "2A",
      "internal": false,
      "left_hand": false
    }
  }
}
```

**Record Value (String Format - Metric):**
```json
{
  "fields": {
    "Thread Specification": "M8x1.25-6g"
  }
}
```

**Record Value (String Format - Unified):**
```json
{
  "fields": {
    "Thread Specification": "1/4-20 UNC-2A"
  }
}
```

**Record Value (Left-Hand Thread):**
```json
{
  "fields": {
    "Special Thread": {
      "standard": "metric",
      "size": 10,
      "pitch": 1.5,
      "class": "6g",
      "internal": false,
      "left_hand": true
    }
  }
}
```

#### Metric Coarse Pitch Reference

Common metric coarse pitches (automatically applied when pitch is not specified):

| Size (mm) | Coarse Pitch (mm) |
|-----------|-------------------|
| M1 | 0.25 |
| M1.6 | 0.35 |
| M2 | 0.4 |
| M2.5 | 0.45 |
| M3 | 0.5 |
| M4 | 0.7 |
| M5 | 0.8 |
| M6 | 1.0 |
| M8 | 1.25 |
| M10 | 1.5 |
| M12 | 1.75 |
| M16 | 2.0 |
| M20 | 2.5 |
| M24 | 3.0 |
| M30 | 3.5 |
| M36 | 4.0 |

#### Use Cases

- Fastener specifications (bolts, screws, nuts)
- Threaded hole callouts
- Bill of materials (BOM) entries
- Manufacturing drawings
- Inspection requirements
- Procurement specifications
- Assembly instructions

---

### Material

**Field Type:** `material`

Handles material specifications for engineering applications. Stores material designation, standard, family, condition, and mechanical properties.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allowed_types` | array | all | Restrict to specific material families |
| `require_standard` | boolean | `false` | Require material standard to be specified |

#### Validation Rules

- Designation is required
- Family must be from predefined list (if specified)
- Standard must be from recognized list (if specified)
- Condition must be from predefined list (if specified)
- Properties must have numeric values where expected
- Automatically attempts to guess material family from designation

#### Default Value

`null`

#### Supported Material Families

| Family | Description |
|--------|-------------|
| `carbon_steel` | Carbon Steel |
| `alloy_steel` | Alloy Steel |
| `stainless_steel` | Stainless Steel |
| `tool_steel` | Tool Steel |
| `aluminum` | Aluminum |
| `copper` | Copper |
| `brass` | Brass |
| `bronze` | Bronze |
| `titanium` | Titanium |
| `nickel` | Nickel Alloy |
| `magnesium` | Magnesium |
| `zinc` | Zinc |
| `cast_iron` | Cast Iron |
| `plastic` | Plastic/Polymer |
| `composite` | Composite |
| `ceramic` | Ceramic |
| `rubber` | Rubber/Elastomer |

#### Supported Standards

- `ASTM` - American Society for Testing and Materials
- `AISI` - American Iron and Steel Institute
- `SAE` - Society of Automotive Engineers
- `ISO` - International Organization for Standardization
- `DIN` - German Institute for Standardization
- `JIS` - Japanese Industrial Standards
- `EN` - European Standard
- `BS` - British Standard
- `GB` - Chinese National Standard
- `UNS` - Unified Numbering System

#### Heat Treatment Conditions

- `annealed`, `normalized`, `hardened`, `tempered`, `quenched`
- `cold_worked`, `hot_rolled`, `cold_rolled`
- `solution_treated`, `age_hardened`, `stress_relieved`
- `as_cast`, `as_forged`

#### Storage Format

```json
{
  "designation": "AISI 304",
  "standard": "ASTM",
  "family": "stainless_steel",
  "condition": "annealed",
  "properties": {
    "density": 8000,
    "yield_strength": 215,
    "tensile_strength": 505,
    "elongation": 40,
    "hardness": "HRB 92"
  },
  "notes": "Corrosion resistant"
}
```

#### Display Format

`AISI 304 Stainless Steel (Annealed)`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Material Specification",
  "type": "material",
  "options": {
    "allowed_types": ["carbon_steel", "stainless_steel", "aluminum"],
    "require_standard": true
  }
}
```

**Record Value (Full Specification):**
```json
{
  "fields": {
    "Material Specification": {
      "designation": "AISI 304",
      "standard": "ASTM",
      "family": "stainless_steel",
      "condition": "annealed",
      "properties": {
        "density": 8000,
        "yield_strength": 215,
        "tensile_strength": 505,
        "elongation": 40,
        "hardness": "HRB 92"
      }
    }
  }
}
```

**Record Value (Simple Designation):**
```json
{
  "fields": {
    "Material Specification": "AISI 304"
  }
}
```

**Record Value (Aluminum with Temper):**
```json
{
  "fields": {
    "Material Specification": {
      "designation": "6061-T6",
      "standard": "ASTM",
      "family": "aluminum",
      "condition": "age_hardened",
      "properties": {
        "density": 2700,
        "yield_strength": 276,
        "tensile_strength": 310
      }
    }
  }
}
```

**Record Value (Tool Steel):**
```json
{
  "fields": {
    "Material Specification": {
      "designation": "D2",
      "standard": "AISI",
      "family": "tool_steel",
      "condition": "hardened",
      "properties": {
        "hardness": "HRC 60-62"
      }
    }
  }
}
```

**Record Value (Plastic):**
```json
{
  "fields": {
    "Material Specification": {
      "designation": "ABS",
      "family": "plastic",
      "properties": {
        "density": 1050,
        "tensile_strength": 46
      },
      "notes": "Injection molding grade"
    }
  }
}
```

#### Property Fields

Common mechanical properties that can be stored:

| Property | Unit | Description |
|----------|------|-------------|
| `density` | kg/m³ | Material density |
| `yield_strength` | MPa | Yield strength |
| `tensile_strength` | MPa | Ultimate tensile strength |
| `elongation` | % | Elongation at break |
| `hardness` | various | Hardness (HRB, HRC, etc.) |
| `modulus` | GPa | Young's modulus |
| `thermal_conductivity` | W/m·K | Thermal conductivity |
| `melting_point` | °C | Melting point |

#### Use Cases

- Bill of materials (BOM)
- Material certifications
- Part specifications
- Procurement requirements
- Quality control
- Material tracking
- Engineering drawings
- Compliance documentation

---

### Surface Finish

**Field Type:** `surface_finish`

Handles surface roughness and finish specifications. Supports Ra, Rz, Rq and other roughness parameters with optional machining process and lay direction indicators.

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `default_parameter` | string | `"Ra"` | Default roughness parameter (Ra, Rz, Rq, etc.) |
| `default_unit` | string | `"μm"` | Default unit (μm, μin) |

#### Validation Rules

- Parameter must be one of the supported roughness parameters
- Value must be positive
- Unit must be `μm` (micrometers) or `μin` (microinches)
- Lay direction must be from predefined list (if specified)
- Process must be from predefined list (if specified)
- Accepts dict, numeric, or string formats

#### Default Value

`null`

#### Supported Roughness Parameters

| Parameter | Description |
|-----------|-------------|
| `Ra` | Arithmetic Average Roughness |
| `Rz` | Average Maximum Height |
| `Rq` | Root Mean Square Roughness |
| `Rt` | Total Height of Profile |
| `Rmax` | Maximum Roughness Depth |
| `Rp` | Maximum Profile Peak Height |
| `Rv` | Maximum Profile Valley Depth |
| `Rsk` | Skewness |
| `Rku` | Kurtosis |

#### Ra Grade Numbers (N-Numbers)

| Ra (μm) | N-Number |
|---------|----------|
| 50 | N12 |
| 25 | N11 |
| 12.5 | N10 |
| 6.3 | N9 |
| 3.2 | N8 |
| 1.6 | N7 |
| 0.8 | N6 |
| 0.4 | N5 |
| 0.2 | N4 |
| 0.1 | N3 |
| 0.05 | N2 |
| 0.025 | N1 |

#### Lay Symbols

| Lay Direction | Symbol |
|---------------|--------|
| `parallel` | = |
| `perpendicular` | ⟂ |
| `crossed` | X |
| `multidirectional` | M |
| `circular` | C |
| `radial` | R |
| `particulate` | P |

#### Machining Processes

- `turned`, `milled`, `ground`, `lapped`, `honed`, `polished`, `superfinished`
- `EDM`, `cast`, `forged`, `rolled`, `drawn`, `extruded`
- `sand_blasted`, `shot_peened`

#### Storage Format

```json
{
  "parameter": "Ra",
  "value": 1.6,
  "max_value": null,
  "unit": "μm",
  "process": "ground",
  "lay": "perpendicular"
}
```

#### Display Format

`Ra 1.6 μm ⟂ (Ground)`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Surface Roughness",
  "type": "surface_finish",
  "options": {
    "default_parameter": "Ra",
    "default_unit": "μm"
  }
}
```

**Record Value (Full Specification):**
```json
{
  "fields": {
    "Surface Roughness": {
      "parameter": "Ra",
      "value": 1.6,
      "unit": "μm",
      "process": "ground",
      "lay": "perpendicular"
    }
  }
}
```

**Record Value (Numeric Only):**
```json
{
  "fields": {
    "Surface Roughness": 1.6
  }
}
```

**Record Value (String Format):**
```json
{
  "fields": {
    "Surface Roughness": "Ra 1.6 μm"
  }
}
```

**Record Value (With Range):**
```json
{
  "fields": {
    "Surface Roughness": {
      "parameter": "Ra",
      "value": 0.8,
      "max_value": 1.6,
      "unit": "μm",
      "process": "milled"
    }
  }
}
```

**Record Value (Rz Parameter):**
```json
{
  "fields": {
    "Surface Roughness": {
      "parameter": "Rz",
      "value": 6.3,
      "unit": "μm",
      "lay": "circular"
    }
  }
}
```

**Record Value (Microinches):**
```json
{
  "fields": {
    "Surface Roughness": {
      "parameter": "Ra",
      "value": 63,
      "unit": "μin",
      "process": "turned"
    }
  }
}
```

**Record Value (With Lay Symbol):**
```json
{
  "fields": {
    "Surface Roughness": {
      "parameter": "Ra",
      "value": 3.2,
      "unit": "μm",
      "process": "ground",
      "lay": "parallel"
    }
  }
}
```

#### Use Cases

- Manufacturing drawings
- Quality control specifications
- Machining requirements
- Inspection plans
- Surface treatment specifications
- Engineering change orders
- CMM inspection programs
- Part finishing requirements

---

## System Fields

System fields are automatically managed by PyBase and track metadata about records. These fields are read-only and cannot be manually edited. They are automatically populated on record creation and updates.

All system fields are:
- **Read-only**: Values are set automatically by the system
- **Non-configurable**: No configuration options available
- **Auto-populated**: Values are generated on create/update operations
- **Always present**: Can be added to any table for audit tracking

---

### Created Time

**Field Type:** `created_time`

Automatically records the timestamp when a record is created. This field is read-only and set once upon record creation.

#### Configuration Options

System fields have no configuration options. The field is automatically managed by PyBase.

#### Validation Rules

- Field is read-only and cannot be manually set or updated
- Automatically populated on record creation
- Timestamp is set to current UTC time
- Cannot be modified after creation
- Persists even if record is updated

#### Default Value

Current UTC timestamp at record creation time.

#### Storage Format

Stored as ISO 8601 datetime string in UTC timezone:
```
YYYY-MM-DDTHH:MM:SS.sssZ
```

Example: `2024-01-15T14:32:18.472Z`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Created",
  "type": "created_time",
  "options": {}
}
```

**Record Value (automatically populated):**
```json
{
  "fields": {
    "Created": "2024-01-15T14:32:18.472Z"
  }
}
```

**Read-only Behavior:**
```json
// Attempting to set created_time manually is ignored
{
  "fields": {
    "Created": "2020-01-01T00:00:00.000Z"
  }
}
// Actual stored value: "2024-01-15T14:32:18.472Z" (system-generated)
```

#### Use Cases

- Audit trails and compliance tracking
- Record age calculations
- Creation date filtering and sorting
- Historical data analysis
- Compliance and regulatory reporting
- Data retention policies
- Created date display in UI
- Chronological record ordering
- Time-based analytics

---

### Last Modified Time

**Field Type:** `last_modified_time`

Automatically records the timestamp when a record is last updated. Updates automatically whenever any field in the record changes.

#### Configuration Options

System fields have no configuration options. The field is automatically managed by PyBase.

#### Validation Rules

- Field is read-only and cannot be manually set
- Automatically updated on any record change
- Timestamp is set to current UTC time on each update
- Initially set to creation time if record never modified
- Updates even if only system fields change

#### Default Value

Current UTC timestamp at record creation, updated on each modification.

#### Storage Format

Stored as ISO 8601 datetime string in UTC timezone:
```
YYYY-MM-DDTHH:MM:SS.sssZ
```

Example: `2024-01-15T16:45:32.891Z`

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Last Modified",
  "type": "last_modified_time",
  "options": {}
}
```

**Record Value (automatically updated):**
```json
{
  "fields": {
    "Last Modified": "2024-01-15T16:45:32.891Z"
  }
}
```

**Auto-update Behavior:**
```json
// Initial creation
{
  "fields": {
    "Name": "Widget A",
    "Last Modified": "2024-01-15T14:32:18.472Z"
  }
}

// After updating Name field
{
  "fields": {
    "Name": "Widget B",
    "Last Modified": "2024-01-15T16:45:32.891Z"  // Auto-updated
  }
}
```

#### Use Cases

- Track recent changes and updates
- Identify stale or outdated records
- Sort by recently modified
- Trigger alerts on recent changes
- Data freshness indicators
- Change detection and monitoring
- Update history tracking
- Cache invalidation logic
- Last updated display in UI
- Activity tracking

---

### Created By

**Field Type:** `created_by`

Automatically records the user who created the record. Stores a reference to the user account and is set once upon creation.

#### Configuration Options

System fields have no configuration options. The field is automatically managed by PyBase.

#### Validation Rules

- Field is read-only and cannot be manually set
- Automatically populated with authenticated user on creation
- References user ID from authentication context
- Cannot be modified after creation
- Persists even if user account is deleted (orphaned references)
- Returns null if created by system/automated process

#### Default Value

User ID of authenticated user creating the record, or `null` for system-created records.

#### Storage Format

Stored as user object reference with ID and display information:
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "name": "John Doe"
}
```

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Created By",
  "type": "created_by",
  "options": {}
}
```

**Record Value (automatically populated):**
```json
{
  "fields": {
    "Created By": {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "email": "john.doe@example.com",
      "name": "John Doe"
    }
  }
}
```

**System-created Record:**
```json
{
  "fields": {
    "Created By": null
  }
}
```

#### Use Cases

- User accountability and tracking
- Record ownership identification
- Creator-based filtering
- Access control and permissions
- Audit trails for compliance
- User activity reports
- Contribution tracking
- Creator attribution in UI
- Workflow assignment based on creator
- User performance metrics

---

### Last Modified By

**Field Type:** `last_modified_by`

Automatically records the user who last modified the record. Updates automatically whenever the record is changed by any user.

#### Configuration Options

System fields have no configuration options. The field is automatically managed by PyBase.

#### Validation Rules

- Field is read-only and cannot be manually set
- Automatically updated with authenticated user on each change
- References user ID from authentication context
- Initially set to creator if record never modified
- Updates even for system-triggered changes
- Returns null if modified by system/automated process

#### Default Value

User ID of authenticated user creating the record, updated to last modifier's ID on changes.

#### Storage Format

Stored as user object reference with ID and display information:
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "name": "Jane Smith"
}
```

#### JSON Examples

**Field Definition:**
```json
{
  "name": "Modified By",
  "type": "last_modified_by",
  "options": {}
}
```

**Record Value (automatically updated):**
```json
{
  "fields": {
    "Modified By": {
      "id": "9f4b2c1a-5d3e-4a2b-8c1d-6e7f8a9b0c1d",
      "email": "jane.smith@example.com",
      "name": "Jane Smith"
    }
  }
}
```

**Update Tracking:**
```json
// Created by John
{
  "fields": {
    "Name": "Widget A",
    "Created By": {
      "id": "user-123",
      "name": "John Doe"
    },
    "Modified By": {
      "id": "user-123",
      "name": "John Doe"
    }
  }
}

// Updated by Jane
{
  "fields": {
    "Name": "Widget B",
    "Created By": {
      "id": "user-123",
      "name": "John Doe"
    },
    "Modified By": {
      "id": "user-456",
      "name": "Jane Smith"
    }
  }
}
```

#### Use Cases

- Track who made recent changes
- User accountability for edits
- Modifier-based filtering and sorting
- Change attribution in audit logs
- Collaborative editing tracking
- Review and approval workflows
- Last editor display in UI
- Edit conflict detection
- User activity monitoring
- Change notification triggers

---

## API Usage Examples

This section provides practical examples for creating and managing fields via the PyBase API. All examples use curl commands with JWT authentication.

### Authentication Setup

First, obtain an access token:

```bash
# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}

# Set token as environment variable
export TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

### Creating Basic Fields

#### Text Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Product Name",
    "type": "text",
    "options": {
      "max_length": 100
    }
  }'
```

#### Long Text Field with Rich Text

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Description",
    "type": "long_text",
    "options": {
      "enable_rich_text": true,
      "max_length": 5000
    }
  }'
```

#### Number Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Quantity",
    "type": "number",
    "options": {
      "precision": 2,
      "allow_negative": false
    }
  }'
```

#### Currency Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Price",
    "type": "currency",
    "options": {
      "currency_symbol": "$",
      "precision": 2
    }
  }'
```

#### Email Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Contact Email",
    "type": "email",
    "options": {
      "allow_multiple": false
    }
  }'
```

#### Phone Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Phone Number",
    "type": "phone",
    "options": {
      "default_country_code": "US",
      "format": "national"
    }
  }'
```

#### URL Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Website",
    "type": "url",
    "options": {
      "allowed_protocols": ["http", "https"],
      "require_protocol": true
    }
  }'
```

### Creating Temporal Fields

#### Date Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Due Date",
    "type": "date",
    "options": {
      "date_format": "YYYY-MM-DD",
      "include_time": false
    }
  }'
```

#### DateTime Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Event Time",
    "type": "datetime",
    "options": {
      "time_format": "24h",
      "timezone": "America/New_York"
    }
  }'
```

#### Duration Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Time Spent",
    "type": "duration",
    "options": {
      "duration_format": "h:mm"
    }
  }'
```

### Creating Choice Fields

#### Single Select Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Priority",
    "type": "single_select",
    "options": {
      "choices": [
        {"name": "High", "color": "red"},
        {"name": "Medium", "color": "yellow"},
        {"name": "Low", "color": "green"}
      ]
    }
  }'
```

#### Multi Select Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Tags",
    "type": "multi_select",
    "options": {
      "choices": [
        {"name": "Urgent", "color": "red"},
        {"name": "Bug", "color": "orange"},
        {"name": "Feature", "color": "blue"},
        {"name": "Documentation", "color": "purple"}
      ]
    }
  }'
```

#### Status Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Status",
    "type": "status",
    "options": {
      "choices": [
        {"name": "Not Started", "color": "gray"},
        {"name": "In Progress", "color": "blue"},
        {"name": "Review", "color": "yellow"},
        {"name": "Done", "color": "green"}
      ]
    }
  }'
```

#### Checkbox Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Completed",
    "type": "checkbox",
    "options": {}
  }'
```

#### Rating Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Quality Rating",
    "type": "rating",
    "options": {
      "max": 5,
      "icon": "star"
    }
  }'
```

### Creating Relational Fields

#### Link (Linked Record) Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Related Projects",
    "type": "link",
    "options": {
      "linked_table_id": "660e8400-e29b-41d4-a716-446655440001",
      "allow_multiple": true
    }
  }'
```

#### Lookup Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Project Manager",
    "type": "lookup",
    "options": {
      "linked_field_id": "770e8400-e29b-41d4-a716-446655440002",
      "lookup_field_id": "880e8400-e29b-41d4-a716-446655440003"
    }
  }'
```

#### Rollup Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Total Budget",
    "type": "rollup",
    "options": {
      "linked_field_id": "770e8400-e29b-41d4-a716-446655440002",
      "rollup_field_id": "990e8400-e29b-41d4-a716-446655440004",
      "function": "SUM"
    }
  }'
```

### Creating Computed Fields

#### Formula Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Total Price",
    "type": "formula",
    "options": {
      "formula": "Quantity * Price"
    }
  }'
```

### Creating Attachment Fields

#### Attachment Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Documents",
    "type": "attachment",
    "options": {
      "allowed_types": ["pdf", "doc", "docx", "xls", "xlsx"],
      "max_size": 10485760
    }
  }'
```

### Creating Engineering Fields

#### Dimension Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Shaft Diameter",
    "type": "dimension",
    "options": {
      "unit": "mm",
      "tolerance_type": "bilateral",
      "precision": 3
    }
  }'
```

#### GD&T Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Geometric Tolerance",
    "type": "gdt",
    "options": {
      "symbol_types": ["flatness", "perpendicularity", "position"],
      "datums": ["A", "B", "C"]
    }
  }'
```

#### Thread Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Thread Spec",
    "type": "thread",
    "options": {
      "standard": "ISO"
    }
  }'
```

#### Material Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Material",
    "type": "material",
    "options": {
      "properties": ["density", "tensile_strength", "hardness"]
    }
  }'
```

#### Surface Finish Field

```bash
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Surface Roughness",
    "type": "surface_finish",
    "options": {
      "roughness_type": "Ra"
    }
  }'
```

### Creating System Fields

System fields are automatically managed by PyBase and cannot be created manually via the API. They are added automatically when tables are created.

### Batch Field Creation

Create multiple fields in a single request:

```bash
curl -X POST "http://localhost:8000/api/v1/fields/batch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "fields": [
      {
        "name": "Part Number",
        "type": "text",
        "options": {"max_length": 50}
      },
      {
        "name": "Description",
        "type": "long_text",
        "options": {"enable_rich_text": false}
      },
      {
        "name": "Quantity",
        "type": "number",
        "options": {"precision": 0, "allow_negative": false}
      },
      {
        "name": "Unit Price",
        "type": "currency",
        "options": {"currency_symbol": "$", "precision": 2}
      },
      {
        "name": "Status",
        "type": "single_select",
        "options": {
          "choices": [
            {"name": "In Stock", "color": "green"},
            {"name": "Low Stock", "color": "yellow"},
            {"name": "Out of Stock", "color": "red"}
          ]
        }
      }
    ]
  }'
```

### Common Field Patterns

#### Parts Inventory Table

```bash
# Create a complete parts inventory table with common fields
curl -X POST "http://localhost:8000/api/v1/tables" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "base_id": "440e8400-e29b-41d4-a716-446655440000",
    "name": "Parts Inventory",
    "fields": [
      {
        "name": "Part Number",
        "type": "text",
        "options": {"max_length": 50}
      },
      {
        "name": "Description",
        "type": "long_text",
        "options": {"enable_rich_text": false, "max_length": 1000}
      },
      {
        "name": "Dimension",
        "type": "dimension",
        "options": {"unit": "mm", "tolerance_type": "bilateral", "precision": 3}
      },
      {
        "name": "Material",
        "type": "material",
        "options": {"properties": ["density", "tensile_strength"]}
      },
      {
        "name": "Quantity",
        "type": "number",
        "options": {"precision": 0, "allow_negative": false}
      },
      {
        "name": "Unit Cost",
        "type": "currency",
        "options": {"currency_symbol": "$", "precision": 2}
      },
      {
        "name": "Status",
        "type": "status",
        "options": {
          "choices": [
            {"name": "In Stock", "color": "green"},
            {"name": "Low Stock", "color": "yellow"},
            {"name": "Out of Stock", "color": "red"},
            {"name": "Discontinued", "color": "gray"}
          ]
        }
      },
      {
        "name": "CAD Files",
        "type": "attachment",
        "options": {"allowed_types": ["dxf", "dwg", "step", "stp"], "max_size": 52428800}
      }
    ]
  }'
```

#### Project Management Table

```bash
curl -X POST "http://localhost:8000/api/v1/tables" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "base_id": "440e8400-e29b-41d4-a716-446655440000",
    "name": "Projects",
    "fields": [
      {
        "name": "Project Name",
        "type": "text",
        "options": {"max_length": 200}
      },
      {
        "name": "Description",
        "type": "long_text",
        "options": {"enable_rich_text": true, "max_length": 5000}
      },
      {
        "name": "Status",
        "type": "status",
        "options": {
          "choices": [
            {"name": "Planning", "color": "gray"},
            {"name": "In Progress", "color": "blue"},
            {"name": "On Hold", "color": "yellow"},
            {"name": "Completed", "color": "green"}
          ]
        }
      },
      {
        "name": "Priority",
        "type": "single_select",
        "options": {
          "choices": [
            {"name": "Critical", "color": "red"},
            {"name": "High", "color": "orange"},
            {"name": "Medium", "color": "yellow"},
            {"name": "Low", "color": "green"}
          ]
        }
      },
      {
        "name": "Start Date",
        "type": "date",
        "options": {"date_format": "YYYY-MM-DD", "include_time": false}
      },
      {
        "name": "Due Date",
        "type": "date",
        "options": {"date_format": "YYYY-MM-DD", "include_time": false}
      },
      {
        "name": "Budget",
        "type": "currency",
        "options": {"currency_symbol": "$", "precision": 2}
      },
      {
        "name": "Completion",
        "type": "percent",
        "options": {"precision": 0}
      },
      {
        "name": "Assigned To",
        "type": "user",
        "options": {"allow_multiple": true}
      },
      {
        "name": "Documents",
        "type": "attachment",
        "options": {"allowed_types": ["pdf", "doc", "docx"], "max_size": 10485760}
      }
    ]
  }'
```

### Updating Fields

#### Update Field Options

```bash
curl -X PATCH "http://localhost:8000/api/v1/fields/550e8400-e29b-41d4-a716-446655440005" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "options": {
      "max_length": 200
    }
  }'
```

#### Add Choice to Select Field

```bash
curl -X PATCH "http://localhost:8000/api/v1/fields/550e8400-e29b-41d4-a716-446655440005" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "options": {
      "choices": [
        {"name": "High", "color": "red"},
        {"name": "Medium", "color": "yellow"},
        {"name": "Low", "color": "green"},
        {"name": "Critical", "color": "purple"}
      ]
    }
  }'
```

### Deleting Fields

```bash
curl -X DELETE "http://localhost:8000/api/v1/fields/550e8400-e29b-41d4-a716-446655440005" \
  -H "Authorization: Bearer $TOKEN"
```

### Field Reordering

```bash
curl -X POST "http://localhost:8000/api/v1/fields/reorder" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "field_order": [
      "field-id-1",
      "field-id-2",
      "field-id-3",
      "field-id-4"
    ]
  }'
```

### Error Handling

#### Invalid Field Type

```bash
# Request
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Test Field",
    "type": "invalid_type"
  }'

# Response (400 Bad Request)
{
  "detail": "Invalid field type: invalid_type"
}
```

#### Missing Required Options

```bash
# Request
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Related Records",
    "type": "link"
  }'

# Response (400 Bad Request)
{
  "detail": "Missing required option: linked_table_id"
}
```

#### Duplicate Field Name

```bash
# Request
curl -X POST "http://localhost:8000/api/v1/fields" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Existing Field Name",
    "type": "text"
  }'

# Response (409 Conflict)
{
  "detail": "Field with name 'Existing Field Name' already exists in this table"
}
```

---

## See Also

- [API Reference](./api.md) - Complete API endpoint documentation
- [Project Overview](./project-overview-pdr.md) - Product requirements and architecture
- [README](../README.md) - Getting started guide
