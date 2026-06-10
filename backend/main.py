"""
main.py – Promoly FastAPI backend (Remotion pipeline).

Pipeline:
  URL → Playwright DOM detection → Gemini AI storyboard
      → build_remotion_props() → Remotion render → MP4
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

# Windows: Playwright needs ProactorEventLoop for subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright
from pydantic import BaseModel

load_dotenv()

from detector import detect_sections, extract_page_meta, extract_visual_elements
from story_extractor import extract_story
from ai import generate_storyboard, build_remotion_props, scenes_for_duration
from motion_planner import plan_motion
from templates import get_template, TEMPLATE_LIST
from style_engine import apply_style, STYLE_LIST, DEFAULT_STYLE_ID
from remotion_bridge import render_remotion_video
from music_selector import select_music
from audio_mixer import mix_audio
from voiceover_provider import get_voiceover_provider
from visual_mapper import map_visuals

BASE_DIR        = Path(__file__).parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
OUTPUT_DIR      = BASE_DIR / "output"
ASSETS_DIR      = BASE_DIR / "assets"

SCREENSHOTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

progress_store: dict[str, dict] = {}

FPS = 30

# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(title="Promoly API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/output",      StaticFiles(directory=str(OUTPUT_DIR)),      name="output")
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")
app.mount("/assets",      StaticFiles(directory=str(ASSETS_DIR)),      name="assets")


class GenerateRequest(BaseModel):
    url: str
    session_id: str | None  = None
    target_duration: int    = 20
    gemini_api_key: str | None = None
    template_id: str | None = None
    video_style: str | None = None   # "hybrid" (default) | "website-showcase" | "motion-graphics"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _set(sid: str, stage: str, pct: int, msg: str = "") -> None:
    progress_store[sid] = {"stage": stage, "pct": pct, "message": msg}


def _validate_url(url: str) -> bool:
    return bool(re.match(
        r"^https?://(?:[A-Z0-9-]+\.)+[A-Z]{2,6}(?::\d+)?(?:/\S*)?$",
        url, re.I,
    ))


async def _launch_browser(p):
    for ch in ("chrome", "msedge"):
        try:
            return await p.chromium.launch(headless=True, channel=ch)
        except Exception:
            continue
    return await p.chromium.launch(headless=True)


# ─── Main pipeline ────────────────────────────────────────────────────────────

async def run_pipeline(
    url: str,
    session_id: str,
    target_duration: int,
    api_key: str | None,
    template_id: str | None = None,
    video_style: str | None = None,
) -> dict:
    session_dir    = SCREENSHOTS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    output_path    = OUTPUT_DIR / f"{session_id}.mp4"
    visual_elements: list = []

    # Base URL for screenshot serving (FastAPI /screenshots/<session>/<file>)
    base_url = "http://localhost:8001"

    async with async_playwright() as pw:
        browser = await _launch_browser(pw)

        # ── STEP 1: Website visit + DOM section detection ─────────────────────
        _set(session_id, "capturing", 10, "Loading website…")
        ctx  = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        meta = await extract_page_meta(page)
        max_sc = scenes_for_duration(target_duration)

        def _cap_cb(pct: int, msg: str):
            _set(session_id, "capturing", pct, msg)

        sections = await detect_sections(
            page, session_dir,
            max_sections=max(max_sc + 2, 7),
            progress_cb=_cap_cb,
        )

        # ── Visual element extraction (same browser session) ──────────────────
        _set(session_id, "capturing", 37, "Extracting visual elements…")
        visual_elements = await extract_visual_elements(page, session_dir, sections)

        await ctx.close()
        await browser.close()

    if not sections:
        raise HTTPException(status_code=500, detail="No sections detected on page.")

    # ── STEP 2: Story extraction ──────────────────────────────────────────────
    _set(session_id, "analyzing", 38, "Extracting product story…")
    story = extract_story(meta, sections)
    print(
        f"[Story] problem={bool(story.problem)} solution={bool(story.solution)} "
        f"benefits={len(story.benefits)} proof={len(story.social_proof)} "
        f"rich={story.is_rich()}",
        flush=True,
    )

    # ── STEP 3: AI storyboard ─────────────────────────────────────────────────
    _set(session_id, "analyzing", 42, "Gemini AI writing video script…")
    raw_board = await generate_storyboard(meta, sections, target_duration, api_key, story=story)

    # If AI was requested but fallback happened — tell frontend
    if api_key and not raw_board.get("ai_used", False):
        gemini_error = raw_board.get("gemini_error", "Gemini API failed")
        raise HTTPException(
            status_code=402,
            detail={"type": "ai_fallback", "reason": gemini_error}
        )

    # ── STEP 3: Build Remotion props (inject screenshot URLs + frame offsets) ──
    _set(session_id, "rendering", 50, "Building Remotion storyboard…")
    remotion_props = build_remotion_props(
        raw_scenes   = raw_board.get("scenes", []),
        sections     = sections,
        meta         = meta,
        base_url     = base_url,
        website_type = raw_board.get("website_type", "saas"),
        video_style  = raw_board.get("video_style",  "explainer"),
    )

    # ── STEP 3b: Visual Mapping ───────────────────────────────────────────────
    _set(session_id, "rendering", 51, "Mapping visuals to story…")
    mapped_scenes = map_visuals(remotion_props.get("scenes", []), visual_elements)
    remotion_props = {**remotion_props, "scenes": mapped_scenes}

    # ── STEP 3c: Video Style ──────────────────────────────────────────────────
    _set(session_id, "rendering", 52, "Applying video style…")
    print(f"[Style] Requested video_style: {video_style or DEFAULT_STYLE_ID}", flush=True)
    remotion_props = apply_style(remotion_props, video_style)

    # ── STEP 3d: Motion Planner ───────────────────────────────────────────────
    _set(session_id, "rendering", 53, "Planning motion…")
    template = get_template(template_id)
    print(f"[Template] Using template: {template.name} ({template.id})", flush=True)
    remotion_props = plan_motion(remotion_props, sections=sections, meta=meta, template=template)

    # ── STEP 4: Remotion render ───────────────────────────────────────────────
    async def _rend_cb(pct: int, msg: str):
        _set(session_id, "rendering", pct, msg)

    await render_remotion_video(
        storyboard  = remotion_props,
        output_path = output_path,
        session_id  = session_id,
        fps         = FPS,
        progress_cb = _rend_cb,
    )

    # ── STEP 5: Music selection ───────────────────────────────────────────────
    _set(session_id, "rendering", 84, "Selecting background music…")
    music_info = select_music(
        template_id  = template_id,
        website_type = raw_board.get("website_type"),
        meta         = meta,
    )

    # ── STEP 6: Voiceover (stub — future ElevenLabs) ─────────────────────────
    vo_provider = get_voiceover_provider("stub")
    vo_path = None
    # When voiceover is ready:
    # script = " ".join(s.get("narration","") for s in remotion_props.get("scenes",[]))
    # vo_path = await vo_provider.generate_voiceover(script)

    # ── STEP 7: Audio mixing ──────────────────────────────────────────────────
    if music_info["musicPath"] is not None or vo_path is not None:
        _set(session_id, "rendering", 88, "Mixing audio…")
        await mix_audio(
            video_path     = output_path,
            music_path     = music_info["musicPath"],
            voiceover_path = vo_path,
        )

    # Cleanup screenshots
    shutil.rmtree(session_dir, ignore_errors=True)

    n         = len(remotion_props.get("scenes", []))
    total_dur = round(n * 5.0, 1)   # 150 frames / 30 fps = 5s per scene
    ai_used   = raw_board.get("ai_used", False)

    _set(session_id, "done", 100, "Video ready!")

    # Build lightweight scene list for frontend storyboard display
    scene_list = [
        {
            "type":             s.get("type", ""),
            "headline":         s.get("headline", ""),
            "narration":        s.get("narration", ""),
            "durationInFrames": s.get("durationInFrames", 150),
            "componentType":    s.get("componentType", ""),
            "componentRole":    s.get("componentRole", ""),
            "motionIntent":     s.get("motionIntent", ""),
        }
        for s in remotion_props.get("scenes", [])
    ]

    return {
        "status":     "success",
        "video":      f"output/{session_id}.mp4",
        "session_id": session_id,
        "duration":   total_dur,
        "resolution": "1920×1080",
        "fps":        FPS,
        "scenes":     n,
        "ai_used":    ai_used,
        "audio": {
            "musicCategory": music_info.get("musicCategory"),
            "musicTrack":    music_info.get("musicTrack"),
        },
        "storyboard": {
            "website_type": remotion_props.get("websiteType", "saas"),
            "video_style":  remotion_props.get("videoStyle",  "explainer"),
            "scenes":       scene_list,
        },
    }


# ─── API routes ───────────────────────────────────────────────────────────────

@app.post("/generate")
async def generate_video(req: GenerateRequest):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not _validate_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL.")

    sid     = req.session_id or uuid.uuid4().hex
    api_key = req.gemini_api_key or os.getenv("GEMINI_API_KEY") or None

    _set(sid, "validating", 5, "Validating URL…")

    try:
        return await run_pipeline(
            url, sid, req.target_duration, api_key,
            req.template_id, req.video_style,
        )
    except HTTPException:
        raise
    except Exception as exc:
        progress_store.pop(sid, None)
        raise HTTPException(status_code=500, detail=str(exc)[:400])


@app.get("/progress/{session_id}")
async def get_progress(session_id: str):
    return progress_store.get(session_id, {"stage": "pending", "pct": 0, "message": ""})


@app.get("/templates")
async def list_templates():
    return {"templates": TEMPLATE_LIST}


@app.get("/styles")
async def list_styles():
    return {"styles": STYLE_LIST, "default": DEFAULT_STYLE_ID}


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "remotion"}
