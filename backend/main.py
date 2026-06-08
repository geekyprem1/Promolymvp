import asyncio
import glob as _glob
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
MUSIC_FILE = ASSETS_DIR / "music.mp3"

SCREENSHOTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory progress store keyed by session_id
progress_store: dict[str, dict] = {}

# ─── Tool detection ───────────────────────────────────────────────────────────

def find_ffmpeg() -> str:
    machine_path = ""
    user_path = ""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ) as k:
            machine_path = winreg.QueryValueEx(k, "Path")[0]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            user_path = winreg.QueryValueEx(k, "PATH")[0]
    except Exception:
        pass
    full_path = machine_path + ";" + user_path
    found = shutil.which("ffmpeg", path=full_path) or shutil.which("ffmpeg")
    if found:
        return found
    for pattern in [
        os.path.expanduser(r"~\AppData\Local\ms-playwright\ffmpeg-*\ffmpeg-win64.exe"),
        os.path.expanduser("~/.cache/ms-playwright/ffmpeg-*/ffmpeg"),
    ]:
        matches = _glob.glob(pattern)
        if matches:
            return matches[-1]
    raise RuntimeError("FFmpeg not found. Install from https://ffmpeg.org/download.html")


def find_font() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\verdanab.ttf",
    ]
    for f in candidates:
        if Path(f).exists():
            return f
    return None


FFMPEG = find_ffmpeg()
FONT_PATH = find_font()

# ─── Video constants ───────────────────────────────────────────────────────────

FPS = 30
SCENE_DURATION = 4.0        # seconds per scene
TRANSITION_DURATION = 0.5   # xfade overlap
FRAMES_PER_SCENE = int(SCENE_DURATION * FPS)   # 120
_NF = FRAMES_PER_SCENE - 1  # 119  (max frame index for crop expressions)

# Ken Burns via scale+crop for 1920×1080 (16:9 landscape).
# Upscale to 1.2× (2304×1296) or 1.15× (2208×1242), then animated crop back to 1920×1080.
# `n` is 0-indexed frame counter (0 → _NF).
KEN_BURNS = [
    # 0 – slow zoom in from center  (1.0 → 1.2×)
    f"scale=2304:1296,"
    f"crop=w='1920+384*(1-n/{_NF})':h='1080+216*(1-n/{_NF})':x='(2304-ow)/2':y='(1296-oh)/2',"
    f"scale=1920:1080:flags=lanczos",
    # 1 – slow zoom out from center (1.2 → 1.0×)
    f"scale=2304:1296,"
    f"crop=w='1920+384*n/{_NF}':h='1080+216*n/{_NF}':x='(2304-ow)/2':y='(1296-oh)/2',"
    f"scale=1920:1080:flags=lanczos",
    # 2 – pan left → right (1.15×)
    f"scale=2208:1242,"
    f"crop=1920:1080:x='round(288*n/{_NF})':y='(1242-1080)/2',"
    f"scale=1920:1080:flags=lanczos",
    # 3 – pan right → left (1.15×)
    f"scale=2208:1242,"
    f"crop=1920:1080:x='round(288*(1-n/{_NF}))':y='(1242-1080)/2',"
    f"scale=1920:1080:flags=lanczos",
    # 4 – diagonal zoom in, top-left anchor
    f"scale=2304:1296,"
    f"crop=w='1920+384*(1-n/{_NF})':h='1080+216*(1-n/{_NF})':x='0':y='0',"
    f"scale=1920:1080:flags=lanczos",
    # 5 – zoom in, top-right anchor
    f"scale=2304:1296,"
    f"crop=w='1920+384*(1-n/{_NF})':h='1080+216*(1-n/{_NF})':x='2304-ow':y='0',"
    f"scale=1920:1080:flags=lanczos",
]

XFADE_TRANSITIONS = ["fade", "slideleft", "slideright", "zoomin", "fadeblack"]

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Promoly API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


class GenerateRequest(BaseModel):
    url: str
    session_id: str | None = None
    target_duration: int = 20   # seconds, 8–30


# ─── Helpers ──────────────────────────────────────────────────────────────────

def validate_url(url: str) -> bool:
    pattern = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|\d{1,3}(?:\.\d{1,3}){3})"
        r"(?::\d+)?(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return bool(pattern.match(url))


def set_progress(sid: str, stage: str, pct: int, message: str = "") -> None:
    progress_store[sid] = {"stage": stage, "pct": pct, "message": message}


async def _launch_browser(p):
    for channel in ("chrome", "msedge"):
        try:
            return await p.chromium.launch(headless=True, channel=channel)
        except Exception:
            continue
    return await p.chromium.launch(headless=True)


# ─── Screenshot capture ───────────────────────────────────────────────────────

SECTION_SELECTORS = [
    # Hero
    ['[class*="hero"]', '[class*="banner"]', '[id*="hero"]', 'header'],
    # Features / Benefits
    ['[class*="feature"]', '[id*="feature"]', '[class*="benefit"]', '[class*="how"]'],
    # Social proof
    ['[class*="testimonial"]', '[class*="review"]', '[class*="trust"]', '[class*="customer"]'],
    # Pricing
    ['[class*="pricing"]', '[id*="pricing"]', '[class*="plan"]', '[id*="plan"]'],
    # CTA
    ['[class*="cta"]', '[class*="call-to-action"]', '[class*="get-started"]', '[class*="signup"]'],
    # Footer
    ['footer', '[class*="footer"]'],
]


async def detect_sections(page) -> list[int]:
    selectors_json = json.dumps(SECTION_SELECTORS)
    scroll_ys: list[int] = await page.evaluate(f"""
    () => {{
        const selectorGroups = {selectors_json};
        const totalH = document.documentElement.scrollHeight;
        const viewH   = window.innerHeight;
        const positions = [];
        const used = [[-300, 300]];   // hero at 0 is always first

        const unique = (y) => used.every(([lo, hi]) => y < lo || y > hi);

        positions.push(0);

        for (const group of selectorGroups) {{
            for (const sel of group) {{
                try {{
                    const els = [...document.querySelectorAll(sel)];
                    for (const el of els) {{
                        const rect = el.getBoundingClientRect();
                        const absY = Math.max(0, Math.min(
                            Math.floor(rect.top + window.scrollY),
                            totalH - viewH
                        ));
                        if (unique(absY) && el.offsetHeight > 80) {{
                            positions.push(absY);
                            used.push([absY - 200, absY + 200]);
                            break;
                        }}
                    }}
                    if (positions.length > 6) break;
                }} catch(e) {{}}
            }}
            if (positions.length > 6) break;
        }}

        // Fallback percentage positions
        for (const pct of [15, 25, 40, 55, 70, 82, 92, 98]) {{
            if (positions.length >= 8) break;
            const y = Math.floor((totalH - viewH) * pct / 100);
            if (y > 0 && unique(y)) {{
                positions.push(y);
                used.push([y - 200, y + 200]);
            }}
        }}

        return positions.sort((a, b) => a - b).slice(0, 8);
    }}
    """)
    return scroll_ys


async def extract_page_text(page) -> dict:
    return await page.evaluate("""
    () => {
        const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
        const trunc = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;
        return {
            title:       trunc(clean(document.title), 60),
            h1:          trunc(clean(document.querySelector('h1')?.innerText), 60),
            h2:          trunc(clean(document.querySelector('h2')?.innerText), 70),
            og_title:    trunc(clean(document.querySelector('meta[property="og:title"]')?.content), 60),
            description: trunc(clean(document.querySelector('meta[name="description"]')?.content), 80),
        };
    }
    """)


async def capture_screenshots(url: str, session_id: str, max_scenes: int = 6) -> tuple[list[Path], dict]:
    session_dir = SCREENSHOTS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    async with async_playwright() as p:
        browser = await _launch_browser(p)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page = await ctx.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        await page.wait_for_timeout(2000)

        page_text = await extract_page_text(page)
        set_progress(session_id, "capturing", 20, "Detecting page sections…")

        scroll_positions = (await detect_sections(page))[:max_scenes]

        for i, scroll_y in enumerate(scroll_positions):
            await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
            await page.wait_for_timeout(900)
            path = session_dir / f"shot_{i:02d}.png"
            await page.screenshot(path=str(path), full_page=False)
            paths.append(path)
            pct = 20 + int((i + 1) / len(scroll_positions) * 30)
            set_progress(session_id, "capturing", pct, f"Screenshot {i+1}/{len(scroll_positions)}")

        await browser.close()

    return paths, page_text


# ─── FFmpeg video builder ─────────────────────────────────────────────────────

def _esc_text(s: str) -> str:
    """Escape a string for use inside FFmpeg drawtext value."""
    return (s
            .replace("\\", "\\\\")
            .replace("'",  "\\'")
            .replace(":",  "\\:")
            .replace("[",  "\\[")
            .replace("]",  "\\]")
            .replace(",",  "\\,"))


def _font_path_ffmpeg(p: str) -> str:
    """Convert Windows path to FFmpeg-safe font path."""
    return p.replace("\\", "/").replace(":", "\\:")


def _fade_alpha(t_in: float, t_out: float, fade: float = 0.4) -> str:
    """Return an FFmpeg alpha expression that fades in and out."""
    t_fi = t_in + fade
    t_fo = t_out + fade
    return (
        f"if(lt(t,{t_in}),0,"
        f"if(lt(t,{t_fi}),(t-{t_in})/{fade},"
        f"if(lt(t,{t_out}),1,"
        f"if(lt(t,{t_fo}),({t_fo}-t)/{fade},0))))"
    )


def build_video_command(
    screenshot_paths: list[Path],
    output_path: Path,
    page_text: dict,
) -> list[str]:
    n = len(screenshot_paths)
    td = TRANSITION_DURATION

    cmd = [FFMPEG, "-y"]

    # One still-image input per scene (slightly over-length for zoompan buffer)
    for path in screenshot_paths:
        cmd += ["-framerate", str(FPS), "-loop", "1", "-t", str(SCENE_DURATION + 1), "-i", str(path)]

    music_idx = n if MUSIC_FILE.exists() else None
    if music_idx is not None:
        cmd += ["-i", str(MUSIC_FILE)]

    parts: list[str] = []

    # ── Per-scene: scale → Ken Burns ──────────────────────────────────────────
    for i in range(n):
        kb = KEN_BURNS[i % len(KEN_BURNS)]
        parts.append(
            f"[{i}:v]"
            f"scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,setsar=1,format=yuv420p,fps={FPS},setpts=PTS-STARTPTS,"
            f"{kb}"
            f"[kb{i}];"
        )

    # ── xfade chain ───────────────────────────────────────────────────────────
    # offset(i) = (i+1) * (SCENE_DURATION - td)
    for i in range(n - 1):
        trans = XFADE_TRANSITIONS[i % len(XFADE_TRANSITIONS)]
        offset = round((i + 1) * (SCENE_DURATION - td), 3)
        src_a = "kb0" if i == 0 else f"xf{i-1}_{i}"
        src_b = f"kb{i+1}"
        dst   = f"xf{i}_{i+1}"
        parts.append(
            f"[{src_a}][{src_b}]"
            f"xfade=transition={trans}:duration={td}:offset={offset}"
            f"[{dst}];"
        )

    assembled = f"xf{n-2}_{n-1}"

    # ── Vignette (cinematic dark edges) ───────────────────────────────────────
    parts.append(f"[{assembled}]vignette=angle=PI/5[vig];")
    final_stream = "vig"

    # ── Text overlays ─────────────────────────────────────────────────────────
    total_dur = SCENE_DURATION * n - td * (n - 1)

    if FONT_PATH:
        fp = _font_path_ffmpeg(FONT_PATH)

        primary = _esc_text(
            page_text.get("og_title") or page_text.get("h1") or page_text.get("title") or ""
        )
        secondary = _esc_text(
            page_text.get("h2") or page_text.get("description") or ""
        )

        if primary:
            t_in, t_out = 1.5, min(6.0, total_dur - 1.5)
            alpha = _fade_alpha(t_in, t_out)
            parts.append(
                f"[{final_stream}]drawtext="
                f"fontfile='{fp}':"
                f"text='{primary}':"
                f"fontsize=54:fontcolor=white:"
                f"x=(w-text_w)/2:y=h*0.80:"
                f"shadowcolor=black@0.75:shadowx=3:shadowy=3:"
                f"alpha='{alpha}':"
                f"enable='between(t,{t_in},{t_out+0.5})'"
                f"[tx1];"
            )
            final_stream = "tx1"

        if secondary and secondary != primary:
            t_in2 = min(8.5, total_dur * 0.42)
            t_out2 = min(t_in2 + 5.0, total_dur - 1.5)
            alpha2 = _fade_alpha(t_in2, t_out2)
            parts.append(
                f"[{final_stream}]drawtext="
                f"fontfile='{fp}':"
                f"text='{secondary}':"
                f"fontsize=36:fontcolor=white@0.9:"
                f"x=(w-text_w)/2:y=h*0.87:"
                f"shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                f"alpha='{alpha2}':"
                f"enable='between(t,{t_in2},{t_out2+0.5})'"
                f"[tx2];"
            )
            final_stream = "tx2"

    # Final output label
    parts.append(f"[{final_stream}]copy[outv]")

    filter_complex = "".join(parts)
    cmd += ["-filter_complex", filter_complex, "-map", "[outv]"]

    if music_idx is not None:
        cmd += ["-map", f"{music_idx}:a", "-shortest", "-c:a", "aac", "-b:a", "192k"]

    cmd += [
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-profile:v", "high",
        "-level:v", "4.2",
        str(output_path),
    ]
    return cmd


def build_fallback_command(screenshot_paths: list[Path], output_path: Path) -> list[str]:
    """Simple concat fallback when advanced filters fail."""
    n = len(screenshot_paths)
    cmd = [FFMPEG, "-y"]
    for path in screenshot_paths:
        cmd += ["-loop", "1", "-t", str(SCENE_DURATION), "-i", str(path)]

    music_idx = n if MUSIC_FILE.exists() else None
    if music_idx is not None:
        cmd += ["-i", str(MUSIC_FILE)]

    fp: list[str] = []
    for i in range(n):
        fp.append(
            f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,setsar=1,format=yuv420p,fps={FPS}[v{i}];"
        )
    inputs = "".join(f"[v{i}]" for i in range(n))
    fp.append(f"{inputs}concat=n={n}:v=1:a=0[outv]")

    cmd += ["-filter_complex", "".join(fp), "-map", "[outv]"]
    if music_idx is not None:
        cmd += ["-map", f"{music_idx}:a", "-shortest", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)]
    return cmd


async def create_video(
    screenshot_paths: list[Path],
    session_id: str,
    page_text: dict,
) -> Path:
    output_path = OUTPUT_DIR / f"{session_id}.mp4"
    set_progress(session_id, "generating", 55, "Applying Ken Burns & transitions…")

    cmd = build_video_command(screenshot_paths, output_path, page_text)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

    if proc.returncode != 0:
        set_progress(session_id, "generating", 60, "Retrying with simplified pipeline…")
        cmd_fb = build_fallback_command(screenshot_paths, output_path)
        proc2 = await asyncio.create_subprocess_exec(
            *cmd_fb,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr2 = await asyncio.wait_for(proc2.communicate(), timeout=300)
        if proc2.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"FFmpeg failed: {stderr2.decode()[-600:]}",
            )

    set_progress(session_id, "done", 100, "Video ready!")
    return output_path


# ─── API endpoints ────────────────────────────────────────────────────────────

@app.post("/generate")
async def generate_video(req: GenerateRequest):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not validate_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL provided.")

    session_id = req.session_id or uuid.uuid4().hex
    target = max(8, min(30, req.target_duration))

    # How many scenes fit in target_duration?
    # actual_duration = n * SCENE_DURATION - (n-1) * TRANSITION_DURATION
    # Solving for n: n = (target + TRANSITION_DURATION) / (SCENE_DURATION - TRANSITION_DURATION + 1... )
    # Simple: try n from 2..8 and pick largest that fits
    max_scenes = 2
    for n in range(2, 9):
        dur = n * SCENE_DURATION - (n - 1) * TRANSITION_DURATION
        if dur <= target:
            max_scenes = n

    set_progress(session_id, "validating", 5, "Validating URL…")

    try:
        screenshot_paths, page_text = await capture_screenshots(url, session_id, max_scenes=max_scenes)
    except Exception as e:
        progress_store.pop(session_id, None)
        raise HTTPException(status_code=500, detail=f"Screenshot capture failed: {str(e)[:300]}")

    if not screenshot_paths:
        raise HTTPException(status_code=500, detail="No screenshots were captured.")

    set_progress(session_id, "generating", 52, "Starting video render…")

    try:
        await create_video(screenshot_paths, session_id, page_text)
    except HTTPException:
        progress_store.pop(session_id, None)
        raise
    except Exception as e:
        progress_store.pop(session_id, None)
        raise HTTPException(status_code=500, detail=f"Video creation failed: {str(e)[:300]}")
    finally:
        shutil.rmtree(SCREENSHOTS_DIR / session_id, ignore_errors=True)

    n = len(screenshot_paths)
    total_dur = round(n * SCENE_DURATION - (n - 1) * TRANSITION_DURATION, 1)

    return {
        "status": "success",
        "video": f"output/{session_id}.mp4",
        "session_id": session_id,
        "duration": total_dur,
        "resolution": "1920×1080",
        "fps": FPS,
        "scenes": n,
        "page_text": page_text,
    }


@app.get("/progress/{session_id}")
async def get_progress(session_id: str):
    return progress_store.get(session_id, {"stage": "pending", "pct": 0, "message": ""})


@app.get("/health")
async def health():
    return {"status": "ok", "ffmpeg": FFMPEG, "font": FONT_PATH}
