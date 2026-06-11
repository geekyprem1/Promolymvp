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

# Reusable disabled-cursor object (motion-graphics scenes have no cursor)
_DISABLED_CURSOR = {
    "enabled": False, "waypoints": [], "clickAtFrame": None,
    "showTrail": False, "color": "#ffffff",
}

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
    scene: dict | None = None,
) -> dict:
    """
    Returns a camera motion dict.  zoomFrom/zoomTo are CSS scale values applied
    to the background image wrapper.  pan values are pixel offsets.
    focusX/Y (0-1) set the transform-origin anchor.

    Priority:
      1. Visual mapper coordinates (scene.focusX / scene.focusY) — actual element position
      2. Template camera config
      3. Built-in heuristics
    """
    # Visual mapper override: use real element coordinates when available
    mapped_fx = scene.get("focusX") if scene else None
    mapped_fy = scene.get("focusY") if scene else None
    has_visual_target = scene.get("visualTargetId") if scene else None

    if template is not None:
        cam = template.camera_for_scene(scene_type)
        if scene_type in ("features", "benefits", "content"):
            direction = 1 if scene_index % 2 == 0 else -1
            cam = {**cam, "panX": cam["panX"] * direction}
        # Inject real focusX/Y from visual mapper if we have a match
        if has_visual_target and mapped_fx is not None:
            cam = {**cam, "focusX": mapped_fx, "focusY": mapped_fy}
        return cam

    # ── Built-in heuristics ───────────────────────────────────────────────────
    base = {"zoomFrom": 1.0, "zoomTo": 1.0, "panX": 0, "panY": 0, "focusX": 0.5, "focusY": 0.5}

    if scene_type == "hero":
        cam = {**base, "zoomFrom": 1.08, "zoomTo": 1.02, "panX": -20, "focusX": 0.45, "focusY": 0.4}
    elif scene_type == "features":
        direction = 1 if scene_index % 2 == 0 else -1
        cam = {**base, "zoomFrom": 1.0, "zoomTo": 1.04, "panX": direction * 18}
    elif scene_type == "benefits":
        cam = {**base, "zoomFrom": 1.03, "zoomTo": 1.0, "panX": 15, "panY": -8, "focusX": 0.6}
    elif scene_type == "testimonials":
        cam = {**base, "zoomFrom": 1.02, "zoomTo": 1.0, "panY": -12, "focusY": 0.55}
    elif scene_type == "cta":
        cam = {**base, "zoomFrom": 0.97, "zoomTo": 1.04, "focusY": 0.65}
    else:
        cam = base

    # Inject real focusX/Y from visual mapper if available
    if has_visual_target and mapped_fx is not None:
        cam = {**cam, "focusX": mapped_fx, "focusY": mapped_fy}

    # Scale zoom range with sceneDesign.motionEnergy
    if scene:
        energy = (scene.get("sceneDesign") or {}).get("motionEnergy", "medium")
        energy_zoom = {"low": 0.98, "medium": 1.0, "high": 1.02, "explosive": 1.04}
        boost = energy_zoom.get(energy, 1.0)
        if boost != 1.0:
            cam = {
                **cam,
                "zoomFrom": round(cam["zoomFrom"] * boost, 3),
                "zoomTo":   round(cam["zoomTo"]   * boost, 3),
            }

    return cam


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
        # Use real button position from visual mapper if available
        bbox = scene.get("highlightBox") if scene else None
        if bbox:
            button_x = bbox["x"] + bbox["width"] // 2
            button_y = bbox["y"] + bbox["height"] // 2
        else:
            button_x, button_y = CX, int(H * 0.68)
        return {
            "enabled": True,
            "showTrail": True,
            "color": "#ffffff",
            "clickAtFrame": int(duration * 0.55),
            "waypoints": [
                {"x": button_x - 280, "y": button_y + 120, "frame": 5},
                {"x": button_x - 100, "y": button_y + 40,  "frame": 20},
                {"x": button_x,       "y": button_y,        "frame": 40},
                {"x": button_x,       "y": button_y,        "frame": duration - 10},
            ],
        }

    if scene_type == "features":
        # Use real card/widget position from visual mapper if available
        bbox = scene.get("highlightBox") if scene else None
        if bbox:
            cx = bbox["x"] + bbox["width"] // 2
            cy = bbox["y"] + bbox["height"] // 2
            start_x, end_x = cx - 60, cx + 60
            start_y = cy
        else:
            reverse = bool(scene.get("reverse", False))
            start_x = int(W * 0.72) if not reverse else int(W * 0.28)
            end_x   = int(W * 0.82) if not reverse else int(W * 0.18)
            start_y = int(H * 0.45)
        return {
            "enabled": True,
            "showTrail": True,
            "color": "#ffffff",
            "clickAtFrame": None,
            "waypoints": [
                {"x": start_x, "y": start_y - 60, "frame": 15},
                {"x": start_x, "y": start_y,       "frame": 35},
                {"x": end_x,   "y": start_y + 30,  "frame": 60},
                {"x": end_x,   "y": start_y + 30,  "frame": duration - 10},
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

    # Use real element bounding box from visual mapper when available
    bbox = scene.get("highlightBox") if scene else None

    def _from_bbox(color: str, start: int, radius_pad: int = 20) -> dict:
        """Build a highlight ring centred on the mapped element."""
        cx = bbox["x"] + bbox["width"] // 2
        cy = bbox["y"] + bbox["height"] // 2
        radius = max(40, (max(bbox["width"], bbox["height"]) // 2) + radius_pad)
        return {"x": cx, "y": cy, "radius": radius,
                "startFrame": start, "exitFrame": exit_frame, "color": color}

    if scene_type == "cta":
        if bbox:
            return [_from_bbox(GREEN, 8, 24)]
        return [{"x": CX, "y": int(H * 0.68), "radius": 80,
                 "startFrame": 8, "exitFrame": exit_frame, "color": GREEN}]

    if scene_type == "features":
        if bbox:
            return [_from_bbox(VIOLET, 25, 20)]
        reverse = bool(scene.get("reverse", False))
        img_cx = int(W * 0.72) if not reverse else int(W * 0.28)
        return [{"x": img_cx, "y": int(H * 0.5), "radius": 90,
                 "startFrame": 25, "exitFrame": exit_frame, "color": VIOLET}]

    if scene_type == "testimonials":
        if bbox:
            return [_from_bbox(CYAN, 20, 30)]
        return [{"x": CX, "y": int(H * 0.45), "radius": 200,
                 "startFrame": 20, "exitFrame": exit_frame, "color": CYAN}]

    if scene_type == "hero":
        if bbox:
            return [_from_bbox(ACCENT, 40, 30)]
        return [{"x": int(W * 0.3), "y": int(H * 0.3), "radius": 120,
                 "startFrame": 40, "exitFrame": exit_frame, "color": ACCENT}]

    if scene_type in ("widget", "solution", "benefits") and bbox:
        return [_from_bbox(ACCENT, 20, 20)]

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

    # Prefer badge texts from Scene Designer when available
    sd = scene.get("sceneDesign")
    sd_badges = sd.get("badgeTexts", []) if sd else []
    accent_variant = sd.get("accentVariant", "default") if sd else "default"
    badge_color = GREEN if accent_variant == "success" else ACCENT

    if scene_type == "cta":
        label = sd_badges[0] if sd_badges else "FREE"
        badges.append({
            "text": label,
            "icon": "✦",
            "x": int(CX + 230),
            "y": int(H * 0.63),
            "startFrame": 30,
            "exitFrame": exit_frame,
            "color": GREEN,
        })

    elif scene_type == "hero":
        label = sd_badges[0] if sd_badges else scene.get("badge", "NEW")
        badges.append({
            "text": label,
            "icon": None,
            "x": int(W * 0.5),
            "y": int(H * 0.18),
            "startFrame": 5,
            "exitFrame": exit_frame,
            "color": badge_color,
        })

    elif scene_type == "features":
        # Use Scene Designer badge first; fall back to first metric in bullets
        if sd_badges:
            badges.append({
                "text": sd_badges[0],
                "icon": None,
                "x": int(W * 0.78),
                "y": int(H * 0.22),
                "startFrame": 20,
                "exitFrame": exit_frame,
                "color": badge_color,
            })
        else:
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
                    break

    elif scene_type == "benefits":
        label = sd_badges[0] if sd_badges else "PROVEN"
        badges.append({
            "text": label,
            "icon": "✦",
            "x": int(W * 0.78),
            "y": int(H * 0.20),
            "startFrame": 18,
            "exitFrame": exit_frame,
            "color": badge_color,
        })

    elif scene_type == "testimonials":
        label = sd_badges[0] if sd_badges else "VERIFIED"
        badges.append({
            "text": label,
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

    Priority:
      1. sceneDesign.primaryComponent (set by Scene Designer from content meaning)
      2. Scene-type heuristics (fallback)
    """
    # Scene Designer override — maps component names to MotionComponent enum values
    _COMPONENT_MAP = {
        "MetricCounter":   "metricCounter",
        "ProgressBar":     "metricCounter",   # progress bars use same slot
        "FeatureCard":     "cursorClick",
        "QuoteCard":       "none",
        "KineticHeadline": "textReveal",
        "FloatingBadge":   "none",
    }
    sd = scene.get("sceneDesign")
    if sd:
        mapped = _COMPONENT_MAP.get(sd.get("primaryComponent", ""), None)
        if mapped is not None:
            # Respect per-scene-type overrides that must not be changed
            if scene_type == "hook":
                return "textReveal"
            if scene_type == "problem":
                return "zoomHighlight"
            if scene_type == "solution":
                return "successPulse"
            if scene_type == "cta":
                return "ctaAnimation"
            return mapped

    # Fallback heuristics
    if scene_type == "hook":
        return "textReveal"
    if scene_type == "problem":
        return "zoomHighlight"
    if scene_type == "solution":
        return "successPulse"
    if scene_type == "cta":
        return "ctaAnimation"
    if scene_type in ("features", "benefits"):
        bullets = [str(b) for b in (scene.get("bullets") or [])]
        body = scene.get("bodyText") or ""
        if _NUMBER_RE.search(" ".join(bullets) + str(body)):
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

        # Video-style role: cursor + highlight rings only make sense over a real
        # screenshot. Motion-graphics scenes keep camera + motionComponent but
        # drop the website-overlay elements. Default to "screenshot" when the
        # style engine hasn't run (backward compatibility).
        role = scene.get("componentRole", "screenshot")
        is_screenshot = role == "screenshot"

        motion_plan = {
            "sceneId":         f"scene_{i}",
            "camera":          _plan_camera(scene_type, duration, i, total, template, scene),
            "cursor":          _plan_cursor(scene_type, duration, scene, i, template) if is_screenshot else _DISABLED_CURSOR.copy(),
            "highlights":      _plan_highlights(scene_type, duration, scene, template) if is_screenshot else [],
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
