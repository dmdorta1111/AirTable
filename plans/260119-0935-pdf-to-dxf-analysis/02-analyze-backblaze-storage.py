#!/usr/bin/env python3
"""
Backblaze B2 Storage Analysis Script
Analyzes the bucket structure, file counts, and size distribution.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    from b2sdk.v2 import B2Api, InMemoryAccountInfo
except ImportError:
    print("ERROR: b2sdk not installed. Run: pip install b2sdk")
    sys.exit(1)

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_config():
    """Load configuration from config.txt file."""
    config_file = Path(__file__).parent / "config.txt"
    if not config_file.exists():
        print(f"ERROR: Config file not found at {config_file}")
        print("Please copy config-template.txt to config.txt and fill in your credentials")
        sys.exit(1)
    
    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    return config

def analyze_bucket(b2_api, bucket_name, max_files=10000):
    """Analyze bucket contents focusing on PDF files."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "bucket_name": bucket_name,
        "files": {
            "total_count": 0,
            "pdf_count": 0,
            "other_count": 0
        },
        "storage": {
            "total_bytes": 0,
            "pdf_bytes": 0,
            "other_bytes": 0
        },
        "pdf_analysis": {
            "size_distribution": {
                "tiny_lt_100kb": 0,
                "small_100kb_1mb": 0,
                "medium_1mb_10mb": 0,
                "large_10mb_100mb": 0,
                "huge_gt_100mb": 0
            },
            "folder_structure": defaultdict(int),
            "sample_paths": [],
            "extensions": defaultdict(int)
        },
        "errors": []
    }
    
    try:
        bucket = b2_api.get_bucket_by_name(bucket_name)
        print(f"Connected to bucket: {bucket_name}")
    except Exception as e:
        results["errors"].append(f"Bucket error: {e}")
        return results
    
    print(f"Scanning files (max {max_files})...")
    file_count = 0
    
    try:
        for file_version, folder_name in bucket.ls(recursive=True):
            file_count += 1
            file_name = file_version.file_name
            file_size = file_version.size
            
            results["files"]["total_count"] += 1
            results["storage"]["total_bytes"] += file_size
            
            # Check if PDF
            ext = Path(file_name).suffix.lower()
            results["pdf_analysis"]["extensions"][ext] += 1
            
            if ext == ".pdf":
                results["files"]["pdf_count"] += 1
                results["storage"]["pdf_bytes"] += file_size
                
                # Size distribution
                if file_size < 100 * 1024:
                    results["pdf_analysis"]["size_distribution"]["tiny_lt_100kb"] += 1
                elif file_size < 1024 * 1024:
                    results["pdf_analysis"]["size_distribution"]["small_100kb_1mb"] += 1
                elif file_size < 10 * 1024 * 1024:
                    results["pdf_analysis"]["size_distribution"]["medium_1mb_10mb"] += 1
                elif file_size < 100 * 1024 * 1024:
                    results["pdf_analysis"]["size_distribution"]["large_10mb_100mb"] += 1
                else:
                    results["pdf_analysis"]["size_distribution"]["huge_gt_100mb"] += 1
                
                # Folder structure
                folder = str(Path(file_name).parent)
                results["pdf_analysis"]["folder_structure"][folder] += 1
                
                # Sample paths (first 20)
                if len(results["pdf_analysis"]["sample_paths"]) < 20:
                    results["pdf_analysis"]["sample_paths"].append({
                        "path": file_name,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / 1024 / 1024, 2)
                    })
            else:
                results["files"]["other_count"] += 1
                results["storage"]["other_bytes"] += file_size
            
            # Progress update
            if file_count % 1000 == 0:
                print(f"  Scanned {file_count} files, {results['files']['pdf_count']} PDFs found...")
            
            # Stop at max_files
            if file_count >= max_files:
                print(f"  Reached max file limit ({max_files})")
                results["note"] = f"Scan limited to {max_files} files. Actual totals may be higher."
                break
                
    except Exception as e:
        results["errors"].append(f"Scan error: {e}")
    
    # Convert defaultdicts to regular dicts for JSON serialization
    results["pdf_analysis"]["folder_structure"] = dict(results["pdf_analysis"]["folder_structure"])
    results["pdf_analysis"]["extensions"] = dict(results["pdf_analysis"]["extensions"])
    
    # Calculate averages
    if results["files"]["pdf_count"] > 0:
        results["pdf_analysis"]["average_size_mb"] = round(
            results["storage"]["pdf_bytes"] / results["files"]["pdf_count"] / 1024 / 1024, 2
        )
    
    return results

def main():
    print("=" * 60)
    print("BACKBLAZE B2 STORAGE ANALYSIS")
    print("=" * 60)
    
    config = load_config()
    
    key_id = config.get("B2_APPLICATION_KEY_ID")
    app_key = config.get("B2_APPLICATION_KEY")
    bucket_name = config.get("B2_BUCKET_NAME")
    
    if not all([key_id, app_key, bucket_name]):
        print("ERROR: Missing B2 configuration in config.txt")
        print("Required: B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME")
        sys.exit(1)
    
    print("Authenticating with Backblaze B2...")
    
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, app_key)
        print("Authenticated successfully!")
        
        # Analyze bucket
        results = analyze_bucket(b2_api, bucket_name, max_files=50000)
        
        # Save results
        output_file = OUTPUT_DIR / "backblaze-analysis.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Results saved to: {output_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total files scanned: {results['files']['total_count']}")
        print(f"PDF files: {results['files']['pdf_count']}")
        print(f"Other files: {results['files']['other_count']}")
        print(f"\nStorage:")
        print(f"  Total: {results['storage']['total_bytes'] / 1024 / 1024 / 1024:.2f} GB")
        print(f"  PDFs: {results['storage']['pdf_bytes'] / 1024 / 1024 / 1024:.2f} GB")
        
        if results["files"]["pdf_count"] > 0:
            print(f"\nPDF Size Distribution:")
            for k, v in results["pdf_analysis"]["size_distribution"].items():
                print(f"  {k}: {v}")
            print(f"\nAverage PDF size: {results['pdf_analysis'].get('average_size_mb', 'N/A')} MB")
        
        print(f"\nFile extensions found:")
        for ext, count in sorted(results["pdf_analysis"]["extensions"].items(), key=lambda x: -x[1])[:10]:
            print(f"  {ext or '(none)'}: {count}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
