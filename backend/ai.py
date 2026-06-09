"""
ai.py – Gemini AI storyboard director.

Sends page metadata + detected sections to Gemini and receives a
structured JSON storyboard. Falls back to a rule-based storyboard
when no API key is available.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detector import SectionData

log = logging.getLogger(__name__)

# ─── Scene count from target duration ─────────────────────────────────────────

SCENE_DURATION  = 4.0
TRANSITION_DUR  = 0.5

def scenes_for_duration(target: int) -> int:
    """Return how many scenes fit within target seconds."""
    best = 2
    for n in range(2, 10):
        dur = n * SCENE_DURATION - (n - 1) * TRANSITION_DUR
        if dur <= target:
            best = n
    return best

# ─── Layout + animation mappings ─────────────────────────────────────────────

SECTION_LAYOUT_MAP = {
    "hero":         "hero_layout",
    "demo":         "split_layout",
    "features":     "feature_layout",
    "benefits":     "split_layout",
    "integrations": "split_layout",
    "testimonials": "reverse_split_layout",
    "customers":    "split_layout",
    "pricing":      "split_layout",
    "faq":          "reverse_split_layout",
    "cta":          "cta_layout",
    "contact":      "cta_layout",
}

SECTION_ANIMATION_MAP = {
    "hero":         "zoom_in",
    "demo":         "pan_left",
    "features":     "pan_right",
    "benefits":     "zoom_in",
    "integrations": "pan_left",
    "testimonials": "pan_right",
    "customers":    "zoom_out",
    "pricing":      "zoom_in",
    "faq":          "pan_left",
    "cta":          "fade",
}

# ─── Gemini prompt ────────────────────────────────────────────────────────────

def _build_prompt(meta: dict, sections: list["SectionData"], n_scenes: int) -> str:
    section_summary = "\n".join(
        f"- [{s.section_type.upper()}] heading: \"{s.heading}\" | sub: \"{s.subheading[:80]}\" | text: \"{s.text[:120]}\""
        for s in sections
    )

    return f"""You are a professional marketing video director specializing in SaaS explainer videos.

Analyze this website and generate a {n_scenes}-scene video storyboard.

WEBSITE DATA:
URL: {meta.get('url','')}
Title: {meta.get('title','')}
H1: {meta.get('h1','')}
Description: {meta.get('description','')}

DETECTED SECTIONS:
{section_summary}

RULES:
1. Select exactly {n_scenes} scenes from the detected sections.
2. First scene MUST use the "hero" section with "hero_layout".
3. Last scene SHOULD be "cta_layout" (use "cta" section or repurpose hero).
4. Headlines must be punchy marketing copy — MAX 5 WORDS.
5. Subheadlines — MAX 10 WORDS.
6. Vary layouts and animations. Do not repeat same layout twice in a row.
7. Ignore: blog, careers, about, legal, footer (unless CTA).
8. Prefer order: hero → features/demo → benefits/testimonials → pricing → cta.

AVAILABLE LAYOUTS: hero_layout, split_layout, reverse_split_layout, feature_layout, cta_layout
AVAILABLE ANIMATIONS: zoom_in, zoom_out, pan_left, pan_right, diagonal_motion, fade

Return ONLY valid JSON — no markdown, no explanation:
{{
  "website_type": "saas|startup|ecommerce|agency|portfolio",
  "video_style": "explainer|launch|showcase|presentation|promo",
  "scenes": [
    {{
      "scene_type": "intro|feature|benefit|social_proof|pricing|cta",
      "headline": "...",
      "subheadline": "...",
      "section": "<one of the detected section types>",
      "layout": "<layout name>",
      "animation": "<animation name>"
    }}
  ]
}}"""


# ─── Gemini call (async) ──────────────────────────────────────────────────────

async def _call_gemini(prompt: str, api_key: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    def _sync():
        return model.generate_content(
            prompt,
            generation_config={"temperature": 0.4, "max_output_tokens": 2048},
        ).text

    return await asyncio.to_thread(_sync)


def _parse_json(raw: str) -> dict:
    """Extract and parse JSON from Gemini response (handles markdown fences)."""
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    # Find first { ... } block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Gemini response")
    return json.loads(match.group())


# ─── Rule-based fallback storyboard ──────────────────────────────────────────

def _fallback_storyboard(sections: list["SectionData"], n_scenes: int) -> dict:
    """Build a storyboard without AI — useful when no Gemini key is available."""
    PRIORITY = ["hero", "demo", "features", "benefits", "testimonials",
                "pricing", "integrations", "customers", "faq", "cta"]

    detected = {s.section_type: s for s in sections}

    # Sort detected sections by priority
    ordered = [s for t in PRIORITY for s in [detected.get(t)] if s]
    # Append any remaining
    for s in sections:
        if s not in ordered:
            ordered.append(s)

    selected = ordered[:n_scenes]

    scenes = []
    animations = ["zoom_in", "pan_left", "pan_right", "zoom_out", "pan_right", "diagonal_motion", "fade"]

    for i, sec in enumerate(selected):
        is_last = i == len(selected) - 1
        layout = SECTION_LAYOUT_MAP.get(sec.section_type, "split_layout")
        if is_last and sec.section_type not in ("cta", "contact"):
            layout = "cta_layout"

        scenes.append({
            "scene_type": "intro" if i == 0 else ("cta" if is_last else "feature"),
            "headline": _default_headline(sec, i),
            "subheadline": sec.subheading[:60] if sec.subheading else "",
            "section": sec.section_type,
            "layout": layout,
            "animation": animations[i % len(animations)],
        })

    return {
        "website_type": "saas",
        "video_style": "explainer",
        "scenes": scenes,
    }


def _default_headline(sec: "SectionData", idx: int) -> str:
    DEFAULTS = {
        "hero":         "Build Something Great",
        "features":     "Powerful Features",
        "demo":         "See It In Action",
        "benefits":     "Built For You",
        "testimonials": "Loved By Thousands",
        "customers":    "Trusted By Leaders",
        "pricing":      "Simple Transparent Pricing",
        "integrations": "Connect Everything",
        "faq":          "Got Questions?",
        "cta":          "Start Free Today",
    }
    if sec.heading and len(sec.heading.split()) <= 7:
        return sec.heading
    return DEFAULTS.get(sec.section_type, "Discover More")


# ─── Public entry point ───────────────────────────────────────────────────────

async def generate_storyboard(
    meta: dict,
    sections: list["SectionData"],
    target_duration: int = 20,
    api_key: str | None = None,
) -> dict:
    n_scenes = scenes_for_duration(target_duration)
    n_scenes = min(n_scenes, len(sections)) if sections else 2

    if not api_key:
        log.info("No Gemini API key — using rule-based fallback storyboard.")
        return _fallback_storyboard(sections, n_scenes)

    try:
        prompt = _build_prompt(meta, sections, n_scenes)
        raw    = await _call_gemini(prompt, api_key)
        board  = _parse_json(raw)

        # Validate & patch scenes
        detected_types = {s.section_type for s in sections}
        valid_scenes = []
        for sc in board.get("scenes", []):
            # If Gemini references a section we don't have, find nearest
            if sc.get("section") not in detected_types:
                sc["section"] = sections[0].section_type if sections else "hero"
            valid_scenes.append(sc)

        board["scenes"] = valid_scenes[:n_scenes]
        log.info("Gemini storyboard: %d scenes, style=%s", len(board["scenes"]), board.get("video_style"))
        return board

    except Exception as exc:
        log.warning("Gemini failed (%s) — falling back to rule-based storyboard.", exc)
        return _fallback_storyboard(sections, n_scenes)
