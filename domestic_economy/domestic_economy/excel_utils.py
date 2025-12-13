"""
Utility functions to read data from the Excel file.
"""
import pandas as pd
from typing import Tuple


def read_movements(excel_path: str) -> pd.DataFrame:
    """
    Read movements data from Excel file.

    Args:
        excel_path: Path to the Excel file

    Returns:
        DataFrame with movements data
    """
    df = pd.read_excel(excel_path, sheet_name='movements')
    if not df.empty and 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.month
        df['year'] = df['date'].dt.year
    return df


def read_budget(excel_path: str) -> pd.DataFrame:
    """
    Read budget data from Excel file.

    Args:
        excel_path: Path to the Excel file

    Returns:
        DataFrame with budget data
    """
    return pd.read_excel(excel_path, sheet_name='budget')


def read_accounts(excel_path: str) -> pd.DataFrame:
    """
    Read accounts data from Excel file.

    Args:
        excel_path: Path to the Excel file

    Returns:
        DataFrame with accounts data
    """
    return pd.read_excel(excel_path, sheet_name='accounts')


def read_all_data(excel_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Read movements, budget, and accounts data from Excel file.

    Args:
        excel_path: Path to the Excel file

    Returns:
        Tuple of (movements_df, budget_df, accounts_df)
    """
    return read_movements(excel_path), read_budget(excel_path), read_accounts(excel_path)
