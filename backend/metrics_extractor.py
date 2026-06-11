"""
metrics_extractor.py – Structured metric extraction for Promoly.

Two extraction paths:
  1. DOM-based  : JavaScript evaluation in the live Playwright page
  2. Text-based : regex over scraped section text (no browser needed)

Every extracted metric is normalized and ranked by importance.
The top-ranked metrics drive MetricCounter scenes in scene_designer.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Metric type taxonomy ───────────────────────────────────────────────────────

METRIC_TYPE_RULES: list[tuple[str, str, list[str]]] = [
    # (type_id, label_hint, trigger_patterns)
    ("uptime",      "Uptime",          ["uptime", "availability", "sla", "reliable"]),
    ("users",       "Users",           ["users", "customers", "teams", "companies", "businesses", "startups", "organizations", "clients", "developers"]),
    ("requests",    "Requests",        ["requests", "api calls", "queries", "events", "transactions"]),
    ("revenue",     "Revenue Saved",   ["saved", "revenue", "arr", "mrr", "funding", "raised"]),
    ("speed",       "Faster",          ["faster", "speed", "latency", "ms", "seconds", "time"]),
    ("reduction",   "Cost Reduction",  ["reduction", "less", "cut", "fewer", "eliminate"]),
    ("growth",      "Growth",          ["growth", "increase", "more", "higher", "gain", "improved"]),
    ("rating",      "Rating",          ["stars", "rating", "score", "nps", "satisfaction", "reviews"]),
    ("support",     "Support",         ["24/7", "247", "always on", "support hours", "availability"]),
    ("compliance",  "Certified",       ["soc2", "soc 2", "gdpr", "hipaa", "iso", "ccpa", "compliant"]),
    ("integration", "Integrations",    ["integrations", "apps", "tools", "connects", "works with"]),
    ("deployment",  "Deploys",         ["deployments", "releases", "deploys", "shipped"]),
]

# Regex: catches numbers like 99.99%, 10M+, $50M, 24/7, 500K, 3x, SOC2
_METRIC_RE = re.compile(
    r"""
    (?:
        \$\s*\d[\d,\.]*\s*(?:M|B|K)?     # dollar amounts: $50M
        | \d[\d,\.]*\s*(?:%|x|×)          # percentages / multipliers: 99.9%, 3x
        | \d[\d,\.]*\s*(?:M|B|K)\+?       # large numbers: 10M+, 500K
        | 24\s*[/\\]\s*7                   # 24/7
        | \d{1,3}(?:,\d{3})+\+?           # comma-formatted: 10,000+
        | SOC\s*2                          # compliance markers
        | ISO\s*\d+                        # ISO certifications
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Context window around a match to extract label
_CONTEXT_WINDOW = 60  # chars on each side


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ExtractedMetric:
    value: str          # raw value as displayed: "99.99%", "10M+", "$50M"
    label: str          # inferred label: "Uptime", "Users", "Revenue"
    type: str           # type_id from taxonomy: "uptime", "users", "speed"
    importance: int     # 0-100 rank
    context: str        # surrounding text used to infer the label
    source: str         # "dom" | "text" | "heading"
    section: str        # which section this came from

    def to_dict(self) -> dict:
        return {
            "value":      self.value,
            "label":      self.label,
            "type":       self.type,
            "importance": self.importance,
            "context":    self.context,
            "source":     self.source,
            "section":    self.section,
        }


# ── Normalization ─────────────────────────────────────────────────────────────

def _normalize_value(raw: str) -> str:
    """Trim whitespace and normalize spacing inside the value."""
    v = re.sub(r"\s+", "", raw.strip())
    # Normalize 24 / 7 → 24/7
    v = re.sub(r"24[/\\]7", "24/7", v, flags=re.IGNORECASE)
    return v


def _infer_type_and_label(context_lower: str) -> tuple[str, str]:
    """Return (type_id, label) by matching context against taxonomy."""
    for type_id, label, triggers in METRIC_TYPE_RULES:
        if any(t in context_lower for t in triggers):
            return type_id, label
    return "metric", "Metric"


def _importance_score(metric: ExtractedMetric, rank: int, total: int) -> int:
    """
    Score 0-100 based on:
      - type priority (uptime > users > revenue > speed > ...)
      - whether it came from a heading vs body text
      - position rank among all metrics
    """
    TYPE_PRIORITY = {
        "uptime": 95, "users": 90, "revenue": 85, "speed": 80,
        "growth": 78, "rating": 75, "reduction": 72, "compliance": 70,
        "requests": 65, "support": 60, "integration": 55, "deployment": 50,
        "metric": 40,
    }
    source_bonus = {"heading": 10, "dom": 5, "text": 0}
    base = TYPE_PRIORITY.get(metric.type, 40)
    position_penalty = int((rank / max(total, 1)) * 20)
    bonus = source_bonus.get(metric.source, 0)
    return max(0, min(100, base + bonus - position_penalty))


# ── Text-based extraction ─────────────────────────────────────────────────────

def extract_metrics_from_text(
    text: str,
    section: str = "unknown",
    source: str = "text",
) -> list[ExtractedMetric]:
    """
    Extract metrics from a plain text string using regex.
    Returns deduplicated, unnormalized metrics (importance not yet set).
    """
    results: list[ExtractedMetric] = []
    seen_values: set[str] = set()

    for m in _METRIC_RE.finditer(text):
        raw_val = m.group(0)
        norm_val = _normalize_value(raw_val)

        if norm_val in seen_values or len(norm_val) < 2:
            continue
        seen_values.add(norm_val)

        # Context: chars before and after the match
        start = max(0, m.start() - _CONTEXT_WINDOW)
        end   = min(len(text), m.end() + _CONTEXT_WINDOW)
        ctx   = text[start:end].strip()
        ctx_lower = ctx.lower()

        type_id, label = _infer_type_and_label(ctx_lower)

        results.append(ExtractedMetric(
            value=norm_val, label=label, type=type_id,
            importance=0,   # set later by rank_metrics()
            context=ctx[:120],
            source=source,
            section=section,
        ))

    return results


def extract_metrics_from_sections(sections) -> list[ExtractedMetric]:
    """
    Run text-based extraction over all scraped sections.
    Headings are treated as higher-priority source.
    """
    all_metrics: list[ExtractedMetric] = []
    seen: set[str] = set()

    for sec in sections:
        # Headings first (source="heading" → higher importance bonus)
        for text, src in [
            (sec.heading, "heading"),
            (sec.subheading, "text"),
            (sec.text, "text"),
        ]:
            if not text:
                continue
            for m in extract_metrics_from_text(text, section=sec.section_type, source=src):
                if m.value not in seen:
                    seen.add(m.value)
                    all_metrics.append(m)

    return all_metrics


# ── DOM-based extraction (called from within Playwright session) ───────────────

async def extract_metrics_from_dom(page) -> list[dict]:
    """
    Run a JavaScript evaluation to find stat/metric elements directly from DOM.
    Returns a list of raw dicts: {value, label, context, selector}.
    Called while the Playwright browser is still open.
    """
    raw: list[dict] = await page.evaluate("""() => {
        const results = [];
        const seen = new Set();

        // Selectors that typically wrap stat numbers
        const STAT_SELECTORS = [
            '[class*="stat"]',
            '[class*="metric"]',
            '[class*="number"]',
            '[class*="count"]',
            '[class*="kpi"]',
            '[class*="figure"]',
            '[class*="highlight"]',
            '[class*="badge"]',
            '[class*="counter"]',
            '[class*="impact"]',
            '[data-stat]',
            '[class*="social-proof"]',
        ];

        // Number pattern — same as Python regex but simplified for JS
        const NUM_RE = /(\\$\\s*\\d[\\d,\\.]*\\s*[MBK]?|\\d[\\d,\\.]*\\s*[%xX×]|\\d[\\d,\\.]*\\s*[MBKmk]\\+?|24\\s*\\/\\s*7|\\d{1,3}(?:,\\d{3})+\\+?|SOC\\s*2|ISO\\s*\\d+)/i;

        const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();

        for (const sel of STAT_SELECTORS) {
            let els;
            try { els = document.querySelectorAll(sel); } catch(e) { continue; }
            for (const el of els) {
                const txt = clean(el.innerText || el.textContent || '');
                if (!txt || txt.length > 200 || txt.length < 2) continue;

                const m = NUM_RE.exec(txt);
                if (!m) continue;

                const value = m[1].replace(/\\s+/g,'').trim();
                if (seen.has(value) || value.length < 2) continue;
                seen.add(value);

                // Look for a label: sibling text, parent, or aria-label
                const parent = el.parentElement;
                const siblingText = parent
                    ? clean([...parent.children]
                        .filter(c => c !== el)
                        .map(c => c.innerText || c.textContent || '')
                        .join(' '))
                    : '';
                const label = siblingText.slice(0, 60) || txt.replace(value, '').trim().slice(0,60);

                results.push({ value, label, context: txt.slice(0, 120), selector: sel });
                if (results.length >= 30) return results;
            }
        }

        return results;
    }""")
    return raw


# ── Rank and deduplicate ──────────────────────────────────────────────────────

def rank_metrics(metrics: list[ExtractedMetric]) -> list[ExtractedMetric]:
    """
    Deduplicate by normalized value, assign importance scores, sort high→low.
    """
    seen: dict[str, ExtractedMetric] = {}

    for m in metrics:
        key = m.value.lower()
        if key not in seen:
            seen[key] = m
        else:
            # Prefer heading source
            existing = seen[key]
            if m.source == "heading" and existing.source != "heading":
                seen[key] = m

    ranked = list(seen.values())
    total = len(ranked)
    for i, m in enumerate(ranked):
        m.importance = _importance_score(m, i, total)

    ranked.sort(key=lambda m: m.importance, reverse=True)
    return ranked[:12]  # cap at 12


# ── Public entry point ────────────────────────────────────────────────────────

async def build_metrics(page, sections) -> list[ExtractedMetric]:
    """
    Full metrics pipeline: DOM extraction + text extraction → ranked list.
    Called while the Playwright browser is still open.
    """
    # DOM-based (most accurate — element-level)
    dom_raw = await extract_metrics_from_dom(page)
    dom_metrics: list[ExtractedMetric] = []
    for r in dom_raw:
        type_id, label = _infer_type_and_label((r.get("context", "") + " " + r.get("label", "")).lower())
        if not label or label == "Metric":
            label = r.get("label", "Metric") or "Metric"
        dom_metrics.append(ExtractedMetric(
            value=_normalize_value(r["value"]),
            label=label[:40],
            type=type_id,
            importance=0,
            context=r.get("context", "")[:120],
            source="dom",
            section="unknown",
        ))

    # Text-based (catches metrics in headings / body copy not in stat elements)
    text_metrics = extract_metrics_from_sections(sections)

    combined = dom_metrics + text_metrics
    ranked   = rank_metrics(combined)

    print(
        f"[Metrics] DOM={len(dom_metrics)} text={len(text_metrics)} "
        f"→ ranked={len(ranked)} top={ranked[0].value if ranked else 'none'}",
        flush=True,
    )
    return ranked
