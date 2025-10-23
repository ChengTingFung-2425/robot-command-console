# Dockerfile for WebUI (HTTP server only)
# Based on python:3.11-slim for smaller images while keeping compatibility

FROM python:3.11-slim

# Create a non-root user
RUN useradd --create-home --shell /bin/bash webui

# Set workdir
WORKDIR /opt/webui

# Install system dependencies required by common Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       ca-certificates \
       git \
       netcat \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
# Prefer project-specific requirements in WebUI/ if present
COPY requirements.txt ./requirements.txt
COPY WebUI/requirements.txt ./webui-requirements.txt

# Install Python dependencies (choose the WebUI one if present)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && if [ -s webui-requirements.txt ]; then pip install --no-cache-dir -r webui-requirements.txt; elif [ -s requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . /opt/webui

# Ensure logs dir exists and is writable
RUN mkdir -p /opt/webui/WebUI/logs \
    && chown -R webui:webui /opt/webui

# Switch to non-root user
USER webui

ENV FLASK_APP=WebUI.microblog:app
ENV PYTHONUNBUFFERED=1

# Expose HTTP port
EXPOSE 5000

# Entrypoint (will be provided by compose or defaults to flask run)
ENTRYPOINT ["/opt/webui/WebUI/docker/docker-entrypoint.sh"]
CMD ["gunicorn", "-b", "0.0.0.0:5000", "WebUI.app:app", "--workers", "3"]
