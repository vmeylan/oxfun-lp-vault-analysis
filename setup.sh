#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting environment setup for Selenium scraping and data analysis project..."

# Function to check if a command exists
command_exists () {
    command -v "$1" >/dev/null 2>&1 ;
}

# Check if Python3 is installed
if ! command_exists python3 ; then
    echo "Error: Python3 is not installed. Please install Python3 before proceeding."
    exit 1
fi

# Create a virtual environment named 'venv' if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating a virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate the virtual environment
echo "Activating the virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install required Python packages
echo "Installing required Python packages..."
pip install selenium webdriver-manager pandas plotly kaleido

# Deactivate the virtual environment
deactivate

echo "Environment setup complete. You can now run your Python script."
