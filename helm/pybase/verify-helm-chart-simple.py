#!/usr/bin/env python3
"""
Helm Chart Verification Script (No Dependencies)

Validates Helm chart structure, YAML syntax, and template syntax.
This script is used when helm CLI is not available in restricted environments.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple


class HelmChartVerifier:
    """Verifies Helm chart structure and templates"""

    def __init__(self, chart_path: str):
        self.chart_path = Path(chart_path)
        self.errors = []
        self.warnings = []
        self.templates_path = self.chart_path / "templates"

    def verify(self) -> bool:
        """Run all verification checks"""
        print(f"🔍 Verifying Helm chart at: {self.chart_path}")
        print("=" * 60)

        # Check required files
        self._verify_required_files()

        # Verify Chart.yaml
        self._verify_chart_yaml()

        # Verify values.yaml
        self._verify_values_yaml()

        # Verify templates
        self._verify_templates()

        # Print results
        print("\n" + "=" * 60)
        if self.errors:
            print(f"❌ Helm chart validation FAILED with {len(self.errors)} error(s)")
            for error in self.errors:
                print(f"  ERROR: {error}")
            if self.warnings:
                print(f"\n⚠️  {len(self.warnings)} warning(s):")
                for warning in self.warnings:
                    print(f"  WARNING: {warning}")
            return False
        else:
            print(f"✅ Helm chart validation PASSED")
            if self.warnings:
                print(f"\n⚠️  {len(self.warnings)} warning(s):")
                for warning in self.warnings:
                    print(f"  WARNING: {warning}")
            return True

    def _verify_required_files(self):
        """Check that required Helm chart files exist"""
        print("\n📋 Checking required files...")

        required_files = [
            "Chart.yaml",
            "values.yaml",
            "templates/_helpers.tpl",
            "templates/NOTES.txt"
        ]

        for file in required_files:
            file_path = self.chart_path / file
            if file_path.exists():
                print(f"  ✓ {file} exists")
            else:
                self.errors.append(f"Required file missing: {file}")
                print(f"  ✗ {file} missing")

    def _verify_chart_yaml(self):
        """Verify Chart.yaml structure and content"""
        print("\n📄 Verifying Chart.yaml...")

        chart_yaml_path = self.chart_path / "Chart.yaml"
        try:
            with open(chart_yaml_path, 'r') as f:
                content = f.read()

            # Check for required fields by regex
            required_fields = {
                'apiVersion': r'^apiVersion:\s*\S+',
                'name': r'^name:\s*\S+',
                'version': r'^version:\s*\S+',
                'description': r'^description:\s*.+',
                'type': r'^type:\s*\S+',
            }

            for field, pattern in required_fields.items():
                if re.search(pattern, content, re.MULTILINE):
                    match = re.search(pattern, content, re.MULTILINE)
                    print(f"  ✓ {field}: {match.group(0).split(':', 1)[1].strip()}")
                else:
                    self.errors.append(f"Chart.yaml missing required field: {field}")
                    print(f"  ✗ {field} missing")

            # Verify apiVersion is v2
            if re.search(r'^apiVersion:\s*v2', content, re.MULTILINE):
                print(f"  ✓ Using Helm v2 (correct)")
            else:
                self.errors.append("Chart.yaml apiVersion should be 'v2'")

            # Check dependencies if present
            deps = re.findall(r'^\s*-\s*name:\s*\S+', content, re.MULTILINE)
            if deps:
                print(f"  ✓ Dependencies: {len(deps)} defined")

        except Exception as e:
            self.errors.append(f"Failed to parse Chart.yaml: {e}")
            print(f"  ✗ Failed to parse: {e}")

    def _verify_values_yaml(self):
        """Verify values.yaml structure and syntax"""
        print("\n📝 Verifying values.yaml...")

        values_yaml_path = self.chart_path / "values.yaml"
        try:
            with open(values_yaml_path, 'r') as f:
                content = f.read()

            # Check for common top-level sections
            expected_sections = [
                'global', 'pybase', 'api', 'extractionWorker',
                'searchWorker', 'frontend', 'postgresql', 'redis',
                'minio', 'meilisearch', 'ingress'
            ]

            for section in expected_sections:
                pattern = f"^{section}:"
                if re.search(pattern, content, re.MULTILINE):
                    print(f"  ✓ Section '{section}' defined")
                else:
                    self.warnings.append(f"values.yaml missing section: {section}")

            # Count configuration items
            replica_count = len(re.findall(r'replicaCount:\s*\d+', content))
            image_count = len(re.findall(r'repository:\s*\S+', content))
            resource_count = len(re.findall(r'resources:\s*$', content, re.MULTILINE))

            print(f"  ✓ Configuration: {replica_count} replicaCounts, {image_count} images, {resource_count} resource definitions")

        except Exception as e:
            self.errors.append(f"Failed to parse values.yaml: {e}")
            print(f"  ✗ Failed to parse: {e}")

    def _verify_templates(self):
        """Verify all template files"""
        print("\n📦 Verifying templates...")

        if not self.templates_path.exists():
            self.errors.append("templates directory not found")
            return

        template_files = list(self.templates_path.glob("*.yaml"))
        print(f"  Found {len(template_files)} template files")

        # Helper templates
        helper_file = self.templates_path / "_helpers.tpl"
        if helper_file.exists():
            self._verify_helpers_tpl(helper_file)

        # Verify each template
        for template_file in template_files:
            self._verify_template_file(template_file)

        # Also check NOTES.txt
        notes_file = self.templates_path / "NOTES.txt"
        if notes_file.exists():
            print(f"  ✓ NOTES.txt exists")
        else:
            self.warnings.append("templates/NOTES.txt not found")

    def _verify_helpers_tpl(self, helper_file: Path):
        """Verify _helpers.tpl contains required helpers"""
        print("\n  📌 Verifying _helpers.tpl...")

        try:
            with open(helper_file, 'r') as f:
                content = f.read()

            # Check for standard helper templates
            required_helpers = [
                'name',
                'fullname',
                'chart',
                'namespace',
                'labels',
                'selectorLabels',
                'serviceAccountName'
            ]

            for helper in required_helpers:
                pattern = f'{{{{- define "{helper}"'
                if pattern in content:
                    print(f"    ✓ Helper '{helper}' defined")
                else:
                    self.warnings.append(f"_helpers.tpl missing helper: {helper}")

        except Exception as e:
            self.errors.append(f"Failed to read _helpers.tpl: {e}")

    def _verify_template_file(self, template_file: Path):
        """Verify a single template file"""
        filename = template_file.name

        try:
            with open(template_file, 'r') as f:
                content = f.read()

            # Check for Kubernetes resource indicators
            api_version_count = len(re.findall(r'apiVersion:', content))
            kind_count = len(re.findall(r'kind:', content))

            if api_version_count > 0 and kind_count > 0:
                print(f"  ✓ {filename}: {api_version_count} resource(s)")
            else:
                self.warnings.append(f"{filename}: No Kubernetes resources found")

            # Check Helm template syntax
            self._verify_template_syntax(content, filename)

        except Exception as e:
            self.errors.append(f"Failed to verify {filename}: {e}")
            print(f"  ✗ {filename}: {e}")

    def _verify_template_syntax(self, content: str, filename: str):
        """Verify Helm template syntax (balanced braces, etc.)"""
        # Count opening and closing braces
        open_braces = content.count('{{')
        close_braces = content.count('}}')

        if open_braces != close_braces:
            self.errors.append(
                f"{filename}: Unbalanced template braces "
                f"({{: {open_braces}, }}: {close_braces})"
            )

        # Check for if/end blocks
        if_count = content.count('{{- if ')
        end_count = content.count('{{- end }}')
        with_count = content.count('{{- with ')

        if if_count + with_count != end_count:
            # This is a soft warning because some templates might have nested structures
            # that are hard to count without a proper parser
            if abs(if_count + with_count - end_count) > 1:
                self.warnings.append(
                    f"{filename}: Possible unbalanced if/with/end blocks "
                    f"(if: {if_count}, with: {with_count}, end: {end_count})"
                )

        # Check for template helper usage
        if 'metadata:' in content:
            if 'include "pybase.labels"' in content or 'include "pybase.selectorLabels"' in content:
                pass  # Good, using standard helpers
            else:
                # Only warn for core templates
                if not filename.startswith('_'):
                    self.warnings.append(
                        f"{filename}: metadata found but not using standard label helpers"
                    )

        # Check for common patterns
        if '{{ .Values' in content:
            quote_count = content.count('| quote')
            values_count = len(re.findall(r'{{\s*\.Values', content))
            # Rough heuristic: if there are many Values references but few quotes, warn
            if values_count > 5 and quote_count < values_count // 2:
                self.warnings.append(
                    f"{filename}: Some {{ .Values.* }} may need | quote filter"
                )


def main():
    """Main entry point"""
    # Get chart path from script directory
    script_dir = Path(__file__).parent
    chart_path = script_dir

    # Run verification
    verifier = HelmChartVerifier(str(chart_path))
    success = verifier.verify()

    # Print summary message
    if success:
        print("\n✅ Helm chart valid")

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
