#!/usr/bin/env python3
"""Shim — delegates to llm-helper/run_tests.py (the canonical source)."""
import os
import runpy
import sys

_here = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(_here, 'llm-helper', 'run_tests.py'), run_name='__main__')
