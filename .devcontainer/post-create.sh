#!/usr/bin/env bash
# DevContainer 後建立腳本：安裝依賴並啟動 Flask WebUI 與 Cloud 服務

set -euo pipefail

for req in Cloud Edge; do
    pip install -r "/workspace/${req}/requirements.txt" -q
done

PYTHONPATH=/workspace/src:/workspace/Edge \
FLASK_DEBUG=1 \
FLASK_APP=WebUI.app \
flask run --host=0.0.0.0 --port=8080 &

PYTHONPATH=/workspace/src:/workspace/Edge \
python /workspace/.devcontainer/run_cloud.py &
