import os

import pytest

from netlist_carpentry import Module, ModuleGraph


def test_build_edges() -> None:
    m = Module(name='m')
    w1 = m.create_wire('w1')
    p1 = m.create_port('p1', direction='input')
    p2 = m.create_port('p2', direction='output')
    p3 = m.create_port('p3', direction='output')
    m.connect(w1, p1)
    m.connect(w1, p2)
    m.connect(w1, p3)
    g = ModuleGraph()
    assert len(g.edges) == 0
    m._build_edges(g)
    assert ('p1', 'p2', 'p1§p2') in g.edges
    assert ('p1', 'p3', 'p1§p3') in g.edges
    assert g.has_edge(p1.name, p2.name)
    assert g.has_edge(p1.name, p3.name)


def test_build_edges_multibit() -> None:
    m = Module(name='m')
    w1 = m.create_wire('w1', width=4)
    p1 = m.create_port('p1', direction='input', width=4)
    p2 = m.create_port('p2', direction='output', width=4)
    p3 = m.create_port('p3', direction='output', width=4, offset=4)
    p4 = m.create_port('p4', direction='output', width=5)
    p5 = m.create_port('p5', direction='output', width=5, offset=4)
    m.connect(w1, p1)
    m.connect(w1, p2)
    m.connect(w1, p3)
    m.connect(w1[0], p4[0])
    m.connect(w1[1], p4[1])
    m.connect(w1[2], p4[2])
    m.connect(w1[3], p4[3])
    m.connect(w1[0], p5[5 + 0])
    m.connect(w1[1], p5[5 + 1])
    m.connect(w1[2], p5[5 + 2])
    m.connect(w1[3], p5[5 + 3])
    g = ModuleGraph()
    assert len(g.edges) == 0
    m._build_edges(g)
    assert g.has_edge(p1.name, p2.name, key='p1§p2')
    assert g.has_edge(p1.name, p3.name, key='p1§p3')  # Offset gets ignored, since it is fully connected
    for i in range(4):
        assert g.has_edge(p1.name, p4.name, key=f'p1[{i}]§p4[{i}]')  # Not fully connected, hence indexing
        assert g.has_edge(p1.name, p5.name, key=f'p1[{i}]§p5[{i + 5}]')  # Not fully connected, plus offset


if __name__ == '__main__':
    file_name = os.path.basename(__file__)
    pytest.main(args=['-k', file_name])
