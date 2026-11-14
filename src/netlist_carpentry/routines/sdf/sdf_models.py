"""Typed data models for the SDF AST."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, NamedTuple

DelayType = Literal["ABSOLUTE", "INCREMENTAL"]

ABSOLUTE: DelayType = "ABSOLUTE"
INCREMENTAL: DelayType = "INCREMENTAL"

DEFAULT_TIMESCALE = "1ns"
DEFAULT_TIMESCALE_SECONDS = 1e-9

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
    delays: tuple[DelayTriplet, ...]
    src_edge: str | None = None
    dst_edge: str | None = None
    delay_type: DelayType = ABSOLUTE
    condition: str | None = None
    is_condelse: bool = False

    def __post_init__(self) -> None:
        if not self.delays:
            raise ValueError(f"IOPATH {self.raw_src}->{self.raw_dst} carries no delay value.")

    @property
    def rise(self) -> DelayTriplet:
        return self.delays[0]

    @property
    def fall(self) -> DelayTriplet:
        return self.delays[1] if len(self.delays) > 1 else self.rise

    @property
    def is_conditional(self) -> bool:
        return self.condition is not None or self.is_condelse

    @property
    def is_incremental(self) -> bool:
        return self.delay_type == INCREMENTAL


@dataclass(frozen=True)
class SdfCell:
    """A CELL block of one instance in the SDF file."""

    instance_name: str
    cell_type: str | None = None
    iopaths: tuple[SdfIoPathSpec, ...] = ()


@dataclass(frozen=True)
class SdfDelayFile:
    """Root node of the parsed SDF AST.

    Delay values in `cells` are kept exactly as written in the file, so they are
    expressed in `timescale` units. Converting is optional: `to_seconds`.
    """

    divider: str = "."
    cells: tuple[SdfCell, ...] = ()
    timescale: str = DEFAULT_TIMESCALE
    timescale_seconds: float = DEFAULT_TIMESCALE_SECONDS

    def to_seconds(self, triplet: DelayTriplet) -> DelayTriplet:
        """Converts a triplet from this file's timescale to seconds; None stays None."""
        factor = self.timescale_seconds
        return DelayTriplet(
            None if triplet.min is None else triplet.min * factor,
            None if triplet.typ is None else triplet.typ * factor,
            None if triplet.max is None else triplet.max * factor,
        )