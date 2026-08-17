import os

import pytest

from netlist_carpentry import LOG
from netlist_carpentry.core.exceptions import IdentifierConflictError, ObjectNotFoundError
from netlist_carpentry.vis.styling import FormatDefinition, Formats
from netlist_carpentry.vis.styling.format import NODE_IMMS_BLUE1


def test_format_definition() -> None:
    f = FormatDefinition()

    assert f.background_color is None
    assert f.border is None
    assert f.border_color is None
    assert f.border_radius is None
    assert f.border_style is None
    assert f.border_width is None
    assert f.box_shadow is None
    assert f.color is None
    assert f.curve_style is None
    assert f.font_family is None
    assert f.font_size is None
    assert f.font_style is None
    assert f.font_weight is None
    assert f.height is None
    assert f.label is None
    assert f.left is None
    assert f.line_color is None
    assert f.line_dash_pattern is None
    assert f.line_height is None
    assert f.line_style is None
    assert f.line_width is None
    assert f.max_width is None
    assert f.min_width is None
    assert f.padding is None
    assert f.padding_bottom is None
    assert f.padding_left is None
    assert f.padding_right is None
    assert f.padding_top is None
    assert f.position is None
    assert f.shape is None
    assert f.target_arrow_color is None
    assert f.target_arrow_shape is None
    assert f.text_background_color is None
    assert f.text_background_opacity is None
    assert f.text_background_padding is None
    assert f.text_halign is None
    assert f.text_max_width is None
    assert f.text_min_width is None
    assert f.text_outline_color is None
    assert f.text_outline_opacity is None
    assert f.text_outline_width is None
    assert f.text_valign is None
    assert f.text_wrap is None
    assert f.top is None
    assert f.transition_property is None
    assert f.transition_duration is None
    assert f.width is None
    assert f.z_index is None

    f = FormatDefinition(color='#FFAA00', width='20', shape='ellipse', position='absolute')
    assert f.color == '#FFAA00'
    assert f.width == '20'
    assert f.shape == 'ellipse'
    assert f.position == 'absolute'


def test_format_definition_to_css() -> None:
    f = FormatDefinition(color='#FFAA00', width='20', shape='ellipse', background_color='#335512')
    d = f.to_css()
    assert len(d) == 4
    assert d['color'] == '#FFAA00'
    assert d['width'] == '20'
    assert d['shape'] == 'ellipse'
    assert d['background-color'] == '#335512'
    assert 'background_color' not in d  # underscores transformed to dashes


def test_format_definition_copy() -> None:
    f = FormatDefinition(color='#FFAA00', width='20', shape='ellipse')
    assert f.color == '#FFAA00'
    assert f.width == '20'
    assert f.shape == 'ellipse'
    assert f.height is None
    f2 = f.copy_({'height': '20px', 'color': None})
    assert f2.color is None
    assert f2.width == '20'
    assert f2.shape == 'ellipse'
    assert f2.height == '20px'


def test_format_definition_merge() -> None:
    f1 = FormatDefinition(color='#FFAA00', width='20', shape='ellipse')
    f2 = FormatDefinition(height='20px', color=None)
    f3 = f1.merge(f2)
    assert f1.color == '#FFAA00'
    assert f1.width == '20'
    assert f1.shape == 'ellipse'
    assert f1.height is None
    assert f2.color is None
    assert f2.width is None
    assert f2.shape is None
    assert f2.height == '20px'
    assert f3.color == '#FFAA00'
    assert f3.width == '20'
    assert f3.shape == 'ellipse'
    assert f3.height == '20px'


def test_format_data() -> None:
    fs = Formats()
    assert fs.definitions == {}
    assert fs.mapping == {}
    assert fs.mapping['nonexisting_node'] == []


def test_format_data_create_format() -> None:
    fs = Formats()
    assert fs.definitions == {}
    fd = FormatDefinition(color='#AABBCC', width='42', shape='rectangle')
    f = fs.add_format('foo', fd)
    assert fd is f
    assert isinstance(f, FormatDefinition)
    assert f.color == '#AABBCC'
    assert f.width == '42'
    assert f.height is None
    assert f.shape == 'rectangle'
    assert fs.definitions == {'foo': f}

    fd2 = FormatDefinition(color='lightblue', width='69', shape='ellipse')
    with pytest.raises(IdentifierConflictError):
        fs.add_format('foo', fd2)
    assert fs.definitions == {'foo': f}
    f2 = fs.add_format('bar', fd2)
    assert f2.color == 'lightblue'
    assert f2.width == '69'
    assert f2.shape == 'ellipse'
    assert fs.definitions == {'foo': f, 'bar': f2}


def test_format_data_remove_format() -> None:
    fs = Formats()
    with pytest.raises(ObjectNotFoundError):
        fs.remove_format('foo')

    fd = FormatDefinition(color='#AABBCC', width='42', shape='rectangle')
    f = fs.add_format('foo', fd)
    assert fs.definitions == {'foo': f}

    fs.remove_format('foo')
    assert fs.definitions == {}


def test_format_data_format_nodes() -> None:
    fs = Formats()
    warns = LOG.warns_quantity
    fs.format_nodes('node1', 'f')
    assert LOG.warns_quantity == warns + 1
    assert fs.definitions == {}
    assert fs.mapping == {'node1': ['f']}

    fs.format_nodes(['node1', 'node2', 'node3'], 'g')
    assert LOG.warns_quantity == warns + 2
    assert fs.definitions == {}
    assert fs.mapping == {'node1': ['f', 'g'], 'node2': ['g'], 'node3': ['g']}

    fs.format_nodes(['node1', 'node2', 'node3'], 'g', append=False)
    assert LOG.warns_quantity == warns + 3
    assert fs.definitions == {}
    assert fs.mapping == {'node1': ['g'], 'node2': ['g'], 'node3': ['g']}

    f = fs.add_format('imms_blue', NODE_IMMS_BLUE1)
    fs.format_nodes(['node4'], 'imms_blue')
    assert LOG.warns_quantity == warns + 3
    assert fs.definitions == {'imms_blue': f}
    assert fs.mapping == {'node1': ['g'], 'node2': ['g'], 'node3': ['g'], 'node4': ['imms_blue']}


if __name__ == '__main__':
    file_name = os.path.basename(__file__)
    pytest.main(args=['-k', file_name])
