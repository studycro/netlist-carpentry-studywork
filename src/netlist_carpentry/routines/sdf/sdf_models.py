"""Typed data models for the SDF AST."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, NamedTuple


class DelayTriplet(NamedTuple):
    """Delay in SDF order (min, typ, max). Missing values are None."""

    min: float | None
    typ: float | None
    max: float | None

    def to_list(self) -> list[float | None]:
        """Plain list, as accepted by the Netlist Carpentry metadata."""
        return [self.min, self.typ, self.max]

    @classmethod
    def from_list(cls, values: Sequence[float | None]) -> DelayTriplet:
        """Inverse of `to_list`."""
        if len(values) != 3:
            raise ValueError(f"Expected 3 values (min, typ, max), got {len(values)}.")
        return cls(values[0], values[1], values[2])


@dataclass(frozen=True)
class SdfIoPathSpec:
    """Raw IOPATH specification from an SDF CELL block."""

    raw_src: str
    raw_dst: str
    rise: DelayTriplet
    fall: DelayTriplet
    src_edge: str | None = None
    dst_edge: str | None = None


@dataclass(frozen=True)
class SdfCell:
    """A CELL block of one instance in the SDF file."""

    instance_name: str
    cell_type: str | None = None
    iopaths: tuple[SdfIoPathSpec, ...] = ()


@dataclass(frozen=True)
class SdfDelayFile:
    """Root node of the parsed SDF AST."""

    divider: str = "."
    cells: tuple[SdfCell, ...] = ()