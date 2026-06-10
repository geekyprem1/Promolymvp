"""
templates.py – Backend Template Registry for Promoly.

Each template defines the behavioral layer:
  • camera  – zoom/pan ranges per scene type
  • transitions – which Remotion transition to use per scene type
  • motion_graphics – which overlays to enable (cursor, highlights, badges)
  • spring – spring physics config (stiffness, damping, mass)

Visual tokens (colors, typography, CTA style) live in remotion/src/lib/templates.ts
and are resolved client-side by Remotion using the templateId key.

Adding a new template:
  1. Create a BackendTemplateConfig instance in this file.
  2. Add it to TEMPLATES dict with the same key you'll use in templates.ts.
  3. Add it to the TEMPLATE_LIST for frontend enumeration.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── Sub-configs ───────────────────────────────────────────────────────────────

@dataclass
class CameraTemplateConfig:
    hero_zoom_from:      float = 1.08
    hero_zoom_to:        float = 1.02
    hero_pan_x:          int   = -20
    hero_pan_y:          int   = 0
    hero_focus_x:        float = 0.45
    hero_focus_y:        float = 0.40

    features_zoom_from:  float = 1.0
    features_zoom_to:    float = 1.03
    features_pan_x:      int   = 18
    features_focus_x:    float = 0.5
    features_focus_y:    float = 0.5

    cta_zoom_from:       float = 0.97
    cta_zoom_to:         float = 1.04
    cta_focus_x:         float = 0.5
    cta_focus_y:         float = 0.65

    hook_zoom_from:      float = 1.06
    hook_zoom_to:        float = 1.0
    problem_zoom_from:   float = 1.0
    problem_zoom_to:     float = 1.0
    solution_zoom_from:  float = 0.97
    solution_zoom_to:    float = 1.02


@dataclass
class TransitionTemplateConfig:
    hero:         str = "fade"
    hook:         str = "fade"
    problem:      str = "dissolve"
    solution:     str = "zoomIn"
    features:     str = "slideLeft"
    benefits:     str = "slideRight"
    testimonials: str = "dissolve"
    cta:          str = "zoomIn"
    default:      str = "fade"


@dataclass
class MotionGraphicsTemplateConfig:
    show_cursor:    bool = True
    show_highlights: bool = True
    show_badges:    bool = True
    cursor_style:   str  = "trail"   # "trail" | "click" | "both" | "none"
    badge_style:    str  = "pill"    # "pill" | "tag" | "chip"
    highlight_on_scenes: list[str] = field(default_factory=lambda: ["features", "cta", "testimonials"])


@dataclass
class SpringTemplateConfig:
    stiffness: float = 100.0
    damping:   float = 14.0
    mass:      float = 1.0


@dataclass
class BackendTemplateConfig:
    id:               str
    name:             str
    description:      str
    camera:           CameraTemplateConfig
    transitions:      TransitionTemplateConfig
    motion_graphics:  MotionGraphicsTemplateConfig
    spring:           SpringTemplateConfig

    def transition_for(self, scene_type: str) -> str:
        return getattr(self.transitions, scene_type, self.transitions.default)

    def camera_for_scene(self, scene_type: str) -> dict:
        """Return a camera dict compatible with motion_planner._plan_camera output."""
        c = self.camera
        if scene_type == "hero":
            return {"zoomFrom": c.hero_zoom_from, "zoomTo": c.hero_zoom_to,
                    "panX": c.hero_pan_x, "panY": c.hero_pan_y,
                    "focusX": c.hero_focus_x, "focusY": c.hero_focus_y}
        if scene_type in ("features", "benefits", "content"):
            direction = 1  # caller can invert based on reverse
            return {"zoomFrom": c.features_zoom_from, "zoomTo": c.features_zoom_to,
                    "panX": c.features_pan_x * direction, "panY": 0,
                    "focusX": c.features_focus_x, "focusY": c.features_focus_y}
        if scene_type == "cta":
            return {"zoomFrom": c.cta_zoom_from, "zoomTo": c.cta_zoom_to,
                    "panX": 0, "panY": 0, "focusX": c.cta_focus_x, "focusY": c.cta_focus_y}
        if scene_type == "hook":
            return {"zoomFrom": c.hook_zoom_from, "zoomTo": c.hook_zoom_to,
                    "panX": 0, "panY": 0, "focusX": 0.5, "focusY": 0.45}
        if scene_type == "problem":
            return {"zoomFrom": c.problem_zoom_from, "zoomTo": c.problem_zoom_to,
                    "panX": 0, "panY": 0, "focusX": 0.5, "focusY": 0.5}
        if scene_type == "solution":
            return {"zoomFrom": c.solution_zoom_from, "zoomTo": c.solution_zoom_to,
                    "panX": 0, "panY": 0, "focusX": 0.5, "focusY": 0.5}
        # testimonials / fallback
        return {"zoomFrom": 1.02, "zoomTo": 1.0,
                "panX": 0, "panY": -8, "focusX": 0.5, "focusY": 0.55}


# ── Template definitions ──────────────────────────────────────────────────────

MODERN_SAAS = BackendTemplateConfig(
    id          = "modern-saas",
    name        = "Modern SaaS",
    description = "Bold gradients, animated overlays, indigo palette",
    camera      = CameraTemplateConfig(),   # all defaults
    transitions = TransitionTemplateConfig(),
    motion_graphics = MotionGraphicsTemplateConfig(
        show_cursor     = True,
        show_highlights = True,
        show_badges     = True,
        cursor_style    = "trail",
        highlight_on_scenes = ["features", "cta", "hero"],
    ),
    spring = SpringTemplateConfig(stiffness=100, damping=14, mass=1.0),
)

APPLE_STYLE = BackendTemplateConfig(
    id          = "apple",
    name        = "Apple Style",
    description = "Elegant, minimal motion, SF-style typography",
    camera      = CameraTemplateConfig(
        hero_zoom_from=1.02, hero_zoom_to=1.0,
        hero_pan_x=0, hero_pan_y=0, hero_focus_x=0.5, hero_focus_y=0.5,
        features_zoom_from=1.0, features_zoom_to=1.015,
        features_pan_x=0,
        cta_zoom_from=1.0, cta_zoom_to=1.01,
        hook_zoom_from=1.02, hook_zoom_to=1.0,
        problem_zoom_from=1.0, problem_zoom_to=1.0,
        solution_zoom_from=1.0, solution_zoom_to=1.01,
    ),
    transitions = TransitionTemplateConfig(
        hero="fade", hook="fade", problem="fade", solution="fade",
        features="fade", benefits="fade", testimonials="fade",
        cta="fade", default="fade",
    ),
    motion_graphics = MotionGraphicsTemplateConfig(
        show_cursor     = False,
        show_highlights = False,
        show_badges     = False,
        cursor_style    = "none",
        highlight_on_scenes = [],
    ),
    spring = SpringTemplateConfig(stiffness=55, damping=24, mass=1.2),
)

STARTUP_PITCH = BackendTemplateConfig(
    id          = "startup",
    name        = "Startup Pitch",
    description = "High energy, bold red, bouncy animations, stats-forward",
    camera      = CameraTemplateConfig(
        hero_zoom_from=1.0, hero_zoom_to=1.08,   # zoom IN (opposite of SaaS)
        hero_pan_x=-30, hero_pan_y=0,
        hero_focus_x=0.5, hero_focus_y=0.5,
        features_zoom_from=1.0, features_zoom_to=1.05,
        features_pan_x=25,
        cta_zoom_from=0.95, cta_zoom_to=1.06,
        hook_zoom_from=1.0, hook_zoom_to=1.08,
        problem_zoom_from=1.02, problem_zoom_to=1.0,
        solution_zoom_from=0.95, solution_zoom_to=1.04,
    ),
    transitions = TransitionTemplateConfig(
        hero="zoomIn", hook="zoomIn", problem="dissolve",
        solution="zoomIn", features="slideLeft",
        benefits="slideRight", testimonials="dissolve",
        cta="zoomIn", default="slideLeft",
    ),
    motion_graphics = MotionGraphicsTemplateConfig(
        show_cursor      = True,
        show_highlights  = True,
        show_badges      = True,
        cursor_style     = "click",
        badge_style      = "chip",
        highlight_on_scenes = ["features", "cta", "hook", "solution"],
    ),
    spring = SpringTemplateConfig(stiffness=240, damping=8, mass=0.8),
)

MINIMAL = BackendTemplateConfig(
    id          = "minimal",
    name        = "Minimal",
    description = "Light background, static camera, opacity-only motion",
    camera      = CameraTemplateConfig(
        hero_zoom_from=1.0, hero_zoom_to=1.0,
        hero_pan_x=0, hero_pan_y=0, hero_focus_x=0.5, hero_focus_y=0.5,
        features_zoom_from=1.0, features_zoom_to=1.0,
        features_pan_x=0,
        cta_zoom_from=1.0, cta_zoom_to=1.0,
        hook_zoom_from=1.0, hook_zoom_to=1.0,
        problem_zoom_from=1.0, problem_zoom_to=1.0,
        solution_zoom_from=1.0, solution_zoom_to=1.0,
    ),
    transitions = TransitionTemplateConfig(
        hero="fade", hook="fade", problem="dissolve", solution="fade",
        features="fade", benefits="fade", testimonials="dissolve",
        cta="fade", default="fade",
    ),
    motion_graphics = MotionGraphicsTemplateConfig(
        show_cursor      = False,
        show_highlights  = False,
        show_badges      = False,
        cursor_style     = "none",
        highlight_on_scenes = [],
    ),
    spring = SpringTemplateConfig(stiffness=40, damping=28, mass=1.5),
)


# ── Registry ──────────────────────────────────────────────────────────────────

TEMPLATES: dict[str, BackendTemplateConfig] = {
    "modern-saas": MODERN_SAAS,
    "apple":       APPLE_STYLE,
    "startup":     STARTUP_PITCH,
    "minimal":     MINIMAL,
}

DEFAULT_TEMPLATE_ID = "modern-saas"

# Ordered list for frontend enumeration
TEMPLATE_LIST = [
    {"id": "modern-saas", "name": "Modern SaaS",    "description": "Bold gradients, animated overlays, indigo palette"},
    {"id": "apple",       "name": "Apple Style",     "description": "Elegant, minimal motion, SF-style typography"},
    {"id": "startup",     "name": "Startup Pitch",   "description": "High energy, bold red, bouncy animations"},
    {"id": "minimal",     "name": "Minimal",         "description": "Light background, static camera, clean type"},
]


def get_template(template_id: str | None) -> BackendTemplateConfig:
    """Resolve a template by ID, falling back to the default."""
    return TEMPLATES.get(template_id or DEFAULT_TEMPLATE_ID, MODERN_SAAS)
