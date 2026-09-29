import os

import ipywidgets as widgets
import pytest
from ipycytoscape import CytoscapeWidget, Edge, Node
from pydantic import ValidationError

from netlist_carpentry import Direction, Port
from netlist_carpentry.core.exceptions import ObjectNotFoundError
from netlist_carpentry.vis.dynamic import CytoscapeConfig, CytoscapeGraph
from netlist_carpentry.vis.styling.format import NODE_IMMS_BLUE1
from tests.utils import connected_module


@pytest.fixture()
def cyto_graph() -> CytoscapeGraph:
    return CytoscapeGraph(module_graph=connected_module().graph())


def test_basics(cyto_graph: CytoscapeGraph) -> None:
    assert isinstance(cyto_graph, CytoscapeGraph)
    assert len(cyto_graph.module_graph.nodes) == 13
    assert len(cyto_graph.module_graph.nodes) == len(cyto_graph.cyto.graph.nodes)
    assert isinstance(cyto_graph.output, widgets.Output)
    assert isinstance(cyto_graph.cyto, CytoscapeWidget)
    assert len(cyto_graph.formats.definitions) == 2
    assert cyto_graph.formats.mapping == {}

    orig_graph = connected_module().graph()
    for n in cyto_graph.module_graph.nodes:
        assert 'ndata' in cyto_graph.module_graph.nodes[n]
        assert 'ndata' in orig_graph.nodes[n]
        assert cyto_graph.module_graph.nodes[n]['ndata'] is not None
        assert orig_graph.nodes[n]['ndata'] is not None
        assert 'label' not in cyto_graph.module_graph.nodes[n]
    for n in cyto_graph.cyto.graph.nodes:
        assert 'ndata' not in n.data
        assert 'label' in n.data  # Label is ID by default


def test_apply_config(cyto_graph: CytoscapeGraph) -> None:
    assert cyto_graph.cyto.min_zoom == 1 / 5e0  # Default values
    assert cyto_graph.cyto.max_zoom == 5e0
    assert cyto_graph.cyto.autolock is False
    assert cyto_graph.cyto.panning_enabled is True
    cyto_graph.apply_config(CytoscapeConfig())  # Unchanged values remain
    assert cyto_graph.cyto.min_zoom == 1 / 5e0
    assert cyto_graph.cyto.max_zoom == 5e0
    assert cyto_graph.cyto.autolock is False
    assert cyto_graph.cyto.panning_enabled is True
    cyto_graph.apply_config(CytoscapeConfig(min_zoom=1, max_zoom=10, panning_enabled=False))  # Overwrite given values
    assert cyto_graph.cyto.min_zoom == 1
    assert cyto_graph.cyto.max_zoom == 10
    assert cyto_graph.cyto.autolock is False
    assert cyto_graph.cyto.panning_enabled is False
    with pytest.raises(ValidationError):
        cyto_graph.apply_config(CytoscapeConfig(selection_type='invalid'))


def test_update_format(cyto_graph: CytoscapeGraph) -> None:
    default_style = [
        {'selector': 'node', 'css': {'background-color': '#11479e'}},
        {'selector': 'node:parent', 'css': {'background-opacity': 0.333}},
        {'selector': 'edge', 'style': {'width': 4, 'line-color': '#9dbaea'}},
        {'selector': 'edge.directed', 'style': {'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'target-arrow-color': '#9dbaea'}},
        {'selector': 'edge.multiple_edges', 'style': {'curve-style': 'bezier'}},
    ]
    assert cyto_graph.cyto.get_style() == default_style
    cyto_graph.update_format()
    new_style = [
        {
            'selector': 'node',
            'style': {
                'color': 'black',
                'font-size': '14px',
                'label': 'data(label)',
                'transition-property': 'background-color, border-width, width',
                'transition-duration': '0.2s',
            },
        },
        {
            'selector': 'edge',
            'style': {'label': 'data(label)', 'font-size': '11px', 'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'text-wrap': 'wrap'},
        },
    ]
    assert cyto_graph.cyto.get_style() == new_style
    cyto_graph.formats.add_format('.imms_blue', NODE_IMMS_BLUE1)
    cyto_graph.update_format()
    new_style = [
        {
            'selector': 'node',
            'style': {
                'color': 'black',
                'font-size': '14px',
                'label': 'data(label)',
                'transition-property': 'background-color, border-width, width',
                'transition-duration': '0.2s',
            },
        },
        {
            'selector': 'edge',
            'style': {'label': 'data(label)', 'font-size': '11px', 'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'text-wrap': 'wrap'},
        },
        {
            'selector': '.imms_blue',
            'style': {
                'background-color': '#95B6DF',
                'color': 'black',
                'font-size': '14px',
                'label': 'data(label)',
                'transition-property': 'background-color, border-width, width',
                'transition-duration': '0.2s',
            },
        },
    ]
    assert cyto_graph.cyto.get_style() == new_style


def test_format_node(cyto_graph: CytoscapeGraph) -> None:
    with pytest.raises(ObjectNotFoundError):
        cyto_graph.format_node('nonexisting_node', 'format')

    assert cyto_graph.formats.mapping == {}
    cyto_graph.format_node('in1', '.format')
    assert cyto_graph.formats.mapping == {'in1': ['.format']}
    cyto_graph.format_node('in1', '.format2')
    assert cyto_graph.formats.mapping == {'in1': ['.format', '.format2']}


def test_format_nodes(cyto_graph: CytoscapeGraph) -> None:
    assert cyto_graph.formats.mapping == {}
    cyto_graph.format_nodes(lambda name, data: False, format_name='.format')
    assert cyto_graph.formats.mapping == {}
    cyto_graph.format_nodes(lambda name, data: 'inst' in name, format_name='.inst_format')
    assert cyto_graph.formats.mapping == {
        'and_inst': ['.inst_format'],
        'dff_inst': ['.inst_format'],
        'not_inst': ['.inst_format'],
        'or_inst': ['.inst_format'],
        'xor_inst': ['.inst_format'],
        # 'out': [], --> Not an instance, so not formatted
        # 'out_ff': [], --> Not an instance, so not formatted
    }
    assert cyto_graph.formats.mapping['out'] == []
    assert cyto_graph.formats.mapping['out_ff'] == []


def test_format_in_out(cyto_graph: CytoscapeGraph) -> None:
    assert cyto_graph.formats.mapping == {}
    cyto_graph.format_nodes(lambda name, data: True, format_name='.format')
    assert cyto_graph.formats.mapping == {
        'in1': ['.format'],
        'in2': ['.format'],
        'in3': ['.format'],
        'in4': ['.format'],
        'clk': ['.format'],
        'rst': ['.format'],
        'and_inst': ['.format'],
        'dff_inst': ['.format'],
        'not_inst': ['.format'],
        'or_inst': ['.format'],
        'xor_inst': ['.format'],
        'out': ['.format'],
        'out_ff': ['.format'],
    }
    cyto_graph.format_in_out(in_format='.format_in', out_format='.format_out')
    assert cyto_graph.formats.mapping == {
        'in1': ['.format', '.format_in'],
        'in2': ['.format', '.format_in'],
        'in3': ['.format', '.format_in'],
        'in4': ['.format', '.format_in'],
        'clk': ['.format', '.format_in'],
        'rst': ['.format', '.format_in'],
        'and_inst': ['.format'],
        'dff_inst': ['.format'],
        'not_inst': ['.format'],
        'or_inst': ['.format'],
        'xor_inst': ['.format'],
        'out': ['.format', '.format_out'],
        'out_ff': ['.format', '.format_out'],
    }


def test_get_node_map(cyto_graph: CytoscapeGraph) -> None:
    m = cyto_graph.get_node_map()
    assert cyto_graph._node_map == m
    new_n = Node()
    new_n.data['id'] = 'LOL'
    cyto_graph.cyto.graph.add_node(new_n)
    with pytest.raises(KeyError):
        m['LOL']

    n = m['in1']
    assert n.data == {'id': 'in1', 'nsubtype': 'input', 'ntype': 'PORT', 'label': 'in1'}
    m = cyto_graph.get_node_map()
    assert cyto_graph._node_map != m  # Contains new node, property doesn't yet
    n2 = m['LOL']
    assert n2.data == {'id': 'LOL'}


def test_get_node(cyto_graph: CytoscapeGraph) -> None:
    with pytest.raises(ObjectNotFoundError):
        cyto_graph.get_node('LOL')

    n = cyto_graph.get_node('in1')
    assert n.data == {'id': 'in1', 'nsubtype': 'input', 'ntype': 'PORT', 'label': 'in1'}

    new_n = Node()
    new_n.data['id'] = 'LOL'
    cyto_graph.cyto.graph.add_node(new_n)
    assert 'LOL' not in cyto_graph._node_map
    n2 = cyto_graph.get_node('LOL')
    assert 'LOL' in cyto_graph._node_map
    assert n2 is cyto_graph._node_map['LOL']
    assert n2.data == {'id': 'LOL'}


def test_get_node_element(cyto_graph: CytoscapeGraph) -> None:
    with pytest.raises(ObjectNotFoundError):
        cyto_graph.get_node_element('nonexisting')

    n = cyto_graph.get_node_element('in1')
    assert isinstance(n, Port)
    assert n.name == 'in1'
    assert n.direction is Direction.IN


def test_get_edge_map(cyto_graph: CytoscapeGraph) -> None:
    m = cyto_graph.get_edge_map()
    assert cyto_graph._edge_map == m
    new_e = Edge()
    new_e.data['ename'] = 'LOL'
    new_e.data['source'] = 'in1'
    new_e.data['target'] = 'in2'
    cyto_graph.cyto.graph.add_edge(new_e)
    with pytest.raises(KeyError):
        m['LOL']

    e = m['in1']
    assert e.data == {'dr_seg': None, 'ename': 'in1', 'ld_seg': None, 'source': 'in1', 'target': 'and_inst', 'width': 1}
    m = cyto_graph.get_edge_map()
    assert cyto_graph._edge_map != m  # Contains new edge, property doesn't yet
    e2 = m['LOL']
    assert e2.data == {'ename': 'LOL', 'source': 'in1', 'target': 'in2'}


def test_get_edge(cyto_graph: CytoscapeGraph) -> None:
    with pytest.raises(ObjectNotFoundError):
        cyto_graph.get_edge('nonexisting')

    n = cyto_graph.get_edge('in1')
    assert n.data == {'dr_seg': None, 'ename': 'in1', 'ld_seg': None, 'source': 'in1', 'target': 'and_inst', 'width': 1}

    new_e = Edge()
    new_e.data['ename'] = 'LOL'
    new_e.data['source'] = 'in1'
    new_e.data['target'] = 'in2'
    cyto_graph.cyto.graph.add_edge(new_e)
    assert 'LOL' not in cyto_graph._edge_map
    e2 = cyto_graph.get_edge('LOL')
    assert 'LOL' in cyto_graph._edge_map
    assert e2 is cyto_graph._edge_map['LOL']
    assert e2.data == {'ename': 'LOL', 'source': 'in1', 'target': 'in2'}


def test_toggle_label(cyto_graph: CytoscapeGraph) -> None:
    assert cyto_graph.get_node('in1').data['label'] == 'in1'
    cyto_graph.toggle_label('in1')
    assert cyto_graph.get_node('in1').data['label'] == 'input'
    cyto_graph.toggle_label(cyto_graph.get_node('in1'))
    assert cyto_graph.get_node('in1').data['label'] == 'in1'


def test_show(cyto_graph: CytoscapeGraph) -> None:
    assert cyto_graph.cyto._interaction_handlers == {}
    assert cyto_graph.cyto.cytoscape_layout == {'name': 'cola'}  # Default layout
    cyto_graph.show()
    assert isinstance(cyto_graph.cyto._interaction_handlers['node']['click'], widgets.CallbackDispatcher)
    assert isinstance(cyto_graph.cyto._interaction_handlers['edge']['click'], widgets.CallbackDispatcher)
    assert cyto_graph.cyto.cytoscape_layout == {'name': 'klay', 'klay': {'spacing': 40, 'nodeLayering': 'LONGEST_PATH'}}


def test_register_callbacks(cyto_graph: CytoscapeGraph) -> None:
    assert cyto_graph.cyto._interaction_handlers == {}

    cyto_graph._register_callbacks()
    assert len(cyto_graph.cyto._interaction_handlers) == 2
    assert 'node' in cyto_graph.cyto._interaction_handlers
    assert 'edge' in cyto_graph.cyto._interaction_handlers
    assert 'click' in cyto_graph.cyto._interaction_handlers['node']
    assert 'click' in cyto_graph.cyto._interaction_handlers['edge']
    assert isinstance(cyto_graph.cyto._interaction_handlers['node']['click'], widgets.CallbackDispatcher)
    assert isinstance(cyto_graph.cyto._interaction_handlers['edge']['click'], widgets.CallbackDispatcher)


def test_node_click(cyto_graph: CytoscapeGraph) -> None:
    in1_node = cyto_graph.get_node('in1')
    in2_node = cyto_graph.get_node('in2')
    assert in2_node.data['label'] == 'in2'
    assert cyto_graph.formats.mapping['in2'] == []
    cyto_graph._node_click({'data': in2_node.data})
    assert in2_node.data['label'] == 'input'
    assert cyto_graph.formats.mapping['in2'] == ['italics', 'selected']
    cyto_graph._node_click({'data': in2_node.data})
    assert in2_node.data['label'] == 'in2'
    assert cyto_graph.formats.mapping['in2'] == []
    cyto_graph._node_click({'data': in2_node.data})
    assert in1_node.data['label'] == 'in1'
    assert in2_node.data['label'] == 'input'
    assert cyto_graph.formats.mapping['in1'] == []
    assert cyto_graph.formats.mapping['in2'] == ['italics', 'selected']
    cyto_graph._node_click({'data': in1_node.data})
    assert in1_node.data['label'] == 'input'
    assert in2_node.data['label'] == 'input'
    assert cyto_graph.formats.mapping['in1'] == ['italics', 'selected']
    assert cyto_graph.formats.mapping['in2'] == ['italics']
    cyto_graph._node_click({'data': in2_node.data})
    assert in1_node.data['label'] == 'input'
    assert in2_node.data['label'] == 'in2'
    assert cyto_graph.formats.mapping['in1'] == ['italics']
    assert cyto_graph.formats.mapping['in2'] == ['selected']


def test_node_hover_in_out(cyto_graph: CytoscapeGraph) -> None:
    in1_node = cyto_graph.get_node('in1')
    in2_node = cyto_graph.get_node('in2')
    assert cyto_graph.formats.mapping['in1'] == []
    assert cyto_graph.formats.mapping['in2'] == []
    cyto_graph._node_hover_in({'data': in1_node.data})
    assert cyto_graph.formats.mapping['in1'] == ['transparent']
    assert cyto_graph.formats.mapping['in2'] == []
    cyto_graph._node_hover_in({'data': in1_node.data})
    assert cyto_graph.formats.mapping['in1'] == ['transparent']
    assert cyto_graph.formats.mapping['in2'] == []
    cyto_graph._node_hover_out({'data': in1_node.data})
    assert cyto_graph.formats.mapping['in1'] == []
    assert cyto_graph.formats.mapping['in2'] == []
    cyto_graph._node_hover_in({'data': in1_node.data})
    assert cyto_graph.formats.mapping['in1'] == ['transparent']
    assert cyto_graph.formats.mapping['in2'] == []
    cyto_graph._node_hover_in({'data': in2_node.data})
    assert cyto_graph.formats.mapping['in1'] == ['transparent']
    assert cyto_graph.formats.mapping['in2'] == ['transparent']
    cyto_graph._node_hover_out({'data': in1_node.data})
    assert cyto_graph.formats.mapping['in1'] == []
    assert cyto_graph.formats.mapping['in2'] == ['transparent']
    cyto_graph._node_hover_out({'data': in2_node.data})
    assert cyto_graph.formats.mapping['in1'] == []
    assert cyto_graph.formats.mapping['in2'] == []


def test_toggle_node_label_style(cyto_graph: CytoscapeGraph) -> None:
    assert cyto_graph.formats.mapping['in1'] == []
    cyto_graph._toggle_node_label_style('in1')
    assert cyto_graph.formats.mapping['in1'] == ['italics']
    cyto_graph._toggle_node_label_style('in1')
    assert cyto_graph.formats.mapping['in1'] == []
    cyto_graph._toggle_node_label_style('in1')
    assert cyto_graph.formats.mapping['in1'] == ['italics']
    assert cyto_graph.formats.mapping['and_inst'] == []
    cyto_graph._toggle_node_label_style('and_inst')
    assert cyto_graph.formats.mapping['in1'] == ['italics']
    assert cyto_graph.formats.mapping['and_inst'] == ['italics']
    cyto_graph._toggle_node_label_style('and_inst')
    assert cyto_graph.formats.mapping['in1'] == ['italics']
    assert cyto_graph.formats.mapping['and_inst'] == []


def test_select_node(cyto_graph: CytoscapeGraph) -> None:
    assert cyto_graph._active_node is None
    assert cyto_graph.formats.mapping['in1'] == []
    cyto_graph._select_node('in1')
    assert cyto_graph._active_node == 'in1'
    assert cyto_graph.formats.mapping['in1'] == ['selected']
    cyto_graph._select_node('in1')
    assert cyto_graph._active_node is None
    assert cyto_graph.formats.mapping['in1'] == []
    cyto_graph._select_node('in1')
    assert cyto_graph._active_node == 'in1'
    assert cyto_graph.formats.mapping['in1'] == ['selected']
    cyto_graph._select_node('and_inst')
    assert cyto_graph._active_node == 'and_inst'
    assert cyto_graph.formats.mapping['in1'] == []
    assert cyto_graph.formats.mapping['and_inst'] == ['selected']
    cyto_graph._select_node('and_inst')
    assert cyto_graph._active_node is None
    assert cyto_graph.formats.mapping['in1'] == []
    assert cyto_graph.formats.mapping['and_inst'] == []


def test_edge_click(cyto_graph: CytoscapeGraph) -> None:
    in1_edge = cyto_graph.get_edge('in1')
    assert 'label' not in in1_edge.data
    assert cyto_graph._shown_edges == {0} - {0}  # Funny eyes <=> empty set
    cyto_graph._edge_click({'data': in1_edge.data})
    assert 'label' in in1_edge.data
    assert cyto_graph._shown_edges == {'in1'}
    assert in1_edge.data['label'] == 'in1\n(1 bit)'
    cyto_graph._edge_click({'data': in1_edge.data})  # Second click, no longer in shown_edges set, but mouse still over the edge
    assert cyto_graph._shown_edges == {0} - {0}  # Funny eyes <=> empty set
    assert in1_edge.data['label'] == 'in1\n(1 bit)'  # Will be removed once the mouse leaves the edge


######## This is to test the package-level import show, doesn't really fit anywhere, and I didn't want to create an additional file for this single test


def test_top_show() -> None:
    from netlist_carpentry import show

    G = show(connected_module())
    assert isinstance(G, CytoscapeGraph)
    assert G.formats.mapping == {
        'and_inst': ['.default'],
        'clk': ['.in'],
        'dff_inst': ['.default'],
        'in1': ['.in'],
        'in2': ['.in'],
        'in3': ['.in'],
        'in4': ['.in'],
        'not_inst': ['.default'],
        'or_inst': ['.default'],
        'out': ['.out'],
        'out_ff': ['.out'],
        'rst': ['.in'],
        'xor_inst': ['.default'],
    }
    assert len(G.formats.definitions) == 8
    # Standard definitions
    assert 'node' in G.formats.definitions
    assert 'edge' in G.formats.definitions
    # Custom definitions
    assert '.default' in G.formats.definitions
    assert '.in' in G.formats.definitions
    assert '.out' in G.formats.definitions
    # Interaction definitions
    assert '.italics' in G.formats.definitions
    assert '.selected' in G.formats.definitions
    assert '.transparent' in G.formats.definitions

    G2 = show(connected_module().graph())
    assert isinstance(G2, CytoscapeGraph)
    assert G.formats == G2.formats


if __name__ == '__main__':
    file_name = os.path.basename(__file__)
    pytest.main(args=['-k', file_name])
