from __future__ import annotations

# (level, title, cumulative XP threshold) — spec Section 4.2
LEVELS: list[tuple[int, str, int]] = [
    (1, "Row Reader", 0),
    (2, "Data Rookie", 100),
    (3, "Filter Finder", 300),
    (4, "Join Juggler", 600),
    (5, "Query Crafter", 1000),
    (6, "Index Seeker", 1500),
    (7, "Schema Sculptor", 2200),
    (8, "Table Titan", 3000),
    (9, "Query Master", 4000),
    (10, "Grandmaster", 5500),
]


def level_for_xp(xp: int) -> int:
    current = 1
    for level, _title, threshold in LEVELS:
        if xp >= threshold:
            current = level
        else:
            break
    return current


def title_for_level(level: int) -> str:
    for lvl, title, _ in LEVELS:
        if lvl == level:
            return title
    return LEVELS[-1][1]


def threshold_for_level(level: int) -> int:
    for lvl, _title, threshold in LEVELS:
        if lvl == level:
            return threshold
    return LEVELS[-1][2]


def next_threshold(level: int) -> int | None:
    """XP required to reach the next level, or None if at max."""
    for lvl, _title, threshold in LEVELS:
        if lvl == level + 1:
            return threshold
    return None
