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

_Documentation for numeric field types will be added in subsequent subtasks._

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
