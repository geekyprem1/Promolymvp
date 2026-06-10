"""
story_extractor.py – Marketing Story Extraction layer.

Extracts a structured narrative (StoryData) from raw DOM text, page metadata,
and detected sections.  No AI required — pure heuristic extraction.

The StoryData is then fed to Gemini so it generates scenes from a
*marketing narrative arc* instead of mirroring website section structure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detector import SectionData

# ── Keyword banks ─────────────────────────────────────────────────────────────

PAIN_WORDS = [
    "struggle", "manual", "waste", "wast", "slow", "slowl", "hard", "difficult",
    "frustrat", "tedious", "complex", "confus", "scatter", "silos", "siloed",
    "broken", "outdated", "inefficient", "bottleneck", "switching", "juggling",
    "too many tools", "context switch", "disconnected", "disjointed", "painful",
    "error-prone", "error prone", "repetitive", "hours", "days wasted",
    "can't keep up", "falling behind", "missed deadlines",
]

OUTCOME_VERBS = [
    "save", "reduce", "increase", "improve", "boost", "accelerate", "automate",
    "simplify", "streamline", "eliminate", "replace", "ship", "launch", "deploy",
    "scale", "grow", "achieve", "deliver", "transform",
]

SOCIAL_PROOF_PATTERNS = [
    r"\b\d[\d,]+\s*\+?\s*(?:users?|teams?|companies|customers|businesses|organizations|startups)",
    r"\b\d+(?:\.\d+)?\s*(?:stars?|★|\/5|out of 5)",
    r"\b\d+\s*%\s*(?:faster|more|better|reduction|increase|improvement|saved|less)",
    r"\b(?:G2|Capterra|Trustpilot|Product\s*Hunt|Gartner|Forrester)",
    r"\b(?:trusted|used|loved|chosen|relied on)\s+by\b",
    r"\$\s*\d[\d,\.]+\s*(?:M|B|million|billion)?\s*(?:saved|generated|revenue)",
    r"\b\d+\s*(?:awards?|reviews?|ratings?)",
]

# Words that suggest a headline is problem-framing rather than solution-framing
PROBLEM_INDICATORS = [
    "without", "no more", "never again", "stop ", "end the", "tired of",
    "why are you still", "the problem with", "what's holding",
]

METRIC_PATTERN = re.compile(
    r"(\d[\d,\.]*\s*(?:%|x|\+|k|K|M|B)?\s*(?:faster|more|less|better|saved?|reduction|users?|teams?|companies|customers)?)",
    re.IGNORECASE,
)

QUOTE_PATTERN = re.compile(r'["“‘](.{20,200})["”’]', re.DOTALL)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class StoryData:
    problem:         str = ""
    solution:        str = ""
    target_audience: str = ""
    benefits:        list[str] = field(default_factory=list)
    social_proof:    list[str] = field(default_factory=list)
    cta:             str = ""
    hook:            str = ""
    product_name:    str = ""
    metrics:         list[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """Serialize for inclusion in Gemini prompt."""
        lines = [
            f"Hook:            {self.hook}",
            f"Problem:         {self.problem}",
            f"Solution:        {self.solution}",
            f"Product name:    {self.product_name}",
            f"Target audience: {self.target_audience}",
            f"Benefits:        {' | '.join(self.benefits[:5])}",
            f"Key metrics:     {' | '.join(self.metrics[:4])}",
            f"Social proof:    {' | '.join(self.social_proof[:4])}",
            f"CTA:             {self.cta}",
        ]
        return "\n".join(lines)

    def is_rich(self) -> bool:
        """True if we have enough story data to use the story-arc prompt."""
        return bool(self.problem and self.solution and len(self.benefits) >= 1)


# ── Helper utilities ──────────────────────────────────────────────────────────

def _clean(s: str, maxlen: int = 200) -> str:
    return re.sub(r"\s+", " ", s or "").strip()[:maxlen]


def _all_text(sections: list["SectionData"]) -> str:
    parts = []
    for s in sections:
        for part in (s.heading, s.subheading, s.text):
            if part:
                parts.append(part)
    return " ".join(parts)


def _section_text(sections: list["SectionData"], *types: str) -> str:
    parts = []
    for s in sections:
        if s.section_type in types:
            for part in (s.heading, s.subheading, s.text):
                if part:
                    parts.append(part)
    return " ".join(parts)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.!?]\s+", text) if len(s.strip()) > 15]


def _score_pain(sentence: str) -> int:
    low = sentence.lower()
    return sum(1 for w in PAIN_WORDS if w in low)


def _extract_metrics(text: str) -> list[str]:
    hits = METRIC_PATTERN.findall(text)
    seen: set[str] = set()
    out: list[str] = []
    for h in hits:
        h = h.strip()
        if h and h not in seen and len(h) > 1:
            seen.add(h)
            out.append(h)
    return out[:6]


# ── Extraction sub-functions ──────────────────────────────────────────────────

def _extract_product_name(meta: dict) -> str:
    domain = meta.get("domain", "")
    # Remove TLD and capitalise
    name = re.sub(r"\.(com|io|co|app|dev|net|org|ai)$", "", domain, flags=re.I)
    if name:
        return name.replace("-", " ").replace("_", " ").title()
    title = meta.get("title", "")
    # Take first word before " – " or " | " or " - "
    first = re.split(r"\s[–\-|]\s", title)[0].strip()
    return first[:40] if first else "Product"


def _extract_problem(meta: dict, sections: list["SectionData"]) -> str:
    # Search each section's text field independently (avoids heading/text bleed)
    candidate_pools: list[str] = []
    for s in sections:
        for field in (s.text, s.subheading, s.heading):
            if field and len(field.strip()) > 15:
                candidate_pools.append(field)

    # 1. Explicit problem-framing sentences
    for pool in candidate_pools:
        for sent in _sentences(pool):
            low = sent.lower()
            for ind in PROBLEM_INDICATORS:
                if ind in low and 15 < len(sent) < 160:
                    return _clean(sent, 160)

    # 2. Sentences with 2+ pain keywords in individual fields
    all_sentences: list[str] = []
    for pool in candidate_pools:
        all_sentences.extend(_sentences(pool))

    scored = sorted(all_sentences, key=_score_pain, reverse=True)
    for sent in scored:
        if _score_pain(sent) >= 2 and 15 < len(sent) < 160:
            return _clean(sent, 160)

    # 3. Single pain-keyword sentence
    for sent in scored:
        if _score_pain(sent) >= 1 and 15 < len(sent) < 160:
            return _clean(sent, 160)

    # 4. Hero subheading as last resort
    for s in sections:
        if s.section_type == "hero" and s.subheading and len(s.subheading) > 10:
            return _clean(s.subheading, 160)

    return ""


def _extract_solution(meta: dict, sections: list["SectionData"]) -> str:
    # Best sources in priority order: og:description > h1 > hero heading > title
    for key in ("og_desc", "og_title", "description", "h1", "title"):
        val = (meta.get(key) or "").strip()
        if val and len(val) > 10:
            return _clean(val, 200)

    hero = next((s for s in sections if s.section_type == "hero"), None)
    if hero and hero.heading:
        return _clean(hero.heading, 160)

    return ""


def _extract_target_audience(meta: dict, sections: list["SectionData"]) -> str:
    all_text = _all_text(sections)
    # Look for "for X" patterns
    m = re.search(
        r"\bfor\s+((?:[\w\s]+?)?(?:teams?|developers?|designers?|managers?|"
        r"startups?|businesses?|companies|enterprises?|agencies?))",
        all_text, re.IGNORECASE,
    )
    if m:
        return _clean(m.group(1), 60)

    # Look for "built for" / "made for" / "designed for"
    m2 = re.search(
        r"\b(?:built|made|designed|created|perfect)\s+for\s+([^.!?]{5,60})",
        all_text, re.IGNORECASE,
    )
    if m2:
        return _clean(m2.group(1), 60)

    return "teams and businesses"


def _extract_benefits(sections: list["SectionData"]) -> list[str]:
    """Pull outcome-oriented bullet points from features/benefits sections."""
    benefits: list[str] = []
    seen: set[str] = set()

    target_sections = [s for s in sections if s.section_type in ("features", "benefits", "demo")]

    for sec in target_sections:
        # Split on newlines, bullets, periods (to handle run-on sentences with metrics)
        raw_lines = re.split(r"[\n\r•·→▶✓✔✗✘⚡]|\s{3,}|\.\s+", sec.text or "")
        for line in raw_lines:
            line = _clean(line, 100)
            if len(line) < 8 or len(line) > 100:
                continue
            low = line.lower()
            has_outcome = any(v in low for v in OUTCOME_VERBS)
            has_metric  = bool(METRIC_PATTERN.search(line))
            if (has_outcome or has_metric) and line not in seen:
                seen.add(line)
                benefits.append(line)
                if len(benefits) >= 5:
                    break
        if len(benefits) >= 5:
            break

    # Fallback: any non-trivial line from target sections
    if len(benefits) < 2:
        for sec in target_sections:
            for line in re.split(r"[\n\r•·→\.\s{3,}]", sec.text or ""):
                line = _clean(line, 80)
                if 8 < len(line) < 80 and line not in seen:
                    seen.add(line)
                    benefits.append(line)
                    if len(benefits) >= 4:
                        break

    return benefits[:5]


def _extract_social_proof(sections: list["SectionData"]) -> list[str]:
    proof: list[str] = []
    seen: set[str] = set()
    all_text = _all_text(sections)

    # Pattern matches — keep only the matched phrase + minimal right context
    for pattern in SOCIAL_PROOF_PATTERNS:
        for m in re.finditer(pattern, all_text, re.IGNORECASE):
            # Extend to end of clause
            end = min(len(all_text), m.end() + 50)
            clause_end = re.search(r"[.!?\n]", all_text[m.end():m.end() + 50])
            if clause_end:
                end = m.end() + clause_end.start()
            snippet = _clean(all_text[m.start():end], 100)
            if not snippet or len(snippet) < 5:
                continue
            # Skip if any existing proof item contains this snippet or vice versa
            is_dupe = any(snippet in existing or existing in snippet for existing in seen)
            if not is_dupe:
                seen.add(snippet)
                proof.append(snippet)
            if len(proof) >= 4:
                break

    # Testimonial quotes (prefer full quoted text)
    testimonial_text = _section_text(sections, "testimonials")
    for m in QUOTE_PATTERN.finditer(testimonial_text):
        quote = _clean(m.group(1), 120)
        if quote and quote not in seen:
            seen.add(quote)
            proof.append(f'"{quote}"')
        if len(proof) >= 5:
            break

    return proof[:5]


def _extract_cta(sections: list["SectionData"]) -> str:
    cta_sec = next((s for s in sections if s.section_type == "cta"), None)
    if cta_sec:
        for text in (cta_sec.heading, cta_sec.subheading, cta_sec.text):
            if text and len(text.strip()) > 4:
                # Take first sentence / line
                first = re.split(r"[\n.!]", text)[0].strip()
                if first:
                    return _clean(first, 80)

    # Generic fallback
    all_text = _all_text(sections)
    m = re.search(
        r"\b((?:start|get started|try|sign up|join|begin)\s+[^.!?\n]{3,50})",
        all_text, re.IGNORECASE,
    )
    if m:
        return _clean(m.group(1), 80)

    return "Get Started Free"


def _synthesize_hook(
    problem: str,
    solution: str,
    benefits: list[str],
    metrics: list[str],
    product_name: str,
) -> str:
    """
    Produce a punchy one-liner hook:
    - If there's a strong metric: "Join [N] teams who [outcome]"
    - If there's a clear pain: "Stop [pain]. Start [solution]."
    - Default: "What if you could [best benefit]?"
    """
    # Prefer metric-anchored hook
    if metrics:
        m = metrics[0]
        if benefits:
            # Use a short version of the first benefit (first 5 words)
            words = benefits[0].split()[:5]
            verb_phrase = " ".join(words).lower().rstrip(".,")
            return f"Join the teams who {verb_phrase} — with {product_name}"

    # Pain-then-relief hook
    if problem and solution:
        pain_short = re.split(r"[,\.]", problem)[0].strip()[:60]
        sol_short  = solution[:50].strip()
        if pain_short and sol_short:
            return f"Stop {pain_short.lower()}. Meet {product_name}."

    # Benefit-led hook
    if benefits:
        return f"What if you could {benefits[0].lower()}?"

    # Solution-led hook
    if solution:
        return solution[:80]

    return f"Discover what {product_name} can do for your team"


# ── Public entry point ────────────────────────────────────────────────────────

def extract_story(meta: dict, sections: list["SectionData"]) -> StoryData:
    """
    Extract a structured marketing story from page metadata and detected sections.

    Returns a StoryData instance.  All fields have fallback values — the result
    is always safe to pass to the Gemini prompt builder even if extraction was
    sparse.
    """
    product_name = _extract_product_name(meta)
    solution     = _extract_solution(meta, sections)
    problem      = _extract_problem(meta, sections)
    audience     = _extract_target_audience(meta, sections)
    benefits     = _extract_benefits(sections)
    proof        = _extract_social_proof(sections)
    cta          = _extract_cta(sections)
    metrics      = _extract_metrics(_all_text(sections))

    hook = _synthesize_hook(problem, solution, benefits, metrics, product_name)

    return StoryData(
        problem         = problem,
        solution        = solution,
        target_audience = audience,
        benefits        = benefits,
        social_proof    = proof,
        cta             = cta,
        hook            = hook,
        product_name    = product_name,
        metrics         = metrics,
    )
