"""Seed chapters 1-2 of the SQLearn curriculum.

Idempotent: safe to re-run. Existing chapters are updated in place,
lesson/exercise/hint content is upserted by natural key, and sandbox
schemas are matched by name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.models import (
    Chapter,
    Difficulty,
    Exercise,
    ExerciseHint,
    Lesson,
)
from apps.sandbox.models import ExerciseDataset, SandboxSchema


# ---------------------------------------------------------------------------
# Dataset definitions
# ---------------------------------------------------------------------------

STUDENTS_SCHEMA_SQL = """
CREATE TABLE students (
    id      INTEGER PRIMARY KEY,
    name    VARCHAR(100) NOT NULL,
    age     INTEGER      NOT NULL,
    grade   VARCHAR(2)   NOT NULL
);

INSERT INTO students (id, name, age, grade) VALUES
    (1, 'Alice',   20, 'A'),
    (2, 'Bob',     22, 'B'),
    (3, 'Charlie', 19, 'A'),
    (4, 'Diana',   21, 'C'),
    (5, 'Ethan',   23, 'B');
""".strip()

BOOKS_SCHEMA_SQL = """
CREATE TABLE books (
    id     INTEGER PRIMARY KEY,
    title  VARCHAR(200) NOT NULL,
    author VARCHAR(100) NOT NULL,
    year   INTEGER      NOT NULL,
    pages  INTEGER      NOT NULL
);

INSERT INTO books (id, title, author, year, pages) VALUES
    (1, 'Database Design',     'C.J. Date',        2003, 420),
    (2, 'SQL Fundamentals',    'Joe Celko',        2014, 310),
    (3, 'The Art of SQL',      'Stephane Faroult', 2006, 376),
    (4, 'Learning PostgreSQL', 'Salahaldin Juba',  2015, 450),
    (5, 'Seven Databases',     'Eric Redmond',     2012, 352);
""".strip()

EMPLOYEES_SCHEMA_SQL = """
CREATE TABLE employees (
    id         INTEGER PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    department VARCHAR(50)  NOT NULL,
    salary     INTEGER      NOT NULL,
    hire_date  DATE         NOT NULL
);

INSERT INTO employees (id, name, department, salary, hire_date) VALUES
    (1, 'Anna Pop',     'Engineering', 75000, DATE '2020-03-15'),
    (2, 'Ben Ionescu',  'Engineering', 82000, DATE '2018-07-22'),
    (3, 'Clara Vasile', 'Marketing',   58000, DATE '2021-01-10'),
    (4, 'Dan Munteanu', 'Sales',       65000, DATE '2019-11-05'),
    (5, 'Eva Radu',     'Engineering', 95000, DATE '2017-04-18'),
    (6, 'Felix Stan',   'Marketing',   52000, DATE '2022-06-01'),
    (7, 'Gina Ene',     'Sales',       70000, DATE '2020-09-30'),
    (8, 'Horia Albu',   'HR',          48000, DATE '2023-02-14');
""".strip()

PRODUCTS_SCHEMA_SQL = """
CREATE TABLE products (
    id       INTEGER        PRIMARY KEY,
    name     VARCHAR(100)   NOT NULL,
    category VARCHAR(50)    NOT NULL,
    price    NUMERIC(8, 2)  NOT NULL,
    stock    INTEGER        NOT NULL
);

INSERT INTO products (id, name, category, price, stock) VALUES
    (1, 'Wireless Mouse', 'Electronics',  29.99, 150),
    (2, 'USB-C Cable',    'Electronics',  12.50, 300),
    (3, 'Notebook',       'Stationery',    4.99, 500),
    (4, 'Desk Lamp',      'Furniture',    45.00,  40),
    (5, 'Office Chair',   'Furniture',   189.00,  15),
    (6, 'Pen Set',        'Stationery',    8.75, 250),
    (7, 'Monitor Stand',  'Furniture',    35.50,  60),
    (8, 'Keyboard',       'Electronics',  59.99,  80),
    (9, 'Sticky Notes',   'Stationery',    3.25, 400);
""".strip()


SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "ch1_students",
        "description": "Tiny roster of students with age and grade. Used in Chapter 1.",
        "schema_sql": STUDENTS_SCHEMA_SQL,
    },
    {
        "name": "ch1_books",
        "description": "A small library catalogue for practising SELECT and FROM.",
        "schema_sql": BOOKS_SCHEMA_SQL,
    },
    {
        "name": "ch2_employees",
        "description": "Company roster with salaries and hire dates for filtering practice.",
        "schema_sql": EMPLOYEES_SCHEMA_SQL,
    },
    {
        "name": "ch2_products",
        "description": "Mini product catalogue with categories, prices, and stock levels.",
        "schema_sql": PRODUCTS_SCHEMA_SQL,
    },
]


# ---------------------------------------------------------------------------
# Curriculum structures
# ---------------------------------------------------------------------------


@dataclass
class ExerciseSpec:
    order: int
    title: str
    instructions: str
    solution_query: str
    expected_result: dict[str, Any]
    datasets: list[str]
    difficulty: str = Difficulty.EASY
    starter_code: str = ""
    hints: list[str] = field(default_factory=list)
    is_chapter_quiz: bool = False


@dataclass
class LessonSpec:
    order: int
    title: str
    theory_content: str
    exercises: list[ExerciseSpec]


@dataclass
class ChapterSpec:
    order: int
    title: str
    description: str
    lessons: list[LessonSpec]
    quiz: ExerciseSpec


def _result(columns: list[str], rows: list[list[Any]], *, ordered: bool = False) -> dict[str, Any]:
    return {"columns": columns, "rows": rows, "order_matters": ordered}


# ---------------------------------------------------------------------------
# Chapter 1 — Getting Started with Data
# ---------------------------------------------------------------------------

CH1 = ChapterSpec(
    order=1,
    title="Getting Started with Data",
    description=(
        "Meet the building blocks of SQL: databases, tables, and the two "
        "keywords you will use more than any other — SELECT and FROM."
    ),
    lessons=[
        LessonSpec(
            order=1,
            title="What is a Database?",
            theory_content=(
                "## Databases and tables\n\n"
                "A **database** is an organised collection of information. "
                "Inside a database we group related facts into **tables** — "
                "rectangular grids made of rows and columns.\n\n"
                "- Each **column** describes *one* property (for example, `name` or `age`).\n"
                "- Each **row** is one complete record (a single student, a single book).\n\n"
                "### Your first tables\n\n"
                "In this chapter you'll work with two small tables. The first is "
                "`students`, which looks like this:\n\n"
                "| id | name    | age | grade |\n"
                "|----|---------|-----|-------|\n"
                "| 1  | Alice   | 20  | A     |\n"
                "| 2  | Bob     | 22  | B     |\n\n"
                "The second is `books` — titles, authors, publication year, and page count.\n\n"
                "SQL (Structured Query Language) is how we *ask questions* of these "
                "tables. A question is called a **query**, and every query ends with "
                "a semicolon.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Meet the students table",
                    instructions=(
                        "Write a query that returns **every column** and **every row** "
                        "from the `students` table.\n\n"
                        "Tip: the shortcut for \"every column\" is the asterisk `*`."
                    ),
                    solution_query="SELECT * FROM students;",
                    expected_result=_result(
                        ["id", "name", "age", "grade"],
                        [
                            [1, "Alice", 20, "A"],
                            [2, "Bob", 22, "B"],
                            [3, "Charlie", 19, "A"],
                            [4, "Diana", 21, "C"],
                            [5, "Ethan", 23, "B"],
                        ],
                    ),
                    datasets=["ch1_students"],
                    hints=[
                        "Every SQL query starts with a verb. Here the verb is `SELECT`.",
                        "Use `*` to mean *all columns*, then tell SQL which table to look in with `FROM`.",
                        "The answer is `SELECT * FROM students;` — don't forget the semicolon.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Meet the books table",
                    instructions=(
                        "Return every column and every row from the `books` table."
                    ),
                    solution_query="SELECT * FROM books;",
                    expected_result=_result(
                        ["id", "title", "author", "year", "pages"],
                        [
                            [1, "Database Design", "C.J. Date", 2003, 420],
                            [2, "SQL Fundamentals", "Joe Celko", 2014, 310],
                            [3, "The Art of SQL", "Stephane Faroult", 2006, 376],
                            [4, "Learning PostgreSQL", "Salahaldin Juba", 2015, 450],
                            [5, "Seven Databases", "Eric Redmond", 2012, 352],
                        ],
                    ),
                    datasets=["ch1_books"],
                    hints=[
                        "Use the same pattern as the previous exercise but change the table name.",
                        "`SELECT * FROM <table>;` always pulls everything from `<table>`.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=2,
            title="SELECT Basics",
            theory_content=(
                "## Picking columns with SELECT\n\n"
                "Most of the time you don't want *every* column — you only want the "
                "ones that answer your question. SELECT lets you list the columns by name:\n\n"
                "```sql\n"
                "SELECT name FROM students;\n"
                "```\n\n"
                "You can ask for more than one column by separating the names with commas. "
                "The columns come back in the order you list them:\n\n"
                "```sql\n"
                "SELECT name, age FROM students;\n"
                "```\n\n"
                "Spelling matters: the column names must match the table exactly. "
                "If you type `SELECT nme FROM students;` PostgreSQL will refuse with "
                "an \"unknown column\" error.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Student names",
                    instructions="Return only the `name` column from `students`.",
                    solution_query="SELECT name FROM students;",
                    expected_result=_result(
                        ["name"],
                        [["Alice"], ["Bob"], ["Charlie"], ["Diana"], ["Ethan"]],
                    ),
                    datasets=["ch1_students"],
                    hints=[
                        "Replace `*` with the specific column you want.",
                        "The answer is `SELECT name FROM students;`.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Names and ages",
                    instructions=(
                        "Return the `name` and `age` of every student, in that order."
                    ),
                    solution_query="SELECT name, age FROM students;",
                    expected_result=_result(
                        ["name", "age"],
                        [
                            ["Alice", 20],
                            ["Bob", 22],
                            ["Charlie", 19],
                            ["Diana", 21],
                            ["Ethan", 23],
                        ],
                    ),
                    datasets=["ch1_students"],
                    hints=[
                        "List the two columns separated by a comma.",
                        "Order matters: write `name, age`, not `age, name`.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Titles and authors",
                    instructions="From `books`, return the `title` followed by the `author`.",
                    solution_query="SELECT title, author FROM books;",
                    expected_result=_result(
                        ["title", "author"],
                        [
                            ["Database Design", "C.J. Date"],
                            ["SQL Fundamentals", "Joe Celko"],
                            ["The Art of SQL", "Stephane Faroult"],
                            ["Learning PostgreSQL", "Salahaldin Juba"],
                            ["Seven Databases", "Eric Redmond"],
                        ],
                    ),
                    datasets=["ch1_books"],
                    hints=[
                        "The table changed, but the pattern is identical to the previous exercise.",
                        "`SELECT <col1>, <col2> FROM <table>;`",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=3,
            title="The FROM Clause",
            theory_content=(
                "## Where the data lives\n\n"
                "`SELECT` picks **which columns** you want. `FROM` tells PostgreSQL "
                "**which table** to read them from. Every query that returns data "
                "from the database needs a `FROM` clause.\n\n"
                "```sql\n"
                "SELECT title FROM books;\n"
                "--     ^^^^^      ^^^^^\n"
                "--     column     table\n"
                "```\n\n"
                "If you forget the table, PostgreSQL has no idea where to look:\n\n"
                "```sql\n"
                "SELECT title;   -- ERROR: column \"title\" does not exist\n"
                "```\n\n"
                "Table names are lowercase by convention and are written *after* "
                "`FROM` with a space between them.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Everything about books",
                    instructions="Show every column for every row in the `books` table.",
                    solution_query="SELECT * FROM books;",
                    expected_result=_result(
                        ["id", "title", "author", "year", "pages"],
                        [
                            [1, "Database Design", "C.J. Date", 2003, 420],
                            [2, "SQL Fundamentals", "Joe Celko", 2014, 310],
                            [3, "The Art of SQL", "Stephane Faroult", 2006, 376],
                            [4, "Learning PostgreSQL", "Salahaldin Juba", 2015, 450],
                            [5, "Seven Databases", "Eric Redmond", 2012, 352],
                        ],
                    ),
                    datasets=["ch1_books"],
                    hints=[
                        "Use `*` to ask for every column.",
                        "Then point `FROM` at `books`.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Just the titles",
                    instructions="Return only the `title` column from `books`.",
                    solution_query="SELECT title FROM books;",
                    expected_result=_result(
                        ["title"],
                        [
                            ["Database Design"],
                            ["SQL Fundamentals"],
                            ["The Art of SQL"],
                            ["Learning PostgreSQL"],
                            ["Seven Databases"],
                        ],
                    ),
                    datasets=["ch1_books"],
                    hints=[
                        "Swap the `*` for the column you care about.",
                        "Answer: `SELECT title FROM books;`.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=4,
            title="SELECT and FROM Together",
            theory_content=(
                "## Putting it all together\n\n"
                "Every query you've written so far follows the same two-step shape:\n\n"
                "```sql\n"
                "SELECT <columns>\n"
                "FROM   <table>;\n"
                "```\n\n"
                "- `SELECT` is the **projection** — it narrows the columns.\n"
                "- `FROM` is the **source** — it says where the rows come from.\n\n"
                "You're free to list columns in whatever order makes sense for "
                "your report. The database doesn't care, and your reader will "
                "thank you for putting the most important column first.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Student report card",
                    instructions="Show each student's `name` followed by their `grade`.",
                    solution_query="SELECT name, grade FROM students;",
                    expected_result=_result(
                        ["name", "grade"],
                        [
                            ["Alice", "A"],
                            ["Bob", "B"],
                            ["Charlie", "A"],
                            ["Diana", "C"],
                            ["Ethan", "B"],
                        ],
                    ),
                    datasets=["ch1_students"],
                    hints=[
                        "Two columns, comma-separated, same order as the prompt.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Book index",
                    instructions=(
                        "From `books`, return `title`, `author`, and `year` — in that order."
                    ),
                    solution_query="SELECT title, author, year FROM books;",
                    expected_result=_result(
                        ["title", "author", "year"],
                        [
                            ["Database Design", "C.J. Date", 2003],
                            ["SQL Fundamentals", "Joe Celko", 2014],
                            ["The Art of SQL", "Stephane Faroult", 2006],
                            ["Learning PostgreSQL", "Salahaldin Juba", 2015],
                            ["Seven Databases", "Eric Redmond", 2012],
                        ],
                    ),
                    datasets=["ch1_books"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Three columns this time.",
                        "Keep them in the requested order: title → author → year.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Age before beauty",
                    instructions=(
                        "Show each student's `age` first and then their `name`. "
                        "The prompt asks for age on the left, so lead with it."
                    ),
                    solution_query="SELECT age, name FROM students;",
                    expected_result=_result(
                        ["age", "name"],
                        [
                            [20, "Alice"],
                            [22, "Bob"],
                            [19, "Charlie"],
                            [21, "Diana"],
                            [23, "Ethan"],
                        ],
                    ),
                    datasets=["ch1_students"],
                    hints=[
                        "The order in your SELECT is the order of the result columns.",
                        "Write `age` before `name`.",
                    ],
                ),
            ],
        ),
    ],
    quiz=ExerciseSpec(
        order=100,
        title="Chapter 1 Quiz — Titles and Page Counts",
        instructions=(
            "Time to put Chapter 1 together. From the `books` table, return the "
            "`title` and the `pages` of every book — title first."
        ),
        solution_query="SELECT title, pages FROM books;",
        expected_result=_result(
            ["title", "pages"],
            [
                ["Database Design", 420],
                ["SQL Fundamentals", 310],
                ["The Art of SQL", 376],
                ["Learning PostgreSQL", 450],
                ["Seven Databases", 352],
            ],
        ),
        datasets=["ch1_books"],
        difficulty=Difficulty.MEDIUM,
        is_chapter_quiz=True,
        hints=[
            "You only need two columns from one table.",
            "Watch the order: title, then pages.",
        ],
    ),
)


# ---------------------------------------------------------------------------
# Chapter 2 — Filtering & Sorting
# ---------------------------------------------------------------------------

CH2 = ChapterSpec(
    order=2,
    title="Filtering & Sorting",
    description=(
        "Learn how to ask pointed questions: keep only the rows that matter, "
        "combine conditions with AND/OR, and put the answer in the order you want."
    ),
    lessons=[
        LessonSpec(
            order=1,
            title="Filtering with WHERE",
            theory_content=(
                "## Trimming the result\n\n"
                "A table can have thousands of rows, but you usually only care "
                "about a handful. The `WHERE` clause filters rows **before** they "
                "reach you:\n\n"
                "```sql\n"
                "SELECT name\n"
                "FROM   employees\n"
                "WHERE  department = 'Engineering';\n"
                "```\n\n"
                "A few rules to remember:\n\n"
                "- Text values go in **single quotes**: `'Engineering'`, not `\"Engineering\"`.\n"
                "- Equality uses a single `=` in SQL (not `==`).\n"
                "- Text comparison is case-sensitive: `'engineering'` won't match `'Engineering'`.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="The Engineering team",
                    instructions=(
                        "List the `name` of every employee whose `department` is "
                        "`Engineering`."
                    ),
                    solution_query=(
                        "SELECT name FROM employees WHERE department = 'Engineering';"
                    ),
                    expected_result=_result(
                        ["name"],
                        [["Anna Pop"], ["Ben Ionescu"], ["Eva Radu"]],
                    ),
                    datasets=["ch2_employees"],
                    hints=[
                        "Add a `WHERE` clause after `FROM`.",
                        "Wrap the department name in single quotes.",
                        "Final form: `WHERE department = 'Engineering'`.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Stationery aisle",
                    instructions=(
                        "From `products`, return the `name` and `price` of every "
                        "product in the `Stationery` category."
                    ),
                    solution_query=(
                        "SELECT name, price FROM products WHERE category = 'Stationery';"
                    ),
                    expected_result=_result(
                        ["name", "price"],
                        [
                            ["Notebook", 4.99],
                            ["Pen Set", 8.75],
                            ["Sticky Notes", 3.25],
                        ],
                    ),
                    datasets=["ch2_products"],
                    hints=[
                        "Two columns in SELECT, one condition in WHERE.",
                        "Category values are stored with a capital letter — match `'Stationery'`.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=2,
            title="Comparison Operators",
            theory_content=(
                "## More than just equality\n\n"
                "PostgreSQL understands the familiar comparison operators from maths:\n\n"
                "| Operator | Meaning                   |\n"
                "|----------|---------------------------|\n"
                "| `=`      | equal to                  |\n"
                "| `<>`     | not equal to (also `!=`)  |\n"
                "| `>`      | greater than              |\n"
                "| `<`      | less than                 |\n"
                "| `>=`     | greater than or equal to  |\n"
                "| `<=`     | less than or equal to     |\n\n"
                "They work on numbers, dates, and even text (alphabetical order). "
                "Dates are written as quoted strings in `YYYY-MM-DD` form:\n\n"
                "```sql\n"
                "WHERE hire_date >= '2020-01-01'\n"
                "```\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="High earners",
                    instructions=(
                        "Return the `name` and `salary` of employees earning **more "
                        "than** 70000."
                    ),
                    solution_query=(
                        "SELECT name, salary FROM employees WHERE salary > 70000;"
                    ),
                    expected_result=_result(
                        ["name", "salary"],
                        [
                            ["Anna Pop", 75000],
                            ["Ben Ionescu", 82000],
                            ["Eva Radu", 95000],
                        ],
                    ),
                    datasets=["ch2_employees"],
                    hints=[
                        "Use the `>` operator in the WHERE clause.",
                        "Numbers are written without quotes: `salary > 70000`.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Running low",
                    instructions=(
                        "From `products`, return the `name` and `stock` of every item "
                        "where the stock is **less than** 50."
                    ),
                    solution_query=(
                        "SELECT name, stock FROM products WHERE stock < 50;"
                    ),
                    expected_result=_result(
                        ["name", "stock"],
                        [["Desk Lamp", 40], ["Office Chair", 15]],
                    ),
                    datasets=["ch2_products"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "The comparison is the mirror image of the previous exercise.",
                        "Use `<` instead of `>`.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Recent hires",
                    instructions=(
                        "Return the `name` and `hire_date` of employees hired on or "
                        "after **January 1st, 2020**."
                    ),
                    solution_query=(
                        "SELECT name, hire_date FROM employees "
                        "WHERE hire_date >= '2020-01-01';"
                    ),
                    expected_result=_result(
                        ["name", "hire_date"],
                        [
                            ["Anna Pop", "2020-03-15"],
                            ["Clara Vasile", "2021-01-10"],
                            ["Felix Stan", "2022-06-01"],
                            ["Gina Ene", "2020-09-30"],
                            ["Horia Albu", "2023-02-14"],
                        ],
                    ),
                    datasets=["ch2_employees"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "\"On or after\" is the same as `>=`.",
                        "Write the date in single quotes with the format `YYYY-MM-DD`.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=3,
            title="Combining Conditions with AND / OR",
            theory_content=(
                "## Two conditions are better than one\n\n"
                "When one filter isn't enough, glue several together with "
                "`AND` and `OR`:\n\n"
                "- `AND` — **both** conditions must be true.\n"
                "- `OR`  — **at least one** condition must be true.\n"
                "- `NOT` — flips the meaning of a condition.\n\n"
                "```sql\n"
                "SELECT name\n"
                "FROM   employees\n"
                "WHERE  department = 'Engineering'\n"
                "  AND  salary > 80000;\n"
                "```\n\n"
                "When you mix `AND` and `OR`, use parentheses to make the grouping "
                "obvious — SQL evaluates `AND` before `OR`, but you shouldn't make "
                "your future self guess.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Well-paid engineers",
                    instructions=(
                        "List the `name` of employees in the `Engineering` department "
                        "who earn **at least** 80000."
                    ),
                    solution_query=(
                        "SELECT name FROM employees "
                        "WHERE department = 'Engineering' AND salary >= 80000;"
                    ),
                    expected_result=_result(
                        ["name"], [["Ben Ionescu"], ["Eva Radu"]]
                    ),
                    datasets=["ch2_employees"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Two filters joined by `AND`.",
                        "\"At least 80000\" is `>= 80000`.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Cheap or electronic",
                    instructions=(
                        "From `products`, return the `name` and `category` of every "
                        "product that is **either** in the `Electronics` category "
                        "**or** priced below 5."
                    ),
                    solution_query=(
                        "SELECT name, category FROM products "
                        "WHERE category = 'Electronics' OR price < 5;"
                    ),
                    expected_result=_result(
                        ["name", "category"],
                        [
                            ["Wireless Mouse", "Electronics"],
                            ["USB-C Cable", "Electronics"],
                            ["Notebook", "Stationery"],
                            ["Keyboard", "Electronics"],
                            ["Sticky Notes", "Stationery"],
                        ],
                    ),
                    datasets=["ch2_products"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Join the two conditions with `OR` — either one is enough.",
                        "Prices are decimals, written without quotes: `price < 5`.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=4,
            title="ORDER BY and LIMIT",
            theory_content=(
                "## Putting things in order\n\n"
                "By default PostgreSQL makes no promises about row order — it returns "
                "whatever is fastest. When you need a specific order, say so with "
                "`ORDER BY`:\n\n"
                "```sql\n"
                "SELECT name, salary\n"
                "FROM   employees\n"
                "ORDER  BY salary DESC;\n"
                "```\n\n"
                "- `ASC` means *ascending* (small → big). This is the default.\n"
                "- `DESC` means *descending* (big → small).\n\n"
                "`LIMIT` keeps only the first N rows after ordering — perfect for "
                "\"top 3\" questions:\n\n"
                "```sql\n"
                "SELECT name FROM employees ORDER BY salary DESC LIMIT 3;\n"
                "```\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Top three salaries",
                    instructions=(
                        "Return the `name` and `salary` of the **three highest-paid** "
                        "employees, highest first."
                    ),
                    solution_query=(
                        "SELECT name, salary FROM employees "
                        "ORDER BY salary DESC LIMIT 3;"
                    ),
                    expected_result=_result(
                        ["name", "salary"],
                        [
                            ["Eva Radu", 95000],
                            ["Ben Ionescu", 82000],
                            ["Anna Pop", 75000],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch2_employees"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`ORDER BY salary DESC` sorts high-to-low.",
                        "Add `LIMIT 3` to keep only the first three rows.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Cheapest first",
                    instructions=(
                        "Return the `name` of every product, sorted from the "
                        "**cheapest** to the **most expensive**."
                    ),
                    solution_query=(
                        "SELECT name FROM products ORDER BY price ASC;"
                    ),
                    expected_result=_result(
                        ["name"],
                        [
                            ["Sticky Notes"],
                            ["Notebook"],
                            ["Pen Set"],
                            ["USB-C Cable"],
                            ["Wireless Mouse"],
                            ["Monitor Stand"],
                            ["Desk Lamp"],
                            ["Keyboard"],
                            ["Office Chair"],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch2_products"],
                    hints=[
                        "Sort by `price` — ascending is the default.",
                        "You can be explicit and write `ASC` if you like.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="The newest colleagues",
                    instructions=(
                        "Return the `name` and `hire_date` of the **two most recently "
                        "hired** employees (most recent first)."
                    ),
                    solution_query=(
                        "SELECT name, hire_date FROM employees "
                        "ORDER BY hire_date DESC LIMIT 2;"
                    ),
                    expected_result=_result(
                        ["name", "hire_date"],
                        [
                            ["Horia Albu", "2023-02-14"],
                            ["Felix Stan", "2022-06-01"],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch2_employees"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "\"Most recent\" means the **largest** date — sort `DESC`.",
                        "Combine `ORDER BY hire_date DESC` with `LIMIT 2`.",
                    ],
                ),
            ],
        ),
    ],
    quiz=ExerciseSpec(
        order=100,
        title="Chapter 2 Quiz — Top Earners in Tech and Sales",
        instructions=(
            "Bring together filtering, combined conditions, and ordering. "
            "Return the `name`, `department`, and `salary` of employees in "
            "**Engineering or Sales** who earn **at least 70000**, sorted by "
            "`salary` from highest to lowest."
        ),
        solution_query=(
            "SELECT name, department, salary FROM employees "
            "WHERE (department = 'Engineering' OR department = 'Sales') "
            "AND salary >= 70000 ORDER BY salary DESC;"
        ),
        expected_result=_result(
            ["name", "department", "salary"],
            [
                ["Eva Radu", "Engineering", 95000],
                ["Ben Ionescu", "Engineering", 82000],
                ["Anna Pop", "Engineering", 75000],
                ["Gina Ene", "Sales", 70000],
            ],
            ordered=True,
        ),
        datasets=["ch2_employees"],
        difficulty=Difficulty.HARD,
        is_chapter_quiz=True,
        hints=[
            "Two departments OR-ed together, then AND-ed with a salary filter.",
            "Parentheses around the OR group keep the logic clear.",
            "Finish with `ORDER BY salary DESC`.",
        ],
    ),
)


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------


def _upsert_schema(spec: dict[str, Any]) -> SandboxSchema:
    schema, _ = SandboxSchema.objects.update_or_create(
        name=spec["name"],
        defaults={
            "description": spec["description"],
            "schema_sql": spec["schema_sql"],
            "is_playground": False,
        },
    )
    return schema


def _upsert_chapter(spec: ChapterSpec) -> Chapter:
    chapter, _ = Chapter.objects.update_or_create(
        order=spec.order,
        defaults={
            "title": spec.title,
            "description": spec.description,
            "is_active": True,
        },
    )
    return chapter


def _upsert_lesson(chapter: Chapter, spec: LessonSpec) -> Lesson:
    lesson, _ = Lesson.objects.update_or_create(
        chapter=chapter,
        order=spec.order,
        defaults={
            "title": spec.title,
            "theory_content": spec.theory_content,
            "is_active": True,
        },
    )
    return lesson


def _upsert_exercise(
    *,
    chapter: Chapter,
    lesson: Lesson | None,
    spec: ExerciseSpec,
    schemas: dict[str, SandboxSchema],
) -> Exercise:
    lookup = dict(chapter=chapter, lesson=lesson, order=spec.order)
    exercise = Exercise.objects.filter(**lookup).first()
    if exercise is None:
        exercise = Exercise(**lookup)

    exercise.title = spec.title
    exercise.instructions = spec.instructions
    exercise.difficulty = spec.difficulty
    exercise.starter_code = spec.starter_code
    exercise.solution_query = spec.solution_query
    exercise.expected_result = spec.expected_result
    exercise.is_chapter_quiz = spec.is_chapter_quiz
    exercise.is_published = True
    exercise.is_active = True
    exercise.save()

    # Hints: small lists → replace wholesale so re-ordering/edits take effect.
    ExerciseHint.objects.filter(exercise=exercise).delete()
    ExerciseHint.objects.bulk_create(
        [
            ExerciseHint(exercise=exercise, order=i, hint_text=text)
            for i, text in enumerate(spec.hints, start=1)
        ]
    )

    # Datasets: idempotent via unique (exercise, schema) constraint.
    for schema_name in spec.datasets:
        schema = schemas[schema_name]
        ExerciseDataset.objects.get_or_create(
            exercise=exercise, sandbox_schema=schema
        )

    return exercise


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed chapters 1 & 2 of the SQLearn curriculum. Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        schemas = {spec["name"]: _upsert_schema(spec) for spec in SCHEMAS}
        self.stdout.write(f"  ✓ {len(schemas)} sandbox schemas")

        for chapter_spec in (CH1, CH2):
            chapter = _upsert_chapter(chapter_spec)
            lesson_count = 0
            exercise_count = 0

            for lesson_spec in chapter_spec.lessons:
                lesson = _upsert_lesson(chapter, lesson_spec)
                lesson_count += 1
                for exercise_spec in lesson_spec.exercises:
                    _upsert_exercise(
                        chapter=chapter,
                        lesson=lesson,
                        spec=exercise_spec,
                        schemas=schemas,
                    )
                    exercise_count += 1

            _upsert_exercise(
                chapter=chapter,
                lesson=None,
                spec=chapter_spec.quiz,
                schemas=schemas,
            )
            exercise_count += 1

            self.stdout.write(
                f"  ✓ Chapter {chapter.order} — "
                f"{lesson_count} lessons, {exercise_count} exercises (incl. quiz)"
            )

        self.stdout.write(self.style.SUCCESS("Curriculum seeded."))
