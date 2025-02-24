# OXFUN LP Vault Analysis

This repository contains Python scripts to scrape, analyze, and visualize performance data for the [OXFUN Liquidity Provider Strategy vault](https://ox.fun/en/vaults/profile/110428). Data is scraped using Selenium, processed with Pandas, and visualized with Plotly. The generated HTML reports and charts are hosted on Vercel.

## Setup

1. Clone the repository:
```
git clone git@github.com:vmeylan/oxfun-lp-vault-analysis.git
cd oxfun-lp-vault-analysis
```

2. Run the setup script to create a virtual environment and install dependencies:
```
bash setup.sh
```

## Running Locally

Activate the virtual environment and run the scripts from the `analysis` folder:
```
cd analysis
source ../venv/bin/activate
python oxfun_vault.py    # Scrapes vault data and saves CSV files
python analyse_data.py    # Analyzes data and generates HTML reports/charts
deactivate
```

## Automation

A GitHub Actions workflow is configured to run the vault and analysis scripts daily at midnight UTC. The workflow uses the `setup.sh` script for environment setup.

## Deployment

The latest HTML report (from the most recent date folder in the `data` directory) is hosted on Vercel.
