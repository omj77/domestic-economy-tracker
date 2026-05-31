import unittest

import pandas as pd

from domestic_economy.excel_utils import parse_movement_dates


class ExcelUtilsTests(unittest.TestCase):
    def test_parse_movement_dates_uses_day_first_for_string_dates(self):
        dates = pd.Series(['04/02/2026', '05/01/2026'])

        parsed = parse_movement_dates(dates)

        self.assertEqual(parsed.dt.strftime('%Y-%m-%d').tolist(), ['2026-02-04', '2026-01-05'])

    def test_parse_movement_dates_supports_mixed_string_and_timestamp_values(self):
        dates = pd.Series(['2025-03-01', pd.Timestamp('2026-06-07')])

        parsed = parse_movement_dates(dates)

        self.assertEqual(parsed.dt.strftime('%Y-%m-%d').tolist(), ['2025-03-01', '2026-06-07'])


if __name__ == '__main__':
    unittest.main()

