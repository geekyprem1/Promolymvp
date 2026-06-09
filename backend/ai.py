"""
ai.py – Gemini AI storyboard director for Remotion pipeline.

Generates a Remotion-compatible storyboard JSON from page metadata
and detected sections. Falls back to rule-based when no API key.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detector import SectionData

log = logging.getLogger(__name__)

# ─── Timing constants ─────────────────────────────────────────────────────────

FPS              = 30
SCENE_FRAMES     = 150   # 5s per scene @ 30fps
MIN_SCENE_FRAMES = 90    # 3s minimum

# ─── Scene type mappings ──────────────────────────────────────────────────────

SECTION_TYPE_MAP = {
    "hero":         "hero",
    "demo":         "features",
    "features":     "features",
    "benefits":     "benefits",
    "integrations": "features",
    "testimonials": "testimonials",
    "customers":    "benefits",
    "pricing":      "features",
    "faq":          "benefits",
    "cta":          "cta",
    "contact":      "cta",
    "content":      "content",
}

SECTION_REVERSE_MAP = {
    "testimonials": True,
    "faq":          True,
    "customers":    True,
    "demo":         True,
}

TRANSITION_MAP = {
    "hero":         "fade",
    "features":     "slideLeft",
    "benefits":     "slideRight",
    "testimonials": "dissolve",
    "pricing":      "slideLeft",
    "cta":          "zoomIn",
    "content":      "slideLeft",
}

HEADLINE_DEFAULTS = {
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
    "contact":      "Get In Touch",
    "content":      "Discover More",
}


def scenes_for_duration(target: int) -> int:
    """Return how many scenes fit within target seconds."""
    best = 2
    for n in range(2, 20):
        dur = n * (SCENE_FRAMES / FPS)
        if dur <= target:
            best = n
        else:
            break
    return best


# ─── Gemini prompt ────────────────────────────────────────────────────────────

def _build_prompt(meta: dict, sections: list["SectionData"], n_scenes: int) -> str:
    section_summary = "\n".join(
        f"- [{s.section_type.upper()}] heading: \"{s.heading}\" | sub: \"{s.subheading[:80]}\" | text: \"{s.text[:150]}\""
        for s in sections
    )

    valid_types = [s.section_type for s in sections]

    json_example = '''
{
  "website_type": "saas",
  "video_style": "explainer",
  "scenes": [
    {
      "type": "hero",
      "headline": "Build Something Great",
      "subheadline": "The platform teams love",
      "badge": "Intro",
      "section": "hero",
      "bullets": [],
      "bodyText": "",
      "ctaLabel": "",
      "quote": "",
      "author": "",
      "company": "",
      "reverse": false,
      "transition": "fade"
    }
  ]
}'''

    return (
        "You are a professional marketing video director for SaaS explainer videos.\n\n"
        f"Generate a {n_scenes}-scene Remotion video storyboard for this website.\n\n"
        "WEBSITE DATA:\n"
        f"URL: {meta.get('url', '')}\n"
        f"Title: {meta.get('title', '')}\n"
        f"H1: {meta.get('h1', '')}\n"
        f"Description: {meta.get('description', '')}\n\n"
        "DETECTED SECTIONS:\n"
        f"{section_summary}\n\n"
        "RULES:\n"
        f"1. Select exactly {n_scenes} scenes.\n"
        "2. First scene type MUST be 'hero'.\n"
        "3. Last scene type SHOULD be 'cta'.\n"
        "4. Headlines MAX 5 words. Subheadlines MAX 10 words.\n"
        "5. For 'features' type: provide 3-4 short bullets (max 8 words each).\n"
        "6. For 'testimonials' type: provide quote, author, company.\n"
        "7. For 'cta' type: provide ctaLabel (e.g. 'Get Started Free').\n"
        "8. Alternate reverse: true/false between scenes.\n"
        "9. badge should be a short 1-2 word label in CAPS (e.g. 'FEATURES', 'HOW IT WORKS').\n"
        f"10. 'section' must be one of: {valid_types}\n\n"
        "VALID SCENE TYPES: hero, features, benefits, testimonials, cta, content\n"
        "VALID TRANSITIONS: fade, slideLeft, slideRight, zoomIn, dissolve\n\n"
        f"Return ONLY valid JSON, no markdown, no explanation:{json_example}"
    )


# ─── Gemini call ──────────────────────────────────────────────────────────────

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
        for attempt in range(3):
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
                    wait = (attempt + 1) * 5
                    log.warning("Model %s got 503, retry %d in %ds...", model_name, attempt + 1, wait)
                    await asyncio.sleep(wait)
                    continue
                log.warning("Model %s failed: %s", model_name, err_str[:120])
                last_err = e
                break

    raise last_err


def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip().replace("```", "").strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON found in Gemini response")
    json_str = raw[start:end]
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
    return json.loads(json_str)


# ─── Build Remotion props from Gemini/fallback scenes + screenshot paths ──────

def build_remotion_props(
    raw_scenes: list[dict],
    sections: list["SectionData"],
    meta: dict,
    base_url: str,
    website_type: str = "saas",
    video_style: str  = "explainer",
) -> dict:
    """
    Convert raw AI scene list → full Remotion PromoVideoProps dict.
    Injects screenshotUrl (HTTP), durationInFrames, from offset.
    """
    sections_map = {s.section_type: s for s in sections}
    remotion_scenes = []
    offset = 0

    for i, sc in enumerate(raw_scenes):
        section_type = sc.get("section", "hero")
        sec_data = sections_map.get(section_type) or (sections[0] if sections else None)

        # Screenshot URL via FastAPI /screenshots/{session}/{file}
        screenshot_url = ""
        if sec_data and sec_data.screenshot_path:
            p = Path(sec_data.screenshot_path)
            # path looks like: screenshots/<session_id>/<filename>
            parts = p.parts
            try:
                idx = next(i for i, pt in enumerate(parts) if pt == "screenshots")
                rel = "/".join(parts[idx:])
                screenshot_url = f"{base_url}/{rel}"
            except StopIteration:
                screenshot_url = f"{base_url}/screenshots/{p.name}"

        scene_type = sc.get("type", SECTION_TYPE_MAP.get(section_type, "content"))
        duration = SCENE_FRAMES

        # Build scene dict matching TypeScript interfaces
        scene: dict = {
            "type":             scene_type,
            "from":             offset,
            "durationInFrames": duration,
            "headline":         sc.get("headline", HEADLINE_DEFAULTS.get(section_type, "Discover More")),
            "subheadline":      sc.get("subheadline", sec_data.subheading[:80] if sec_data else ""),
            "badge":            sc.get("badge", section_type.upper()),
            "screenshotUrl":    screenshot_url,
            "transition":       sc.get("transition", TRANSITION_MAP.get(section_type, "fade")),
        }

        # Type-specific fields
        if scene_type == "features":
            bullets = sc.get("bullets", [])
            if not bullets and sec_data:
                # Extract from section text
                raw_lines = [l.strip() for l in sec_data.text.split("\n") if len(l.strip()) > 10]
                bullets = raw_lines[:4]
            scene["bullets"]  = bullets or ["Fast and reliable", "Easy to use", "Scales with you"]
            scene["reverse"]  = bool(sc.get("reverse", SECTION_REVERSE_MAP.get(section_type, False)))
            scene["bodyText"] = sc.get("bodyText", sec_data.text[:200] if sec_data else "")

        elif scene_type == "benefits":
            scene["reverse"]  = bool(sc.get("reverse", SECTION_REVERSE_MAP.get(section_type, False)))
            scene["bodyText"] = sc.get("bodyText", sec_data.text[:200] if sec_data else "")

        elif scene_type == "testimonials":
            scene["quote"]   = sc.get("quote", sec_data.subheading[:200] if sec_data else sc.get("subheadline", ""))
            scene["author"]  = sc.get("author", "")
            scene["company"] = sc.get("company", "")

        elif scene_type == "cta":
            scene["ctaLabel"] = sc.get("ctaLabel", "Get Started Free")
            scene["domain"]   = meta.get("domain", "")

        elif scene_type == "content":
            scene["reverse"]  = bool(sc.get("reverse", False))
            scene["bodyText"] = sc.get("bodyText", sec_data.text[:200] if sec_data else "")

        remotion_scenes.append(scene)
        offset += duration

    return {
        "scenes":      remotion_scenes,
        "websiteType": website_type,
        "videoStyle":  video_style,
    }


# ─── Fallback storyboard ──────────────────────────────────────────────────────

def _fallback_storyboard(sections: list["SectionData"], n_scenes: int) -> dict:
    PRIORITY = ["hero", "demo", "features", "benefits", "testimonials",
                "pricing", "integrations", "customers", "faq", "cta"]

    detected = {s.section_type: s for s in sections}
    ordered  = [s for t in PRIORITY for s in [detected.get(t)] if s]
    for s in sections:
        if s not in ordered:
            ordered.append(s)
    selected = ordered[:n_scenes]

    transitions = ["fade", "slideLeft", "slideRight", "dissolve", "zoomIn", "slideLeft", "fade"]
    scenes = []

    for i, sec in enumerate(selected):
        is_last  = i == len(selected) - 1
        sec_type = SECTION_TYPE_MAP.get(sec.section_type, "content")
        if is_last and sec.section_type not in ("cta", "contact"):
            sec_type = "cta"

        headline = sec.heading if (sec.heading and len(sec.heading.split()) <= 7) else HEADLINE_DEFAULTS.get(sec.section_type, "Discover More")

        scene: dict = {
            "type":       sec_type,
            "headline":   headline,
            "subheadline": sec.subheading[:80] if sec.subheading else "",
            "badge":      sec.section_type.upper().replace("_", " "),
            "section":    sec.section_type,
            "reverse":    SECTION_REVERSE_MAP.get(sec.section_type, False),
            "transition": transitions[i % len(transitions)],
        }

        if sec_type == "features":
            raw_lines = [l.strip() for l in sec.text.split("\n") if len(l.strip()) > 10]
            scene["bullets"]  = raw_lines[:4] or ["Powerful and fast", "Easy to integrate", "Scales with you"]
            scene["bodyText"] = sec.text[:200]
        elif sec_type == "benefits":
            scene["bodyText"] = sec.text[:200]
        elif sec_type == "testimonials":
            scene["quote"]   = sec.subheading[:200] if sec.subheading else sec.text[:200]
            scene["author"]  = ""
            scene["company"] = ""
        elif sec_type == "cta":
            scene["ctaLabel"] = "Get Started Free"
        elif sec_type == "content":
            scene["bodyText"] = sec.text[:200]

        scenes.append(scene)

    return {
        "website_type": "saas",
        "video_style":  "explainer",
        "scenes":       scenes,
        "ai_used":      False,
    }


# ─── Public entry point ───────────────────────────────────────────────────────

async def generate_storyboard(
    meta: dict,
    sections: list["SectionData"],
    target_duration: int = 20,
    api_key: str | None  = None,
) -> dict:
    n_scenes = scenes_for_duration(target_duration)
    n_scenes = min(n_scenes, len(sections)) if sections else 2

    if not api_key:
        log.info("No Gemini key — rule-based storyboard.")
        return _fallback_storyboard(sections, n_scenes)

    try:
        prompt = _build_prompt(meta, sections, n_scenes)
        raw    = await _call_gemini(prompt, api_key)
        board  = _parse_json(raw)

        detected_types = {s.section_type for s in sections}
        valid_scenes = []
        for sc in board.get("scenes", []):
            if sc.get("section") not in detected_types:
                sc["section"] = sections[0].section_type if sections else "hero"
            valid_scenes.append(sc)

        board["scenes"]   = valid_scenes[:n_scenes]
        board["ai_used"]  = True
        log.info("✅ Gemini storyboard: %d scenes", len(board["scenes"]))
        return board

    except Exception as exc:
        log.warning("Gemini failed (%s) — fallback.", exc)
        return _fallback_storyboard(sections, n_scenes)
