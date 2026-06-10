import React from "react";
import { AbsoluteFill, Series } from "remotion";
import { theme, fonts } from "../lib/theme";
import {
  FeatureCard,
  MetricCounter,
  FloatingBadge,
  HighlightRing,
  CursorClickOverlay,
  CursorTrail,
  CTAButtonAnimation,
  ProgressBar,
  SuccessAnimation,
  TextReveal,
} from "../components/motionlib";

const SCENE_FRAMES = 90; // 3s per component demo

const SceneBg: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <AbsoluteFill
    style={{
      background: theme.bg,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 40,
      fontFamily: fonts.body,
    }}
  >
    {/* Dot grid */}
    <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.12 }}>
      <defs>
        <pattern id="dots" width="40" height="40" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1.5" fill={theme.textFaint} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#dots)" />
    </svg>

    {/* Component label */}
    <div
      style={{
        position: "absolute",
        top: 48,
        left: 80,
        fontSize: 16,
        fontWeight: 600,
        color: theme.textFaint,
        letterSpacing: "3px",
        textTransform: "uppercase",
        borderLeft: `3px solid ${theme.accent}`,
        paddingLeft: 16,
      }}
    >
      {label}
    </div>

    {children}
  </AbsoluteFill>
);

// ─── Scene 1: FeatureCard ─────────────────────────────────────────────────────
const FeatureCardDemo: React.FC = () => (
  <SceneBg label="FeatureCard">
    <div style={{ display: "flex", gap: 40 }}>
      <FeatureCard
        icon="⚡"
        title="Lightning Fast"
        description="Deploy in seconds with zero-config setup. Your workflow, accelerated."
        startFrame={0}
        exitStartFrame={75}
      />
      <FeatureCard
        icon="🔒"
        title="Secure by Default"
        description="End-to-end encryption and SOC2 compliance built in from day one."
        accentColor="#8b5cf6"
        startFrame={10}
        exitStartFrame={75}
      />
      <FeatureCard
        icon="📈"
        title="Auto Scaling"
        description="From zero to millions of users without touching a config file."
        accentColor="#22c55e"
        startFrame={20}
        exitStartFrame={75}
      />
    </div>
  </SceneBg>
);

// ─── Scene 2: MetricCounter ───────────────────────────────────────────────────
const MetricCounterDemo: React.FC = () => (
  <SceneBg label="MetricCounter">
    <div style={{ display: "flex", gap: 120, alignItems: "center" }}>
      <MetricCounter to={99.9} suffix="%" label="Uptime SLA" decimals={1} startFrame={0} exitStartFrame={75} />
      <MetricCounter to={4200000} prefix="$" label="Revenue Generated" startFrame={5} exitStartFrame={75} accentColor="#22c55e" />
      <MetricCounter to={50} suffix="ms" label="Avg Response" startFrame={10} exitStartFrame={75} accentColor="#8b5cf6" />
    </div>
  </SceneBg>
);

// ─── Scene 3: FloatingBadge ───────────────────────────────────────────────────
const FloatingBadgeDemo: React.FC = () => (
  <SceneBg label="FloatingBadge">
    <div style={{ display: "flex", flexDirection: "column", gap: 36, alignItems: "center" }}>
      <FloatingBadge text="New Feature" icon="✨" startFrame={0} exitStartFrame={75} />
      <FloatingBadge text="Beta" variant="tag" accentColor="#f97316" startFrame={10} exitStartFrame={75} />
      <FloatingBadge text="Pro Plan" icon="👑" variant="chip" accentColor="#8b5cf6" startFrame={20} exitStartFrame={75} />
      <FloatingBadge text="Live" icon="🔴" accentColor="#22c55e" startFrame={30} exitStartFrame={75} />
    </div>
  </SceneBg>
);

// ─── Scene 4: HighlightRing ───────────────────────────────────────────────────
const HighlightRingDemo: React.FC = () => (
  <SceneBg label="HighlightRing">
    <div style={{ position: "relative", width: 800, height: 500, border: `1px solid ${theme.border}`, borderRadius: 20, overflow: "hidden" }}>
      {/* Mock UI */}
      <div style={{ position: "absolute", inset: 0, background: theme.bg2, display: "flex", flexDirection: "column", padding: 40, gap: 20 }}>
        <div style={{ width: 180, height: 36, background: theme.surface, borderRadius: 8 }} />
        <div style={{ display: "flex", gap: 20 }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ flex: 1, height: 120, background: theme.surface, borderRadius: 12 }} />
          ))}
        </div>
        <div style={{ width: "60%", height: 20, background: theme.surface, borderRadius: 4 }} />
        <div style={{ width: "40%", height: 20, background: theme.surface, borderRadius: 4 }} />
        <div style={{ width: 140, height: 48, background: `${theme.accent}33`, border: `1px solid ${theme.accent}`, borderRadius: 10 }} />
      </div>
      <HighlightRing x={400 + 10} y={194} radius={72} startFrame={0} exitStartFrame={75} />
      <HighlightRing x={80 + 70} y={340} radius={30} color="#22c55e" startFrame={15} exitStartFrame={75} />
    </div>
  </SceneBg>
);

// ─── Scene 5: CursorClick ─────────────────────────────────────────────────────
const CursorClickDemo: React.FC = () => (
  <SceneBg label="CursorClick">
    <div style={{ position: "relative", width: 800, height: 400, border: `1px solid ${theme.border}`, borderRadius: 20, overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, background: theme.bg2, display: "flex", alignItems: "center", justifyContent: "center", gap: 40 }}>
        <div style={{ padding: "20px 48px", background: theme.accent, borderRadius: 12, fontSize: 22, fontWeight: 700, color: "#fff" }}>
          Get Started
        </div>
        <div style={{ padding: "20px 48px", background: "transparent", border: `2px solid ${theme.accent}`, borderRadius: 12, fontSize: 22, fontWeight: 700, color: theme.accent }}>
          Learn More
        </div>
      </div>
      <CursorClickOverlay x={296} y={200} clickFrame={25} startFrame={0} exitStartFrame={75} />
    </div>
  </SceneBg>
);

// ─── Scene 6: CursorTrail ─────────────────────────────────────────────────────
const CursorTrailDemo: React.FC = () => (
  <SceneBg label="CursorTrail">
    <div style={{ position: "relative", width: 900, height: 480, border: `1px solid ${theme.border}`, borderRadius: 20, overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, background: theme.bg2 }}>
        {/* Mock dashboard */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20, padding: 30 }}>
          {["Users", "Revenue", "Signups"].map((label, i) => (
            <div key={i} style={{ background: theme.surface, borderRadius: 12, padding: 24, border: `1px solid ${theme.border}` }}>
              <div style={{ fontSize: 14, color: theme.textMuted }}>{label}</div>
              <div style={{ fontSize: 32, fontWeight: 800, color: theme.text, marginTop: 8 }}>{["12.4K", "$48K", "892"][i]}</div>
            </div>
          ))}
        </div>
      </div>
      <CursorTrail
        waypoints={[
          { x: 100, y: 400 },
          { x: 150, y: 100 },
          { x: 300, y: 80 },
          { x: 600, y: 80 },
          { x: 750, y: 100 },
          { x: 800, y: 300 },
        ].map((p, i) => ({ x: p.x, y: p.y, frame: i * 15 }))}
        color={theme.accent}
        startFrame={0}
        exitStartFrame={75}
      />
    </div>
  </SceneBg>
);

// ─── Scene 7: CTAButtonAnimation ─────────────────────────────────────────────
const CTAButtonDemo: React.FC = () => (
  <SceneBg label="CTAButtonAnimation">
    <div style={{ display: "flex", flexDirection: "column", gap: 36, alignItems: "center" }}>
      <CTAButtonAnimation label="Start Free Trial" icon="🚀" startFrame={0} exitStartFrame={75} />
      <CTAButtonAnimation label="View Pricing" variant="outline" startFrame={12} exitStartFrame={75} />
      <CTAButtonAnimation label="Watch Demo" variant="ghost" icon="▶" accentColor="#8b5cf6" startFrame={24} exitStartFrame={75} />
    </div>
  </SceneBg>
);

// ─── Scene 8: ProgressBar ────────────────────────────────────────────────────
const ProgressBarDemo: React.FC = () => (
  <SceneBg label="ProgressBar">
    <div style={{ width: 700, display: "flex", flexDirection: "column", gap: 40 }}>
      <ProgressBar toPercent={87} label="Storage Used" startFrame={0} exitStartFrame={75} />
      <ProgressBar toPercent={64} label="Monthly Budget" accentColor="#f97316" startFrame={8} exitStartFrame={75} />
      <ProgressBar toPercent={100} label="Onboarding Complete" accentColor="#22c55e" height={20} startFrame={16} exitStartFrame={75} />
      <ProgressBar toPercent={33} label="API Quota" accentColor="#8b5cf6" startFrame={24} exitStartFrame={75} />
    </div>
  </SceneBg>
);

// ─── Scene 9: SuccessAnimation ────────────────────────────────────────────────
const SuccessAnimationDemo: React.FC = () => (
  <SceneBg label="SuccessAnimation">
    <div style={{ display: "flex", gap: 100, alignItems: "center" }}>
      <SuccessAnimation label="Payment Sent!" startFrame={0} exitStartFrame={75} size={100} />
      <SuccessAnimation label="Deployed!" color="#6366f1" startFrame={15} exitStartFrame={75} size={100} />
      <SuccessAnimation label="All Tests Pass" color="#f97316" startFrame={30} exitStartFrame={75} size={100} />
    </div>
  </SceneBg>
);

// ─── Scene 10: TextReveal ─────────────────────────────────────────────────────
const TextRevealDemo: React.FC = () => (
  <SceneBg label="TextReveal — 4 Modes">
    <div style={{ display: "flex", flexDirection: "column", gap: 36, alignItems: "flex-start", width: 900 }}>
      <div style={{ fontSize: 13, color: theme.textFaint, letterSpacing: "2px" }}>WORDS MODE</div>
      <TextReveal text="Build products your customers will love" startFrame={0} exitStartFrame={75} style={{ fontSize: 48, fontWeight: 800, color: theme.text }} />

      <div style={{ width: "100%", height: 1, background: theme.border }} />

      <div style={{ fontSize: 13, color: theme.textFaint, letterSpacing: "2px" }}>CHARS MODE</div>
      <TextReveal text="Instant. Reliable. Scalable." mode="chars" startFrame={10} exitStartFrame={75} style={{ fontSize: 40, fontWeight: 700, color: theme.accent }} stagger={3} />

      <div style={{ width: "100%", height: 1, background: theme.border }} />

      <div style={{ fontSize: 13, color: theme.textFaint, letterSpacing: "2px" }}>MASK MODE</div>
      <TextReveal text="The future of software deployment" mode="mask" startFrame={20} exitStartFrame={75} style={{ fontSize: 44, fontWeight: 700, color: theme.violet }} />
    </div>
  </SceneBg>
);

// ─── Root composition ─────────────────────────────────────────────────────────
export const ComponentDemo: React.FC = () => (
  <Series>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><FeatureCardDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><MetricCounterDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><FloatingBadgeDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><HighlightRingDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><CursorClickDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><CursorTrailDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><CTAButtonDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><ProgressBarDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><SuccessAnimationDemo /></Series.Sequence>
    <Series.Sequence durationInFrames={SCENE_FRAMES}><TextRevealDemo /></Series.Sequence>
  </Series>
);
