import os

import ipywidgets as widgets
import pytest

from netlist_carpentry import Circuit, Instance, Module
from netlist_carpentry.utils.gate_factory import not_gate
from netlist_carpentry.vis.dynamic.widgets import INFO_BOX_BASE_STYLE, InfoBox


@pytest.fixture()
def module() -> Module:
    m = Module(name='m')
    p1 = m.create_port('in1', 'input', width=4)
    p2 = m.create_port('out1', 'output', width=4, offset=2)
    not_gate(m, 'not_inst', A=p1, Y=p2)
    return m


def test_info_box_basics() -> None:
    b = InfoBox()
    template = """\n<div style="\n    {style}\n">\n    <h3 style="margin-top: 0; border-bottom: 1px solid #000; padding-bottom: 0px;">{title}</h3>\n    <div style="margin: 0; white-space: pre-wrap; tab-size: 4;">{content}</div>\n</div>\n"""
    assert isinstance(b, InfoBox)
    assert b.html_template == template
    assert isinstance(b.widget(), widgets.HTML)
    assert b.style == INFO_BOX_BASE_STYLE
    b.style.color = '#123456'
    assert b.style != INFO_BOX_BASE_STYLE
    assert b.style.color == '#123456'


def test_change_object(module: Module) -> None:
    b = InfoBox()
    assert b._object is None
    b.change_object(module.ports['in1'])
    assert b._object is module.ports['in1']
    b.change_object(module.instances['not_inst'])
    assert b._object is module.instances['not_inst']
    b.change_object(None)
    assert b._object is None


def test_get_display_data(module: Module) -> None:
    b = InfoBox()
    assert b.get_display_data() == '<i>Click on a node to see its details here.</i>'
    b.change_object(module.ports['in1'])
    assert b.get_display_data() == '<b>Name</b>: in1<br><b>Direction</b>: input<br><b>Width</b>: 4 bit'
    b.change_object(module.ports['out1'])
    assert b.get_display_data() == '<b>Name</b>: out1<br><b>Direction</b>: output<br><b>Width</b>: 4 bit<br><b>Offset</b>: 2'
    b.change_object(module.instances['not_inst'])
    assert (
        b.get_display_data()
        == '<b>Name</b>: not_inst<br><b>Type</b>: NotGate (§not)<br><b>Category</b>: Primitive Gate Instance<br><b>Ports</b>: <div style="margin: -14px; padding-left: 20px;"><br>\tA (input, 4 bit)<br>\tY (output, 4 bit)</div><br><b>Parameters</b>: <div style="margin: -14px; padding-left: 20px;"><br>\tY_WIDTH: 4<br>\tA_WIDTH: 4<br>\tA_SIGNED: False</div><br>'
    )


def test_get_display_data_port(module: Module) -> None:
    b = InfoBox()
    target_data = {'Name': 'in1', 'Direction': 'input', 'Width': '4 bit'}
    found_data = b._get_display_data_port(module.ports['in1'])
    assert target_data == found_data

    target_data = {'Name': 'out1', 'Direction': 'output', 'Width': '4 bit', 'Offset': '2'}
    found_data = b._get_display_data_port(module.ports['out1'])
    assert target_data == found_data


def test_get_display_data_instance(module: Module) -> None:
    b = InfoBox()
    target_data = {
        'Name': 'not_inst',
        'Type': 'NotGate (§not)',
        'Category': 'Primitive Gate Instance',
        'Ports': '<div style="margin: -14px; padding-left: 20px;"><br>\tA (input, 4 bit)<br>\tY (output, 4 bit)</div>',
        'Parameters': '<div style="margin: -14px; padding-left: 20px;"><br>\tY_WIDTH: 4<br>\tA_WIDTH: 4<br>\tA_SIGNED: False</div>',
    }
    found_data = b._get_display_data_instance(module.instances['not_inst'])
    assert target_data == found_data

    c = Circuit(name='c')
    c.add_module(module)
    msub = c.create_module('msub')
    msub.create_port('A')
    msub_inst = module.create_instance(msub, 'MSUB_INST')

    target_data = {
        'Name': 'MSUB_INST',
        'Type': 'msub',
        'Category': 'Module Instance (Submodule)',
        'Ports': '<div style="margin: -14px; padding-left: 20px;"><br>\tA (unknown, 1 bit)</div>',
    }
    found_data = b._get_display_data_instance(msub_inst)
    assert target_data == found_data

    mbb_inst = Instance(name='MBB_INST', instance_type='mbb', module=module)

    target_data = {
        'Name': 'MBB_INST',
        'Type': 'mbb',
        'Category': 'Blackbox Instance (No definition found)',
        'Ports': 'No Ports',
    }
    found_data = b._get_display_data_instance(mbb_inst)
    assert target_data == found_data


def test_get_idle_text() -> None:
    b = InfoBox()
    assert b._get_idle_text() == '<i>Click on a node to see its details here.</i>'


if __name__ == '__main__':
    file_name = os.path.basename(__file__)
    pytest.main(args=['-k', file_name])
