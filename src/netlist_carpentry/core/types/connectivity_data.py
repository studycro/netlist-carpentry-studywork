from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Set, Union

from pydantic import NonNegativeInt

from netlist_carpentry.core.exceptions import StructureMismatchError, WidthMismatchError
from netlist_carpentry.core.netlist_elements.element_path import PortPath
from netlist_carpentry.core.netlist_elements.port_segment import PortSegment

if TYPE_CHECKING:
    from netlist_carpentry import Instance, Module, Port, Wire

    PORT = Union[Port[Instance], Port[Module]]


@dataclass
class ConnectivityData(MutableMapping[NonNegativeInt, List[PortSegment]]):
    """Aggregated connectivity information for a port or wire, summarizing which segments connect to which other ports.

    This dataclass wraps the raw segment-level connections e.g. returned by `Port.loads()` or `Port.driver()` (analogously for `Wire`),
    providing higher-level views such as per-port mappings and detection of fully connected (1:1) relationships across all bits,
    since these would simplify the whole load/driver tracking process a lot.

    Attributes:
        base (Port | Wire): The port or wire whose connectivity is being described (e.g. the port or wire on which `loads()` or `driver()` was called).
        connections (Dict[NonNegativeInt, List[PortSegment]]): A mapping from segment index to the list of connected `PortSegment` objects.
            For `loads()`, these are the load segments; for `driver()`, these are the driving segments (at most 1 per index).
    """

    base: Union[PORT, Wire]
    """The base port or wire from which the connectivity is modeled by this instance."""
    connections: Dict[NonNegativeInt, List[PortSegment]]
    """The connection dictionary for each index of the base port or wire.

    Each index of the port or wire is mapped to a list of port segments (i.e. the associated connections).
    """

    def __getitem__(self, key: NonNegativeInt) -> List[PortSegment]:
        return self.connections[key]

    def __setitem__(self, key: NonNegativeInt, value: List[PortSegment]) -> None:
        self.connections[key] = value

    def __delitem__(self, key: NonNegativeInt) -> None:
        del self.connections[key]

    def __iter__(self) -> Iterator[NonNegativeInt]:
        return iter(self.connections)

    def __len__(self) -> NonNegativeInt:
        return len(self.connections)

    def __repr__(self) -> str:
        return repr(self.connections)

    def __eq__(self, value: object) -> bool:
        if isinstance(value, dict):
            return self.connections == value
        elif isinstance(value, ConnectivityData):
            return self.connections == value.connections and self.base == value.base
        return super().__eq__(value)

    @property
    def connections_as_ports(self) -> Dict[NonNegativeInt, List[PORT]]:
        """Mapping from segment index to the list of parent Port objects (one per connected segment).

        Unlike `connections`, which returns individual port segments, this property collapses each segment
        to its parent port. A single port may appear multiple times in the list if multiple segments of the port
        connect to the same parent port. Accordingly, for e.g. a 4-bit port (or wire) connected to a 4-bit port,
        the target port will appear 4 times, once for each segment index.

        Returns:
            Dict[NonNegativeInt, List[Port]]: A dictionary mapping each segment index of the base port or wire to a list of its driving or loading ports.
        """
        return {idx: [ps.parent for ps in pslist] for idx, pslist in self.connections.items()}

    @property
    def indices_with_connections(self) -> Set[NonNegativeInt]:
        """Returns a set of indices that belong to segments of the base port or wire WITH connected ports in the connection mapping."""
        return set(k for k, lst in self.connections.items() if lst)

    @property
    def indices_without_connections(self) -> Set[NonNegativeInt]:
        """Returns a set of indices that belong to segments of the base port or wire WITHOUT connected ports in the connection mapping."""
        return set(self.base.segments.keys()) - self.indices_with_connections

    @property
    def connected_ports(self) -> Set[PortPath]:
        """Set of `PortPath` objects representing ports that are somehow connected to this base port or wire.

        Other relevant properties are `partially_connected_ports` and `fully_connected_ports`.

        Returns:
            Set[PortPath]: A set of `PortPath` objects for ports that somehow connect to this base port or wire.
                The set lists all ports connected to the base port, even if only one segment is connected.

        Example:
            ```python
            >>> from netlist_carpentry import Module
            >>> m = Module(name='m')
            >>> p1 = m.create_port('p1', 'in', width=2)
            >>> p2 = m.create_port('p2', 'out', width=2, offset=4)  # To make it more interesting
            >>> ConnectivityData(base=p1, connections=p1.loads()).connected_ports  # Completely unconnected initially
            set()
            >>> m.connect(p1[0], p2[4+0])
            >>> ConnectivityData(base=p1, connections=p1.loads()).connected_ports
            {PortPath m.p2}
            >>> m.connect(p1[1], p2[4+1])  # Now fully connected
            >>> ConnectivityData(base=p1, connections=p1.loads()).connected_ports
            {PortPath m.p2}

            ```
        """
        sets = [{p.path for p in plist} for plist in self.connections_as_ports.values()]
        if sets:
            return set.union(*sets)  # This contains all port paths, without distinguishing between fully and partially connected ports
        return set()

    @property
    def partially_connected_ports(self) -> Set[PortPath]:
        """Set of `PortPath` objects representing ports that are **only partially** connected to this base port or wire.

        Other relevant properties are `connected_ports` and `fully_connected_ports`.

        Returns:
            Set[PortPath]: A set of `PortPath` objects for ports that partially connect to this base port or wire.
                Accordingly, all ports that are connected 1:1 to this base port or wire, are excluded.
                If a connected port is larger or smaller than the base port or wire, it is listed in this set.

        Example:
            ```
            >>> from netlist_carpentry import Module
            >>> m = Module(name='m')
            >>> p1 = m.create_port('p1', 'in', width=2)
            >>> p2 = m.create_port('p2', 'out', width=2, offset=4)  # To make it more interesting
            >>> m.connect(p1[0], p2[4+0])
            >>> ConnectivityData(base=p1, connections=p1.loads()).partially_connected_ports
            {PortPath m.p2}
            >>> m.connect(p1[1], p2[4+1])  # Now fully connected
            >>> ConnectivityData(base=p1, connections=p1.loads()).partially_connected_ports
            set()

            ```
        """
        return self.connected_ports - self.fully_connected_ports  # Removes the fully connected ports, so only the partially connected ports remain

    @property
    def fully_connected_ports(self) -> Set[PortPath]:
        """Set of `PortPath` objects representing ports that are connected to **every** segment of the base port or wire.

        This property also checks whether the target port is actually the same width.
        A port appears in this set only if every segments of this base port or wire is connected to the other port.
        Partially connected ports are excluded.

        This property **does not care about index order**. If a port is connected in reverse order (e.g. indices are
        connected 3->0, 2->1, 1->2, 0->3) but of the same width, the port is still in this set.
        However, such port will be excluded from `ordered_ports`, and instead can be found in the `misordered_ports` set.

        Other relevant properties are `partially_connected_ports` and `connected_ports`.

        Returns:
            Set[PortPath]: A set of `PortPath` objects for ports that fully connect to every segment of the base port or wire.
                Returns the intersection of all per-index port sets; if any index has no connections, the result is empty.

        Example:
            ```python
            >>> from netlist_carpentry import Module
            >>> m = Module(name='m')
            >>> p1 = m.create_port('p1', 'in', width=2)
            >>> p2 = m.create_port('p2', 'out', width=2, offset=4)  # To make it more interesting
            >>> m.connect(p1[0], p2[4+0])
            >>> ConnectivityData(base=p1, connections=p1.loads()).fully_connected_ports
            set()
            >>> m.connect(p1[1], p2[4+1])  # Now fully connected
            >>> ConnectivityData(base=p1, connections=p1.loads()).fully_connected_ports
            {PortPath m.p2}

            ```
        """
        connected_ports_same_width = [{p.path for p in plist if p.width == self.base.width} for plist in self.connections_as_ports.values()]
        if connected_ports_same_width:
            return set.intersection(*connected_ports_same_width)
        return set()

    @property
    def ordered_ports(self) -> Set[PortPath]:
        """Set of `PortPath` objects representing ports that are connected in the same index order.

        If a port from the `connections` dictionary is connected in the exact same index order, it is listed in this set.
        Only ports that are fully connected and of the same width (and connected in the same order) are listed in this set.

        This property acts as a counterpart to the `misordered_ports` property.

        Example:
            ```python
            >>> from netlist_carpentry import Module
            >>> m = Module(name='m')
            >>> p1 = m.create_port('p1', 'in', width=2)
            >>> p2 = m.create_port('p2', 'out', width=2, offset=4)  # To make it more interesting
            >>> m.connect(p1[0], p2[4+0]) # Correct order
            >>> m.connect(p1[1], p2[4+1])
            >>> ConnectivityData(base=p1, connections=p1.loads()).ordered_ports
            {PortPath m.p2}
            >>> m.disconnect(p1)
            >>> m.disconnect(p2)
            >>> m.connect(p1[0], p2[4+1])  # Switched order
            >>> m.connect(p1[1], p2[4+0])
            >>> ConnectivityData(base=p1, connections=p1.loads()).ordered_ports
            set()

            ```
        """
        return self.fully_connected_ports.difference(self.misordered_ports)

    @property
    def misordered_ports(self) -> Set[PortPath]:
        """Set of `PortPath` objects representing ports that are **not** connected in the same index order.

        If a port from the `connections` dictionary is not connected in the exact same index order, it is listed in this set.
        Only ports that are fully connected and of the same width (but connected in a different order) are listed in this set.

        This property acts as a counterpart to the `ordered_ports` property.

        Example:
            ```python
            >>> from netlist_carpentry import Module
            >>> m = Module(name='m')
            >>> p1 = m.create_port('p1', 'in', width=2)
            >>> p2 = m.create_port('p2', 'out', width=2, offset=4)  # To make it more interesting
            >>> m.connect(p1[0], p2[4+0]) # Correct order
            >>> m.connect(p1[1], p2[4+1])
            >>> ConnectivityData(base=p1, connections=p1.loads()).misordered_ports
            set()
            >>> m.disconnect(p1)
            >>> m.disconnect(p2)
            >>> m.connect(p1[0], p2[4+1])  # Switched order
            >>> m.connect(p1[1], p2[4+0])
            >>> ConnectivityData(base=p1, connections=p1.loads()).misordered_ports
            {PortPath m.p2}

            ```
        """
        wrong_order = set()
        for idx, pslist in self.connections.items():
            for ps in pslist:
                offset = (ps.parent.offset or 0) - (self.base.offset or 0)
                if idx != (ps.index - offset) and ps.parent.path in self.fully_connected_ports:
                    wrong_order.add(ps.parent.path)
        return wrong_order

    @staticmethod
    def _get_path(port: Union[PORT, PortPath]) -> PortPath:
        """Returns the path of the given object if it is a Port, otherwise just returns the given PortPath."""
        return port if isinstance(port, PortPath) else port.path

    def connected_to(self, other: Union[PORT, PortPath]) -> bool:
        """Checks if the given port is in any way connected to this base port or wire."""
        return self._get_path(other) in self.connected_ports

    def fully_connected_to(self, other: Union[PORT, PortPath]) -> bool:
        """Checks if the given port is completely connected to this base port or wire such that every index of this port is connected to the other port.

        The base port or wire and the given port must be of the same width. Index order is ignored, however, such that a connection with reversed indices
        (e.g. indices are connected 3->0, 2->1, 1->2, 0->3) is still considered "fully connected".
        """
        return self._get_path(other) in self.fully_connected_ports

    def partially_connected_to(self, other: Union[PORT, PortPath]) -> bool:
        """Checks if the given port is partially connected to this base port or wire, but not fully connected to the other port."""
        return self._get_path(other) in self.partially_connected_ports

    def connected_1to1(self, other: Union[PORT, PortPath]) -> bool:
        """Checks if an exact 1:1 connection exists between the given port and the base port or wire.

        Returns:
            bool: True, only if an exact 1:1 connection exists between the given port and the base port or wire. False otherwise.
                If True, a standard Verilog assignment `assing x = y;` is possible and no slicing is required.
        """
        return self._get_path(other) in self.ordered_ports

    def connected_in_different_order(self, other: Union[PORT, PortPath]) -> bool:
        """Checks if the given port connects fully to the base port or wire, but in a different index order.

        Returns:
            bool: True, only if the base port or wire and the given port are of the same width, fully connected to each other, and in a different index order,
                e.g. with reversed indices (such as indices connected 3->0, 2->1, 1->2, 0->3). False in every other case.

        Example:
            ```python
            >>> from netlist_carpentry import Module
            >>> m = Module(name='m')
            >>> p1 = m.create_port('p1', 'in', width=2)
            >>> p2 = m.create_port('p2', 'out', width=2)
            >>> m.connect(p1[0], p2[1])  # Switched index order
            >>> m.connect(p1[1], p2[0])
            >>> ConnectivityData(base=p1, connections=p1.loads()).connected_in_different_order(p2)
            True

            ```
        """
        return self._get_path(other) in self.misordered_ports

    def get_connected_port(self) -> PORT:
        """Returns the port connected to the base port or wire (i.e. the opposing driver or load port).

        This method returns the opposing port of this ConnectivityData, but only if it exists unambiguously.
        For example, if a driving port has only one load port, and this ConnectivityData object models this
        connection (e.g. via `driving_port.loads()`, or in the other direction via `load_port.driver()`),
        then the load port is returned.

        Alternatively, for `load_port.loads()`, this method returns the other load port, if exactly one other load port exists.

        In all other cases, an error is raised.

        Raises:
            StructureMismatchError: If there are multiple ports connected to this port.
                Is also raised if they are only partially connected.
            WidthMismatchError: If there is only one counterpart port, but the widths differ.

        Returns:
            Port: The port that is connected to the base port (i.e. the opposing driver or load port).

        Example:
            ```python
            >>> from netlist_carpentry import Module
            >>> m = Module(name='m')
            >>> p_in = m.create_port('p_in', 'in')
            >>> p_out = m.create_port('p_out', 'out')
            >>> m.connect(p_in, p_out)
            >>> p_in.loads().get_connected_port()
            Port(output p_out, 1 bit)
            >>> p_out2 = m.create_port('p_out2', 'out')
            >>> m.connect(p_in, p_out2)
            >>> p_in.loads().get_connected_port()
            Traceback (most recent call last):
                ...
            netlist_carpentry.core.exceptions.StructureMismatchError: Cannot find single connected port: 2 ports are connected to Port 'm.p_in'!

            ```
        """
        ppath = self.base.raw_path
        ports = self.get_connected_ports()
        if len(ports) != 1:
            cls_name = self.base.__class__.__name__
            if len(self.connected_ports) != 1:
                err_msg = f'Cannot find single connected port: {len(self.connected_ports)} ports are connected to {cls_name} {ppath!r}!'
                raise StructureMismatchError(err_msg)
            raise WidthMismatchError(f'Cannot determine port connected to {cls_name} {ppath!r}: Differing port widths!')
        return ports.pop()  # Only one element, just return "random" element

    def get_connected_ports(self) -> List[PORT]:
        """Returns a list of ports that are connected to the base port or wire.

        This method returns the opposing ports of this ConnectivityData.
        The returned list contains all ports that are fully connected to the base port or wire and vice versa.
        Accordingly, the width of all ports from the list is equal to the width of the base port or wire.

        Returns:
            List[Port]: A list of ports that are connected fully to the base port or wire and vice versa.

        Example:
            ```python
            >>> from netlist_carpentry import Module
            >>> m = Module(name='m')
            >>> p_in = m.create_port('p_in', 'in')
            >>> p_out1 = m.create_port('p_out1', 'out')
            >>> p_out2 = m.create_port('p_out2', 'out')
            >>> m.connect(p_in, p_out1)
            >>> m.connect(p_in, p_out2)
            >>> p_in.loads().get_connected_ports()
            [Port(output p_out1, 1 bit), Port(output p_out2, 1 bit)]

            ```
        """
        # Must also exist in the first list (i.e. first segment), so iterating over the first list should be fine
        plist = self.connections_as_ports[next(iter(self.connections_as_ports))]
        return [p for p in plist if p.path in self.fully_connected_ports]
