"""Decorator pattern — XP calculator chain.

`BaseXPCalculator` returns XP by difficulty (or the chapter-quiz rate).
`FirstAttemptDecorator` adds +50% of the base XP when solved on first try.
`StreakDecorator` adds +25% of the base XP when the streak is ≥ 3 days.

Bonuses are additive against the base amount so stacking gives the formula
``final_xp = base_xp × (1 + applicable_bonuses)`` from the spec.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from apps.curriculum.models import Difficulty

BASE_XP_BY_DIFFICULTY: dict[str, int] = {
    Difficulty.EASY: 20,
    Difficulty.MEDIUM: 40,
    Difficulty.HARD: 60,
}

CHAPTER_QUIZ_XP = 100

FIRST_ATTEMPT_BONUS = 0.5
STREAK_BONUS = 0.25


@dataclass
class XPLine:
    label: str
    amount: int


class XPCalculator(ABC):
    @abstractmethod
    def calculate(self) -> int:
        ...

    @abstractmethod
    def breakdown(self) -> list[XPLine]:
        ...

    @property
    @abstractmethod
    def base_amount(self) -> int:
        ...


class BaseXPCalculator(XPCalculator):
    def __init__(self, exercise):
        if getattr(exercise, "is_chapter_quiz", False):
            self._base = CHAPTER_QUIZ_XP
            self._label = "base (chapter quiz)"
        else:
            self._base = BASE_XP_BY_DIFFICULTY.get(
                exercise.difficulty, BASE_XP_BY_DIFFICULTY[Difficulty.EASY]
            )
            self._label = f"base ({exercise.difficulty})"

    @property
    def base_amount(self) -> int:
        return self._base

    def calculate(self) -> int:
        return self._base

    def breakdown(self) -> list[XPLine]:
        return [XPLine(label=self._label, amount=self._base)]


class _XPDecorator(XPCalculator):
    def __init__(self, wrapped: XPCalculator):
        self._wrapped = wrapped

    @property
    def base_amount(self) -> int:
        return self._wrapped.base_amount


class FirstAttemptDecorator(_XPDecorator):
    def calculate(self) -> int:
        return self._wrapped.calculate() + int(self.base_amount * FIRST_ATTEMPT_BONUS)

    def breakdown(self) -> list[XPLine]:
        bonus = int(self.base_amount * FIRST_ATTEMPT_BONUS)
        return self._wrapped.breakdown() + [
            XPLine(label="first attempt (+50%)", amount=bonus)
        ]


class StreakDecorator(_XPDecorator):
    def calculate(self) -> int:
        return self._wrapped.calculate() + int(self.base_amount * STREAK_BONUS)

    def breakdown(self) -> list[XPLine]:
        bonus = int(self.base_amount * STREAK_BONUS)
        return self._wrapped.breakdown() + [
            XPLine(label="streak (+25%)", amount=bonus)
        ]


def build_calculator(
    exercise, *, first_attempt: bool, streak_days: int
) -> XPCalculator:
    calc: XPCalculator = BaseXPCalculator(exercise)
    if first_attempt:
        calc = FirstAttemptDecorator(calc)
    if streak_days >= 3:
        calc = StreakDecorator(calc)
    return calc
