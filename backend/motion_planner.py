"""
motion_planner.py – Motion Planner layer between AI storyboard and Remotion renderer.

Takes remotion_props (scenes[]) produced by build_remotion_props() and injects
a motionPlan object into each scene describing:
  - camera  : zoom/pan/focus for the background image
  - cursor  : optional animated cursor with waypoints and click events
  - highlights : HighlightRing targets overlaid on the scene
  - badges  : FloatingBadge placements
  - transitions: refined in/out transition per scene position

All coordinates are in 1920×1080 space.
Template overrides camera ranges, transition choices, and motion graphics.
"""
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detector import SectionData
    from templates import BackendTemplateConfig

# ── Canvas constants ──────────────────────────────────────────────────────────

W, H = 1920, 1080
CX, CY = W // 2, H // 2   # canvas centre

# Accent colour palette (matches Remotion theme)
ACCENT   = "#6366f1"
VIOLET   = "#8b5cf6"
GREEN    = "#22c55e"
ORANGE   = "#f97316"
CYAN     = "#06b6d4"

SCENE_COLORS = {
    "hero":         ACCENT,
    "features":     VIOLET,
    "benefits":     GREEN,
    "testimonials": CYAN,
    "pricing":      ORANGE,
    "cta":          GREEN,
    "content":      ACCENT,
}


# ── Camera planning ───────────────────────────────────────────────────────────

def _plan_camera(
    scene_type: str,
    duration: int,
    scene_index: int,
    total: int,
    template: "BackendTemplateConfig | None" = None,
) -> dict:
    """
    Returns a camera motion dict.  zoomFrom/zoomTo are CSS scale values applied
    to the background image wrapper.  pan values are pixel offsets.
    focusX/Y (0-1) set the transform-origin anchor.

    If a template is provided, use its camera config. Otherwise fall back to
    the built-in heuristics.
    """
    if template is not None:
        cam = template.camera_for_scene(scene_type)
        # For features/benefits, alternate pan direction by scene index
        if scene_type in ("features", "benefits", "content"):
            direction = 1 if scene_index % 2 == 0 else -1
            cam = {**cam, "panX": cam["panX"] * direction}
        return cam

    # ── Built-in heuristics (no template) ────────────────────────────────────
    base = {"zoomFrom": 1.0, "zoomTo": 1.0, "panX": 0, "panY": 0, "focusX": 0.5, "focusY": 0.5}

    if scene_type == "hero":
        return {**base, "zoomFrom": 1.08, "zoomTo": 1.02, "panX": -20, "focusX": 0.45, "focusY": 0.4}
    if scene_type == "features":
        direction = 1 if scene_index % 2 == 0 else -1
        return {**base, "zoomFrom": 1.0, "zoomTo": 1.04, "panX": direction * 18}
    if scene_type == "benefits":
        return {**base, "zoomFrom": 1.03, "zoomTo": 1.0, "panX": 15, "panY": -8, "focusX": 0.6}
    if scene_type == "testimonials":
        return {**base, "zoomFrom": 1.02, "zoomTo": 1.0, "panY": -12, "focusY": 0.55}
    if scene_type == "cta":
        return {**base, "zoomFrom": 0.97, "zoomTo": 1.04, "focusY": 0.65}
    return base


# ── Cursor planning ───────────────────────────────────────────────────────────

def _plan_cursor(
    scene_type: str,
    duration: int,
    scene: dict,
    scene_index: int,
    template: "BackendTemplateConfig | None" = None,
) -> dict:
    """
    Returns cursor motion.  waypoints use absolute 1920×1080 coords.
    frame values are relative to the start of the scene (not global).
    """
    disabled = {"enabled": False, "waypoints": [], "clickAtFrame": None, "showTrail": False, "color": "#ffffff"}

    # Template gate: if template disables cursor entirely, always return disabled
    if template is not None and not template.motion_graphics.show_cursor:
        return disabled

    if scene_type == "hero":
        return disabled

    if scene_type == "cta":
        # Move from lower-left to CTA button, click it
        button_x, button_y = CX, H * 0.68
        return {
            "enabled": True,
            "showTrail": True,
            "color": "#ffffff",
            "clickAtFrame": int(duration * 0.55),
            "waypoints": [
                {"x": CX - 280, "y": H * 0.82, "frame": 5},
                {"x": CX - 100, "y": H * 0.72, "frame": 20},
                {"x": button_x, "y": button_y, "frame": 40},
                {"x": button_x, "y": button_y, "frame": duration - 10},
            ],
        }

    if scene_type == "features":
        # Cursor sweeps across feature area
        reverse = bool(scene.get("reverse", False))
        start_x = W * 0.72 if not reverse else W * 0.28
        end_x   = W * 0.82 if not reverse else W * 0.18
        return {
            "enabled": True,
            "showTrail": True,
            "color": "#ffffff",
            "clickAtFrame": None,
            "waypoints": [
                {"x": start_x, "y": H * 0.38, "frame": 15},
                {"x": start_x, "y": H * 0.52, "frame": 35},
                {"x": end_x,   "y": H * 0.58, "frame": 60},
                {"x": end_x,   "y": H * 0.58, "frame": duration - 10},
            ],
        }

    if scene_type == "benefits":
        return {
            "enabled": True,
            "showTrail": False,
            "color": ACCENT,
            "clickAtFrame": None,
            "waypoints": [
                {"x": W * 0.5, "y": H * 0.55, "frame": 10},
                {"x": W * 0.6, "y": H * 0.45, "frame": 45},
                {"x": W * 0.55, "y": H * 0.45, "frame": duration - 10},
            ],
        }

    return disabled


# ── Highlight planning ────────────────────────────────────────────────────────

def _plan_highlights(
    scene_type: str,
    duration: int,
    scene: dict,
    template: "BackendTemplateConfig | None" = None,
) -> list[dict]:
    """
    Returns list of HighlightRing targets.
    Each item: {x, y, radius, startFrame, exitFrame, color}
    """
    # Template gate
    if template is not None and not template.motion_graphics.show_highlights:
        return []
    if template is not None and scene_type not in template.motion_graphics.highlight_on_scenes:
        return []

    exit_frame = duration - 15

    if scene_type == "cta":
        return [{
            "x": CX,
            "y": int(H * 0.68),
            "radius": 80,
            "startFrame": 8,
            "exitFrame": exit_frame,
            "color": GREEN,
        }]

    if scene_type == "features":
        reverse = bool(scene.get("reverse", False))
        img_cx = int(W * 0.72) if not reverse else int(W * 0.28)
        return [{
            "x": img_cx,
            "y": int(H * 0.5),
            "radius": 90,
            "startFrame": 25,
            "exitFrame": exit_frame,
            "color": VIOLET,
        }]

    if scene_type == "testimonials":
        return [{
            "x": CX,
            "y": int(H * 0.45),
            "radius": 200,
            "startFrame": 20,
            "exitFrame": exit_frame,
            "color": CYAN,
        }]

    if scene_type == "hero":
        return [{
            "x": int(W * 0.3),
            "y": int(H * 0.3),
            "radius": 120,
            "startFrame": 40,
            "exitFrame": exit_frame,
            "color": ACCENT,
        }]

    return []


# ── Badge planning ────────────────────────────────────────────────────────────

_NUMBER_RE = re.compile(r"\d[\d,\.%x]+")

def _has_numbers(text: str) -> bool:
    return bool(_NUMBER_RE.search(text or ""))

def _plan_badges(
    scene_type: str,
    duration: int,
    scene: dict,
    template: "BackendTemplateConfig | None" = None,
) -> list[dict]:
    """
    Returns list of FloatingBadge placements.
    Each item: {text, icon, x, y, startFrame, exitFrame, color}
    """
    # Template gate
    if template is not None and not template.motion_graphics.show_badges:
        return []

    exit_frame = duration - 15
    badges: list[dict] = []

    if scene_type == "cta":
        badges.append({
            "text": "FREE",
            "icon": "✦",
            "x": int(CX + 230),
            "y": int(H * 0.63),
            "startFrame": 30,
            "exitFrame": exit_frame,
            "color": GREEN,
        })

    elif scene_type == "hero":
        badges.append({
            "text": scene.get("badge", "NEW"),
            "icon": None,
            "x": int(W * 0.5),
            "y": int(H * 0.18),
            "startFrame": 5,
            "exitFrame": exit_frame,
            "color": ACCENT,
        })

    elif scene_type == "features":
        # If any bullet contains a number/metric, surface it as a badge
        bullets = scene.get("bullets", [])
        for b in bullets:
            m = _NUMBER_RE.search(b or "")
            if m:
                badges.append({
                    "text": m.group(),
                    "icon": None,
                    "x": int(W * 0.78),
                    "y": int(H * 0.22),
                    "startFrame": 20,
                    "exitFrame": exit_frame,
                    "color": ORANGE,
                })
                break  # one metric badge per scene

    elif scene_type == "testimonials":
        badges.append({
            "text": "VERIFIED",
            "icon": "✓",
            "x": int(CX + 300),
            "y": int(H * 0.68),
            "startFrame": 35,
            "exitFrame": exit_frame,
            "color": CYAN,
        })

    return badges


# ── Transition planning ───────────────────────────────────────────────────────

VALID_TRANSITIONS = {"fade", "slideLeft", "slideRight", "zoomIn", "dissolve"}

# ── Motion component assignment ────────────────────────────────────────────────

def _assign_motion_component(
    scene_type: str,
    scene: dict,
    template: "BackendTemplateConfig | None" = None,
) -> str:
    """
    Decide which Motion Graphics Library component the scene should render.
    Returned value matches MotionComponent type in types.ts.

    hook        → textReveal   (big stat + TextReveal headline)
    problem     → zoomHighlight (zoom + HighlightRing overlay)
    solution    → successPulse  (SuccessAnimation on checkpoint completion)
    features    → metricCounter if any bullet contains a number, else cursorClick
    benefits    → metricCounter  (outcome metric display)
    testimonials→ none          (card + quote are enough)
    cta         → ctaAnimation  (CTAButtonAnimation)
    default     → none
    """
    if scene_type == "hook":
        return "textReveal"
    if scene_type == "problem":
        return "zoomHighlight"
    if scene_type == "solution":
        return "successPulse"
    if scene_type == "cta":
        return "ctaAnimation"
    if scene_type in ("features", "benefits"):
        # Use MetricCounter if any bullet / bodyText has numbers
        bullets = [str(b) for b in (scene.get("bullets") or [])]
        body = scene.get("bodyText") or ""
        text_to_check = " ".join(bullets) + str(body)
        if _NUMBER_RE.search(text_to_check):
            return "metricCounter"
        return "cursorClick"
    return "none"

def _plan_transitions(
    scene_type: str,
    scene_index: int,
    total: int,
    scene: dict,
    template: "BackendTemplateConfig | None" = None,
) -> dict:
    """Refine/override transitions based on position, type, and template."""
    # Template-driven transition lookup
    if template is not None:
        current_in = template.transition_for(scene_type)
    else:
        current_in = scene.get("transition", "fade")

    if current_in not in VALID_TRANSITIONS:
        current_in = "fade"

    # Position rules (always enforced, even over template)
    if scene_index == 0:
        current_in = "fade"
    elif scene_index == total - 1:
        # Last scene: use template's cta transition, or zoomIn
        if template is not None:
            current_in = template.transition_for("cta")
        else:
            current_in = "zoomIn"

    # Out transition: always fade so next scene enters cleanly
    out = "fade"

    easing_map = {
        "fade":       "easeOutCubic",
        "slideLeft":  "easeOutBack",
        "slideRight": "easeOutBack",
        "zoomIn":     "easeOutCubic",
        "dissolve":   "easeInOutCubic",
    }

    return {
        "in":     current_in,
        "out":    out,
        "easing": easing_map.get(current_in, "easeOutCubic"),
    }


# ── Public entry point ────────────────────────────────────────────────────────

def plan_motion(
    remotion_props: dict,
    sections: list | None = None,
    meta: dict | None = None,
    template: "BackendTemplateConfig | None" = None,
) -> dict:
    """
    Inject a motionPlan object into every scene in remotion_props.

    Returns a new dict (does not mutate the input) with the same shape as
    PromoVideoProps but each scene gains:
        scene.motionPlan = { sceneId, camera, cursor, highlights, badges, transitions }
    """
    scenes = remotion_props.get("scenes", [])
    total = len(scenes)
    planned: list[dict] = []

    for i, scene in enumerate(scenes):
        scene_type = scene.get("type", "hero")
        duration   = scene.get("durationInFrames", 150)

        motion_plan = {
            "sceneId":         f"scene_{i}",
            "camera":          _plan_camera(scene_type, duration, i, total, template),
            "cursor":          _plan_cursor(scene_type, duration, scene, i, template),
            "highlights":      _plan_highlights(scene_type, duration, scene, template),
            "badges":          _plan_badges(scene_type, duration, scene, template),
            "transitions":     _plan_transitions(scene_type, i, total, scene, template),
            "motionComponent": _assign_motion_component(scene_type, scene, template),
        }

        # Override scene.transition with the planned in-transition so
        # the existing Remotion transition logic picks it up
        planned_scene = {
            **scene,
            "transition": motion_plan["transitions"]["in"],
            "motionPlan": motion_plan,
        }
        planned.append(planned_scene)

    result = {**remotion_props, "scenes": planned}
    if template is not None:
        result["templateId"] = template.id
        result["templateSpring"] = {
            "stiffness": template.spring.stiffness,
            "damping":   template.spring.damping,
            "mass":      template.spring.mass,
        }
    return result
