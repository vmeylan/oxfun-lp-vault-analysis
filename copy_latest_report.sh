#!/bin/bash
# Find the latest folder in 'data' (folders are named as yyyy-mm-dd)
latest=$(ls -1d data/* | sort | tail -n 1)
echo "Latest report folder: $latest"

# Create the public directory if it doesn't exist
mkdir -p public

# Copy the HTML report (for example, pnl_analysis_report.html) from the latest folder to public/index.html
cp "$latest/pnl_analysis_report.html" public/index.html

