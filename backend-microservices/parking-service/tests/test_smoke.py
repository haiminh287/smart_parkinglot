"""Smoke tests — verify service files parse and load correctly.

Refs: S1-CRIT-1
"""

import ast
from pathlib import Path

PARKING_SERVICE_ROOT = Path(__file__).resolve().parent.parent


def test_views_py_parses():
    """Regression: views.py had duplicate block at EOF causing SyntaxError."""
    views_path = PARKING_SERVICE_ROOT / "infrastructure" / "views.py"
    source = views_path.read_text(encoding="utf-8")
    # ast.parse raises SyntaxError if invalid
    ast.parse(source, filename=str(views_path))


def test_no_duplicate_trailing_block_in_views():
    """Regression: duplicate 'zone' + }) block at end of views.py."""
    views_path = PARKING_SERVICE_ROOT / "infrastructure" / "views.py"
    source = views_path.read_text(encoding="utf-8")
    lines = source.rstrip().splitlines()
    # File should end with }) closing the Response dict, not a duplicate
    last_content_lines = [l.strip() for l in lines[-5:] if l.strip()]
    # Count occurrences of the closing pattern
    closing_count = sum(1 for l in last_content_lines if l == "})")
    assert (
        closing_count <= 1
    ), f"Found {closing_count} '}})' in last 5 lines — possible duplicate block"
