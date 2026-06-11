"""
scene_designer.py – Scene Designer Layer for Promoly.

Sits between apply_style() and plan_motion() in the pipeline.

Input  : remotion_props (scenes with componentType/componentRole already set)
Output : same shape, each scene gains a `sceneDesign` dict describing:
            concept            – detected primary concept ("growth", "security", …)
            visualMetaphor     – specific visual treatment ("rocket", "shield", …)
            primaryComponent   – hero Remotion component name
            secondaryComponents – supporting components list
            background         – background component name
            motionEnergy       – "low" | "medium" | "high" | "explosive"
            density            – "minimal" | "standard" | "dense"
            accentVariant      – "default" | "success" | "warning" | "danger"
            badgeTexts         – suggested badge chip labels
            motionIntensity    – 0.0-1.0 float for Remotion metaphor component

The design drives:
  • motion_planner.py  – motionComponent selection + zoom/badge intensity
  • MotionGraphicsScene.tsx – layout variant + MetaphorRenderer
"""
from __future__ import annotations

import re

from visual_metaphors import (
    CONCEPT_KEYWORDS,
    CONCEPT_METAPHORS,
    SCENE_TYPE_CONCEPT,
    resolve_metaphor,
)

# ── Scene-level energy overrides ──────────────────────────────────────────────
SCENE_TYPE_ENERGY_OVERRIDE: dict[str, str] = {
    "hook":         "explosive",
    "cta":          "high",
    "testimonials": "low",
    "problem":      "medium",
}

# ── Badge text suggestions per concept ────────────────────────────────────────
CONCEPT_BADGES: dict[str, list[str]] = {
    "speed":        ["Instant", "10× Faster", "Real-Time"],
    "growth":       ["Scale Up", "Growing Fast", "Top Rated"],
    "security":     ["Trusted", "SOC 2", "Secure"],
    "automation":   ["Automated", "Zero Manual Work", "AI-Powered"],
    "ai":           ["AI-Powered", "Intelligent", "Next-Gen"],
    "savings":      ["Save 40%", "Free Trial", "ROI Proven"],
    "simplicity":   ["Easy Setup", "No Code", "5 Min Setup"],
    "social_proof": ["Verified", "5-Star", "10K+ Users"],
    "performance":  ["99.9% Uptime", "Enterprise Grade", "Reliable"],
    "collaboration":["Team Ready", "Collaborate", "Share Instantly"],
    "analytics":    ["Data-Driven", "Live Insights", "Real-Time"],
    "scale":        ["Global", "Millions Served", "Enterprise"],
    "trust":        ["Trusted", "Certified", "Verified"],
}

# ── Scorer ────────────────────────────────────────────────────────────────────

_NONWORD = re.compile(r"[^a-z0-9 ]+")


def _score_concepts(text: str) -> dict[str, float]:
    """
    Score each concept by keyword hits in text.
    Returns {concept: score} (higher = better match).
    """
    clean = _NONWORD.sub(" ", text.lower())
    scores: dict[str, float] = {}
    for concept, keywords in CONCEPT_KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            if kw in clean:
                # Longer keyword phrases score more
                score += 1.0 + len(kw.split()) * 0.3
        scores[concept] = score
    return scores


def _detect_concept(scene: dict) -> str:
    """
    Detect the primary concept from scene content.
    Falls back to scene-type prior when no keyword hits.
    """
    parts = [
        scene.get("headline", ""),
        scene.get("subheadline", ""),
        scene.get("narration", ""),
        scene.get("badge", ""),
        " ".join(str(b) for b in (scene.get("bullets") or [])),
        scene.get("bodyText", "") or "",
        " ".join(str(b) for b in (scene.get("checkpoints") or [])),
        " ".join(str(b) for b in (scene.get("painPoints") or [])),
        scene.get("quote", "") or "",
    ]
    combined = " ".join(str(p) for p in parts if p)
    scores = _score_concepts(combined)

    best_concept = max(scores, key=lambda k: scores[k]) if scores else None
    if best_concept and scores[best_concept] > 0.5:
        return best_concept

    # Fall back to scene-type prior
    return SCENE_TYPE_CONCEPT.get(scene.get("type", "hero"), "growth")


def _pick_metaphor(concept: str, scene_type: str) -> str:
    """
    Pick the best visual metaphor for this concept + scene type combination.
    Social-proof scene types always prefer quote-card regardless of concept.
    """
    if scene_type == "testimonials":
        return "quote-card"
    if scene_type == "cta":
        return "metric-counter"   # urgency / value counter
    candidates = CONCEPT_METAPHORS.get(concept, ["growth-chart"])
    return candidates[0]


def _suggest_badges(concept: str, scene: dict) -> list[str]:
    """
    Pick 2-3 badge chip labels from concept suggestions, plus the scene's own badge.
    """
    suggestions = CONCEPT_BADGES.get(concept, ["Featured", "Proven"])[:2]
    own_badge = scene.get("badge", "")
    if own_badge and own_badge not in suggestions:
        suggestions = [own_badge] + suggestions
    return suggestions[:3]


# ── Public API ────────────────────────────────────────────────────────────────

def design_scene(scene: dict) -> dict:
    """
    Produce a SceneDesign dict for a single scene.
    Pure function — does not mutate the input scene.
    """
    scene_type = scene.get("type", "hero")

    concept = _detect_concept(scene)
    spec    = resolve_metaphor(concept, scene_type)

    # Apply scene-type energy override
    energy = SCENE_TYPE_ENERGY_OVERRIDE.get(scene_type, spec.energy)

    return {
        "concept":             concept,
        "visualMetaphor":      spec.id,
        "metaphorComponent":   spec.component,   # Remotion SVG animation component
        "primaryComponent":    spec.primary_component,
        "secondaryComponents": spec.secondary_components,
        "background":          spec.background,
        "motionEnergy":        energy,
        "density":             spec.density,
        "accentVariant":       spec.accent,
        "badgeTexts":          _suggest_badges(concept, scene),
        "motionIntensity":     spec.motion_intensity,
    }


def design_scenes(remotion_props: dict) -> dict:
    """
    Inject a `sceneDesign` dict into every scene in remotion_props.

    Called AFTER apply_style(), BEFORE plan_motion().
    Does not mutate the input dict.
    """
    scenes  = remotion_props.get("scenes", [])
    designed: list[dict] = []

    for scene in scenes:
        sd = design_scene(scene)
        designed.append({**scene, "sceneDesign": sd})
        print(
            f"[SceneDesigner] scene={scene.get('type','?'):12s} "
            f"concept={sd['concept']:14s} "
            f"metaphor={sd['visualMetaphor']:18s} "
            f"energy={sd['motionEnergy']}",
            flush=True,
        )

    return {**remotion_props, "scenes": designed}
