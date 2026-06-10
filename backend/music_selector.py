"""
music_selector.py – Selects background music based on template, website type, and story tone.

Returns a track path and category without ever crashing the pipeline.
If no music files are found the result contains None values and the
pipeline continues silently.
"""
from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from story_extractor import StoryData

log = logging.getLogger(__name__)

MUSIC_DIR = Path(__file__).parent / "assets" / "music"

# ── Category mapping rules ────────────────────────────────────────────────────
#
# Priority order:
#   1. template_id  (strongest signal — user chose it)
#   2. website_type (from Gemini / fallback storyboard)
#   3. story tone   (keywords in title/tagline)
#   4. default

TEMPLATE_TO_CATEGORY: dict[str, str] = {
    "modern-saas": "modern-saas",
    "apple":       "minimal-premium",
    "minimal":     "minimal-premium",
    "startup":     "tech-futuristic",
}

WEBSITE_TYPE_TO_CATEGORY: dict[str, str] = {
    "saas":        "modern-saas",
    "ai":          "tech-futuristic",
    "automation":  "tech-futuristic",
    "devtools":    "tech-futuristic",
    "finance":     "corporate",
    "crm":         "corporate",
    "hr":          "corporate",
    "legal":       "corporate",
    "healthcare":  "corporate",
    "ecommerce":   "modern-saas",
    "marketplace": "modern-saas",
    "productivity":"modern-saas",
    "analytics":   "tech-futuristic",
    "security":    "tech-futuristic",
    "design":      "minimal-premium",
    "creative":    "minimal-premium",
    "agency":      "minimal-premium",
}

# Keywords found in product title / tagline → category
TONE_KEYWORDS: list[tuple[list[str], str]] = [
    (["ai", "artificial intelligence", "machine learning", "automate", "automation", "gpt"], "tech-futuristic"),
    (["bank", "finance", "invest", "payroll", "accounting", "compliance", "legal", "crm"], "corporate"),
    (["design", "creative", "studio", "portfolio", "minimal", "elegant"], "minimal-premium"),
]

DEFAULT_CATEGORY = "modern-saas"


def _pick_track(category: str) -> Path | None:
    """Randomly pick one MP3/WAV from the given category folder. Returns None if empty."""
    folder = MUSIC_DIR / category
    if not folder.is_dir():
        log.warning("[Music] Category folder missing: %s", folder)
        return None
    tracks = list(folder.glob("*.mp3")) + list(folder.glob("*.wav"))
    if not tracks:
        log.warning("[Music] No tracks in category: %s", category)
        return None
    chosen = random.choice(tracks)
    log.info("[Music] Selected: %s / %s", category, chosen.name)
    return chosen


def _detect_tone(meta: dict) -> str | None:
    """Scan page title + tagline for tone keywords."""
    text = " ".join([
        meta.get("title", ""),
        meta.get("tagline", ""),
        meta.get("description", ""),
    ]).lower()
    for keywords, category in TONE_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category
    return None


def select_music(
    template_id: str | None = None,
    website_type: str | None = None,
    meta: dict | None = None,
    story: "StoryData | None" = None,
) -> dict:
    """
    Select a background music track.

    Returns:
        {
            "musicCategory": str | None,
            "musicTrack":    str | None,   # relative URL: /assets/music/<cat>/<file>
            "musicPath":     Path | None,  # absolute path for FFmpeg
        }
    """
    try:
        # Priority 1 — template
        category = TEMPLATE_TO_CATEGORY.get(template_id or "")

        # Priority 2 — website type
        if not category and website_type:
            category = WEBSITE_TYPE_TO_CATEGORY.get(website_type.lower())

        # Priority 3 — tone from meta
        if not category and meta:
            category = _detect_tone(meta)

        # Priority 4 — default
        if not category:
            category = DEFAULT_CATEGORY

        track_path = _pick_track(category)

        # If chosen category is empty, try other categories before giving up
        if track_path is None:
            fallback_order = ["modern-saas", "minimal-premium", "tech-futuristic", "corporate"]
            for fallback in fallback_order:
                if fallback != category:
                    track_path = _pick_track(fallback)
                    if track_path:
                        category = fallback
                        break

        if track_path is None:
            print("[Music] No music files found anywhere — continuing without music.", flush=True)
            return {"musicCategory": None, "musicTrack": None, "musicPath": None}

        relative_url = f"/assets/music/{category}/{track_path.name}"
        print(f"[Music] Category={category}  Track={track_path.name}", flush=True)

        return {
            "musicCategory": category,
            "musicTrack":    relative_url,
            "musicPath":     track_path,
        }

    except Exception as exc:
        log.error("[Music] select_music failed: %s", exc)
        return {"musicCategory": None, "musicTrack": None, "musicPath": None}
