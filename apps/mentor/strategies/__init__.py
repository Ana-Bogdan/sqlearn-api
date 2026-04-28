"""Strategy pattern — one prompt-building class per AI Mentor request kind.

The ``AIMentorService`` selects the right strategy based on the request type
and delegates prompt construction to it. Each strategy returns a
``BuiltPrompt`` (system instruction + user message + prior chat history) which
the service hands to the Gemini SDK.

This keeps prompt engineering localized: tweaking how we phrase a hint never
touches the Gemini client code, and adding a fourth request type means
writing a new strategy class — no other code changes.
"""

from .base import (
    BuiltPrompt,
    ChatMessage,
    ChatRole,
    PromptStrategy,
)
from .explain_error import ExplainErrorContext, ExplainErrorStrategy
from .hint import HintContext, HintStrategy
from .nl_to_sql import NLToSQLContext, NLToSQLStrategy

__all__ = [
    "BuiltPrompt",
    "ChatMessage",
    "ChatRole",
    "PromptStrategy",
    "ExplainErrorContext",
    "ExplainErrorStrategy",
    "HintContext",
    "HintStrategy",
    "NLToSQLContext",
    "NLToSQLStrategy",
]
