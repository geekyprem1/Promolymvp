"""
visual_intelligence.py – Visual Intelligence Engine for Promoly.

Builds a structured visual inventory from:
  • detected sections    (SectionData from detector.py)
  • visual elements      (VisualElement from detector.py)
  • ranked metrics       (ExtractedMetric from metrics_extractor.py)

Output: VisualInventory — a ranked, typed catalogue of every meaningful
visual asset on the page, with importance scores 0-100.

Used by:
  • ai.py            — enriches Gemini prompt with actual visual evidence
  • scene_designer.py — auto-generates MetricCounter scenes for top metrics
  • motion_planner.py — prioritises which elements camera should focus on
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from detector import SectionData, VisualElement
    from metrics_extractor import ExtractedMetric


# ── Importance scoring constants ──────────────────────────────────────────────

IMPORTANCE = {
    "hero_cta":        100,
    "primary_metric":   95,
    "pricing_card":     90,
    "dashboard_widget": 85,
    "feature_card":     75,
    "testimonial":      70,
    "logo":             50,
    "secondary_cta":    60,
    "trust_indicator":  65,
}


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class VisualItem:
    id: str
    type: str                        # cta | metric | pricing | feature | testimonial | widget | logo | trust
    text: str
    importance: int                  # 0-100
    section: str
    screenshot: Optional[str]        # relative path for serving via FastAPI
    metadata: dict = field(default_factory=dict)  # type-specific extras

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "type":       self.type,
            "text":       self.text,
            "importance": self.importance,
            "section":    self.section,
            "screenshot": self.screenshot,
            "metadata":   self.metadata,
        }


@dataclass
class VisualInventory:
    ctas:             list[VisualItem] = field(default_factory=list)
    pricing_cards:    list[VisualItem] = field(default_factory=list)
    feature_cards:    list[VisualItem] = field(default_factory=list)
    testimonials:     list[VisualItem] = field(default_factory=list)
    dashboard_widgets:list[VisualItem] = field(default_factory=list)
    metrics:          list[VisualItem] = field(default_factory=list)
    logos:            list[VisualItem] = field(default_factory=list)
    trust_indicators: list[VisualItem] = field(default_factory=list)

    @property
    def all_items(self) -> list[VisualItem]:
        return sorted(
            self.ctas + self.pricing_cards + self.feature_cards +
            self.testimonials + self.dashboard_widgets + self.metrics +
            self.logos + self.trust_indicators,
            key=lambda x: x.importance,
            reverse=True,
        )

    @property
    def top_metrics(self) -> list[VisualItem]:
        return sorted(self.metrics, key=lambda x: x.importance, reverse=True)[:3]

    def summary(self) -> str:
        return (
            f"ctas={len(self.ctas)} pricing={len(self.pricing_cards)} "
            f"features={len(self.feature_cards)} testimonials={len(self.testimonials)} "
            f"widgets={len(self.dashboard_widgets)} metrics={len(self.metrics)} "
            f"logos={len(self.logos)} trust={len(self.trust_indicators)}"
        )

    def to_prompt_block(self) -> str:
        """Serialize for Gemini prompt — compact and information-dense."""
        lines = ["VISUAL INVENTORY (use these in your scenes):"]

        if self.metrics:
            lines.append("METRICS:")
            for m in self.top_metrics:
                meta = m.metadata
                lines.append(f"  • {m.text}  [{meta.get('label','Metric')}]  importance={m.importance}")

        if self.ctas:
            lines.append("CTA BUTTONS:")
            for c in self.ctas[:3]:
                lines.append(f"  • \"{c.text}\"  section={c.section}")

        if self.pricing_cards:
            lines.append("PRICING CARDS:")
            for p in self.pricing_cards[:3]:
                lines.append(f"  • {p.text[:80]}")

        if self.testimonials:
            lines.append("TESTIMONIALS:")
            for t in self.testimonials[:2]:
                lines.append(f"  • {t.text[:100]}")

        if self.trust_indicators:
            lines.append("TRUST INDICATORS:")
            for ti in self.trust_indicators[:4]:
                lines.append(f"  • {ti.text}")

        if self.dashboard_widgets:
            lines.append("DASHBOARD/WIDGETS detected — reference these in feature scenes.")

        lines.append("")
        lines.append("INSTRUCTIONS:")
        lines.append("1. Use the METRICS values verbatim in headlines and subheadlines.")
        lines.append("2. CTA button text → use as ctaLabel in cta scene.")
        lines.append("3. Pricing card content → use in a dedicated features scene.")
        lines.append("4. Trust indicators → mention in testimonial or CTA scenes.")
        lines.append("5. If top metric has importance ≥ 90, make it the hook stat.")

        return "\n".join(lines)

    def to_scene_hints(self) -> dict:
        """
        Returns hints that scene_designer.py can use to inject MetricCounter scenes.
        """
        return {
            "top_metrics": [
                {
                    "value": m.text,
                    "label": m.metadata.get("label", ""),
                    "type":  m.metadata.get("metric_type", "metric"),
                    "importance": m.importance,
                }
                for m in self.top_metrics
            ],
            "has_pricing":    len(self.pricing_cards) > 0,
            "has_dashboard":  len(self.dashboard_widgets) > 0,
            "has_testimonial": len(self.testimonials) > 0,
            "primary_cta":    self.ctas[0].text if self.ctas else "",
            "cta_screenshot": self.ctas[0].screenshot if self.ctas else None,
            "pricing_screenshot": self.pricing_cards[0].screenshot if self.pricing_cards else None,
            "dashboard_screenshot": self.dashboard_widgets[0].screenshot if self.dashboard_widgets else None,
        }


# ── Trust indicator patterns ──────────────────────────────────────────────────

_TRUST_PATTERNS = [
    r"SOC\s*2", r"ISO\s*\d+", r"GDPR", r"HIPAA", r"CCPA",
    r"PCI\s*DSS", r"FedRAMP", r"AICPA",
    r"\d+[\+]?\s*(?:reviews?|ratings?|stars?)",
    r"(?:G2|Capterra|Trustpilot|Gartner|Forrester)",
    r"(?:Award|Winner|Top\s+\d+|Leader\s+in)",
    r"(?:trusted|verified|certified|approved)\s+by",
    r"(?:Money-back|Guarantee|No\s+credit\s+card)",
]
_TRUST_RE = re.compile("|".join(_TRUST_PATTERNS), re.IGNORECASE)


# ── Screenshot path → URL ─────────────────────────────────────────────────────

def _screenshot_url(path_str: Optional[str]) -> Optional[str]:
    if not path_str:
        return None
    # Convert absolute path to relative screenshots/... portion
    import re as _re
    m = _re.search(r"screenshots[\\/].+", path_str)
    if m:
        return m.group(0).replace("\\", "/")
    return path_str


# ── Builders per visual type ──────────────────────────────────────────────────

def _build_ctas(visual_elements: list["VisualElement"]) -> list[VisualItem]:
    items: list[VisualItem] = []
    for i, el in enumerate(visual_elements):
        if el.element_type != "button":
            continue
        text = el.text.strip()
        if not text or len(text) > 80:
            continue
        # Hero section CTAs are highest value
        in_hero = el.section_type in ("hero", "cta")
        importance = IMPORTANCE["hero_cta"] if in_hero else IMPORTANCE["secondary_cta"]
        items.append(VisualItem(
            id=f"cta_{i}",
            type="cta",
            text=text,
            importance=importance,
            section=el.section_type,
            screenshot=_screenshot_url(str(el.screenshot_path) if el.screenshot_path else None),
            metadata={"bounding_box": el.bounding_box},
        ))
    return sorted(items, key=lambda x: x.importance, reverse=True)


def _build_pricing(visual_elements: list["VisualElement"]) -> list[VisualItem]:
    items: list[VisualItem] = []
    for i, el in enumerate(visual_elements):
        if el.element_type not in ("pricing", "card"):
            continue
        text = el.text.strip()
        if not text:
            continue
        is_pricing = el.element_type == "pricing" or el.section_type == "pricing"
        if not is_pricing:
            continue
        items.append(VisualItem(
            id=f"pricing_{i}",
            type="pricing",
            text=text[:120],
            importance=IMPORTANCE["pricing_card"],
            section=el.section_type,
            screenshot=_screenshot_url(str(el.screenshot_path) if el.screenshot_path else None),
        ))
    return items


def _build_feature_cards(visual_elements: list["VisualElement"]) -> list[VisualItem]:
    items: list[VisualItem] = []
    for i, el in enumerate(visual_elements):
        if el.element_type != "card" or el.section_type == "pricing":
            continue
        text = el.text.strip()
        if not text or len(text) < 8:
            continue
        items.append(VisualItem(
            id=f"feature_{i}",
            type="feature",
            text=text[:100],
            importance=IMPORTANCE["feature_card"],
            section=el.section_type,
            screenshot=_screenshot_url(str(el.screenshot_path) if el.screenshot_path else None),
        ))
    return items[:6]


def _build_testimonials(
    visual_elements: list["VisualElement"],
    sections: list["SectionData"],
) -> list[VisualItem]:
    items: list[VisualItem] = []

    # From visual elements
    for i, el in enumerate(visual_elements):
        if el.element_type != "testimonial":
            continue
        text = el.text.strip()
        if text and len(text) >= 20:
            items.append(VisualItem(
                id=f"testimonial_{i}",
                type="testimonial",
                text=text[:200],
                importance=IMPORTANCE["testimonial"],
                section=el.section_type,
                screenshot=_screenshot_url(str(el.screenshot_path) if el.screenshot_path else None),
            ))

    # From sections text (fallback)
    for sec in sections:
        if sec.section_type == "testimonials" and sec.text and not items:
            items.append(VisualItem(
                id="testimonial_sec",
                type="testimonial",
                text=sec.text[:200],
                importance=IMPORTANCE["testimonial"],
                section="testimonials",
                screenshot=_screenshot_url(str(sec.screenshot_path) if sec.screenshot_path else None),
            ))

    return items[:4]


def _build_widgets(visual_elements: list["VisualElement"]) -> list[VisualItem]:
    items: list[VisualItem] = []
    for i, el in enumerate(visual_elements):
        if el.element_type != "widget":
            continue
        text = el.text.strip()
        items.append(VisualItem(
            id=f"widget_{i}",
            type="widget",
            text=text[:80],
            importance=IMPORTANCE["dashboard_widget"],
            section=el.section_type,
            screenshot=_screenshot_url(str(el.screenshot_path) if el.screenshot_path else None),
        ))
    return items[:4]


def _build_metrics_items(ranked_metrics: list["ExtractedMetric"]) -> list[VisualItem]:
    items: list[VisualItem] = []
    for i, m in enumerate(ranked_metrics[:8]):
        items.append(VisualItem(
            id=f"metric_{i}",
            type="metric",
            text=m.value,
            importance=m.importance,
            section=m.section,
            screenshot=None,
            metadata={
                "label":       m.label,
                "metric_type": m.type,
                "context":     m.context,
                "source":      m.source,
            },
        ))
    return items


def _build_trust_indicators(sections: list["SectionData"]) -> list[VisualItem]:
    items: list[VisualItem] = []
    seen: set[str] = set()

    for sec in sections:
        all_text = " ".join(filter(None, [sec.heading, sec.subheading, sec.text]))
        for m in _TRUST_RE.finditer(all_text):
            snippet = m.group(0).strip()
            if snippet and snippet not in seen:
                seen.add(snippet)
                items.append(VisualItem(
                    id=f"trust_{len(items)}",
                    type="trust",
                    text=snippet,
                    importance=IMPORTANCE["trust_indicator"],
                    section=sec.section_type,
                    screenshot=None,
                ))
                if len(items) >= 6:
                    return items

    return items


def _build_logos(visual_elements: list["VisualElement"]) -> list[VisualItem]:
    items: list[VisualItem] = []
    for i, el in enumerate(visual_elements):
        if el.element_type != "hero":
            continue
        # Heuristic: very small elements in hero sections are likely logos
        bb = el.bounding_box
        if bb.get("height", 0) < 60 and bb.get("width", 0) < 200:
            items.append(VisualItem(
                id=f"logo_{i}",
                type="logo",
                text=el.text.strip()[:40],
                importance=IMPORTANCE["logo"],
                section=el.section_type,
                screenshot=_screenshot_url(str(el.screenshot_path) if el.screenshot_path else None),
            ))
    return items[:3]


# ── Public entry point ────────────────────────────────────────────────────────

def build_visual_inventory(
    sections: list["SectionData"],
    visual_elements: list["VisualElement"],
    ranked_metrics: list["ExtractedMetric"],
) -> VisualInventory:
    """
    Build the full VisualInventory from all available data.

    Called after DOM scraping and metrics extraction are complete.
    Pure function — no browser, no I/O.
    """
    inventory = VisualInventory(
        ctas              = _build_ctas(visual_elements),
        pricing_cards     = _build_pricing(visual_elements),
        feature_cards     = _build_feature_cards(visual_elements),
        testimonials      = _build_testimonials(visual_elements, sections),
        dashboard_widgets = _build_widgets(visual_elements),
        metrics           = _build_metrics_items(ranked_metrics),
        trust_indicators  = _build_trust_indicators(sections),
        logos             = _build_logos(visual_elements),
    )

    print(f"[VIE] Visual inventory: {inventory.summary()}", flush=True)
    return inventory
