"""Regression tests for S1-CRIT-2a: no hardcoded GATEWAY_SECRET."""
import ast
import os
import re

# Root of backend-microservices
BACKEND_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
HARDCODED_SECRET = "gateway-internal-secret-key"
SKIP_DIRS = {"venv", "__pycache__", ".git", "node_modules", ".eggs", "*.egg-info"}


def _collect_py_files(root, exclude_tests=True):
    """Collect .py files under root, optionally excluding tests/ dirs."""
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith('.egg-info')]
        if exclude_tests and os.path.basename(dirpath) == 'tests':
            continue
        for f in filenames:
            if f.endswith('.py'):
                results.append(os.path.join(dirpath, f))
    return results


class TestNoHardcodedGatewaySecret:
    """should detect hardcoded gateway secrets in source files."""

    def test_should_have_zero_hardcoded_secrets_when_scanning_source_py(self):
        """Scan all non-test .py files for hardcoded GATEWAY_SECRET string."""
        violations = []
        for fpath in _collect_py_files(BACKEND_ROOT, exclude_tests=True):
            with open(fpath, encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if HARDCODED_SECRET in line and not line.lstrip().startswith('#'):
                        rel = os.path.relpath(fpath, BACKEND_ROOT)
                        violations.append(f"{rel}:{i}: {line.strip()}")
        assert violations == [], (
            f"Found {len(violations)} hardcoded GATEWAY_SECRET:\n" +
            "\n".join(violations)
        )

    def test_should_have_zero_hardcoded_secrets_when_scanning_go_files(self):
        """Scan .go files for hardcoded GATEWAY_SECRET string."""
        violations = []
        for dirpath, dirnames, filenames in os.walk(BACKEND_ROOT):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                if f.endswith('.go'):
                    fpath = os.path.join(dirpath, f)
                    with open(fpath, encoding='utf-8', errors='ignore') as fh:
                        for i, line in enumerate(fh, 1):
                            if HARDCODED_SECRET in line and not line.lstrip().startswith('//'):
                                rel = os.path.relpath(fpath, BACKEND_ROOT)
                                violations.append(f"{rel}:{i}: {line.strip()}")
        assert violations == [], (
            f"Found {len(violations)} hardcoded GATEWAY_SECRET in Go:\n" +
            "\n".join(violations)
        )

    def test_should_have_zero_hardcoded_secrets_when_scanning_bat_files(self):
        """Scan .bat files for hardcoded GATEWAY_SECRET string."""
        violations = []
        for dirpath, dirnames, filenames in os.walk(BACKEND_ROOT):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                if f.endswith('.bat'):
                    fpath = os.path.join(dirpath, f)
                    with open(fpath, encoding='utf-8', errors='ignore') as fh:
                        for i, line in enumerate(fh, 1):
                            if HARDCODED_SECRET in line and not line.lstrip().startswith('REM'):
                                rel = os.path.relpath(fpath, BACKEND_ROOT)
                                violations.append(f"{rel}:{i}: {line.strip()}")
        assert violations == [], (
            f"Found {len(violations)} hardcoded GATEWAY_SECRET in bat:\n" +
            "\n".join(violations)
        )
