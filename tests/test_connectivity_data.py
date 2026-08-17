import os
from collections.abc import MutableMapping

import pytest

from netlist_carpentry import ConnectivityData, Module
from netlist_carpentry.core.exceptions import StructureMismatchError, WidthMismatchError
from netlist_carpentry.core.netlist_elements.element_path import PortPath


@pytest.fixture()
def module() -> Module:
    from tests.utils import connected_module

    module = connected_module()
    module.connect(module.create_port('I4', 'in', 4), module.create_port('O4', 'out', 4, offset=3))
    return module


def test_basics(module: Module) -> None:
    p = module.ports['in1']
    p2 = module.ports['in2']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert isinstance(cd, MutableMapping)
    assert cd.base is p
    assert cd.connections == p.loads()
    assert cd[0] is cd.connections[0]

    cd[1] = []  # To test __setitem__
    assert 1 in cd
    assert cd[1] == []
    del cd[1]  # To tset __delitem__
    assert 1 not in cd
    for i in cd:  # To test __iter__
        assert cd[i] is cd.connections[i]
    assert len(cd) == 1  # To test __len__

    # Automatically created from MutableMapping class
    assert cd.keys() == cd.connections.keys()
    assert list(cd.values()) == list(cd.connections.values())
    assert cd.items() == cd.connections.items()
    assert repr(cd) == repr(cd.connections)
    assert repr(cd) == '{0: [PortSegment(test_module1.and_inst.A.0, Signal:x)]}'

    cd2 = ConnectivityData(base=p, connections=p.loads())
    cd3 = ConnectivityData(base=p2, connections=p.loads())
    assert cd == cd2
    assert cd == cd2.connections
    assert cd != cd3  # Not the same root port ...
    assert cd == cd3.connections  # ... but the same connections


def test_connections_as_ports(module: Module) -> None:
    p = module.ports['in1']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd.connections_as_ports == {0: [module.instances['and_inst'].ports['A']]}

    p2 = module.ports['I4']
    cd = ConnectivityData(base=p2, connections=p2.loads())
    assert cd.connections_as_ports == {0: [module.ports['O4']], 1: [module.ports['O4']], 2: [module.ports['O4']], 3: [module.ports['O4']]}

    p3 = module.ports['O4']
    cd = p3.driver()
    assert cd.connections_as_ports == {3: [module.ports['I4']], 4: [module.ports['I4']], 5: [module.ports['I4']], 6: [module.ports['I4']]}


def test_indices_connections(module: Module) -> None:
    p = module.ports['in1']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd.indices_without_connections == {0} - {0}  # Funny eyes <=> empty set
    assert cd.indices_with_connections == {0}

    o1 = module.create_port('O1', 'out')
    cd = ConnectivityData(base=o1, connections=o1.driver())
    assert cd.indices_without_connections == {0}
    assert cd.indices_with_connections == {0} - {0}  # Funny eyes <=> empty set

    module.connect(module.ports['I4'][0].ws, o1[0])
    dr = o1.driver()
    cd = ConnectivityData(base=o1, connections=dr)
    assert cd.indices_without_connections == {0} - {0}  # Funny eyes <=> empty set
    assert cd.indices_with_connections == {0}

    o1.create_port_segments(3, 1)
    cd = ConnectivityData(base=o1, connections=dr)
    assert cd.indices_without_connections == {1, 2, 3}
    assert cd.indices_with_connections == {0}

    cd = ConnectivityData(base=o1, connections={})
    assert cd.indices_without_connections == {0, 1, 2, 3}
    assert cd.indices_with_connections == {0} - {0}  # Funny eyes <=> empty set

    cd = ConnectivityData(base=o1, connections={0: []})
    assert cd.indices_without_connections == {0, 1, 2, 3}
    assert cd.indices_with_connections == {0} - {0}  # Funny eyes <=> empty set

    module.connect(module.ports['I4'][1].ws, o1[3])  # Now fully connected but with different index orders --> ignored by unconnected_indices property
    module.connect(module.ports['I4'][2].ws, o1[1])
    module.connect(module.ports['I4'][3].ws, o1[2])
    cd = ConnectivityData(base=o1, connections=o1.driver())
    assert cd.indices_without_connections == {0} - {0}  # Funny eyes <=> empty set
    assert cd.indices_with_connections == {0, 1, 2, 3}


def test_connected_ports(module: Module) -> None:
    p = module.ports['in1']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd.connected_ports == {PortPath(raw='test_module1.and_inst.A')}

    p2 = module.ports['I4']
    cd = ConnectivityData(base=p2, connections=p2.loads())
    assert cd.partially_connected_ports == {0} - {0}  # Funny eyes <=> empty set
    assert cd.connected_ports == {PortPath(raw='test_module1.O4')}

    o1 = module.create_port('O1', 'out')
    module.connect(p2[0].ws, o1[0])
    cd = ConnectivityData(base=p2, connections=p2.loads())
    assert cd.connected_ports == {PortPath(raw='test_module1.O4'), PortPath(raw='test_module1.O1')}


def test_partially_fully_connected_ports(module: Module) -> None:
    p = module.ports['in1']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd.partially_connected_ports == {0} - {0}  # Funny eyes <=> empty set
    assert cd.fully_connected_ports == {PortPath(raw='test_module1.and_inst.A')}

    p2 = module.ports['I4']
    cd = ConnectivityData(base=p2, connections=p2.loads())
    assert cd.partially_connected_ports == {0} - {0}  # Funny eyes <=> empty set
    assert cd.fully_connected_ports == {PortPath(raw='test_module1.O4')}

    o1 = module.create_port('O1', 'out')
    module.connect(p2[0].ws, o1[0])
    cd = ConnectivityData(base=p2, connections=p2.loads())
    assert len(cd.connections[0]) == 2
    assert len(cd.connections[1]) == 1
    assert len(cd.connections[2]) == 1
    assert len(cd.connections[3]) == 1
    assert cd.partially_connected_ports == {PortPath(raw='test_module1.O1')}
    assert cd.fully_connected_ports == {PortPath(raw='test_module1.O4')}

    o1.create_port_segments(3, 1)
    module.connect(p2[1].ws, o1[3])  # Now fully connected but with different index orders --> ignored by fully_connected_ports property
    module.connect(p2[2].ws, o1[1])
    module.connect(p2[3].ws, o1[2])
    cd = ConnectivityData(base=p2, connections=p2.loads())
    assert len(cd.connections[0]) == 2
    assert len(cd.connections[1]) == 2
    assert len(cd.connections[2]) == 2
    assert len(cd.connections[3]) == 2
    assert cd.partially_connected_ports == {0} - {0}  # Funny eyes <=> empty set
    assert cd.fully_connected_ports == {PortPath(raw='test_module1.O4'), PortPath(raw='test_module1.O1')}
    o1.create_port_segments(1, 4)
    cd = ConnectivityData(base=p2, connections=p2.loads())
    assert cd.partially_connected_ports == {PortPath(raw='test_module1.O1')}  # Port now 5 bit wide
    assert cd.fully_connected_ports == {PortPath(raw='test_module1.O4')}  # PortPath(raw='test_module1.O1')} not there, since too large now

    cd = ConnectivityData(base=p2, connections={})  # No connections
    assert cd.connected_ports == {0} - {0}  # Funny eyes <=> empty set
    assert cd.fully_connected_ports == {0} - {0}  # Funny eyes <=> empty set
    assert cd.partially_connected_ports == {0} - {0}  # Funny eyes <=> empty set


def test_ordered_misordered_ports(module: Module) -> None:
    p = module.ports['in1']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd.ordered_ports == {PortPath(raw='test_module1.and_inst.A')}
    assert cd.misordered_ports == {0} - {0}  # Funny eyes <=> empty set

    p_i4 = module.ports['I4']
    p_o4 = module.ports['O4']
    cd = ConnectivityData(base=p_i4, connections=p_i4.loads())
    assert cd.ordered_ports == {p_o4.path}
    assert cd.misordered_ports == {0} - {0}  # Funny eyes <=> empty set
    module.disconnect(p_o4[p_o4.offset + 1])
    module.disconnect(p_o4[p_o4.offset + 2])
    module.connect(p_i4[1].ws, p_o4[p_o4.offset + 2])  # Switch
    module.connect(p_i4[2].ws, p_o4[p_o4.offset + 1])  # Switch
    cd = ConnectivityData(base=p_i4, connections=p_i4.loads())
    assert cd.misordered_ports == {PortPath(raw='test_module1.O4')}  # No longer following index order
    assert cd.ordered_ports == {0} - {0}  # Funny eyes <=> empty set

    p_o1 = module.create_port('O1', 'out')
    module.connect(p_i4[1].ws, p_o1)  # Not same width, hence not in misordered ports
    cd = ConnectivityData(base=p_i4, connections=p_i4.loads())
    assert p_o1.path not in cd.misordered_ports  # Not same width --> ignored by both properties
    assert p_o1.path not in cd.ordered_ports
    assert cd.misordered_ports == {PortPath(raw='test_module1.O4')}
    assert cd.ordered_ports == {0} - {0}  # Funny eyes <=> empty set

    module.connect(p_i4, module.create_port('O4_2', 'out', 4, offset=2))
    cd = ConnectivityData(base=p_i4, connections=p_i4.loads())
    assert cd.misordered_ports == {PortPath(raw='test_module1.O4')}
    assert cd.ordered_ports == {PortPath(raw='test_module1.O4_2')}

    cd = ConnectivityData(base=p_i4, connections={})  # No connections
    assert cd.misordered_ports == {0} - {0}  # Funny eyes <=> empty set
    assert cd.ordered_ports == {0} - {0}  # Funny eyes <=> empty set


def test_get_path(module: Module) -> None:
    p = module.ports['in1']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd._get_path(p) == p.path
    assert cd._get_path(p.path) == p.path
    with pytest.raises(AttributeError):
        cd._get_path('foo')


def test_connected_methods(module: Module) -> None:
    p = module.ports['in1']
    p_and = module.instances['and_inst'].ports['A']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd.connected_to(p_and) is True
    assert cd.partially_connected_to(p_and) is False
    assert cd.fully_connected_to(p_and) is True
    assert cd.connected_1to1(p_and) is True
    assert cd.connected_in_different_order(p_and) is False

    p_i4 = module.ports['I4']
    o1 = module.create_port('O1', 'out')
    module.connect(p_i4[0].ws, o1[0])
    cd = ConnectivityData(base=p_i4, connections=p_i4.loads())
    assert cd.connected_to(p_and) is False
    assert cd.connected_to(o1) is True
    assert cd.partially_connected_to(o1) is True
    assert cd.fully_connected_to(o1) is False
    assert cd.connected_1to1(o1) is False
    assert cd.connected_in_different_order(o1) is False

    o1.create_port_segments(3, 1)
    module.connect(p_i4[1].ws, o1[3])  # Now fully connected but with different index orders --> ignored by connected_to methods
    module.connect(p_i4[2].ws, o1[1])
    module.connect(p_i4[3].ws, o1[2])
    cd = ConnectivityData(base=p_i4, connections=p_i4.loads())
    assert cd.connected_to(p_and) is False
    assert cd.connected_to(o1) is True
    assert cd.partially_connected_to(o1) is False
    assert cd.fully_connected_to(o1) is True
    assert cd.connected_1to1(o1) is False
    assert cd.connected_in_different_order(o1) is True

    module.disconnect(o1)
    module.connect(p_i4[0].ws, o1[0])  # Now correct index orders
    module.connect(p_i4[1].ws, o1[1])
    module.connect(p_i4[2].ws, o1[2])
    module.connect(p_i4[3].ws, o1[3])
    cd = ConnectivityData(base=p_i4, connections=p_i4.loads())
    assert cd.connected_to(o1) is True
    assert cd.partially_connected_to(o1) is False
    assert cd.fully_connected_to(o1) is True
    assert cd.connected_1to1(o1) is True
    assert cd.connected_in_different_order(o1) is False


def test_get_connected_port(module: Module) -> None:
    p = module.ports['in1']
    p_and = module.instances['and_inst'].ports['A']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd.get_connected_port() is p_and

    po = module.create_port('po', 'out')
    module.connect(p, po)
    cd = ConnectivityData(base=p, connections=p.loads())
    with pytest.raises(StructureMismatchError, match=r"Cannot find single connected port: 2 ports are connected to Port 'test_module1.in1'!"):
        cd.get_connected_port()

    module.disconnect(po)
    p.create_port_segment(1)
    cd = ConnectivityData(base=p, connections=p.loads())
    with pytest.raises(WidthMismatchError, match=r"Cannot determine port connected to Port 'test_module1.in1': Differing port widths!"):
        cd.get_connected_port()


def test_get_connected_ports(module: Module) -> None:
    p = module.ports['in1']
    p_and = module.instances['and_inst'].ports['A']
    cd = ConnectivityData(base=p, connections=p.loads())
    assert cd.get_connected_ports() == [p_and]

    cd = ConnectivityData(base=p_and, connections=p_and.loads())
    assert cd.get_connected_ports() == []  # The load itself currently has no other loads

    po = module.create_port('po', 'out')
    module.connect(p, po)
    cd = ConnectivityData(base=p, connections=p.loads())
    assert len(cd.get_connected_ports()) == 2
    assert p_and in cd.get_connected_ports()
    assert po in cd.get_connected_ports()

    po2 = module.create_port('po2', 'out', 4)
    module.connect(p[0].ws, po2[0])
    cd = ConnectivityData(base=p, connections=p.loads())
    assert len(cd.get_connected_ports()) == 2  # po2 not included since only partially connected
    assert p_and in cd.get_connected_ports()
    assert po in cd.get_connected_ports()

    cd = ConnectivityData(base=p_and, connections=p_and.loads())
    assert cd.get_connected_ports() == [po]


def test_basics_for_wires(module: Module) -> None:
    w = module.wires['in1']
    w2 = module.wires['in2']
    cd = ConnectivityData(base=w, connections=w.connections)
    assert isinstance(cd, MutableMapping)
    assert cd.base is w
    assert cd.connections == w.connections
    assert cd[0] is cd.connections[0]

    cd[1] = []  # To test __setitem__
    assert 1 in cd
    assert cd[1] == []
    del cd[1]  # To tset __delitem__
    assert 1 not in cd
    for i in cd:  # To test __iter__
        assert cd[i] is cd.connections[i]
    assert len(cd) == 1  # To test __len__

    # Automatically created from MutableMapping class
    assert cd.keys() == cd.connections.keys()
    assert list(cd.values()) == list(cd.connections.values())
    assert cd.items() == cd.connections.items()
    assert repr(cd) == repr(cd.connections)
    assert repr(cd) == '{0: [PortSegment(test_module1.in1.0, Signal:x), PortSegment(test_module1.and_inst.A.0, Signal:x)]}'

    cd2 = ConnectivityData(base=w, connections=w.connections)
    cd3 = ConnectivityData(base=w2, connections=w.connections)
    assert cd == cd2
    assert cd == cd2.connections
    assert cd != cd3  # Not the same root port ...
    assert cd == cd3.connections  # ... but the same connections


def test_properties_for_wires(module: Module) -> None:
    w = module.wires['in1']
    cd = ConnectivityData(base=w, connections=w.connections)
    assert cd.connections_as_ports == {0: [module.ports['in1'], module.instances['and_inst'].ports['A']]}
    assert cd.indices_without_connections == {0} - {0}  # Funny eyes <=> empty set
    assert cd.indices_with_connections == {0}
    assert cd.connected_ports == {PortPath(raw='test_module1.in1'), PortPath(raw='test_module1.and_inst.A')}
    assert cd.partially_connected_ports == {0} - {0}  # Funny eyes <=> empty set
    assert cd.fully_connected_ports == {PortPath(raw='test_module1.in1'), PortPath(raw='test_module1.and_inst.A')}
    assert cd.ordered_ports == {PortPath(raw='test_module1.in1'), PortPath(raw='test_module1.and_inst.A')}
    assert cd.misordered_ports == {0} - {0}  # Funny eyes <=> empty set


def test_methods_for_wires(module: Module) -> None:
    w = module.wires['in1']
    p = module.ports['in1']
    p_and = module.instances['and_inst'].ports['A']
    cd = ConnectivityData(base=w, connections=w.connections)
    assert cd.connected_to(p_and) is True
    assert cd.partially_connected_to(p_and) is False
    assert cd.fully_connected_to(p_and) is True
    assert cd.connected_1to1(p_and) is True
    assert cd.connected_in_different_order(p_and) is False
    assert cd.get_connected_ports() == [p, p_and]
    with pytest.raises(StructureMismatchError, match=r"Cannot find single connected port: 2 ports are connected to Wire 'test_module1.in1'!"):
        cd.get_connected_port()


if __name__ == '__main__':
    file_name = os.path.basename(__file__)
    pytest.main(args=['-k', file_name])
