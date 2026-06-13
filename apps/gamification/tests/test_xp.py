"""Unit tests for the Decorator-based XP calculator chain."""

from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.curriculum.models import Difficulty
from apps.gamification.xp import (
    BASE_XP_BY_DIFFICULTY,
    CHAPTER_QUIZ_XP,
    BaseXPCalculator,
    FirstAttemptDecorator,
    StreakDecorator,
    build_calculator,
)


def _exercise(difficulty=Difficulty.EASY, is_chapter_quiz=False):
    return SimpleNamespace(difficulty=difficulty, is_chapter_quiz=is_chapter_quiz)


class BaseXPCalculatorTests(SimpleTestCase):
    def test_base_xp_by_difficulty(self):
        for difficulty, expected in BASE_XP_BY_DIFFICULTY.items():
            calc = BaseXPCalculator(_exercise(difficulty=difficulty))
            self.assertEqual(calc.calculate(), expected)

    def test_chapter_quiz_uses_flat_rate(self):
        calc = BaseXPCalculator(_exercise(is_chapter_quiz=True))
        self.assertEqual(calc.calculate(), CHAPTER_QUIZ_XP)
        self.assertEqual(calc.base_amount, CHAPTER_QUIZ_XP)

    def test_unknown_difficulty_falls_back_to_easy(self):
        calc = BaseXPCalculator(_exercise(difficulty="bogus"))
        self.assertEqual(calc.calculate(), BASE_XP_BY_DIFFICULTY[Difficulty.EASY])


class DecoratorTests(SimpleTestCase):
    def test_first_attempt_adds_50_percent(self):
        base = BaseXPCalculator(_exercise(difficulty=Difficulty.MEDIUM))  # 40
        calc = FirstAttemptDecorator(base)
        self.assertEqual(calc.calculate(), 40 + 20)

    def test_streak_adds_25_percent(self):
        base = BaseXPCalculator(_exercise(difficulty=Difficulty.MEDIUM))  # 40
        calc = StreakDecorator(base)
        self.assertEqual(calc.calculate(), 40 + 10)

    def test_stacked_bonuses_are_additive_on_base(self):
        # 40 base + 50% (20) + 25% (10) = 70
        calc = StreakDecorator(
            FirstAttemptDecorator(
                BaseXPCalculator(_exercise(difficulty=Difficulty.MEDIUM))
            )
        )
        self.assertEqual(calc.calculate(), 70)

    def test_breakdown_lists_each_line(self):
        calc = StreakDecorator(
            FirstAttemptDecorator(
                BaseXPCalculator(_exercise(difficulty=Difficulty.EASY))
            )
        )
        labels = [line.label for line in calc.breakdown()]
        self.assertEqual(len(labels), 3)
        self.assertIn("first attempt (+50%)", labels)
        self.assertIn("streak (+25%)", labels)


class BuildCalculatorTests(SimpleTestCase):
    def test_no_bonuses(self):
        calc = build_calculator(
            _exercise(difficulty=Difficulty.HARD), first_attempt=False, streak_days=0
        )
        self.assertEqual(calc.calculate(), 60)

    def test_first_attempt_only(self):
        calc = build_calculator(
            _exercise(difficulty=Difficulty.HARD), first_attempt=True, streak_days=2
        )
        self.assertEqual(calc.calculate(), 60 + 30)

    def test_streak_requires_three_days(self):
        below = build_calculator(
            _exercise(difficulty=Difficulty.EASY), first_attempt=False, streak_days=2
        )
        at_threshold = build_calculator(
            _exercise(difficulty=Difficulty.EASY), first_attempt=False, streak_days=3
        )
        self.assertEqual(below.calculate(), 20)
        self.assertEqual(at_threshold.calculate(), 20 + 5)

    def test_both_bonuses(self):
        calc = build_calculator(
            _exercise(difficulty=Difficulty.EASY), first_attempt=True, streak_days=5
        )
        self.assertEqual(calc.calculate(), 20 + 10 + 5)
