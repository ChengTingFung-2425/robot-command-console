ARG VARIANT=3.12-bullseye
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT}

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace/src:/workspace/Edge

# 設定工作目錄
WORKDIR /workspace

# 複製 requirements.txt 並安裝 Python 依賴
COPY requirements.txt /tmp/pip-tmp/
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir \
    -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

# 安裝開發工具（linting, testing, validation）
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir \
    "flake8>=7.0.0" \
    "pytest>=7.4.0" \
    "pytest-cov>=4.1.0" \
    "openapi-spec-validator>=0.7.1" \
    "bandit>=1.7.5" \
    "pyyaml>=6.0" \
    "black>=24.0.0"
