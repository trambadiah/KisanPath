from __future__ import annotations

import ast
from pathlib import Path


def test_vendor_sdks_are_imported_only_inside_provider_adapters() -> None:
    source_root = Path(__file__).parents[2] / "src" / "kisanpath"
    vendor_roots = {"openai", "anthropic", "google", "ollama"}
    violations: list[str] = []

    for path in source_root.rglob("*.py"):
        relative = path.relative_to(source_root)
        if relative.parts[:2] == ("llm", "providers"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for module in imported:
                if module.split(".", maxsplit=1)[0] in vendor_roots:
                    violations.append(f"{relative}:{node.lineno} imports {module}")

    assert violations == []


def test_domain_and_evaluation_do_not_depend_on_framework_or_provider_layers() -> None:
    source_root = Path(__file__).parents[2] / "src" / "kisanpath"
    owned_roots = [source_root / "domain", source_root / "evaluation"]
    banned = {
        "fastapi",
        "sqlalchemy",
        "openai",
        "anthropic",
        "google",
        "ollama",
        "kisanpath.api",
        "kisanpath.llm",
        "kisanpath.persistence",
        "kisanpath.workflows",
        "kisanpath.agents",
    }
    violations: list[str] = []

    for owned_root in owned_roots:
        for path in owned_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                for module in modules:
                    if any(module == item or module.startswith(f"{item}.") for item in banned):
                        violations.append(f"{path.relative_to(source_root)}:{node.lineno}")

    assert violations == []
