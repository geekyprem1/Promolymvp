"""
style_engine.py – Video Style System for Promoly.

A video STYLE is orthogonal to a TEMPLATE:
  • template  → look & feel (colors, typography, camera physics)   [templates.py]
  • style     → how each scene is rendered (screenshot vs motion graphics)

Three built-in styles:
  • website-showcase : every scene shows the real website (screenshots,
                       cursor, highlight rings, zoom). Feels like a product demo.
  • motion-graphics  : no screenshots — animated cards, counters, kinetic type.
                       Feels like a SaaS ad / Product Hunt launch video.
  • hybrid (default) : motion graphics for narrative scenes (hook/problem/
                       solution/benefits), real screenshots for proof scenes
                       (features/cta/hero). Premium and modern.

The engine resolves, per scene, a `componentType` (the Remotion renderer key)
and a coarse `role` ("screenshot" | "motion") used by the motion planner to
decide which overlays apply.

Adding a future style (Apple / Commercial / Documentary / Social) only requires
adding a VideoStyleConfig here and an entry in STYLE_LIST — no pipeline changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Coarse rendering roles
ROLE_SCREENSHOT = "screenshot"
ROLE_MOTION     = "motion"

# Remotion top-level renderer keys (must match PromoVideo.tsx dispatch)
RENDERER_SCREENSHOT = "ScreenshotScene"
RENDERER_MOTION     = "MotionGraphicsScene"

# Per-scene-type descriptive component name when in MOTION role.
# (For display / storyboard only — Remotion dispatches on the renderer key.)
MOTION_COMPONENT_NAME: dict[str, str] = {
    "hook":         "AnimatedHeadline",
    "problem":      "AnimatedList",
    "solution":     "SuccessAnimation",
    "features":     "FeatureCard",
    "benefits":     "MetricCounter",
    "testimonials": "QuoteCard",
    "cta":          "CTAAnimation",
    "hero":         "AnimatedHeadline",
    "content":      "FeatureCard",
}

# Motion intent per role (drives motion planner emphasis)
INTENT_SCREENSHOT = {
    "hook": "zoom", "problem": "zoom", "solution": "zoom",
    "features": "highlight", "benefits": "highlight",
    "testimonials": "highlight", "cta": "cursor",
    "hero": "zoom", "content": "highlight",
}


@dataclass
class VideoStyleConfig:
    id:          str
    name:        str
    description: str
    # scene_type → role ("screenshot" | "motion"). Missing keys use default_role.
    scene_roles: dict[str, str] = field(default_factory=dict)
    default_role: str = ROLE_MOTION

    def role_for(self, scene_type: str) -> str:
        return self.scene_roles.get(scene_type, self.default_role)

    def component_type_for(self, scene_type: str) -> str:
        role = self.role_for(scene_type)
        if role == ROLE_SCREENSHOT:
            return RENDERER_SCREENSHOT
        # Motion role: keep a descriptive name for the storyboard; the Remotion
        # dispatcher treats anything != ScreenshotScene as MotionGraphicsScene.
        return MOTION_COMPONENT_NAME.get(scene_type, RENDERER_MOTION)

    def motion_intent_for(self, scene_type: str) -> str:
        role = self.role_for(scene_type)
        if role == ROLE_SCREENSHOT:
            return INTENT_SCREENSHOT.get(scene_type, "zoom")
        return "animate"


# ── Style definitions ──────────────────────────────────────────────────────────

WEBSITE_SHOWCASE = VideoStyleConfig(
    id           = "website-showcase",
    name         = "Website Showcase",
    description  = "Real screenshots, cursor & zoom — like a live product demo",
    scene_roles  = {},                 # everything is a screenshot
    default_role = ROLE_SCREENSHOT,
)

MOTION_GRAPHICS = VideoStyleConfig(
    id           = "motion-graphics",
    name         = "Motion Graphics",
    description  = "Animated cards, counters & kinetic type — a modern SaaS ad",
    scene_roles  = {},                 # everything is motion graphics
    default_role = ROLE_MOTION,
)

HYBRID = VideoStyleConfig(
    id           = "hybrid",
    name         = "Hybrid",
    description  = "Motion-graphics story + real screenshots for proof. Premium.",
    scene_roles  = {
        "hook":         ROLE_MOTION,
        "problem":      ROLE_MOTION,
        "solution":     ROLE_MOTION,
        "benefits":     ROLE_MOTION,
        "testimonials": ROLE_MOTION,
        "features":     ROLE_SCREENSHOT,   # feature demonstration
        "cta":          ROLE_SCREENSHOT,   # CTA + cursor + highlight
        "hero":         ROLE_SCREENSHOT,   # establish the real product
        "content":      ROLE_SCREENSHOT,
    },
    default_role = ROLE_MOTION,
)


# ── Registry ──────────────────────────────────────────────────────────────────

STYLES: dict[str, VideoStyleConfig] = {
    "website-showcase": WEBSITE_SHOWCASE,
    "motion-graphics":  MOTION_GRAPHICS,
    "hybrid":           HYBRID,
}

DEFAULT_STYLE_ID = "hybrid"

STYLE_LIST = [
    {"id": "hybrid",           "name": "Hybrid",            "description": HYBRID.description},
    {"id": "website-showcase", "name": "Website Showcase",  "description": WEBSITE_SHOWCASE.description},
    {"id": "motion-graphics",  "name": "Motion Graphics",   "description": MOTION_GRAPHICS.description},
]


def get_style(style_id: str | None) -> VideoStyleConfig:
    """Resolve a style by ID, falling back to the default (hybrid)."""
    return STYLES.get(style_id or DEFAULT_STYLE_ID, HYBRID)


def apply_style(remotion_props: dict, style_id: str | None) -> dict:
    """
    Inject style-resolved fields into every scene.

    Adds to each scene:
        videoStyle     — the resolved style id
        componentType  — Remotion renderer key (ScreenshotScene / motion name)
        componentRole  — coarse role: "screenshot" | "motion"
        motionIntent   — refined intent (kept from visual_mapper if already set
                         for a screenshot scene, else style default)

    Returns a new dict (does not mutate input).
    """
    style  = get_style(style_id)
    scenes = remotion_props.get("scenes", [])
    styled: list[dict] = []

    counts = {ROLE_SCREENSHOT: 0, ROLE_MOTION: 0}

    for scene in scenes:
        scene_type = scene.get("type", "hero")
        role       = style.role_for(scene_type)
        counts[role] = counts.get(role, 0) + 1

        # Preserve a visual_mapper-supplied motionIntent for screenshot scenes,
        # otherwise use the style's default intent.
        existing_intent = scene.get("motionIntent")
        if role == ROLE_SCREENSHOT and existing_intent and existing_intent != "zoom":
            motion_intent = existing_intent
        else:
            motion_intent = style.motion_intent_for(scene_type)

        styled.append({
            **scene,
            "videoStyle":    style.id,
            "componentType": style.component_type_for(scene_type),
            "componentRole": role,
            "motionIntent":  motion_intent,
        })

    print(
        f"[Style] {style.id}: {counts[ROLE_SCREENSHOT]} screenshot, "
        f"{counts[ROLE_MOTION]} motion scenes",
        flush=True,
    )

    return {**remotion_props, "scenes": styled, "videoStyle": style.id}
