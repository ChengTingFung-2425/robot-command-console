#!/usr/bin/env python3
"""
Comprehensive Linting Report and Auto-Fix Script

This script checks and fixes linting issues across the repository for both Python and JavaScript files.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return the output"""
    try:
        # Use list format instead of shell=True for security
        import shlex
        cmd_list = shlex.split(cmd) if isinstance(cmd, str) else cmd
        result = subprocess.run(
            cmd_list,
            shell=False,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def check_python_lint():
    """Check Python linting with flake8"""
    print("=" * 80)
    print("PYTHON LINTING CHECK")
    print("=" * 80)
    
    # Critical errors only (E and F)
    cmd = """python3 -m flake8 . --select=E,F --max-line-length=120 \
--exclude=.venv,node_modules,__pycache__,*.pyc,dist,build,htmlcov,.pytest_cache,.git,Edge/electron-app \
--count --statistics"""
    
    stdout, stderr, code = run_command(cmd)
    
    if code == 0 and not stdout.strip():
        print("✅ No critical Python errors found!")
        return True
    else:
        print("❌ Critical Python errors found:")
        print(stdout)
        if stderr:
            print("Errors:", stderr)
        return False

def check_javascript_syntax():
    """Check JavaScript syntax"""
    print("\n" + "=" * 80)
    print("JAVASCRIPT SYNTAX CHECK")
    print("=" * 80)
    
    # Find all JS files
    cmd = """find . -name "*.js" -not -path "*/node_modules/*" -not -path "*/.venv/*" \
-not -path "*/dist/*" -not -path "*/.git/*" -not -name "*.min.js" """
    
    stdout, stderr, _ = run_command(cmd)
    js_files = [f.strip() for f in stdout.split('\n') if f.strip()]
    
    print(f"Found {len(js_files)} JavaScript files to check")
    
    errors = []
    for js_file in js_files:
        stdout, stderr, code = run_command(f"node --check {js_file}")
        if code != 0:
            errors.append((js_file, stderr))
    
    if not errors:
        print("✅ All JavaScript files have valid syntax!")
        return True
    else:
        print("❌ JavaScript syntax errors found:")
        for file, error in errors:
            print(f"  {file}: {error}")
        return False

def get_lint_summary():
    """Get a summary of all lint issues"""
    print("\n" + "=" * 80)
    print("COMPLETE LINTING SUMMARY")
    print("=" * 80)
    
    cmd = """python3 -m flake8 . --select=E,F,W --max-line-length=120 \
--exclude=.venv,node_modules,__pycache__,*.pyc,dist,build,htmlcov,.pytest_cache,.git,Edge/electron-app \
--count --statistics"""
    
    stdout, stderr, _ = run_command(cmd)
    
    if stdout:
        lines = stdout.strip().split('\n')
        print("\nIssue Summary:")
        for line in lines[-20:]:  # Last 20 lines (statistics)
            print(line)
    
    return stdout

def fix_trailing_whitespace():
    """Fix trailing whitespace in Python files"""
    print("\n" + "=" * 80)
    print("FIXING TRAILING WHITESPACE")
    print("=" * 80)
    
    cmd = """find . -name "*.py" -not -path "*/.venv/*" -not -path "*/node_modules/*" \
-not -path "*/.git/*" -type f -exec sed -i 's/[[:space:]]*$//' {} +"""
    
    stdout, stderr, code = run_command(cmd)
    if code == 0:
        print("✅ Trailing whitespace fixed")
    else:
        print(f"❌ Error fixing whitespace: {stderr}")

def main():
    """Main entry point"""
    print("ROBOT COMMAND CONSOLE - COMPREHENSIVE LINT CHECK")
    print("=" * 80)
    print()
    
    # Check Python linting
    python_ok = check_python_lint()
    
    # Check JavaScript syntax
    js_ok = check_javascript_syntax()
    
    # Get complete summary
    get_lint_summary()
    
    # Offer to fix common issues
    print("\n" + "=" * 80)
    print("AUTO-FIX OPTIONS")
    print("=" * 80)
    print("\nTo auto-fix trailing whitespace issues, uncomment and run:")
    print("  # fix_trailing_whitespace()")
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if python_ok and js_ok:
        print("✅ All checks passed!")
        return 0
    else:
        print("❌ Some checks failed. Please review the issues above.")
        if not python_ok:
            print("  - Python linting has critical errors")
        if not js_ok:
            print("  - JavaScript has syntax errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())
