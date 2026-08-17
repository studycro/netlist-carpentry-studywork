"""Package for circuit visualization, mainly for displaying module graphs."""

from typing import Union

from netlist_carpentry import Module, ModuleGraph

from .dynamic import CytoscapeGraph
from .styling.format import FORMATS_IMMS


def show(module: Union[Module, ModuleGraph]) -> CytoscapeGraph:
    if isinstance(module, Module):
        module = module.graph()
    g = CytoscapeGraph(module_graph=module, formats=FORMATS_IMMS)
    g.format_nodes(lambda n, d: d['ntype'] == 'INSTANCE', '.default')
    g.format_in_out(in_format='.in', out_format='.out')
    g.show()
    return g
