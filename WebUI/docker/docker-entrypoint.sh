#!/bin/bash
set -euo pipefail

# Simple entrypoint for the WebUI container.
# - if first argument looks like a flag (starts with -), prepend the default command
# - support waiting for a DB (if DATABASE_URL set) using a small loop

# Default command is provided by the Dockerfile CMD (gunicorn ...)

# Wait for database (optional)
if [[ -n "${DATABASE_URL-}" ]]; then
  echo "Waiting for database to be available..."
  # Try a few times to access the DB host/port extracted from DATABASE_URL
  # If DATABASE_URL uses a socket or other scheme, skip the active wait.
  if [[ "$DATABASE_URL" =~ ^postgresql://([^:/]+):([0-9]+) ]]; then
    host=${BASH_REMATCH[1]}
    port=${BASH_REMATCH[2]}
    for i in {1..10}; do
      if nc -z "$host" "$port" 2>/dev/null; then
        echo "Database is reachable"
        break
      fi
      echo "Database not reachable yet, retrying ($i/10)..."
      sleep 2
    done
  fi
fi

# If invoked with a flag, prepend the CMD
if [[ "${1-}" == "-"* ]]; then
  set -- "$@"
fi

exec "$@"
