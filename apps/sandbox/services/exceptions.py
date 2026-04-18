class QueryTimeout(Exception):
    """Raised when a sandbox query exceeds the configured timeout."""


class QuerySyntaxError(Exception):
    """Raised when PostgreSQL reports an SQL syntax error."""


class QueryExecutionError(Exception):
    """Raised for any other PostgreSQL error during execution."""
