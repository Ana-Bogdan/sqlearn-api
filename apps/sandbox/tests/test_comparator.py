"""Unit tests for the result comparator (pure logic, no DB)."""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from apps.sandbox.services.comparator import compare_results


class CompareResultsTests(SimpleTestCase):
    def test_identical_results_are_correct(self):
        expected = {"columns": ["id", "name"], "rows": [[1, "Alice"], [2, "Bob"]]}
        actual = {"columns": ["id", "name"], "rows": [[1, "Alice"], [2, "Bob"]]}
        self.assertEqual(compare_results(expected, actual), (True, None))

    def test_column_mismatch(self):
        ok, reason = compare_results(
            {"columns": ["id"], "rows": []}, {"columns": ["name"], "rows": []}
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "columns_mismatch")

    def test_columns_compared_case_insensitively_and_trimmed(self):
        ok, _ = compare_results(
            {"columns": [" ID "], "rows": []}, {"columns": ["id"], "rows": []}
        )
        self.assertTrue(ok)

    def test_row_count_mismatch(self):
        ok, reason = compare_results(
            {"columns": ["id"], "rows": [[1]]},
            {"columns": ["id"], "rows": [[1], [2]]},
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "row_count_mismatch")

    def test_rows_mismatch(self):
        ok, reason = compare_results(
            {"columns": ["id"], "rows": [[1]]},
            {"columns": ["id"], "rows": [[2]]},
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "rows_mismatch")

    def test_row_order_ignored_by_default(self):
        ok, _ = compare_results(
            {"columns": ["id"], "rows": [[1], [2]]},
            {"columns": ["id"], "rows": [[2], [1]]},
        )
        self.assertTrue(ok)

    def test_order_matters_flag_enforces_ordering(self):
        ok, reason = compare_results(
            {"columns": ["id"], "rows": [[1], [2]], "order_matters": True},
            {"columns": ["id"], "rows": [[2], [1]]},
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "rows_mismatch")

    def test_numeric_types_are_normalized(self):
        # int vs float vs Decimal collapse onto the same canonical value.
        ok, _ = compare_results(
            {"columns": ["v"], "rows": [[1]]},
            {"columns": ["v"], "rows": [[Decimal("1.0")]]},
        )
        self.assertTrue(ok)

    def test_dates_compared_against_iso_strings(self):
        ok, _ = compare_results(
            {"columns": ["d"], "rows": [["2026-06-13"]]},
            {"columns": ["d"], "rows": [[date(2026, 6, 13)]]},
        )
        self.assertTrue(ok)

    def test_strings_are_trimmed(self):
        ok, _ = compare_results(
            {"columns": ["s"], "rows": [["hello"]]},
            {"columns": ["s"], "rows": [["  hello  "]]},
        )
        self.assertTrue(ok)

    def test_null_handling(self):
        ok, _ = compare_results(
            {"columns": ["v"], "rows": [[None]]},
            {"columns": ["v"], "rows": [[None]]},
        )
        self.assertTrue(ok)

    def test_empty_results_are_equal(self):
        self.assertEqual(compare_results({}, {}), (True, None))
