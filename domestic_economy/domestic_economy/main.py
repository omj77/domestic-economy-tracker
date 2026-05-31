"""
Main Streamlit application for domestic economy tracking.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from pathlib import Path
import sys
from typing import Sequence

# Add parent directory to path to import excel_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from domestic_economy.excel_utils import read_all_data

# Constants
EXCEL_PATH = Path(__file__).parent.parent / 'data' / 'economy.xlsx'
ACCOUNT_COLUMNS = ['CX', 'BBVA', 'Inversiones', 'Plan_Pensiones']
NEW_HOME_CATEGORY_KEY = 'new home'
MONTH_NAMES_ES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre',
}


def normalize_dimension_value(value: object) -> str:
    """Normalize text values for case-insensitive joins."""
    if pd.isna(value):
        return ''
    return str(value).strip().casefold()


def format_period(year: int, month: int) -> str:
    """Format a month/year tuple for display."""
    return f"{MONTH_NAMES_ES.get(int(month), str(month))} {int(year)}"


def build_available_periods(*dfs: pd.DataFrame) -> list[tuple[int, int]]:
    """Collect every unique month/year pair available across the loaded datasets."""
    periods: set[tuple[int, int]] = set()

    for df in dfs:
        if df.empty or 'year' not in df.columns or 'month' not in df.columns:
            continue

        valid_periods = df[['year', 'month']].dropna().drop_duplicates()
        for year, month in valid_periods.itertuples(index=False, name=None):
            periods.add((int(year), int(month)))

    return sorted(periods, reverse=True)


def get_default_selected_periods(
    available_periods: Sequence[tuple[int, int]],
    today: date | None = None,
) -> list[tuple[int, int]]:
    """Return the default periods shown in the selector.

    Prefer every closed month from the current year up to the current month.
    If none are available, fall back to the current year and finally to the
    latest available period so the dashboard always opens with data selected.
    """
    normalized_periods = sorted({(int(year), int(month)) for year, month in available_periods}, reverse=True)
    if not normalized_periods:
        return []

    current_date = today or date.today()
    closed_current_year_periods = [
        (year, month)
        for year, month in normalized_periods
        if year == current_date.year and month < current_date.month
    ]
    if closed_current_year_periods:
        return closed_current_year_periods

    current_year_periods = [
        (year, month)
        for year, month in normalized_periods
        if year == current_date.year and month <= current_date.month
    ]
    if current_year_periods:
        return current_year_periods

    return normalized_periods[:1]


def filter_dataframe_by_periods(df: pd.DataFrame, selected_periods: Sequence[tuple[int, int]]) -> pd.DataFrame:
    """Filter a dataframe by a list of (year, month) pairs."""
    if df.empty or 'year' not in df.columns or 'month' not in df.columns or not selected_periods:
        return df.copy()

    selected_periods_df = pd.DataFrame(selected_periods, columns=['year', 'month']).drop_duplicates()
    return df.merge(selected_periods_df, on=['year', 'month'], how='inner')


def is_new_home_movement(movements_df: pd.DataFrame) -> pd.Series:
    """Return a boolean mask for rows categorized as New Home."""
    if movements_df.empty:
        return pd.Series(dtype=bool)
    if 'category' not in movements_df.columns:
        return pd.Series(False, index=movements_df.index)
    return movements_df['category'].apply(normalize_dimension_value).eq(NEW_HOME_CATEGORY_KEY)


def summarize_financials(movements_df: pd.DataFrame) -> dict[str, float]:
    """Return a compact financial summary for a filtered set of movements."""
    if movements_df.empty or 'amount' not in movements_df.columns:
        return {
            'income': 0.0,
            'expenses': 0.0,
            'new_home_expenses': 0.0,
            'expenses_without_new_home': 0.0,
            'balance': 0.0,
            'balance_without_new_home': 0.0,
        }

    new_home_mask = is_new_home_movement(movements_df)
    total_income = movements_df.loc[movements_df['amount'] > 0, 'amount'].sum()
    total_expenses = abs(movements_df.loc[movements_df['amount'] < 0, 'amount'].sum())
    new_home_expenses = abs(movements_df.loc[(movements_df['amount'] < 0) & new_home_mask, 'amount'].sum())
    expenses_without_new_home = abs(movements_df.loc[(movements_df['amount'] < 0) & ~new_home_mask, 'amount'].sum())
    balance = movements_df['amount'].sum()
    balance_without_new_home = movements_df.loc[~new_home_mask, 'amount'].sum()

    return {
        'income': float(total_income),
        'expenses': float(total_expenses),
        'new_home_expenses': float(new_home_expenses),
        'expenses_without_new_home': float(expenses_without_new_home),
        'balance': float(balance),
        'balance_without_new_home': float(balance_without_new_home),
    }


def build_previous_year_pairs(selected_periods: Sequence[tuple[int, int]]) -> pd.DataFrame:
    """Build the month-by-month mapping used for previous-year comparisons."""
    pairs = []
    for year, month in sorted({(int(year), int(month)) for year, month in selected_periods}):
        pairs.append({
            'selected_period': format_period(year, month),
            'previous_year_period': format_period(year - 1, month),
            'year': year,
            'month': month,
            'previous_year': year - 1,
            'previous_month': month,
        })

    return pd.DataFrame(pairs)


def get_available_account_columns(accounts_df: pd.DataFrame) -> list[str]:
    """Return the account columns currently supported and present in the file."""
    return [column for column in ACCOUNT_COLUMNS if column in accounts_df.columns]


def calculate_budget_comparison(movements_df: pd.DataFrame, budget_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare actual spending vs budget.

    Args:
        movements_df: DataFrame with movements
        budget_df: DataFrame with budget

    Returns:
        DataFrame with comparison data
    """
    if budget_df.empty:
        return pd.DataFrame()

    prepared_budget = budget_df.copy()
    prepared_movements = movements_df.copy()

    for df in (prepared_budget, prepared_movements):
        df['category_key'] = df['category'].apply(normalize_dimension_value)
        df['subcategory_key'] = df['subcategory'].apply(normalize_dimension_value)

    # Group both income and expenses so the comparison includes positive categories too.
    actual = prepared_movements.groupby(
        ['category_key', 'subcategory_key', 'month', 'year'],
        dropna=False
    ).agg(
        actual=('amount', 'sum'),
        actual_category=('category', 'first'),
        actual_subcategory=('subcategory', 'first'),
    ).reset_index()

    # Merge with budget, keeping actual-only rows too so new or uncategorized spend/income is still visible.
    comparison = pd.merge(
        prepared_budget,
        actual,
        on=['category_key', 'subcategory_key', 'month', 'year'],
        how='outer'
    )
    comparison['category'] = comparison['category'].fillna(comparison['actual_category'])
    comparison['subcategory'] = comparison['subcategory'].fillna(comparison['actual_subcategory'])
    comparison['budget'] = comparison['budget'].fillna(0)
    comparison['actual'] = comparison['actual'].fillna(0)
    comparison['budget_abs'] = comparison['budget'].abs()
    comparison['actual_abs'] = comparison['actual'].abs()
    comparison['is_income'] = comparison['category_key'].eq('income') | comparison['budget'].gt(0)

    # Expenses: positive variance means spending less than planned.
    # Income: positive variance means earning more than planned.
    comparison['difference'] = comparison['budget_abs'] - comparison['actual_abs']
    comparison.loc[comparison['is_income'], 'difference'] = (
        comparison.loc[comparison['is_income'], 'actual_abs']
        - comparison.loc[comparison['is_income'], 'budget_abs']
    )

    comparison['percentage'] = 0.0
    valid_budget = comparison['budget_abs'] > 0
    comparison.loc[valid_budget, 'percentage'] = (
        comparison.loc[valid_budget, 'actual_abs']
        / comparison.loc[valid_budget, 'budget_abs']
        * 100
    ).round(2)

    return comparison


def calculate_income_expense_summary(movements_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate income and expense summary by month and year.

    Args:
        movements_df: DataFrame with movements

    Returns:
        DataFrame with income/expense summary
    """
    if movements_df.empty:
        return pd.DataFrame()

    summary_rows = []
    for (year, month), period_df in movements_df.groupby(['year', 'month']):
        period_summary = summarize_financials(period_df)
        summary_rows.append({
            'year': int(year),
            'month': int(month),
            **period_summary,
        })

    summary = pd.DataFrame(summary_rows)

    return add_cumulative_balance_columns(summary)


def add_cumulative_balance_columns(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Recalculate cumulative balances using only the rows currently present."""
    if summary_df.empty:
        return summary_df.copy()

    summary_with_cumulative = summary_df.copy()
    summary_with_cumulative.sort_values(['year', 'month'], inplace=True)
    summary_with_cumulative['cumulative_balance'] = summary_with_cumulative['balance'].cumsum()
    summary_with_cumulative['cumulative_balance_without_new_home'] = (
        summary_with_cumulative['balance_without_new_home'].cumsum()
    )

    return summary_with_cumulative


def get_comparison_metric_options() -> dict[str, tuple[str, str]]:
    """Return the supported metric pairs for selected-vs-previous-year comparison."""
    return {
        'Income': ('current_income', 'previous_income'),
        'All expenses': ('current_expenses', 'previous_expenses'),
        'Expenses w/o New Home': (
            'current_expenses_without_new_home',
            'previous_expenses_without_new_home',
        ),
        'Balance w/o New Home': (
            'current_balance_without_new_home',
            'previous_balance_without_new_home',
        ),
        'All balance': ('current_balance', 'previous_balance'),
    }


def append_totals_row(comparison_df: pd.DataFrame, label_column: str = 'pair') -> pd.DataFrame:
    """Append a final totals row summing every numeric comparison column."""
    if comparison_df.empty:
        return comparison_df.copy()

    totals_row = {label_column: 'Total'}
    for column in comparison_df.columns:
        if column == label_column:
            continue
        if pd.api.types.is_numeric_dtype(comparison_df[column]):
            totals_row[column] = float(comparison_df[column].sum())
        else:
            totals_row[column] = ''

    return pd.concat([comparison_df, pd.DataFrame([totals_row])], ignore_index=True)


def main():
    st.set_page_config(page_title="Domestic Economy", layout="wide")

    st.title("💰 Domestic Economy Dashboard")
    st.markdown("---")

    # Check if Excel file exists
    if not EXCEL_PATH.exists():
        st.error(f"Excel file not found at: {EXCEL_PATH}")
        st.info("Please run 'poetry run python create_excel.py' to create the initial Excel file.")
        return

    # Load data
    try:
        movements_df, budget_df, accounts_df = read_all_data(str(EXCEL_PATH))
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return

    # Sidebar filters
    st.sidebar.header("📊 Filters")
    if st.sidebar.button(
        "🔄 Refresh dashboard",
        help="Reload data from economy.xlsx while keeping the current filter selections whenever possible.",
    ):
        st.sidebar.success("Dashboard refreshed from economy.xlsx")

    available_periods = build_available_periods(movements_df, budget_df, accounts_df)
    default_periods = get_default_selected_periods(available_periods)

    if available_periods:
        selected_periods = st.sidebar.multiselect(
            "Month / Year",
            options=available_periods,
            default=default_periods,
            format_func=lambda period: format_period(period[0], period[1]),
            placeholder="Choose one or more periods",
            help="Combine any month + year pair, e.g. February 2026 + March 2026.",
        )
        st.sidebar.caption("Multi-select period filter, inspired by Excel but streamlined for the dashboard.")
    else:
        selected_periods = []

    if not selected_periods:
        selected_periods = available_periods
        if available_periods:
            st.sidebar.info("No period selected, so all available periods are currently shown.")

    selected_periods = sorted({(int(year), int(month)) for year, month in selected_periods}, reverse=True)

    selected_period_labels = [format_period(year, month) for year, month in selected_periods]
    filtered_movements = filter_dataframe_by_periods(movements_df, selected_periods)
    filtered_budget = filter_dataframe_by_periods(budget_df, selected_periods)
    filtered_accounts = filter_dataframe_by_periods(accounts_df, selected_periods)

    # Main content
    if selected_period_labels:
        st.caption(f"Selected periods: {', '.join(selected_period_labels)}")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Overview",
        "💵 Budget vs Actual",
        "📊 Income & Expenses",
        "🏦 Accounts",
        "📂 Category Details",
        "📆 Previous Year Comparison",
        "📋 Data",
    ])

    # Tab 1: Overview
    with tab1:
        st.header("Financial Overview")

        if not filtered_movements.empty:
            metrics_summary = summarize_financials(filtered_movements)

            # Key metrics
            col1, col2, col3, col4 = st.columns(4)

            total_income = metrics_summary['income']
            total_expenses = metrics_summary['expenses']
            balance = metrics_summary['balance']
            savings_rate = (balance / total_income * 100) if total_income else 0

            col1.metric("Total Income", f"€{total_income:,.2f}")
            col2.metric("Total Expenses", f"€{total_expenses:,.2f}")
            col3.metric(
                "Balance",
                f"€{balance:,.2f}",
                delta=f"{savings_rate:,.1f}% of income" if total_income else "No income in selection",
            )

            # Total in accounts
            if not filtered_accounts.empty:
                account_columns = get_available_account_columns(filtered_accounts)
                valid_accounts = filtered_accounts.dropna(subset=account_columns, how='any') if account_columns else pd.DataFrame()
                if not valid_accounts.empty:
                    latest_accounts = valid_accounts.sort_values(['year', 'month'], ascending=False).iloc[0]
                    total_accounts = sum(latest_accounts[col] for col in account_columns if col in latest_accounts)
                    col4.metric("Total in Accounts", f"€{total_accounts:,.2f}")
                else:
                    col4.metric("Total in Accounts", "€0.00")
            elif not filtered_budget.empty:
                total_budget = filtered_budget['budget'].abs().sum()
                col4.metric("Total Budget", f"€{total_budget:,.2f}")

            # Expense by category pie chart
            st.subheader("Expenses by Category")
            expenses_by_cat = filtered_movements[filtered_movements['amount'] < 0].groupby('category')['amount'].sum().abs()

            if not expenses_by_cat.empty:
                fig_pie = px.pie(
                    values=expenses_by_cat.values,
                    names=expenses_by_cat.index,
                    title="Expense Distribution"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No expense data available for the selected period.")
        else:
            st.info("No movements data available for the selected periods.")

    # Tab 2: Budget vs Actual
    with tab2:
        st.header("Budget vs Actual Comparison")

        if not movements_df.empty and not budget_df.empty:
            comparison_df = calculate_budget_comparison(movements_df, budget_df)

            comparison_filtered = filter_dataframe_by_periods(comparison_df, selected_periods)

            if not comparison_filtered.empty:
                # Group by category and subcategory, summing the values
                grouped_comparison = comparison_filtered.groupby(['category', 'subcategory']).agg({
                    'budget_abs': 'sum',
                    'actual_abs': 'sum',
                    'difference': 'sum'
                }).reset_index()
                grouped_comparison.rename(columns={'budget_abs': 'budget', 'actual_abs': 'actual'}, inplace=True)

                # Recalculate percentage after grouping using absolute magnitudes.
                grouped_comparison['percentage'] = 0.0
                valid_budget = grouped_comparison['budget'] > 0
                grouped_comparison.loc[valid_budget, 'percentage'] = (
                    grouped_comparison.loc[valid_budget, 'actual']
                    / grouped_comparison.loc[valid_budget, 'budget']
                    * 100
                ).round(2)

                # Format all numeric columns to 2 decimal places for display
                display_df = grouped_comparison.copy()
                display_df['budget'] = display_df['budget'].apply(lambda x: f"€{x:,.2f}")
                display_df['actual'] = display_df['actual'].apply(lambda x: f"€{x:,.2f}")
                display_df['difference'] = display_df['difference'].apply(lambda x: f"€{x:,.2f}")
                display_df['percentage'] = display_df['percentage'].apply(lambda x: f"{x:.2f}%")

                # Function to apply color based on difference
                def color_rows(row):
                    idx = row.name
                    original_row = grouped_comparison.iloc[idx]
                    diff = original_row['difference']
                    budget = original_row['budget']
                    base = max(abs(budget), 1)

                    if diff > 0:
                        intensity = min(abs(diff) / base * 100, 100)
                        green_value = int(255 - (intensity * 1.5))
                        color = f'background-color: rgba(0, {green_value}, 0, 0.3)'
                    elif diff < 0:
                        intensity = min(abs(diff) / base * 100, 100)
                        red_value = int(255 - (intensity * 1.5))
                        color = f'background-color: rgba(255, {red_value}, {red_value}, 0.3)'
                    else:
                        # Exactly on budget - no color
                        color = 'background-color: transparent'
                    return [color] * len(row)

                # Display comparison table with styling
                styled_df = display_df[['category', 'subcategory', 'budget', 'actual', 'difference', 'percentage']].style.apply(
                    color_rows,
                    axis=1
                )

                st.dataframe(
                    styled_df,
                    use_container_width=True
                )

                # Budget vs Actual bar chart
                st.subheader("Budget vs Actual by Category")
                chart_data = grouped_comparison.groupby('category')[['budget', 'actual']].sum().reset_index()
                fig_comparison = go.Figure()
                fig_comparison.add_trace(go.Bar(
                    name='Budget',
                    x=chart_data['category'],
                    y=chart_data['budget'],
                    marker_color='lightblue'
                ))
                fig_comparison.add_trace(go.Bar(
                    name='Actual',
                    x=chart_data['category'],
                    y=chart_data['actual'],
                    marker_color='darkblue'
                ))

                fig_comparison.update_layout(
                    barmode='group',
                    title="Budget vs Actual by Category",
                    xaxis_title="Category",
                    yaxis_title="Amount (€)",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_comparison, use_container_width=True)
            else:
                st.info("No budget comparison data available for the selected period.")
        else:
            st.info("Need both movements and budget data for comparison.")

    # Tab 3: Income & Expenses
    with tab3:
        st.header("Income & Expenses Analysis")

        if not movements_df.empty:
            summary_df = calculate_income_expense_summary(movements_df)
            summary_filtered = filter_dataframe_by_periods(summary_df, selected_periods).copy()
            summary_filtered = add_cumulative_balance_columns(summary_filtered)

            if not summary_filtered.empty:
                # Display summary table
                st.subheader("Monthly Summary")
                summary_display = summary_filtered.copy()
                summary_display['period'] = summary_display.apply(
                    lambda row: format_period(row['year'], row['month']),
                    axis=1,
                )
                summary_display = summary_display[
                    [
                        'period',
                        'income',
                        'expenses',
                        'new_home_expenses',
                        'expenses_without_new_home',
                        'balance',
                        'balance_without_new_home',
                    ]
                ].rename(columns={
                    'period': 'Period',
                    'income': 'Income',
                    'expenses': 'All expenses',
                    'new_home_expenses': 'New Home expenses',
                    'expenses_without_new_home': 'Expenses w/o New Home',
                    'balance': 'All balance',
                    'balance_without_new_home': 'Balance w/o New Home',
                })
                st.dataframe(summary_display, use_container_width=True)

                # Income vs Expenses line chart
                st.subheader("Income and Expenses Trend")
                summary_filtered['period'] = summary_filtered.apply(
                    lambda row: format_period(row['year'], row['month']),
                    axis=1,
                )

                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=summary_filtered['period'],
                    y=summary_filtered['income'],
                    mode='lines+markers',
                    name='Income',
                    line=dict(color='green', width=2)
                ))
                fig_trend.add_trace(go.Scatter(
                    x=summary_filtered['period'],
                    y=summary_filtered['expenses_without_new_home'],
                    mode='lines+markers',
                    name='Expenses w/o New Home',
                    line=dict(color='red', width=2)
                ))
                fig_trend.add_trace(go.Scatter(
                    x=summary_filtered['period'],
                    y=summary_filtered['new_home_expenses'],
                    mode='lines+markers',
                    name='New Home expenses',
                    line=dict(color='orange', width=2, dash='dot')
                ))
                fig_trend.add_trace(go.Scatter(
                    x=summary_filtered['period'],
                    y=summary_filtered['expenses'],
                    mode='lines+markers',
                    name='All expenses',
                    line=dict(color='pink', width=2, dash='dash')
                ))
                fig_trend.update_layout(
                    title="Monthly income and expenses with New Home separated",
                    xaxis_title="Period",
                    yaxis_title="Amount (€)",
                    hovermode='x unified',
                )
                st.plotly_chart(fig_trend, use_container_width=True)

                # Cumulative balance
                st.subheader("Balance evolution")
                balance_chart_source = summary_filtered.melt(
                    id_vars=['period'],
                    value_vars=['cumulative_balance', 'cumulative_balance_without_new_home'],
                    var_name='series',
                    value_name='amount',
                )
                balance_chart_source['series'] = balance_chart_source['series'].map({
                    'cumulative_balance': 'All balance',
                    'cumulative_balance_without_new_home': 'Balance w/o New Home',
                })
                fig_cumulative = px.line(
                    balance_chart_source,
                    x='period',
                    y='amount',
                    color='series',
                    title="Cumulative balance with and without New Home",
                    markers=True,
                    labels={'period': 'Period', 'amount': 'Amount (€)', 'series': 'Series'},
                )
                st.plotly_chart(fig_cumulative, use_container_width=True)
            else:
                st.info("No data available for the selected periods.")
        else:
            st.info("No movements data available.")

    # Tab 4: Accounts
    with tab4:
        st.header("Accounts Overview")

        if not accounts_df.empty:
            account_columns = get_available_account_columns(accounts_df)
            valid_accounts_df = accounts_df.dropna(subset=account_columns, how='any') if account_columns else pd.DataFrame()

            if valid_accounts_df.empty:
                st.info("No valid account data available. Please add data to the Excel file.")
            else:
                filtered_accounts_view = filter_dataframe_by_periods(valid_accounts_df, selected_periods).copy()

                if filtered_accounts_view.empty:
                    st.info("No account data available for the selected periods.")
                else:
                    # Calculate total for each month
                    filtered_accounts_view['Total'] = filtered_accounts_view[account_columns].sum(axis=1)

                    # Display accounts data
                    st.subheader("Account Balances by Month")
                    st.dataframe(filtered_accounts_view, use_container_width=True)

                    # Latest balances
                    latest = filtered_accounts_view.sort_values(['year', 'month'], ascending=False).iloc[0]

                    st.subheader("Latest Balances")
                    cols = st.columns(len(account_columns) + 1)
                    for idx, col in enumerate(account_columns):
                        cols[idx].metric(col.replace('_', ' '), f"€{latest[col]:,.2f}")
                    cols[len(account_columns)].metric("Total", f"€{latest['Total']:,.2f}")

                    # Evolution of total
                    st.subheader("Total Account Evolution")
                    filtered_accounts_view['period'] = filtered_accounts_view['year'].astype(str) + '-' + filtered_accounts_view['month'].astype(str).str.zfill(2)

                    fig_total_evolution = px.line(
                        filtered_accounts_view,
                        x='period',
                        y='Total',
                        title="Total Balance Evolution",
                        markers=True,
                        labels={"Total": "Total Balance (€)", "period": "Period"}
                    )
                    fig_total_evolution.update_traces(line_color='green', line_width=3)
                    st.plotly_chart(fig_total_evolution, use_container_width=True)

                    # Individual account evolution
                    st.subheader("Individual Account Evolution")
                    fig_accounts_evolution = go.Figure()

                    for account in account_columns:
                        fig_accounts_evolution.add_trace(go.Scatter(
                            x=filtered_accounts_view['period'],
                            y=filtered_accounts_view[account],
                            mode='lines+markers',
                            name=account.replace('_', ' '),
                            line=dict(width=2)
                        ))

                    fig_accounts_evolution.update_layout(
                        title="Account Balances Over Time",
                        xaxis_title="Period",
                        yaxis_title="Balance (€)",
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_accounts_evolution, use_container_width=True)

                    # Distribution pie chart
                    st.subheader("Current Distribution")
                    latest_row = filtered_accounts_view.sort_values(['year', 'month'], ascending=False).iloc[0]
                    account_values = [latest_row[col] for col in account_columns]

                    fig_pie_accounts = px.pie(
                        values=account_values,
                        names=[col.replace('_', ' ') for col in account_columns],
                        title="Account Distribution"
                    )
                    st.plotly_chart(fig_pie_accounts, use_container_width=True)
        else:
            st.info("No accounts data available. Please add data to the Excel file.")

    # Tab 5: Category Details
    with tab5:
        st.header("Category Details")

        if not filtered_movements.empty:
            category_movements = filtered_movements.copy()

            # Get all categories (filter out NaN values before sorting)
            categories = sorted(category_movements['category'].dropna().unique())

            if categories:
                # Category selector
                selected_category = st.selectbox("Select a category to view subcategory details", options=categories)

                # Filter data by selected category
                category_data = category_movements[category_movements['category'] == selected_category].copy()
                category_data['amount_abs'] = category_data['amount'].abs()

                # Group by subcategory
                subcategory_summary = category_data.groupby('subcategory')['amount_abs'].sum().reset_index()
                subcategory_summary.sort_values('amount_abs', ascending=False, inplace=True)

                if not subcategory_summary.empty:
                    # Display total for selected category
                    total_category = subcategory_summary['amount_abs'].sum()
                    st.metric(f"Total for {selected_category}", f"€{total_category:,.2f}")

                    st.markdown("---")

                    # Create two columns for charts
                    col1, col2 = st.columns(2)

                    with col1:
                        # Bar chart with subcategory totals
                        st.subheader("Subcategory Totals (Bar Chart)")
                        fig_bar = px.bar(
                            subcategory_summary,
                            x='subcategory',
                            y='amount_abs',
                            title=f"Subcategories in {selected_category}",
                            labels={"amount_abs": "Total Amount (€)", "subcategory": "Subcategory"},
                            color='amount_abs',
                            color_continuous_scale=px.colors.sequential.Blues
                        )
                        fig_bar.update_layout(showlegend=False)
                        st.plotly_chart(fig_bar, use_container_width=True)

                    with col2:
                        # Pie chart with subcategory distribution
                        st.subheader("Subcategory Distribution (Pie Chart)")
                        fig_pie = px.pie(
                            subcategory_summary,
                            values='amount_abs',
                            names='subcategory',
                            title=f"Distribution of {selected_category}"
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)

                    # Display detailed table
                    st.subheader("Detailed Breakdown")
                    st.dataframe(
                        subcategory_summary.rename(columns={'amount_abs': 'Total Amount (€)'}),
                        use_container_width=True,
                        hide_index=True
                    )

                    # Show all transactions for this category
                    st.subheader(f"All Transactions in {selected_category}")
                    display_columns = ['date', 'subcategory', 'description', 'amount']
                    st.dataframe(
                        category_data[display_columns].sort_values('date', ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info(f"No data available for category: {selected_category}")
            else:
                st.info("No categories available for the selected period.")
        else:
            st.info("No movements data available for the selected periods.")

    # Tab 6: Previous year comparison
    with tab6:
        st.header("Previous Year Comparison")

        if filtered_movements.empty:
            st.info("No movement data available for the selected periods.")
        else:
            previous_year_pairs = build_previous_year_pairs(selected_periods)
            comparison_periods = [
                (int(row.previous_year), int(row.previous_month))
                for row in previous_year_pairs.itertuples(index=False)
            ]
            previous_year_movements = filter_dataframe_by_periods(movements_df, comparison_periods)

            st.subheader("Period mapping")
            st.dataframe(
                previous_year_pairs[['selected_period', 'previous_year_period']].rename(columns={
                    'selected_period': 'Selected period',
                    'previous_year_period': 'Compared against',
                }),
                use_container_width=True,
                hide_index=True,
            )

            available_movement_periods = set(build_available_periods(movements_df))
            missing_previous_periods = [
                format_period(year - 1, month)
                for year, month in selected_periods
                if (year - 1, month) not in available_movement_periods
            ]
            if missing_previous_periods:
                st.warning(
                    "No movement data found for these previous-year periods: "
                    + ", ".join(missing_previous_periods)
                )

            current_summary = summarize_financials(filtered_movements)
            previous_summary = summarize_financials(previous_year_movements)

            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric(
                "Income vs prev. year",
                f"€{current_summary['income']:,.2f}",
                delta=f"€{current_summary['income'] - previous_summary['income']:,.2f}",
            )
            metric_col2.metric(
                "Expenses vs prev. year",
                f"€{current_summary['expenses']:,.2f}",
                delta=f"€{current_summary['expenses'] - previous_summary['expenses']:,.2f}",
                delta_color="inverse",
            )
            metric_col3.metric(
                "Balance vs prev. year",
                f"€{current_summary['balance']:,.2f}",
                delta=f"€{current_summary['balance'] - previous_summary['balance']:,.2f}",
            )

            comparison_rows = []
            for year, month in selected_periods:
                current_period = filter_dataframe_by_periods(movements_df, [(year, month)])
                previous_period = filter_dataframe_by_periods(movements_df, [(year - 1, month)])
                current_period_summary = summarize_financials(current_period)
                previous_period_summary = summarize_financials(previous_period)
                comparison_rows.append({
                    'pair': f"{format_period(year, month)} vs {format_period(year - 1, month)}",
                    'current_income': current_period_summary['income'],
                    'previous_income': previous_period_summary['income'],
                    'current_expenses': current_period_summary['expenses'],
                    'previous_expenses': previous_period_summary['expenses'],
                    'current_new_home_expenses': current_period_summary['new_home_expenses'],
                    'previous_new_home_expenses': previous_period_summary['new_home_expenses'],
                    'current_expenses_without_new_home': current_period_summary['expenses_without_new_home'],
                    'previous_expenses_without_new_home': previous_period_summary['expenses_without_new_home'],
                    'current_balance': current_period_summary['balance'],
                    'previous_balance': previous_period_summary['balance'],
                    'current_balance_without_new_home': current_period_summary['balance_without_new_home'],
                    'previous_balance_without_new_home': previous_period_summary['balance_without_new_home'],
                })

            comparison_by_period_df = pd.DataFrame(comparison_rows)

            if not comparison_by_period_df.empty:
                st.subheader("Current selection vs previous year by period")
                comparison_metric_options = get_comparison_metric_options()
                selected_metric_label = st.selectbox(
                    "Series to compare",
                    options=list(comparison_metric_options.keys()),
                    index=0,
                )
                current_metric_column, previous_metric_column = comparison_metric_options[selected_metric_label]
                selected_metric_total = float(comparison_by_period_df[current_metric_column].sum())
                previous_metric_total = float(comparison_by_period_df[previous_metric_column].sum())

                total_col1, total_col2 = st.columns(2)
                total_col1.metric(
                    f"{selected_metric_label} total (selected)",
                    f"€{selected_metric_total:,.2f}",
                )
                total_col2.metric(
                    f"{selected_metric_label} total (previous year)",
                    f"€{previous_metric_total:,.2f}",
                    delta=f"€{selected_metric_total - previous_metric_total:,.2f}",
                    delta_color="inverse" if 'expenses' in selected_metric_label.casefold() else "normal",
                )

                chart_source = comparison_by_period_df.melt(
                    id_vars=['pair'],
                    value_vars=[
                        current_metric_column,
                        previous_metric_column,
                    ],
                    var_name='series',
                    value_name='amount',
                )
                chart_source['series'] = chart_source['series'].map({
                    current_metric_column: f'{selected_metric_label} (selected)',
                    previous_metric_column: f'{selected_metric_label} (previous year)',
                })
                fig_previous_year = px.bar(
                    chart_source,
                    x='pair',
                    y='amount',
                    color='series',
                    barmode='group',
                    title=f'{selected_metric_label} for selected periods vs the same month one year earlier',
                    labels={'pair': 'Period pair', 'amount': 'Amount (€)', 'series': 'Series'},
                )
                st.plotly_chart(fig_previous_year, use_container_width=True)

                expense_current = filtered_movements[filtered_movements['amount'] < 0].copy()
                expense_previous = previous_year_movements[previous_year_movements['amount'] < 0].copy()

                expense_current_by_category = expense_current.groupby('category')['amount'].sum().abs().reset_index(name='selected_periods')
                expense_previous_by_category = expense_previous.groupby('category')['amount'].sum().abs().reset_index(name='previous_year')
                category_year_comparison = expense_current_by_category.merge(
                    expense_previous_by_category,
                    on='category',
                    how='outer'
                ).fillna(0)

                if not category_year_comparison.empty:
                    category_chart_df = category_year_comparison.melt(
                        id_vars=['category'],
                        value_vars=['selected_periods', 'previous_year'],
                        var_name='period_group',
                        value_name='amount',
                    )
                    category_chart_df['period_group'] = category_chart_df['period_group'].map({
                        'selected_periods': 'Selected periods',
                        'previous_year': 'Previous year equivalents',
                    })
                    st.subheader("Expense comparison by category")
                    fig_category_comparison = px.bar(
                        category_chart_df,
                        x='category',
                        y='amount',
                        color='period_group',
                        barmode='group',
                        labels={'amount': 'Expenses (€)', 'period_group': 'Period set', 'category': 'Category'},
                    )
                    st.plotly_chart(fig_category_comparison, use_container_width=True)

                st.subheader("Comparison table")
                comparison_table = append_totals_row(comparison_by_period_df)
                st.dataframe(
                    comparison_table.rename(columns={
                        'pair': 'Period pair',
                        'current_income': 'Income (selected)',
                        'previous_income': 'Income (previous year)',
                        'current_expenses': 'All expenses (selected)',
                        'previous_expenses': 'All expenses (previous year)',
                        'current_new_home_expenses': 'New Home expenses (selected)',
                        'previous_new_home_expenses': 'New Home expenses (previous year)',
                        'current_expenses_without_new_home': 'Expenses w/o New Home (selected)',
                        'previous_expenses_without_new_home': 'Expenses w/o New Home (previous year)',
                        'current_balance': 'All balance (selected)',
                        'previous_balance': 'All balance (previous year)',
                        'current_balance_without_new_home': 'Balance w/o New Home (selected)',
                        'previous_balance_without_new_home': 'Balance w/o New Home (previous year)',
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

    # Tab 7: Raw Data
    with tab7:
        st.header("Raw Data")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("Movements")
            if not movements_df.empty:
                st.dataframe(movements_df, use_container_width=True)
            else:
                st.info("No movements data available.")

        with col2:
            st.subheader("Budget")
            if not budget_df.empty:
                st.dataframe(budget_df, use_container_width=True)
            else:
                st.info("No budget data available.")

        with col3:
            st.subheader("Accounts")
            if not accounts_df.empty:
                st.dataframe(accounts_df, use_container_width=True)
            else:
                st.info("No accounts data available.")


if __name__ == "__main__":
    main()
