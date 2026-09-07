from typing import Literal, Optional

from pydantic import BaseModel


class CytoscapeConfig(BaseModel):
    """A configuration class for cytoscape objects, handling environment values like
    `'min_zoom'`/`'max_zoom'` or `'panning_enabled'` that handle how the rendered widget behaves.
    A `CytoscapeConfig` can be applied to a CytoscapeWidget via `CytoscapeGraph.apply_config()`,
    where unset values (i.e. values that are `None`) are ignored, and the previous settings are kept.
    """

    min_zoom: Optional[float] = None
    """Minimum zoom level (scale factor) of the viewport."""
    max_zoom: Optional[float] = None
    """Maximum zoom level (scale factor) of the viewport."""
    zooming_enabled: Optional[bool] = None
    """Whether zooming of the viewport is enabled."""
    user_zooming_enabled: Optional[bool] = None
    """Whether user-initiated zooming (scroll/pinch) is enabled."""
    panning_enabled: Optional[bool] = None
    """Whether panning of the viewport is enabled."""
    user_panning_enabled: Optional[bool] = None
    """Whether user-initiated panning (drag) is enabled."""
    box_selection_enabled: Optional[bool] = None
    """Whether box (rectangle) selection of elements is enabled."""
    selection_type: Optional[Literal['single', 'additive']] = None
    """Selection mode: 'single' replaces the selection, 'additive' adds to it."""
    touch_tap_threshold: Optional[int] = None
    """Number of taps on a touch device required to trigger a selection."""
    desktop_tap_threshold: Optional[int] = None
    """Number of clicks on a desktop required to trigger a selection."""
    autolock: Optional[bool] = None
    """Whether the graph layout is automatically locked after rendering."""
    auto_ungrabify: Optional[bool] = None
    """Whether nodes are automatically made non-grabbable (non-movable by user)."""
    auto_unselectify: Optional[bool] = None
    """Whether nodes are automatically made non-selectable by the user."""

    # rendering options
    headless: Optional[bool] = None
    """Whether to run in headless mode (no visual rendering)."""
    style_enabled: Optional[bool] = None
    """Whether CSS-like styling of elements is enabled."""
    hide_edges_on_viewport: Optional[bool] = None
    """Whether to hide edges when zoomed out beyond a threshold."""
    texture_on_viewport: Optional[bool] = None
    """Whether to use texture-based rendering for the viewport."""
    motion_blur: Optional[bool] = None
    """Whether to apply a motion blur effect during panning/zooming."""
    motion_blur_opacity: Optional[float] = None
    """Opacity of the motion blur trail (0.0 to 1.0)."""
    wheel_sensitivity: Optional[float] = None
    """Sensitivity multiplier for mouse-wheel zooming."""
    zoom: Optional[float] = None
    """Initial zoom level (scale factor) of the viewport."""


DEFAULT_CONFIG = CytoscapeConfig(min_zoom=1 / 5e0, max_zoom=5e0, autolock=False)
"""A default config for ipycytoscape with common settings."""
