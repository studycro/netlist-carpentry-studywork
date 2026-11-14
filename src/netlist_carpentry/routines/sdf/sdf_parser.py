"""Parser and AST builder for SDF files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .sdf_models import (
    ABSOLUTE,
    DEFAULT_TIMESCALE,
    DEFAULT_TIMESCALE_SECONDS,
    DelayTriplet,
    DelayType,
    INCREMENTAL,
    SdfCell,
    SdfDelayFile,
    SdfIoPathSpec,
)

TRIPLET_SIZE = 3
DEFAULT_DIVIDER = "."

TAG_DELAYFILE = "DELAYFILE"
TAG_DIVIDER = "DIVIDER"
TAG_TIMESCALE = "TIMESCALE"
TAG_CELL = "CELL"
TAG_CELLTYPE = "CELLTYPE"
TAG_INSTANCE = "INSTANCE"
TAG_DELAY = "DELAY"
TAG_IOPATH = "IOPATH"

DELAY_TYPE_TAGS: dict[str, DelayType] = {
    "ABSOLUTE": ABSOLUTE,
    "INCREMENTAL": INCREMENTAL,
}

TIMESCALE_UNITS_IN_SECONDS = {
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
    "ps": 1e-12,
    "fs": 1e-15,
}

TIMESCALE_PATTERN = re.compile(
    r"\s*(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>ms|us|ns|ps|fs|s)\s*",
    re.IGNORECASE,
)

IGNORED_TOKEN_KINDS = frozenset({"COMMENT", "WS"})

TOKEN_PATTERN = re.compile(
    r"""
    (?P<COMMENT>//[^\n]*|/\*[\s\S]*?\*/) |
    (?P<WS>\s+) |
    (?P<LPAREN>\() |
    (?P<RPAREN>\)) |
    (?P<STRING>"(?:\\.|[^"\\])*") |
    (?P<ESCAPED>\\\S+) |
    (?P<ATOM>[^\s()"]+)
    """,
    re.VERBOSE,
)

def tokenize(text: str) -> list[str]:
    """Turns SDF text into a flat list of tokens."""
    tokens: list[str] = []
    for match in TOKEN_PATTERN.finditer(text):
        kind = match.lastgroup
        if kind in IGNORED_TOKEN_KINDS:
            continue

        value = match.group()
        if kind == "STRING":
            value = value[1:-1]
        tokens.append(value)

    return tokens


def parse_tokens(tokens: list[str]) -> list[Any]:
    """Turns tokens into nested S-expressions (lists)."""
    stack: list[list[Any]] = [[]]
    for token in tokens:
        if token == "(":
            stack.append([])
        elif token == ")":
            if len(stack) == 1:
                raise ValueError("Syntax error: unexpected ')'")
            completed_block = stack.pop()
            stack[-1].append(completed_block)
        else:
            stack[-1].append(token)

    if len(stack) != 1:
        raise ValueError("Syntax error: missing ')'")
    return stack[0]


def parse_delay_triplet(raw_val: list[str] | str) -> DelayTriplet:
    """DelayTriplet(min, typ, max)."""
    val_str = raw_val[0] if isinstance(raw_val, list) else raw_val
    parts: list[float | None] = [float(p) if p else None for p in val_str.split(":")]

    while len(parts) < TRIPLET_SIZE:
        parts.append(parts[-1])

    min_val, typ_val, max_val = parts[:TRIPLET_SIZE]
    return DelayTriplet(min=min_val, typ=typ_val, max=max_val)


def extract_port_and_edge(raw_port: str | list[str]) -> tuple[str, str | None]:
    """['posedge', 'CLK'] -> ('CLK', 'posedge'); 'A' -> ('A', None)."""
    if isinstance(raw_port, list):
        edge, port = raw_port
        return port, edge
    return raw_port, None

def parse_timescale(raw_value: list[Any]) -> tuple[str, float]:
    text = "".join(str(part) for part in raw_value)
    match = TIMESCALE_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"Unknown TIMESCALE value {text!r}.")

    number = float(match.group("number"))
    unit = match.group("unit").lower()
    return text.strip(), number * TIMESCALE_UNITS_IN_SECONDS[unit]

def _has_tag(node: Any, tag: str) -> bool:
    """Checks whether an AST node is a list starting with the expected tag."""
    return isinstance(node, list) and bool(node) and node[0] == tag


def _extract_divider(delayfile_node: list[Any]) -> str:
    for entry in delayfile_node[1:]:
        if _has_tag(entry, TAG_DIVIDER) and len(entry) > 1:
            return str(entry[1])
    return DEFAULT_DIVIDER

def _extract_timescale(delayfile_node: list[Any]) -> tuple[str, float]:
    for entry in delayfile_node[1:]:
        if _has_tag(entry, TAG_TIMESCALE) and len(entry) > 1:
            return parse_timescale(entry[1:])
    return DEFAULT_TIMESCALE, DEFAULT_TIMESCALE_SECONDS

def _build_iopath_spec(entry: list[Any], *, delay_type: DelayType = ABSOLUTE) -> SdfIoPathSpec:
    _, raw_src_spec, raw_dst_spec, rise_spec, *rest = entry
    raw_src, src_edge = extract_port_and_edge(raw_src_spec)
    raw_dst, dst_edge = extract_port_and_edge(raw_dst_spec)

    rise = parse_delay_triplet(rise_spec)
    fall = parse_delay_triplet(rest[0]) if rest else rise

    return SdfIoPathSpec(
        raw_src=raw_src,
        raw_dst=raw_dst,
        rise=rise,
        fall=fall,
        src_edge=src_edge,
        dst_edge=dst_edge,
        delay_type=delay_type,
    )


def _extract_iopaths_from_delay(delay_entries: list[Any]) -> list[SdfIoPathSpec]:
    """Reads the ABSOLUTE and INCREMENTAL sections of one DELAY block.

    Any other section is skipped instead of being mistaken for an ABSOLUTE one.
    """
    specs: list[SdfIoPathSpec] = []
    for block in delay_entries:
        if not isinstance(block, list) or not block:
            continue

        delay_type = DELAY_TYPE_TAGS.get(str(block[0]))
        if delay_type is None:
            continue

        specs.extend(
            _build_iopath_spec(entry, delay_type=delay_type)
            for entry in block[1:]
            if _has_tag(entry, TAG_IOPATH)
        )
    return specs


def _build_cell(entry: Any) -> SdfCell | None:
    if not _has_tag(entry, TAG_CELL):
        return None

    inst_name: str | None = None
    cell_type: str | None = None
    iopaths: list[SdfIoPathSpec] = []

    for item in entry[1:]:
        if not isinstance(item, list) or not item:
            continue
        tag, *payload = item
        if tag == TAG_INSTANCE and payload:
            inst_name = str(payload[0])
        elif tag == TAG_CELLTYPE and payload:
            cell_type = str(payload[0])
        elif tag == TAG_DELAY:
            iopaths.extend(_extract_iopaths_from_delay(payload))

    if not inst_name:
        return None

    return SdfCell(
        instance_name=inst_name,
        cell_type=cell_type,
        iopaths=tuple(iopaths),
    )


def parse_sdf(text: str) -> SdfDelayFile:
    """Parses SDF text directly into a typed SdfDelayFile object."""
    ast = parse_tokens(tokenize(text))
    if not ast or not _has_tag(ast[0], TAG_DELAYFILE):
        raise ValueError("Not a valid SDF file: DELAYFILE block is missing.")

    delayfile_node = ast[0]
    divider = _extract_divider(delayfile_node)
    timescale, timescale_seconds = _extract_timescale(delayfile_node)
    cells = tuple(
        cell
        for entry in delayfile_node[1:]
        if (cell := _build_cell(entry)) is not None
    )
    return SdfDelayFile(
        divider=divider,
        cells=cells,
        timescale=timescale,
        timescale_seconds=timescale_seconds,
    )


def parse_sdf_file(path: str | Path) -> SdfDelayFile:
    """Reads an SDF file and returns a typed SdfDelayFile object."""
    return parse_sdf(Path(path).read_text(encoding="utf-8"))