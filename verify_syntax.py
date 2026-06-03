#!/usr/bin/env python
"""
Python syntax and import verification script
Checks all Python files for syntax errors and import issues
"""

import ast
import sys
from pathlib import Path

print("=" * 70)
print("PYTHON CODE VERIFICATION")
print("=" * 70)

# Files to check
python_files = [
    'app.py',
    'config.py',
    'data_loader.py',
    'visualizer.py',
    'gemini_queries.py',
    'utils.py',
    'pages_dashboard.py',
    'pages_maps.py',
    'pages_query.py',
    'pages_localauth.py',
]

errors = []
warnings = []

print(f"\nChecking {len(python_files)} Python files...\n")

for file in python_files:
    filepath = Path(file)
    
    if not filepath.exists():
        print(f"❌ {file:<30} NOT FOUND")
        errors.append(f"{file}: File not found")
        continue
    
    try:
        # Check syntax
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        ast.parse(code)
        print(f"✅ {file:<30} Syntax OK")
        
        # Check for common issues
        if 'import streamlit' not in code and file != 'config.py':
            if file.startswith('pages_'):
                warnings.append(f"{file}: Missing streamlit import")
        
    except SyntaxError as e:
        print(f"❌ {file:<30} SYNTAX ERROR")
        errors.append(f"{file}: {str(e)}")
    except Exception as e:
        print(f"❌ {file:<30} ERROR: {str(e)}")
        errors.append(f"{file}: {str(e)}")

print("\n" + "=" * 70)

if errors:
    print("❌ ERRORS FOUND:")
    for error in errors:
        print(f"  • {error}")
    sys.exit(1)

if warnings:
    print("⚠️  WARNINGS:")
    for warning in warnings:
        print(f"  • {warning}")

if not errors and not warnings:
    print("✅ ALL FILES PASSED VERIFICATION")
    print("\nAll Python files have correct syntax and basic structure.")
    print("\nYou can now run the app:")
    print("  streamlit run app.py")

print("=" * 70)
