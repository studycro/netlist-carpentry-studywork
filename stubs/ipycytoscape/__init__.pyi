from typing import Any, Callable, Dict, List, Optional, Union

import ipywidgets as widgets
import networkx as nx
from traitlets import Instance

from netlist_carpentry.vis.styling import StylesheetDict

class Element(widgets.Widget):
    """Base class for Node and Edge."""

    data: Dict[str, str]
    classes: str

    def __init__(self, **kwargs: Any) -> None: ...

class Node(Element):
    position: Dict[str, Union[float, int]]

    def __init__(self, **kwargs: Any) -> None: ...

class Edge(Element):
    pannable: bool

    def __init__(self, **kwargs: Any) -> None: ...

class Graph(widgets.Widget):
    """Graph Widget containing nodes and edges."""

    nodes: List[Node]
    edges: List[Edge]

    def __init__(self, **kwargs: Any) -> None: ...
    def add_node(self, node: Node) -> None: ...
    def add_edge(self, edge: Edge) -> None: ...
    def add_graph_from_networkx(self, g: nx.Graph[str], directed: Optional[bool] = None, multiple_edges: Optional[bool] = None) -> None: ...
    def add_graph_from_json(self, json_file: Union[str, Dict[str, Any]]) -> None: ...

class CytoscapeWidget(widgets.DOMWidget):
    # interaction options
    min_zoom: float
    max_zoom: float
    zooming_enabled: bool
    user_zooming_enabled: bool
    panning_enabled: bool
    user_panning_enabled: bool
    box_selection_enabled: bool
    selection_type: str
    touch_tap_threshold: int
    desktop_tap_threshold: int
    autolock: bool = False
    auto_ungrabify: bool = False
    auto_unselectify: bool = True

    # rendering options
    headless: bool = False
    style_enabled: bool = True
    hide_edges_on_viewport: bool = False
    texture_on_viewport: bool = False
    motion_blur: bool = False
    motion_blur_opacity: float = 0.2
    wheel_sensitivity: float = 1
    cytoscape_layout: Dict[str, str]
    pixel_ratio: Union[str, float]
    cytoscape_style: List[StylesheetDict]
    zoom: float = 2.0
    rendered_position: Dict[str, Dict[str, int]] = Dict({'renderedPosition': {'x': 100, 'y': 100}})
    tooltip_source: str

    graph: Instance[Graph]

    def __init__(self, graph: Optional[Instance[Graph]] = None, **kwargs: object) -> None: ...
    def on(self, widget_type: str, event_type: str, callback: Callable[[Dict[str, Dict[str, str]]], None], remove: bool = False) -> None: ...
    def set_layout(self, **kwargs: object) -> None: ...
    def get_layout(self) -> Dict[str, str]: ...
    def relayout(self) -> None: ...
    def set_style(self, style: List[Dict[str, object]]) -> None: ...
    def get_style(self) -> List[Dict[str, object]]: ...
    def set_tooltip_source(self, source: str) -> None: ...
