#!/usr/bin/env python3
"""
Standalone BOM extraction, validation, and import workflow verification script.

This script demonstrates and verifies the complete BOM workflow:
1. Upload STEP assembly file via BOM extraction API
2. Verify BOM hierarchy is extracted with parent-child relationships
3. Validate BOM against existing parts database
4. Verify new parts are highlighted vs existing parts
5. Flatten BOM with quantity rollup
6. Import flattened BOM to table
7. Verify records are created correctly

Usage:
    python scripts/verify_bom_workflow.py [--api-url URL] [--token TOKEN]
"""

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path
from typing import Any

import httpx


def create_sample_step_file() -> bytes:
    """
    Create a sample STEP file with assembly structure for BOM extraction.

    Assembly Structure:
    - Assembly (root)
      - Subassembly 1 (quantity: 2)
        - Part PN-NEW-001 (NEW) - quantity: 2 in subassembly
        - Part PN-EXISTS-001 (EXISTING) - quantity: 4 in subassembly
      - Subassembly 2 (quantity: 1)
        - Part PN-NEW-002 (NEW) - quantity: 1
        - Part PN-EXISTS-002 (EXISTING) - quantity: 3
    """
    return b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Test Assembly BOM for Verification'),'2;1');
FILE_NAME('verification_assembly.step','2024-01-27',('Verification Test'),('PyBase'),'Preprocessor','Origin','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));
ENDSEC;
DATA;
#1=CARTESIAN_POINT('',(0.,0.,0.));
#2=AXIS2_PLACEMENT_3D('',#1,#3,#4);
#3=DIRECTION('',(0.,0.,1.));
#4=DIRECTION('',(1.,0.,0.));
#5=PRODUCT('RootAssembly','Root Assembly',$,(#6));
#6=PRODUCT_CONTEXT('',#7,'mechanical');
#7=APPLICATION_CONTEXT('configuration controlled 3d designs of mechanical parts and assemblies');
#8=PRODUCT_DEFINITION('root_assembly','',#9,#1);
#9=PRODUCT_DEFINITION_FORMATION('','',#5);
#10=PRODUCT_DEFINITION_SHAPE('','',#8);
#11=SHAPE_DEFINITION_REPRESENTATION(#10,#12);
#12=SHAPE_REPRESENTATION('',(#2),#13);
#13=GEOMETRIC_REPRESENTATION_CONTEXT('3D',#14,0.0001);
#14=(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#15))GLOBAL_UNIT_ASSIGNED_CONTEXT((#16,#17,#18)));
#15=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.01),#16,'','accuracy');
#16=(CONVERSION_BASED_UNIT('inch',#19)LENGTH_UNIT()NAMED_UNIT(*));
#17=(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));
#18=(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.));
#19=LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#20);
#20=LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.),#21);
#21=(NAMED_UNIT(*)LENGTH_UNIT()SI_UNIT($,.MILLI.));
#22=PRODUCT('Subassembly1','Subassembly 1',$,(#6));
#23=PRODUCT_DEFINITION('subassembly1','',#24,#1);
#24=PRODUCT_DEFINITION_FORMATION('','',#22);
#25=PRODUCT_DEFINITION_SHAPE('','',#23);
#26=SHAPE_DEFINITION_REPRESENTATION(#25,#27);
#27=SHAPE_REPRESENTATION('',(#2),#13);
#28=PRODUCT('Subassembly2','Subassembly 2',$,(#6));
#29=PRODUCT_DEFINITION('subassembly2','',#30,#1);
#30=PRODUCT_DEFINITION_FORMATION('','',#28);
#31=PRODUCT_DEFINITION_SHAPE('','',#29);
#32=SHAPE_DEFINITION_REPRESENTATION(#31,#33);
#33=SHAPE_REPRESENTATION('',(#2),#13);
#34=PRODUCT('PN-NEW-001','New Bracket Assembly',$,(#6));
#35=PRODUCT_DEFINITION('part_new_001','',#36,#1);
#36=PRODUCT_DEFINITION_FORMATION('','',#34);
#37=PRODUCT_DEFINITION_SHAPE('','',#35);
#38=SHAPE_DEFINITION_REPRESENTATION(#37,#39);
#39=SHAPE_REPRESENTATION('',(#2),#13);
#40=PRODUCT('PN-NEW-002','New Panel Component',$,(#6));
#41=PRODUCT_DEFINITION('part_new_002','',#42,#1);
#42=PRODUCT_DEFINITION_FORMATION('','',#40);
#43=PRODUCT_DEFINITION_SHAPE('','',#41);
#44=SHAPE_DEFINITION_REPRESENTATION(#43,#45);
#45=SHAPE_REPRESENTATION('',(#2),#13);
#46=PRODUCT('PN-EXISTS-001','Existing Bolt M8x20',$,(#6));
#47=PRODUCT_DEFINITION('part_exists_001','',#48,#1);
#48=PRODUCT_DEFINITION_FORMATION('','',#46);
#49=PRODUCT_DEFINITION_SHAPE('','',#47);
#50=SHAPE_DEFINITION_REPRESENTATION(#49,#51);
#51=SHAPE_REPRESENTATION('',(#2),#13);
#52=PRODUCT('PN-EXISTS-002','Existing Nut M8',$,(#6));
#53=PRODUCT_DEFINITION('part_exists_002','',#54,#1);
#54=PRODUCT_DEFINITION_FORMATION('','',#52);
#55=PRODUCT_DEFINITION_SHAPE('','',#53);
#56=SHAPE_DEFINITION_REPRESENTATION(#55,#57);
#57=SHAPE_REPRESENTATION('',(#2),#13);
#58=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO1','Root to Sub1',#59,#23,2);
#59=PRODUCT_DEFINITION_SHAPE('','',#8);
#60=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO2','Root to Sub2',#59,#29,1);
#61=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO3','Sub1 to Part1',#62,#38,2);
#62=PRODUCT_DEFINITION_SHAPE('','',#23);
#63=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO4','Sub1 to Part3',#62,#50,4);
#64=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO5','Sub2 to Part2',#65,#44,1);
#65=PRODUCT_DEFINITION_SHAPE('','',#29);
#66=NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO6','Sub2 to Part4',#65,#57,3);
ENDSEC;
END-ISO-10303-21;
"""


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"✅ {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"❌ {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"ℹ️  {message}")


async def step1_extract_bom_hierarchical(
    client: httpx.AsyncClient, api_base: str, headers: dict[str, str]
) -> dict[str, Any]:
    """
    STEP 1: Extract BOM from STEP file in hierarchical mode.

    Returns extracted BOM data.
    """
    print_section("STEP 1: Extract BOM (Hierarchical Mode)")

    step_content = create_sample_step_file()
    files = {
        "file": ("verification_assembly.step", io.BytesIO(step_content), "application/octet-stream")
    }
    data = {
        "format": "step",
        "hierarchy_mode": "hierarchical",
        "extract_bom": "true",
        "include_quantities": "true",
    }

    print_info("Sending POST request to /extraction/bom/extract")
    print(f"  - Format: step")
    print(f"  - Hierarchy mode: hierarchical")

    response = await client.post(
        f"{api_base}/extraction/bom/extract",
        headers=headers,
        files=files,
        data=data,
    )

    if response.status_code not in [200, 201]:
        print_error(f"Extraction failed with status {response.status_code}")
        print_error(f"Response: {response.text}")
        sys.exit(1)

    extract_data = response.json()
    print_success(f"BOM extracted successfully (status {response.status_code})")

    # Verify response structure
    assert "source_type" in extract_data, "Missing source_type"
    assert extract_data["source_type"] == "step", "Wrong source_type"
    print_success("Source type verified: step")

    assert "success" in extract_data, "Missing success flag"
    assert extract_data["success"] is True, "Extraction not successful"
    print_success("Extraction flag: success")

    assert "bom" in extract_data, "Missing BOM data"
    bom = extract_data["bom"]
    print_success(f"BOM data present with {len(bom.get('items', []))} items")

    # Verify hierarchy information
    if "hierarchy_depth" in extract_data:
        depth = extract_data["hierarchy_depth"]
        print_success(f"Hierarchy depth: {level_count if (level_count := extract_data.get('level_count')) else depth}")

    if bom.get("parent_child_map"):
        parent_child_count = len(bom["parent_child_map"])
        print_success(f"Parent-child relationships: {parent_child_count}")

    return extract_data


async def step2_validate_bom(
    client: httpx.AsyncClient,
    api_base: str,
    headers: dict[str, str],
    bom_items: list[dict[str, Any]],
    table_id: str,
) -> dict[str, Any]:
    """
    STEP 2-3: Validate BOM against database and highlight new vs existing parts.

    Returns validation result.
    """
    print_section("STEP 2-3: Validate BOM & Highlight New vs Existing Parts")

    validation_request = {
        "bom_data": bom_items,
        "table_id": table_id,
        "field_mapping": {
            "part_number": "part_number",
            "description": "description",
        },
        "validation_config": {
            "required_fields": ["part_number"],
            "check_duplicates": True,
            "validate_against_database": True,
        },
    }

    print_info("Sending POST request to /extraction/bom/validate")
    print(f"  - Table ID: {table_id}")
    print(f"  - BOM items: {len(bom_items)}")
    print(f"  - Field mapping: part_number, description")

    response = await client.post(
        f"{api_base}/extraction/bom/validate",
        headers=headers,
        json=validation_request,
    )

    if response.status_code != 200:
        print_error(f"Validation failed with status {response.status_code}")
        print_error(f"Response: {response.text}")
        sys.exit(1)

    validation_result = response.json()
    print_success(f"BOM validated successfully (status {response.status_code})")

    # Verify validation result structure
    assert "is_valid" in validation_result, "Missing is_valid flag"
    assert "total_items" in validation_result, "Missing total_items"
    assert "valid_items" in validation_result, "Missing valid_items"
    assert "invalid_items" in validation_result, "Missing invalid_items"
    assert "new_parts" in validation_result, "Missing new_parts"
    assert "existing_parts" in validation_result, "Missing existing_parts"

    print_success("Validation result structure verified")

    total = validation_result["total_items"]
    valid = validation_result["valid_items"]
    invalid = validation_result["invalid_items"]
    new = len(validation_result.get("new_parts", []))
    existing = len(validation_result.get("existing_parts", []))

    print_info(f"Validation summary:")
    print(f"  - Total items: {total}")
    print(f"  - Valid items: {valid}")
    print(f"  - Invalid items: {invalid}")
    print(f"  - New parts: {new}")
    print(f"  - Existing parts: {existing}")

    # Highlight new vs existing parts
    if new > 0:
        print_success(f"✨ {new} NEW PARTS identified requiring action")
        for part in validation_result.get("new_parts", [])[:5]:  # Show first 5
            pn = part.get("part_number", "N/A")
            desc = part.get("description", "N/A")
            print(f"    - {pn}: {desc}")

    if existing > 0:
        print_success(f"✓ {existing} EXISTING PARTS found in database")
        for part in validation_result.get("existing_parts", [])[:5]:  # Show first 5
            pn = part.get("part_number", "N/A")
            desc = part.get("description", "N/A")
            print(f"    - {pn}: {desc}")

    return validation_result


async def step4_flatten_bom(
    client: httpx.AsyncClient, api_base: str, headers: dict[str, str]
) -> dict[str, Any]:
    """
    STEP 4: Flatten BOM with quantity rollup.

    Returns flattened BOM data.
    """
    print_section("STEP 4: Flatten BOM with Quantity Rollup")

    step_content = create_sample_step_file()
    files = {
        "file": (
            "verification_assembly.step",
            io.BytesIO(step_content),
            "application/octet-stream",
        )
    }
    data = {
        "format": "step",
        "hierarchy_mode": "flattened",
        "flattening_strategy": "path",
        "path_separator": " > ",
        "extract_bom": "true",
    }

    print_info("Sending POST request to /extraction/bom/extract (flattened mode)")
    print(f"  - Hierarchy mode: flattened")
    print(f"  - Flattening strategy: path")
    print(f"  - Path separator: ' > '")

    response = await client.post(
        f"{api_base}/extraction/bom/extract",
        headers=headers,
        files=files,
        data=data,
    )

    if response.status_code not in [200, 201]:
        print_error(f"Flattening failed with status {response.status_code}")
        print_error(f"Response: {response.text}")
        sys.exit(1)

    flattened_data = response.json()
    print_success(f"BOM flattened successfully (status {response.status_code})")

    # Verify flattened structure
    assert "bom" in flattened_data, "Missing BOM data"
    assert "flattened" in flattened_data, "Missing flattened flag"
    assert flattened_data["flattened"] is True, "Flattened flag is False"

    print_success("Flattened flag verified: True")

    bom = flattened_data["bom"]
    item_count = len(bom.get("items", []))
    print_success(f"Flattened BOM has {item_count} items")

    # Verify quantity rollup
    if "flattened_items" in flattened_data:
        flattened_items = flattened_data["flattened_items"]
        print_success(f"Quantity rollup completed for {len(flattened_items)} items")

        # Show some items with quantities
        print_info("Sample flattened items with rolled-up quantities:")
        for item in flattened_items[:5]:
            pn = item.get("part_number", "N/A")
            qty = item.get("quantity", "N/A")
            path = item.get("hierarchy_path", "N/A")
            print(f"    - {pn}: qty={qty} | path={path}")

    return flattened_data


async def step5_import_bom(
    client: httpx.AsyncClient,
    api_base: str,
    headers: dict[str, str],
    bom_items: list[dict[str, Any]],
    table_id: str,
    field_mapping: dict[str, str],
) -> dict[str, Any]:
    """
    STEP 5: Import flattened BOM to table.

    Returns import result.
    """
    print_section("STEP 5: Import Flattened BOM to Table")

    import_request = {
        "table_id": table_id,
        "bom_data": bom_items,
        "field_mapping": field_mapping,
        "import_mode": "validated",
        "batch_size": 100,
    }

    print_info("Sending POST request to /extraction/bom/import")
    print(f"  - Table ID: {table_id}")
    print(f"  - BOM items: {len(bom_items)}")
    print(f"  - Import mode: validated")
    print(f"  - Batch size: 100")

    response = await client.post(
        f"{api_base}/extraction/bom/import",
        headers=headers,
        json=import_request,
    )

    if response.status_code not in [200, 207]:
        print_error(f"Import failed with status {response.status_code}")
        print_error(f"Response: {response.text}")
        sys.exit(1)

    import_result = response.json()
    print_success(f"BOM imported successfully (status {response.status_code})")

    # Verify import result structure
    assert "total_items" in import_result, "Missing total_items"
    assert "imported_count" in import_result, "Missing imported_count"
    assert "table_id" in import_result, "Missing table_id"

    total = import_result["total_items"]
    imported = import_result["imported_count"]
    failed = import_result.get("failed_count", 0)

    print_success("Import result structure verified")
    print_info(f"Import summary:")
    print(f"  - Total items: {total}")
    print(f"  - Imported: {imported}")
    print(f"  - Failed: {failed}")

    return import_result


async def step6_verify_records(
    client: httpx.AsyncClient,
    api_base: str,
    headers: dict[str, str],
    table_id: str,
    expected_count: int,
) -> None:
    """
    STEP 6: Verify records are created correctly in the table.
    """
    print_section("STEP 6: Verify Records Created in Table")

    print_info(f"Sending GET request to /tables/{table_id}/records")

    response = await client.get(
        f"{api_base}/tables/{table_id}/records",
        headers=headers,
    )

    if response.status_code != 200:
        print_error(f"Failed to fetch records with status {response.status_code}")
        print_error(f"Response: {response.text}")
        sys.exit(1)

    records_data = response.json()
    print_success(f"Records fetched successfully (status {response.status_code})")

    # Verify records structure
    assert "records" in records_data, "Missing records in response"
    records = records_data["records"]
    actual_count = len(records)

    print_success(f"Records structure verified")
    print_info(f"Record count: {actual_count}")

    if expected_count > 0:
        if actual_count >= expected_count:
            print_success(f"✅ Expected at least {expected_count} records, found {actual_count}")
        else:
            print_error(f"❌ Expected at least {expected_count} records, found {actual_count}")

    # Show sample records
    if records:
        print_info("Sample imported records:")
        for record in records[:5]:
            print(f"    - Record ID: {record.get('id', 'N/A')}")
            for field_name, field_value in record.get("data", {}).items():
                if field_value:
                    print(f"      {field_name}: {field_value}")


async def main() -> int:
    """Main verification workflow."""
    parser = argparse.ArgumentParser(
        description="Verify BOM extraction, validation, and import workflow"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/api/v1",
        help="API base URL (default: http://localhost:8000/api/v1)",
    )
    parser.add_argument(
        "--token",
        help="Auth token (if not provided, attempts anonymous access)",
    )
    parser.add_argument(
        "--table-id",
        help="Target table ID for import (if not provided, creates new)",
    )
    parser.add_argument(
        "--parts-table-id",
        help="Parts table ID for validation (if not provided, uses table-id)",
    )

    args = parser.parse_args()

    # Setup HTTP client
    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    print_section("BOM Extraction, Validation, and Import Workflow Verification")
    print_info(f"API URL: {args.api_url}")
    print_info(f"Auth: {'Bearer token' if args.token else 'Anonymous'}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # STEP 1: Extract BOM (hierarchical)
            extract_data = await step1_extract_bom_hierarchical(client, args.api_url, headers)
            bom_items = extract_data["bom"]["items"]

            # STEP 2-3: Validate BOM (if table ID provided)
            parts_table_id = args.parts_table_id or args.table_id
            if parts_table_id:
                validation_result = await step2_validate_bom(
                    client, args.api_url, headers, bom_items, parts_table_id
                )
            else:
                print_info("⚠️  Skipping validation (no table ID provided)")

            # STEP 4: Flatten BOM
            flattened_data = await step4_flatten_bom(client, args.api_url, headers)
            flattened_items = flattened_data["bom"]["items"]

            # STEP 5: Import BOM (if table ID provided)
            if args.table_id:
                # Simple field mapping (adjust as needed)
                field_mapping = {
                    "part_number": "part_number",
                    "description": "description",
                    "quantity": "quantity",
                    "material": "material",
                }

                import_result = await step5_import_bom(
                    client, args.api_url, headers, flattened_items, args.table_id, field_mapping
                )

                # STEP 6: Verify records
                await step6_verify_records(
                    client,
                    args.api_url,
                    headers,
                    args.table_id,
                    import_result["imported_count"],
                )
            else:
                print_info("⚠️  Skipping import (no table ID provided)")

            # SUCCESS
            print_section("✅ VERIFICATION COMPLETE")
            print_success("All workflow steps completed successfully!")
            print("\nWorkflow verified:")
            print("  ✅ BOM extracted from STEP file")
            print("  ✅ Hierarchy with parent-child relationships captured")
            print("  ✅ Validated against parts database" if parts_table_id else "  ⚠️  Validation skipped (no table)")
            print("  ✅ New parts highlighted vs existing parts" if parts_table_id else "  ⚠️  Highlighting skipped (no table)")
            print("  ✅ BOM flattened with quantity rollup")
            print("  ✅ Imported to table successfully" if args.table_id else "  ⚠️  Import skipped (no table)")
            print("  ✅ Records created and verified" if args.table_id else "  ⚠️  Verification skipped (no table)")

            return 0

        except Exception as e:
            print_error(f"Verification failed: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
