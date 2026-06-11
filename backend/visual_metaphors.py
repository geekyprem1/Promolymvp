"""
visual_metaphors.py – Visual Metaphor Registry for Promoly.

Single source of truth for:
  • concept keyword taxonomy  (what words trigger each concept)
  • concept → metaphor mapping (ordered by preference)
  • metaphor → component spec  (what Remotion component + settings to use)
  • concept → badge suggestions

Adding a new metaphor:
  1. Add a MetaphorSpec entry to METAPHOR_REGISTRY.
  2. Add the Remotion component to MetaphorRenderer.tsx METAPHOR_MAP.
  That is the entire change required — the pipeline is unaffected.

Imported by:
  scene_designer.py  →  resolve_metaphor(), get_spec()
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── Concept keyword taxonomy ──────────────────────────────────────────────────

CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "speed": [
        "fast", "speed", "instant", "quick", "rapid", "10x", "2x", "3x",
        "save time", "minutes", "seconds", "accelerate", "boost", "lightning",
        "real-time", "realtime", "zero latency", "latency",
    ],
    "growth": [
        "scale", "grow", "growth", "increase", "expand", "revenue", "mrr",
        "users", "traffic", "100x", "rocket", "skyrocket", "upward",
        "trend", "chart", "more customers", "acquisition",
    ],
    "security": [
        "secure", "security", "safe", "protect", "privacy", "encrypt",
        "compliant", "compliance", "soc 2", "gdpr", "hipaa", "trust",
        "zero trust", "end-to-end", "lock", "shield", "vault",
    ],
    "automation": [
        "automate", "automation", "automatic", "workflow", "hands-free",
        "no-code", "low-code", "trigger", "integrate", "connect",
        "pipeline", "orchestrate", "schedule", "sync", "integrate",
    ],
    "ai": [
        "ai", "artificial intelligence", "machine learning", "ml", "gpt",
        "llm", "neural", "intelligent", "smart", "ai-powered",
        "generative", "predict", "model", "embedding",
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
    "scale": [
        "scale", "global", "enterprise", "millions", "worldwide", "regions",
        "distributed", "cluster", "infrastructure", "cloud",
    ],
    "trust": [
        "trust", "reliable", "honest", "transparent", "verified", "certified",
        "audit", "compliance", "soc", "iso", "guarantee",
    ],
}

# Scene-type concept priors
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

# ── Metaphor spec ─────────────────────────────────────────────────────────────

@dataclass
class MetaphorSpec:
    id: str
    concept: str
    component: str          # Remotion component name (must exist in MetaphorRenderer.tsx)
    label: str              # Human-readable label
    energy: str             # "low" | "medium" | "high" | "explosive"
    density: str            # "minimal" | "standard" | "dense"
    accent: str             # "default" | "success" | "warning" | "danger"
    background: str         # "ParticleField" | "AnimatedGrid" | "GlowBackground"
    primary_component: str  # recommended Remotion data component
    secondary_components: list[str] = field(default_factory=list)
    badge_texts: list[str]  = field(default_factory=list)
    motion_intensity: float = 0.7  # 0.0-1.0 passed to the Remotion component


# ── Registry ──────────────────────────────────────────────────────────────────
# Adding a new metaphor: add one MetaphorSpec here.

METAPHOR_REGISTRY: dict[str, MetaphorSpec] = {

    # ── Growth ────────────────────────────────────────────────────────────────
    "rocket": MetaphorSpec(
        id="rocket", concept="growth", component="RocketAnimation",
        label="Rocket Launch", energy="explosive", density="dense",
        accent="success", background="ParticleField",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["Scale Up", "Growing Fast", "Top Rated"],
        motion_intensity=1.0,
    ),
    "growth-chart": MetaphorSpec(
        id="growth-chart", concept="growth", component="GrowthChart",
        label="Growth Chart", energy="high", density="dense",
        accent="success", background="ParticleField",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["300% Growth", "Trending Up", "Top Rated"],
        motion_intensity=0.8,
    ),
    "upward-arrow": MetaphorSpec(
        id="upward-arrow", concept="growth", component="GrowthChart",
        label="Upward Trend", energy="high", density="standard",
        accent="success", background="ParticleField",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge"],
        badge_texts=["Scale Up", "Growing Fast"],
        motion_intensity=0.75,
    ),
    "expanding-circles": MetaphorSpec(
        id="expanding-circles", concept="scale", component="ExpandingCircles",
        label="Expanding Scale", energy="high", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge"],
        badge_texts=["Global Scale", "Millions Served", "Enterprise"],
        motion_intensity=0.8,
    ),

    # ── Security ──────────────────────────────────────────────────────────────
    "shield": MetaphorSpec(
        id="shield", concept="security", component="ShieldVisual",
        label="Shield", energy="low", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge"],
        badge_texts=["Trusted", "SOC 2", "Secure"],
        motion_intensity=0.6,
    ),
    "vault": MetaphorSpec(
        id="vault", concept="security", component="ShieldVisual",
        label="Vault", energy="medium", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["Bank-Grade", "Encrypted", "SOC 2"],
        motion_intensity=0.65,
    ),
    "lock": MetaphorSpec(
        id="lock", concept="security", component="ShieldVisual",
        label="Lock", energy="low", density="minimal",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge"],
        badge_texts=["Secure", "Private", "Compliant"],
        motion_intensity=0.5,
    ),

    # ── Automation ────────────────────────────────────────────────────────────
    "workflow-nodes": MetaphorSpec(
        id="workflow-nodes", concept="automation", component="WorkflowNodes",
        label="Workflow Nodes", energy="medium", density="dense",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["Automated", "Zero Manual Work", "Connected"],
        motion_intensity=0.75,
    ),
    "gear": MetaphorSpec(
        id="gear", concept="automation", component="WorkflowNodes",
        label="Gears", energy="medium", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge"],
        badge_texts=["Automated", "AI-Powered"],
        motion_intensity=0.65,
    ),
    "connected-flow": MetaphorSpec(
        id="connected-flow", concept="automation", component="WorkflowNodes",
        label="Connected Systems", energy="high", density="dense",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["100+ Integrations", "Plug & Play"],
        motion_intensity=0.8,
    ),

    # ── Speed ─────────────────────────────────────────────────────────────────
    "speed-lines": MetaphorSpec(
        id="speed-lines", concept="speed", component="SpeedLines",
        label="Speed Lines", energy="high", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["10× Faster", "Instant", "Real-Time"],
        motion_intensity=0.9,
    ),
    "lightning": MetaphorSpec(
        id="lightning", concept="speed", component="SpeedLines",
        label="Lightning", energy="explosive", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge"],
        badge_texts=["Instant", "Zero Latency", "Real-Time"],
        motion_intensity=1.0,
    ),
    "acceleration": MetaphorSpec(
        id="acceleration", concept="speed", component="SpeedLines",
        label="Acceleration", energy="high", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["Accelerate", "2× Faster", "Boost"],
        motion_intensity=0.85,
    ),

    # ── AI ────────────────────────────────────────────────────────────────────
    "neural-network": MetaphorSpec(
        id="neural-network", concept="ai", component="NeuralNetwork",
        label="Neural Network", energy="high", density="dense",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge", "MetricCounter"],
        badge_texts=["AI-Powered", "Intelligent", "GPT-4"],
        motion_intensity=0.85,
    ),
    "glowing-nodes": MetaphorSpec(
        id="glowing-nodes", concept="ai", component="NeuralNetwork",
        label="Intelligence Grid", energy="medium", density="dense",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge"],
        badge_texts=["AI-Powered", "Smart", "Intelligent"],
        motion_intensity=0.75,
    ),
    "intelligence-grid": MetaphorSpec(
        id="intelligence-grid", concept="ai", component="NeuralNetwork",
        label="Intelligence Grid", energy="high", density="dense",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["AI Native", "Next-Gen"],
        motion_intensity=0.8,
    ),

    # ── Trust / Social Proof ──────────────────────────────────────────────────
    "star-rating": MetaphorSpec(
        id="star-rating", concept="social_proof", component="StarBurst",
        label="Star Rating", energy="low", density="minimal",
        accent="default", background="GlowBackground",
        primary_component="QuoteCard",
        secondary_components=["FloatingBadge"],
        badge_texts=["5-Star Rated", "Verified", "10K+ Users"],
        motion_intensity=0.6,
    ),
    "verified-badge": MetaphorSpec(
        id="verified-badge", concept="trust", component="StarBurst",
        label="Verified", energy="low", density="minimal",
        accent="default", background="GlowBackground",
        primary_component="QuoteCard",
        secondary_components=["FloatingBadge"],
        badge_texts=["Verified", "Trusted", "Certified"],
        motion_intensity=0.55,
    ),
    "customer-wall": MetaphorSpec(
        id="customer-wall", concept="social_proof", component="StarBurst",
        label="Customer Wall", energy="medium", density="standard",
        accent="default", background="GlowBackground",
        primary_component="QuoteCard",
        secondary_components=["FloatingBadge", "MetricCounter"],
        badge_texts=["10K+ Teams", "Loved by All", "Join Them"],
        motion_intensity=0.65,
    ),

    # ── Scale ─────────────────────────────────────────────────────────────────
    "global-network": MetaphorSpec(
        id="global-network", concept="scale", component="ExpandingCircles",
        label="Global Network", energy="high", density="dense",
        accent="default", background="AnimatedGrid",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge"],
        badge_texts=["Global", "Worldwide", "Millions"],
        motion_intensity=0.85,
    ),
    "server-clusters": MetaphorSpec(
        id="server-clusters", concept="scale", component="ExpandingCircles",
        label="Server Clusters", energy="medium", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge", "ProgressBar"],
        badge_texts=["99.9% Uptime", "Redundant", "Enterprise"],
        motion_intensity=0.7,
    ),

    # ── Savings / ROI ─────────────────────────────────────────────────────────
    "metric-counter": MetaphorSpec(
        id="metric-counter", concept="savings", component="GrowthChart",
        label="ROI Counter", energy="high", density="standard",
        accent="success", background="ParticleField",
        primary_component="MetricCounter",
        secondary_components=["ProgressBar", "FloatingBadge"],
        badge_texts=["Save 40%", "ROI Proven", "Free Trial"],
        motion_intensity=0.8,
    ),

    # ── Simplicity ────────────────────────────────────────────────────────────
    "step-flow": MetaphorSpec(
        id="step-flow", concept="simplicity", component="WorkflowNodes",
        label="Step Flow", energy="medium", density="standard",
        accent="default", background="AnimatedGrid",
        primary_component="FeatureCard",
        secondary_components=["ProgressBar", "FloatingBadge"],
        badge_texts=["Easy Setup", "No Code", "5 Min Setup"],
        motion_intensity=0.6,
    ),
    "checkmarks": MetaphorSpec(
        id="checkmarks", concept="simplicity", component="WorkflowNodes",
        label="Checkmarks", energy="medium", density="standard",
        accent="success", background="GlowBackground",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge"],
        badge_texts=["One-Click", "No Code", "Just Works"],
        motion_intensity=0.6,
    ),

    # ── Performance ───────────────────────────────────────────────────────────
    "uptime-bar": MetaphorSpec(
        id="uptime-bar", concept="performance", component="GrowthChart",
        label="Uptime Bar", energy="high", density="dense",
        accent="success", background="AnimatedGrid",
        primary_component="MetricCounter",
        secondary_components=["ProgressBar", "FloatingBadge"],
        badge_texts=["99.9% Uptime", "Enterprise Grade", "Reliable"],
        motion_intensity=0.8,
    ),
    "pulse-graph": MetaphorSpec(
        id="pulse-graph", concept="performance", component="GrowthChart",
        label="Pulse Graph", energy="high", density="standard",
        accent="default", background="ParticleField",
        primary_component="MetricCounter",
        secondary_components=["FloatingBadge"],
        badge_texts=["Real-Time", "Live Monitoring"],
        motion_intensity=0.85,
    ),

    # ── Analytics ─────────────────────────────────────────────────────────────
    "dashboard": MetaphorSpec(
        id="dashboard", concept="analytics", component="GrowthChart",
        label="Dashboard", energy="high", density="dense",
        accent="default", background="AnimatedGrid",
        primary_component="MetricCounter",
        secondary_components=["ProgressBar", "FloatingBadge"],
        badge_texts=["Live Insights", "Data-Driven", "Real-Time"],
        motion_intensity=0.8,
    ),

    # ── Collaboration ─────────────────────────────────────────────────────────
    "user-avatars": MetaphorSpec(
        id="user-avatars", concept="collaboration", component="StarBurst",
        label="User Avatars", energy="medium", density="standard",
        accent="default", background="GlowBackground",
        primary_component="FeatureCard",
        secondary_components=["FloatingBadge", "MetricCounter"],
        badge_texts=["Team Ready", "Collaborate", "Share Instantly"],
        motion_intensity=0.65,
    ),
}

# ── Concept → preferred metaphor order ───────────────────────────────────────

CONCEPT_METAPHORS: dict[str, list[str]] = {
    "speed":        ["speed-lines", "lightning", "acceleration"],
    "growth":       ["rocket", "growth-chart", "upward-arrow"],
    "security":     ["shield", "vault", "lock"],
    "automation":   ["workflow-nodes", "connected-flow", "gear"],
    "ai":           ["neural-network", "intelligence-grid", "glowing-nodes"],
    "savings":      ["metric-counter", "growth-chart", "upward-arrow"],
    "simplicity":   ["step-flow", "checkmarks", "workflow-nodes"],
    "social_proof": ["star-rating", "customer-wall", "verified-badge"],
    "performance":  ["uptime-bar", "pulse-graph", "growth-chart"],
    "collaboration":["user-avatars", "workflow-nodes", "step-flow"],
    "analytics":    ["dashboard", "growth-chart", "pulse-graph"],
    "scale":        ["expanding-circles", "global-network", "server-clusters"],
    "trust":        ["verified-badge", "shield", "star-rating"],
}

# Scene-type metaphor overrides (forced regardless of concept)
SCENE_TYPE_METAPHOR_OVERRIDE: dict[str, str] = {
    "testimonials": "star-rating",
    "cta":          "rocket",
}

# ── Public API ────────────────────────────────────────────────────────────────

def get_spec(metaphor_id: str) -> MetaphorSpec:
    return METAPHOR_REGISTRY.get(metaphor_id, METAPHOR_REGISTRY["growth-chart"])


def resolve_metaphor(concept: str, scene_type: str) -> MetaphorSpec:
    """
    Pick the best MetaphorSpec for this concept + scene type.
    Scene-type overrides take priority.
    """
    if scene_type in SCENE_TYPE_METAPHOR_OVERRIDE:
        mid = SCENE_TYPE_METAPHOR_OVERRIDE[scene_type]
        return get_spec(mid)
    candidates = CONCEPT_METAPHORS.get(concept, ["growth-chart"])
    return get_spec(candidates[0])


def all_metaphors() -> list[dict]:
    """Return all registered metaphors as plain dicts (for API/docs)."""
    return [
        {
            "id": s.id, "concept": s.concept, "label": s.label,
            "component": s.component, "energy": s.energy,
        }
        for s in METAPHOR_REGISTRY.values()
    ]
