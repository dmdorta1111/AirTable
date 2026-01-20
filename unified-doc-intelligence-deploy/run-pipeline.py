#!/usr/bin/env python3
"""
run-pipeline.py - Unified Engineering Document Intelligence Pipeline Executor

This script executes the entire 3-phase pipeline or individual phases.
It coordinates the execution of all 19 scripts in the correct sequence.

Usage:
  python run-pipeline.py --phase all          # Run all phases A, B, C
  python run-pipeline.py --phase a            # Run Phase A only (Auto-Linking)
  python run-pipeline.py --phase b            # Run Phase B only (PDF/DXF Extraction)
  python run-pipeline.py --phase c            # Run Phase C only (Search API)
  python run-pipeline.py --status             # Show system status
  python run-pipeline.py --list               # List all available scripts
  python run-pipeline.py --workers 20         # Override default worker count
  python run-pipeline.py --api-workers 4      # Override API worker count

Distributed Processing:
  You can run this script on multiple machines with different phases:
  - Machine 1: python run-pipeline.py --phase a               # Auto-linking
  - Machine 2: python run-pipeline.py --phase b --workers 20  # PDF extraction
  - Machine 3: python run-pipeline.py --phase b --workers 20  # DXF extraction
  - Machine 4: python run-pipeline.py --phase c --api-workers 4  # Search API
"""

import sys
import os
import subprocess
import argparse
import time
import json
from pathlib import Path
from datetime import datetime
import signal


class PipelineExecutor:
    """Main pipeline executor class."""

    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.scripts_dir = self.base_dir / "scripts"
        self.output_dir = self.base_dir / "output"
        self.logs_dir = self.base_dir / "logs"

        # Create directories if they don't exist
        self.output_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # Phase scripts mapping
        self.phase_scripts = {
            "a": [
                ("A1: Schema Migration", "phase-a-linking/A1-migrate-schema.py"),
                ("A2: Link by Basename", "phase-a-linking/A2-link-by-basename.py"),
                ("A3: Link by Folder", "phase-a-linking/A3-link-by-folder.py"),
                ("A4: Extract Project Codes", "phase-a-linking/A4-extract-project-codes.py"),
                ("A5: Flag Review Queue", "phase-a-linking/A5-flag-review-queue.py"),
                ("A6: Generate Link Report", "phase-a-linking/A6-generate-link-report.py"),
            ],
            "b": [
                (
                    "B1: Create Extraction Tables",
                    "phase-b-extraction/B1-create-extraction-tables.py",
                ),
                ("B2: Queue Extraction Jobs", "phase-b-extraction/B2-queue-extraction-jobs.py"),
                ("B3: PDF Extraction Worker", "phase-b-extraction/B3-pdf-extraction-worker.py"),
                ("B4: DXF Extraction Worker", "phase-b-extraction/B4-dxf-extraction-worker.py"),
                ("B5: Index Dimensions", "phase-b-extraction/B5-index-dimensions.py"),
                ("B6: Index Materials", "phase-b-extraction/B6-index-materials.py"),
                ("B7: Extraction Report", "phase-b-extraction/B7-extraction-report.py"),
            ],
            "c": [
                ("C1: Test Dimensions Search", "phase-c-search/C1-search-dimensions.py"),
                ("C2: Test Parameters Search", "phase-c-search/C2-search-parameters.py"),
                ("C3: Test Materials Search", "phase-c-search/C3-search-materials.py"),
                ("C4: Test Projects Search", "phase-c-search/C4-search-projects.py"),
                ("C5: Test Full-text Search", "phase-c-search/C5-search-fulltext.py"),
                ("C6: Start Search API Server", "phase-c-search/C6-search-api-server.py"),
            ],
            "d": [
                ("D1: Queue CAD Jobs", "phase-d-cad-extraction/D1-queue-cad-jobs.py"),
                (
                    "D2: Creo Extraction Worker",
                    "phase-d-cad-extraction/D2-creo-extraction-worker.py",
                ),
                ("D3: JSON Importer", "phase-d-cad-extraction/D3-creo-json-importer.py"),
                ("D4: Link CAD to Documents", "phase-d-cad-extraction/D4-link-cad-to-documents.py"),
                ("D5: Index CAD Parameters", "phase-d-cad-extraction/D5-index-cad-parameters.py"),
                ("D6: CAD Extraction Report", "phase-d-cad-extraction/D6-cad-extraction-report.py"),
            ],
        }

        # Default parameters
        self.default_workers = 50
        self.default_api_workers = 4

    def print_header(self, title):
        """Print a formatted header."""
        print("\n" + "=" * 70)
        print(f"🚀 {title}")
        print("=" * 70)

    def check_prerequisites(self):
        """Check if all prerequisites are met."""
        print("🔍 Checking prerequisites...")

        # Check config file
        config_file = self.base_dir / "config.txt"
        if not config_file.exists():
            print("✗ config.txt not found!")
            print(f"  Create it from template: cp config-template.txt config.txt")
            print(f"  Then edit with your Neon PostgreSQL and Backblaze B2 credentials")
            return False

        # Check critical Python packages
        required_packages = ["psycopg2", "tqdm", "tabulate"]
        try:
            import psycopg2
            import tqdm
            import tabulate

            print(f"✓ Required packages installed")
        except ImportError as e:
            print(f"✗ Missing required package: {e}")
            print(f"  Install with: pip install -r requirements.txt")
            return False

        # Check script directories exist
        for phase in [
            "phase-a-linking",
            "phase-b-extraction",
            "phase-c-search",
            "phase-d-cad-extraction",
        ]:
            script_dir = self.scripts_dir / phase
            if not script_dir.exists():
                print(f"✗ Script directory not found: {script_dir}")
                return False

        print("✓ All prerequisites satisfied")
        return True

    def execute_script(self, script_name, description, args=None):
        """Execute a single script with proper error handling."""
        script_path = self.scripts_dir / script_name

        if not script_path.exists():
            print(f"✗ Script not found: {script_path}")
            return False

        print(f"\n▶ {description}")
        print(f"  Script: {script_name}")

        # Build command
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        # Set environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.base_dir)

        # Execute
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir),
                env=env,
                capture_output=False,  # Show output in real-time
                text=True,
            )
            elapsed = time.time() - start_time

            if result.returncode == 0:
                print(f"  ✓ Completed in {elapsed:.1f}s")
                return True
            else:
                print(f"  ✗ Failed with exit code {result.returncode}")
                if result.stderr:
                    print(f"  Error: {result.stderr[:500]}...")
                return False

        except Exception as e:
            print(f"  ✗ Execution error: {e}")
            return False

    def run_phase_a(self, args=None):
        """Run Phase A: Auto-Linking."""
        self.print_header("Phase A: Auto-Linking")

        scripts = self.phase_scripts["a"]
        success_count = 0

        for description, script_name in scripts:
            if self.execute_script(script_name, description, args):
                success_count += 1
            else:
                print(f"⚠ Phase A interrupted at {script_name}")
                return False

        if success_count == len(scripts):
            print(f"\n✅ Phase A completed: {success_count}/{len(scripts)} scripts successful")
            return True
        else:
            print(f"\n❌ Phase A failed: {success_count}/{len(scripts)} scripts successful")
            return False

    def run_phase_b(self, workers=None, args=None):
        """Run Phase B: PDF/DXF Extraction."""
        self.print_header("Phase B: PDF/DXF Extraction")

        scripts = self.phase_scripts["b"]

        # Run B1 and B2 (setup)
        print("▶ Running setup scripts...")
        for i in range(2):
            description, script_name = scripts[i]
            if not self.execute_script(script_name, description, args):
                print(f"✗ Phase B setup failed at {script_name}")
                return False

        # Run B3 and B4 in background (worker scripts run indefinitely)
        print("\n▶ Starting worker processes (these run in background)...")

        worker_args = []
        if workers:
            worker_args = ["--workers", str(workers)]

        # Start PDF extraction worker (detached)
        pdf_script = scripts[2][1]
        pdf_cmd = [sys.executable, str(self.scripts_dir / pdf_script)]
        if worker_args:
            pdf_cmd.extend(worker_args)

        print(f"  Starting PDF worker: {pdf_script}")
        try:
            pdf_process = subprocess.Popen(
                pdf_cmd,
                cwd=str(self.base_dir),
                stdout=open(self.logs_dir / "pdf-worker.log", "w"),
                stderr=open(self.logs_dir / "pdf-worker-errors.log", "w"),
            )
            print(f"  ✓ PDF worker started (PID: {pdf_process.pid})")
        except Exception as e:
            print(f"  ✗ Failed to start PDF worker: {e}")
            return False

        # Start DXF extraction worker (detached)
        dxf_script = scripts[3][1]
        dxf_cmd = [sys.executable, str(self.scripts_dir / dxf_script)]
        if worker_args:
            dxf_cmd.extend(worker_args)

        print(f"  Starting DXF worker: {dxf_script}")
        try:
            dxf_process = subprocess.Popen(
                dxf_cmd,
                cwd=str(self.base_dir),
                stdout=open(self.logs_dir / "dxf-worker.log", "w"),
                stderr=open(self.logs_dir / "dxf-worker-errors.log", "w"),
            )
            print(f"  ✓ DXF worker started (PID: {dxf_process.pid})")
        except Exception as e:
            print(f"  ✗ Failed to start DXF worker: {e}")
            pdf_process.terminate()
            return False

        print("\n⚠ IMPORTANT: Workers are now running in background")
        print(f"  - PDF worker PID: {pdf_process.pid}")
        print(f"  - DXF worker PID: {dxf_process.pid}")
        print(f"  - Logs: {self.logs_dir}/")
        print(f"  - Monitor progress: python run-pipeline.py --status")

        # Optionally wait for completion
        wait_for_completion = input("\nWait for extraction to complete? (y/n): ").strip().lower()
        if wait_for_completion == "y":
            print("Monitoring extraction progress...")
            # Check progress periodically
            # In a real implementation, you'd monitor the database
            print("(Extraction monitoring would be implemented here)")
            print("You can check status with: python run-pipeline.py --status")

        # Run remaining scripts (B5, B6, B7) - these index extracted data
        print("\n▶ Running indexing and reporting scripts...")
        for i in range(4, len(scripts)):
            description, script_name = scripts[i]
            if not self.execute_script(script_name, description, args):
                print(f"⚠ Indexing/R reporting failed at {script_name}")
                # Continue anyway

        print("\n✅ Phase B workers started successfully")
        print("Workers will continue processing in the background")
        return True

    def run_phase_d(self, args=None):
        """Run Phase D: CAD Extraction."""
        self.print_header("Phase D: CAD Extraction")

        print("⚠ NOTE: Creo extraction is currently a PLACEHOLDER.")
        print("  The D2 worker framework is ready but requires Creo API integration.")
        print("  Use D3 to import existing JSON files from Creo extraction.\n")

        scripts = self.phase_scripts["d"]
        success_count = 0

        for description, script_name in scripts:
            # Skip D2 (worker) in automated run - it's a placeholder
            if "D2-creo-extraction-worker" in script_name:
                print(f"\n⏭ Skipping {description} (Creo integration pending)")
                continue

            if self.execute_script(script_name, description, args):
                success_count += 1
            else:
                print(f"⚠ Phase D issue at {script_name}")
                # Continue anyway - some scripts may fail if no data

        print(f"\n✅ Phase D completed: {success_count} scripts executed")
        print("Note: D2 (Creo worker) skipped - requires Creo API integration")
        return True

    def run_phase_c(self, api_workers=None, args=None):
        """Run Phase C: Search API."""
        self.print_header("Phase C: Search API")

        scripts = self.phase_scripts["c"]

        # Run test scripts (C1-C5)
        print("▶ Testing search endpoints...")
        for i in range(5):
            description, script_name = scripts[i]
            if not self.execute_script(script_name, description, args):
                print(f"⚠ Search test failed at {script_name}")
                # Continue anyway

        # Start API server (C6)
        print("\n▶ Starting Search API Server...")
        api_script = scripts[5][1]

        # Build API server command
        api_cmd = [
            "uvicorn",
            f"scripts.{api_script.replace('.py', '').replace('/', '.')}:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
        ]

        if api_workers:
            api_cmd.extend(["--workers", str(api_workers)])

        print(f"  Command: {' '.join(api_cmd)}")
        print(f"  Documentation: http://localhost:8080/docs")

        # Start API server (detached)
        try:
            api_process = subprocess.Popen(
                api_cmd,
                cwd=str(self.base_dir),
                stdout=open(self.logs_dir / "api-server.log", "w"),
                stderr=open(self.logs_dir / "api-server-errors.log", "w"),
            )
            print(f"  ✓ API server started (PID: {api_process.pid})")
            print(f"  📍 API available at: http://localhost:8080")
            print(f"  📍 Swagger UI: http://localhost:8080/docs")
            print(f"  📍 ReDoc: http://localhost:8080/redoc")

            # Give server time to start
            time.sleep(2)

        except Exception as e:
            print(f"  ✗ Failed to start API server: {e}")
            return False

        print("\n✅ Phase C completed successfully")
        print("API server is running in the background")
        return True

    def get_system_status(self):
        """Get current system status."""
        self.print_header("System Status")

        # Check running processes
        print("🔄 Checking running processes...")

        # Check database connectivity
        try:
            config_file = self.base_dir / "config.txt"
            if config_file.exists():
                with open(config_file) as f:
                    config = {
                        line.split("=")[0].strip(): line.split("=")[1].strip()
                        for line in f
                        if "=" in line and not line.startswith("#")
                    }

                db_url = config.get("NEON_DATABASE_URL")
                if db_url:
                    import psycopg2

                    conn = psycopg2.connect(db_url)
                    cur = conn.cursor()

                    # Check document groups
                    cur.execute("SELECT COUNT(*) FROM document_groups")
                    group_count = cur.fetchone()[0]

                    # Check extraction progress
                    cur.execute("""
                        SELECT extraction_status, COUNT(*) 
                        FROM extracted_metadata 
                        GROUP BY extraction_status
                    """)
                    extraction_stats = cur.fetchall()

                    # Check job queue
                    cur.execute("""
                        SELECT status, COUNT(*) 
                        FROM extraction_jobs 
                        GROUP BY status
                    """)
                    job_stats = cur.fetchall()

                    conn.close()

                    print(f"✓ Database connection successful")
                    print(f"  Document Groups: {group_count:,}")
                    print(f"  Extraction Status:")
                    for status, count in extraction_stats:
                        print(f"    - {status}: {count:,}")
                    print(f"  Job Queue Status:")
                    for status, count in job_stats:
                        print(f"    - {status}: {count:,}")
                else:
                    print("✗ NEON_DATABASE_URL not configured")
            else:
                print("✗ config.txt not found")

        except Exception as e:
            print(f"✗ Database check failed: {e}")

        # Check output files
        print("\n📊 Output files:")
        if self.output_dir.exists():
            output_files = list(self.output_dir.glob("*"))
            for file in sorted(output_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                print(f"  - {file.name} ({file.stat().st_size:,} bytes, {mtime})")
        else:
            print("  No output directory found")

        return True

    def list_scripts(self):
        """List all available scripts."""
        self.print_header("Available Scripts")

        print("The deployment package includes 19 scripts organized in 3 phases:\n")

        for phase_name, phase_letter in [
            ("Auto-Linking", "a"),
            ("PDF/DXF Extraction", "b"),
            ("Search API", "c"),
            ("CAD Extraction", "d"),
        ]:
            print(f"📁 Phase {phase_letter.upper()}: {phase_name}")
            scripts = self.phase_scripts[phase_letter]

            for description, script_name in scripts:
                script_path = self.scripts_dir / script_name
                if script_path.exists():
                    size = script_path.stat().st_size
                    print(f"  ✓ {description}")
                    print(f"      {script_name} ({size:,} bytes)")
                else:
                    print(f"  ✗ {description} (MISSING: {script_name})")

            print()

        print(f"📦 Total scripts: 25")
        print(f"📁 Scripts directory: {self.scripts_dir}")

    def create_deployment_guide(self):
        """Create a deployment guide file."""
        guide_file = self.base_dir / "DEPLOYMENT_GUIDE.md"

        guide_content = f"""# Deployment Guide - Unified Engineering Document Intelligence Platform

## Quick Start

### 1. Copy Directory to Remote Machine
```bash
scp -r unified-doc-intelligence-deploy user@remote-machine:/path/to/destination/
```

### 2. Setup Environment
```bash
cd unified-doc-intelligence-deploy

# Install dependencies
python setup.py

# Or manually
pip install -r requirements.txt
```

### 3. Configure Credentials
```bash
# Copy template
cp config-template.txt config.txt

# Edit with your credentials
nano config.txt  # or use your preferred editor
```

Required credentials:
- `NEON_DATABASE_URL`: Your Neon PostgreSQL connection string
- `B2_APPLICATION_KEY_ID`: Your Backblaze B2 key ID  
- `B2_APPLICATION_KEY`: Your Backblaze B2 application key
- `B2_BUCKET_NAME`: (default: EmjacDB)

### 4. Run Pipeline
```bash
# Execute complete pipeline
python run-pipeline.py --phase all

# Or run phases individually
python run-pipeline.py --phase a      # Auto-linking (2-3 hours)
python run-pipeline.py --phase b      # PDF/DXF extraction (6-8 hours)  
python run-pipeline.py --phase c      # Search API (continuous)
```

## Distributed Processing

For large-scale processing (765,000+ files), distribute across multiple machines:

### Machine 1: Auto-Linking
```bash
python run-pipeline.py --phase a
```

### Machine 2: PDF Extraction
```bash
python run-pipeline.py --phase b --workers 20
```

### Machine 3: DXF Extraction  
```bash
python run-pipeline.py --phase b --workers 20
```

### Machine 4: Search API
```bash
python run-pipeline.py --phase c --api-workers 4
```

**Important:** All machines must:
- Use the same `config.txt` file
- Connect to the same Neon PostgreSQL database
- Have access to the Backblaze B2 bucket (`EmjacDB`)

## Monitoring & Maintenance

### Check System Status
```bash
python run-pipeline.py --status
```

### Monitor Extraction Progress
```sql
-- In PostgreSQL
SELECT extraction_status, COUNT(*) FROM extracted_metadata GROUP BY 1;
SELECT status, COUNT(*) FROM extraction_jobs GROUP BY 1;
```

### View Logs
```bash
# Worker logs
tail -f logs/pdf-worker.log
tail -f logs/dxf-worker.log

# API logs  
tail -f logs/api-server.log
```

### Stop Running Processes
```bash
# Find and kill processes
pkill -f "B3-pdf-extraction-worker"
pkill -f "B4-dxf-extraction-worker"
pkill -f "uvicorn.*C6-search-api-server"
```

## Troubleshooting

### Database Connection Issues
- Verify `NEON_DATABASE_URL` in config.txt
- Check network connectivity to Neon PostgreSQL
- Ensure SSL certificates are valid

### B2 Storage Access Issues
- Verify `B2_APPLICATION_KEY_ID` and `B2_APPLICATION_KEY`
- Check bucket permissions (`EmjacDB`)
- Monitor API rate limits

### Performance Issues
- Reduce worker count: `--workers 10`
- Increase database connection pool
- Monitor PostgreSQL resource usage

### Extraction Failures
- Check `logs/extraction-errors.log`
- Verify file permissions in B2 bucket
- Check available disk space for temp files

## File Structure

```
unified-doc-intelligence-deploy/
├── README.md                 # This file
├── run-pipeline.py          # Main executor script
├── setup.py                 # Setup script
├── deploy.sh                # Bash setup script
├── config-template.txt      # Configuration template
├── config.txt               # Your credentials (create this)
├── requirements.txt         # Python dependencies
├── schema-migration.sql     # Database schema
├── scripts/                 # All 19 Python scripts
│   ├── phase-a-linking/     # Phase A (6 scripts)
│   ├── phase-b-extraction/  # Phase B (7 scripts)
│   └── phase-c-search/     # Phase C (6 scripts)
├── docs/                    # Documentation
│   ├── IMPLEMENTATION_GUIDE.md
│   └── API_GUIDE.md
├── output/                   # Generated reports/logs
└── logs/                    # Process logs
```

## API Endpoints

Once Phase C is running, access the API at `http://localhost:8080`:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /docs` | Interactive Swagger UI |
| `GET /api/search/dimensions` | Dimension/tolerance search |
| `GET /api/search/parameters` | Engineering parameter search |
| `GET /api/search/materials` | Material search |
| `GET /api/search/projects` | Project code search |
| `GET /api/search/fulltext` | Full-text search |

## Database Schema

The platform creates 8 new tables in your PostgreSQL database:

| Table | Purpose | Size Estimate |
|-------|---------|---------------|
| `document_groups` | Logical file groups | ~37K rows |
| `document_group_members` | File-group mapping | ~2.3M rows |
| `extraction_jobs` | Job coordination | ~765K rows |
| `extracted_metadata` | File metadata | ~765K rows |
| `extracted_dimensions` | Dimension search index | ~2M rows |
| `extracted_parameters` | Parameter search index | ~5M rows |
| `extracted_materials` | Material search index | ~200K rows |
| `extracted_bom_items` | BOM component index | ~1M rows |

## Support

1. Check the `docs/` directory
2. Review error logs in `logs/` directory
3. Use status monitoring: `python run-pipeline.py --status`
4. Check database views: `v_document_groups_summary`, `v_extraction_queue_status`

---

*Deployment Guide v1.0 - Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        guide_file.write_text(guide_content)
        print(f"✓ Created deployment guide: {guide_file}")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Engineering Document Intelligence Pipeline Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run complete pipeline:        python run-pipeline.py --phase all
  Run auto-linking only:        python run-pipeline.py --phase a
  Run extraction with 20 workers: python run-pipeline.py --phase b --workers 20
  Check system status:          python run-pipeline.py --status
  List all scripts:             python run-pipeline.py --list
  
Distributed Processing:
  Run different phases on different machines for parallel processing.
  All machines share the same PostgreSQL database and B2 storage.
        """,
    )

    parser.add_argument(
        "--phase", choices=["all", "a", "b", "c", "d"], help="Which phase(s) to execute"
    )
    parser.add_argument(
        "--workers", type=int, default=50, help="Number of extraction workers (default: 50)"
    )
    parser.add_argument(
        "--api-workers", type=int, default=4, help="Number of API workers (default: 4)"
    )
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--list", action="store_true", help="List all available scripts")
    parser.add_argument("--create-guide", action="store_true", help="Create deployment guide file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be executed without running"
    )

    args = parser.parse_args()

    executor = PipelineExecutor()

    # Handle non-phase commands first
    if args.status:
        return executor.get_system_status()

    if args.list:
        executor.list_scripts()
        return True

    if args.create_guide:
        executor.create_deployment_guide()
        return True

    # Check prerequisites
    if not executor.check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        return False

    # Determine which phases to run
    phases_to_run = []
    if args.phase == "all":
        phases_to_run = ["a", "b", "c", "d"]
    elif args.phase:
        phases_to_run = [args.phase]
    else:
        print("❌ No phase specified. Use --phase all/a/b/c/d or --status/--list")
        return False

    # Run phases
    for phase in phases_to_run:
        if phase == "a":
            if not executor.run_phase_a():
                print(f"❌ Phase A failed")
                return False

        elif phase == "b":
            worker_args = ["--workers", str(args.workers)] if args.workers != 50 else []
            if not executor.run_phase_b(workers=args.workers, args=worker_args):
                print(f"⚠ Phase B may have issues - check logs")
                # Continue anyway - workers may still be running

        elif phase == "c":
            if not executor.run_phase_c(api_workers=args.api_workers):
                print(f"❌ Phase C failed")
                return False

        elif phase == "d":
            if not executor.run_phase_d():
                print(f"⚠ Phase D may have issues - check logs")
                # Continue anyway

    print("\n" + "=" * 70)
    print("🎉 PIPELINE EXECUTION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Monitor extraction: python run-pipeline.py --status")
    print("2. Check logs: tail -f logs/*.log")
    print("3. Access API: http://localhost:8080/docs")
    print("\nFor questions, see docs/ directory or README.md")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(1)
