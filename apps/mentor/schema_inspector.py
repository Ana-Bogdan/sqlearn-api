"""Utility for turning a sandbox dataset into a compact prompt-ready schema.

The mentor prompts include a "schema available" block so Gemini knows what
tables and columns it can reference. Including the full ``schema_sql`` (DDL
+ all INSERTs) burns tokens and isn't structurally useful — Gemini only
needs the CREATE TABLE shape.

This module extracts just the ``CREATE TABLE ...`` blocks from a
``SandboxSchema.schema_sql`` text. If the regex misses (weird formatting,
non-DDL statements, etc.) we fall back to the raw text truncated to a safe
length so the prompt always has *something* to work with.
"""

from __future__ import annotations

import re

# Matches a CREATE TABLE block including its column definitions, up to and
# including the closing ");". Greedy on the parens-balanced body is hard
# in pure regex, so we accept any chars (DOTALL) until the first ");" — for
# the seeded SQLearn datasets this is sufficient.
_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE[^;]*?\([^;]*?\)\s*;",
    re.IGNORECASE | re.DOTALL,
)

_MAX_FALLBACK_CHARS = 1500


def extract_schema_description(schema_sql: str) -> str:
    """Return a compact human-readable schema description for prompts.

    Strategy:
    1. Pull every ``CREATE TABLE ... ();`` block from the source text.
    2. If we found at least one, join them with blank lines.
    3. Otherwise fall back to the raw text, truncated.
    """

    if not schema_sql or not schema_sql.strip():
        return "(no schema provided)"

    matches = _CREATE_TABLE_RE.findall(schema_sql)
    if matches:
        # Normalize internal whitespace so token usage is predictable.
        cleaned = []
        for ddl in matches:
            collapsed = re.sub(r"[ \t]+", " ", ddl).strip()
            cleaned.append(collapsed)
        return "\n\n".join(cleaned)

    truncated = schema_sql.strip()
    if len(truncated) > _MAX_FALLBACK_CHARS:
        truncated = truncated[:_MAX_FALLBACK_CHARS] + "\n-- (truncated)"
    return truncated


def schema_for_exercise(exercise) -> str:
    """Return a schema description for an Exercise's first dataset.

    Most exercises have exactly one ``ExerciseDataset``; if there are
    multiple we concatenate them. Returns a friendly message if none.
    """

    datasets = list(exercise.datasets.select_related("sandbox_schema").all())
    if not datasets:
        return "(this exercise has no attached dataset)"

    parts = []
    for ds in datasets:
        parts.append(
            f"-- Dataset: {ds.sandbox_schema.name}\n"
            f"{extract_schema_description(ds.sandbox_schema.schema_sql)}"
        )
    return "\n\n".join(parts)


def schema_for_playground():
    """Return a schema description for the playground sandbox.

    The free Sandbox uses the ``SandboxSchema`` row where ``is_playground``
    is True. Returns a placeholder if no playground schema is seeded yet.
    """

    from apps.sandbox.models import SandboxSchema

    playground = SandboxSchema.objects.filter(is_playground=True).first()
    if not playground:
        return "(no playground schema configured)"
    return extract_schema_description(playground.schema_sql)
