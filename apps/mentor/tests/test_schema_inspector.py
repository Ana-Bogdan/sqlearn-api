"""Pure-unit tests for the DDL extraction helper."""

from django.test import SimpleTestCase

from apps.mentor.schema_inspector import extract_schema_description


class ExtractSchemaDescriptionTests(SimpleTestCase):
    def test_pulls_only_create_table_blocks(self):
        sql = """
        CREATE TABLE students (
            id INT PRIMARY KEY,
            name TEXT
        );

        INSERT INTO students VALUES (1, 'Alice');
        INSERT INTO students VALUES (2, 'Bob');

        CREATE TABLE books (
            id INT PRIMARY KEY,
            title TEXT
        );
        """
        out = extract_schema_description(sql)
        self.assertIn("CREATE TABLE students", out)
        self.assertIn("CREATE TABLE books", out)
        self.assertNotIn("INSERT", out)
        self.assertNotIn("Alice", out)

    def test_collapses_internal_whitespace(self):
        sql = "CREATE TABLE   t   (   id   INT   );"
        out = extract_schema_description(sql)
        # Multiple spaces collapse to single, but newlines may survive.
        self.assertNotIn("   ", out)

    def test_empty_input(self):
        self.assertEqual(extract_schema_description(""), "(no schema provided)")
        self.assertEqual(extract_schema_description("   \n  "), "(no schema provided)")

    def test_falls_back_to_truncated_raw_when_no_ddl_match(self):
        sql = "-- just a comment, no DDL here"
        out = extract_schema_description(sql)
        self.assertIn("just a comment", out)

    def test_truncates_very_long_fallback(self):
        sql = "x" * 5000
        out = extract_schema_description(sql)
        self.assertIn("(truncated)", out)
        self.assertLess(len(out), 2000)
