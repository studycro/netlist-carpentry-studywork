"""Wrapper module for ipycytoscape, handling the creation of graph objects for Jupyter notebooks."""

from __future__ import annotations

from typing import Callable, Dict, List, Literal, Optional, Set, TypedDict, Union

import ipywidgets as widgets
from ipycytoscape import CytoscapeWidget, Edge, Node
from IPython.display import display
from pydantic import BaseModel

from netlist_carpentry import Instance, Module, ModuleGraph, Port
from netlist_carpentry.core.exceptions import ObjectNotFoundError
from netlist_carpentry.vis.dynamic.config import DEFAULT_CONFIG, CytoscapeConfig
from netlist_carpentry.vis.dynamic.widgets import InfoBox
from netlist_carpentry.vis.styling import Formats
from netlist_carpentry.vis.styling.format import DEFAULT_EDGE, DEFAULT_NODE

cssDict = Dict[str, Dict[str, str]]


class GraphDataDict(TypedDict):
    ntype: Literal['PORT', 'INSTANCE']
    nsubtype: str
    ndata: Union[Port[Module], Instance]


class CytoscapeGraph(BaseModel):
    """Interactive cytoscape graph visualization for Jupyter notebooks using ipycytoscape."""

    model_config = {'arbitrary_types_allowed': True}

    module_graph: ModuleGraph
    """The ModuleGraph (i.e. the source graph) represented in this Cytoscape graph."""
    formats: Formats = Formats(definitions={'node': DEFAULT_NODE, 'edge': DEFAULT_EDGE})
    """Contains all format definitons for this Cytoscape graph, along with a mapping of nodes to formats, and labels."""
    _output: Optional[widgets.Output] = None
    _cyto: Optional[CytoscapeWidget] = None

    @property
    def output(self) -> widgets.Output:
        """The output widget that handles output triggered by widget interaction."""
        if self._output is None:
            self._output = widgets.Output()
        return self._output

    @property
    def cyto(self) -> CytoscapeWidget:
        """The CytoscapeWidget that contains the graph and properties."""
        if self._cyto is None:
            self._cyto = CytoscapeWidget()
        return self._cyto

    @property
    def info_box(self) -> widgets.HTML:
        return self._info_box.widget()

    def model_post_init(self, context: object) -> None:
        self._shown_edges: Set[str] = set()
        self._active_node: Optional[str] = None
        self._hovered_node: Optional[str] = None
        self._info_box = InfoBox()
        self._add_graph_to_cyto()
        self._node_map = self.get_node_map()
        self._edge_map = self.get_edge_map()
        self.apply_config(DEFAULT_CONFIG)
        return super().model_post_init(context)

    def _add_graph_to_cyto(self) -> None:
        tmp_graph = self.module_graph.copy()
        for n in tmp_graph.nodes:
            tmp_graph.nodes[n].pop('ndata')  # type: ignore[misc]
            tmp_graph.nodes[n]['label'] = n  # type: ignore[misc]
        self.cyto.graph.add_graph_from_networkx(tmp_graph)

    def apply_config(self, cfg: CytoscapeConfig) -> None:
        """Applies the given CytoscapeConfig to this instance's CytoscapeWidget.

        The CytoscapeConfig defines environment values like `'min_zoom'`/`'max_zoom'`
        or `'panning_enabled'` that handle how the rendered widget behaves.
        Unset values (i.e. values that are `None`) are ignored, and the previous settings are kept.

        Args:
            cfg (CytoscapeConfig): The config object with the parameter values to set. Unset parameters
                (i.e. parameters that are `None`) are ignored, and the previous settings are kept.
        """
        for param_name, param_value in cfg.model_dump(exclude_none=True).items():  # type: ignore[misc]
            setattr(self.cyto, param_name, param_value)  # type: ignore[misc]

    def _update_node_classes(self, nodes: Optional[List[Node]] = None) -> None:
        if nodes is None:
            nodes = self.cyto.graph.nodes
        for n in nodes:
            self._update_node_classes_single(n)

    def _update_node_classes_single(self, node: Node) -> None:
        node_id = node.data.get('id')
        cls_name = self.formats.mapping[node_id] if node_id in self.formats.mapping else None
        node.classes = ' '.join(c[1:] if c[0] == '.' else c for c in cls_name) if cls_name is not None else ''

    def update_format(self, nodes: Optional[List[Node]] = None) -> None:
        """Reads the current format definitions, translates them into css and applies them as stylesheet to the CytoscapeWidget."""
        self._update_node_classes(nodes)
        stylesheet = [{'selector': fname, 'style': f.to_css()} for fname, f in self.formats.definitions.items()]
        self.cyto.set_style(stylesheet)  # type: ignore[arg-type]

    def format_node(self, node_id: str, format_name: str) -> None:
        """Apply a given format to a given node.

        The node must exist in the module graph, otherwise an `ObjectNotFoundError` is raised.

        Args:
            node_id (str): The node id of the node to format. Must exist in the module graph
            format_name (str): The name of the format. `format_name='foo'` will apply the format `'foo'`,
                which in css conforms to the class `'.foo'`.

        Raises:
            ObjectNotFoundError: If no node with the given id exists in the module graph.
        """
        if node_id not in self.module_graph.nodes:
            raise ObjectNotFoundError(f"Unable to format node: No node '{node_id}' exists in the given graph!")
        self.formats.format_nodes(node_id, format_name)

    def format_nodes(self, predicate: Callable[[str, GraphDataDict], bool], format_name: str) -> None:
        for n, d in self.module_graph.nodes(data=True):
            if predicate(n, d):
                self.format_node(n, format_name)

    def format_in_out(self, *, in_format: Optional[str] = None, out_format: Optional[str] = None) -> None:
        for node in self.module_graph.nodes:
            ntype: str = self.module_graph.node_subtype(node)
            if ntype == 'input' and in_format is not None:
                self.format_node(node, in_format)
            elif ntype == 'output' and out_format is not None:
                self.format_node(node, out_format)

    def get_node_map(self) -> Dict[str, Node]:
        return {n.data['id']: n for n in self.cyto.graph.nodes}

    def get_node(self, node_id: str) -> Node:
        """Returns the node object for the given node identifier.

        Args:
            node_id (str): The node identifier, i.e. the node name in the graph.

        Raises:
            ObjectNotFoundError: If no node with the given identifier exists.

        Returns:
            Node: An ipycytoscape Node object whose identifier matches the given identifier.
        """
        if node_id in self._node_map:
            return self._node_map[node_id]
        if node_id in self.get_node_map():
            self._node_map = self.get_node_map()
            return self.get_node(node_id)
        raise ObjectNotFoundError(f'No node with id {node_id!r} found!')

    def get_node_element(self, node_id: str) -> Union[Instance, Port[Module]]:
        if node_id not in self.module_graph.nodes:
            raise ObjectNotFoundError(f'No node with id {node_id!r} found!')
        return self.module_graph.get_data(node_id, 'ndata')

    def get_edge_map(self) -> Dict[str, Edge]:
        return {e.data['ename']: e for e in self.cyto.graph.edges}

    def get_edge(self, wire_name: str) -> Edge:
        """Returns the edge object for the given wire name.

        Args:
            wire_name (str): The wire name in the graph.

        Raises:
            ObjectNotFoundError: If no edge with the given wire name exists.

        Returns:
            Edge: An ipycytoscape Edge object whose identifier matches the given wire name.
        """
        if wire_name in self._edge_map:
            return self._edge_map[wire_name]
        if wire_name in self.get_edge_map():
            self._edge_map = self.get_edge_map()
            return self.get_edge(wire_name)
        raise ObjectNotFoundError(f'No edge for wire name {wire_name!r} found!')

    def toggle_label(self, node: Union[str, Node]) -> None:
        """Toggles the label of the given node id or object.

        If the name of the node is currently shown, it will switch to the type of the node.
        If the type of the node is currently shown, it will switch to the name of the node instead.

        Args:
            node (Union[str, Node]): The name (identifer) of the node, or the node object itself.
        """
        if isinstance(node, str):
            node = self.get_node(node)
        node.data['label'] = node.data['id'] if node.data['label'] != node.data['id'] else node.data['nsubtype']

    def show(self) -> None:
        """Create and return an ipycytoscape widget for display in Jupyter notebooks."""

        self.cyto.cytoscape_layout = {'name': 'klay', 'klay': {'spacing': 40, 'nodeLayering': 'LONGEST_PATH'}}  # type: ignore
        # Assign CSS classes to nodes based on Formats.mapping
        # Updates formate and applies stylesheet
        self.update_format()

        # register callbacks
        self._register_callbacks()

        display(widgets.VBox([self.info_box, self.cyto]))  # type: ignore
        display(self.output)  # type: ignore[no-untyped-call]

    def _register_callbacks(self) -> None:
        """Register event callbacks for node/edge interactions."""

        # THere is a weird bug where only the first callback fnc is registered, and the second is ignored, so we add them manually
        CD = widgets.CallbackDispatcher  # type: ignore
        self.cyto._interaction_handlers = {  # type: ignore
            'node': {'click': CD(), 'mouseover': CD(), 'mouseout': CD()},  # type: ignore[misc]
            'edge': {'click': CD(), 'mouseover': CD(), 'mouseout': CD()},  # type: ignore[misc]
        }

        # Node/edge click: toggle node/edge label visibility
        self.cyto.on('node', 'click', self._node_click)
        self.cyto.on('node', 'mouseover', self._node_hover_in)
        self.cyto.on('node', 'mouseout', self._node_hover_out)
        self.cyto.on('edge', 'click', self._edge_click)
        self.cyto.on('edge', 'mouseover', self._edge_toggle)
        self.cyto.on('edge', 'mouseout', self._edge_toggle)

    def _node_click(self, node_data: cssDict) -> None:
        """Handle node click events to toggle label visibility.

        Args:
            node_data: Dictionary containing node data including 'id'.
        """
        with self.output:
            clicked_id = node_data.get('data', {}).get('id', '')
            self._toggle_node_label_style(clicked_id)
            self._select_node(clicked_id)
            self.update_format()

    def _node_hover_in(self, node_data: cssDict) -> None:
        clicked_id = node_data.get('data', {}).get('id', '')
        if 'transparent' not in self.formats.mapping[clicked_id]:
            self.formats.mapping[clicked_id].append('transparent')
        self.update_format()

    def _node_hover_out(self, node_data: cssDict) -> None:
        clicked_id = node_data.get('data', {}).get('id', '')
        if 'transparent' in self.formats.mapping[clicked_id]:
            self.formats.mapping[clicked_id].remove('transparent')
        self.update_format()

    def _toggle_node_label_style(self, clicked_id: str) -> None:
        n = self.get_node(clicked_id)
        self.toggle_label(n)  # Toggle the label string: name->type->name
        if 'italics' in self.formats.mapping[clicked_id]:
            self.formats.mapping[clicked_id].remove('italics')
        else:
            self.formats.mapping[clicked_id].append('italics')

    def _select_node(self, clicked_id: str) -> None:
        element = self.get_node_element(clicked_id)
        if self._active_node and 'selected' in self.formats.mapping[self._active_node]:
            self.formats.mapping[self._active_node].remove('selected')
        self._active_node = clicked_id if self._active_node != clicked_id else None
        if self._active_node:
            self.formats.mapping[self._active_node].append('selected')
        self._info_box.change_object(element if self._active_node is not None else None)

    def _edge_click(self, edge_data: cssDict) -> None:
        """Handle edge click events to toggle label visibility.

        Args:
            edge_data: Dictionary containing edge data including 'id'.
        """
        clicked_id = edge_data.get('data', {}).get('ename', '')
        if clicked_id in self._shown_edges:
            self._shown_edges.remove(clicked_id)
            self.get_edge(clicked_id).data['label'] = ''
        else:
            self._shown_edges.add(clicked_id)
        self._edge_toggle(edge_data)  # Toggle the label string on click (show/hide)

    def _edge_toggle(self, edge_data: cssDict) -> None:
        clicked_id = edge_data['data']['ename']
        edge = self.get_edge(clicked_id)
        if 'label' not in edge.data:
            edge.data['label'] = ''
        show_name = clicked_id in self._shown_edges or edge.data['label'] == ''
        width = f'\n({edge.data["width"]} bit)' if 'width' in edge.data else ''
        edge.data['label'] = f'{edge.data["ename"]}{width}' if show_name else ''

        self.update_format(nodes=[])  # No nodes to update, can skip this extra loop
