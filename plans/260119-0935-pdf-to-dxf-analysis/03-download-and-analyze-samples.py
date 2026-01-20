#!/usr/bin/env python3
"""PDF Sample Download and Analysis Script"""
import json, sys, random
from datetime import datetime
from pathlib import Path

try:
    from b2sdk.v2 import B2Api, InMemoryAccountInfo, DownloadDestLocalFile
except ImportError:
    print("ERROR: b2sdk not installed. Run: pip install b2sdk")
    sys.exit(1)

try:
    import fitz
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
SAMPLES_DIR = OUTPUT_DIR / "samples"
OUTPUT_DIR.mkdir(exist_ok=True)
SAMPLES_DIR.mkdir(exist_ok=True)

def load_config():
    config_file = SCRIPT_DIR / "config.txt"
    if not config_file.exists():
        print(f"ERROR: Config file not found at {config_file}")
        sys.exit(1)
    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config

def analyze_pdf(pdf_path):
    analysis = {"path": str(pdf_path), "filename": Path(pdf_path).name, "is_valid": False, 
                "page_count": 0, "content_type": "unknown", "has_vector_graphics": False,
                "has_images": False, "has_text": False, "image_count": 0, "vector_path_count": 0,
                "text_block_count": 0, "fonts": [], "pdf_version": "", "producer": "",
                "creator": "", "estimated_dxf_quality": "unknown", "notes": []}
    try:
        doc = fitz.open(pdf_path)
        analysis["is_valid"] = True
        analysis["page_count"] = len(doc)
        analysis["pdf_version"] = doc.metadata.get("format", "")
        analysis["producer"] = doc.metadata.get("producer", "")
        analysis["creator"] = doc.metadata.get("creator", "")
        total_images, total_drawings, total_text_blocks = 0, 0, 0
        all_fonts = set()
        for page in doc:
            total_images += len(page.get_images())
            total_drawings += len(page.get_drawings())
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    total_text_blocks += 1
        analysis["image_count"] = total_images
        analysis["vector_path_count"] = total_drawings
        analysis["text_block_count"] = total_text_blocks
        analysis["has_vector_graphics"] = total_drawings > 10
        analysis["has_images"] = total_images > 0
        analysis["has_text"] = total_text_blocks > 0
        if total_drawings > 100 and total_images == 0:
            analysis["content_type"] = "vector"
            analysis["estimated_dxf_quality"] = "excellent"
        elif total_drawings > 100 and total_images > 0:
            analysis["content_type"] = "mixed"
            analysis["estimated_dxf_quality"] = "good"
        elif total_images > 0 and total_drawings < 10:
            analysis["content_type"] = "raster"
            analysis["estimated_dxf_quality"] = "poor"
        elif total_text_blocks > 0 and total_drawings < 10 and total_images == 0:
            analysis["content_type"] = "text_only"
            analysis["estimated_dxf_quality"] = "fair"
        doc.close()
    except Exception as e:
        analysis["notes"].append(f"Error: {e}")
    return analysis

def main():
    print("PDF SAMPLE DOWNLOAD AND ANALYSIS")
    config = load_config()
    existing_samples = list(SAMPLES_DIR.glob("*.pdf"))
    samples = None
    if existing_samples:
        print(f"Found {len(existing_samples)} existing samples")
        samples = [{"local_path": str(p), "original_path": "local"} for p in existing_samples]
    if samples is None:
        key_id = config.get("B2_APPLICATION_KEY_ID")
        app_key = config.get("B2_APPLICATION_KEY")
        bucket_name = config.get("B2_BUCKET_NAME")
        if not all([key_id, app_key, bucket_name]):
            print(f"ERROR: Missing B2 config. Place PDFs manually in: {SAMPLES_DIR}")
            sys.exit(1)
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, app_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        pdf_files = []
        for file_version, _ in bucket.ls(recursive=True):
            if file_version.file_name.lower().endswith(".pdf"):
                pdf_files.append({"name": file_version.file_name, "size": file_version.size, "id": file_version.id_})
            if len(pdf_files) >= 1000:
                break
        pdf_files.sort(key=lambda x: x["size"])
        to_download = pdf_files[:10] if len(pdf_files) < 10 else [pdf_files[i * len(pdf_files) // 10] for i in range(10)]
        samples = []
        for i, pdf_info in enumerate(to_download):
            local_path = SAMPLES_DIR / f"sample_{i+1:02d}.pdf"
            try:
                download_dest = DownloadDestLocalFile(str(local_path))
                bucket.download_file_by_id(pdf_info["id"], download_dest)
                samples.append({"local_path": str(local_path), "original_path": pdf_info["name"]})
            except Exception as e:
                print(f"Error: {e}")
    if not samples:
        print("ERROR: No samples")
        sys.exit(1)
    print(f"Analyzing {len(samples)} samples...")
    results = {"timestamp": datetime.now().isoformat(), "sample_count": len(samples), "analyses": [],
               "summary": {"content_types": {}, "quality_distribution": {}, "total_pages": 0}}
    for sample in samples:
        analysis = analyze_pdf(sample["local_path"])
        analysis["original_b2_path"] = sample.get("original_path", "")
        results["analyses"].append(analysis)
        ct = analysis["content_type"]
        results["summary"]["content_types"][ct] = results["summary"]["content_types"].get(ct, 0) + 1
        q = analysis["estimated_dxf_quality"]
        results["summary"]["quality_distribution"][q] = results["summary"]["quality_distribution"].get(q, 0) + 1
        results["summary"]["total_pages"] += analysis["page_count"]
        print(f"  {analysis['filename']}: {ct}, {q}")
    output_file = OUTPUT_DIR / "pdf-analysis.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
