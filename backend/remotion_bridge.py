"""
remotion_bridge.py – Python → Remotion render bridge.

Serialises the storyboard JSON (with screenshot HTTP URLs) to disk,
then shells out to `npx remotion render` and returns the output MP4 path.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

REMOTION_DIR = Path(__file__).parent.parent / "remotion"

# Chrome executable candidates (checked in order)
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Users\{user}\AppData\Local\Google\Chrome\Application\chrome.exe",
    r"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"/usr/bin/google-chrome",
    r"/usr/bin/chromium-browser",
]


def _find_npx() -> str:
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx not found. Make sure Node.js is installed and in PATH.")
    return npx


def _find_chrome() -> str | None:
    """Find an installed Chrome/Chromium executable."""
    import os
    import getpass
    for candidate in CHROME_CANDIDATES:
        # Expand {user} placeholder
        candidate = candidate.replace("{user}", getpass.getuser())
        if Path(candidate).exists():
            return candidate
    return None


async def render_remotion_video(
    storyboard: dict,
    output_path: Path,
    session_id: str,
    fps: int = 30,
    progress_cb=None,
) -> Path:
    """
    Render a Remotion composition to MP4.

    Args:
        storyboard:  PromoVideoProps dict (scenes with screenshotUrl already set).
        output_path: Where to write the final .mp4.
        session_id:  Used for the props file name.
        fps:         Frames per second (default 30).
        progress_cb: Optional async callable(pct, msg).

    Returns:
        output_path on success.
    """
    props_file = REMOTION_DIR / f"props_{session_id}.json"
    props_file.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")

    npx   = _find_npx()
    chrome = _find_chrome()

    cmd = [
        npx, "remotion", "render",
        "PromoVideo",
        str(output_path),
        "--props", str(props_file),
        "--fps", str(fps),
        "--width", "1920",
        "--height", "1080",
        "--codec", "h264",
        "--crf", "18",
        "--log", "error",
        "--concurrency", "4",
    ]
    if chrome:
        cmd += ["--browser-executable", chrome]
        log.info("Using Chrome: %s", chrome)

    log.info("Starting Remotion render: %s → %s", session_id, output_path)
    if progress_cb:
        await progress_cb(55, "Remotion rendering scenes…")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(REMOTION_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Stream stderr for progress
    frames_rendered = 0
    total_frames = sum(s.get("durationInFrames", 120) for s in storyboard.get("scenes", []))

    async def _stream_stderr():
        nonlocal frames_rendered
        assert proc.stderr
        async for line in proc.stderr:
            decoded = line.decode(errors="replace").strip()
            if decoded:
                log.debug("remotion: %s", decoded)
                # Parse Remotion progress lines like "Rendered 45/120 frames"
                if "Rendered" in decoded and "/" in decoded:
                    try:
                        parts = decoded.split()
                        for p in parts:
                            if "/" in p:
                                n, t = p.split("/")
                                frames_rendered = int(n)
                                total = int(t.rstrip(","))
                                if progress_cb and total > 0:
                                    pct = 55 + int((frames_rendered / total) * 25)
                                    await progress_cb(pct, f"Rendering frame {frames_rendered}/{total}…")
                                break
                    except Exception:
                        pass

    try:
        await asyncio.gather(
            asyncio.wait_for(proc.wait(), timeout=600),
            _stream_stderr(),
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("Remotion render timed out after 10 minutes.")

    if proc.returncode != 0:
        stderr_out = b""
        if proc.stderr:
            try:
                stderr_out = await proc.stderr.read()
            except Exception:
                pass
        raise RuntimeError(f"Remotion render failed (exit {proc.returncode}):\n{stderr_out.decode(errors='replace')[-800:]}")

    # Cleanup props file
    props_file.unlink(missing_ok=True)

    log.info("Remotion render complete → %s", output_path)
    if progress_cb:
        await progress_cb(82, "Render complete, finalising…")

    return output_path
