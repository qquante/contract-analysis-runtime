"""Load design specs from the repository design files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import DesignSpec, ModelValidationError


class DesignLoadError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def load_design(path: str | Path) -> DesignSpec:
    path = Path(path)
    if not path.is_file():
        raise DesignLoadError("design_not_found", f"Design file not found: {path}")
    try:
        payload = parse_simple_yaml(path.read_text(encoding="utf-8"))
        return DesignSpec.from_json(payload)
    except ModelValidationError as exc:
        raise DesignLoadError(exc.code, exc.message) from exc
    except ValueError as exc:
        raise DesignLoadError("invalid_design_yaml", str(exc)) from exc


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by design.yaml.

    Supported shape:
    - top-level scalars;
    - top-level maps;
    - top-level list of maps;
    - string/bool values;
    - list of scalar strings.
    """

    root: dict[str, Any] = {}
    lines = [line.rstrip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(" "):
            raise ValueError(f"Unexpected indentation at top level: {line}")
        key, raw = _split_key_value(line)
        if raw:
            root[key] = _parse_scalar(raw)
            i += 1
            continue
        child_indent = _next_indent(lines, i + 1)
        if child_indent is None:
            root[key] = None
            i += 1
        elif lines[i + 1].lstrip().startswith("- "):
            values, i = _parse_list(lines, i + 1, child_indent)
            root[key] = values
        else:
            mapping, i = _parse_mapping(lines, i + 1, child_indent)
            root[key] = mapping
    return root


def _parse_mapping(lines: list[str], start: int, indent: int) -> tuple[dict[str, Any], int]:
    payload: dict[str, Any] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        current_indent = _indent(line)
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError(f"Unexpected mapping indentation: {line}")
        key, raw = _split_key_value(line.strip())
        if raw:
            payload[key] = _parse_scalar(raw)
            i += 1
            continue
        next_indent = _next_indent(lines, i + 1)
        if next_indent is None or next_indent <= indent:
            payload[key] = None
            i += 1
        elif lines[i + 1].lstrip().startswith("- "):
            values, i = _parse_list(lines, i + 1, next_indent)
            payload[key] = values
        else:
            values, i = _parse_mapping(lines, i + 1, next_indent)
            payload[key] = values
    return payload, i


def _parse_list(lines: list[str], start: int, indent: int) -> tuple[list[Any], int]:
    values: list[Any] = []
    i = start
    while i < len(lines):
        line = lines[i]
        current_indent = _indent(line)
        if current_indent < indent:
            break
        if current_indent != indent or not line.lstrip().startswith("- "):
            raise ValueError(f"Unexpected list item: {line}")
        raw_item = line.strip()[2:].strip()
        if not raw_item:
            item: dict[str, Any] = {}
            i += 1
        elif ":" in raw_item:
            key, raw = _split_key_value(raw_item)
            item = {key: _parse_scalar(raw) if raw else None}
            i += 1
        else:
            values.append(_parse_scalar(raw_item))
            i += 1
            continue

        while i < len(lines):
            next_indent = _indent(lines[i])
            if next_indent <= indent:
                break
            key, raw = _split_key_value(lines[i].strip())
            if raw:
                item[key] = _parse_scalar(raw)
                i += 1
                continue
            nested_indent = _next_indent(lines, i + 1)
            if nested_indent is None or nested_indent <= next_indent:
                item[key] = None
                i += 1
            elif lines[i + 1].lstrip().startswith("- "):
                nested, i = _parse_list(lines, i + 1, nested_indent)
                item[key] = nested
            else:
                nested, i = _parse_mapping(lines, i + 1, nested_indent)
                item[key] = nested
        values.append(item)
    return values, i


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Expected key/value line: {line}")
    key, raw = line.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Empty key: {line}")
    return key, raw.strip()


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw in {"true", "True"}:
        return True
    if raw in {"false", "False"}:
        return False
    if raw in {"null", "Null", "~"}:
        return None
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        return raw[1:-1]
    return raw


def _next_indent(lines: list[str], start: int) -> int | None:
    if start >= len(lines):
        return None
    return _indent(lines[start])


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
