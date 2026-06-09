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
    for n in range(2, 20):
        dur = n * SCENE_DURATION - (n - 1) * TRANSITION_DUR
        if dur <= target:
            best = n
        else:
            break  # increasing n only makes duration longer
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

    json_example = '''
{
  "website_type": "saas",
  "video_style": "explainer",
  "scenes": [
    {
      "scene_type": "intro",
      "headline": "Build Something Great",
      "subheadline": "The platform teams love",
      "section": "hero",
      "layout": "hero_layout",
      "animation": "zoom_in"
    }
  ]
}'''

    return (
        f"You are a professional marketing video director specializing in SaaS explainer videos.\n\n"
        f"Analyze this website and generate a {n_scenes}-scene video storyboard.\n\n"
        f"WEBSITE DATA:\n"
        f"URL: {meta.get('url','')}\n"
        f"Title: {meta.get('title','')}\n"
        f"H1: {meta.get('h1','')}\n"
        f"Description: {meta.get('description','')}\n\n"
        f"DETECTED SECTIONS:\n{section_summary}\n\n"
        f"RULES:\n"
        f"1. Select exactly {n_scenes} scenes.\n"
        f"2. First scene MUST be hero section with hero_layout.\n"
        f"3. Last scene SHOULD be cta_layout.\n"
        f"4. Headlines MAX 5 WORDS. Subheadlines MAX 10 WORDS.\n"
        f"5. Vary layouts — no same layout twice in a row.\n"
        f"6. Section value must be one of: {[s.section_type for s in sections]}\n\n"
        f"AVAILABLE LAYOUTS: hero_layout, split_layout, reverse_split_layout, feature_layout, cta_layout\n"
        f"AVAILABLE ANIMATIONS: zoom_in, zoom_out, pan_left, pan_right, diagonal_motion, fade\n\n"
        f"Return ONLY valid JSON, no markdown, no explanation. Example format:{json_example}"
    )


# ─── Gemini call (async) ──────────────────────────────────────────────────────

async def _call_gemini(prompt: str, api_key: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
        "gemini-pro-latest",
    ]

    last_err = None
    for model_name in MODELS:
        for attempt in range(3):  # retry 3x on 503
            try:
                def _sync(m=model_name):
                    return client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.4,
                            max_output_tokens=2048,
                        ),
                    ).text
                result = await asyncio.to_thread(_sync)
                log.info("✅ Gemini model used: %s", model_name)
                return result
            except Exception as e:
                err_str = str(e)
                if "503" in err_str and attempt < 2:
                    wait = (attempt + 1) * 5  # 5s, 10s
                    log.warning("Model %s got 503, retry %d in %ds...", model_name, attempt+1, wait)
                    await asyncio.sleep(wait)
                    continue
                log.warning("Model %s failed: %s", model_name, err_str[:120])
                last_err = e
                break

    raise last_err


def _parse_json(raw: str) -> dict:
    """Extract and parse JSON from Gemini response (handles markdown fences)."""
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    raw = raw.replace("```", "").strip()
    # Find first { ... } block
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in Gemini response")
    json_str = raw[start:end]
    # Fix common Gemini JSON issues: trailing commas
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
    return json.loads(json_str)


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
        board = _fallback_storyboard(sections, n_scenes)
        board["ai_used"] = False
        return board

    try:
        prompt = _build_prompt(meta, sections, n_scenes)
        raw    = await _call_gemini(prompt, api_key)
        board  = _parse_json(raw)

        # Validate & patch scenes
        detected_types = {s.section_type for s in sections}
        valid_scenes = []
        for sc in board.get("scenes", []):
            if sc.get("section") not in detected_types:
                sc["section"] = sections[0].section_type if sections else "hero"
            valid_scenes.append(sc)

        board["scenes"] = valid_scenes[:n_scenes]
        board["ai_used"] = True
        log.info("✅ Gemini storyboard: %d scenes, style=%s", len(board["scenes"]), board.get("video_style"))
        return board

    except Exception as exc:
        log.warning("Gemini failed (%s) — falling back to rule-based storyboard.", exc)
        board = _fallback_storyboard(sections, n_scenes)
        board["ai_used"] = False
        return board
