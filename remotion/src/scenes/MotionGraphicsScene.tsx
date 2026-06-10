import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { AnySceneProps } from "../lib/types";
import { HookScene } from "./HookScene";
import { ProblemScene } from "./ProblemScene";
import { SolutionScene } from "./SolutionScene";
import { CTAScene } from "./CTAScene";
import { TextReveal } from "../components/TextReveal";
import { Badge } from "../components/Badge";
import { FeatureCard } from "../components/motionlib/FeatureCard";
import { MetricCounter } from "../components/motionlib/MetricCounter";
import { FloatingBadge } from "../components/motionlib/FloatingBadge";
import { ProgressBar } from "../components/motionlib/ProgressBar";
import { ParticleField } from "../components/motionlib/ParticleField";
import { AnimatedGrid } from "../components/motionlib/AnimatedGrid";
import { GlowBackground } from "../components/GlowBackground";
import { easeOutCubic, easeOutBack } from "../lib/easing";
import { useTemplate } from "../lib/templates";

// ── Helpers ───────────────────────────────────────────────────────────────────

const METRIC_RE = /(\d[\d,\.]*)\s*(%|x|\+|k|K|M|B)?/g;
const CARD_ICONS = ["⚡", "✦", "◆", "●", "▲", "✧", "★", "◉"];

interface ExtractedMetric {
  value: number;
  suffix: string;
  prefix: string;
  label: string;
}

function extractMetrics(texts: string[]): ExtractedMetric[] {
  const results: ExtractedMetric[] = [];
  const seen = new Set<number>();
  for (const text of texts) {
    const matches = [...text.matchAll(METRIC_RE)];
    for (const m of matches) {
      const val = parseFloat(m[1].replace(/,/g, ""));
      if (!seen.has(val) && val > 0 && val < 1_000_000) {
        seen.add(val);
        const suffix = m[2] ?? "";
        const prefix = text.includes("$") ? "$" : "";
        const label  = text.replace(m[0], "").replace(/[$]/g, "").trim().slice(0, 24);
        results.push({ value: val, suffix, prefix, label });
        if (results.length >= 3) return results;
      }
    }
  }
  return results;
}

/**
 * MotionGraphicsScene — modern SaaS ad renderer. No website screenshots.
 *
 * Every scene has 3 layers:
 *   BG     — AnimatedGrid / ParticleField / GlowBackground
 *   Secondary — FloatingBadge chips, MetricCounters, Stars
 *   Primary — animated cards, kinetic headlines, quote cards
 */
export const MotionGraphicsScene: React.FC<AnySceneProps> = (scene) => {
  switch (scene.type) {
    case "hook":
      return <HookScene {...scene} screenshotUrl="" />;
    case "problem":
      return <ProblemScene {...scene} screenshotUrl="" />;
    case "solution":
      return <SolutionScene {...scene} screenshotUrl="" />;
    case "cta":
      return <CTAScene {...scene} />;
    case "features":
    case "content":
      return <FeatureGrid scene={scene} />;
    case "benefits":
      return <BenefitGrid scene={scene} />;
    case "testimonials":
      return <QuoteCard {...scene} />;
    case "hero":
      return <KineticHeadline {...scene} />;
    default:
      return <KineticHeadline {...(scene as AnySceneProps)} />;
  }
};

// ── FeatureGrid ───────────────────────────────────────────────────────────────

const FeatureGrid: React.FC<{ scene: AnySceneProps }> = ({ scene }) => {
  const { headline, subheadline, badge } = scene;
  const bullets: string[] = (scene as any).bullets ?? [];
  const bodyText: string  = (scene as any).bodyText ?? "";
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();
  const c   = tpl.colors;
  const frame = useCurrentFrame();

  // Build feature items
  const rawItems = (bullets?.length ? bullets : bodyText.split(".").map((s: string) => s.trim()))
    .filter((b: string) => b && b.length > 3)
    .slice(0, 3);
  const items = rawItems.length ? rawItems : ["Fast and reliable", "Easy to integrate", "Scales with you"];

  // Auto-detect metrics from headline + subheadline + bullets
  const allText = [headline, subheadline, ...items].filter(Boolean);
  const metrics = extractMetrics(allText);
  const primaryMetric = metrics[0];

  // Progress values for cards (staggered 70-95%)
  const cardProgress = [92, 78, 86];

  // Secondary badge floats in top-right corner
  const badgeTexts = ["Trusted", "Proven", "Fast", "Secure", "Top Rated"];
  const badgeText  = badge || badgeTexts[Math.floor(Math.random() * badgeTexts.length)] || "Featured";

  // Title slide
  const titleY = interpolate(frame, [8, 28], [30, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });
  const titleOpacity = interpolate(frame, [8, 28], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", fontFamily: tpl.typography.headingFont }}>

      {/* BG layer */}
      <GlowBackground variant="hero" startFrame={0} />
      <AnimatedGrid color={c.accent} opacity={0.08} startFrame={0} />

      {/* Secondary layer — floating badge top-right + optional metric chip */}
      <div style={{ position: "absolute", top: 52, right: 60, zIndex: 3, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 16 }}>
        <FloatingBadge text={badgeText} icon="✦" variant="chip" startFrame={5} />
        {primaryMetric && (
          <FloatingBadge
            text={`${primaryMetric.prefix}${primaryMetric.value}${primaryMetric.suffix}`}
            variant="chip"
            startFrame={18}
            style={{ fontSize: 14 }}
          />
        )}
      </div>

      {/* Primary layer */}
      <div style={{
        position: "relative", zIndex: 2,
        width: "100%", height: "100%",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        fontFamily: tpl.typography.headingFont,
      }}>
        {/* Header */}
        <div style={{
          textAlign: "center", marginBottom: 52,
          opacity: titleOpacity, transform: `translateY(${titleY}px)`,
        }}>
          <Badge text={badge} startFrame={4} />
          <h2 style={{
            fontSize: Math.round(68 * tpl.typography.sizeScale),
            fontWeight: tpl.typography.headingWeight, color: c.text,
            lineHeight: tpl.typography.lineHeight, letterSpacing: tpl.typography.letterSpacing,
            margin: "12px auto 0", maxWidth: "22ch",
            textTransform: tpl.typography.textTransform,
          }}>
            <TextReveal text={headline} startFrame={12} wordDelay={4} />
          </h2>
          {subheadline && (
            <p style={{ fontSize: 22, color: c.textMuted, marginTop: 12, maxWidth: "48ch" }}>
              <TextReveal text={subheadline} startFrame={20} wordDelay={2} color={c.textMuted} />
            </p>
          )}
        </div>

        {/* Cards row */}
        <div style={{ display: "flex", gap: 28, justifyContent: "center", alignItems: "flex-start" }}>
          {items.map((text: string, i: number) => {
            const title = text.split(" ").slice(0, 3).join(" ");
            const desc  = text.length > 30 ? text.slice(0, 72) : `${text}.`;
            return (
              <div key={i} style={{ display: "flex", flexDirection: "column", gap: 16, width: 360 }}>
                <FeatureCard
                  icon={CARD_ICONS[i % CARD_ICONS.length]}
                  title={title}
                  description={desc}
                  startFrame={24 + i * 12}
                />
                <ProgressBar
                  toPercent={cardProgress[i]}
                  showValue={true}
                  startFrame={36 + i * 12}
                  height={10}
                  style={{ width: 360 }}
                />
              </div>
            );
          })}
        </div>
      </div>

      <Watermark tpl={tpl} />
    </div>
  );
};

// ── BenefitGrid ───────────────────────────────────────────────────────────────

const BenefitGrid: React.FC<{ scene: AnySceneProps }> = ({ scene }) => {
  const { headline, subheadline, badge } = scene;
  const bodyText: string = (scene as any).bodyText ?? "";
  const bullets: string[] = (scene as any).bullets ?? [];
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();
  const c   = tpl.colors;
  const frame = useCurrentFrame();

  const allLines = [
    ...(bodyText ? bodyText.split(".").map((s: string) => s.trim()) : []),
    ...bullets,
  ].filter((b: string) => b && b.length > 3);

  const metrics = extractMetrics([headline, subheadline, ...allLines].filter(Boolean));
  const safeMetrics = metrics.length > 0 ? metrics : [{ value: 99, suffix: "%", prefix: "", label: "Uptime" }];

  const benefitLines = allLines.filter((l: string) => !METRIC_RE.test(l)).slice(0, 4);
  const safeBenefits = benefitLines.length ? benefitLines : ["Built to scale", "Loved by teams", "Enterprise ready"];

  // Badge chips from metrics
  const badgeChips = [
    badge || "Proven Results",
    ...safeMetrics.map(m => `${m.prefix}${m.value}${m.suffix}+`).slice(0, 2),
  ];

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const titleY = interpolate(frame, [0, 20], [20, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", fontFamily: tpl.typography.headingFont }}>

      {/* BG layer */}
      <GlowBackground variant="cta" startFrame={0} />
      <ParticleField color={c.accent} startFrame={0} intensity={0.7} />

      {/* Secondary layer — badge chips top left */}
      <div style={{ position: "absolute", top: 52, left: 60, zIndex: 3, display: "flex", gap: 12 }}>
        {badgeChips.map((txt, i) => (
          <FloatingBadge key={i} text={txt} variant="chip" startFrame={i * 10} />
        ))}
      </div>

      {/* Primary layer */}
      <div style={{
        position: "relative", zIndex: 2,
        width: "100%", height: "100%",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
      }}>
        {/* Title */}
        <div style={{ textAlign: "center", marginBottom: 48, opacity: titleOpacity, transform: `translateY(${titleY}px)` }}>
          <Badge text={badge} startFrame={4} />
          <h2 style={{
            fontSize: Math.round(68 * tpl.typography.sizeScale),
            fontWeight: tpl.typography.headingWeight, color: c.text,
            lineHeight: tpl.typography.lineHeight, letterSpacing: tpl.typography.letterSpacing,
            margin: "12px auto 0", maxWidth: "22ch",
            textTransform: tpl.typography.textTransform,
          }}>
            <TextReveal text={headline} startFrame={8} wordDelay={4} />
          </h2>
          {subheadline && (
            <p style={{ fontSize: 22, color: c.textMuted, marginTop: 12, maxWidth: "48ch" }}>
              {subheadline}
            </p>
          )}
        </div>

        {/* Metrics row */}
        <div style={{ display: "flex", gap: 60, justifyContent: "center", marginBottom: 44 }}>
          {safeMetrics.slice(0, 3).map((m, i) => (
            <MetricCounter
              key={i}
              from={0}
              to={m.value}
              prefix={m.prefix}
              suffix={m.suffix}
              label={m.label || ""}
              startFrame={20 + i * 14}
              style={{ minWidth: 160 }}
            />
          ))}
        </div>

        {/* Benefit rows */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "center" }}>
          {safeBenefits.slice(0, 3).map((text: string, i: number) => (
            <BenefitRow key={i} text={text} accent={c.accent} textColor={c.text} startFrame={34 + i * 10} />
          ))}
        </div>
      </div>

      <Watermark tpl={tpl} />
    </div>
  );
};

const BenefitRow: React.FC<{ text: string; accent: string; textColor: string; startFrame: number }> = ({
  text, accent, textColor, startFrame,
}) => {
  const frame = useCurrentFrame();
  const f = frame - startFrame;
  const opacity = interpolate(f, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const x = interpolate(f, [0, 16], [-40, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutBack });
  const tpl = useTemplate();
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 16,
      padding: "14px 32px",
      background: `${accent}10`,
      border: `1px solid ${accent}28`,
      borderRadius: 12,
      minWidth: 560,
      opacity, transform: `translateX(${x}px)`,
      fontFamily: tpl.typography.bodyFont,
    }}>
      <span style={{ color: accent, fontWeight: 800, fontSize: 22 }}>✓</span>
      <span style={{ fontSize: 22, color: textColor, fontWeight: 500 }}>{text.slice(0, 56)}</span>
    </div>
  );
};

// ── QuoteCard ─────────────────────────────────────────────────────────────────

const QuoteCard: React.FC<AnySceneProps> = (scene) => {
  const quote   = (scene as any).quote || scene.subheadline || scene.headline;
  const author  = (scene as any).author || "";
  const company = (scene as any).company || "";
  const { width, height, fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const tpl = useTemplate();
  const c = tpl.colors;

  const cardScale   = spring({ fps, frame, config: { stiffness: tpl.spring.stiffness, damping: tpl.spring.damping, mass: tpl.spring.mass }, durationInFrames: 40 });
  const cardOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Star rating reveal
  const starsOpacity = interpolate(frame, [28, 42], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const starsY       = interpolate(frame, [28, 42], [14, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Author line slide up
  const authorOpacity = interpolate(frame, [38, 52], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const authorY       = interpolate(frame, [38, 52], [14, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: tpl.typography.headingFont }}>

      {/* BG layer */}
      <GlowBackground variant="hero" startFrame={0} />
      <ParticleField color={c.accent} startFrame={0} count={12} intensity={0.5} />

      {/* Secondary — "Verified Customer" badge top-right */}
      <div style={{ position: "absolute", top: 52, right: 60, zIndex: 3 }}>
        <FloatingBadge text="Verified Customer" icon="✓" variant="chip" startFrame={8} />
      </div>
      {/* Decorative large quote mark — top-left */}
      <QuoteMark c={c} />

      {/* Primary — card */}
      <div style={{
        position: "relative", zIndex: 2, maxWidth: 1100, textAlign: "center",
        background: c.surface,
        border: `1px solid ${c.border}`,
        borderRadius: 28, padding: "72px 96px",
        opacity: cardOpacity, transform: `scale(${cardScale})`,
        boxShadow: `0 40px 120px rgba(0,0,0,0.45), 0 0 0 1px ${c.accent}18`,
      }}>

        {/* Quote text */}
        <div style={{ fontSize: Math.round(44 * tpl.typography.sizeScale), fontWeight: 600, color: c.text, lineHeight: 1.4, maxWidth: "30ch", margin: "0 auto" }}>
          <TextReveal text={quote.slice(0, 160)} startFrame={10} wordDelay={3} />
        </div>

        {/* Stars */}
        <div style={{ marginTop: 32, opacity: starsOpacity, transform: `translateY(${starsY}px)` }}>
          {[0, 1, 2, 3, 4].map(i => (
            <StarIcon key={i} color={c.accent} delay={i * 4} />
          ))}
        </div>

        {/* Author */}
        {(author || company) && (
          <div style={{
            marginTop: 28, fontSize: 22, color: c.textMuted,
            opacity: authorOpacity, transform: `translateY(${authorY}px)`,
          }}>
            <span style={{ color: c.text, fontWeight: 700 }}>{author}</span>
            {author && company ? <span style={{ color: c.accent }}> · </span> : ""}
            {company}
          </div>
        )}
      </div>

      <Watermark tpl={tpl} />
    </div>
  );
};

const QuoteMark: React.FC<{ c: any }> = ({ c }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 24], [0, 0.12], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", top: 40, left: 60, zIndex: 1,
      fontSize: 280, lineHeight: 1, color: c.accent, opacity,
      fontFamily: "Georgia, serif", pointerEvents: "none", userSelect: "none",
    }}>"</div>
  );
};

const StarIcon: React.FC<{ color: string; delay: number }> = ({ color, delay }) => {
  const frame = useCurrentFrame();
  const f = frame - 28 - delay;
  const scale = spring({ frame: f, fps: 30, config: { damping: 10, stiffness: 200, mass: 0.5 } });
  return (
    <span style={{
      fontSize: 28, color,
      display: "inline-block",
      transform: `scale(${scale})`,
      margin: "0 3px",
      textShadow: `0 0 12px ${color}88`,
    }}>★</span>
  );
};

// ── KineticHeadline ───────────────────────────────────────────────────────────

const KineticHeadline: React.FC<AnySceneProps> = ({ headline, subheadline, badge }) => {
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();
  const c   = tpl.colors;
  const frame = useCurrentFrame();

  // Animated underline
  const lineW = interpolate(frame, [32, 56], [0, 260], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });

  // Subheadline fade
  const subOpacity = interpolate(frame, [36, 52], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const subY = interpolate(frame, [36, 52], [16, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });

  // Floating chips
  const chips = ["#1 Rated", "Now Live", "Get Started"];
  const chipText = badge
    ? [badge, chips[1]]
    : chips.slice(0, 2);

  // Extract any metric from headline/subheadline
  const metrics = extractMetrics([headline, subheadline].filter(Boolean));
  const heroMetric = metrics[0];

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", fontFamily: tpl.typography.headingFont }}>

      {/* BG layer */}
      <GlowBackground variant="hero" startFrame={0} />
      <AnimatedGrid color={c.accent} opacity={0.07} spacing={56} startFrame={0} />
      <ParticleField color={c.accent} count={14} startFrame={0} intensity={0.6} />

      {/* Secondary — chip row top + metric chip bottom-left */}
      <div style={{ position: "absolute", top: 52, left: "50%", transform: "translateX(-50%)", zIndex: 3, display: "flex", gap: 14 }}>
        {chipText.map((txt, i) => (
          <FloatingBadge key={i} text={txt} variant="chip" startFrame={4 + i * 8} />
        ))}
      </div>
      {heroMetric && (
        <div style={{ position: "absolute", bottom: 80, left: 80, zIndex: 3 }}>
          <MetricCounter
            from={0}
            to={heroMetric.value}
            prefix={heroMetric.prefix}
            suffix={heroMetric.suffix}
            label={heroMetric.label || ""}
            startFrame={30}
            style={{ transform: "scale(0.7)", transformOrigin: "bottom left" }}
          />
        </div>
      )}

      {/* Primary — kinetic headline */}
      <div style={{ position: "relative", zIndex: 2, padding: "0 120px" }}>
        <h1 style={{
          fontSize: Math.round(108 * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight, color: c.text,
          lineHeight: tpl.typography.lineHeight, letterSpacing: tpl.typography.letterSpacing,
          margin: "0 auto", maxWidth: "18ch",
          textTransform: tpl.typography.textTransform,
        }}>
          <TextReveal text={headline} startFrame={6} wordDelay={6} />
        </h1>

        {/* Accent underline that draws itself */}
        <div style={{ display: "flex", justifyContent: "center", marginTop: 28 }}>
          <div style={{
            width: lineW, height: 5, borderRadius: 3,
            background: `linear-gradient(90deg, ${c.accent}, ${c.secondary ?? c.accent}88)`,
            boxShadow: `0 0 20px ${c.accent}66`,
          }} />
        </div>

        {subheadline && (
          <p style={{
            fontSize: 30, color: c.textMuted, marginTop: 28, maxWidth: "44ch",
            marginLeft: "auto", marginRight: "auto",
            opacity: subOpacity, transform: `translateY(${subY}px)`,
          }}>
            <TextReveal text={subheadline} startFrame={32} wordDelay={2} color={c.textMuted} />
          </p>
        )}
      </div>

      <Watermark tpl={tpl} />
    </div>
  );
};

// ── Shared ────────────────────────────────────────────────────────────────────

const Watermark: React.FC<{ tpl: ReturnType<typeof useTemplate> }> = ({ tpl }) => (
  <div style={{
    position: "absolute", bottom: 28, right: 36,
    fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase",
    color: tpl.colors.textFaint, fontFamily: tpl.typography.bodyFont,
  }}>PROMOLY</div>
);
