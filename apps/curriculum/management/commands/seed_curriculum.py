"""Seed chapters 1-8 of the SQLearn curriculum.

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

ORDERS_SCHEMA_SQL = """
CREATE TABLE orders (
    id            INTEGER      PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    category      VARCHAR(50)  NOT NULL,
    quantity      INTEGER      NOT NULL,
    unit_price    NUMERIC(8,2) NOT NULL,
    order_date    DATE         NOT NULL
);

INSERT INTO orders (id, customer_name, category, quantity, unit_price, order_date) VALUES
    (1,  'Alice',   'Stationery',   3,   4.99, DATE '2024-01-05'),
    (2,  'Alice',   'Electronics',  1,  59.99, DATE '2024-01-20'),
    (3,  'Bob',     'Electronics',  2,  12.50, DATE '2024-02-11'),
    (4,  'Bob',     'Furniture',    1,  45.00, DATE '2024-02-15'),
    (5,  'Charlie', 'Furniture',    2,  35.50, DATE '2024-03-01'),
    (6,  'Charlie', 'Stationery',   5,   8.75, DATE '2024-03-02'),
    (7,  'Diana',   'Furniture',    1, 189.00, DATE '2024-03-10'),
    (8,  'Diana',   'Electronics',  2,  29.99, DATE '2024-04-01'),
    (9,  'Alice',   'Stationery',  10,   3.25, DATE '2024-04-05'),
    (10, 'Ethan',   'Electronics',  1,  82.00, DATE '2024-04-12');
""".strip()

CUSTOMERS_CH4_SCHEMA_SQL = """
CREATE TABLE customers (
    id          INTEGER       PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL,
    city        VARCHAR(100)  NOT NULL,
    country     VARCHAR(100)  NOT NULL,
    signup_year INTEGER       NOT NULL,
    phone       VARCHAR(30),
    total_spent NUMERIC(10,2) NOT NULL
);

INSERT INTO customers (id, name, city, country, signup_year, phone, total_spent) VALUES
    (1, 'Alice',   'Cluj',   'Romania', 2020, '0712-111-222', 1250.00),
    (2, 'Bob',     'London', 'UK',      2021, NULL,            850.50),
    (3, 'Charlie', 'Paris',  'France',  2020, '0601234567',   2100.00),
    (4, 'Diana',   'Cluj',   'Romania', 2022, NULL,            450.25),
    (5, 'Ethan',   'Berlin', 'Germany', 2023, '017612345',     999.99),
    (6, 'Fiona',   'Paris',  'France',  2023, NULL,             75.00),
    (7, 'George',  'London', 'UK',      2022, '07911123456',  3500.00),
    (8, 'Hana',    'Berlin', 'Germany', 2020, NULL,           1800.00);
""".strip()

ECOMMERCE_SCHEMA_SQL = """
CREATE TABLE customers (
    id      INTEGER      PRIMARY KEY,
    name    VARCHAR(100) NOT NULL,
    country VARCHAR(50)  NOT NULL
);

CREATE TABLE orders (
    id          INTEGER       PRIMARY KEY,
    customer_id INTEGER,
    order_date  DATE          NOT NULL,
    total       NUMERIC(10,2) NOT NULL
);

CREATE TABLE order_items (
    id         INTEGER       PRIMARY KEY,
    order_id   INTEGER       NOT NULL,
    product    VARCHAR(100)  NOT NULL,
    quantity   INTEGER       NOT NULL,
    unit_price NUMERIC(8,2)  NOT NULL
);

INSERT INTO customers (id, name, country) VALUES
    (1, 'Alice',   'Romania'),
    (2, 'Bob',     'UK'),
    (3, 'Charlie', 'France'),
    (4, 'Diana',   'Romania'),
    (5, 'Ethan',   'Germany');

INSERT INTO orders (id, customer_id, order_date, total) VALUES
    (101, 1,   DATE '2024-01-10',  50.00),
    (102, 1,   DATE '2024-02-15', 120.00),
    (103, 2,   DATE '2024-02-20',  35.00),
    (104, 3,   DATE '2024-03-01', 200.00),
    (105, 4,   DATE '2024-03-10',  80.00),
    (106, 999, DATE '2024-03-15',  99.00);

INSERT INTO order_items (id, order_id, product, quantity, unit_price) VALUES
    (1001, 101, 'Notebook',  10,   5.00),
    (1002, 102, 'Keyboard',   1, 120.00),
    (1003, 103, 'Mouse',      1,  35.00),
    (1004, 104, 'Monitor',    1, 200.00),
    (1005, 105, 'Desk Lamp',  2,  40.00);
""".strip()

TASKS_SCHEMA_SQL = """
CREATE TABLE tasks (
    id       INTEGER      PRIMARY KEY,
    title    VARCHAR(200) NOT NULL,
    status   VARCHAR(20)  NOT NULL,
    priority INTEGER      NOT NULL,
    assignee VARCHAR(100)
);

INSERT INTO tasks (id, title, status, priority, assignee) VALUES
    (1, 'Write spec',        'done',  1, 'Alice'),
    (2, 'Design database',   'done',  1, 'Bob'),
    (3, 'Implement API',     'doing', 2, 'Alice'),
    (4, 'Build UI',          'doing', 2, 'Charlie'),
    (5, 'Write tests',       'todo',  3, 'Bob'),
    (6, 'Deploy to staging', 'todo',  3, NULL),
    (7, 'Update changelog',  'todo',  4, 'Diana');
""".strip()

SALES_RETURNS_SCHEMA_SQL = """
CREATE TABLE sales (
    id          INTEGER       PRIMARY KEY,
    region      VARCHAR(50)   NOT NULL,
    salesperson VARCHAR(100)  NOT NULL,
    quarter     VARCHAR(10)   NOT NULL,
    amount      NUMERIC(10,2) NOT NULL
);

CREATE TABLE returns (
    id          INTEGER       PRIMARY KEY,
    region      VARCHAR(50)   NOT NULL,
    salesperson VARCHAR(100)  NOT NULL,
    quarter     VARCHAR(10)   NOT NULL,
    amount      NUMERIC(10,2) NOT NULL
);

INSERT INTO sales (id, region, salesperson, quarter, amount) VALUES
    (1,  'North', 'Alice',   'Q1', 12000),
    (2,  'North', 'Bob',     'Q1',  9000),
    (3,  'South', 'Charlie', 'Q1', 15000),
    (4,  'South', 'Diana',   'Q1',  8000),
    (5,  'North', 'Alice',   'Q2', 14000),
    (6,  'North', 'Bob',     'Q2', 11000),
    (7,  'South', 'Charlie', 'Q2', 16000),
    (8,  'South', 'Diana',   'Q2',  7000),
    (9,  'North', 'Alice',   'Q3', 13000),
    (10, 'South', 'Charlie', 'Q3', 18000);

INSERT INTO returns (id, region, salesperson, quarter, amount) VALUES
    (1, 'North', 'Alice', 'Q1', 500),
    (2, 'South', 'Diana', 'Q2', 300),
    (3, 'North', 'Bob',   'Q2', 200);
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
    {
        "name": "ch3_orders",
        "description": "Small orders ledger used to practise aggregation and grouping.",
        "schema_sql": ORDERS_SCHEMA_SQL,
    },
    {
        "name": "ch4_customers",
        "description": (
            "Customer directory with NULL phones and signup years for DISTINCT, "
            "CASE, and COALESCE practice."
        ),
        "schema_sql": CUSTOMERS_CH4_SCHEMA_SQL,
    },
    {
        "name": "ch5_ecommerce",
        "description": (
            "Three related tables — customers, orders, order_items — with one "
            "customer who has no orders and one orphan order for JOIN practice."
        ),
        "schema_sql": ECOMMERCE_SCHEMA_SQL,
    },
    {
        "name": "ch7_tasks",
        "description": "Editable task list for INSERT, UPDATE, and DELETE practice.",
        "schema_sql": TASKS_SCHEMA_SQL,
    },
    {
        "name": "ch8_sales",
        "description": (
            "Regional sales ledger with a companion returns table for window "
            "functions, UNION, and set operations."
        ),
        "schema_sql": SALES_RETURNS_SCHEMA_SQL,
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
# Chapter 3 — Working with Functions
# ---------------------------------------------------------------------------

CH3 = ChapterSpec(
    order=3,
    title="Working with Functions",
    description=(
        "Summarise data with aggregate functions, then slice those summaries "
        "by group and filter them with HAVING."
    ),
    lessons=[
        LessonSpec(
            order=1,
            title="Counting Rows with COUNT",
            theory_content=(
                "## From rows to answers\n\n"
                "So far every query you've written returned one row per row in "
                "the table. **Aggregate functions** collapse many rows into a "
                "single value — a total, an average, a count.\n\n"
                "`COUNT(*)` counts rows, regardless of their contents:\n\n"
                "```sql\n"
                "SELECT COUNT(*) FROM orders;\n"
                "```\n\n"
                "`COUNT(column)` counts only rows where `column` is not NULL, "
                "and `COUNT(DISTINCT column)` counts each unique value once.\n\n"
                "Aggregates always return a row — even an empty table produces "
                "`COUNT(*) = 0`.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="How many orders?",
                    instructions=(
                        "Count every row in the `orders` table. Return a single "
                        "row with the total count."
                    ),
                    solution_query="SELECT COUNT(*) FROM orders;",
                    expected_result=_result(["count"], [[10]]),
                    datasets=["ch3_orders"],
                    hints=[
                        "Use the aggregate `COUNT(*)` — the star means \"every row\".",
                        "`SELECT COUNT(*) FROM orders;` returns one row, one column.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="How many different customers?",
                    instructions=(
                        "Count the number of **distinct** customers who have placed "
                        "orders. Return the count only."
                    ),
                    solution_query=(
                        "SELECT COUNT(DISTINCT customer_name) FROM orders;"
                    ),
                    expected_result=_result(["count"], [[5]]),
                    datasets=["ch3_orders"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`COUNT(DISTINCT col)` removes duplicates before counting.",
                        "The column you care about is `customer_name`.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=2,
            title="SUM, AVG, MIN, MAX",
            theory_content=(
                "## The rest of the aggregate family\n\n"
                "| Function   | What it returns                          |\n"
                "|------------|------------------------------------------|\n"
                "| `SUM(col)` | the total of all non-NULL values         |\n"
                "| `AVG(col)` | the arithmetic mean of non-NULL values   |\n"
                "| `MIN(col)` | the smallest value                       |\n"
                "| `MAX(col)` | the largest value                        |\n\n"
                "Numeric averages often come back with many decimal places. "
                "Wrap them in `ROUND(value, n)` to keep the result tidy:\n\n"
                "```sql\n"
                "SELECT ROUND(AVG(unit_price), 2) FROM orders;\n"
                "```\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Total units sold",
                    instructions=(
                        "Return the **sum** of the `quantity` column across every "
                        "order in the `orders` table."
                    ),
                    solution_query="SELECT SUM(quantity) FROM orders;",
                    expected_result=_result(["sum"], [[28]]),
                    datasets=["ch3_orders"],
                    hints=[
                        "`SUM()` adds the values of a numeric column.",
                        "`SELECT SUM(quantity) FROM orders;` returns one row.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Cheapest and priciest",
                    instructions=(
                        "Return the minimum and maximum `unit_price`, in that order."
                    ),
                    solution_query=(
                        "SELECT MIN(unit_price), MAX(unit_price) FROM orders;"
                    ),
                    expected_result=_result(["min", "max"], [[3.25, 189.00]]),
                    datasets=["ch3_orders"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Two aggregates in one SELECT — separate them with a comma.",
                        "Keep the order: `MIN(unit_price), MAX(unit_price)`.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Average price, rounded",
                    instructions=(
                        "Return the **average unit price**, rounded to two decimal "
                        "places, aliased as `avg_price`."
                    ),
                    solution_query=(
                        "SELECT ROUND(AVG(unit_price), 2) AS avg_price FROM orders;"
                    ),
                    expected_result=_result(["avg_price"], [[47.10]]),
                    datasets=["ch3_orders"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Wrap `AVG(unit_price)` in `ROUND(..., 2)`.",
                        "Alias the result with `AS avg_price` so the column has a readable name.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=3,
            title="GROUP BY",
            theory_content=(
                "## One answer per group\n\n"
                "`GROUP BY` splits the table into buckets that share the same "
                "value for a column (or combination of columns). Each aggregate "
                "then runs *per bucket*:\n\n"
                "```sql\n"
                "SELECT customer_name, COUNT(*)\n"
                "FROM   orders\n"
                "GROUP  BY customer_name;\n"
                "```\n\n"
                "A crucial rule: every column in your SELECT list must either be "
                "inside an aggregate function or appear in the `GROUP BY`. "
                "Otherwise PostgreSQL can't decide which row's value to show.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Orders per customer",
                    instructions=(
                        "For each `customer_name`, return the customer and the "
                        "number of orders they've placed (column `count`)."
                    ),
                    solution_query=(
                        "SELECT customer_name, COUNT(*) FROM orders "
                        "GROUP BY customer_name;"
                    ),
                    expected_result=_result(
                        ["customer_name", "count"],
                        [
                            ["Alice", 3],
                            ["Bob", 2],
                            ["Charlie", 2],
                            ["Diana", 2],
                            ["Ethan", 1],
                        ],
                    ),
                    datasets=["ch3_orders"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Group by `customer_name`, then apply `COUNT(*)`.",
                        "The grouped column must appear in the SELECT list.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Units per category",
                    instructions=(
                        "For each `category`, return the total `quantity` sold "
                        "(alias `total_units`). Sort by `category` alphabetically."
                    ),
                    solution_query=(
                        "SELECT category, SUM(quantity) AS total_units FROM orders "
                        "GROUP BY category ORDER BY category;"
                    ),
                    expected_result=_result(
                        ["category", "total_units"],
                        [
                            ["Electronics", 6],
                            ["Furniture", 4],
                            ["Stationery", 18],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch3_orders"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Group by `category`, aggregate with `SUM(quantity)`.",
                        "Add `ORDER BY category` at the end for alphabetical order.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Revenue per customer",
                    instructions=(
                        "For each customer, compute their total revenue "
                        "(`quantity * unit_price`, summed) aliased as `revenue`. "
                        "Sort by `revenue` descending."
                    ),
                    solution_query=(
                        "SELECT customer_name, SUM(quantity * unit_price) AS revenue "
                        "FROM orders GROUP BY customer_name ORDER BY revenue DESC;"
                    ),
                    expected_result=_result(
                        ["customer_name", "revenue"],
                        [
                            ["Diana", 248.98],
                            ["Charlie", 114.75],
                            ["Alice", 107.46],
                            ["Ethan", 82.00],
                            ["Bob", 70.00],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch3_orders"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "You can aggregate an expression: `SUM(quantity * unit_price)`.",
                        "Alias the aggregate so `ORDER BY revenue DESC` can reference it.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=4,
            title="Filtering Groups with HAVING",
            theory_content=(
                "## WHERE vs HAVING\n\n"
                "`WHERE` filters rows **before** they are grouped. `HAVING` "
                "filters groups **after** the aggregates have been computed:\n\n"
                "```sql\n"
                "SELECT customer_name, COUNT(*)\n"
                "FROM   orders\n"
                "GROUP  BY customer_name\n"
                "HAVING COUNT(*) >= 2;\n"
                "```\n\n"
                "You can't use an aggregate inside `WHERE` — at the time `WHERE` "
                "runs, the groups haven't been formed yet.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Repeat customers",
                    instructions=(
                        "Return every `customer_name` with **2 or more** orders, "
                        "together with their order count. Sort by name."
                    ),
                    solution_query=(
                        "SELECT customer_name, COUNT(*) FROM orders "
                        "GROUP BY customer_name HAVING COUNT(*) >= 2 "
                        "ORDER BY customer_name;"
                    ),
                    expected_result=_result(
                        ["customer_name", "count"],
                        [
                            ["Alice", 3],
                            ["Bob", 2],
                            ["Charlie", 2],
                            ["Diana", 2],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch3_orders"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Group first, then filter the groups with `HAVING COUNT(*) >= 2`.",
                        "`HAVING` goes *after* `GROUP BY` and *before* `ORDER BY`.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Popular categories",
                    instructions=(
                        "Return each `category` whose total `quantity` sold is "
                        "**more than 5**, as `category` and `total_units`. "
                        "Sort alphabetically."
                    ),
                    solution_query=(
                        "SELECT category, SUM(quantity) AS total_units FROM orders "
                        "GROUP BY category HAVING SUM(quantity) > 5 "
                        "ORDER BY category;"
                    ),
                    expected_result=_result(
                        ["category", "total_units"],
                        [["Electronics", 6], ["Stationery", 18]],
                        ordered=True,
                    ),
                    datasets=["ch3_orders"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Same `GROUP BY` as before, but add a `HAVING SUM(quantity) > 5`.",
                        "`HAVING` can reference the aggregate directly; you don't need its alias.",
                    ],
                ),
            ],
        ),
    ],
    quiz=ExerciseSpec(
        order=100,
        title="Chapter 3 Quiz — Top Q1 Customers",
        instructions=(
            "Combine a `WHERE` with a grouped aggregate and a `HAVING`. Looking "
            "only at orders placed **before April 2024** (the first quarter), "
            "for each customer return their `customer_name` and their total "
            "revenue (`SUM(quantity * unit_price)`, rounded to 2 decimals) "
            "aliased as `total`, keeping only customers whose Q1 total is "
            "**greater than 50**. Sort by `total` from highest to lowest."
        ),
        solution_query=(
            "SELECT customer_name, ROUND(SUM(quantity * unit_price), 2) AS total "
            "FROM orders WHERE order_date < '2024-04-01' "
            "GROUP BY customer_name HAVING SUM(quantity * unit_price) > 50 "
            "ORDER BY total DESC;"
        ),
        expected_result=_result(
            ["customer_name", "total"],
            [
                ["Diana", 189.00],
                ["Charlie", 114.75],
                ["Alice", 74.96],
                ["Bob", 70.00],
            ],
            ordered=True,
        ),
        datasets=["ch3_orders"],
        difficulty=Difficulty.HARD,
        is_chapter_quiz=True,
        hints=[
            "Start with `WHERE order_date < '2024-04-01'` so only Q1 rows reach the groups.",
            "Group by customer_name and aggregate `SUM(quantity * unit_price)`.",
            "Filter groups with `HAVING SUM(quantity * unit_price) > 50`, then order.",
        ],
    ),
)


# ---------------------------------------------------------------------------
# Chapter 4 — Shaping Your Results
# ---------------------------------------------------------------------------

CH4 = ChapterSpec(
    order=4,
    title="Shaping Your Results",
    description=(
        "Reshape query output: remove duplicates with DISTINCT, rename columns "
        "with aliases, branch on conditions with CASE, and keep NULLs from "
        "leaking into your reports with COALESCE."
    ),
    lessons=[
        LessonSpec(
            order=1,
            title="Removing Duplicates with DISTINCT",
            theory_content=(
                "## Unique values only\n\n"
                "`DISTINCT` sits immediately after `SELECT` and collapses rows "
                "that are identical across the selected columns:\n\n"
                "```sql\n"
                "SELECT DISTINCT country FROM customers;\n"
                "```\n\n"
                "It applies to the **whole row** in the result, so "
                "`SELECT DISTINCT country, signup_year` returns one row per "
                "unique *pair* of country + year.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Which countries?",
                    instructions=(
                        "Return the distinct list of `country` values from "
                        "`customers`, sorted alphabetically."
                    ),
                    solution_query=(
                        "SELECT DISTINCT country FROM customers ORDER BY country;"
                    ),
                    expected_result=_result(
                        ["country"],
                        [["France"], ["Germany"], ["Romania"], ["UK"]],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    hints=[
                        "Use `SELECT DISTINCT country` to drop duplicate countries.",
                        "Finish with `ORDER BY country` for alphabetical order.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Cities we serve",
                    instructions=(
                        "Return the distinct list of `city` values from "
                        "`customers`, sorted alphabetically."
                    ),
                    solution_query=(
                        "SELECT DISTINCT city FROM customers ORDER BY city;"
                    ),
                    expected_result=_result(
                        ["city"],
                        [["Berlin"], ["Cluj"], ["London"], ["Paris"]],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    hints=[
                        "Swap `country` for `city` in the previous pattern.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Country / signup pairs",
                    instructions=(
                        "Return each distinct combination of `country` and "
                        "`signup_year`, sorted by `country` then `signup_year`."
                    ),
                    solution_query=(
                        "SELECT DISTINCT country, signup_year FROM customers "
                        "ORDER BY country, signup_year;"
                    ),
                    expected_result=_result(
                        ["country", "signup_year"],
                        [
                            ["France", 2020],
                            ["France", 2023],
                            ["Germany", 2020],
                            ["Germany", 2023],
                            ["Romania", 2020],
                            ["Romania", 2022],
                            ["UK", 2021],
                            ["UK", 2022],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`DISTINCT` applies to every selected column taken together.",
                        "`ORDER BY country, signup_year` makes the secondary sort explicit.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=2,
            title="Column Aliases",
            theory_content=(
                "## Naming your output\n\n"
                "An alias renames a column in the *result set* — useful for "
                "readability and for referring to computed values later in the "
                "query (e.g. `ORDER BY`). The keyword is `AS`, but it is "
                "optional:\n\n"
                "```sql\n"
                "SELECT name AS customer, total_spent / 1000 AS thousands\n"
                "FROM   customers;\n"
                "```\n\n"
                "Aliases apply only to the result; the table's real column "
                "names don't change.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Rename for a report",
                    instructions=(
                        "From `customers`, return `name` as `customer` and `city` "
                        "as `hometown`. Sort by `id` ascending."
                    ),
                    solution_query=(
                        "SELECT name AS customer, city AS hometown FROM customers "
                        "ORDER BY id;"
                    ),
                    expected_result=_result(
                        ["customer", "hometown"],
                        [
                            ["Alice", "Cluj"],
                            ["Bob", "London"],
                            ["Charlie", "Paris"],
                            ["Diana", "Cluj"],
                            ["Ethan", "Berlin"],
                            ["Fiona", "Paris"],
                            ["George", "London"],
                            ["Hana", "Berlin"],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    hints=[
                        "`col AS alias` renames a column in the output.",
                        "You can sort by the real column (`id`) even though it's not in SELECT.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Spending in thousands",
                    instructions=(
                        "Return each customer's `name` and their `total_spent` "
                        "converted to thousands (`total_spent / 1000`), rounded "
                        "to 2 decimals, aliased as `thousands`. Sort by `name`."
                    ),
                    solution_query=(
                        "SELECT name, ROUND(total_spent / 1000, 2) AS thousands "
                        "FROM customers ORDER BY name;"
                    ),
                    expected_result=_result(
                        ["name", "thousands"],
                        [
                            ["Alice", 1.25],
                            ["Bob", 0.85],
                            ["Charlie", 2.10],
                            ["Diana", 0.45],
                            ["Ethan", 1.00],
                            ["Fiona", 0.08],
                            ["George", 3.50],
                            ["Hana", 1.80],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Compute the value, then wrap it in `ROUND(..., 2)`.",
                        "Alias the computed column with `AS thousands`.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=3,
            title="Branching with CASE WHEN",
            theory_content=(
                "## if/else inside a query\n\n"
                "`CASE` lets you return different values depending on a "
                "condition. The most flexible form is the **searched** CASE:\n\n"
                "```sql\n"
                "SELECT name,\n"
                "       CASE\n"
                "           WHEN total_spent >= 1500 THEN 'VIP'\n"
                "           ELSE 'Regular'\n"
                "       END AS tier\n"
                "FROM   customers;\n"
                "```\n\n"
                "`WHEN` clauses are checked top to bottom; the first one that "
                "matches wins. Always alias the CASE expression — otherwise the "
                "column name defaults to a generic `case`.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="VIP or Regular?",
                    instructions=(
                        "For each customer, return their `name` and a column "
                        "`tier` that is `'VIP'` when `total_spent` is at least "
                        "1500 and `'Regular'` otherwise. Sort by `name`."
                    ),
                    solution_query=(
                        "SELECT name, CASE WHEN total_spent >= 1500 THEN 'VIP' "
                        "ELSE 'Regular' END AS tier FROM customers ORDER BY name;"
                    ),
                    expected_result=_result(
                        ["name", "tier"],
                        [
                            ["Alice", "Regular"],
                            ["Bob", "Regular"],
                            ["Charlie", "VIP"],
                            ["Diana", "Regular"],
                            ["Ethan", "Regular"],
                            ["Fiona", "Regular"],
                            ["George", "VIP"],
                            ["Hana", "VIP"],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "One WHEN, one ELSE, wrapped in `CASE ... END`.",
                        "Don't forget `AS tier` to name the column.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Gold, Silver, Bronze",
                    instructions=(
                        "Return `name` and a column `tier` with three levels: "
                        "`'Gold'` for `total_spent >= 2000`, `'Silver'` for "
                        "`total_spent >= 1000`, and `'Bronze'` otherwise. "
                        "Sort by `name`."
                    ),
                    solution_query=(
                        "SELECT name, CASE "
                        "WHEN total_spent >= 2000 THEN 'Gold' "
                        "WHEN total_spent >= 1000 THEN 'Silver' "
                        "ELSE 'Bronze' END AS tier "
                        "FROM customers ORDER BY name;"
                    ),
                    expected_result=_result(
                        ["name", "tier"],
                        [
                            ["Alice", "Silver"],
                            ["Bob", "Bronze"],
                            ["Charlie", "Gold"],
                            ["Diana", "Bronze"],
                            ["Ethan", "Bronze"],
                            ["Fiona", "Bronze"],
                            ["George", "Gold"],
                            ["Hana", "Silver"],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Three WHEN branches are evaluated top-down — put the "
                        "strictest (`>= 2000`) first.",
                        "`ELSE 'Bronze'` catches everything that didn't match.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=4,
            title="Handling NULL with COALESCE",
            theory_content=(
                "## Fill-in values for missing data\n\n"
                "`NULL` means \"unknown\" — it isn't zero, isn't an empty "
                "string, and comparing it with `=` always yields `NULL`. "
                "`COALESCE(a, b, c, ...)` returns the first non-NULL argument, "
                "so it's the easiest way to substitute a default:\n\n"
                "```sql\n"
                "SELECT COALESCE(phone, 'no phone') AS phone FROM customers;\n"
                "```\n\n"
                "You can pass as many fallbacks as you like; evaluation stops "
                "at the first non-NULL value.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Phone or placeholder",
                    instructions=(
                        "Return `name` and a column `phone` that shows the real "
                        "phone number or the text `'unknown'` when it is NULL. "
                        "Sort by `id` ascending."
                    ),
                    solution_query=(
                        "SELECT name, COALESCE(phone, 'unknown') AS phone "
                        "FROM customers ORDER BY id;"
                    ),
                    expected_result=_result(
                        ["name", "phone"],
                        [
                            ["Alice", "0712-111-222"],
                            ["Bob", "unknown"],
                            ["Charlie", "0601234567"],
                            ["Diana", "unknown"],
                            ["Ethan", "017612345"],
                            ["Fiona", "unknown"],
                            ["George", "07911123456"],
                            ["Hana", "unknown"],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Wrap the `phone` column in `COALESCE(phone, 'unknown')`.",
                        "Alias the result back to `phone` so the column name stays familiar.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Has a phone on file?",
                    instructions=(
                        "Return `name` and a column `has_phone` that reads "
                        "`'yes'` when `phone` is set and `'no'` when it is NULL. "
                        "Sort by `name`."
                    ),
                    solution_query=(
                        "SELECT name, CASE WHEN phone IS NULL THEN 'no' "
                        "ELSE 'yes' END AS has_phone FROM customers ORDER BY name;"
                    ),
                    expected_result=_result(
                        ["name", "has_phone"],
                        [
                            ["Alice", "yes"],
                            ["Bob", "no"],
                            ["Charlie", "yes"],
                            ["Diana", "no"],
                            ["Ethan", "yes"],
                            ["Fiona", "no"],
                            ["George", "yes"],
                            ["Hana", "no"],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch4_customers"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Test NULL with `IS NULL`, not `= NULL`.",
                        "`CASE WHEN phone IS NULL THEN 'no' ELSE 'yes' END`.",
                    ],
                ),
            ],
        ),
    ],
    quiz=ExerciseSpec(
        order=100,
        title="Chapter 4 Quiz — Customer Directory",
        instructions=(
            "Build a compact customer directory. For each row return: `name`, "
            "a `tier` column (`'Gold'` for `total_spent >= 2000`, `'Silver'` "
            "for `>= 1000`, `'Bronze'` otherwise), and a `phone` column that "
            "shows the actual phone number or `'no phone'` when it is NULL. "
            "Sort by `name` ascending."
        ),
        solution_query=(
            "SELECT name, "
            "CASE WHEN total_spent >= 2000 THEN 'Gold' "
            "WHEN total_spent >= 1000 THEN 'Silver' "
            "ELSE 'Bronze' END AS tier, "
            "COALESCE(phone, 'no phone') AS phone "
            "FROM customers ORDER BY name;"
        ),
        expected_result=_result(
            ["name", "tier", "phone"],
            [
                ["Alice", "Silver", "0712-111-222"],
                ["Bob", "Bronze", "no phone"],
                ["Charlie", "Gold", "0601234567"],
                ["Diana", "Bronze", "no phone"],
                ["Ethan", "Bronze", "017612345"],
                ["Fiona", "Bronze", "no phone"],
                ["George", "Gold", "07911123456"],
                ["Hana", "Silver", "no phone"],
            ],
            ordered=True,
        ),
        datasets=["ch4_customers"],
        difficulty=Difficulty.HARD,
        is_chapter_quiz=True,
        hints=[
            "Three expressions in SELECT: `name`, a CASE block, a COALESCE.",
            "Put the strictest tier threshold (`>= 2000`) first in the CASE.",
            "Alias the tier column as `tier` and the phone column as `phone`.",
        ],
    ),
)


# ---------------------------------------------------------------------------
# Chapter 5 — Combining Tables
# ---------------------------------------------------------------------------

CH5 = ChapterSpec(
    order=5,
    title="Combining Tables",
    description=(
        "Bring related tables together with JOINs. Start with INNER JOIN, then "
        "meet the outer variants that keep unmatched rows on one or both sides."
    ),
    lessons=[
        LessonSpec(
            order=1,
            title="INNER JOIN",
            theory_content=(
                "## Matching rows across tables\n\n"
                "`INNER JOIN` (often written just `JOIN`) keeps only the rows "
                "that have a match in **both** tables, based on a join "
                "condition:\n\n"
                "```sql\n"
                "SELECT c.name, o.order_date\n"
                "FROM   customers AS c\n"
                "INNER  JOIN orders AS o ON c.id = o.customer_id;\n"
                "```\n\n"
                "Table aliases (`c`, `o`) keep the query readable. Qualify "
                "column names with their alias (`c.name`, `o.order_date`) "
                "whenever the same name exists in multiple tables.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Customers with orders",
                    instructions=(
                        "List every order together with the customer who placed "
                        "it. Return `name`, `order_date`, and `total`, sorted by "
                        "order `id`."
                    ),
                    solution_query=(
                        "SELECT c.name, o.order_date, o.total "
                        "FROM customers c INNER JOIN orders o "
                        "ON c.id = o.customer_id ORDER BY o.id;"
                    ),
                    expected_result=_result(
                        ["name", "order_date", "total"],
                        [
                            ["Alice", "2024-01-10", 50.00],
                            ["Alice", "2024-02-15", 120.00],
                            ["Bob", "2024-02-20", 35.00],
                            ["Charlie", "2024-03-01", 200.00],
                            ["Diana", "2024-03-10", 80.00],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Join the two tables on `c.id = o.customer_id`.",
                        "The orphan order (customer_id = 999) and the customer with no orders both drop out of an INNER JOIN.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Three-table join",
                    instructions=(
                        "Join `customers`, `orders`, and `order_items` so each "
                        "row shows the customer's `name`, the `product`, and "
                        "the `quantity`. Sort by order_items `id`."
                    ),
                    solution_query=(
                        "SELECT c.name, oi.product, oi.quantity "
                        "FROM customers c "
                        "INNER JOIN orders o ON c.id = o.customer_id "
                        "INNER JOIN order_items oi ON o.id = oi.order_id "
                        "ORDER BY oi.id;"
                    ),
                    expected_result=_result(
                        ["name", "product", "quantity"],
                        [
                            ["Alice", "Notebook", 10],
                            ["Alice", "Keyboard", 1],
                            ["Bob", "Mouse", 1],
                            ["Charlie", "Monitor", 1],
                            ["Diana", "Desk Lamp", 2],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Chain two INNER JOINs: customers → orders → order_items.",
                        "Each JOIN needs its own `ON` condition tying the id columns together.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=2,
            title="LEFT JOIN",
            theory_content=(
                "## Keep every row on the left\n\n"
                "A `LEFT JOIN` keeps **every row** from the left table; when "
                "there is no match on the right, NULLs fill in:\n\n"
                "```sql\n"
                "SELECT c.name, o.id\n"
                "FROM   customers c\n"
                "LEFT   JOIN orders o ON c.id = o.customer_id;\n"
                "```\n\n"
                "That makes LEFT JOIN ideal for \"show me everyone, including "
                "those who haven't done X yet\" questions.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Orders per customer (including zero)",
                    instructions=(
                        "Return every `customer_name` and the number of orders "
                        "they've placed — customers with no orders should show "
                        "`0`. Alias the count as `order_count` and sort by name."
                    ),
                    solution_query=(
                        "SELECT c.name AS customer_name, "
                        "COUNT(o.id) AS order_count "
                        "FROM customers c LEFT JOIN orders o "
                        "ON c.id = o.customer_id "
                        "GROUP BY c.name ORDER BY c.name;"
                    ),
                    expected_result=_result(
                        ["customer_name", "order_count"],
                        [
                            ["Alice", 2],
                            ["Bob", 1],
                            ["Charlie", 1],
                            ["Diana", 1],
                            ["Ethan", 0],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Use `COUNT(o.id)` (not `COUNT(*)`) so unmatched rows count as 0.",
                        "LEFT JOIN keeps Ethan in the result even though he has no orders.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Each customer's latest order",
                    instructions=(
                        "Return each customer's `name` and their most recent "
                        "`order_date` (NULL when they haven't ordered). Alias "
                        "the date as `last_order` and sort by `name`."
                    ),
                    solution_query=(
                        "SELECT c.name, MAX(o.order_date) AS last_order "
                        "FROM customers c LEFT JOIN orders o "
                        "ON c.id = o.customer_id "
                        "GROUP BY c.name ORDER BY c.name;"
                    ),
                    expected_result=_result(
                        ["name", "last_order"],
                        [
                            ["Alice", "2024-02-15"],
                            ["Bob", "2024-02-20"],
                            ["Charlie", "2024-03-01"],
                            ["Diana", "2024-03-10"],
                            ["Ethan", None],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "LEFT JOIN keeps Ethan; `MAX(o.order_date)` over no rows is NULL.",
                        "Group by `c.name` so the aggregate runs per customer.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=3,
            title="RIGHT and FULL OUTER JOINs",
            theory_content=(
                "## Keeping the other side, and both sides\n\n"
                "`RIGHT JOIN` is the mirror image of `LEFT JOIN` — every row "
                "from the **right** table survives, with NULLs on the left "
                "when there's no match.\n\n"
                "`FULL OUTER JOIN` keeps every row from **both** tables, "
                "filling NULLs wherever the match is missing:\n\n"
                "```sql\n"
                "SELECT c.name, o.id\n"
                "FROM   customers c\n"
                "FULL   OUTER JOIN orders o ON c.id = o.customer_id;\n"
                "```\n\n"
                "Most engineers prefer to use only LEFT JOIN (swapping the "
                "tables if necessary), but RIGHT and FULL joins show up in "
                "reporting queries.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Every order, named or not",
                    instructions=(
                        "For every row in `orders`, return the order `id` and "
                        "the matching customer `name` (NULL when the "
                        "`customer_id` has no match). Use a RIGHT JOIN. Sort by "
                        "order `id`."
                    ),
                    solution_query=(
                        "SELECT o.id, c.name FROM customers c "
                        "RIGHT JOIN orders o ON c.id = o.customer_id "
                        "ORDER BY o.id;"
                    ),
                    expected_result=_result(
                        ["id", "name"],
                        [
                            [101, "Alice"],
                            [102, "Alice"],
                            [103, "Bob"],
                            [104, "Charlie"],
                            [105, "Diana"],
                            [106, None],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Start from `customers RIGHT JOIN orders` — the right side drives the result.",
                        "The orphan order (106) has customer_id 999, which doesn't match any customer.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Full picture",
                    instructions=(
                        "Return every `name` from `customers` alongside every "
                        "order `id`, showing NULLs on both sides when there is "
                        "no match. Use a FULL OUTER JOIN."
                    ),
                    solution_query=(
                        "SELECT c.name, o.id FROM customers c "
                        "FULL OUTER JOIN orders o ON c.id = o.customer_id;"
                    ),
                    expected_result=_result(
                        ["name", "id"],
                        [
                            ["Alice", 101],
                            ["Alice", 102],
                            ["Bob", 103],
                            ["Charlie", 104],
                            ["Diana", 105],
                            ["Ethan", None],
                            [None, 106],
                        ],
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "`FULL OUTER JOIN` keeps unmatched rows from both sides.",
                        "Expect 7 rows: 5 matched, Ethan (no orders), order 106 (no customer).",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=4,
            title="Multi-Table Reports",
            theory_content=(
                "## Three tables, one answer\n\n"
                "Real reports routinely join three or more tables. Line them up "
                "one after another and keep each `ON` clause close to its "
                "`JOIN`:\n\n"
                "```sql\n"
                "SELECT c.name, SUM(oi.quantity * oi.unit_price) AS revenue\n"
                "FROM   customers c\n"
                "JOIN   orders      o  ON c.id = o.customer_id\n"
                "JOIN   order_items oi ON o.id = oi.order_id\n"
                "GROUP  BY c.name;\n"
                "```\n\n"
                "Whenever you're not sure whether to use INNER or LEFT, ask "
                "yourself: *\"Do I want rows on the outer table without a "
                "match?\"* If yes, reach for LEFT.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Revenue per customer",
                    instructions=(
                        "Join the three tables and return each customer's "
                        "`name` and total revenue (`SUM(quantity * unit_price)` "
                        "from `order_items`) aliased as `revenue`. Sort by "
                        "revenue descending."
                    ),
                    solution_query=(
                        "SELECT c.name, "
                        "SUM(oi.quantity * oi.unit_price) AS revenue "
                        "FROM customers c "
                        "JOIN orders o ON c.id = o.customer_id "
                        "JOIN order_items oi ON o.id = oi.order_id "
                        "GROUP BY c.name ORDER BY revenue DESC;"
                    ),
                    expected_result=_result(
                        ["name", "revenue"],
                        [
                            ["Charlie", 200.00],
                            ["Alice", 170.00],
                            ["Diana", 80.00],
                            ["Bob", 35.00],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Chain INNER JOINs across all three tables, then GROUP BY `c.name`.",
                        "`SUM(oi.quantity * oi.unit_price)` sums per-item revenue within each group.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Items sold per country",
                    instructions=(
                        "Join the three tables and return each `country` with "
                        "the total units sold there (`SUM(quantity)` from "
                        "`order_items`) aliased as `total_items`. Sort by "
                        "`country` alphabetically."
                    ),
                    solution_query=(
                        "SELECT c.country, SUM(oi.quantity) AS total_items "
                        "FROM customers c "
                        "JOIN orders o ON c.id = o.customer_id "
                        "JOIN order_items oi ON o.id = oi.order_id "
                        "GROUP BY c.country ORDER BY c.country;"
                    ),
                    expected_result=_result(
                        ["country", "total_items"],
                        [
                            ["France", 1],
                            ["Romania", 13],
                            ["UK", 1],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Only countries with at least one order surface after INNER JOIN.",
                        "Group by `c.country`, not by customer.",
                    ],
                ),
            ],
        ),
    ],
    quiz=ExerciseSpec(
        order=100,
        title="Chapter 5 Quiz — Total Spend (Including Zero)",
        instructions=(
            "For every customer return their `name` and their total spend "
            "(`SUM(quantity * unit_price)` from `order_items`) aliased as "
            "`total`. Customers with no orders must still appear with a total "
            "of `0`. Sort by `total` descending."
        ),
        solution_query=(
            "SELECT c.name, "
            "COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total "
            "FROM customers c "
            "LEFT JOIN orders o ON c.id = o.customer_id "
            "LEFT JOIN order_items oi ON o.id = oi.order_id "
            "GROUP BY c.name ORDER BY total DESC;"
        ),
        expected_result=_result(
            ["name", "total"],
            [
                ["Charlie", 200.00],
                ["Alice", 170.00],
                ["Diana", 80.00],
                ["Bob", 35.00],
                ["Ethan", 0],
            ],
            ordered=True,
        ),
        datasets=["ch5_ecommerce"],
        difficulty=Difficulty.HARD,
        is_chapter_quiz=True,
        hints=[
            "LEFT JOIN keeps Ethan even though he has no orders.",
            "Wrap the `SUM` in `COALESCE(..., 0)` so his total is 0, not NULL.",
            "`ORDER BY total DESC` uses the column alias.",
        ],
    ),
)


# ---------------------------------------------------------------------------
# Chapter 6 — Subqueries
# ---------------------------------------------------------------------------

CH6 = ChapterSpec(
    order=6,
    title="Subqueries",
    description=(
        "Use the result of one query inside another: scalar subqueries, "
        "`IN` / `EXISTS`, correlated references, and CTEs (`WITH`)."
    ),
    lessons=[
        LessonSpec(
            order=1,
            title="Scalar Subqueries",
            theory_content=(
                "## A query that returns one value\n\n"
                "A **scalar subquery** returns exactly one row and one column. "
                "You can drop it anywhere a single value is expected — inside "
                "`WHERE`, `SELECT`, or even as the entire right-hand side of a "
                "comparison:\n\n"
                "```sql\n"
                "SELECT name\n"
                "FROM   customers\n"
                "WHERE  id = (SELECT customer_id FROM orders ORDER BY total DESC LIMIT 1);\n"
                "```\n\n"
                "If the inner query returns more than one row, PostgreSQL will "
                "raise an error — that's when you reach for `IN` or `EXISTS`.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="The single biggest order",
                    instructions=(
                        "Return every column of the order whose `total` equals "
                        "the maximum `total` across `orders`."
                    ),
                    solution_query=(
                        "SELECT * FROM orders "
                        "WHERE total = (SELECT MAX(total) FROM orders);"
                    ),
                    expected_result=_result(
                        ["id", "customer_id", "order_date", "total"],
                        [[104, 3, "2024-03-01", 200.00]],
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "The scalar subquery `(SELECT MAX(total) FROM orders)` yields a single number.",
                        "Compare it against `total` in the outer WHERE.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Above-average orders",
                    instructions=(
                        "Return the `id` and `total` of orders whose `total` is "
                        "**greater than the average order total**. Sort by "
                        "`id` ascending."
                    ),
                    solution_query=(
                        "SELECT id, total FROM orders "
                        "WHERE total > (SELECT AVG(total) FROM orders) "
                        "ORDER BY id;"
                    ),
                    expected_result=_result(
                        ["id", "total"],
                        [[102, 120.00], [104, 200.00], [106, 99.00]],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Compute the average in a scalar subquery inside WHERE.",
                        "`total > (SELECT AVG(total) FROM orders)`.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=2,
            title="IN and NOT IN",
            theory_content=(
                "## Matching against a list\n\n"
                "`IN (subquery)` checks whether a value appears in the rows "
                "returned by an inner SELECT:\n\n"
                "```sql\n"
                "SELECT name\n"
                "FROM   customers\n"
                "WHERE  id IN (SELECT customer_id FROM orders);\n"
                "```\n\n"
                "`NOT IN` is the inverse, but be careful — if the subquery "
                "returns even one NULL, `NOT IN` evaluates to NULL for every "
                "row (and nothing is returned). Filter out NULLs in the "
                "subquery or use `NOT EXISTS` when you're unsure.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Customers who have ordered",
                    instructions=(
                        "Return the `name` of every customer whose `id` appears "
                        "in the `orders.customer_id` column. Sort by `name`."
                    ),
                    solution_query=(
                        "SELECT name FROM customers "
                        "WHERE id IN (SELECT customer_id FROM orders) "
                        "ORDER BY name;"
                    ),
                    expected_result=_result(
                        ["name"],
                        [["Alice"], ["Bob"], ["Charlie"], ["Diana"]],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`WHERE id IN (SELECT customer_id FROM orders)`.",
                        "The orphan order's customer_id (999) just isn't present in `customers`, so it doesn't affect the match.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Romanian products",
                    instructions=(
                        "Return the `product` of every row in `order_items` whose "
                        "`order_id` belongs to an order placed by a customer in "
                        "`Romania`. Sort by `product`."
                    ),
                    solution_query=(
                        "SELECT product FROM order_items "
                        "WHERE order_id IN ("
                        "  SELECT id FROM orders WHERE customer_id IN ("
                        "    SELECT id FROM customers WHERE country = 'Romania'"
                        "  )"
                        ") ORDER BY product;"
                    ),
                    expected_result=_result(
                        ["product"],
                        [["Desk Lamp"], ["Keyboard"], ["Notebook"]],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Three-level nesting: order_items → orders → customers.",
                        "Innermost subquery selects Romanian customer ids; middle picks orders from those customers; outer WHERE checks the order_id.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=3,
            title="EXISTS and Correlated Subqueries",
            theory_content=(
                "## Does a matching row exist?\n\n"
                "`EXISTS (subquery)` is true if the subquery returns at least "
                "one row. The subquery can reference columns from the outer "
                "query — that makes it a **correlated subquery**:\n\n"
                "```sql\n"
                "SELECT name\n"
                "FROM   customers c\n"
                "WHERE  EXISTS (\n"
                "    SELECT 1 FROM orders o WHERE o.customer_id = c.id\n"
                ");\n"
                "```\n\n"
                "`NOT EXISTS` handles the opposite question without the NULL "
                "traps of `NOT IN`.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Customers who have ordered (again)",
                    instructions=(
                        "Return the `name` of every customer who has at least "
                        "one matching row in `orders`. Use `EXISTS`. Sort by "
                        "`name`."
                    ),
                    solution_query=(
                        "SELECT name FROM customers c "
                        "WHERE EXISTS (SELECT 1 FROM orders o "
                        "WHERE o.customer_id = c.id) "
                        "ORDER BY name;"
                    ),
                    expected_result=_result(
                        ["name"],
                        [["Alice"], ["Bob"], ["Charlie"], ["Diana"]],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "The `SELECT 1` inside EXISTS is idiomatic — only the existence of a row matters, not what it contains.",
                        "Correlate with `o.customer_id = c.id`.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Customers with no orders",
                    instructions=(
                        "Return the `name` of every customer who has **no** "
                        "matching rows in `orders`. Use `NOT EXISTS`. Sort by "
                        "`name`."
                    ),
                    solution_query=(
                        "SELECT name FROM customers c "
                        "WHERE NOT EXISTS (SELECT 1 FROM orders o "
                        "WHERE o.customer_id = c.id) "
                        "ORDER BY name;"
                    ),
                    expected_result=_result(
                        ["name"], [["Ethan"]]
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Flip the previous query to `NOT EXISTS`.",
                        "Only Ethan has no matching order.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=4,
            title="Common Table Expressions (WITH)",
            theory_content=(
                "## Naming sub-results with WITH\n\n"
                "A Common Table Expression (CTE) lets you name an intermediate "
                "result and reference it later in the same query. It reads "
                "top-to-bottom, which makes complex queries much easier to "
                "follow:\n\n"
                "```sql\n"
                "WITH customer_totals AS (\n"
                "    SELECT c.id, c.name, COALESCE(SUM(o.total), 0) AS total\n"
                "    FROM   customers c\n"
                "    LEFT   JOIN orders o ON c.id = o.customer_id\n"
                "    GROUP  BY c.id, c.name\n"
                ")\n"
                "SELECT name, total FROM customer_totals WHERE total > 100;\n"
                "```\n\n"
                "CTEs are scoped to a single statement — you can't reuse them "
                "in another query without redefining them.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Big spenders with a CTE",
                    instructions=(
                        "Using a `WITH` clause, compute each customer's total "
                        "order value (`SUM(orders.total)`, `COALESCE`d to 0 for "
                        "customers with no orders). Return only customers whose "
                        "total is **above 100**, as `name` and `total`. Sort by "
                        "`total` descending."
                    ),
                    solution_query=(
                        "WITH customer_totals AS ("
                        "  SELECT c.name, COALESCE(SUM(o.total), 0) AS total "
                        "  FROM customers c "
                        "  LEFT JOIN orders o ON c.id = o.customer_id "
                        "  GROUP BY c.name"
                        ") "
                        "SELECT name, total FROM customer_totals "
                        "WHERE total > 100 ORDER BY total DESC;"
                    ),
                    expected_result=_result(
                        ["name", "total"],
                        [["Charlie", 200.00], ["Alice", 170.00]],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Open with `WITH customer_totals AS ( ... )`.",
                        "The final SELECT reads from the CTE as if it were a table.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Recent-order count per customer",
                    instructions=(
                        "Using a CTE, collect every order placed on or after "
                        "`'2024-02-01'`, then join it against `customers` to "
                        "return each customer's `name` and their count of "
                        "recent orders (alias `recent_orders`). Exclude "
                        "customers with no recent orders. Sort by `name`."
                    ),
                    solution_query=(
                        "WITH recent AS ("
                        "  SELECT customer_id FROM orders "
                        "  WHERE order_date >= '2024-02-01'"
                        ") "
                        "SELECT c.name, COUNT(*) AS recent_orders "
                        "FROM customers c JOIN recent r ON c.id = r.customer_id "
                        "GROUP BY c.name ORDER BY c.name;"
                    ),
                    expected_result=_result(
                        ["name", "recent_orders"],
                        [
                            ["Alice", 1],
                            ["Bob", 1],
                            ["Charlie", 1],
                            ["Diana", 1],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch5_ecommerce"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "The CTE only needs `customer_id` — it's the key we'll join on.",
                        "An INNER JOIN to the CTE naturally drops customers with no recent orders; the orphan id 999 is also dropped because it has no matching customer.",
                    ],
                ),
            ],
        ),
    ],
    quiz=ExerciseSpec(
        order=100,
        title="Chapter 6 Quiz — Top-Spending Countries",
        instructions=(
            "Write a CTE-driven query that computes each `country`'s total "
            "revenue (`SUM(quantity * unit_price)` from `order_items`, joined "
            "through `orders` and `customers`). Return only countries with "
            "revenue **above 50**, as `country` and `revenue`. Sort by "
            "`revenue` descending."
        ),
        solution_query=(
            "WITH country_revenue AS ("
            "  SELECT c.country, SUM(oi.quantity * oi.unit_price) AS revenue "
            "  FROM customers c "
            "  JOIN orders o ON c.id = o.customer_id "
            "  JOIN order_items oi ON o.id = oi.order_id "
            "  GROUP BY c.country"
            ") "
            "SELECT country, revenue FROM country_revenue "
            "WHERE revenue > 50 ORDER BY revenue DESC;"
        ),
        expected_result=_result(
            ["country", "revenue"],
            [["Romania", 250.00], ["France", 200.00]],
            ordered=True,
        ),
        datasets=["ch5_ecommerce"],
        difficulty=Difficulty.HARD,
        is_chapter_quiz=True,
        hints=[
            "Inside the CTE, INNER JOIN the three tables and group by country.",
            "Filter the CTE with `WHERE revenue > 50` and order by revenue.",
        ],
    ),
)


# ---------------------------------------------------------------------------
# Chapter 7 — Modifying Data
# ---------------------------------------------------------------------------
# Chapter 7 is the first chapter where non-SELECT statements are permitted
# by ``ForbiddenOperationHandler``. Every write exercise uses ``RETURNING`` so
# the result comparator has columns/rows to match against.
# ---------------------------------------------------------------------------

CH7 = ChapterSpec(
    order=7,
    title="Modifying Data",
    description=(
        "Change the contents of a table with INSERT, UPDATE, and DELETE. "
        "Every exercise uses RETURNING so you can see exactly which rows "
        "your statement affected."
    ),
    lessons=[
        LessonSpec(
            order=1,
            title="Inserting Rows",
            theory_content=(
                "## Adding new data\n\n"
                "`INSERT INTO` appends rows to a table:\n\n"
                "```sql\n"
                "INSERT INTO tasks (id, title, status, priority, assignee)\n"
                "VALUES (8, 'Add docs', 'todo', 2, 'Ethan')\n"
                "RETURNING title, status;\n"
                "```\n\n"
                "You can insert many rows at once by separating value groups "
                "with commas. The optional `RETURNING` clause echoes the "
                "inserted rows back — handy for verifying what happened (and "
                "required in these exercises).\n\n"
                "Every exercise starts from a fresh copy of the `tasks` table, "
                "so you never need to undo earlier writes.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Insert a single task",
                    instructions=(
                        "Insert a new row into `tasks` with `id = 8`, "
                        "`title = 'Add docs'`, `status = 'todo'`, "
                        "`priority = 2`, `assignee = 'Ethan'`. Return the new "
                        "row's `title` and `status`."
                    ),
                    solution_query=(
                        "INSERT INTO tasks (id, title, status, priority, assignee) "
                        "VALUES (8, 'Add docs', 'todo', 2, 'Ethan') "
                        "RETURNING title, status;"
                    ),
                    expected_result=_result(
                        ["title", "status"],
                        [["Add docs", "todo"]],
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Name the columns in the same order as the values.",
                        "Add `RETURNING title, status;` so PostgreSQL echoes the new row.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Insert two tasks at once",
                    instructions=(
                        "With a single statement, insert two rows: "
                        "(`id = 8`, `title = 'Fix bug'`, status `'todo'`, "
                        "priority `1`, assignee `'Alice'`) and "
                        "(`id = 9`, `title = 'Refactor auth'`, status `'todo'`, "
                        "priority `2`, assignee `'Bob'`). "
                        "Return `id`, `title`, `priority` for each inserted row."
                    ),
                    solution_query=(
                        "INSERT INTO tasks (id, title, status, priority, assignee) "
                        "VALUES (8, 'Fix bug', 'todo', 1, 'Alice'), "
                        "(9, 'Refactor auth', 'todo', 2, 'Bob') "
                        "RETURNING id, title, priority;"
                    ),
                    expected_result=_result(
                        ["id", "title", "priority"],
                        [[8, "Fix bug", 1], [9, "Refactor auth", 2]],
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Provide two value groups separated by a comma: `VALUES (...), (...)`.",
                        "`RETURNING` echoes every inserted row, not just the first.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=2,
            title="Updating Rows",
            theory_content=(
                "## Changing existing data\n\n"
                "`UPDATE` modifies rows that match a condition. The `SET` "
                "clause lists the columns and their new values:\n\n"
                "```sql\n"
                "UPDATE tasks\n"
                "SET    status = 'doing'\n"
                "WHERE  id = 5\n"
                "RETURNING id, title, status;\n"
                "```\n\n"
                "Forgetting the `WHERE` clause updates **every row** in the "
                "table — always double-check your filter before running an "
                "update. The new value can be a fresh literal or an expression "
                "based on the current row: `SET priority = priority + 1`.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Promote a single task",
                    instructions=(
                        "Set `status` to `'doing'` for the task with `id = 5`. "
                        "Return `id`, `title`, and the new `status`."
                    ),
                    solution_query=(
                        "UPDATE tasks SET status = 'doing' WHERE id = 5 "
                        "RETURNING id, title, status;"
                    ),
                    expected_result=_result(
                        ["id", "title", "status"],
                        [[5, "Write tests", "doing"]],
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`UPDATE tasks SET <col> = <value> WHERE <filter>`.",
                        "Return the id, title, and new status with `RETURNING`.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Assign the orphans",
                    instructions=(
                        "Set `assignee` to `'Alice'` for every task whose "
                        "`assignee` is currently NULL. Return the `title` of "
                        "each affected task."
                    ),
                    solution_query=(
                        "UPDATE tasks SET assignee = 'Alice' "
                        "WHERE assignee IS NULL RETURNING title;"
                    ),
                    expected_result=_result(
                        ["title"], [["Deploy to staging"]]
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Use `WHERE assignee IS NULL` — never `= NULL`.",
                        "Only one task matches (Deploy to staging).",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Bump priorities",
                    instructions=(
                        "Increase `priority` by 1 for every task whose `status` "
                        "is `'todo'`. Return the `id` and the new `priority` of "
                        "each affected row."
                    ),
                    solution_query=(
                        "UPDATE tasks SET priority = priority + 1 "
                        "WHERE status = 'todo' RETURNING id, priority;"
                    ),
                    expected_result=_result(
                        ["id", "priority"],
                        [[5, 4], [6, 4], [7, 5]],
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "The right-hand side of SET can use the column itself: `priority = priority + 1`.",
                        "Three todo tasks match — returning all three is fine in any order.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=3,
            title="Deleting Rows",
            theory_content=(
                "## Removing rows\n\n"
                "`DELETE FROM` removes every row matching a filter:\n\n"
                "```sql\n"
                "DELETE FROM tasks\n"
                "WHERE  id = 7\n"
                "RETURNING title;\n"
                "```\n\n"
                "Just like UPDATE, a missing `WHERE` clause deletes *every* "
                "row. Using `RETURNING` lets you confirm exactly which rows "
                "were removed.\n\n"
                "To empty a table completely, PostgreSQL prefers `TRUNCATE`, "
                "but `TRUNCATE` is a DDL statement and isn't allowed in these "
                "exercises.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Delete a single task",
                    instructions=(
                        "Delete the task with `id = 7`. Return its `title`."
                    ),
                    solution_query=(
                        "DELETE FROM tasks WHERE id = 7 RETURNING title;"
                    ),
                    expected_result=_result(
                        ["title"], [["Update changelog"]]
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`DELETE FROM tasks WHERE id = 7`.",
                        "Add `RETURNING title` to echo the deleted row.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Archive completed work",
                    instructions=(
                        "Delete every task whose `status` is `'done'`. Return "
                        "the `id` and `title` of each deleted row."
                    ),
                    solution_query=(
                        "DELETE FROM tasks WHERE status = 'done' "
                        "RETURNING id, title;"
                    ),
                    expected_result=_result(
                        ["id", "title"],
                        [[1, "Write spec"], [2, "Design database"]],
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "Filter with `WHERE status = 'done'`.",
                        "Both rows are returned — the order is not fixed.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Prune low-priority work",
                    instructions=(
                        "Delete every task whose `priority` is **at least 3**. "
                        "Return the `id` of each deleted row."
                    ),
                    solution_query=(
                        "DELETE FROM tasks WHERE priority >= 3 RETURNING id;"
                    ),
                    expected_result=_result(
                        ["id"], [[5], [6], [7]]
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "\"At least 3\" means `>= 3`.",
                        "Three rows match — return just their ids.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=4,
            title="Expressions in Write Statements",
            theory_content=(
                "## Computing new values as you go\n\n"
                "Both `UPDATE` and `DELETE` accept expressions and functions "
                "on both sides of the comparison. `UPDATE ... SET` can apply "
                "string functions, arithmetic, or `CASE` blocks to derive the "
                "new value:\n\n"
                "```sql\n"
                "UPDATE tasks\n"
                "SET    priority = CASE status\n"
                "                      WHEN 'done'  THEN 1\n"
                "                      WHEN 'doing' THEN 2\n"
                "                      ELSE 3\n"
                "                  END\n"
                "RETURNING id, priority;\n"
                "```\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Shout your todos",
                    instructions=(
                        "For every task whose `status` is `'todo'`, replace "
                        "`title` with its UPPERCASE version. Return the `id` "
                        "and the new `title` of each affected task."
                    ),
                    solution_query=(
                        "UPDATE tasks SET title = UPPER(title) "
                        "WHERE status = 'todo' RETURNING id, title;"
                    ),
                    expected_result=_result(
                        ["id", "title"],
                        [
                            [5, "WRITE TESTS"],
                            [6, "DEPLOY TO STAGING"],
                            [7, "UPDATE CHANGELOG"],
                        ],
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "`UPPER(title)` returns the uppercase form of the string.",
                        "Filter on `status = 'todo'` so only three rows change.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Drop the un-assigned",
                    instructions=(
                        "Delete every task whose `assignee` is NULL. Return "
                        "the `id` of the removed row(s)."
                    ),
                    solution_query=(
                        "DELETE FROM tasks WHERE assignee IS NULL RETURNING id;"
                    ),
                    expected_result=_result(["id"], [[6]]),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`IS NULL` is the right operator for a NULL check.",
                        "Only task 6 has no assignee.",
                    ],
                ),
                ExerciseSpec(
                    order=3,
                    title="Priority by status",
                    instructions=(
                        "For every row in `tasks`, set `priority` to `1` when "
                        "`status` is `'done'`, `2` when `status` is `'doing'`, "
                        "and `3` otherwise. Return the `id` and the new "
                        "`priority` of every row."
                    ),
                    solution_query=(
                        "UPDATE tasks SET priority = CASE status "
                        "WHEN 'done' THEN 1 "
                        "WHEN 'doing' THEN 2 "
                        "ELSE 3 END "
                        "RETURNING id, priority;"
                    ),
                    expected_result=_result(
                        ["id", "priority"],
                        [
                            [1, 1],
                            [2, 1],
                            [3, 2],
                            [4, 2],
                            [5, 3],
                            [6, 3],
                            [7, 3],
                        ],
                    ),
                    datasets=["ch7_tasks"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Use a CASE block on the right-hand side of `SET priority = ...`.",
                        "No WHERE clause means the CASE runs against every row.",
                    ],
                ),
            ],
        ),
    ],
    quiz=ExerciseSpec(
        order=100,
        title="Chapter 7 Quiz — Start the Sprint",
        instructions=(
            "Kick off the sprint: update every task whose `status` is "
            "`'todo'` **and** whose `priority` is **greater than 2** so that "
            "`status` becomes `'doing'` and `priority` becomes `2`. Return "
            "the `id`, `title`, and new `priority` of each affected row."
        ),
        solution_query=(
            "UPDATE tasks SET status = 'doing', priority = 2 "
            "WHERE status = 'todo' AND priority > 2 "
            "RETURNING id, title, priority;"
        ),
        expected_result=_result(
            ["id", "title", "priority"],
            [
                [5, "Write tests", 2],
                [6, "Deploy to staging", 2],
                [7, "Update changelog", 2],
            ],
        ),
        datasets=["ch7_tasks"],
        difficulty=Difficulty.HARD,
        is_chapter_quiz=True,
        hints=[
            "Two columns in the SET list: `status = 'doing', priority = 2`.",
            "Two filters combined with AND: `status = 'todo' AND priority > 2`.",
            "RETURNING echoes every affected row.",
        ],
    ),
)


# ---------------------------------------------------------------------------
# Chapter 8 — Advanced Queries
# ---------------------------------------------------------------------------

CH8 = ChapterSpec(
    order=8,
    title="Advanced Queries",
    description=(
        "Level up with window functions, UNION, and the set-based operators "
        "that compare whole result sets to each other."
    ),
    lessons=[
        LessonSpec(
            order=1,
            title="Window Functions: ROW_NUMBER and RANK",
            theory_content=(
                "## Per-row rankings without collapsing rows\n\n"
                "Aggregates (`GROUP BY`) collapse rows into one per group. "
                "**Window functions** compute across a set of rows but keep "
                "every input row in the output. The window is defined by the "
                "`OVER` clause:\n\n"
                "```sql\n"
                "SELECT salesperson, amount,\n"
                "       ROW_NUMBER() OVER (ORDER BY amount DESC) AS rn\n"
                "FROM   sales;\n"
                "```\n\n"
                "`PARTITION BY` splits the window into groups (like `GROUP BY` "
                "without collapsing). Common ranking functions: "
                "`ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Rank every sale",
                    instructions=(
                        "For every row in `sales`, return `id`, `salesperson`, "
                        "`amount`, and a `rn` column giving the row number "
                        "when the table is ordered by `amount` **descending**. "
                        "Sort the final result by `rn` ascending."
                    ),
                    solution_query=(
                        "SELECT id, salesperson, amount, "
                        "ROW_NUMBER() OVER (ORDER BY amount DESC) AS rn "
                        "FROM sales ORDER BY rn;"
                    ),
                    expected_result=_result(
                        ["id", "salesperson", "amount", "rn"],
                        [
                            [10, "Charlie", 18000, 1],
                            [7, "Charlie", 16000, 2],
                            [3, "Charlie", 15000, 3],
                            [5, "Alice", 14000, 4],
                            [9, "Alice", 13000, 5],
                            [1, "Alice", 12000, 6],
                            [6, "Bob", 11000, 7],
                            [2, "Bob", 9000, 8],
                            [4, "Diana", 8000, 9],
                            [8, "Diana", 7000, 10],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch8_sales"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Window functions require an `OVER(...)` clause.",
                        "`ROW_NUMBER() OVER (ORDER BY amount DESC)` numbers every row.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Rank within each region",
                    instructions=(
                        "Return `region`, `salesperson`, `amount`, and a "
                        "`rnk` column giving the rank of each sale **within "
                        "its region** (highest amount first). Sort by "
                        "`region` then `rnk`."
                    ),
                    solution_query=(
                        "SELECT region, salesperson, amount, "
                        "RANK() OVER (PARTITION BY region ORDER BY amount DESC) "
                        "AS rnk FROM sales ORDER BY region, rnk;"
                    ),
                    expected_result=_result(
                        ["region", "salesperson", "amount", "rnk"],
                        [
                            ["North", "Alice", 14000, 1],
                            ["North", "Alice", 13000, 2],
                            ["North", "Alice", 12000, 3],
                            ["North", "Bob", 11000, 4],
                            ["North", "Bob", 9000, 5],
                            ["South", "Charlie", 18000, 1],
                            ["South", "Charlie", 16000, 2],
                            ["South", "Charlie", 15000, 3],
                            ["South", "Diana", 8000, 4],
                            ["South", "Diana", 7000, 5],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch8_sales"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "`PARTITION BY region` scopes the ranking to each region.",
                        "Rank restarts at 1 inside each partition.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=2,
            title="Running Totals, LAG and LEAD",
            theory_content=(
                "## Looking across neighbouring rows\n\n"
                "With a window you can also aggregate incrementally "
                "(`SUM(...) OVER`) or peek at nearby rows with `LAG` (previous "
                "row) and `LEAD` (next row):\n\n"
                "```sql\n"
                "SELECT quarter, SUM(amount) AS q_total,\n"
                "       SUM(SUM(amount)) OVER (ORDER BY quarter) AS running_total\n"
                "FROM   sales\n"
                "GROUP  BY quarter;\n"
                "```\n\n"
                "Any missing neighbour (for the first or last row) comes back "
                "as NULL.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="Running total by quarter",
                    instructions=(
                        "Per quarter, return the quarter label, its total "
                        "`amount` (alias `q_total`), and the running total "
                        "across quarters in order (alias `running_total`). "
                        "Sort by `quarter` ascending."
                    ),
                    solution_query=(
                        "SELECT quarter, SUM(amount) AS q_total, "
                        "SUM(SUM(amount)) OVER (ORDER BY quarter) "
                        "AS running_total "
                        "FROM sales GROUP BY quarter ORDER BY quarter;"
                    ),
                    expected_result=_result(
                        ["quarter", "q_total", "running_total"],
                        [
                            ["Q1", 44000, 44000],
                            ["Q2", 48000, 92000],
                            ["Q3", 31000, 123000],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch8_sales"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Aggregate by quarter in `GROUP BY`, then apply the "
                        "window on top: `SUM(SUM(amount)) OVER (ORDER BY quarter)`.",
                        "Quarter labels sort naturally as strings ('Q1' < 'Q2' < 'Q3').",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Previous quarter's amount",
                    instructions=(
                        "Per salesperson, return their `salesperson`, "
                        "`quarter`, `amount`, and the `amount` from their "
                        "**previous** quarter (NULL for the first). Alias "
                        "the previous value `prev_amount`. Sort by "
                        "`salesperson` then `quarter`."
                    ),
                    solution_query=(
                        "SELECT salesperson, quarter, amount, "
                        "LAG(amount) OVER (PARTITION BY salesperson "
                        "ORDER BY quarter) AS prev_amount "
                        "FROM sales ORDER BY salesperson, quarter;"
                    ),
                    expected_result=_result(
                        ["salesperson", "quarter", "amount", "prev_amount"],
                        [
                            ["Alice", "Q1", 12000, None],
                            ["Alice", "Q2", 14000, 12000],
                            ["Alice", "Q3", 13000, 14000],
                            ["Bob", "Q1", 9000, None],
                            ["Bob", "Q2", 11000, 9000],
                            ["Charlie", "Q1", 15000, None],
                            ["Charlie", "Q2", 16000, 15000],
                            ["Charlie", "Q3", 18000, 16000],
                            ["Diana", "Q1", 8000, None],
                            ["Diana", "Q2", 7000, 8000],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch8_sales"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "`LAG(amount) OVER (PARTITION BY salesperson ORDER BY quarter)`.",
                        "Each salesperson's first quarter has no previous row → NULL.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=3,
            title="UNION and UNION ALL",
            theory_content=(
                "## Stacking result sets\n\n"
                "`UNION` combines the rows of two queries that have the same "
                "column shape. It removes duplicates by default; "
                "`UNION ALL` keeps every row (and is faster when duplicates "
                "don't matter):\n\n"
                "```sql\n"
                "SELECT salesperson FROM sales\n"
                "UNION\n"
                "SELECT salesperson FROM returns;\n"
                "```\n\n"
                "Both sides must agree on the number of columns and on each "
                "column's data type. The top query's column names determine "
                "the result.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="All salespeople, once",
                    instructions=(
                        "Return the set of distinct `salesperson` values that "
                        "appear in **either** `sales` or `returns`, sorted "
                        "alphabetically."
                    ),
                    solution_query=(
                        "SELECT salesperson FROM sales "
                        "UNION SELECT salesperson FROM returns "
                        "ORDER BY salesperson;"
                    ),
                    expected_result=_result(
                        ["salesperson"],
                        [["Alice"], ["Bob"], ["Charlie"], ["Diana"]],
                        ordered=True,
                    ),
                    datasets=["ch8_sales"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`UNION` removes duplicates automatically.",
                        "The outer `ORDER BY` applies to the combined result.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Label every movement",
                    instructions=(
                        "Combine `sales` and `returns` into a single listing. "
                        "Each row should show a `type` column with value "
                        "`'sale'` or `'return'`, followed by `salesperson` "
                        "and `amount`. Use `UNION ALL`. Sort by `type` "
                        "ascending then `amount` descending."
                    ),
                    solution_query=(
                        "SELECT 'sale' AS type, salesperson, amount FROM sales "
                        "UNION ALL "
                        "SELECT 'return' AS type, salesperson, amount FROM returns "
                        "ORDER BY type, amount DESC;"
                    ),
                    expected_result=_result(
                        ["type", "salesperson", "amount"],
                        [
                            ["return", "Alice", 500],
                            ["return", "Diana", 300],
                            ["return", "Bob", 200],
                            ["sale", "Charlie", 18000],
                            ["sale", "Charlie", 16000],
                            ["sale", "Charlie", 15000],
                            ["sale", "Alice", 14000],
                            ["sale", "Alice", 13000],
                            ["sale", "Alice", 12000],
                            ["sale", "Bob", 11000],
                            ["sale", "Bob", 9000],
                            ["sale", "Diana", 8000],
                            ["sale", "Diana", 7000],
                        ],
                        ordered=True,
                    ),
                    datasets=["ch8_sales"],
                    difficulty=Difficulty.HARD,
                    hints=[
                        "Add a literal `'sale' AS type` column on one side and `'return' AS type` on the other.",
                        "`UNION ALL` preserves duplicates; `UNION` would drop any repeated (type, salesperson, amount) triples.",
                    ],
                ),
            ],
        ),
        LessonSpec(
            order=4,
            title="INTERSECT and EXCEPT",
            theory_content=(
                "## Set membership beyond UNION\n\n"
                "`INTERSECT` returns rows that appear in **both** queries; "
                "`EXCEPT` returns rows in the first query that are **not** in "
                "the second. Like `UNION`, both sides need matching column "
                "shapes:\n\n"
                "```sql\n"
                "SELECT salesperson FROM sales\n"
                "INTERSECT\n"
                "SELECT salesperson FROM returns;\n"
                "```\n\n"
                "Both operators remove duplicates by default. Add `ALL` "
                "(e.g. `EXCEPT ALL`) if you need multiset semantics.\n"
            ),
            exercises=[
                ExerciseSpec(
                    order=1,
                    title="People who both sold and returned",
                    instructions=(
                        "Return the list of distinct `salesperson` names who "
                        "appear in **both** `sales` and `returns`. Sort "
                        "alphabetically."
                    ),
                    solution_query=(
                        "SELECT salesperson FROM sales "
                        "INTERSECT SELECT salesperson FROM returns "
                        "ORDER BY salesperson;"
                    ),
                    expected_result=_result(
                        ["salesperson"],
                        [["Alice"], ["Bob"], ["Diana"]],
                        ordered=True,
                    ),
                    datasets=["ch8_sales"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`INTERSECT` keeps only rows that both sides produce.",
                        "Charlie only appears in `sales`, so he drops out.",
                    ],
                ),
                ExerciseSpec(
                    order=2,
                    title="Clean sellers",
                    instructions=(
                        "Return the list of `salesperson` names that appear in "
                        "`sales` but **not** in `returns`. Sort alphabetically."
                    ),
                    solution_query=(
                        "SELECT salesperson FROM sales "
                        "EXCEPT SELECT salesperson FROM returns "
                        "ORDER BY salesperson;"
                    ),
                    expected_result=_result(
                        ["salesperson"], [["Charlie"]]
                    ),
                    datasets=["ch8_sales"],
                    difficulty=Difficulty.MEDIUM,
                    hints=[
                        "`EXCEPT` subtracts the second set from the first.",
                        "Only Charlie has sales and no returns.",
                    ],
                ),
            ],
        ),
    ],
    quiz=ExerciseSpec(
        order=100,
        title="Chapter 8 Quiz — Net Performance",
        instructions=(
            "For every salesperson who has sold anything, report their "
            "`salesperson`, their total sales (alias `sales_total`), total "
            "returns (alias `returns_total`, `0` when there are none), and "
            "their net result (`sales_total - returns_total`, alias `net`). "
            "Sort by `net` descending. Use CTEs to keep the query tidy."
        ),
        solution_query=(
            "WITH sale_totals AS ("
            "  SELECT salesperson, SUM(amount) AS total FROM sales "
            "  GROUP BY salesperson"
            "), return_totals AS ("
            "  SELECT salesperson, SUM(amount) AS total FROM returns "
            "  GROUP BY salesperson"
            ") "
            "SELECT s.salesperson, s.total AS sales_total, "
            "COALESCE(r.total, 0) AS returns_total, "
            "s.total - COALESCE(r.total, 0) AS net "
            "FROM sale_totals s "
            "LEFT JOIN return_totals r ON s.salesperson = r.salesperson "
            "ORDER BY net DESC;"
        ),
        expected_result=_result(
            ["salesperson", "sales_total", "returns_total", "net"],
            [
                ["Charlie", 49000, 0, 49000],
                ["Alice", 39000, 500, 38500],
                ["Bob", 20000, 200, 19800],
                ["Diana", 15000, 300, 14700],
            ],
            ordered=True,
        ),
        datasets=["ch8_sales"],
        difficulty=Difficulty.HARD,
        is_chapter_quiz=True,
        hints=[
            "Two CTEs: one per-salesperson sum from `sales`, one from `returns`.",
            "LEFT JOIN them on salesperson so sellers without returns still appear.",
            "`COALESCE(r.total, 0)` keeps the arithmetic safe for salespeople with no returns.",
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
    help = "Seed chapters 1-8 of the SQLearn curriculum. Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        schemas = {spec["name"]: _upsert_schema(spec) for spec in SCHEMAS}
        self.stdout.write(f"  ✓ {len(schemas)} sandbox schemas")

        for chapter_spec in (CH1, CH2, CH3, CH4, CH5, CH6, CH7, CH8):
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
