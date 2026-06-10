"""
detector.py – Smart DOM-based section detection via Playwright.

Instead of random scroll percentages, we analyse the DOM to find
semantic sections (hero, features, pricing, …), capture a viewport
screenshot of each, and extract heading/body text.

Also provides extract_visual_elements() which runs in the same browser
session to capture individual UI elements (buttons, cards, widgets) with
bounding boxes — used by visual_mapper.py for precise camera targeting.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ─── Section type → ordered CSS selectors (most-specific first) ───────────────

SECTION_PATTERNS: dict[str, list[str]] = {
    "hero": [
        '[class*="hero"]', '[id*="hero"]',
        '[class*="jumbotron"]', '[class*="banner"]',
        '[class*="above-fold"]', '[class*="landing"]',
        'header[class]', '.hero', '#hero',
        'main > section:first-of-type',
        'main > div:first-child',
    ],
    "demo": [
        '[class*="demo"]', '[id*="demo"]',
        '[class*="product-demo"]', '[class*="preview"]',
        '[class*="screenshot"]', '[class*="product-shot"]',
    ],
    "features": [
        '[class*="feature"]', '[id*="features"]',
        '[id*="feature"]', '.features', '#features',
        '[class*="capabilities"]', '[class*="what-we"]',
        '[class*="product"]',
    ],
    "benefits": [
        '[class*="benefit"]', '[id*="benefits"]',
        '[class*="why-us"]', '[class*="why-choose"]',
        '[class*="value-prop"]', '[class*="advantage"]',
    ],
    "integrations": [
        '[class*="integration"]', '[id*="integrations"]',
        '[class*="connect"]', '[class*="ecosystem"]',
        '[class*="partners"]', '[class*="built-with"]',
    ],
    "testimonials": [
        '[class*="testimonial"]', '[id*="testimonials"]',
        '[class*="review"]', '[id*="reviews"]',
        '[class*="social-proof"]', '[class*="quote"]',
        '[class*="what-people"]',
    ],
    "customers": [
        '[class*="customer"]', '[id*="customers"]',
        '[class*="client"]', '[class*="trusted-by"]',
        '[class*="logo-wall"]', '[class*="brand"]',
    ],
    "pricing": [
        '[class*="pricing"]', '[id*="pricing"]',
        '[class*="plans"]', '[id*="plans"]',
        '[class*="plan"]', '[class*="subscription"]',
    ],
    "faq": [
        '[class*="faq"]', '[id*="faq"]',
        '[class*="accordion"]', '[class*="question"]',
        '[class*="help"]',
    ],
    "cta": [
        '[class*="cta"]', '[id*="cta"]',
        '[class*="call-to-action"]', '[class*="get-started"]',
        '[class*="start-free"]', '[class*="try-free"]',
        '[class*="signup-section"]',
        'section:last-of-type',
    ],
}


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class SectionData:
    section_type: str
    heading: str
    subheading: str
    text: str
    scroll_y: int
    screenshot_path: Optional[Path] = None

    def to_dict(self) -> dict:
        return {
            "section_type": self.section_type,
            "heading": self.heading,
            "subheading": self.subheading,
            "text": self.text,
            "screenshot_path": str(self.screenshot_path) if self.screenshot_path else None,
        }


@dataclass
class VisualElement:
    """
    A single interactive/visual UI element captured at the element level.
    Coordinates (x, y, width, height) are in 1920×1080 viewport space,
    relative to the scroll position at capture time.
    """
    id: str                          # e.g. "cta_button_0"
    element_type: str                # button | card | pricing | testimonial | widget | hero | nav
    text: str                        # visible label / heading text
    screenshot_path: Optional[Path]  # element crop screenshot
    bounding_box: dict               # {x, y, width, height, centerX, centerY, focusX, focusY}
    section_type: str                # which section this was found in
    scroll_y: int                    # page scroll at capture time

    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "element_type":   self.element_type,
            "text":           self.text,
            "screenshot_path": str(self.screenshot_path) if self.screenshot_path else None,
            "bounding_box":   self.bounding_box,
            "section_type":   self.section_type,
        }


# ─── Detection ────────────────────────────────────────────────────────────────

async def detect_sections(
    page,
    session_dir: Path,
    max_sections: int = 7,
    progress_cb=None,
) -> list[SectionData]:
    """
    Analyse the DOM of the current page, detect semantic sections,
    scroll to each and capture a viewport screenshot.
    """
    patterns_json = json.dumps(SECTION_PATTERNS)

    raw: list[dict] = await page.evaluate(
        """(patterns) => {
            const results = [];
            const usedRanges = [];
            const viewH = window.innerHeight;
            const totalH = document.documentElement.scrollHeight;

            const unique = (y) =>
                usedRanges.every(([lo, hi]) => y < lo || y > hi);

            const clean = (s) =>
                (s || '').replace(/\\s+/g, ' ').trim();

            const headingOf = (el) => {
                for (const tag of ['h1','h2','h3']) {
                    const t = el.querySelector(tag)?.innerText;
                    if (t && t.trim().length > 2) return clean(t).slice(0, 120);
                }
                return '';
            };

            const subOf = (el) => {
                for (const sel of [
                    'h4','h5','.subtitle','.sub-heading',
                    '.description','p.lead','.tagline','p',
                ]) {
                    const t = el.querySelector(sel)?.innerText;
                    if (t && t.trim().length > 10) return clean(t).slice(0, 160);
                }
                return '';
            };

            for (const [type, selectors] of Object.entries(patterns)) {
                if (results.length >= 8) break;
                for (const sel of selectors) {
                    let el;
                    try { el = document.querySelector(sel); } catch(e) { continue; }
                    if (!el || el.offsetHeight < 60) continue;

                    const rect = el.getBoundingClientRect();
                    const absY = Math.floor(rect.top + window.scrollY);
                    const scrollY = Math.max(0, Math.min(absY, totalH - viewH));

                    if (!unique(scrollY)) continue;

                    const heading    = headingOf(el);
                    const subheading = subOf(el);
                    const text       = clean(el.innerText).slice(0, 500);

                    results.push({ type, scrollY, heading, subheading, text });
                    usedRanges.push([scrollY - 250, scrollY + 250]);
                    break;
                }
            }

            return results;
        }""",
        json.loads(patterns_json),
    )

    # Ensure hero is always first; sort rest by scroll position
    raw.sort(key=lambda r: (0 if r["type"] == "hero" else 1, r["scrollY"]))
    raw = raw[:max_sections]

    # ── Scroll-based fallback: fill up to max_sections if DOM detection found too few ──
    if len(raw) < max_sections:
        page_height, view_height = await page.evaluate(
            "() => [document.documentElement.scrollHeight, window.innerHeight]"
        )
        used_y = {r["scrollY"] for r in raw}
        extra_needed = max_sections - len(raw)
        # Divide page into equal strips, skip positions already captured
        SCROLL_TYPES = ["content", "benefits", "features", "demo",
                        "testimonials", "integrations", "pricing", "cta"]
        strip_count  = extra_needed + len(raw) + 2
        step         = max(1, (page_height - view_height) // strip_count)
        added        = 0
        for k in range(1, strip_count + 1):
            if added >= extra_needed:
                break
            y = min(k * step, page_height - view_height)
            if any(abs(y - uy) < 300 for uy in used_y):
                continue
            used_y.add(y)
            stype = SCROLL_TYPES[added % len(SCROLL_TYPES)]
            raw.append({"type": stype, "scrollY": y,
                        "heading": "", "subheading": "", "text": ""})
            added += 1

    sections: list[SectionData] = []

    for i, r in enumerate(raw):
        await page.evaluate(
            "y => window.scrollTo({top: y, behavior: 'smooth'})", r["scrollY"]
        )
        await page.wait_for_timeout(800)

        path = session_dir / f"{r['type']}_{i:02d}.png"
        await page.screenshot(path=str(path), full_page=False)

        sections.append(SectionData(
            section_type=r["type"],
            heading=r.get("heading", ""),
            subheading=r.get("subheading", ""),
            text=r.get("text", ""),
            scroll_y=r["scrollY"],
            screenshot_path=path,
        ))

        if progress_cb:
            pct = 15 + int((i + 1) / len(raw) * 25)
            progress_cb(pct, f"Captured section {i+1}/{len(raw)}: {r['type']}")

    return sections


async def extract_visual_elements(
    page,
    session_dir: Path,
    sections: list["SectionData"],
) -> list["VisualElement"]:
    """
    Extract individual UI elements (buttons, cards, widgets) from the page.

    Called after detect_sections() while the browser is still open.
    Scrolls to each section's position and captures element-level bounding
    boxes + cropped screenshots.

    Returns a flat list of VisualElement objects sorted by section order.
    Never raises — returns empty list on any failure.
    """
    ELEMENT_SELECTORS: dict[str, list[str]] = {
        "button": [
            'a[class*="btn"]:not(nav a)',
            'a[class*="button"]:not(nav a)',
            'button[class*="cta"]',
            'button[class*="primary"]',
            'a[class*="cta"]',
            'a[class*="get-started"]',
            'a[class*="start-free"]',
            'a[class*="try-free"]',
            'a[class*="sign-up"]',
            'a[class*="signup"]',
            '.hero a[href]',
            'a[class*="primary"]',
        ],
        "card": [
            '[class*="feature-card"]',
            '[class*="feature-item"]',
            '[class*="feature-box"]',
            '[class*="card"]:not(nav)',
            '[class*="feature__item"]',
        ],
        "pricing": [
            '[class*="pricing-card"]',
            '[class*="pricing-plan"]',
            '[class*="plan-card"]',
            '[class*="tier"]',
        ],
        "testimonial": [
            '[class*="testimonial-card"]',
            '[class*="review-card"]',
            '[class*="quote-card"]',
            'blockquote',
        ],
        "widget": [
            '[class*="dashboard"]',
            '[class*="analytics"]',
            '[class*="chart"]',
            '[class*="metric"]',
            '[class*="stat-card"]',
            '[class*="kpi"]',
        ],
        "hero": [
            'h1',
            '[class*="hero-title"]',
            '[class*="hero-heading"]',
        ],
    }

    elements: list[VisualElement] = []
    counters: dict[str, int] = {}

    for section in sections:
        if section.scroll_y is None:
            continue

        # Scroll to the section
        try:
            await page.evaluate("y => window.scrollTo({top: y, behavior: 'instant'})", section.scroll_y)
            await page.wait_for_timeout(400)
        except Exception:
            continue

        # Collect all elements visible in this viewport position
        for el_type, selectors in ELEMENT_SELECTORS.items():
            for sel in selectors:
                try:
                    raw_els: list[dict] = await page.evaluate(
                        """([sel, maxItems]) => {
                            const els = Array.from(document.querySelectorAll(sel)).slice(0, maxItems);
                            return els.map(el => {
                                const r = el.getBoundingClientRect();
                                // Only include elements visible in the current viewport
                                if (r.width < 20 || r.height < 10) return null;
                                if (r.top < -100 || r.bottom > window.innerHeight + 100) return null;
                                if (r.left < 0 || r.right > window.innerWidth + 20) return null;
                                const text = (el.innerText || el.textContent || el.alt || '').replace(/\\s+/g,' ').trim().slice(0,120);
                                return {
                                    x: Math.round(r.left),
                                    y: Math.round(r.top),
                                    width: Math.round(r.width),
                                    height: Math.round(r.height),
                                    text: text,
                                };
                            }).filter(Boolean);
                        }""",
                        [sel, 3],
                    )
                except Exception:
                    continue

                for raw in raw_els:
                    if not raw or raw["width"] < 20 or raw["height"] < 10:
                        continue

                    idx = counters.get(el_type, 0)
                    counters[el_type] = idx + 1
                    el_id = f"{el_type}_{section.section_type}_{idx}"

                    # Bounding box in 1920×1080 viewport space
                    x, y, w, h = raw["x"], raw["y"], raw["width"], raw["height"]
                    cx = x + w // 2
                    cy = y + h // 2
                    bbox = {
                        "x": x, "y": y,
                        "width": w, "height": h,
                        "centerX": cx, "centerY": cy,
                        "focusX": round(cx / 1920, 4),
                        "focusY": round(cy / 1080, 4),
                    }

                    # Crop screenshot of the element (with 12px padding)
                    el_path: Optional[Path] = None
                    try:
                        pad = 12
                        clip = {
                            "x": max(0, x - pad),
                            "y": max(0, y - pad),
                            "width": min(1920, w + pad * 2),
                            "height": min(1080, h + pad * 2),
                        }
                        el_path = session_dir / f"el_{el_id}.png"
                        await page.screenshot(
                            path=str(el_path),
                            full_page=False,
                            clip=clip,
                        )
                    except Exception:
                        el_path = None

                    elements.append(VisualElement(
                        id=el_id,
                        element_type=el_type,
                        text=raw.get("text", ""),
                        screenshot_path=el_path,
                        bounding_box=bbox,
                        section_type=section.section_type,
                        scroll_y=section.scroll_y,
                    ))

                # Only take first matching selector per type per section
                if raw_els:
                    break

    print(f"[Detector] Visual elements found: {len(elements)} ({', '.join(f'{t}:{n}' for t, n in counters.items())})", flush=True)
    return elements


async def extract_page_meta(page) -> dict:
    return await page.evaluate("""() => {
        const c = (s) => (s || '').replace(/\\s+/g,' ').trim();
        const t = (s, n) => c(s).slice(0, n);
        return {
            url:         window.location.href,
            title:       t(document.title, 80),
            h1:          t(document.querySelector('h1')?.innerText, 100),
            description: t(document.querySelector('meta[name="description"]')?.content, 200),
            og_title:    t(document.querySelector('meta[property="og:title"]')?.content, 100),
            og_desc:     t(document.querySelector('meta[property="og:description"]')?.content, 200),
            domain:      window.location.hostname.replace('www.',''),
        };
    }""")
