"""Enforce the domain's dependency and I/O boundary."""

import ast
from pathlib import Path

import gatherly.domain


def test_domain_imports_only_pure_dependencies_and_never_reads_system_time() -> None:
    """Block adapters, filesystem/network imports, and ambient clock calls in domain."""
    root = Path(gatherly.domain.__file__).parent
    permitted = {
        "datetime",
        "typing",
        "types",
        "dataclasses",
        "collections.abc",
        "pydantic",
    }
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert module in permitted or module.startswith("gatherly.domain"), path
            if isinstance(node, ast.Import):
                assert all(alias.name in permitted for alias in node.names), path
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in {
                        "open",
                        "print",
                        "input",
                        "__import__",
                    }, path
                if isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in {"today", "now", "utcnow"}, path
