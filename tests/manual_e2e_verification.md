# Manual End-to-End Verification for Extraction Preview UI

This document describes the manual verification steps for the extraction preview and import workflow.

## Prerequisites

1. Backend server running on `http://localhost:8000`
2. Frontend server running on `http://localhost:5173`
3. User account created and logged in
4. At least one workspace, base, and table created

## Test Scenario: Upload PDF, Preview Data, Map Fields, Import to Table

### Step 1: Navigate to Table View

1. Open browser to `http://localhost:5173`
2. Log in with valid credentials
3. Navigate to a table (e.g., `http://localhost:5173/tables/{table_id}`)
4. **Expected:** Table view loads with existing records and fields

### Step 2: Click 'Import from CAD/PDF' Button

1. Locate the "Import from CAD/PDF" button in the table header
2. Click the button
3. **Expected:** Extraction dialog opens with file upload dropzone

### Step 3: Upload a Test PDF File

1. Either:
   - Drag and drop a PDF file with table data into the dropzone, OR
   - Click the dropzone to select a file from your system
2. Select a PDF file (e.g., parts list, BOM, dimension table)
3. **Expected:**
   - File appears in the file list
   - File size is displayed
   - Remove button (X) is available

### Step 4: Verify Extraction Preview Displays Correctly

**Note:** In the current implementation, the frontend integration uses mock data for the preview. A full implementation would:

1. Upload the file to the backend extraction API
2. Create an extraction job
3. Poll for job completion
4. Fetch the extraction results
5. Display the preview with actual extracted data

**Current Expected Behavior:**
1. Mock preview data displays after file selection
2. Preview shows:
   - Table with extracted data
   - Row selection checkboxes
   - Data type badges for each column
   - Validation status indicators
   - Summary cards showing total records, selected rows, valid/invalid cells

### Step 5: Map Fields from Extracted Data to Table Columns

1. Click "Configure Field Mapping" button
2. **Expected:** Field mapping dialog opens
3. Review the suggested mappings (shown with sparkle icons)
4. Adjust mappings using the select dropdowns if needed
5. **Expected:**
   - Source fields (from extracted data) listed on the left
   - Target fields (from table) available in dropdowns
   - Mapping statistics displayed
   - Unmapped fields warning (if any)

### Step 6: Select Rows to Import

1. In the extraction preview, click checkboxes to select rows
2. Or click "Select All" to select all rows
3. **Expected:**
   - Selected rows highlighted with background color
   - "Import X Selected Rows" button updates with count

### Step 7: Click Import Button

1. Click the "Import {count} Selected Rows" button
2. **Expected:**
   - Import request sent to backend
   - Loading state shown
   - Success/error message displayed

### Step 8: Verify Records are Created in the Table

1. Close the extraction dialog
2. View the table records
3. **Expected:**
   - New records appear in the table
   - Record data matches the imported rows
   - Field values correctly mapped to table columns

### Step 9: Verify Error Handling for Failed Extractions

**Test with Invalid File:**

1. Click "Import from CAD/PDF" again
2. Upload an invalid file (e.g., text file with .pdf extension)
3. **Expected:**
   - File validation error displayed
   - Clear error message shown
   - No records created

**Test with Invalid Data:**

1. Upload a file with data that doesn't match field types
2. Attempt import with strict validation
3. **Expected:**
   - Validation errors displayed
   - Option to skip invalid rows
   - Error summary shows which rows failed

## API Endpoints Used

### 1. Create Extraction Job
```
POST /api/v1/extraction/jobs
- Uploads file
- Returns job_id
```

### 2. Check Job Status
```
GET /api/v1/extraction/jobs/{job_id}
- Returns job status, progress, result
```

### 3. Preview Import
```
POST /api/v1/extraction/jobs/{job_id}/preview?table_id={table_id}
- Returns source_fields, target_fields, suggested_mapping, sample_data
```

### 4. Import Data
```
POST /api/v1/extraction/import
- Body: { job_id, table_id, field_mapping, create_missing_fields, skip_errors }
- Returns success, records_imported, records_failed, errors
```

## Test Data

### Sample PDF Content (Parts List)

| Part Number | Description | Quantity | Unit Price |
|-------------|-------------|----------|------------|
| PN-001      | Widget A    | 10       | 5.99       |
| PN-002      | Gadget B    | 25       | 12.50      |
| PN-003      | Component C | 100      | 1.25       |

### Expected Table Fields

- Part Number (Text)
- Description (Text)
- Quantity (Number)
- Unit Price (Number)

## Success Criteria

✅ All UI components render without errors
✅ File upload works (drag-drop and click-to-upload)
✅ Extraction preview displays data correctly
✅ Field mapping interface is functional
✅ Row selection works correctly
✅ Import creates records in the database
✅ Error handling shows clear messages
✅ No console errors in browser
✅ No server errors in backend logs

## Known Limitations

1. **Mock Data:** Current frontend implementation uses mock preview data. Full backend integration pending.
2. **Job Polling:** Job status polling not fully implemented in frontend.
3. **File Storage:** Uploaded files not persisted (in-memory storage only).
4. **Real Extraction:** Actual PDF/CAD extraction requires extraction worker implementation.

## Next Steps for Production

1. Implement actual file upload to backend
2. Add job status polling with progress indicator
3. Integrate real extraction results
4. Add file storage (S3/object storage)
5. Implement extraction worker with job queue (Celery/RQ)
6. Add comprehensive error recovery
7. Implement undo/rollback for failed imports
8. Add import history and audit trail
