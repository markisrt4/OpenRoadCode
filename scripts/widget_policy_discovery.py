# SPDX-License-Identifier: MIT

"""Find UiWidget inheritance without importing widgets or loading a toolkit."""

import ast
import os
from pathlib import Path


MARKER = "ui.ui_widget.UiWidget"
EXCLUDED = {
    "venv", ".venv", "node_modules", "__pycache__",
    "unit_test", "integration_test", "component_test",
}


def _sources(root):
    for directory, children, files in os.walk(root):
        children[:] = [name for name in children
                       if name not in EXCLUDED and not name.startswith(".")]
        for name in files:
            if name.endswith(".py") and not name.startswith("test_"):
                yield Path(directory) / name


def _module(path):
    parts = path.with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name(node.value)
        return f"{parent}.{node.attr}" if parent else None
    if isinstance(node, ast.Subscript):
        return _name(node.value)
    return None


def discover_widgets(root):
    """Resolve static bases, import aliases and re-exports across source modules.

    This is static discovery, not runtime type checking. Dynamic class factories
    and computed imports are outside its scope; directory rules still apply.
    """
    edges = {"ui.UiWidget": {MARKER}}
    owners = {}
    for path in sorted(_sources(root)):
        relative = path.relative_to(root)
        module = _module(relative)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
        except SyntaxError:
            # Unrelated legacy files may not parse; Ruff checks source syntax.
            continue
        imports = {}
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.asname or alias.name.split(".")[0]] = (
                        alias.name if alias.asname else alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                source = node.module or ""
                if node.level:
                    package = module.split(".") if path.name == "__init__.py" else module.split(".")[:-1]
                    source = ".".join(package[:len(package) - node.level + 1]
                                      + ([source] if source else []))
                for alias in node.names:
                    if alias.name != "*":
                        local = alias.asname or alias.name
                        target = f"{source}.{alias.name}"
                        imports[local] = target
                        edges.setdefault(f"{module}.{local}", set()).add(target)

        def resolve(node):
            name = _name(node)
            if name is None:
                return None
            first, _, rest = name.partition(".")
            target = imports.get(first, f"{module}.{first}")
            return f"{target}.{rest}" if rest else target

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                name = f"{module}.{node.name}"
                owners[name] = path
                edges.setdefault(name, set()).update(
                    target for base in node.bases if (target := resolve(base)))
            elif isinstance(node, ast.Assign):
                target = resolve(node.value)
                if target is not None:
                    for alias in node.targets:
                        if isinstance(alias, ast.Name):
                            edges.setdefault(f"{module}.{alias.id}", set()).add(target)

    marked = {MARKER}
    while True:
        added = {name for name, bases in edges.items() if bases & marked} - marked
        if not added:
            break
        marked.update(added)
    return {owners[name] for name in marked if name in owners}
