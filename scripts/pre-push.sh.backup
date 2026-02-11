#!/usr/bin/env bash
echo "Linting check..."
python3 -m flake8 . --select=E,F --max-line-length=120 --exclude=.venv,node_modules,__pycache__,dist,build,.git,Edge/electron-app,Edge/WebUI/migrations --count
