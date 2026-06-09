"""
detector.py – Smart DOM-based section detection via Playwright.

Instead of random scroll percentages, we analyse the DOM to find
semantic sections (hero, features, pricing, …), capture a viewport
screenshot of each, and extract heading/body text.
"""
from __future__ import annotations

import json
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


# ─── Data model ───────────────────────────────────────────────────────────────

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
