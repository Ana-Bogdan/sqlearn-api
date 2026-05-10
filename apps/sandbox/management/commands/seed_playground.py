"""Seed (or refresh) the free Sandbox playground SandboxSchema.

The playground is one e-commerce-themed dataset with five related tables —
``customers``, ``products``, ``categories``, ``orders``, ``order_items`` —
designed to support every chapter's query patterns: filters, aggregates,
joins (inner, left, multi-step), subqueries, and modifications.

Idempotent: re-running just refreshes the row in place.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.sandbox.models import SandboxSchema

PLAYGROUND_NAME = "Playground — E-commerce store"
PLAYGROUND_DESCRIPTION = (
    "A small e-commerce dataset for free exploration. Customers in five "
    "countries place orders containing one or more products from four "
    "categories. Use it to practice joins, aggregates, filters, and "
    "subqueries — or to invent your own questions."
)

PLAYGROUND_SCHEMA_SQL = """
CREATE TABLE categories (
    id          INTEGER PRIMARY KEY,
    name        VARCHAR(80)  NOT NULL,
    slug        VARCHAR(80)  NOT NULL UNIQUE
);

INSERT INTO categories (id, name, slug) VALUES
    (1, 'Books',       'books'),
    (2, 'Electronics', 'electronics'),
    (3, 'Home',        'home'),
    (4, 'Outdoors',    'outdoors');

CREATE TABLE customers (
    id           INTEGER PRIMARY KEY,
    full_name    VARCHAR(120) NOT NULL,
    email        VARCHAR(160) NOT NULL UNIQUE,
    country      VARCHAR(60)  NOT NULL,
    signed_up_on DATE         NOT NULL,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE
);

INSERT INTO customers (id, full_name, email, country, signed_up_on, is_active) VALUES
    (1,  'Alina Constantinescu', 'alina@example.com',  'Romania',  DATE '2024-02-14', TRUE),
    (2,  'Mihai Popescu',        'mihai@example.com',  'Romania',  DATE '2024-04-03', TRUE),
    (3,  'Sofia Marinescu',      'sofia@example.com',  'Romania',  DATE '2025-01-09', TRUE),
    (4,  'Lucas Becker',         'lucas@example.com',  'Germany',  DATE '2023-11-20', TRUE),
    (5,  'Hannah Müller',        'hannah@example.com', 'Germany',  DATE '2024-06-30', TRUE),
    (6,  'Daan de Vries',        'daan@example.com',   'Netherlands', DATE '2024-08-18', TRUE),
    (7,  'Eva Janssen',          'eva@example.com',    'Netherlands', DATE '2025-03-05', FALSE),
    (8,  'Pablo García',         'pablo@example.com',  'Spain',    DATE '2023-12-12', TRUE),
    (9,  'Lucia Romero',         'lucia@example.com',  'Spain',    DATE '2024-09-22', TRUE),
    (10, 'Olivia Clarke',        'olivia@example.com', 'Ireland',  DATE '2025-02-28', TRUE);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    category_id INTEGER      NOT NULL REFERENCES categories(id),
    price       NUMERIC(8,2) NOT NULL,
    stock       INTEGER      NOT NULL,
    in_catalog  BOOLEAN      NOT NULL DEFAULT TRUE
);

INSERT INTO products (id, name, category_id, price, stock, in_catalog) VALUES
    (1,  'Designing Data-Intensive Applications', 1, 39.50, 24, TRUE),
    (2,  'The Pragmatic Programmer',              1, 32.00, 12, TRUE),
    (3,  'PostgreSQL: Up and Running',            1, 28.75,  9, TRUE),
    (4,  'Mechanical Keyboard 65%',               2, 119.00, 5, TRUE),
    (5,  'USB-C Hub 7-in-1',                      2, 45.00, 30, TRUE),
    (6,  '4K Webcam',                             2, 89.90,  0, TRUE),
    (7,  'Linen Bedsheet Set',                    3, 64.00, 18, TRUE),
    (8,  'Ceramic Mug — set of 2',                3, 22.50, 60, TRUE),
    (9,  'Wool Blanket',                          3, 78.00,  4, TRUE),
    (10, 'Trail Backpack 28L',                    4, 95.00,  7, TRUE),
    (11, 'Insulated Water Bottle',                4, 29.00, 42, TRUE),
    (12, 'Camping Stove',                         4, 54.00,  0, FALSE);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY,
    customer_id  INTEGER     NOT NULL REFERENCES customers(id),
    placed_on    DATE        NOT NULL,
    status       VARCHAR(20) NOT NULL,
    total        NUMERIC(10,2) NOT NULL
);

INSERT INTO orders (id, customer_id, placed_on, status, total) VALUES
    (1,  1, DATE '2025-03-12', 'shipped',   71.50),
    (2,  1, DATE '2025-04-02', 'delivered', 28.75),
    (3,  2, DATE '2025-04-18', 'delivered', 119.00),
    (4,  3, DATE '2025-04-25', 'pending',   45.00),
    (5,  4, DATE '2025-03-30', 'delivered', 141.50),
    (6,  4, DATE '2025-05-01', 'shipped',   95.00),
    (7,  5, DATE '2025-04-09', 'delivered', 96.00),
    (8,  6, DATE '2025-04-21', 'cancelled', 78.00),
    (9,  6, DATE '2025-05-05', 'pending',   54.00),
    (10, 8, DATE '2025-03-22', 'delivered', 64.00),
    (11, 8, DATE '2025-04-30', 'shipped',   164.00),
    (12, 9, DATE '2025-04-12', 'delivered', 39.50),
    (13, 10, DATE '2025-05-02', 'pending',   89.90);

CREATE TABLE order_items (
    id          INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    unit_price  NUMERIC(8,2) NOT NULL
);

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
    (1,   1,  1,  1, 39.50),
    (2,   1,  8,  1, 22.50),
    (3,   1, 11,  1,  9.50),
    (4,   2,  3,  1, 28.75),
    (5,   3,  4,  1, 119.00),
    (6,   4,  5,  1, 45.00),
    (7,   5,  4,  1, 119.00),
    (8,   5,  8,  1, 22.50),
    (9,   6, 10,  1, 95.00),
    (10,  7,  2,  1, 32.00),
    (11,  7,  7,  1, 64.00),
    (12,  8,  9,  1, 78.00),
    (13,  9, 12,  1, 54.00),
    (14, 10,  7,  1, 64.00),
    (15, 11,  4,  1, 119.00),
    (16, 11,  5,  1, 45.00),
    (17, 12,  1,  1, 39.50),
    (18, 13,  6,  1, 89.90);
""".strip()


class Command(BaseCommand):
    help = "Create or refresh the free-Sandbox playground dataset. Idempotent."

    def handle(self, *args, **options):
        playground, created = SandboxSchema.objects.update_or_create(
            is_playground=True,
            defaults={
                "name": PLAYGROUND_NAME,
                "description": PLAYGROUND_DESCRIPTION,
                "schema_sql": PLAYGROUND_SCHEMA_SQL,
            },
        )
        verb = "Created" if created else "Refreshed"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} playground sandbox: '{playground.name}'."
            )
        )
