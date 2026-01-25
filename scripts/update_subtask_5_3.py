#!/usr/bin/env python3
"""Update subtask-5-3 status to completed."""

import json
from pathlib import Path

plan_file = Path(__file__).parent.parent / ".auto-claude" / "specs" / "018-bulk-job-database-migration" / "implementation_plan.json"

with open(plan_file, "r") as f:
    data = json.load(f)

# Update subtask-5-3
subtask = data["phases"][4]["subtasks"][2]
subtask["status"] = "completed"
subtask["notes"] = """Created comprehensive verification scripts and documentation for testing job persistence across worker restart. Two verification approaches: (1) Database-direct script (verify_worker_restart_persistence.py) for environments with database access, (2) API-based script (verify_worker_restart_persistence_api.py) that avoids circular dependency issues. Both scripts create bulk extraction jobs, monitor status transitions before/after worker restart, and verify jobs continue processing after restart. Includes detailed README with troubleshooting guide, expected output examples, and success criteria. Tests use bulk extraction with dummy files (will fail to extract, but that's OK - testing persistence not extraction). Verification points: job persists in database, worker picks up after restart, timestamps preserved, no duplicates."""

with open(plan_file, "w") as f:
    json.dump(data, f, indent=2)

print("✓ Updated subtask-5-3 status to completed")
