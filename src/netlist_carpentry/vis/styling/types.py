"""A bunch of classes and type aliases related to graph formatting and visualization, for convenience and structure."""

from typing import Literal, TypedDict, Union

from pydantic import BaseModel
from typing_extensions import NotRequired

StyleDict = TypedDict(
    'StyleDict',
    {
        'background-color': NotRequired[str],
        'color': NotRequired[str],
        'content': NotRequired[str],
        'curve-style': NotRequired[str],
        'font-size': NotRequired[str],
        'font-style': NotRequired[str],
        'height': NotRequired[str],
        'label': NotRequired[str],
        'line-color': NotRequired[str],
        'shape': NotRequired[str],
        'target-arrow-color': NotRequired[str],
        'target-arrow-shape': NotRequired[str],
        'text-background-color': NotRequired[str],
        'text-background-opacity': NotRequired[int],
        'text-background-padding': NotRequired[str],
        'text-halign': NotRequired[str],
        'text-valign': NotRequired[str],
        'transition-property': NotRequired[str],
        'transition-duration': NotRequired[str],
        'width': NotRequired[str],
    },
)


class StylesheetDict(BaseModel):
    selector: Union[Literal['node', 'edge'], str]
    css: StyleDict


BorderStyleLiteral = Literal['dotted', 'dashed', 'solid', 'double', 'groove', 'ridge', 'inset', 'outset', 'none', 'hidden']
PositionLiteral = Literal['static', 'absolute', 'fixed', 'relative', 'sticky', 'initial', 'inherit']
CurveStyleLiteral = Literal['bezier', 'haystack', 'segments', 'straight', 'straight-triangle', 'taxi', 'unbundled-bezier']
FontStyleLiteral = Literal['normal', 'italic', 'oblique']
FontWeightLiteral = Literal['bold', 'bolder', 'lighter', 'normal']
LineStyleLiteral = Literal['solid', 'dashed', 'dotted']
ShapeLiteral = Literal[
    'barrel',
    'bottom-round-rectangle',
    'circle',
    'concave-hexagon',
    'cut-rectangle',
    'diamond',
    'ellipse',
    'hexagon',
    'heptagon',
    'octagon',
    'pentagon',
    'rectangle',
    'rhomboid',
    'round-diamond',
    'round-heptagon',
    'round-hexagon',
    'round-octagon',
    'round-rectangle',
    'round-tag',
    'round-triangle',
    'square',
    'star',
    'tag',
    'triangle',
    'vee',
]
ArrowShapeLiteral = Literal[
    'arrow', 'box-arrow', 'circle', 'circle-triangle', 'diamond', 'none', 'oval', 'tee', 'triangle', 'triangle-rectangle', 'triangle-vee', 'vee'
]
TextHAlignLiteral = Literal['left', 'center', 'right']
TextVAlignLiteral = Literal['top', 'center', 'bottom']
TextWrapLiteral = Literal['wrap', 'ellipsis', 'none']
