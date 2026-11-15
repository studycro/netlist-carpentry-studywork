"""SDF semantics: turns s-expressions into the typed models of `sdf_models`.

The generic layer below it (tokenizing, parentheses, tree helpers) lives in `sdf_tokenizer`.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from .sdf_models import (
    ABSOLUTE,
    DEFAULT_TIMESCALE,
    DEFAULT_TIMESCALE_SECONDS,
    INCREMENTAL,
    DelayContext,
    DelayTriplet,
    DelayType,
    SdfCell,
    SdfDelayFile,
    SdfIoPathSpec,
)
from .sdf_tokenizer import find_tagged, has_tag, parse_tokens, stringify, tokenize

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
TAG_RETAIN = "RETAIN"
TAG_COND = "COND"
TAG_CONDELSE = "CONDELSE"

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


def _extract_divider(delayfile_node: list[Any]) -> str:
    entry = find_tagged(delayfile_node, TAG_DIVIDER)
    if entry is not None and len(entry) > 1:
        return str(entry[1])
    return DEFAULT_DIVIDER


def _extract_timescale(delayfile_node: list[Any]) -> tuple[str, float]:
    entry = find_tagged(delayfile_node, TAG_TIMESCALE)
    if entry is not None and len(entry) > 1:
        return parse_timescale(entry[1:])
    return DEFAULT_TIMESCALE, DEFAULT_TIMESCALE_SECONDS


def _iter_iopath_entries(
    node: Any,
    context: DelayContext,
) -> list[tuple[list[Any], DelayContext]]:
    """IOPATH entries of one DELAY-section child, descending into COND and CONDELSE.

    `context` describes the enclosing delay section; a COND or CONDELSE wrapper
    refines it, so conditional delays keep their condition instead of being dropped.
    """
    if has_tag(node, TAG_IOPATH):
        return [(node, context)]

    if has_tag(node, TAG_CONDELSE):
        refined = replace(context, is_condelse=True)
        return [(child, refined) for child in node[1:] if has_tag(child, TAG_IOPATH)]

    if has_tag(node, TAG_COND):
        children = node[1:]
        split = next(
            (i for i, child in enumerate(children) if has_tag(child, TAG_IOPATH)),
            len(children),
        )
        condition = " ".join(stringify(part) for part in children[:split]) or None
        refined = replace(context, condition=condition)
        return [
            (child, refined)
            for child in children[split:]
            if has_tag(child, TAG_IOPATH)
        ]

    return []


def _build_iopath_spec(entry: list[Any], context: DelayContext) -> SdfIoPathSpec:
    _, raw_src_spec, raw_dst_spec, *rest = entry
    raw_src, src_edge = extract_port_and_edge(raw_src_spec)
    raw_dst, dst_edge = extract_port_and_edge(raw_dst_spec)

    retain: tuple[DelayTriplet, ...] = ()
    if rest and has_tag(rest[0], TAG_RETAIN):
        retain = tuple(parse_delay_triplet(value) for value in rest[0][1:])
        rest = rest[1:]

    delays = tuple(parse_delay_triplet(value) for value in rest)

    return SdfIoPathSpec(
        raw_src=raw_src,
        raw_dst=raw_dst,
        delays=delays,
        src_edge=src_edge,
        dst_edge=dst_edge,
        context=context,
        retain=retain,
    )


def _extract_iopaths_from_delay(delay_entries: list[Any]) -> list[SdfIoPathSpec]:
    """Reads the ABSOLUTE and INCREMENTAL sections of one DELAY block.

    Any other section is skipped instead of being mistaken for an ABSOLUTE one.
    COND and CONDELSE wrappers are descended into.
    """
    specs: list[SdfIoPathSpec] = []
    for block in delay_entries:
        if not isinstance(block, list) or not block:
            continue

        delay_type = DELAY_TYPE_TAGS.get(str(block[0]))
        if delay_type is None:
            continue

        context = DelayContext(delay_type=delay_type)
        for child in block[1:]:
            specs.extend(
                _build_iopath_spec(entry, entry_context)
                for entry, entry_context in _iter_iopath_entries(child, context)
            )
    return specs


def _build_cell(entry: Any) -> SdfCell | None:
    if not has_tag(entry, TAG_CELL):
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
    if not ast or not has_tag(ast[0], TAG_DELAYFILE):
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