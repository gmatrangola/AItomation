#!/usr/bin/env python3
"""Validate Python backend code before deployment."""

import sys
import os
import py_compile
from pathlib import Path

# Add workspace to path
WORKSPACE = Path(__file__).parent.parent
AITOMATIONS_DIR = WORKSPACE / "aitomations"

# Add aitomations directory to Python path (where 'src' package lives)
sys.path.insert(0, str(AITOMATIONS_DIR))

BACKEND_DIR = AITOMATIONS_DIR / "src" / "backend"

# Directories to scan for Python files
DIRS_TO_SCAN = ["api", "llm", "."]

# Files to exclude from syntax check
EXCLUDE_FILES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}

def find_python_files():
    """Find all Python files in the backend directory."""
    python_files = []
    
    for dir_name in DIRS_TO_SCAN:
        dir_path = BACKEND_DIR / dir_name if dir_name != "." else BACKEND_DIR
        
        if not dir_path.exists():
            print(f"⚠ Directory not found: {dir_name}")
            continue
        
        # Find all .py files in this directory and subdirectories
        for py_file in dir_path.rglob("*.py"):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in EXCLUDE_FILES):
                continue
            
            # Get relative path from BACKEND_DIR
            rel_path = py_file.relative_to(BACKEND_DIR)
            python_files.append(rel_path)
    
    return sorted(python_files)

def check_syntax(files=None):
    """Check Python syntax for all files."""
    if files is None:
        files = find_python_files()
    
    print(f"Checking Python syntax for {len(files)} files...")
    errors = []
    
    for file_path in files:
        full_path = BACKEND_DIR / file_path
        try:
            py_compile.compile(str(full_path), doraise=True)
            print(f"  ✓ {file_path}")
        except py_compile.PyCompileError as e:
            errors.append(f"Syntax error in {file_path}: {e}")
            print(f"  ✗ {file_path}: {e}")
        except Exception as e:
            errors.append(f"Error checking {file_path}: {e}")
            print(f"  ✗ {file_path}: {e}")
    
    if errors:
        print(f"\n❌ Syntax validation failed ({len(errors)} errors):")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print(f"\n✓ All {len(files)} Python files have valid syntax")
    return True

def check_imports():
    """Test that critical modules can be imported."""
    print("\nChecking critical imports...")
    
    # Critical imports that must work
    imports_to_test = [
        ("src.backend.api.routes", "api_blueprint"),
        ("src.backend.llm.base", "LLMProvider"),
        ("src.backend.llm.ollama", "OllamaProvider"),
        ("src.backend.llm.gemini", "GeminiProvider"),
        ("src.backend.api.network", "resolve_hostname"),
        ("src.backend.api.network", "test_connection"),
    ]
    
    success = True
    errors = []
    
    for module_name, attr_name in imports_to_test:
        try:
            # Import the module
            module = __import__(module_name, fromlist=[attr_name])
            # Verify the attribute exists
            getattr(module, attr_name)
            print(f"  ✓ {module_name}.{attr_name}")
        except ImportError as e:
            error_msg = str(e)
            print(f"  ✗ {module_name}.{attr_name}: Import failed")
            print(f"     {error_msg}")
            errors.append((module_name, attr_name, error_msg))
            success = False
        except AttributeError as e:
            error_msg = f"{attr_name} not found in module"
            print(f"  ✗ {module_name}.{attr_name}: {error_msg}")
            print(f"     {e}")
            errors.append((module_name, attr_name, error_msg))
            success = False
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            print(f"  ✗ {module_name}.{attr_name}: Unexpected error")
            print(f"     {error_msg}")
            errors.append((module_name, attr_name, error_msg))
            success = False
    
    if success:
        print("\n✓ All critical imports successful")
    else:
        print(f"\n❌ {len(errors)} import(s) failed")
        print("\nMost common issues:")
        print("  • Missing __init__.py files")
        print("  • Incorrect import paths (e.g., importing 'zeroconfSetup' instead of 'network')")
        print("  • Missing dependencies")
        print("  • Circular imports")
    
    return success

def check_required_files():
    """Check that all required files exist."""
    print("\nChecking required files...")
    
    required_files = [
        "app.py",
        "api/__init__.py",
        "api/routes.py",
        "api/network.py",
        "llm/__init__.py",
        "llm/base.py",
        "llm/ollama.py",
        "llm/gemini.py",
    ]
    
    missing = []
    for file_path in required_files:
        full_path = BACKEND_DIR / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} (MISSING)")
            missing.append(file_path)
    
    if missing:
        print(f"\n❌ {len(missing)} required file(s) missing:")
        for f in missing:
            print(f"  - {f}")
        return False
    
    print("\n✓ All required files present")
    return True

def main():
    """Run all validations."""
    print("=" * 60)
    print("Backend Validation")
    print("=" * 60)
    print(f"Python path: {sys.path[0]}")
    print(f"Backend dir: {BACKEND_DIR}")
    print()
    
    # Find all Python files
    print("Scanning for Python files...")
    python_files = find_python_files()
    print(f"Found {len(python_files)} Python files\n")
    
    # Check required files exist
    files_ok = check_required_files()
    if not files_ok:
        print("\n" + "=" * 60)
        print("❌ Validation failed: missing required files")
        print("=" * 60)
        sys.exit(1)
    
    # Check syntax of all Python files
    syntax_ok = check_syntax(python_files)
    if not syntax_ok:
        print("\n" + "=" * 60)
        print("❌ Validation failed: syntax errors")
        print("=" * 60)
        sys.exit(1)
    
    # Check critical imports
    imports_ok = check_imports()
    if not imports_ok:
        print("\n" + "=" * 60)
        print("❌ Validation failed: import errors")
        print("=" * 60)
        print("\nRun the validation again with detailed error output:")
        print("  python3 scripts/validate_backend.py")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✓ All validations passed!")
    print("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()