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

# Windows: force ProactorEventLoop BEFORE uvicorn touches the event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)

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
from scene_designer import design_scenes
from metrics_extractor import build_metrics
from visual_intelligence import build_visual_inventory

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


KOKORO_VALID_VOICES = {
    "af_heart", "af_nova", "af_sky", "af_bella", "af_jessica", "af_sarah",
    "am_echo", "am_michael", "am_liam", "bm_george", "bm_daniel",
}

class GenerateRequest(BaseModel):
    url: str
    session_id: str | None  = None
    target_duration: int    = 20
    gemini_api_key: str | None = None
    template_id: str | None = None
    video_style: str | None = None   # "hybrid" (default) | "website-showcase" | "motion-graphics"
    kokoro_voice: str | None = None  # Kokoro TTS voice ID (default: af_heart)


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
    kokoro_voice: str | None = None,
) -> dict:
    session_dir    = SCREENSHOTS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    output_path    = OUTPUT_DIR / f"{session_id}.mp4"
    visual_elements: list = []
    ranked_metrics:  list = []

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

        # ── Metric extraction (same browser session — needs live DOM) ──────────
        _set(session_id, "capturing", 39, "Extracting metrics…")
        try:
            ranked_metrics = await build_metrics(page, sections)
        except Exception as e:
            print(f"[VIE] Metric extraction failed (non-fatal): {e}", flush=True)
            ranked_metrics = []

        await ctx.close()
        await browser.close()

    if not sections:
        raise HTTPException(status_code=500, detail="No sections detected on page.")

    # ── Build Visual Inventory from all extracted data ────────────────────────
    _set(session_id, "analyzing", 40, "Building visual inventory…")
    try:
        inventory = build_visual_inventory(sections, visual_elements, ranked_metrics)
    except Exception as e:
        print(f"[VIE] Inventory build failed (non-fatal): {e}", flush=True)
        inventory = None

    # ── STEP 2: Story extraction ──────────────────────────────────────────────
    _set(session_id, "analyzing", 41, "Extracting product story…")
    story = extract_story(meta, sections)
    print(
        f"[Story] problem={bool(story.problem)} solution={bool(story.solution)} "
        f"benefits={len(story.benefits)} proof={len(story.social_proof)} "
        f"rich={story.is_rich()}",
        flush=True,
    )

    # ── STEP 3: AI storyboard ─────────────────────────────────────────────────
    _set(session_id, "analyzing", 42, "Gemini AI writing video script…")
    raw_board = await generate_storyboard(meta, sections, target_duration, api_key, story=story, inventory=inventory)

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

    # ── STEP 3c.5: Scene Designer ─────────────────────────────────────────────
    _set(session_id, "rendering", 52, "Designing scenes…")
    remotion_props = design_scenes(remotion_props, inventory=inventory)

    # ── STEP 3c.6: Hybrid Screenshot Overrides ───────────────────────────────
    if inventory is not None:
        try:
            hints = inventory.to_scene_hints()
            dash_url  = hints.get("dashboard_screenshot")
            price_url = hints.get("pricing_screenshot")
            cta_url   = hints.get("cta_screenshot")
            def _full_url(rel):
                return f"{base_url}/{rel}" if rel and not rel.startswith("http") else rel

            updated = []
            for s in remotion_props.get("scenes", []):
                stype = s.get("type", "")
                if stype in ("features", "solution") and dash_url and not s.get("screenshotUrl"):
                    s = {**s, "screenshotUrl": _full_url(dash_url)}
                elif stype == "pricing" and price_url and not s.get("screenshotUrl"):
                    s = {**s, "screenshotUrl": _full_url(price_url)}
                elif stype == "cta" and cta_url and not s.get("screenshotUrl"):
                    s = {**s, "screenshotUrl": _full_url(cta_url)}
                updated.append(s)
            remotion_props = {**remotion_props, "scenes": updated}
        except Exception as e:
            print(f"[VIE] Hybrid screenshot override failed (non-fatal): {e}", flush=True)

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

    # ── STEP 6: Voiceover (Kokoro via OpenRouter) ────────────────────────────
    # Use request-provided key first (user's browser key), then env fallback
    openrouter_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY")
    voice = kokoro_voice if kokoro_voice in KOKORO_VALID_VOICES else "af_heart"
    vo_path = None
    if openrouter_key:
        _set(session_id, "rendering", 86, f"Generating voiceover ({voice})…")
        vo_provider = get_voiceover_provider(
            "kokoro",
            api_key    = openrouter_key,
            output_dir = OUTPUT_DIR,
            voice      = voice,
        )
        _scenes = remotion_props.get("scenes", [])
        narrations = [
            s.get("narration", "").strip()
            for s in _scenes
            if s.get("narration", "").strip()
        ]
        # Fallback: Gemini ne narration nahi diya — headline+subheadline se banao
        if not narrations:
            print("[Voiceover] No narration from AI — building from headlines", flush=True)
            for s in _scenes:
                h  = s.get("headline", "").strip()
                sh = s.get("subheadline", "").strip()
                line = f"{h}. {sh}" if sh else h
                if line.strip():
                    narrations.append(line[:120])
        print(f"[Voiceover] {len(narrations)} narration lines across {len(_scenes)} scenes", flush=True)
        script = ". ".join(narrations)

        if script:
            try:
                vo_path = await vo_provider.generate_voiceover(
                    script,
                    output_path = OUTPUT_DIR / f"{session_id}_vo.mp3",
                )
                print(f"[Voiceover] vo_path = {vo_path}", flush=True)
            except Exception as e:
                print(f"[Voiceover] Exception (non-fatal): {type(e).__name__}: {e}", flush=True)
                vo_path = None
        else:
            print("[Voiceover] Script is empty — no narration in scenes", flush=True)
    else:
        print("[Voiceover] No OPENROUTER_API_KEY found — skipping voiceover.", flush=True)

    # ── STEP 7: Audio mixing ──────────────────────────────────────────────────
    print(f"[Audio] music={music_info.get('musicPath')}  vo={vo_path}", flush=True)
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
            req.template_id, req.video_style, req.kokoro_voice,
        )
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] {tb}", flush=True)
        progress_store.pop(sid, None)
        raise HTTPException(status_code=500, detail=tb[-600:])


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


class VoiceTestRequest(BaseModel):
    api_key: str
    text: str = "Hello, this is a voiceover test from Promoly."
    voice: str = "af_heart"

@app.post("/test-voice")
async def test_voice(req: VoiceTestRequest):
    """Quick endpoint to test Kokoro TTS without running the full pipeline."""
    import httpx
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="api_key required")
    voice = req.voice if req.voice in KOKORO_VALID_VOICES else "af_heart"
    payload = {"model": "hexgrad/kokoro-82m", "input": req.text, "voice": voice}
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://promoly.app",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/audio/speech",
                headers=headers, json=payload,
            )
        ct = resp.headers.get("content-type", "")
        if resp.status_code != 200 or "json" in ct:
            return {
                "ok": False,
                "status": resp.status_code,
                "content_type": ct,
                "error": resp.text[:400],
            }
        out = OUTPUT_DIR / "voice_test.mp3"
        out.write_bytes(resp.content)
        return {
            "ok": True,
            "bytes": len(resp.content),
            "content_type": ct,
            "audio_url": f"/output/voice_test.mp3",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, loop="none")
