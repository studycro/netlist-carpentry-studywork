"""SDF semantics: turns s-expressions into the typed models of `sdf_models`.

The generic layer below it (tokenizing, parentheses, tree helpers) lives in `sdf_tokenizer`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
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
    SdfHeader,
    SdfIoPathSpec,
)
from .sdf_tokenizer import find_tagged, has_tag, parse_tokens, stringify, tokenize

__all__ = ["parse_sdf", "parse_sdf_file"]

_TRIPLET_SIZE = 3
_DEFAULT_DIVIDER = "."

_TAG_DELAYFILE = "DELAYFILE"
_TAG_SDFVERSION = "SDFVERSION"
_TAG_DESIGN = "DESIGN"
_TAG_DATE = "DATE"
_TAG_VENDOR = "VENDOR"
_TAG_PROGRAM = "PROGRAM"
_TAG_VERSION = "VERSION"
_TAG_VOLTAGE = "VOLTAGE"
_TAG_PROCESS = "PROCESS"
_TAG_TEMPERATURE = "TEMPERATURE"
_TAG_DIVIDER = "DIVIDER"
_TAG_TIMESCALE = "TIMESCALE"
_TAG_CELL = "CELL"
_TAG_CELLTYPE = "CELLTYPE"
_TAG_INSTANCE = "INSTANCE"
_TAG_DELAY = "DELAY"
_TAG_IOPATH = "IOPATH"
_TAG_RETAIN = "RETAIN"
_TAG_COND = "COND"
_TAG_CONDELSE = "CONDELSE"

_DELAY_TYPE_TAGS: dict[str, DelayType] = {
    "ABSOLUTE": ABSOLUTE,
    "INCREMENTAL": INCREMENTAL,
}

_TIMESCALE_UNITS_IN_SECONDS = {
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
    "ps": 1e-12,
    "fs": 1e-15,
}

_TIMESCALE_PATTERN = re.compile(
    r"\s*(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>ms|us|ns|ps|fs|s)\s*",
    re.IGNORECASE,
)

def _parse_delay_triplet(raw_val: list[str] | str) -> DelayTriplet:
    """DelayTriplet(min, typ, max)."""
    val_str = raw_val[0] if isinstance(raw_val, list) else raw_val
    parts: list[float | None] = [float(p) if p else None for p in val_str.split(":")]

    while len(parts) < _TRIPLET_SIZE:
        parts.append(parts[-1])

    min_val, typ_val, max_val = parts[:_TRIPLET_SIZE]
    return DelayTriplet(min=min_val, typ=typ_val, max=max_val)


def _extract_port_and_edge(raw_port: str | list[str]) -> tuple[str, str | None]:
    """['posedge', 'CLK'] -> ('CLK', 'posedge'); 'A' -> ('A', None)."""
    if isinstance(raw_port, list):
        edge, port = raw_port
        return port, edge
    return raw_port, None


def _parse_timescale(raw_value: list[Any]) -> tuple[str, float]:
    text = "".join(str(part) for part in raw_value)
    match = _TIMESCALE_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"Unknown TIMESCALE value {text!r}.")

    number = float(match.group("number"))
    unit = match.group("unit").lower()
    return text.strip(), number * _TIMESCALE_UNITS_IN_SECONDS[unit]

def _extract_divider(delayfile_node: list[Any]) -> str:
    entry = find_tagged(delayfile_node, _TAG_DIVIDER)
    if entry is not None and len(entry) > 1:
        return str(entry[1])
    return _DEFAULT_DIVIDER

def _header_text(delayfile_node: list[Any], tag: str) -> str | None:
    entry = find_tagged(delayfile_node, tag)
    if entry is None or len(entry) < 2:
        return None
    return str(entry[1])


def _header_triplet(delayfile_node: list[Any], tag: str) -> DelayTriplet | None:
    text = _header_text(delayfile_node, tag)
    if text is None:
        return None
    try:
        return _parse_delay_triplet(text)
    except ValueError as exc:
        raise ValueError(f"Cannot read {tag} value {text!r}: {exc}") from exc


def _extract_header(delayfile_node: list[Any]) -> SdfHeader:
    return SdfHeader(
        sdf_version=_header_text(delayfile_node, _TAG_SDFVERSION),
        design=_header_text(delayfile_node, _TAG_DESIGN),
        date=_header_text(delayfile_node, _TAG_DATE),
        vendor=_header_text(delayfile_node, _TAG_VENDOR),
        program=_header_text(delayfile_node, _TAG_PROGRAM),
        program_version=_header_text(delayfile_node, _TAG_VERSION),
        voltage=_header_triplet(delayfile_node, _TAG_VOLTAGE),
        process=_header_text(delayfile_node, _TAG_PROCESS),
        temperature=_header_triplet(delayfile_node, _TAG_TEMPERATURE),
    )


def _extract_timescale(delayfile_node: list[Any]) -> tuple[str, float]:
    entry = find_tagged(delayfile_node, _TAG_TIMESCALE)
    if entry is not None and len(entry) > 1:
        return _parse_timescale(entry[1:])
    return DEFAULT_TIMESCALE, DEFAULT_TIMESCALE_SECONDS


_IoPathEntries = list[tuple[list[Any], DelayContext]]

_DelayChildHandler = Callable[[list[Any], DelayContext], _IoPathEntries]


def _iopath_children(children: list[Any], context: DelayContext) -> _IoPathEntries:
    """Pairs every IOPATH among `children` with `context`."""
    return [(child, context) for child in children if has_tag(child, _TAG_IOPATH)]


def _unwrap_iopath(node: list[Any], context: DelayContext) -> _IoPathEntries:
    """A bare `(IOPATH ...)`: the context stays as it is."""
    return [(node, context)]


def _unwrap_condelse(node: list[Any], context: DelayContext) -> _IoPathEntries:
    """`(CONDELSE (IOPATH ...) ...)`: marks the paths as the default branch."""
    return _iopath_children(node[1:], replace(context, is_condelse=True))


def _unwrap_cond(node: list[Any], context: DelayContext) -> _IoPathEntries:
    """`(COND <expression> (IOPATH ...) ...)`: everything before the first IOPATH
    belongs to the condition expression."""
    children = node[1:]
    split = next(
        (i for i, child in enumerate(children) if has_tag(child, _TAG_IOPATH)),
        len(children),
    )
    condition = " ".join(stringify(part) for part in children[:split]) or None
    return _iopath_children(children[split:], replace(context, condition=condition))


_DELAY_CHILD_HANDLERS: dict[str, _DelayChildHandler] = {
    _TAG_IOPATH: _unwrap_iopath,
    _TAG_CONDELSE: _unwrap_condelse,
    _TAG_COND: _unwrap_cond,
}

def _iter_iopath_entries(node: Any, context: DelayContext) -> _IoPathEntries:
    """IOPATH entries of one DELAY-section child, descending into known wrappers.

    `context` describes the enclosing delay section; a wrapper refines it, so
    conditional delays keep their condition instead of being dropped. A child with
    no handler yields nothing.
    """
    if not isinstance(node, list) or not node:
        return []

    handler = _DELAY_CHILD_HANDLERS.get(str(node[0]))
    return handler(node, context) if handler is not None else []


def _build_iopath_spec(entry: list[Any], context: DelayContext) -> SdfIoPathSpec:
    _, raw_src_spec, raw_dst_spec, *rest = entry
    raw_src, src_edge = _extract_port_and_edge(raw_src_spec)
    raw_dst, dst_edge = _extract_port_and_edge(raw_dst_spec)

    retain: tuple[DelayTriplet, ...] = ()
    if rest and has_tag(rest[0], _TAG_RETAIN):
        retain = tuple(_parse_delay_triplet(value) for value in rest[0][1:])
        rest = rest[1:]

    delays = tuple(_parse_delay_triplet(value) for value in rest)

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

        delay_type = _DELAY_TYPE_TAGS.get(str(block[0]))
        if delay_type is None:
            continue

        context = DelayContext(delay_type=delay_type)
        for child in block[1:]:
            specs.extend(
                _build_iopath_spec(entry, entry_context)
                for entry, entry_context in _iter_iopath_entries(child, context)
            )
    return specs


@dataclass
class _CellBuilder:
    """Collects what the handlers below read out of one CELL block.

    A new construct adds a field here and a handler, not a branch in `_build_cell`.
    """

    instance_name: str | None = None
    cell_type: str | None = None
    iopaths: list[SdfIoPathSpec] = field(default_factory=list)

    def build(self) -> SdfCell | None:
        """The finished cell, or None when the block carries no INSTANCE."""
        if not self.instance_name:
            return None
        return SdfCell(
            instance_name=self.instance_name,
            cell_type=self.cell_type,
            iopaths=tuple(self.iopaths),
        )


_CellHandler = Callable[[_CellBuilder, list[Any]], None]


def _handle_instance(builder: _CellBuilder, payload: list[Any]) -> None:
    if payload:
        builder.instance_name = str(payload[0])


def _handle_celltype(builder: _CellBuilder, payload: list[Any]) -> None:
    if payload:
        builder.cell_type = str(payload[0])


def _handle_delay(builder: _CellBuilder, payload: list[Any]) -> None:
    builder.iopaths.extend(_extract_iopaths_from_delay(payload))


_CELL_HANDLERS: dict[str, _CellHandler] = {
    _TAG_INSTANCE: _handle_instance,
    _TAG_CELLTYPE: _handle_celltype,
    _TAG_DELAY: _handle_delay,
}

def _build_cell(entry: Any) -> SdfCell | None:
    """Reads one `(CELL ...)` block. Constructs without a handler are skipped."""
    if not has_tag(entry, _TAG_CELL):
        return None

    builder = _CellBuilder()
    for item in entry[1:]:
        if not isinstance(item, list) or not item:
            continue
        handler = _CELL_HANDLERS.get(str(item[0]))
        if handler is not None:
            handler(builder, item[1:])

    return builder.build()


def parse_sdf(text: str) -> SdfDelayFile:
    """Parses SDF text directly into a typed SdfDelayFile object."""
    ast = parse_tokens(tokenize(text))
    if not ast or not has_tag(ast[0], _TAG_DELAYFILE):
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
        header=_extract_header(delayfile_node),
    )


def parse_sdf_file(path: str | Path) -> SdfDelayFile:
    """Reads an SDF file and returns a typed SdfDelayFile object."""
    return parse_sdf(Path(path).read_text(encoding="utf-8"))