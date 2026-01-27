#!/usr/bin/env python3
"""
Verify Kubernetes manifests for YAML syntax and structure.
This script validates all manifests in k8s/base directory.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file."""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error in {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        sys.exit(1)


def validate_kubernetes_resource(resource: Dict[str, Any], file_path: Path) -> bool:
    """Validate a Kubernetes resource has required fields."""
    api_version = resource.get('apiVersion')
    kind = resource.get('kind')
    metadata = resource.get('metadata', {})

    if not api_version:
        print(f"❌ Missing apiVersion in {file_path}")
        return False
    if not kind:
        print(f"❌ Missing kind in {file_path}")
        return False
    if not metadata.get('name'):
        print(f"❌ Missing metadata.name in {file_path}")
        return False

    return True


def validate_kustomization(kustomization_path: Path) -> bool:
    """Validate kustomization.yaml file."""
    if not kustomization_path.exists():
        print(f"❌ kustomization.yaml not found at {kustomization_path}")
        return False

    kustomization = load_yaml(kustomization_path)

    # Check required fields
    if 'apiVersion' not in kustomization:
        print(f"❌ Missing apiVersion in {kustomization_path}")
        return False
    if 'kind' not in kustomization:
        print(f"❌ Missing kind in {kustomization_path}")
        return False
    if kustomization['kind'] != 'Kustomization':
        print(f"❌ Expected kind=Kustomization, got {kustomization['kind']}")
        return False

    # Check resources list
    resources = kustomization.get('resources', [])
    if not resources:
        print(f"❌ No resources listed in {kustomization_path}")
        return False

    # Verify all referenced resources exist
    base_dir = kustomization_path.parent
    missing_files = []
    for resource in resources:
        resource_path = base_dir / resource
        if not resource_path.exists():
            missing_files.append(str(resource_path))

    if missing_files:
        print(f"❌ Referenced resources not found:")
        for file in missing_files:
            print(f"   - {file}")
        return False

    print(f"✓ Kustomization file valid with {len(resources)} resources")
    return True


def validate_manifest_files(base_dir: Path) -> List[str]:
    """Validate all YAML manifests in the base directory."""
    yaml_files = sorted(base_dir.glob('*.yaml'))
    errors = []
    valid_count = 0

    print(f"\nValidating {len(yaml_files)} manifest files...")

    for yaml_file in yaml_files:
        # Skip template files and kustomization.yaml
        if yaml_file.name.endswith('.template') or yaml_file.name == 'kustomization.yaml':
            print(f"⊙ Skipping: {yaml_file.name}")
            continue

        try:
            # Load all YAML documents from file
            with open(yaml_file, 'r') as f:
                documents = list(yaml.safe_load_all(f))

            # Filter out None documents (e.g., empty document separators)
            documents = [d for d in documents if d is not None]

            if not documents:
                print(f"⊙ {yaml_file.name:40} (empty document)")
                continue

            # Validate each resource
            all_valid = True
            for i, resource in enumerate(documents):
                if not validate_kubernetes_resource(resource, yaml_file):
                    all_valid = False
                    errors.append(f"{yaml_file.name} (document {i+1})")

            if all_valid:
                # Show first resource's kind and name
                kind = documents[0].get('kind', 'Unknown')
                name = documents[0].get('metadata', {}).get('name', 'unknown')
                doc_count = f" ({len(documents)} docs)" if len(documents) > 1 else ""
                print(f"✓ {yaml_file.name:40} {kind}/{name}{doc_count}")
                valid_count += 1

        except yaml.YAMLError as e:
            errors.append(f"{yaml_file.name}: {str(e)}")
            print(f"❌ {yaml_file.name}: YAML syntax error")
            print(f"   {e}")
        except Exception as e:
            errors.append(f"{yaml_file.name}: {str(e)}")
            print(f"❌ {yaml_file.name}: {e}")

    return errors


def check_required_components(base_dir: Path) -> bool:
    """Check that all required component manifests are present."""
    required_files = [
        'namespace.yaml',
        'kustomization.yaml',
        'postgres-deployment.yaml',
        'postgres-service.yaml',
        'redis-deployment.yaml',
        'redis-service.yaml',
        'api-deployment.yaml',
        'api-service.yaml',
        'api-hpa.yaml',
        'extraction-worker-deployment.yaml',
        'search-worker-deployment.yaml',
        'workers-hpa.yaml',
        'frontend-deployment.yaml',
        'frontend-service.yaml',
        'ingress.yaml',
        'network-policy.yaml',
        'pdb.yaml',
        'rbac.yaml',
    ]

    print("\nChecking for required component manifests...")
    missing = []
    for required_file in required_files:
        file_path = base_dir / required_file
        if not file_path.exists():
            missing.append(required_file)
        else:
            print(f"✓ {required_file}")

    if missing:
        print(f"\n❌ Missing required files:")
        for file in missing:
            print(f"   - {file}")
        return False

    return True


def main():
    """Main verification function."""
    base_dir = Path(__file__).parent / 'base'

    if not base_dir.exists():
        print(f"❌ Base directory not found: {base_dir}")
        sys.exit(1)

    print("=" * 70)
    print("Kubernetes Manifests Verification")
    print("=" * 70)

    # Check required components
    components_valid = check_required_components(base_dir)

    # Validate kustomization.yaml
    print("\n" + "-" * 70)
    kustomization_valid = validate_kustomization(base_dir / 'kustomization.yaml')

    # Validate all manifest files
    print("\n" + "-" * 70)
    errors = validate_manifest_files(base_dir)

    # Summary
    print("\n" + "=" * 70)
    print("Verification Summary")
    print("=" * 70)

    if components_valid and kustomization_valid and not errors:
        print("✅ Base manifests valid")
        print("\nAll Kubernetes manifests are syntactically valid and properly structured.")
        return 0
    else:
        print("❌ Validation failed")
        if not components_valid:
            print("   - Missing required component files")
        if not kustomization_valid:
            print("   - Kustomization file has errors")
        if errors:
            print(f"   - {len(errors)} manifest files have errors")
        return 1


if __name__ == '__main__':
    sys.exit(main())
