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
