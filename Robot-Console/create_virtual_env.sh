#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define the virtual environment directory
VENV_DIR="venv"

# Create a virtual environment
python3 -m venv $VENV_DIR

# Activate the virtual environment
source $VENV_DIR/bin/activate

# Upgrade pip to the latest version
pip install --upgrade pip

# Install dependencies from requirements.txt if the file exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Skipping dependency installation."
fi

echo "Virtual environment setup complete. To activate, run: source $VENV_DIR/bin/activate"
echo "To run the remote control, run: python pubsub.py"