import unittest
import sys
import types
from datetime import date

import pandas as pd

sys.modules.setdefault('streamlit', types.ModuleType('streamlit'))
sys.modules.setdefault('plotly', types.ModuleType('plotly'))
sys.modules.setdefault('plotly.express', types.ModuleType('plotly.express'))
sys.modules.setdefault('plotly.graph_objects', types.ModuleType('plotly.graph_objects'))

from domestic_economy.main import (
    add_cumulative_balance_columns,
    append_totals_row,
    build_previous_year_pairs,
    build_subcategory_year_comparison,
    calculate_category_previous_year_comparison,
    calculate_budget_comparison,
    calculate_income_expense_summary,
    filter_dataframe_by_periods,
    format_period,
    get_default_selected_periods,
    summarize_financials,
)


class DashboardLogicTests(unittest.TestCase):
    def test_filter_dataframe_by_periods_keeps_only_selected_month_year_pairs(self):
        df = pd.DataFrame(
            {
                'year': [2025, 2025, 2026, 2026],
                'month': [2, 3, 2, 3],
                'value': [10, 20, 30, 40],
            }
        )

        filtered = filter_dataframe_by_periods(df, [(2025, 2), (2026, 3)])

        self.assertEqual(filtered['value'].tolist(), [10, 40])

    def test_calculate_budget_comparison_uses_absolute_values_and_includes_income(self):
        movements_df = pd.DataFrame(
            [
                {'category': 'income', 'subcategory': 'Salary', 'month': 2, 'year': 2026, 'amount': 3200.0},
                {'category': 'Transport', 'subcategory': 'Fuel', 'month': 2, 'year': 2026, 'amount': -80.0},
                {'category': 'Transport', 'subcategory': 'Fuel', 'month': 3, 'year': 2026, 'amount': -120.0},
            ]
        )
        budget_df = pd.DataFrame(
            [
                {'category': 'Income', 'subcategory': 'Salary', 'month': 2, 'year': 2026, 'budget': 3000.0},
                {'category': 'Transport', 'subcategory': 'Fuel', 'month': 2, 'year': 2026, 'budget': -100.0},
                {'category': 'Transport', 'subcategory': 'Fuel', 'month': 3, 'year': 2026, 'budget': -100.0},
            ]
        )

        comparison = calculate_budget_comparison(movements_df, budget_df)

        income_row = comparison[
            (comparison['category'] == 'Income')
            & (comparison['subcategory'] == 'Salary')
            & (comparison['month'] == 2)
            & (comparison['year'] == 2026)
        ].iloc[0]
        transport_feb_row = comparison[
            (comparison['category'] == 'Transport')
            & (comparison['subcategory'] == 'Fuel')
            & (comparison['month'] == 2)
            & (comparison['year'] == 2026)
        ].iloc[0]
        transport_mar_row = comparison[
            (comparison['category'] == 'Transport')
            & (comparison['subcategory'] == 'Fuel')
            & (comparison['month'] == 3)
            & (comparison['year'] == 2026)
        ].iloc[0]

        self.assertEqual(income_row['actual_abs'], 3200.0)
        self.assertEqual(income_row['budget_abs'], 3000.0)
        self.assertEqual(income_row['difference'], 200.0)
        self.assertEqual(transport_feb_row['budget_abs'], 100.0)
        self.assertEqual(transport_feb_row['actual_abs'], 80.0)
        self.assertEqual(transport_feb_row['difference'], 20.0)
        self.assertEqual(transport_mar_row['difference'], -20.0)

    def test_build_previous_year_pairs_maps_each_selected_month_independently(self):
        pairs = build_previous_year_pairs([(2026, 3), (2025, 2)])

        expected_rows = [
            ('Febrero 2025', 'Febrero 2024'),
            ('Marzo 2026', 'Marzo 2025'),
        ]

        self.assertEqual(
            list(pairs[['selected_period', 'previous_year_period']].itertuples(index=False, name=None)),
            expected_rows,
        )
        self.assertEqual(format_period(2026, 2), 'Febrero 2026')

    def test_build_subcategory_year_comparison_orders_periods_and_compares_against_previous_year(self):
        movements_df = pd.DataFrame(
            [
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 3, 'year': 2026, 'amount': -80.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 1, 'year': 2026, 'amount': -100.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 2, 'year': 2026, 'amount': -120.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 1, 'year': 2025, 'amount': -90.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 2, 'year': 2025, 'amount': -110.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 3, 'year': 2025, 'amount': -70.0},
                {'category': 'Casa', 'subcategory': 'Varis', 'month': 1, 'year': 2026, 'amount': -30.0},
            ]
        )

        comparison = build_subcategory_year_comparison(
            movements_df,
            [(2026, 3), (2026, 1), (2026, 2)],
            'Casa',
            ['Neteja'],
        )

        self.assertEqual(comparison['period'].tolist(), ['Enero 2026', 'Febrero 2026', 'Marzo 2026'])
        self.assertEqual(comparison['current_amount'].tolist(), [100.0, 120.0, 80.0])
        self.assertEqual(comparison['previous_year_amount'].tolist(), [90.0, 110.0, 70.0])

    def test_build_subcategory_year_comparison_zero_fills_missing_selected_or_previous_periods(self):
        movements_df = pd.DataFrame(
            [
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 2, 'year': 2026, 'amount': -125.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 1, 'year': 2025, 'amount': -60.0},
            ]
        )

        comparison = build_subcategory_year_comparison(
            movements_df,
            [(2026, 1), (2026, 2)],
            'Casa',
            ['Neteja'],
        )

        self.assertEqual(comparison['current_amount'].tolist(), [0.0, 125.0])
        self.assertEqual(comparison['previous_year_amount'].tolist(), [60.0, 0.0])

    def test_build_subcategory_year_comparison_sums_multiple_selected_subcategories(self):
        movements_df = pd.DataFrame(
            [
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 1, 'year': 2026, 'amount': -100.0},
                {'category': 'Casa', 'subcategory': 'Varis', 'month': 1, 'year': 2026, 'amount': -25.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 2, 'year': 2026, 'amount': -80.0},
                {'category': 'Casa', 'subcategory': 'Varis', 'month': 2, 'year': 2026, 'amount': -35.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 1, 'year': 2025, 'amount': -70.0},
                {'category': 'Casa', 'subcategory': 'Varis', 'month': 1, 'year': 2025, 'amount': -15.0},
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 2, 'year': 2025, 'amount': -60.0},
                {'category': 'Casa', 'subcategory': 'Varis', 'month': 2, 'year': 2025, 'amount': -20.0},
                {'category': 'Casa', 'subcategory': 'Altres', 'month': 1, 'year': 2026, 'amount': -999.0},
            ]
        )

        comparison = build_subcategory_year_comparison(
            movements_df,
            [(2026, 1), (2026, 2)],
            'Casa',
            ['Varis', 'Neteja'],
        )

        self.assertEqual(comparison['current_amount'].tolist(), [125.0, 115.0])
        self.assertEqual(comparison['previous_year_amount'].tolist(), [85.0, 80.0])

    def test_calculate_category_previous_year_comparison_uses_same_selected_months(self):
        movements_df = pd.DataFrame(
            [
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 1, 'year': 2026, 'amount': -100.0},
                {'category': 'Casa', 'subcategory': 'Varis', 'month': 2, 'year': 2026, 'amount': -50.0},
                {'category': 'Casa', 'subcategory': 'Comunitat', 'month': 1, 'year': 2025, 'amount': -80.0},
                {'category': 'Casa', 'subcategory': 'Comunitat', 'month': 2, 'year': 2025, 'amount': -40.0},
                {'category': 'Casa', 'subcategory': 'Comunitat', 'month': 3, 'year': 2025, 'amount': -999.0},
                {'category': 'Transport', 'subcategory': 'Fuel', 'month': 1, 'year': 2026, 'amount': -25.0},
            ]
        )

        comparison = calculate_category_previous_year_comparison(
            movements_df,
            [(2026, 2), (2026, 1)],
            'Casa',
        )

        self.assertEqual(comparison['current_total'], 150.0)
        self.assertEqual(comparison['previous_total'], 120.0)
        self.assertEqual(comparison['difference'], 30.0)
        self.assertAlmostEqual(comparison['percentage_change'], 25.0)

    def test_calculate_category_previous_year_comparison_handles_missing_previous_total(self):
        movements_df = pd.DataFrame(
            [
                {'category': 'Casa', 'subcategory': 'Neteja', 'month': 1, 'year': 2026, 'amount': -100.0},
            ]
        )

        comparison = calculate_category_previous_year_comparison(
            movements_df,
            [(2026, 1)],
            'Casa',
        )

        self.assertEqual(comparison['current_total'], 100.0)
        self.assertEqual(comparison['previous_total'], 0.0)
        self.assertEqual(comparison['difference'], 100.0)
        self.assertIsNone(comparison['percentage_change'])

    def test_summarize_financials_separates_new_home_from_other_expenses(self):
        movements_df = pd.DataFrame(
            [
                {'category': 'Income', 'subcategory': 'Salary', 'month': 4, 'year': 2026, 'amount': 5000.0},
                {'category': 'Casa', 'subcategory': 'Supermercat', 'month': 4, 'year': 2026, 'amount': -1200.0},
                {'category': 'New Home', 'subcategory': 'Arquitecte', 'month': 4, 'year': 2026, 'amount': -3000.0},
            ]
        )

        summary = summarize_financials(movements_df)

        self.assertEqual(summary['income'], 5000.0)
        self.assertEqual(summary['expenses'], 4200.0)
        self.assertEqual(summary['new_home_expenses'], 3000.0)
        self.assertEqual(summary['expenses_without_new_home'], 1200.0)
        self.assertEqual(summary['balance'], 800.0)
        self.assertEqual(summary['balance_without_new_home'], 3800.0)

    def test_calculate_income_expense_summary_adds_new_home_aware_monthly_columns(self):
        movements_df = pd.DataFrame(
            [
                {'category': 'Income', 'subcategory': 'Salary', 'month': 3, 'year': 2026, 'amount': 4000.0},
                {'category': 'Casa', 'subcategory': 'Menjar', 'month': 3, 'year': 2026, 'amount': -1000.0},
                {'category': 'New Home', 'subcategory': 'Terreny', 'month': 3, 'year': 2026, 'amount': -500.0},
                {'category': 'Income', 'subcategory': 'Salary', 'month': 4, 'year': 2026, 'amount': 4000.0},
                {'category': 'Casa', 'subcategory': 'Menjar', 'month': 4, 'year': 2026, 'amount': -900.0},
            ]
        )

        summary = calculate_income_expense_summary(movements_df)

        march_row = summary[(summary['year'] == 2026) & (summary['month'] == 3)].iloc[0]
        april_row = summary[(summary['year'] == 2026) & (summary['month'] == 4)].iloc[0]

        self.assertEqual(march_row['new_home_expenses'], 500.0)
        self.assertEqual(march_row['expenses_without_new_home'], 1000.0)
        self.assertEqual(march_row['balance_without_new_home'], 3000.0)
        self.assertEqual(march_row['cumulative_balance'], 2500.0)
        self.assertEqual(march_row['cumulative_balance_without_new_home'], 3000.0)
        self.assertEqual(april_row['cumulative_balance'], 5600.0)
        self.assertEqual(april_row['cumulative_balance_without_new_home'], 6100.0)

    def test_add_cumulative_balance_columns_recalculates_on_filtered_rows_only(self):
        summary_df = pd.DataFrame(
            [
                {'year': 2026, 'month': 1, 'balance': 100.0, 'balance_without_new_home': 150.0},
                {'year': 2026, 'month': 2, 'balance': 200.0, 'balance_without_new_home': 250.0},
                {'year': 2026, 'month': 3, 'balance': -50.0, 'balance_without_new_home': 25.0},
            ]
        )

        filtered_summary = summary_df[summary_df['month'].isin([2, 3])]
        recalculated = add_cumulative_balance_columns(filtered_summary)

        self.assertEqual(recalculated['cumulative_balance'].tolist(), [200.0, 150.0])
        self.assertEqual(recalculated['cumulative_balance_without_new_home'].tolist(), [250.0, 275.0])

    def test_append_totals_row_adds_numeric_totals_to_comparison_table(self):
        comparison_df = pd.DataFrame(
            [
                {'pair': 'Abril 2026 vs Abril 2025', 'current_income': 10.0, 'previous_income': 7.0},
                {'pair': 'Marzo 2026 vs Marzo 2025', 'current_income': 20.0, 'previous_income': 9.0},
            ]
        )

        comparison_with_totals = append_totals_row(comparison_df)

        totals_row = comparison_with_totals.iloc[-1]
        self.assertEqual(totals_row['pair'], 'Total')
        self.assertEqual(totals_row['current_income'], 30.0)
        self.assertEqual(totals_row['previous_income'], 16.0)

    def test_get_default_selected_periods_prefers_closed_months_of_current_year(self):
        available_periods = [(2026, 4), (2026, 3), (2026, 2), (2026, 1), (2025, 12)]

        default_periods = get_default_selected_periods(available_periods, today=date(2026, 5, 3))

        self.assertEqual(default_periods, [(2026, 4), (2026, 3), (2026, 2), (2026, 1)])

    def test_get_default_selected_periods_falls_back_to_latest_available_period(self):
        available_periods = [(2025, 12), (2025, 11)]

        default_periods = get_default_selected_periods(available_periods, today=date(2026, 5, 3))

        self.assertEqual(default_periods, [(2025, 12)])


if __name__ == '__main__':
    unittest.main()


