#!/bin/bash

# Define the name of the zip file
ZIP_FILE="deploy_package.zip"

# Create the zip file, excluding venv and __pycache__ directories
zip -r $ZIP_FILE . -x "venv/*" -x "__pycache__/*"

echo "Deployment package created: $ZIP_FILE"