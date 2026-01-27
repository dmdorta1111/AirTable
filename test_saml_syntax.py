#!/usr/bin/env python3
"""Test script to verify SAMLService syntax."""

import ast
import sys

try:
    with open('src/pybase/services/saml_service.py', 'r') as f:
        code = f.read()

    # Try to parse the file
    ast.parse(code)
    print("SAMLService file: Syntax is valid")
    sys.exit(0)
except SyntaxError as e:
    print(f"Syntax error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
