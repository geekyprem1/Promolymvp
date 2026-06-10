"""
visual_mapper.py – Visual Mapping Layer for Promoly.

Matches AI-generated story scenes to real UI elements captured by detector.py.

Each scene gets:
  visualTarget  — id of the best-matching VisualElement
  focusX/Y      — normalized camera focus point (0-1) derived from element center
  highlightBox  — {x, y, width, height} for HighlightRing overlay
  motionIntent  — "zoom" | "highlight" | "cursor" | "none"

Fallback: if no element matches above threshold, uses the section screenshot
with the existing default camera position.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detector import SectionData, VisualElement

# ── Scoring constants ──────────────────────────────────────────────────────────

MATCH_THRESHOLD   = 0.15   # minimum relevance score to use element vs section fallback
EXACT_MATCH_BONUS = 0.6    # score added when element text is substring of scene text
WORD_MATCH_SCORE  = 0.12   # score per matching word
TYPE_MATCH_BONUS  = 0.25   # score when element type aligns with scene type

# ── Scene type → preferred element types ──────────────────────────────────────

SCENE_TYPE_PREFERS: dict[str, list[str]] = {
    "hero":         ["hero", "button"],
    "hook":         ["hero", "widget"],
    "cta":          ["button"],
    "features":     ["card", "widget"],
    "benefits":     ["card", "widget"],
    "solution":     ["widget", "card"],
    "problem":      ["hero", "card"],
    "pricing":      ["pricing"],
    "testimonials": ["testimonial"],
    "content":      ["card", "widget"],
}

# ── Motion intent rules ───────────────────────────────────────────────────────

def _motion_intent(scene_type: str, element_type: str) -> str:
    if scene_type == "cta" and element_type == "button":
        return "cursor"       # cursor moves to and clicks the button
    if element_type in ("widget", "card"):
        return "highlight"    # HighlightRing around the element
    if scene_type in ("hero", "hook"):
        return "zoom"         # camera zooms in on hero element
    if element_type == "button":
        return "cursor"
    if element_type == "testimonial":
        return "highlight"
    return "zoom"


# ── Text tokenizer ────────────────────────────────────────────────────────────

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "be", "it", "this",
    "that", "your", "our", "we", "you", "i", "my", "their", "its",
}

def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


# ── Relevance scoring ─────────────────────────────────────────────────────────

def _score(
    scene: dict,
    element: "VisualElement",
) -> float:
    """
    Compute relevance score between a scene and a visual element.
    Higher = better match.
    """
    score = 0.0
    scene_type = scene.get("type", "")

    # Scene text: combine all text fields
    scene_text = " ".join(filter(None, [
        scene.get("headline", ""),
        scene.get("subheadline", ""),
        scene.get("narration", ""),
        scene.get("badge", ""),
        " ".join(scene.get("bullets", []) or []),
        " ".join(scene.get("painPoints", []) or []),
        " ".join(scene.get("checkpoints", []) or []),
    ])).lower()

    el_text = (element.text or "").lower()

    if not el_text:
        return 0.0

    # Exact substring match (element text appears in scene text)
    if el_text and el_text in scene_text:
        score += EXACT_MATCH_BONUS

    # Reverse: scene words in element
    scene_tokens = _tokens(scene_text)
    el_tokens    = _tokens(el_text)
    if scene_tokens and el_tokens:
        overlap = scene_tokens & el_tokens
        score  += len(overlap) * WORD_MATCH_SCORE

    # Type alignment bonus
    preferred = SCENE_TYPE_PREFERS.get(scene_type, [])
    if element.element_type in preferred:
        score += TYPE_MATCH_BONUS
        # Extra bonus for first preferred type (strongest signal)
        if preferred and element.element_type == preferred[0]:
            score += 0.1

    # Section match bonus: element lives in the same section as the scene
    scene_section = scene.get("section", scene_type)
    if element.section_type == scene_section:
        score += 0.1

    return round(score, 4)


# ── Public API ────────────────────────────────────────────────────────────────

def map_visuals(
    scenes: list[dict],
    visual_elements: list["VisualElement"],
) -> list[dict]:
    """
    For each scene, find the best-matching VisualElement and inject
    visual targeting data.

    Returns the same scenes list with these keys added to each scene:
        visualTargetId  — str | None
        focusX          — float (0-1, camera focus X, replaces hardcoded)
        focusY          — float (0-1, camera focus Y)
        highlightBox    — {x, y, width, height} | None
        motionIntent    — "zoom" | "highlight" | "cursor" | "none"
        elementScreenshotUrl — str | None  (URL of element crop, if available)
    """
    if not visual_elements:
        # No elements captured — return scenes unchanged with None targets
        for scene in scenes:
            scene.setdefault("visualTargetId", None)
            scene.setdefault("focusX", 0.5)
            scene.setdefault("focusY", 0.5)
            scene.setdefault("highlightBox", None)
            scene.setdefault("motionIntent", "zoom")
            scene.setdefault("elementScreenshotUrl", None)
        return scenes

    updated = []
    for scene in scenes:
        # Score all elements for this scene
        scored = [
            (el, _score(scene, el))
            for el in visual_elements
        ]
        scored.sort(key=lambda t: t[1], reverse=True)

        best_el, best_score = scored[0] if scored else (None, 0.0)

        if best_el and best_score >= MATCH_THRESHOLD:
            bbox  = best_el.bounding_box
            scene = {
                **scene,
                "visualTargetId":       best_el.id,
                "focusX":               bbox["focusX"],
                "focusY":               bbox["focusY"],
                "highlightBox": {
                    "x":      bbox["x"],
                    "y":      bbox["y"],
                    "width":  bbox["width"],
                    "height": bbox["height"],
                },
                "motionIntent": _motion_intent(scene.get("type", ""), best_el.element_type),
                "elementScreenshotUrl": None,  # filled by main.py when serving
                "_visualScore": best_score,    # debug only
            }
            print(
                f"[VisualMapper] scene={scene.get('type')} → "
                f"{best_el.id} ({best_el.element_type}) "
                f"text='{best_el.text[:40]}' score={best_score:.2f}",
                flush=True,
            )
        else:
            # No good match — use centre of section screenshot (existing behaviour)
            scene = {
                **scene,
                "visualTargetId":       None,
                "focusX":               scene.get("focusX", 0.5),
                "focusY":               scene.get("focusY", 0.5),
                "highlightBox":         None,
                "motionIntent":         "zoom",
                "elementScreenshotUrl": None,
            }
            print(
                f"[VisualMapper] scene={scene.get('type')} → no match (best score={best_score:.2f}), fallback",
                flush=True,
            )

        updated.append(scene)

    return updated
