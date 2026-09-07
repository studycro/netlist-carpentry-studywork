"""Package for circuit visualization, mainly for displaying module graphs."""

from typing import Union

from netlist_carpentry import Module, ModuleGraph

from .dynamic import CytoscapeGraph
from .styling.format import FORMATS_IMMS


def show(module: Union[Module, ModuleGraph]) -> CytoscapeGraph:
    """Visualizes the given Module or ModuleGraph with standard settings and common formats.

    Loads and formats the graph, and displays it if possible in the current environment (e.g. in a Jupyter Notebook).
    Also returns the formatted CytoscapeGraph object for further modification.

    Args:
        module (Union[Module, ModuleGraph]): The Module or ModuleGraph object to visualize.

    Returns:
        CytoscapeGraph: The CytoscapeGraph object. Calling `CytoscapeGraph.show()` will show the graph
            if possible in the current environment (e.g. in a Jupyter Notebook).
    """
    if isinstance(module, Module):
        module = module.graph()
    g = CytoscapeGraph(module_graph=module, formats=FORMATS_IMMS)
    g.format_nodes(lambda n, d: d['ntype'] == 'INSTANCE', '.default')
    g.format_in_out(in_format='.in', out_format='.out')
    g.show()
    return g
