"""
scene_designer.py – Scene Designer Layer for Promoly.

Sits between apply_style() and plan_motion() in the pipeline.

Input  : remotion_props (scenes with componentType/componentRole already set)
Output : same shape, each scene gains a `sceneDesign` dict describing:
            concept            – detected primary concept ("growth", "security", …)
            visualMetaphor     – specific visual treatment ("growth-chart", "shield", …)
            primaryComponent   – hero Remotion component name
            secondaryComponents – supporting components list
            background         – background component name
            motionEnergy       – "low" | "medium" | "high" | "explosive"
            density            – "minimal" | "standard" | "dense"
            accentVariant      – "default" | "success" | "warning" | "danger"
            badgeTexts         – suggested badge chip labels

The design drives:
  • motion_planner.py  – motionComponent selection + zoom/badge intensity
  • MotionGraphicsScene.tsx – layout variant within each scene type
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

# ── Concept keyword taxonomy ──────────────────────────────────────────────────
# Maps concept name → trigger words (case-insensitive, partial match)

CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "speed": [
        "fast", "speed", "instant", "quick", "rapid", "10x", "2x", "3x",
        "save time", "minutes", "seconds", "accelerate", "boost", "lightning",
        "real-time", "realtime", "zero latency", "latency",
    ],
    "growth": [
        "scale", "grow", "growth", "increase", "expand", "revenue", "mrr",
        "users", "traffic", "10x", "100x", "rocket", "skyrocket", "upward",
        "trend", "chart", "more customers", "acquisition",
    ],
    "security": [
        "secure", "security", "safe", "protect", "privacy", "encrypt",
        "compliant", "compliance", "soc 2", "gdpr", "hipaa", "trust",
        "zero trust", "end-to-end", "lock", "shield", "vault",
    ],
    "automation": [
        "automate", "automation", "automatic", "workflow", "hands-free",
        "no-code", "low-code", "ai", "ai-powered", "trigger", "integrate",
        "connect", "pipeline", "orchestrate", "schedule", "sync",
    ],
    "savings": [
        "save", "cost", "price", "affordable", "roi", "return", "cut costs",
        "reduce", "cheaper", "free", "trial", "money", "budget", "spend",
    ],
    "simplicity": [
        "simple", "easy", "one-click", "intuitive", "drag", "drop",
        "minutes to set up", "no coding", "effortless", "just works",
        "out of the box", "plug and play",
    ],
    "social_proof": [
        "customers", "trusted", "review", "rating", "stars", "testimonial",
        "case study", "users love", "join", "teams use", "companies",
    ],
    "performance": [
        "uptime", "reliable", "99%", "sla", "performance", "throughput",
        "requests", "concurrent", "handles", "never goes down",
    ],
    "collaboration": [
        "team", "collaborate", "share", "together", "workspace", "invite",
        "comment", "assign", "mention", "slack", "notification",
    ],
    "analytics": [
        "analytics", "data", "insight", "dashboard", "report", "metric",
        "track", "measure", "monitor", "graph", "chart", "kpi",
    ],
}

# Scene-type concept priors — when no strong signal from text, use these
SCENE_TYPE_CONCEPT: dict[str, str] = {
    "hook":         "growth",
    "problem":      "simplicity",
    "solution":     "simplicity",
    "features":     "performance",
    "benefits":     "growth",
    "testimonials": "social_proof",
    "cta":          "growth",
    "hero":         "growth",
    "content":      "performance",
}

# ── Visual metaphor lookup ────────────────────────────────────────────────────
# Maps concept → list of candidate metaphors (first is preferred)

CONCEPT_METAPHORS: dict[str, list[str]] = {
    "speed":        ["speed-lines",    "progress-bar",   "clock"],
    "growth":       ["growth-chart",   "upward-trend",   "rocket"],
    "security":     ["shield",         "lock-badge",     "trust-card"],
    "automation":   ["workflow-nodes", "gear",           "connected-flow"],
    "savings":      ["metric-counter", "roi-chart",      "badge-savings"],
    "simplicity":   ["step-flow",      "checkmarks",     "progress-bar"],
    "social_proof": ["quote-card",     "star-rating",    "verified-badge"],
    "performance":  ["metric-counter", "uptime-bar",     "pulse-graph"],
    "collaboration": ["user-avatars",  "activity-feed",  "checkmarks"],
    "analytics":    ["growth-chart",   "metric-counter", "uptime-bar"],
}

# ── Component prescriptions per metaphor ──────────────────────────────────────

@dataclass
class ComponentPrescription:
    primary: str
    secondary: list[str]
    background: str
    energy: str          # "low" | "medium" | "high" | "explosive"
    density: str         # "minimal" | "standard" | "dense"
    accent: str          # "default" | "success" | "warning" | "danger"

METAPHOR_COMPONENTS: dict[str, ComponentPrescription] = {
    # ── Speed ──
    "speed-lines": ComponentPrescription(
        primary="MetricCounter", secondary=["FloatingBadge", "ProgressBar"],
        background="AnimatedGrid", energy="high", density="standard", accent="default",
    ),
    "progress-bar": ComponentPrescription(
        primary="ProgressBar", secondary=["MetricCounter", "FloatingBadge"],
        background="AnimatedGrid", energy="medium", density="standard", accent="default",
    ),
    "clock": ComponentPrescription(
        primary="MetricCounter", secondary=["FloatingBadge"],
        background="ParticleField", energy="high", density="minimal", accent="default",
    ),

    # ── Growth ──
    "growth-chart": ComponentPrescription(
        primary="MetricCounter", secondary=["FloatingBadge", "ProgressBar"],
        background="ParticleField", energy="high", density="dense", accent="success",
    ),
    "upward-trend": ComponentPrescription(
        primary="MetricCounter", secondary=["FloatingBadge"],
        background="ParticleField", energy="explosive", density="dense", accent="success",
    ),
    "rocket": ComponentPrescription(
        primary="KineticHeadline", secondary=["MetricCounter", "FloatingBadge"],
        background="ParticleField", energy="explosive", density="dense", accent="success",
    ),

    # ── Security ──
    "shield": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge", "TrustBadge"],
        background="AnimatedGrid", energy="low", density="standard", accent="default",
    ),
    "lock-badge": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge"],
        background="AnimatedGrid", energy="low", density="minimal", accent="default",
    ),
    "trust-card": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge", "ProgressBar"],
        background="AnimatedGrid", energy="medium", density="standard", accent="default",
    ),

    # ── Automation ──
    "workflow-nodes": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge", "ProgressBar"],
        background="AnimatedGrid", energy="medium", density="dense", accent="default",
    ),
    "gear": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge"],
        background="AnimatedGrid", energy="medium", density="standard", accent="default",
    ),
    "connected-flow": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge", "ProgressBar"],
        background="AnimatedGrid", energy="high", density="dense", accent="default",
    ),

    # ── Savings ──
    "metric-counter": ComponentPrescription(
        primary="MetricCounter", secondary=["FloatingBadge", "ProgressBar"],
        background="ParticleField", energy="high", density="standard", accent="success",
    ),
    "roi-chart": ComponentPrescription(
        primary="MetricCounter", secondary=["ProgressBar", "FloatingBadge"],
        background="ParticleField", energy="high", density="dense", accent="success",
    ),
    "badge-savings": ComponentPrescription(
        primary="FloatingBadge", secondary=["MetricCounter"],
        background="GlowBackground", energy="medium", density="minimal", accent="success",
    ),

    # ── Simplicity ──
    "step-flow": ComponentPrescription(
        primary="FeatureCard", secondary=["ProgressBar", "FloatingBadge"],
        background="AnimatedGrid", energy="medium", density="standard", accent="default",
    ),
    "checkmarks": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge"],
        background="GlowBackground", energy="medium", density="standard", accent="success",
    ),

    # ── Social proof ──
    "quote-card": ComponentPrescription(
        primary="QuoteCard", secondary=["StarRating", "FloatingBadge"],
        background="GlowBackground", energy="low", density="minimal", accent="default",
    ),
    "star-rating": ComponentPrescription(
        primary="QuoteCard", secondary=["StarRating", "FloatingBadge"],
        background="ParticleField", energy="medium", density="standard", accent="default",
    ),
    "verified-badge": ComponentPrescription(
        primary="QuoteCard", secondary=["FloatingBadge"],
        background="GlowBackground", energy="low", density="minimal", accent="default",
    ),

    # ── Performance ──
    "uptime-bar": ComponentPrescription(
        primary="MetricCounter", secondary=["ProgressBar", "FloatingBadge"],
        background="AnimatedGrid", energy="high", density="dense", accent="default",
    ),
    "pulse-graph": ComponentPrescription(
        primary="MetricCounter", secondary=["FloatingBadge"],
        background="ParticleField", energy="high", density="standard", accent="default",
    ),

    # ── Collaboration ──
    "user-avatars": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge", "MetricCounter"],
        background="GlowBackground", energy="medium", density="standard", accent="default",
    ),
    "activity-feed": ComponentPrescription(
        primary="FeatureCard", secondary=["FloatingBadge"],
        background="AnimatedGrid", energy="medium", density="dense", accent="default",
    ),

    # ── Analytics ──
}

# Fallback prescription
_DEFAULT_PRESCRIPTION = ComponentPrescription(
    primary="FeatureCard", secondary=["FloatingBadge"],
    background="GlowBackground", energy="medium", density="standard", accent="default",
)

# ── Badge text suggestions per concept ────────────────────────────────────────

CONCEPT_BADGES: dict[str, list[str]] = {
    "speed":        ["Instant", "10× Faster", "Real-Time"],
    "growth":       ["Scale Up", "Growing Fast", "Top Rated"],
    "security":     ["Trusted", "SOC 2", "Secure"],
    "automation":   ["Automated", "Zero Manual Work", "AI-Powered"],
    "savings":      ["Save 40%", "Free Trial", "ROI Proven"],
    "simplicity":   ["Easy Setup", "No Code", "5 Min Setup"],
    "social_proof": ["Verified", "5-Star", "10K+ Users"],
    "performance":  ["99.9% Uptime", "Enterprise Grade", "Reliable"],
    "collaboration": ["Team Ready", "Collaborate", "Share Instantly"],
    "analytics":    ["Data-Driven", "Live Insights", "Real-Time"],
}

# ── Scene-level energy overrides ──────────────────────────────────────────────
# Force certain scene types to specific energy regardless of concept

SCENE_TYPE_ENERGY_OVERRIDE: dict[str, str] = {
    "hook":         "explosive",   # opener must grab attention
    "cta":          "high",        # CTA must feel urgent
    "testimonials": "low",         # testimonials should feel authentic/calm
    "problem":      "medium",      # problem should feel tense but not chaotic
}

# ── Scorer ────────────────────────────────────────────────────────────────────

_NONWORD = re.compile(r"[^a-z0-9 ]+")


def _score_concepts(text: str) -> dict[str, float]:
    """
    Score each concept by keyword hits in text.
    Returns {concept: score} (higher = better match).
    """
    clean = _NONWORD.sub(" ", text.lower())
    scores: dict[str, float] = {}
    for concept, keywords in CONCEPT_KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            if kw in clean:
                # Longer keyword phrases score more
                score += 1.0 + len(kw.split()) * 0.3
        scores[concept] = score
    return scores


def _detect_concept(scene: dict) -> str:
    """
    Detect the primary concept from scene content.
    Falls back to scene-type prior when no keyword hits.
    """
    parts = [
        scene.get("headline", ""),
        scene.get("subheadline", ""),
        scene.get("narration", ""),
        scene.get("badge", ""),
        " ".join(str(b) for b in (scene.get("bullets") or [])),
        scene.get("bodyText", "") or "",
        " ".join(str(b) for b in (scene.get("checkpoints") or [])),
        " ".join(str(b) for b in (scene.get("painPoints") or [])),
        scene.get("quote", "") or "",
    ]
    combined = " ".join(str(p) for p in parts if p)
    scores = _score_concepts(combined)

    best_concept = max(scores, key=lambda k: scores[k]) if scores else None
    if best_concept and scores[best_concept] > 0.5:
        return best_concept

    # Fall back to scene-type prior
    return SCENE_TYPE_CONCEPT.get(scene.get("type", "hero"), "growth")


def _pick_metaphor(concept: str, scene_type: str) -> str:
    """
    Pick the best visual metaphor for this concept + scene type combination.
    Social-proof scene types always prefer quote-card regardless of concept.
    """
    if scene_type == "testimonials":
        return "quote-card"
    if scene_type == "cta":
        return "metric-counter"   # urgency / value counter
    candidates = CONCEPT_METAPHORS.get(concept, ["growth-chart"])
    return candidates[0]


def _suggest_badges(concept: str, scene: dict) -> list[str]:
    """
    Pick 2-3 badge chip labels from concept suggestions, plus the scene's own badge.
    """
    suggestions = CONCEPT_BADGES.get(concept, ["Featured", "Proven"])[:2]
    own_badge = scene.get("badge", "")
    if own_badge and own_badge not in suggestions:
        suggestions = [own_badge] + suggestions
    return suggestions[:3]


# ── Public API ────────────────────────────────────────────────────────────────

def design_scene(scene: dict) -> dict:
    """
    Produce a SceneDesign dict for a single scene.
    Pure function — does not mutate the input scene.
    """
    scene_type = scene.get("type", "hero")

    concept  = _detect_concept(scene)
    metaphor = _pick_metaphor(concept, scene_type)
    pres     = METAPHOR_COMPONENTS.get(metaphor, _DEFAULT_PRESCRIPTION)

    # Apply scene-type energy override
    energy = SCENE_TYPE_ENERGY_OVERRIDE.get(scene_type, pres.energy)

    return {
        "concept":             concept,
        "visualMetaphor":      metaphor,
        "primaryComponent":    pres.primary,
        "secondaryComponents": pres.secondary,
        "background":          pres.background,
        "motionEnergy":        energy,
        "density":             pres.density,
        "accentVariant":       pres.accent,
        "badgeTexts":          _suggest_badges(concept, scene),
    }


def design_scenes(remotion_props: dict) -> dict:
    """
    Inject a `sceneDesign` dict into every scene in remotion_props.

    Called AFTER apply_style(), BEFORE plan_motion().
    Does not mutate the input dict.
    """
    scenes  = remotion_props.get("scenes", [])
    designed: list[dict] = []

    for scene in scenes:
        sd = design_scene(scene)
        designed.append({**scene, "sceneDesign": sd})
        print(
            f"[SceneDesigner] scene={scene.get('type','?'):12s} "
            f"concept={sd['concept']:14s} "
            f"metaphor={sd['visualMetaphor']:18s} "
            f"energy={sd['motionEnergy']}",
            flush=True,
        )

    return {**remotion_props, "scenes": designed}
