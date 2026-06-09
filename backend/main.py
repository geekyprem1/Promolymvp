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
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright
from pydantic import BaseModel

load_dotenv()

from detector import detect_sections, extract_page_meta
from ai import generate_storyboard, build_remotion_props, scenes_for_duration
from remotion_bridge import render_remotion_video

BASE_DIR        = Path(__file__).parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
OUTPUT_DIR      = BASE_DIR / "output"

SCREENSHOTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

progress_store: dict[str, dict] = {}

FPS = 30

# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(title="Promoly API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/output",      StaticFiles(directory=str(OUTPUT_DIR)),      name="output")
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")


class GenerateRequest(BaseModel):
    url: str
    session_id: str | None  = None
    target_duration: int    = 20
    gemini_api_key: str | None = None


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
) -> dict:
    session_dir = SCREENSHOTS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{session_id}.mp4"

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
        await ctx.close()
        await browser.close()

    if not sections:
        raise HTTPException(status_code=500, detail="No sections detected on page.")

    # ── STEP 2: AI storyboard ─────────────────────────────────────────────────
    _set(session_id, "analyzing", 42, "Gemini AI analysing website…")
    raw_board = await generate_storyboard(meta, sections, target_duration, api_key)

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

    # Cleanup screenshots
    shutil.rmtree(session_dir, ignore_errors=True)

    n         = len(remotion_props.get("scenes", []))
    total_dur = round(n * 5.0, 1)   # 150 frames / 30 fps = 5s per scene
    ai_used   = raw_board.get("ai_used", False)

    _set(session_id, "done", 100, "Video ready!")

    return {
        "status":     "success",
        "video":      f"output/{session_id}.mp4",
        "session_id": session_id,
        "duration":   total_dur,
        "resolution": "1920×1080",
        "fps":        FPS,
        "scenes":     n,
        "ai_used":    ai_used,
        "storyboard": {
            "website_type": remotion_props.get("websiteType", "saas"),
            "video_style":  remotion_props.get("videoStyle",  "explainer"),
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
        return await run_pipeline(url, sid, req.target_duration, api_key)
    except HTTPException:
        raise
    except Exception as exc:
        progress_store.pop(sid, None)
        raise HTTPException(status_code=500, detail=str(exc)[:400])


@app.get("/progress/{session_id}")
async def get_progress(session_id: str):
    return progress_store.get(session_id, {"stage": "pending", "pct": 0, "message": ""})


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "remotion"}
