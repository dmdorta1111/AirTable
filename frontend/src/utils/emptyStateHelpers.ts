/**
 * Empty state helper utilities for field-type-specific placeholder messages.
 *
 * Provides contextual guidance messages for empty cells based on field type,
 * improving user experience by indicating expected data format.
 */

import type { FieldType } from "../types"

/**
 * Field type to empty state message mapping.
 * Maps each field type to a user-friendly placeholder message that
 * indicates what kind of data is expected.
 */
const EMPTY_STATE_MESSAGES: Record<FieldType, string> = {
  // Text fields
  text: "Enter text...",
  long_text: "Enter text...",

  // Number fields
  number: "Enter a number...",
  currency: "Enter amount...",
  percent: "Enter percentage...",
  rating: "Set rating...",
  autonumber: "Auto-generated",
  duration: "Enter duration...",

  // Boolean fields
  checkbox: "Unchecked",

  // Selection fields
  single_select: "Select an option...",
  multi_select: "Select options...",
  status: "Select status...",

  // Date/Time fields
  date: "Select a date...",
  datetime: "Select date & time...",

  // Link fields
  url: "Enter URL...",
  email: "Enter email address...",
  phone: "Enter phone number...",

  // Relationship fields
  linked_record: "Link records...",
  lookup: "No linked data",
  rollup: "No data to aggregate",

  // Computed fields
  formula: "Calculated automatically",

  // Attachment fields
  attachment: "No files attached",
}

/**
 * Get contextual empty state message for a field type.
 *
 * Returns an appropriate placeholder message based on the field type,
 * helping users understand what kind of data should be entered.
 *
 * @param fieldType - The type of field (e.g., 'text', 'number', 'date')
 * @returns User-friendly placeholder message for empty state
 *
 * @example
 * ```ts
 * // Get message for text field
 * const message = getEmptyStateMessage('text')
 * // Returns: "Enter text..."
 *
 * // Get message for email field
 * const emailMsg = getEmptyStateMessage('email')
 * // Returns: "Enter email address..."
 *
 * // Get message for attachment field
 * const attachMsg = getEmptyStateMessage('attachment')
 * // Returns: "No files attached"
 * ```
 */
export function getEmptyStateMessage(fieldType: FieldType): string {
  return EMPTY_STATE_MESSAGES[fieldType] || "Empty"
}

/**
 * Check if a field type is computed/read-only.
 *
 * Computed fields like formulas, lookups, rollups, and autonumbers
 * are automatically calculated and cannot be directly edited by users.
 *
 * @param fieldType - The type of field to check
 * @returns True if the field is computed/read-only
 *
 * @example
 * ```ts
 * isComputedField('formula')  // Returns: true
 * isComputedField('text')     // Returns: false
 * isComputedField('autonumber')  // Returns: true
 * ```
 */
export function isComputedField(fieldType: FieldType): boolean {
  const computedTypes: FieldType[] = ["formula", "lookup", "rollup", "autonumber"]
  return computedTypes.includes(fieldType)
}

/**
 * Get CSS classes for empty state styling based on field type.
 *
 * Returns appropriate CSS classes for styling empty states.
 * Computed fields get a different visual treatment than editable fields.
 *
 * @param fieldType - The type of field
 * @returns CSS class string for empty state styling
 *
 * @example
 * ```ts
 * // Editable field styling
 * getEmptyStateClasses('text')
 * // Returns: "text-muted-foreground text-xs"
 *
 * // Computed field styling
 * getEmptyStateClasses('formula')
 * // Returns: "text-muted-foreground text-xs italic"
 * ```
 */
export function getEmptyStateClasses(fieldType: FieldType): string {
  const baseClasses = "text-muted-foreground text-xs"
  return isComputedField(fieldType) ? `${baseClasses} italic` : baseClasses
}
