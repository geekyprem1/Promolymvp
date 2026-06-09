"""
renderer.py – HTML-template-based scene renderer.

Each scene is rendered as a 1920×1080 PNG by:
  1. Building a self-contained HTML page (screenshot embedded as base64).
  2. Loading it in a headless Playwright page.
  3. Taking a full screenshot → saved as a designed PNG frame.

FFmpeg then applies Ken Burns motion + xfade transitions to these frames.
"""
from __future__ import annotations

import asyncio
import base64
import io
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from detector import SectionData

W, H = 1920, 1080

# ─── Design tokens (shared CSS vars used in every template) ───────────────────

SHARED_CSS = """
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg:            #070712;
    --bg2:           #0d0d1f;
    --surface:       rgba(255,255,255,0.04);
    --border:        rgba(255,255,255,0.08);
    --text:          #ffffff;
    --text-muted:    rgba(255,255,255,0.55);
    --text-faint:    rgba(255,255,255,0.30);
    --accent:        #6366f1;
    --accent-glow:   rgba(99,102,241,0.25);
    --violet:        #8b5cf6;
    --shadow:        rgba(0,0,0,0.6);
  }

  body {
    width: 1920px; height: 1080px; overflow: hidden;
    background: var(--bg);
    font-family: 'Inter', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }

  .badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase;
    color: #a5b4fc;
    background: rgba(99,102,241,0.12);
    border: 1px solid rgba(99,102,241,0.25);
    padding: 8px 18px; border-radius: 100px;
    margin-bottom: 30px;
  }

  .headline {
    font-weight: 800; color: var(--text);
    line-height: 1.05; letter-spacing: -2px;
  }

  .sub {
    font-size: 28px; font-weight: 400;
    color: var(--text-muted); line-height: 1.6;
    margin-top: 20px;
  }

  .card {
    border-radius: 14px; overflow: hidden;
    box-shadow: 0 0 0 1px var(--border), 0 30px 80px var(--shadow);
    background: #12121e;
  }

  .card-chrome {
    height: 36px; background: #16162a;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; padding: 0 14px; gap: 7px;
  }
  .dot { width: 11px; height: 11px; border-radius: 50%; }
  .dot-r { background: #ff5f57; }
  .dot-y { background: #ffbd2e; }
  .dot-g { background: #28c840; }

  .card img { width: 100%; display: block; }

  .promoly-badge {
    position: fixed; bottom: 28px; right: 36px;
    font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;
    color: rgba(255,255,255,0.18);
  }
"""

# ─── Image → base64 data-URI ──────────────────────────────────────────────────

def _b64(path: Path, max_w: int = 1200, quality: int = 82) -> str:
    try:
        img = Image.open(path).convert("RGB")
        if img.width > max_w:
            r = max_w / img.width
            img = img.resize((max_w, int(img.height * r)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def _b64_full(path: Path) -> str:
    """Full-resolution for hero backgrounds (will be blurred/small anyway)."""
    return _b64(path, max_w=1920, quality=70)


def _esc(s: str) -> str:
    """Escape HTML special characters."""
    return (s.replace("&", "&amp;").replace("<", "&lt;")
              .replace(">", "&gt;").replace('"', "&quot;"))


def _wrap(text: str, width: int = 28) -> str:
    return "<br>".join(textwrap.wrap(_esc(text), width=width))

# ─── Layout templates ─────────────────────────────────────────────────────────

def _base(body_html: str, extra_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
{SHARED_CSS}
{extra_css}
</style>
</head>
<body>
{body_html}
<div class="promoly-badge">PROMOLY</div>
</body>
</html>"""


# ── 1. HERO LAYOUT ─────────────────────────────────────────────────────────────

def hero_layout(headline: str, subheadline: str, badge_text: str, screenshot: Path) -> str:
    img = _b64_full(screenshot)
    css = """
    .bg {
      position: absolute; inset: 0;
      background-image: url('__IMG__');
      background-size: cover; background-position: center top;
      filter: blur(28px) brightness(0.22) saturate(0.6);
      transform: scale(1.08);
    }
    .glow-a {
      position: absolute; inset: 0;
      background: radial-gradient(ellipse 100% 80% at 30% 40%,
        rgba(99,102,241,0.22) 0%, transparent 60%);
    }
    .glow-b {
      position: absolute; inset: 0;
      background: radial-gradient(ellipse 80% 100% at 75% 60%,
        rgba(139,92,246,0.14) 0%, transparent 55%);
    }
    .overlay {
      position: absolute; inset: 0;
      background: linear-gradient(to bottom,
        rgba(7,7,18,0.3) 0%, rgba(7,7,18,0.55) 50%, rgba(7,7,18,0.80) 100%);
    }
    .content {
      position: relative; z-index: 2;
      width: 100%; height: 100%;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      text-align: center; padding: 0 240px;
    }
    .headline { font-size: 108px; max-width: 14ch; }
    .sub { max-width: 50ch; }
    .accent-line {
      width: 72px; height: 4px; border-radius: 2px;
      background: linear-gradient(90deg, var(--accent), var(--violet));
      margin-top: 36px;
    }
    """.replace("__IMG__", img)

    body = f"""
    <div class="bg"></div>
    <div class="glow-a"></div>
    <div class="glow-b"></div>
    <div class="overlay"></div>
    <div class="content">
      <div class="badge">{_esc(badge_text)}</div>
      <h1 class="headline">{_wrap(headline, 20)}</h1>
      {"<p class='sub'>" + _wrap(subheadline, 55) + "</p>" if subheadline else ""}
      <div class="accent-line"></div>
    </div>"""
    return _base(body, css)


# ── 2. SPLIT LAYOUT (text left, card right) ────────────────────────────────────

def split_layout(headline: str, subheadline: str, body_text: str,
                 badge_text: str, screenshot: Path, reverse: bool = False) -> str:
    img = _b64(screenshot)
    left_w = 44 if not reverse else 50
    right_w = 56 if not reverse else 50

    txt_side  = "left"  if not reverse else "right"
    card_side = "right" if not reverse else "left"

    css = f"""
    body {{ display: flex; }}
    .bg-grad {{
      position: fixed; inset: 0;
      background:
        radial-gradient(ellipse 70% 100% at {20 if not reverse else 80}% 50%,
          rgba(99,102,241,0.10) 0%, transparent 60%),
        var(--bg);
      z-index: 0;
    }}
    .text-col {{
      position: relative; z-index: 1;
      width: {left_w if not reverse else right_w}%;
      display: flex; flex-direction: column; justify-content: center;
      padding: {'90px 60px 90px 100px' if not reverse else '90px 100px 90px 60px'};
    }}
    .img-col {{
      position: relative; z-index: 1;
      width: {right_w if not reverse else left_w}%;
      display: flex; align-items: center; justify-content: center;
      padding: 60px {'80px 60px 20px' if not reverse else '20px 60px 80px'};
    }}
    .headline {{ font-size: 76px; max-width: 14ch; }}
    .sub {{ font-size: 26px; margin-top: 18px; max-width: 38ch; }}
    .body-text {{
      font-size: 24px; color: var(--text-faint);
      line-height: 1.7; margin-top: 22px; max-width: 42ch;
    }}
    .img-col .card {{ width: 100%; }}
    .blob {{
      position: absolute;
      width: 500px; height: 500px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%);
      filter: blur(40px);
      pointer-events: none;
    }}
    """

    card_html = f"""
    <div class="card">
      <div class="card-chrome">
        <div class="dot dot-r"></div>
        <div class="dot dot-y"></div>
        <div class="dot dot-g"></div>
      </div>
      <img src="{img}" alt="">
    </div>"""

    text_html = f"""
    <div class="badge">{_esc(badge_text)}</div>
    <h2 class="headline">{_wrap(headline, 18)}</h2>
    {"<p class='sub'>" + _wrap(subheadline, 48) + "</p>" if subheadline else ""}
    {"<p class='body-text'>" + _wrap(body_text[:180], 52) + "</p>" if body_text else ""}
    """

    if not reverse:
        body = f"""
        <div class="bg-grad"></div>
        <div class="text-col">{text_html}</div>
        <div class="img-col"><div class="blob"></div>{card_html}</div>"""
    else:
        body = f"""
        <div class="bg-grad"></div>
        <div class="img-col"><div class="blob"></div>{card_html}</div>
        <div class="text-col">{text_html}</div>"""

    return _base(body, css)


# ── 3. FEATURE LAYOUT (headline top, bullets left, card right) ─────────────────

def feature_layout(headline: str, subheadline: str, section_text: str,
                   badge_text: str, screenshot: Path) -> str:
    img = _b64(screenshot)

    # Extract bullet points from section text
    raw_lines = [l.strip() for l in section_text.split("\n") if len(l.strip()) > 15]
    bullets = raw_lines[:4] or ["Powerful and fast", "Easy to integrate", "Scales with you"]

    bullet_items = "".join(
        f'<li><span class="check">✓</span>{_esc(b[:70])}</li>' for b in bullets
    )

    css = """
    body {
      display: flex; flex-direction: column;
      background:
        radial-gradient(ellipse 80% 60% at 20% 10%,
          rgba(99,102,241,0.12) 0%, transparent 55%),
        var(--bg);
    }
    .top {
      padding: 56px 100px 36px;
      display: flex; flex-direction: column;
    }
    .bottom {
      flex: 1; display: flex; padding: 0 100px 56px; gap: 60px;
    }
    .headline { font-size: 72px; max-width: 18ch; }
    .sub { font-size: 26px; margin-top: 12px; }
    .bullets-col {
      flex: 0 0 680px;
      display: flex; flex-direction: column; justify-content: center;
      gap: 0;
    }
    ul.bullets { list-style: none; display: flex; flex-direction: column; gap: 18px; }
    ul.bullets li {
      display: flex; align-items: flex-start; gap: 16px;
      font-size: 26px; color: var(--text-muted); line-height: 1.4;
    }
    .check {
      color: var(--accent); font-weight: 800; font-size: 22px;
      flex-shrink: 0; margin-top: 3px;
    }
    .card-col {
      flex: 1; display: flex; align-items: center; justify-content: center;
    }
    .card-col .card { width: 100%; }
    """

    body = f"""
    <div class="top">
      <div class="badge">{_esc(badge_text)}</div>
      <h2 class="headline">{_wrap(headline, 22)}</h2>
      {"<p class='sub'>" + _wrap(subheadline, 70) + "</p>" if subheadline else ""}
    </div>
    <div class="bottom">
      <div class="bullets-col">
        <ul class="bullets">{bullet_items}</ul>
      </div>
      <div class="card-col">
        <div class="card">
          <div class="card-chrome">
            <div class="dot dot-r"></div>
            <div class="dot dot-y"></div>
            <div class="dot dot-g"></div>
          </div>
          <img src="{img}" alt="">
        </div>
      </div>
    </div>"""
    return _base(body, css)


# ── 4. CTA LAYOUT ─────────────────────────────────────────────────────────────

def cta_layout(headline: str, cta_text: str, domain: str) -> str:
    cta_label = cta_text or "Get Started Free"
    css = """
    body {
      display: flex; align-items: center; justify-content: center;
      background:
        radial-gradient(ellipse 120% 80% at 50% 20%,
          rgba(99,102,241,0.20) 0%, transparent 55%),
        radial-gradient(ellipse 80% 120% at 80% 90%,
          rgba(139,92,246,0.15) 0%, transparent 55%),
        #050510;
    }
    .card-wrap {
      text-align: center;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 28px;
      padding: 90px 120px;
      backdrop-filter: blur(8px);
      box-shadow: 0 40px 120px rgba(0,0,0,0.5);
      min-width: 1100px;
    }
    .headline { font-size: 110px; max-width: 16ch; margin: 0 auto; }
    .cta-btn {
      display: inline-block; margin-top: 52px;
      padding: 22px 70px; border-radius: 100px;
      background: linear-gradient(135deg, var(--accent), var(--violet));
      font-size: 32px; font-weight: 700; color: white;
      box-shadow: 0 8px 40px rgba(99,102,241,0.45);
      letter-spacing: -0.5px;
    }
    .domain {
      margin-top: 36px;
      font-size: 20px; font-weight: 500; letter-spacing: 1px;
      color: var(--text-faint);
    }
    .sparkles {
      font-size: 22px; margin-bottom: 20px; opacity: 0.6;
      letter-spacing: 8px;
    }
    """

    body = f"""
    <div class="card-wrap">
      <div class="sparkles">✦ ✦ ✦</div>
      <h2 class="headline">{_wrap(headline, 16)}</h2>
      <div class="cta-btn">{_esc(cta_label)}</div>
      <p class="domain">{_esc(domain)}</p>
    </div>"""
    return _base(body, css)


# ─── Dispatch layout by name ──────────────────────────────────────────────────

def build_scene_html(scene: dict, sections_map: dict, meta: dict) -> str:
    layout    = scene.get("layout", "split_layout")
    section_t = scene.get("section", "hero")
    headline  = scene.get("headline", "")
    sub       = scene.get("subheadline", "")
    badge     = scene.get("scene_type", section_t).replace("_", " ").title()
    domain    = meta.get("domain", "")

    sec_data: SectionData | None = sections_map.get(section_t) or next(iter(sections_map.values()), None)
    screenshot = sec_data.screenshot_path if sec_data else None
    body_text  = sec_data.text if sec_data else ""
    sub        = sub or (sec_data.subheading if sec_data else "")

    # Fallback screenshot = first available
    if screenshot is None or not screenshot.exists():
        for sd in sections_map.values():
            if sd.screenshot_path and sd.screenshot_path.exists():
                screenshot = sd.screenshot_path
                break

    if layout == "hero_layout":
        return hero_layout(headline, sub, badge, screenshot)

    elif layout == "reverse_split_layout":
        return split_layout(headline, sub, body_text, badge, screenshot, reverse=True)

    elif layout == "feature_layout":
        return feature_layout(headline, sub, body_text, badge, screenshot)

    elif layout == "cta_layout":
        cta_label = _extract_cta_label(sec_data) if sec_data else "Get Started Free"
        return cta_layout(headline, cta_label, domain)

    else:  # split_layout (default)
        return split_layout(headline, sub, body_text, badge, screenshot, reverse=False)


def _extract_cta_label(sec: "SectionData") -> str:
    import re
    text = sec.text.lower()
    for phrase in ["get started", "start free", "try free", "sign up", "join free",
                   "start now", "book demo", "request demo", "get demo"]:
        if phrase in text:
            return phrase.title()
    return "Get Started Free"


# ─── Render all scenes ────────────────────────────────────────────────────────

async def render_all_scenes(
    storyboard: dict,
    sections_map: dict,
    meta: dict,
    session_dir: Path,
    browser,
    progress_cb=None,
) -> list[Path]:
    """
    For each scene in the storyboard, render its HTML template
    via Playwright and save a 1920×1080 PNG.
    """
    scenes = storyboard.get("scenes", [])
    frame_paths: list[Path] = []

    context = await browser.new_context(viewport={"width": W, "height": H})

    for i, scene in enumerate(scenes):
        html = build_scene_html(scene, sections_map, meta)
        path = session_dir / f"frame_{i:02d}_{scene.get('layout','scene')}.png"

        page = await context.new_page()
        try:
            await page.set_content(html, wait_until="networkidle", timeout=10000)
        except Exception:
            await page.set_content(html)
            await asyncio.sleep(0.8)

        await page.screenshot(path=str(path), full_page=False)
        await page.close()
        frame_paths.append(path)

        if progress_cb:
            pct = 55 + int((i + 1) / len(scenes) * 25)
            progress_cb(pct, f"Rendered scene {i+1}/{len(scenes)}: {scene.get('layout')}")

    await context.close()
    return frame_paths
