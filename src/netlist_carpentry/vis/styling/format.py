from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Union

from pydantic import BaseModel, ConfigDict
from typing_extensions import Self

import netlist_carpentry.vis.styling.types as types
from netlist_carpentry.core.exceptions import IdentifierConflictError, ObjectNotFoundError
from netlist_carpentry.utils import LOG

FormatName = str
NodeName = str
Label = str


def to_css_syntax(string: str) -> str:
    return string.replace('_', '-')


class FormatDefinition(BaseModel):
    model_config = ConfigDict(alias_generator=to_css_syntax, populate_by_name=True)  # populate_by_name: Can still use line_color="blue" in Python

    background_color: Optional[str] = None
    """Node background color as a plain string, e.g. `'red'` or hex code, e.g. `'#ABCDEF'`."""
    background_opacity: Optional[str] = None
    """Node background opacity from 0 (transparent) to 1 (opaque), e.g. `'0.5'`."""
    border: Optional[str] = None
    """Shorthand for `border-width border-style (required) border-color`, e.g. `'solid'` or `'5px dotted blue'`."""
    border_color: Optional[str] = None
    """Node border color as a plain string, e.g. `'black'` or hex code, e.g. `'#ABCDEF'`."""
    border_radius: Optional[str] = None
    """Node border corner radius, e.g. `'5px'`."""
    border_style: Union[str, types.BorderStyleLiteral, None] = None
    """Node border style, e.g. `'solid'` or `'dashed'`."""
    border_width: Optional[str] = None
    """Node border width, e.g. `'2px'`."""
    box_shadow: Optional[str] = None
    """Node box shadow effect, e.g. `'2px 2px 5px #ABCDEF'`."""
    color: Optional[str] = None
    """Node text color as a plain string, e.g. `'red'` or hex code, e.g. `'#ABCDEF'`."""
    curve_style: Union[str, types.CurveStyleLiteral, None] = None
    """Style of edges curvature, e.g. `'bezier'`, `'unbundled-bezier'`, or `'source-target'`."""
    font_family: Optional[str] = None
    """Node or edge label font family, e.g. `'sans-serif'` or `'monospace'`."""
    font_size: Optional[str] = None
    """Node or edge label text size, e.g. `'14px'`."""
    font_style: Union[str, types.FontStyleLiteral, None] = None
    """Node or edge label font style, e.g. `'italic'`, `'oblique'`, or `'normal'`."""
    font_weight: Union[str, types.FontWeightLiteral, None] = None
    """Node or edge label font weight, e.g. `'normal'`, `'bold'`, `'bolder'`, `'lighter'`, or a number from 100 to 900."""
    height: Optional[str] = None
    """Node height, e.g. `'80px'`."""
    label: Optional[str] = None
    """Node or edge label as plain text."""
    left: Optional[str] = None
    """Node horizontal position from the left edge, e.g. `'100px'`."""
    line_color: Optional[str] = None
    """Edge color as a plain string, e.g. `'red'` or hex code, e.g. `'#ABCDEF'`."""
    line_dash_pattern: Optional[str] = None
    """Edge line dash pattern, e.g. `'4,2'` for dashed lines or `'2,2'` for dotted lines."""
    line_height: Optional[str] = None
    """Line height multiplier for text, e.g. `'1.2'`."""
    line_style: Union[str, types.LineStyleLiteral, None] = None
    """Edge line style, e.g. `'solid'`, `'dashed'`, or `'dotted'`."""
    line_width: Optional[str] = None
    """Edge line width, e.g. `'2px'`."""
    max_width: Optional[str] = None
    """Maximum node width, e.g. `'200px'`."""
    min_width: Optional[str] = None
    """Minimum node width, e.g. `'50px'`."""
    padding: Optional[str] = None
    """Node internal padding, e.g. `'10px'`."""
    padding_bottom: Optional[str] = None
    """Node internal bottom padding, e.g. `'10px'`."""
    padding_left: Optional[str] = None
    """Node internal left padding, e.g. `'10px'`."""
    padding_right: Optional[str] = None
    """Node internal right padding, e.g. `'10px'`."""
    padding_top: Optional[str] = None
    """Node internal top padding, e.g. `'10px'`."""
    position: Union[str, types.PositionLiteral, None] = None
    """Node position as coordinates, e.g. `'{x: 100, y: 200}'`."""
    shape: Union[str, types.ShapeLiteral, None] = None
    """Node shape, e.g. `'rectangle'`, `'ellipse'`, `'circle'`, `'diamond'`, `'triangle'`, etc."""
    target_arrow_color: Optional[str] = None
    """Edge arrow color as a plain string, e.g. `'red'` or hex code, e.g. `'#ABCDEF'`."""
    target_arrow_shape: Union[str, types.ArrowShapeLiteral, None] = None
    """Edge arrow shape, e.g. `'triangle'`, `'vee'`, `'circle'`, `'diamond'`, `'none'`, etc."""
    text_background_color: Optional[str] = None
    """Text background fill color, e.g. `'white'` or hex code, `'#ABCDEF'`."""
    text_background_opacity: Optional[str] = None
    """Text background opacity from 0 (transparent) to 1 (opaque), e.g. `'0.5'`."""
    text_background_padding: Optional[str] = None
    """Padding around text background, e.g. `'5px'`."""
    text_halign: Union[str, types.TextHAlignLiteral, None] = None
    """Horizontal alignment of node or edge text, e.g. `'center'`, `'left'`, or `'right'`."""
    text_max_width: Optional[str] = None
    """Maximum text width before wrapping, e.g. `'150px'`."""
    text_min_width: Optional[str] = None
    """Minimum text width before wrapping, e.g. `'150px'`."""
    text_outline_color: Optional[str] = None
    """Text outline/stroke color, e.g. `'white'` or hex code, `'#ABCDEF'`."""
    text_outline_opacity: Optional[str] = None
    """Text outline opacity from 0 (transparent) to 1 (opaque), e.g. `'0.5'`."""
    text_outline_width: Optional[str] = None
    """Text outline/stroke width, e.g. `'1px'`."""
    text_valign: Union[str, types.TextVAlignLiteral, None] = None
    """Vertical alignment of node or edge text, e.g. `'center'`, `'top'`, or `'bottom'`."""
    text_wrap: Union[str, types.TextWrapLiteral, None] = None
    """Text wrapping mode, e.g. `'wrap'`, `'ellipsis'`, or `'none'`."""
    top: Optional[str] = None
    """Node vertical position from the top edge, e.g. `'50px'`."""
    transition_property: Optional[str] = None
    """CSS property to animate, e.g. `'background-color'`."""
    transition_duration: Optional[str] = None
    """Animation duration, e.g. `'0.3s'`."""
    width: Optional[str] = None
    """Node width, e.g. `'80px'`."""
    z_index: Optional[str] = None
    """Stacking order of the node, e.g. `'10'`."""

    def to_css(self) -> Dict[str, Optional[str]]:
        return self.model_dump(by_alias=True, exclude_none=True)  # type: ignore

    def copy_(self, update: Optional[Dict[str, Optional[str]]] = None) -> Self:
        """Alias for self.model_copy(update).

        Copies the current object and updates values in the new object as specified in the given dictionary.

        Args:
            update (Optional[Dict[str, Optional[str]]], optional): An update dictionary with values to set in the new object.
                Entries with `None` as value are also valid, since this will reset the parameter to its default value.
                If None, the object is copied and left as-is. Defaults to None.

        Returns:
            Self: A copy of this object, with value changes if specified in the `update` dictionary.
        """
        return self.model_copy(update=update)

    def merge(self, other: Self) -> Self:
        """Merges the current object together with another FormatDefinition object into a new object.

        None values in both objects are ignored (i.e. remain as None).
        The values from the `other` object take precedence over the current object.
        Both original objects remain unchanged, and a new object with the merged properties is returned.

        Args:
            other (Self): Another FormatDefinition object to merge with.

        Returns:
            Self: A **new** FormatDefinition object that combines the properties of both objects.

        Example:
            ```python
            >>> f1 = FormatDefinition(color='red', width='20')
            >>> f2 = FormatDefinition(height='30', color=None)
            >>> f3 = f1.merge(f2)
            >>> f3.color
            'red'
            >>> f3.width
            '20'
            >>> f3.height
            '30'

            ```
        """
        merged_dict: Dict[str, Optional[str]] = self.model_dump(exclude_none=True)
        other_dict: Dict[str, Optional[str]] = other.model_dump(exclude_none=True)
        merged_dict.update(other_dict)
        return self.__class__(**merged_dict)


class Formats(BaseModel):
    definitions: Dict[FormatName, FormatDefinition] = {}
    mapping: Dict[NodeName, List[FormatName]] = defaultdict(list)  # Maps node names to a list of format names (i.e. classes)
    _label_types: Dict[NodeName, Label] = {}
    _label_names: Dict[NodeName, Label] = {}

    def add_format(self, name: FormatName, format: FormatDefinition) -> FormatDefinition:
        """Adds a format with the given name and the provided format definition.

        If the format name starts with a period (.), ipycytoscape will treat it like a CSS class.

        Args:
            name (FormatName): The name of the format.
                If the format name starts with a period (.), ipycytoscape will treat it like a CSS class.
            format (FormatDefinition): The format definition associated with the given name.

        Raises:
            IdentifierConflictError: If the given name is already used for a format definition.

        Returns:
            FormatDefinition: The given format definition.
        """
        if name in self.definitions:
            raise IdentifierConflictError(f'A format {name!r} already exists!')
        self.definitions[name] = format
        return format

    def remove_format(self, format: FormatName) -> None:
        """Removes a format with the given name from the definitions.

        Args:
            format (FormatName): The name of the format to remove.

        Raises:
            ObjectNotFoundError: If the given format name does not exist.
        """
        if format not in self.definitions:
            raise ObjectNotFoundError(f'A format {format!r} does not exist!')
        self.definitions.pop(format)

    def format_nodes(self, nodes: Union[NodeName, Iterable[NodeName]], format: FormatName, append: bool = True) -> None:
        """Formats the specified nodes with the given format.

        If `append` is True, the format is added to the existing formats for each node.
        If False, it overwrites any existing formats, so that the specified nodes only have the given format afterwards.

        Args:
            nodes (Union[NodeName, Iterable[NodeName]]): The nodes to format.
            format (FormatName): The name of the format to apply.
            append (bool, optional): Whether to append the format to existing formats for each node.
                If False, overwrites existing formats. Defaults to True.
        """
        if format not in self.definitions:
            LOG.warn(f'No format with name {format!r} found!')
        if isinstance(nodes, str):
            nodes = [nodes]
        for n in nodes:
            if append:
                self.mapping[n].append(format)
            else:
                self.mapping[n] = [format]


CSS_TRANSITION: Dict[str, Optional[str]] = {'transition_property': 'background-color, border-width, width', 'transition_duration': '0.2s'}
DEFAULT_NODE = FormatDefinition(color='black', label='data(label)', font_size='14px').copy_(CSS_TRANSITION)
DEFAULT_EDGE = FormatDefinition(label='data(label)', curve_style='bezier', target_arrow_shape='triangle', font_size='11px', text_wrap='wrap')

NODE_IMMS_BLUE1 = DEFAULT_NODE.merge(FormatDefinition(background_color='#95B6DF'))
NODE_IMMS_BLUE2 = DEFAULT_NODE.merge(FormatDefinition(background_color='#6C8CC7'))
NODE_IMMS_BLUE3 = DEFAULT_NODE.merge(FormatDefinition(background_color='#005BAA'))
NODE_IMMS_BLUE4 = DEFAULT_NODE.merge(FormatDefinition(background_color='#034694'))
NODE_IMMS_GREEN1 = DEFAULT_NODE.merge(FormatDefinition(background_color='#B2D235'))
NODE_IMMS_GREEN2 = DEFAULT_NODE.merge(FormatDefinition(background_color='#7EA831'))
NODE_IMMS_GREEN3 = DEFAULT_NODE.merge(FormatDefinition(background_color='#54771E'))
NODE_IMMS_RED = DEFAULT_NODE.merge(FormatDefinition(background_color='#C9252C'))

FORMATS_IMMS = Formats(
    definitions={
        'node': DEFAULT_NODE,
        'edge': DEFAULT_EDGE,
        '.in': NODE_IMMS_RED,
        '.out': NODE_IMMS_GREEN3,
        '.default': NODE_IMMS_BLUE1.merge(FormatDefinition(shape='round-rectangle')),
        '.italics': FormatDefinition(font_style='italic'),
        '.selected': FormatDefinition(border_color='#8800AA', border_width='5px', border_style='solid', background_color='#FFAA55'),
        '.transparent': FormatDefinition(background_opacity='0.5'),
    }
)
