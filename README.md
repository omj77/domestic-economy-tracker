# Domestic Economy Tracker

A Python application for tracking and visualizing domestic economy using Streamlit.

## Features

- 📊 Track income and expenses with categorization
- 💰 Budget management and comparison
- 📈 Visual analytics with interactive charts
- 📅 Monthly and yearly summaries
- 🗓️ Multi-select month/year filtering across tabs
- 💵 Budget vs actual spending analysis
- 📆 Previous-year comparison for the same selected months
- 🏦 Track balances across multiple bank accounts
- 📊 Visualize account evolution and distribution

## Setup

This project now uses `uv` for dependency management and command execution.

> The Python project lives in the `domestic_economy/` subfolder, so run the commands below from there.

```bash
cd domestic_economy
uv sync

# Create initial Excel file with sample data if you need it
uv run python create_excel.py
```

## Usage

### Running the Application

```bash
cd domestic_economy
uv run streamlit run domestic_economy/main.py
```

If `streamlit` was previously failing with `Command not found`, it usually means the dependencies were not installed in the active environment. `uv sync` installs the declared dependencies and `uv run ...` executes them inside the project environment.

The application will open in your default web browser.

Use the left sidebar to select one or more `month + year` combinations (for example, `February 2026` + `March 2026`). All analytical tabs will update to those exact periods.

### Alternative: run everything from the repository root

If you prefer not to `cd` into the project folder:

```bash
uv --directory domestic_economy sync
uv --directory domestic_economy run python create_excel.py
uv --directory domestic_economy run streamlit run domestic_economy/main.py
```

### Excel File Structure

The application reads data from `data/economy.xlsx` with three sheets:

#### 1. Movements Sheet
- **category**: Main category (e.g., Income, Groceries, Transport)
- **subcategory**: Specific subcategory (e.g., Salary, Supermarket, Gas)
- **date**: Transaction date
- **description**: Transaction description
- **amount**: Transaction amount (positive for income, negative for expenses)

#### 2. Budget Sheet
- **category**: Main category
- **subcategory**: Specific subcategory
- **month**: Month number (1-12)
- **year**: Year
- **budget**: Budget amount for that category/subcategory/period

#### 3. Accounts Sheet
- **month**: Month number (1-12)
- **year**: Year
- **CX**: Balance in CX account
- **BBVA**: Balance in BBVA account
- **Inversiones**: Balance in Inversiones account
- **Plan_Pensiones**: Balance in Plan Pensiones account

### Adding Your Data

1. Open `data/economy.xlsx` in Excel or any spreadsheet application
2. Add your movements in the "movements" sheet
3. Set your budgets in the "budget" sheet
4. Add your monthly account balances in the "accounts" sheet
5. Save the file
6. Refresh the Streamlit application

## Dashboard Tabs

1. **Overview**: Key metrics, total in accounts, and expense distribution
2. **Budget vs Actual**: Compare your budgets against actual values with absolute-value charting
3. **Income & Expenses**: Monthly trends and cumulative balance
4. **Accounts**: Track account balances, evolution, and distribution
5. **Category Details**: Interactive category selector with subcategory breakdown in bar charts and pie charts
6. **Previous Year Comparison**: Compare each selected month against the same month one year earlier
7. **Data**: View raw data from all sheets

## Project Structure

```
domestic-economy-tracker/
├── README.md
└── domestic_economy/
	├── data/
	│   └── economy.xlsx      # Excel file with movements, budget, and accounts
	├── domestic_economy/
	│   ├── __init__.py
	│   ├── excel_utils.py    # Utilities for reading Excel data
	│   └── main.py           # Main Streamlit application
	├── create_excel.py       # Script to create initial Excel file
	├── pyproject.toml        # uv / project configuration
	├── tests/
	└── uv.lock
```

## Common commands

```bash
cd domestic_economy

# Install/update dependencies
uv sync

# Launch the dashboard
uv run streamlit run domestic_economy/main.py

# Run tests
uv run python -m unittest discover -s tests
```

## Technologies Used

- **Python 3.10+**
- **Streamlit**: Web application framework
- **Pandas**: Data manipulation
- **Plotly**: Interactive visualizations
- **OpenPyXL**: Excel file handling

## License

MIT
