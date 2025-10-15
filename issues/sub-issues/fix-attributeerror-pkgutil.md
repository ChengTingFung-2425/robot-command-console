### Sub-Issue: Fix AttributeError in Python 3.12

**Description:**
Resolve the Python 3.12 compatibility error: AttributeError: module 'pkgutil' has no attribute 'ImpImporter'. Investigate if this comes from a direct usage in our code or an outdated dependency. Update our code or upgrade/remove the problematic dependency accordingly. Verify that the workflow passes after the fix.

**Reference:** [Issue #7](https://github.com/ChengTingFung-2425/robot-command-console/issues/7)