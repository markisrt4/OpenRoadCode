# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Load the deliberately small CSS vocabulary used by OpenRoadCode themes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import tinycss2

from .theme_bundle import ThemeBundle
from .ui_theme import UiTheme

_VAR_PATTERN = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*\)")


@dataclass(frozen=True, slots=True)
class StyleSheet:
    """Parsed CSS declarations indexed by simple selector."""

    rules: dict[str, dict[str, str]]

    def declarations(self, selector: str) -> dict[str, str]:
        return dict(self.rules.get(selector, {}))

    def value(self, selector: str, property_name: str) -> str:
        try:
            return self.rules[selector][property_name]
        except KeyError as exc:
            raise KeyError(f"Missing CSS value {selector} {property_name}") from exc


def load_style_sheet(path: str | Path) -> StyleSheet:
    """Parse a theme CSS file and resolve CSS custom-property references."""

    source = Path(path).read_text(encoding="utf-8")
    parsed = tinycss2.parse_stylesheet(source, skip_comments=True, skip_whitespace=True)
    rules: dict[str, dict[str, str]] = {}

    for rule in parsed:
        if rule.type == "error":
            raise ValueError(f"Invalid CSS in {path}: {rule.message}")
        if rule.type != "qualified-rule":
            continue

        selector = tinycss2.serialize(rule.prelude).strip()
        if not selector:
            continue

        declarations = tinycss2.parse_declaration_list(
            rule.content,
            skip_comments=True,
            skip_whitespace=True,
        )
        values = rules.setdefault(selector, {})
        for declaration in declarations:
            if declaration.type == "error":
                raise ValueError(f"Invalid declaration in {path}: {declaration.message}")
            if declaration.type != "declaration":
                continue
            values[declaration.name] = tinycss2.serialize(declaration.value).strip()

    variables = rules.get(":root", {})
    resolved = {
        selector: {
            name: _resolve_variables(value, variables)
            for name, value in declarations.items()
        }
        for selector, declarations in rules.items()
    }
    return StyleSheet(resolved)


def load_ui_theme(path: str | Path) -> UiTheme:
    """Load the semantic :root palette from an ORC theme stylesheet."""

    return _ui_theme_from_sheet(load_style_sheet(path), path)


def load_theme_bundle(path: str | Path) -> ThemeBundle:
    """Load one stylesheet and its resolved semantic UI theme."""

    sheet = load_style_sheet(path)
    return ThemeBundle(
        ui=_ui_theme_from_sheet(sheet, path),
        style_sheet=sheet,
    )


def _ui_theme_from_sheet(sheet: StyleSheet, path: str | Path) -> UiTheme:
    root = sheet.declarations(":root")

    def required(name: str) -> str:
        try:
            return root[name]
        except KeyError as exc:
            raise ValueError(
                f"Theme {path} is missing required property {name}"
            ) from exc

    return UiTheme(
        background=required("--background"),
        surface=required("--surface"),
        surface_alt=required("--surface-alt"),
        border=required("--border"),
        text=required("--text"),
        text_muted=required("--text-muted"),
        accent_primary=required("--accent-primary"),
        accent_success=required("--accent-success"),
        accent_warning=required("--accent-warning"),
        accent_danger=required("--accent-danger"),
        control_background=required("--control-background"),
        control_active=required("--control-active"),
        control_text=required("--control-text"),
    )


def _resolve_variables(value: str, variables: dict[str, str]) -> str:
    """Resolve the simple var(--name) references supported by ORC themes."""

    def resolve(text: str, stack: tuple[str, ...]) -> str:
        def replace(match: re.Match[str]) -> str:
            variable = match.group(1)

            if variable in stack:
                chain = " -> ".join((*stack, variable))
                raise ValueError(
                    f"Cyclic CSS custom property reference: {chain}"
                )

            try:
                replacement = variables[variable]
            except KeyError as exc:
                raise ValueError(
                    f"Undefined CSS custom property: {variable}"
                ) from exc

            return resolve(replacement, (*stack, variable))

        return _VAR_PATTERN.sub(replace, text)

    return resolve(value, ())
