"""
Script to create the initial Excel file with three sheets: movements, budget, and accounts.
"""
import pandas as pd
from datetime import datetime

# Sample data for movements sheet
movements_data = {
    'category': ['Income', 'Groceries', 'Transport', 'Income', 'Utilities'],
    'subcategory': ['Salary', 'Supermarket', 'Gas', 'Freelance', 'Electricity'],
    'date': [
        datetime(2024, 1, 1),
        datetime(2024, 1, 5),
        datetime(2024, 1, 10),
        datetime(2024, 1, 15),
        datetime(2024, 1, 20)
    ],
    'description': ['Monthly salary', 'Weekly groceries', 'Car refuel', 'Project payment', 'Monthly bill'],
    'amount': [3000.00, -150.50, -45.00, 500.00, -80.00]
}

# Sample data for budget sheet
budget_data = {
    'category': ['Groceries', 'Transport', 'Utilities', 'Entertainment', 'Savings'],
    'subcategory': ['Supermarket', 'Gas', 'Electricity', 'Dining', 'Emergency Fund'],
    'month': [1, 1, 1, 1, 1],
    'year': [2024, 2024, 2024, 2024, 2024],
    'budget': [600.00, 200.00, 100.00, 300.00, 500.00]
}

# Sample data for accounts sheet
accounts_data = {
    'month': [1, 2, 3],
    'year': [2024, 2024, 2024],
    'CX': [5000.00, 5200.00, 5500.00],
    'BBVA': [3000.00, 3100.00, 3250.00],
    'Inversiones': [10000.00, 10500.00, 11000.00],
    'Plan_Pensiones': [8000.00, 8200.00, 8400.00]
}

# Create DataFrames
movements_df = pd.DataFrame(movements_data)
budget_df = pd.DataFrame(budget_data)
accounts_df = pd.DataFrame(accounts_data)

# Write to Excel file with three sheets
excel_path = 'data/economy.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    movements_df.to_excel(writer, sheet_name='movements', index=False)
    budget_df.to_excel(writer, sheet_name='budget', index=False)
    accounts_df.to_excel(writer, sheet_name='accounts', index=False)

print(f"Excel file created successfully at: {excel_path}")
print(f"\nMovements sheet: {len(movements_df)} rows")
print(f"Budget sheet: {len(budget_df)} rows")
print(f"Accounts sheet: {len(accounts_df)} rows")
