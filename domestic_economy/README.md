# Domestic Economy Tracker

A Python application for tracking and visualizing domestic economy using Streamlit.

## Features

- 📊 Track income and expenses with categorization
- 💰 Budget management and comparison
- 📈 Visual analytics with interactive charts
- 📅 Monthly and yearly summaries
- 💵 Budget vs actual spending analysis
- 🏦 Track balances across multiple bank accounts
- 📊 Visualize account evolution and distribution

## Installation

This project uses Poetry for dependency management.

```bash
# Install dependencies
poetry install

# Create initial Excel file with sample data
poetry run python create_excel.py
```

## Usage

### Running the Application

```bash
poetry run streamlit run domestic_economy/main.py
```

The application will open in your default web browser.

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
2. **Budget vs Actual**: Compare your spending against budgets
3. **Income & Expenses**: Monthly trends and cumulative balance
4. **Accounts**: Track account balances, evolution, and distribution
5. **Category Details**: Interactive category selector with subcategory breakdown in bar charts and pie charts
6. **Data**: View raw data from all sheets

## Project Structure

```
domestic_economy/
├── data/
│   └── economy.xlsx          # Excel file with movements, budget, and accounts
├── domestic_economy/
│   ├── __init__.py
│   ├── excel_utils.py        # Utilities for reading Excel data
│   └── main.py               # Main Streamlit application
├── create_excel.py           # Script to create initial Excel file
├── pyproject.toml            # Poetry configuration
└── README.md
```

## Technologies Used

- **Python 3.10+**
- **Streamlit**: Web application framework
- **Pandas**: Data manipulation
- **Plotly**: Interactive visualizations
- **OpenPyXL**: Excel file handling

## License

MIT
