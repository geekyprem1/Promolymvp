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
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detector import SectionData
    from story_extractor import StoryData

log = logging.getLogger(__name__)

# Force UTF-8 output on Windows to avoid charmap errors
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Timing constants ──────────────────────────────────────────────────────────

FPS              = 30
SCENE_FRAMES     = 150   # 5s default per scene @ 30fps
MIN_SCENE_FRAMES = 90    # 3s minimum

# Content-aware durations: shorter for punchy scenes, longer for detail scenes
SCENE_DURATION_FRAMES: dict[str, int] = {
    "hook":         90,    # 3s – short punchy opener
    "problem":      120,   # 4s – establish the pain
    "solution":     120,   # 4s – introduce the product
    "features":     150,   # 5s – show the demo / feature
    "benefits":     150,   # 5s – outcome-led copy
    "testimonials": 120,   # 4s – social proof
    "proof":        120,   # 4s – alias
    "cta":          90,    # 3s – clear, no overthinking
    "content":      150,
    "hero":         150,
}

# ── Scene type mappings ───────────────────────────────────────────────────────

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
    # Story-arc scene types pass through unchanged
    "hook":         "hook",
    "problem":      "problem",
    "solution":     "solution",
    "proof":        "testimonials",
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
    """Return how many scenes fit within target seconds.
    Uses the average of a typical persuasion arc to estimate capacity.
    Average arc duration: hook(3) + problem(4) + solution(4) + 2×features(5) + cta(3) ≈ 4s avg.
    """
    avg_scene_seconds = sum(SCENE_DURATION_FRAMES.values()) / len(SCENE_DURATION_FRAMES) / FPS
    best = max(2, int(target / avg_scene_seconds))
    return min(best, 10)  # cap at 10 scenes


# ── Gemini prompts ────────────────────────────────────────────────────────────

def _build_story_prompt(
    story: "StoryData",
    meta: dict,
    sections: list["SectionData"],
    n_scenes: int,
) -> str:
    """
    Story-arc based prompt.  Sends the extracted marketing narrative to Gemini
    and asks it to produce scenes that follow a persuasion arc rather than
    mirroring website structure.
    """
    section_snapshot = "\n".join(
        f"- [{s.section_type.upper()}] {s.heading[:60]}"
        for s in sections if s.heading
    )

    json_example = '''{
  "website_type": "saas",
  "video_style": "story",
  "scenes": [
    {
      "type": "hook",
      "headline": "Ship 3x Faster",
      "subheadline": "The platform 50,000 teams rely on",
      "badge": "INTRO",
      "section": "hero",
      "stat": "3x",
      "statLabel": "faster shipping",
      "narration": "Imagine shipping three times faster — without changing your workflow.",
      "transition": "fade"
    },
    {
      "type": "problem",
      "headline": "Context Switching Kills Flow",
      "subheadline": "Teams lose 8 hours a week to tool chaos",
      "badge": "THE PROBLEM",
      "section": "hero",
      "painPoints": ["12 disconnected tools", "Endless status meetings", "Missed deadlines"],
      "transition": "dissolve"
    },
    {
      "type": "solution",
      "headline": "One Platform. Everything Connected.",
      "subheadline": "Replace your entire toolstack",
      "badge": "THE SOLUTION",
      "section": "features",
      "checkpoints": ["Instant setup", "Works with your stack", "Ship in days not weeks"],
      "transition": "zoomIn"
    },
    {
      "type": "features",
      "headline": "Built For Speed",
      "subheadline": "Real outcomes, not just features",
      "badge": "BENEFITS",
      "section": "features",
      "bullets": ["Automate repetitive tasks", "Real-time collaboration", "One-click deploys"],
      "reverse": false,
      "bodyText": "",
      "transition": "slideLeft"
    },
    {
      "type": "cta",
      "headline": "Start Building Today",
      "subheadline": "Free forever, no credit card needed",
      "badge": "GET STARTED",
      "section": "cta",
      "ctaLabel": "Start Free",
      "domain": "example.com",
      "transition": "zoomIn"
    }
  ]
}'''

    valid_section_types = [s.section_type for s in sections]

    return (
        "You are an expert marketing video director specialising in SaaS conversion videos.\n"
        "Your job is to write a video script that SELLS — not one that describes a website.\n\n"
        "──────────────────────────────────────────\n"
        "EXTRACTED PRODUCT STORY\n"
        "──────────────────────────────────────────\n"
        f"{story.to_prompt_block()}\n\n"
        "WEBSITE CONTEXT\n"
        f"URL:   {meta.get('url', '')}\n"
        f"Title: {meta.get('title', '')}\n"
        f"Sections on page:\n{section_snapshot}\n\n"
        "──────────────────────────────────────────\n"
        "YOUR TASK\n"
        "──────────────────────────────────────────\n"
        f"Generate exactly {n_scenes} scenes following a persuasion arc:\n"
        "  Scene 1 → HOOK: open with the transformation / biggest benefit\n"
        "  Scene 2 → PROBLEM: show the audience's pain with specifics\n"
        "  Scene 3 → SOLUTION: introduce the product as the answer\n"
        f"  Scenes 4–{n_scenes - 1} → BENEFIT or PROOF: one concrete outcome or social proof per scene\n"
        f"  Scene {n_scenes} → CTA: clear, low-friction call to action\n\n"
        "COPY RULES\n"
        "1. Headlines: MAX 5 words. Bold, benefit-led, not descriptive.\n"
        "2. Subheadlines: MAX 12 words. Expand the headline with specifics.\n"
        "3. For 'hook' type: add 'stat' (e.g. '10x') and 'statLabel' (e.g. 'faster').\n"
        "4. For 'problem' type: add 'painPoints' — 3 specific bullets (max 6 words each).\n"
        "5. For 'solution' type: add 'checkpoints' — 3 outcome bullets (max 6 words each).\n"
        "6. For 'features' type: add 3–4 'bullets' (max 8 words each).\n"
        "7. For 'proof' type: add 'quote', 'author', 'company'.\n"
        "8. For 'cta' type: add 'ctaLabel' (action phrase, max 4 words) and 'domain'.\n"
        "9. badge: 1–3 word CAPS label describing the scene's role (e.g. 'THE PROBLEM').\n"
        "13. Add 'narration': one sentence (max 20 words) to be spoken aloud for each scene.\n"
        f"10. 'section' must be one of: {valid_section_types}\n"
        "11. Write for OUTCOMES and TRANSFORMATION, not feature lists.\n"
        "12. Use the extracted metrics and social proof where they fit naturally.\n\n"
        "VALID SCENE TYPES: hook, problem, solution, features, benefits, proof, cta\n"
        "VALID TRANSITIONS: fade, slideLeft, slideRight, zoomIn, dissolve\n\n"
        f"Return ONLY valid JSON matching this schema exactly — no markdown:\n{json_example}"
    )


def _build_section_prompt(meta: dict, sections: list["SectionData"], n_scenes: int) -> str:
    """
    Fallback structural prompt used when StoryData is too sparse.
    Mirrors the original section-mapping approach.
    """
    section_summary = "\n".join(
        f"- [{s.section_type.upper()}] heading: \"{s.heading}\" | sub: \"{s.subheading[:80]}\" | text: \"{s.text[:150]}\""
        for s in sections
    )
    valid_types = [s.section_type for s in sections]

    json_example = '''{
  "website_type": "saas",
  "video_style": "explainer",
  "scenes": [
    {
      "type": "hero",
      "headline": "Build Something Great",
      "subheadline": "The platform teams love",
      "badge": "INTRO",
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


# ── Gemini call ───────────────────────────────────────────────────────────────

async def _call_gemini(prompt: str, api_key: str) -> str:
    """
    Call OpenRouter API (OpenAI-compatible) with Gemini 2.5 Flash.
    Falls back through model cascade if a model is unavailable.
    """
    import httpx

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    MODELS = [
        "google/gemini-2.5-flash",
        "google/gemini-2.5-flash-lite",
        "google/gemini-2.0-flash-001",
        "google/gemini-flash-1.5",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://promoly.app",
        "X-Title": "Promoly",
    }

    last_err = None
    for model_name in MODELS:
        for attempt in range(3):
            try:
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 8192,
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)

                if resp.status_code == 503 and attempt < 2:
                    wait = (attempt + 1) * 5
                    log.warning("Model %s got 503, retry %d in %ds...", model_name, attempt + 1, wait)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code in (401, 403):
                    raise ValueError(f"API_KEY invalid: {resp.status_code} {resp.text[:100]}")
                if resp.status_code == 429:
                    raise ValueError(f"429 quota_exceeded: {resp.text[:100]}")
                if resp.status_code != 200:
                    raise ValueError(f"OpenRouter error {resp.status_code}: {resp.text[:200]}")

                data = resp.json()
                result = data["choices"][0]["message"]["content"]
                log.info("OpenRouter model used: %s", model_name)
                print(f"[AI] OpenRouter model used: {model_name} (response len={len(result)})", flush=True)
                return result

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                err_str = str(e)
                if attempt < 2:
                    await asyncio.sleep((attempt + 1) * 5)
                    continue
                log.warning("Model %s network error: %s", model_name, err_str[:120])
                last_err = ValueError(err_str)
                break
            except ValueError:
                raise
            except Exception as e:
                log.warning("Model %s failed: %s", model_name, str(e)[:120])
                print(f"[AI] Model {model_name} failed: {str(e)[:120]}", flush=True)
                last_err = e
                break

    raise last_err or ValueError("All OpenRouter models failed")


def _parse_json(raw: str) -> dict:
    # Strip markdown code fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().replace("```", "").strip()

    start = raw.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Gemini response")

    json_str = raw[start:]

    # Fix trailing commas before } or ]
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

    # Try direct parse first
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # If truncated, try to close open brackets/braces
    try:
        fixed = _close_json(json_str)
        return json.loads(fixed)
    except Exception:
        pass

    # Last resort: find last valid closing brace
    for end in range(len(json_str), 0, -1):
        try:
            return json.loads(json_str[:end])
        except json.JSONDecodeError:
            continue

    raise ValueError("Could not parse JSON from Gemini response")


def _close_json(s: str) -> str:
    """Attempt to close truncated JSON by counting open brackets."""
    closers = {"{": "}", "[": "]"}
    stack = []
    in_string = False
    escape = False

    for ch in s:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(closers[ch])
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()

    # Close any open strings and brackets
    suffix = ""
    if in_string:
        suffix += '"'
    while stack:
        suffix += stack.pop()
    return s + suffix


# ── Build Remotion props from Gemini/fallback scenes + screenshot paths ───────

def build_remotion_props(
    raw_scenes: list[dict],
    sections: list["SectionData"],
    meta: dict,
    base_url: str,
    website_type: str = "saas",
    video_style: str  = "explainer",
) -> dict:
    """
    Convert raw AI scene list to full Remotion PromoVideoProps dict.
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
            parts = p.parts
            try:
                idx = next(i for i, pt in enumerate(parts) if pt == "screenshots")
                rel = "/".join(parts[idx:])
                screenshot_url = f"{base_url}/{rel}"
            except StopIteration:
                screenshot_url = f"{base_url}/screenshots/{p.name}"

        scene_type = sc.get("type", SECTION_TYPE_MAP.get(section_type, "content"))
        duration = SCENE_DURATION_FRAMES.get(scene_type, SCENE_FRAMES)

        scene: dict = {
            "type":             scene_type,
            "from":             offset,
            "durationInFrames": duration,
            "headline":         sc.get("headline", HEADLINE_DEFAULTS.get(section_type, "Discover More")),
            "subheadline":      sc.get("subheadline", sec_data.subheading[:80] if sec_data else ""),
            "badge":            sc.get("badge", section_type.upper()),
            "screenshotUrl":    screenshot_url,
            "transition":       sc.get("transition", TRANSITION_MAP.get(section_type, "fade")),
            "narration":        sc.get("narration", ""),
        }

        # ── Story-arc scene types ──────────────────────────────────────────────
        if scene_type == "hook":
            scene["stat"]      = sc.get("stat", "")
            scene["statLabel"] = sc.get("statLabel", "")

        elif scene_type == "problem":
            pain = sc.get("painPoints", [])
            if not pain:
                pain = [sc.get("subheadline", ""), "Too many disconnected tools", "Wasted time and effort"]
            scene["painPoints"] = [p for p in pain if p][:4]

        elif scene_type == "solution":
            cps = sc.get("checkpoints", [])
            if not cps:
                cps = ["Simple setup", "Instant results", "Built to scale"]
            scene["checkpoints"] = [c for c in cps if c][:4]

        # ── Existing scene types ───────────────────────────────────────────────
        elif scene_type == "features":
            bullets = sc.get("bullets", [])
            if not bullets and sec_data:
                raw_lines = [l.strip() for l in sec_data.text.split("\n") if len(l.strip()) > 10]
                bullets = raw_lines[:4]
            scene["bullets"]  = bullets or ["Fast and reliable", "Easy to use", "Scales with you"]
            scene["reverse"]  = bool(sc.get("reverse", SECTION_REVERSE_MAP.get(section_type, False)))
            scene["bodyText"] = sc.get("bodyText", sec_data.text[:200] if sec_data else "")

        elif scene_type == "benefits":
            scene["reverse"]  = bool(sc.get("reverse", SECTION_REVERSE_MAP.get(section_type, False)))
            scene["bodyText"] = sc.get("bodyText", sec_data.text[:200] if sec_data else "")

        elif scene_type in ("testimonials", "proof"):
            scene["type"]    = "testimonials"
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


# ── Story-aware rule-based fallback ──────────────────────────────────────────

def _story_fallback(
    story: "StoryData",
    sections: list["SectionData"],
    n_scenes: int,
) -> dict:
    """
    Rule-based storyboard built from StoryData.
    Produces a narrative arc without Gemini: hook → problem → solution → benefit(s) → cta.
    """
    def _first_section(stype: str) -> str:
        for s in sections:
            if s.section_type == stype:
                return s.section_type
        return sections[0].section_type if sections else "hero"

    arc: list[dict] = []
    transitions = ["fade", "dissolve", "zoomIn", "slideLeft", "slideRight", "slideLeft", "zoomIn"]

    # Scene 1 – Hook
    arc.append({
        "type":       "hook",
        "headline":   story.solution[:40] if story.solution else story.product_name,
        "subheadline": story.hook[:80] if story.hook else "",
        "badge":      "INTRO",
        "section":    _first_section("hero"),
        "stat":       story.metrics[0] if story.metrics else "",
        "statLabel":  "improvement",
        "transition": "fade",
    })

    # Scene 2 – Problem (only if n_scenes >= 3)
    if n_scenes >= 3 and story.problem:
        arc.append({
            "type":       "problem",
            "headline":   "The Old Way Is Broken",
            "subheadline": story.problem[:80],
            "badge":      "THE PROBLEM",
            "section":    _first_section("hero"),
            "painPoints": [story.problem[:60]] + (story.benefits[:2] if len(story.benefits) >= 2 else []),
            "transition": "dissolve",
        })

    # Scene 3 – Solution
    if len(arc) < n_scenes - 1:
        checkpoints = story.benefits[:3] if story.benefits else ["Simple setup", "Instant results", "No learning curve"]
        arc.append({
            "type":        "solution",
            "headline":    f"Meet {story.product_name}",
            "subheadline": story.solution[:80] if story.solution else "",
            "badge":       "THE SOLUTION",
            "section":     _first_section("features"),
            "checkpoints": checkpoints,
            "transition":  "zoomIn",
        })

    # Middle scenes – Benefits
    remaining = n_scenes - 1 - len(arc)
    for i in range(remaining):
        b = story.benefits[i] if i < len(story.benefits) else f"Benefit {i+1}"
        proof = story.social_proof[i] if i < len(story.social_proof) else ""
        if proof:
            arc.append({
                "type":      "proof",
                "headline":  "Loved By Teams",
                "subheadline": proof[:80],
                "badge":     "SOCIAL PROOF",
                "section":   _first_section("testimonials"),
                "quote":     proof,
                "author":    "",
                "company":   "",
                "transition": transitions[(len(arc)) % len(transitions)],
            })
        else:
            arc.append({
                "type":      "features",
                "headline":  b[:40],
                "subheadline": "",
                "badge":     "BENEFITS",
                "section":   _first_section("features"),
                "bullets":   story.benefits[:4],
                "reverse":   i % 2 == 1,
                "bodyText":  "",
                "transition": transitions[(len(arc)) % len(transitions)],
            })

    # Last scene – CTA
    arc.append({
        "type":       "cta",
        "headline":   "Start Today",
        "subheadline": story.cta[:80] if story.cta else "No credit card required",
        "badge":      "GET STARTED",
        "section":    _first_section("cta"),
        "ctaLabel":   story.cta[:30] if story.cta else "Get Started Free",
        "domain":     "",
        "transition": "zoomIn",
    })

    return {
        "website_type": "saas",
        "video_style":  "story",
        "scenes":       arc[:n_scenes],
        "ai_used":      False,
        "strategy":     "story-fallback",
    }


# ── Section-based fallback storyboard ─────────────────────────────────────────

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


# ── Public entry point ────────────────────────────────────────────────────────

async def generate_storyboard(
    meta: dict,
    sections: list["SectionData"],
    target_duration: int = 20,
    api_key: str | None  = None,
    story: "StoryData | None" = None,
) -> dict:
    n_scenes = scenes_for_duration(target_duration)
    n_scenes = min(n_scenes, len(sections)) if sections else 2

    if not api_key:
        print("[AI] No Gemini key -- using story-aware rule-based storyboard.", flush=True)
        log.info("No Gemini key -- story-aware rule-based storyboard.")
        return _story_fallback(story, sections, n_scenes) if (story and story.is_rich()) \
            else _fallback_storyboard(sections, n_scenes)

    # Pick prompt strategy: prefer story-arc if we have rich story data
    use_story_prompt = story is not None and story.is_rich()
    strategy = "story-arc" if use_story_prompt else "section-map"
    print(f"[AI] OpenRouter key received (len={len(api_key)}) -- strategy: {strategy}", flush=True)

    try:
        if use_story_prompt:
            prompt = _build_story_prompt(story, meta, sections, n_scenes)
        else:
            prompt = _build_section_prompt(meta, sections, n_scenes)

        raw   = await _call_gemini(prompt, api_key)
        board = _parse_json(raw)

        detected_types = {s.section_type for s in sections}
        valid_scenes = []
        for sc in board.get("scenes", []):
            if sc.get("section") not in detected_types:
                sc["section"] = sections[0].section_type if sections else "hero"
            valid_scenes.append(sc)

        board["scenes"]   = valid_scenes[:n_scenes]
        board["ai_used"]  = True
        board["strategy"] = strategy
        print(f"[AI] OpenRouter storyboard ({strategy}): {len(board['scenes'])} scenes", flush=True)
        log.info("OpenRouter storyboard (%s): %d scenes", strategy, len(board["scenes"]))
        return board

    except Exception as exc:
        err_str = str(exc)
        print(f"[AI] OpenRouter failed: {err_str[:200]}", flush=True)
        log.warning("OpenRouter failed (%s) -- fallback.", exc)

        result = _story_fallback(story, sections, n_scenes) if (story and story.is_rich()) \
            else _fallback_storyboard(sections, n_scenes)

        if "RESOURCE_EXHAUSTED" in err_str or "credits are depleted" in err_str:
            result["gemini_error"] = "prepaid_credits_depleted"
        elif "API_KEY" in err_str or "401" in err_str or "403" in err_str:
            result["gemini_error"] = "invalid_api_key"
        elif "429" in err_str:
            result["gemini_error"] = "quota_exceeded"
        else:
            result["gemini_error"] = err_str[:150]
        return result
