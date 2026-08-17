from typing import Literal, Optional

from pydantic import BaseModel


class CytoscapeConfig(BaseModel):
    """A configuration class for cytoscape objects, handling environment values like
    `'min_zoom'`/`'max_zoom'` or `'panning_enabled'` that handle how the rendered widget behaves.
    A `CytoscapeConfig` can be applied to a CytoscapeWidget via `CytoscapeGraph.apply_config()`,
    where unset values (i.e. values that are `None`) are ignored, and the previous settings are kept.
    """

    min_zoom: Optional[float] = None
    max_zoom: Optional[float] = None
    zooming_enabled: Optional[bool] = None
    user_zooming_enabled: Optional[bool] = None
    panning_enabled: Optional[bool] = None
    user_panning_enabled: Optional[bool] = None
    box_selection_enabled: Optional[bool] = None
    selection_type: Optional[Literal['single', 'additive']] = None
    touch_tap_threshold: Optional[int] = None
    desktop_tap_threshold: Optional[int] = None
    autolock: Optional[bool] = None
    auto_ungrabify: Optional[bool] = None
    auto_unselectify: Optional[bool] = None

    # rendering options
    headless: Optional[bool] = None
    style_enabled: Optional[bool] = None
    hide_edges_on_viewport: Optional[bool] = None
    texture_on_viewport: Optional[bool] = None
    motion_blur: Optional[bool] = None
    motion_blur_opacity: Optional[float] = None
    wheel_sensitivity: Optional[float] = None
    zoom: Optional[float] = None


DEFAULT_CONFIG = CytoscapeConfig(min_zoom=1 / 5e0, max_zoom=5e0, autolock=False)
