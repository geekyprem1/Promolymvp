"""
main.py – Promoly FastAPI backend.

Pipeline:
  URL → Playwright DOM detection → Gemini AI storyboard
      → HTML scene renderer → FFmpeg Ken Burns + xfade → MP4
"""
from __future__ import annotations

import asyncio
import glob as _glob
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

load_dotenv()  # reads backend/.env if present

from detector import detect_sections, extract_page_meta
from ai import generate_storyboard
from renderer import render_all_scenes

BASE_DIR       = Path(__file__).parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
OUTPUT_DIR     = BASE_DIR / "output"
ASSETS_DIR     = BASE_DIR / "assets"
MUSIC_FILE     = ASSETS_DIR / "music.mp3"

SCREENSHOTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

progress_store: dict[str, dict] = {}

# ─── Tool detection ───────────────────────────────────────────────────────────

def find_ffmpeg() -> str:
    machine_path = user_path = ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as k:
            machine_path = winreg.QueryValueEx(k, "Path")[0]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            user_path = winreg.QueryValueEx(k, "PATH")[0]
    except Exception:
        pass
    full = machine_path + ";" + user_path
    found = shutil.which("ffmpeg", path=full) or shutil.which("ffmpeg")
    if found:
        return found
    for pattern in [
        os.path.expanduser(r"~\AppData\Local\ms-playwright\ffmpeg-*\ffmpeg-win64.exe"),
        os.path.expanduser("~/.cache/ms-playwright/ffmpeg-*/ffmpeg"),
    ]:
        hits = _glob.glob(pattern)
        if hits:
            return hits[-1]
    raise RuntimeError("FFmpeg not found. Install from https://ffmpeg.org/download.html")


FFMPEG = find_ffmpeg()

# ─── Video constants ──────────────────────────────────────────────────────────

FPS            = 30
SCENE_DURATION = 4.0
TRANSITION_DUR = 0.5
_NF            = int(SCENE_DURATION * FPS) - 1   # 119

# Ken Burns patterns (scale+crop on 1920×1080 designed frames)
KEN_BURNS = [
    f"scale=2304:1296,crop=w='1920+384*(1-n/{_NF})':h='1080+216*(1-n/{_NF})':x='(2304-ow)/2':y='(1296-oh)/2',scale=1920:1080:flags=lanczos",
    f"scale=2304:1296,crop=w='1920+384*n/{_NF}':h='1080+216*n/{_NF}':x='(2304-ow)/2':y='(1296-oh)/2',scale=1920:1080:flags=lanczos",
    f"scale=2208:1242,crop=1920:1080:x='round(288*n/{_NF})':y='(1242-1080)/2',scale=1920:1080:flags=lanczos",
    f"scale=2208:1242,crop=1920:1080:x='round(288*(1-n/{_NF}))':y='(1242-1080)/2',scale=1920:1080:flags=lanczos",
    f"scale=2304:1296,crop=w='1920+384*(1-n/{_NF})':h='1080+216*(1-n/{_NF})':x='0':y='0',scale=1920:1080:flags=lanczos",
    f"scale=2304:1296,crop=w='1920+384*(1-n/{_NF})':h='1080+216*(1-n/{_NF})':x='2304-ow':y='0',scale=1920:1080:flags=lanczos",
]

XFADE_TRANSITIONS = ["fade", "slideleft", "slideright", "zoomin", "fadeblack"]

ANIMATION_KB_MAP = {
    "zoom_in":        0,
    "zoom_out":       1,
    "pan_left":       2,
    "pan_right":      3,
    "diagonal_motion":4,
    "fade":           0,
    "slide":          2,
}

# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(title="Promoly API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


class GenerateRequest(BaseModel):
    url: str
    session_id: str | None = None
    target_duration: int   = 20
    gemini_api_key: str | None = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

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


# ─── FFmpeg video assembly ────────────────────────────────────────────────────

def _build_video_cmd(
    frame_paths: list[Path],
    animations: list[str],
    output_path: Path,
) -> list[str]:
    n = len(frame_paths)
    td = TRANSITION_DUR

    cmd = [FFMPEG, "-y"]
    for p in frame_paths:
        cmd += ["-framerate", str(FPS), "-loop", "1",
                "-t", str(SCENE_DURATION + 1), "-i", str(p)]

    music_idx = n if MUSIC_FILE.exists() else None
    if music_idx is not None:
        cmd += ["-i", str(MUSIC_FILE)]

    parts: list[str] = []

    # Per-scene Ken Burns
    for i, anim in enumerate(animations):
        kb_idx = ANIMATION_KB_MAP.get(anim, i % len(KEN_BURNS))
        kb = KEN_BURNS[kb_idx % len(KEN_BURNS)]
        parts.append(
            f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,setsar=1,format=yuv420p,fps={FPS},setpts=PTS-STARTPTS,"
            f"{kb}[kb{i}];"
        )

    # xfade chain
    for i in range(n - 1):
        trans  = XFADE_TRANSITIONS[i % len(XFADE_TRANSITIONS)]
        offset = round((i + 1) * (SCENE_DURATION - td), 3)
        src_a  = "kb0" if i == 0 else f"xf{i-1}_{i}"
        dst    = f"xf{i}_{i+1}"
        parts.append(f"[{src_a}][kb{i+1}]xfade=transition={trans}:duration={td}:offset={offset}[{dst}];")

    final = f"xf{n-2}_{n-1}" if n > 1 else "kb0"
    parts.append(f"[{final}]copy[outv]")

    cmd += ["-filter_complex", "".join(parts), "-map", "[outv]"]

    if music_idx is not None:
        cmd += ["-map", f"{music_idx}:a", "-shortest", "-c:a", "aac", "-b:a", "192k"]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-profile:v", "high", "-level:v", "4.2",
        str(output_path),
    ]
    return cmd


async def _run_ffmpeg(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    if proc.returncode != 0:
        raise HTTPException(status_code=500,
                            detail=f"FFmpeg error: {stderr.decode()[-600:]}")


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

    async with async_playwright() as pw:
        browser = await _launch_browser(pw)

        # ── STEP 1: Website visit + section detection ─────────────────────────
        _set(session_id, "capturing", 10, "Loading website…")
        ctx  = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        meta = await extract_page_meta(page)

        from ai import scenes_for_duration
        max_sc = scenes_for_duration(target_duration)

        def _cap_cb(pct: int, msg: str):
            _set(session_id, "capturing", pct, msg)

        sections = await detect_sections(page, session_dir, max_sections=max(max_sc + 2, 7),
                                         progress_cb=_cap_cb)
        await ctx.close()

        if not sections:
            await browser.close()
            raise HTTPException(status_code=500, detail="No sections detected on page.")

        sections_map = {s.section_type: s for s in sections}

        # ── STEP 2: AI storyboard ─────────────────────────────────────────────
        _set(session_id, "analyzing", 42, "Gemini AI analyzing website…")
        storyboard = await generate_storyboard(meta, sections, target_duration, api_key)

        # ── STEP 3: Render designed scenes ───────────────────────────────────
        _set(session_id, "rendering", 55, "Rendering scenes…")

        def _rend_cb(pct: int, msg: str):
            _set(session_id, "rendering", pct, msg)

        frame_paths = await render_all_scenes(
            storyboard, sections_map, meta, session_dir, browser,
            progress_cb=_rend_cb,
        )

        await browser.close()

    if not frame_paths:
        raise HTTPException(status_code=500, detail="Scene rendering produced no frames.")

    # ── STEP 4: FFmpeg encode ─────────────────────────────────────────────────
    _set(session_id, "encoding", 82, "Encoding video with FFmpeg…")
    animations = [sc.get("animation", "zoom_in") for sc in storyboard.get("scenes", [])]
    cmd = _build_video_cmd(frame_paths, animations, output_path)
    await _run_ffmpeg(cmd)

    shutil.rmtree(session_dir, ignore_errors=True)

    n = len(frame_paths)
    total_dur = round(n * SCENE_DURATION - (n - 1) * TRANSITION_DUR, 1)
    _set(session_id, "done", 100, "Video ready!")

    return {
        "status":     "success",
        "video":      f"output/{session_id}.mp4",
        "session_id": session_id,
        "duration":   total_dur,
        "resolution": "1920×1080",
        "fps":        FPS,
        "scenes":     n,
        "ai_used":    storyboard.get("ai_used", False),
        "storyboard": storyboard,
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
    return {"status": "ok", "ffmpeg": FFMPEG}
