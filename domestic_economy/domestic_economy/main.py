"""
Main Streamlit application for domestic economy tracking.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add parent directory to path to import excel_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from domestic_economy.excel_utils import read_all_data

# Constants
EXCEL_PATH = Path(__file__).parent.parent / 'data' / 'economy.xlsx'


def calculate_budget_comparison(movements_df: pd.DataFrame, budget_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare actual spending vs budget.

    Args:
        movements_df: DataFrame with movements
        budget_df: DataFrame with budget

    Returns:
        DataFrame with comparison data
    """
    # Filter only expenses (negative amounts)
    expenses = movements_df[movements_df['amount'] < 0].copy()
    # Keep the negative sign - don't use abs()

    # Group by category, subcategory, month, year
    actual = expenses.groupby(['category', 'subcategory', 'month', 'year'])['amount'].sum().reset_index()
    actual.rename(columns={'amount': 'actual'}, inplace=True)

    # Merge with budget
    comparison = pd.merge(
        budget_df,
        actual,
        on=['category', 'subcategory', 'month', 'year'],
        how='left'
    )
    comparison['actual'] = comparison['actual'].fillna(0)
    # Difference: budget - |actual| (since actual is negative, we need to add it)
    # If budget is 100 and actual is -80, difference should be 100 - 80 = 20 (money saved)
    comparison['difference'] = comparison['budget'] - comparison['actual']
    comparison['percentage'] = (abs(comparison['actual']) / comparison['budget'] * 100).round(2)

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

    # Calculate income, expenses, and balance separately
    grouped = movements_df.groupby(['year', 'month'])

    summary = pd.DataFrame({
        'income': grouped['amount'].apply(lambda x: x[x > 0].sum()),
        'expenses': grouped['amount'].apply(lambda x: abs(x[x < 0].sum())),
        'balance': grouped['amount'].sum()
    }).reset_index()

    summary['cumulative_balance'] = summary['balance'].cumsum()

    return summary


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

    if not movements_df.empty:
        years = sorted(movements_df['year'].unique())
        selected_year = st.sidebar.selectbox("Year", years, index=len(years)-1 if years else 0)

        months = sorted(movements_df[movements_df['year'] == selected_year]['month'].unique())
        selected_month = st.sidebar.selectbox("Month", ['All'] + months)
    else:
        selected_year = 2024
        selected_month = 'All'

    # Main content
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Overview", "💵 Budget vs Actual", "📊 Income & Expenses", "🏦 Accounts", "📂 Category Details", "📋 Data"])

    # Tab 1: Overview
    with tab1:
        st.header("Financial Overview")

        if not movements_df.empty:
            # Filter data
            filtered_movements = movements_df[movements_df['year'] == selected_year]
            if selected_month != 'All':
                filtered_movements = filtered_movements[filtered_movements['month'] == selected_month]

            # Key metrics
            col1, col2, col3, col4 = st.columns(4)

            total_income = filtered_movements[filtered_movements['amount'] > 0]['amount'].sum()
            total_expenses = abs(filtered_movements[filtered_movements['amount'] < 0]['amount'].sum())
            balance = total_income - total_expenses

            col1.metric("Total Income", f"€{total_income:,.2f}")
            col2.metric("Total Expenses", f"€{total_expenses:,.2f}")
            col3.metric("Balance", f"€{balance:,.2f}", delta=f"€{balance:,.2f}")

            # Total in accounts
            if not accounts_df.empty:
                # Get the latest account balances (filter out rows with NaN values)
                valid_accounts = accounts_df.dropna(subset=['CX', 'BBVA', 'Inversiones', 'Plan_Pensiones'], how='any')
                if not valid_accounts.empty:
                    latest_accounts = valid_accounts.sort_values(['year', 'month'], ascending=False).iloc[0]
                    account_columns = ['CX', 'BBVA', 'Inversiones', 'Plan_Pensiones']
                    total_accounts = sum(latest_accounts[col] for col in account_columns if col in latest_accounts)
                    col4.metric("Total in Accounts", f"€{total_accounts:,.2f}")
                else:
                    col4.metric("Total in Accounts", "€0.00")
            elif not budget_df.empty:
                total_budget = budget_df[
                    (budget_df['year'] == selected_year)
                ]['budget'].sum()
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
            st.info("No movements data available. Please add data to the Excel file.")

    # Tab 2: Budget vs Actual
    with tab2:
        st.header("Budget vs Actual Comparison")

        if not movements_df.empty and not budget_df.empty:
            comparison_df = calculate_budget_comparison(movements_df, budget_df)

            # Filter by selected year
            comparison_filtered = comparison_df[comparison_df['year'] == selected_year]
            if selected_month != 'All':
                comparison_filtered = comparison_filtered[comparison_filtered['month'] == selected_month]

            if not comparison_filtered.empty:
                # Display comparison table
                st.dataframe(
                    comparison_filtered[['category', 'subcategory', 'month', 'year', 'budget', 'actual', 'difference', 'percentage']],
                    use_container_width=True
                )

                # Budget vs Actual bar chart
                st.subheader("Budget vs Actual by Category")
                fig_comparison = go.Figure()

                categories = comparison_filtered['category'].unique()
                for cat in categories:
                    cat_data = comparison_filtered[comparison_filtered['category'] == cat]
                    fig_comparison.add_trace(go.Bar(
                        name=f'{cat} - Budget',
                        x=[cat],
                        y=[cat_data['budget'].sum()],
                        marker_color='lightblue'
                    ))
                    fig_comparison.add_trace(go.Bar(
                        name=f'{cat} - Actual',
                        x=[cat],
                        y=[cat_data['actual'].sum()],
                        marker_color='darkblue'
                    ))

                fig_comparison.update_layout(barmode='group', title="Budget vs Actual Spending")
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

            # Filter by year
            summary_filtered = summary_df[summary_df['year'] == selected_year]

            if not summary_filtered.empty:
                # Display summary table
                st.subheader("Monthly Summary")
                st.dataframe(summary_filtered, use_container_width=True)

                # Income vs Expenses line chart
                st.subheader("Income vs Expenses Trend")
                summary_filtered['period'] = summary_filtered['year'].astype(str) + '-' + summary_filtered['month'].astype(str).str.zfill(2)

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
                    y=summary_filtered['expenses'],
                    mode='lines+markers',
                    name='Expenses',
                    line=dict(color='red', width=2)
                ))
                fig_trend.update_layout(title="Monthly Income vs Expenses", xaxis_title="Period", yaxis_title="Amount (€)")
                st.plotly_chart(fig_trend, use_container_width=True)

                # Cumulative balance
                st.subheader("Cumulative Balance")
                fig_cumulative = px.line(
                    summary_filtered,
                    x='period',
                    y='cumulative_balance',
                    title="Cumulative Balance Over Time",
                    markers=True
                )
                fig_cumulative.update_traces(line_color='blue', line_width=2)
                st.plotly_chart(fig_cumulative, use_container_width=True)
            else:
                st.info("No data available for the selected year.")
        else:
            st.info("No movements data available.")

    # Tab 4: Accounts
    with tab4:
        st.header("Accounts Overview")

        if not accounts_df.empty:
            # Filter out rows with NaN values first
            valid_accounts_df = accounts_df.dropna(subset=['CX', 'BBVA', 'Inversiones', 'Plan_Pensiones'], how='any')

            if valid_accounts_df.empty:
                st.info("No valid account data available. Please add data to the Excel file.")
            else:
                # Filter by selected year
                filtered_accounts = valid_accounts_df[valid_accounts_df['year'] == selected_year].copy()

                if filtered_accounts.empty:
                    st.info(f"No account data available for year {selected_year}.")
                else:
                    # Calculate total for each month
                    account_columns = ['CX', 'BBVA', 'Inversiones', 'Plan_Pensiones']
                    filtered_accounts['Total'] = filtered_accounts[account_columns].sum(axis=1)

                    # Display accounts data
                    st.subheader("Account Balances by Month")
                    st.dataframe(filtered_accounts, use_container_width=True)

                    # Latest balances
                    latest = filtered_accounts.sort_values(['year', 'month'], ascending=False).iloc[0]

                    st.subheader("Latest Balances")
                    cols = st.columns(5)
                    for idx, col in enumerate(account_columns):
                        cols[idx].metric(col.replace('_', ' '), f"€{latest[col]:,.2f}")
                    cols[4].metric("Total", f"€{latest['Total']:,.2f}")

                    # Evolution of total
                    st.subheader("Total Account Evolution")
                    filtered_accounts['period'] = filtered_accounts['year'].astype(str) + '-' + filtered_accounts['month'].astype(str).str.zfill(2)

                    fig_total_evolution = px.line(
                        filtered_accounts,
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
                            x=filtered_accounts['period'],
                            y=filtered_accounts[account],
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
                    latest_row = filtered_accounts.sort_values(['year', 'month'], ascending=False).iloc[0]
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

        if not movements_df.empty:
            # Filter by selected year and month
            filtered_movements = movements_df[movements_df['year'] == selected_year].copy()
            if selected_month != 'All':
                filtered_movements = filtered_movements[filtered_movements['month'] == selected_month]

            # Get all categories (filter out NaN values before sorting)
            categories = sorted(filtered_movements['category'].dropna().unique())

            if categories:
                # Category selector
                selected_category = st.selectbox("Select a category to view subcategory details", options=categories)

                # Filter data by selected category
                category_data = filtered_movements[filtered_movements['category'] == selected_category].copy()
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
            st.info("No movements data available. Please add data to the Excel file.")

    # Tab 6: Raw Data
    with tab6:
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
