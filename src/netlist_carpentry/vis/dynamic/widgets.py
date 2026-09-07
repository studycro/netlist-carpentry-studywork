"""Handles the behavior of additional widges, e.g. the InfoBox."""

from typing import Callable, Dict, TypeVar, Union

import ipywidgets as widgets
from pydantic import BaseModel

from netlist_carpentry import Instance, Module, Port
from netlist_carpentry.vis.styling.format import FormatDefinition

INFO_BOX_BASE_STYLE = FormatDefinition(
    background_color='#95B6DF',  # IMMS light blue 1
    border='2px solid #6C8CC7',  # IMMS light blue 2
    border_radius='8px',
    box_shadow='0px 4px 10px rgba(0,0,0,1)',
    color='#000',
    font_family='sans-serif',
    left='15px',
    line_height='1.2',
    min_width='200px',
    padding='10px',
    position='absolute',
    text_wrap='wrap',
    top='15px',
    z_index='999',
)

T = TypeVar('T')


class InfoBox(BaseModel):
    """The InfoBox widget containing additional data about the selected node."""

    _style = INFO_BOX_BASE_STYLE.model_copy()
    _object: Union[Instance, Port[Module], None] = None
    _data: Dict[str, str] = {}

    @property
    def style(self) -> FormatDefinition:
        """The style (FormatDefinition) of this info box."""
        return self._style

    @property
    def html_template(self) -> str:
        return """
<div style="
    {style}
">
    <h3 style="margin-top: 0; border-bottom: 1px solid #000; padding-bottom: 0px;">{title}</h3>
    <div style="margin: 0; white-space: pre-wrap; tab-size: 4;">{content}</div>
</div>
"""

    def model_post_init(self, context: object) -> None:
        self._html: widgets.HTML = widgets.HTML()

    def change_object(self, new_obj: Union[Instance, Port[Module], None]) -> None:
        """Changes the currently selected object to the new (given) object, whose data will then be shown.

        If None is passed, the previously selected object will just be removed and the idle/inactive text will be shown instead.

        Args:
            new_obj (Union[Instance, Port[Module], None]): The new object (module port or instance), whose date will then be shown.
                If None, the previously selected object will just be removed and the idle/inactive text will be shown instead.
        """
        self._object = new_obj
        self.widget()

    def get_display_data(self) -> str:
        """Returns the data to display in the info box based on the currently selected node."""
        if isinstance(self._object, Port):
            return '<br>'.join(f'<b>{k}</b>: {v}' for k, v in self._get_display_data_port(self._object).items())
        elif isinstance(self._object, Instance):
            return ''.join(f'<b>{k}</b>: {v}<br>' for k, v in self._get_display_data_instance(self._object).items())
        return self._get_idle_text()

    def _get_display_data_port(self, port: Port[Module]) -> Dict[str, str]:
        data = {'Name': port.name, 'Direction': port.direction.value, 'Width': f'{port.width} bit'}
        if port.offset:
            data['Offset'] = str(port.offset)
        return data

    def _get_display_data_instance(self, instance: Instance) -> Dict[str, str]:
        if instance.is_primitive:
            itype = f'{instance.__class__.__name__} ({instance.instance_type})'
            category = 'Primitive Gate Instance'
        else:
            itype = instance.instance_type
            category = 'Module Instance (Submodule)' if instance.is_module_instance else 'Blackbox Instance (No definition found)'
        ports = self._make_list(dict(instance.ports), lambda n, p: f'{n} ({p.direction.value}, {p.width} bit)') if instance.ports else 'No Ports'
        data = {'Name': instance.name, 'Type': itype, 'Category': category, 'Ports': ports}
        if instance.parameters:
            data['Parameters'] = self._make_list(instance.parameters.model_dump(exclude_none=True), lambda k, v: f'{k}: {v}')  # type: ignore[misc]
        return data

    def _make_list(self, data_dict: Dict[str, T], format_fnc: Callable[[str, T], str]) -> str:
        lst_template = '<div style="margin: -14px; padding-left: 20px;">{content}</div>'
        data = ''.join(f'<br>\t{format_fnc(k, v)}' for k, v in data_dict.items())
        return lst_template.format(content=data)

    def _get_idle_text(self) -> str:
        return '<i>Click on a node to see its details here.</i>'

    def widget(self) -> widgets.HTML:
        """Returns the HTML widget representing this info box.

        Can be displayed via `display(InfoBox.widget())`

        Returns:
            widgets.HTML: The HTML widget representing this info box.
        """
        style = '\n    '.join(f'{k}: {v};' for k, v in self.style.to_css().items())
        title = 'Node Info'
        self._html.value = self.html_template.format(style=style, title=title, content=self.get_display_data())
        return self._html
