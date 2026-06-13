"""Unit tests for the level/threshold helpers."""

from django.test import SimpleTestCase

from apps.gamification.levels import (
    LEVELS,
    level_for_xp,
    next_threshold,
    threshold_for_level,
    title_for_level,
)


class LevelForXPTests(SimpleTestCase):
    def test_zero_xp_is_level_one(self):
        self.assertEqual(level_for_xp(0), 1)

    def test_just_below_threshold_stays_lower(self):
        self.assertEqual(level_for_xp(99), 1)

    def test_exact_threshold_promotes(self):
        self.assertEqual(level_for_xp(100), 2)
        self.assertEqual(level_for_xp(300), 3)

    def test_huge_xp_caps_at_max_level(self):
        self.assertEqual(level_for_xp(1_000_000), LEVELS[-1][0])


class TitleAndThresholdTests(SimpleTestCase):
    def test_title_for_level(self):
        self.assertEqual(title_for_level(1), "Row Reader")
        self.assertEqual(title_for_level(10), "Grandmaster")

    def test_title_for_unknown_level_returns_max(self):
        self.assertEqual(title_for_level(999), "Grandmaster")

    def test_threshold_for_level(self):
        self.assertEqual(threshold_for_level(1), 0)
        self.assertEqual(threshold_for_level(5), 1000)

    def test_threshold_for_unknown_level_returns_max(self):
        self.assertEqual(threshold_for_level(999), LEVELS[-1][2])


class NextThresholdTests(SimpleTestCase):
    def test_next_threshold_returns_following_level_requirement(self):
        self.assertEqual(next_threshold(1), 100)
        self.assertEqual(next_threshold(4), 1000)

    def test_next_threshold_at_max_is_none(self):
        self.assertIsNone(next_threshold(10))
