"""Pure-unit tests for the prompt strategies (no DB, no SDK)."""

from django.test import SimpleTestCase

from apps.mentor.strategies import (
    BuiltPrompt,
    ChatMessage,
    ChatRole,
    ExplainErrorContext,
    ExplainErrorStrategy,
    HintContext,
    HintStrategy,
    NLToSQLContext,
    NLToSQLStrategy,
)
from apps.mentor.strategies.base import TUTOR_PERSONA
from apps.mentor.strategies.hint import LEVEL_GUIDANCE


class ExplainErrorStrategyTests(SimpleTestCase):
    def test_includes_exercise_user_sql_and_error(self):
        ctx = ExplainErrorContext(
            exercise_title="Filter students by age",
            exercise_instructions="Return all rows where age > 20.",
            user_sql="SELECT * FORM students WHERE age > 20;",
            error_message='syntax error at or near "FORM"',
        )
        prompt = ExplainErrorStrategy(ctx).build()

        self.assertIsInstance(prompt, BuiltPrompt)
        self.assertIn(TUTOR_PERSONA, prompt.system_instruction)
        self.assertIn("Filter students by age", prompt.user_message)
        self.assertIn("FORM", prompt.user_message)  # learner SQL preserved
        self.assertIn("syntax error", prompt.user_message)
        # Strategy must NOT instruct the model to write the corrected SQL.
        self.assertIn("Do NOT write the corrected SQL", prompt.system_instruction)

    def test_history_is_carried_through(self):
        history = [
            ChatMessage(role=ChatRole.USER, content="why FORM?"),
            ChatMessage(role=ChatRole.ASSISTANT, content="typo of FROM"),
        ]
        ctx = ExplainErrorContext(
            exercise_title="t",
            exercise_instructions="i",
            user_sql="x",
            error_message="e",
            history=history,
        )
        prompt = ExplainErrorStrategy(ctx).build()
        self.assertEqual(len(prompt.history), 2)
        self.assertEqual(prompt.history[0].role, ChatRole.USER)


class HintStrategyTests(SimpleTestCase):
    def _ctx(self, level):
        return HintContext(
            exercise_title="Find expensive products",
            exercise_instructions="Return product names with price > 100.",
            schema_description="CREATE TABLE products (id, name, price);",
            user_sql="SELECT name FROM products;",
            hint_level=level,
        )

    def test_each_level_uses_correct_guidance(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                prompt = HintStrategy(self._ctx(level)).build()
                # The level-specific guidance string must appear in the system
                # instruction so the model knows how specific to be.
                self.assertIn(LEVEL_GUIDANCE[level], prompt.system_instruction)
                self.assertIn(f"level-{level}", prompt.user_message)

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            HintContext(
                exercise_title="t",
                exercise_instructions="i",
                schema_description="s",
                user_sql="",
                hint_level=4,
            )

    def test_blank_sql_shows_placeholder_block(self):
        ctx = HintContext(
            exercise_title="t",
            exercise_instructions="i",
            schema_description="s",
            user_sql="",
            hint_level=1,
        )
        prompt = HintStrategy(ctx).build()
        self.assertIn("haven't written anything yet", prompt.user_message)


class NLToSQLStrategyTests(SimpleTestCase):
    def test_builds_two_section_prompt(self):
        ctx = NLToSQLContext(
            natural_language="show me all customers from Spain",
            schema_description="CREATE TABLE customers (id, name, country);",
        )
        prompt = NLToSQLStrategy(ctx).build()

        self.assertIn("CREATE TABLE customers", prompt.user_message)
        self.assertIn("show me all customers from Spain", prompt.user_message)
        # System prompt must specify the two-section output format so we can
        # parse SQL out reliably on the FE.
        self.assertIn("```sql```", prompt.system_instruction)
        self.assertIn("Why", prompt.system_instruction)


class BaseStrategyHelpersTests(SimpleTestCase):
    def test_format_history_filters_blank(self):
        from apps.mentor.strategies.base import PromptStrategy

        cleaned = PromptStrategy._format_history(
            [
                ChatMessage(role=ChatRole.USER, content="  "),
                ChatMessage(role=ChatRole.ASSISTANT, content="real"),
            ]
        )
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0].content, "real")
