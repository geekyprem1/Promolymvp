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
import { GlowBackground } from "../components/GlowBackground";
import { easeOutCubic } from "../lib/easing";
import { useTemplate } from "../lib/templates";

const METRIC_RE = /(\d[\d,\.]*)\s*(%|x|\+|k|K|M|B)?/;
const CARD_ICONS = ["⚡", "✦", "◆", "●", "▲", "✧"];

/**
 * MotionGraphicsScene — the MOTION GRAPHICS renderer (no website screenshots).
 *
 * Dispatches by scene.type:
 *   hook / problem / solution / cta → existing pure-motion scenes
 *                                      (screenshot stripped so the backdrop is clean)
 *   features / benefits / content   → animated FeatureCard grid
 *   testimonials                    → animated quote card
 *   hero                            → kinetic headline
 *
 * Feels like a modern SaaS ad / Product Hunt launch video.
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

// ── FeatureGrid: animated cards from bullets ──────────────────────────────────

const FeatureGrid: React.FC<{ scene: AnySceneProps }> = ({ scene }) => {
  const { headline, subheadline, badge } = scene;
  const bullets: string[] = (scene as any).bullets ?? [];
  const bodyText: string  = (scene as any).bodyText ?? "";
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();
  const c = tpl.colors;

  const items = (bullets?.length ? bullets : (bodyText ? bodyText.split(".").map(s => s.trim()) : []))
    .filter(b => b && b.length > 3)
    .slice(0, 3);
  const safe = items.length ? items : ["Fast and reliable", "Easy to integrate", "Scales with you"];

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      fontFamily: tpl.typography.headingFont }}>
      <GlowBackground variant="split" startFrame={0} />

      <div style={{ position: "relative", zIndex: 1, textAlign: "center", marginBottom: 56 }}>
        <Badge text={badge} startFrame={5} />
        <h2 style={{
          fontSize: Math.round(70 * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight, color: c.text,
          lineHeight: tpl.typography.lineHeight, letterSpacing: tpl.typography.letterSpacing,
          margin: "10px auto 0", maxWidth: "20ch", textTransform: tpl.typography.textTransform,
        }}>
          <TextReveal text={headline} startFrame={10} wordDelay={4} />
        </h2>
        {subheadline && (
          <p style={{ fontSize: 24, color: c.textMuted, marginTop: 14, maxWidth: "44ch" }}>{subheadline}</p>
        )}
      </div>

      <div style={{ position: "relative", zIndex: 1, display: "flex", gap: 32, justifyContent: "center" }}>
        {safe.map((text, i) => {
          const title = text.split(" ").slice(0, 3).join(" ");
          const desc  = text.length > 24 ? text : `${text}.`;
          return (
            <FeatureCard
              key={i}
              icon={CARD_ICONS[i % CARD_ICONS.length]}
              title={title}
              description={desc.slice(0, 80)}
              accentColor={c.accent}
              startFrame={20 + i * 10}
            />
          );
        })}
      </div>

      <div style={{ position: "absolute", bottom: 28, right: 36, fontSize: 11, fontWeight: 700,
        letterSpacing: 2, textTransform: "uppercase", color: c.textFaint, fontFamily: tpl.typography.bodyFont }}>PROMOLY</div>
    </div>
  );
};

// ── BenefitGrid: metric counter + benefit cards ───────────────────────────────

const BenefitGrid: React.FC<{ scene: AnySceneProps }> = ({ scene }) => {
  const { headline, subheadline, badge } = scene;
  const bodyText: string = (scene as any).bodyText ?? "";
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();
  const c = tpl.colors;

  const lines = (bodyText ? bodyText.split(".").map(s => s.trim()) : []).filter(b => b && b.length > 3);
  const metricLine = lines.find(l => METRIC_RE.test(l) && /\d/.test(l));
  const m = metricLine ? METRIC_RE.exec(metricLine) : null;
  const metricVal = m ? parseFloat(m[1].replace(/,/g, "")) : 0;
  const metricSuffix = m?.[2] ?? "";
  const cards = lines.filter(l => l !== metricLine).slice(0, 2);
  const safeCards = cards.length ? cards : ["Built to scale", "Loved by teams"];

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      fontFamily: tpl.typography.headingFont }}>
      <GlowBackground variant="cta" startFrame={0} />

      <div style={{ position: "relative", zIndex: 1, textAlign: "center", marginBottom: 44 }}>
        <Badge text={badge} startFrame={5} />
        <h2 style={{
          fontSize: Math.round(72 * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight, color: c.text,
          lineHeight: tpl.typography.lineHeight, letterSpacing: tpl.typography.letterSpacing,
          margin: "10px auto 0", maxWidth: "20ch", textTransform: tpl.typography.textTransform,
        }}>
          <TextReveal text={headline} startFrame={10} wordDelay={4} />
        </h2>
        {subheadline && <p style={{ fontSize: 24, color: c.textMuted, marginTop: 14, maxWidth: "44ch" }}>{subheadline}</p>}
      </div>

      <div style={{ position: "relative", zIndex: 1, display: "flex", gap: 40, alignItems: "center" }}>
        {metricVal > 0 && (
          <MetricCounter from={0} to={metricVal} suffix={metricSuffix} label="" accentColor={c.accent}
            startFrame={24} exitStartFrame={999} />
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          {safeCards.map((text, i) => {
            const start = 30 + i * 10;
            return <BenefitRow key={i} text={text} accent={c.accent} textColor={c.text} startFrame={start} />;
          })}
        </div>
      </div>

      <div style={{ position: "absolute", bottom: 28, right: 36, fontSize: 11, fontWeight: 700,
        letterSpacing: 2, textTransform: "uppercase", color: c.textFaint, fontFamily: tpl.typography.bodyFont }}>PROMOLY</div>
    </div>
  );
};

const BenefitRow: React.FC<{ text: string; accent: string; textColor: string; startFrame: number }> = ({ text, accent, textColor, startFrame }) => {
  const frame = useCurrentFrame();
  const f = frame - startFrame;
  const opacity = interpolate(f, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const x = interpolate(f, [0, 16], [-30, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 28, color: textColor,
      opacity, transform: `translateX(${x}px)` }}>
      <span style={{ color: accent, fontWeight: 800 }}>✓</span>
      {text.slice(0, 48)}
    </div>
  );
};

// ── QuoteCard: animated testimonial ───────────────────────────────────────────

const QuoteCard: React.FC<AnySceneProps> = (scene) => {
  const quote   = (scene as any).quote || scene.subheadline || scene.headline;
  const author  = (scene as any).author || "";
  const company = (scene as any).company || "";
  const { width, height, fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const tpl = useTemplate();
  const c = tpl.colors;

  const cardScale = spring({ fps, frame, config: { stiffness: tpl.spring.stiffness, damping: tpl.spring.damping, mass: tpl.spring.mass }, durationInFrames: 40 });
  const cardOpacity = interpolate(frame, [0, 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      display: "flex", alignItems: "center", justifyContent: "center", fontFamily: tpl.typography.headingFont }}>
      <GlowBackground variant="cta" startFrame={0} />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 1200, textAlign: "center",
        background: c.surface, border: `1px solid ${c.border}`, borderRadius: 28, padding: "80px 100px",
        opacity: cardOpacity, transform: `scale(${cardScale})`, boxShadow: "0 40px 120px rgba(0,0,0,0.45)" }}>
        <div style={{ fontSize: 80, color: c.accent, lineHeight: 0.5, marginBottom: 30, opacity: 0.5 }}>“</div>
        <div style={{ fontSize: Math.round(46 * tpl.typography.sizeScale), fontWeight: 600, color: c.text, lineHeight: 1.35, maxWidth: "28ch", margin: "0 auto" }}>
          <TextReveal text={quote.slice(0, 160)} startFrame={12} wordDelay={3} />
        </div>
        {(author || company) && (
          <div style={{ marginTop: 36, fontSize: 22, color: c.textMuted }}>
            <span style={{ color: c.text, fontWeight: 700 }}>{author}</span>
            {author && company ? " · " : ""}{company}
          </div>
        )}
      </div>

      <div style={{ position: "absolute", bottom: 28, right: 36, fontSize: 11, fontWeight: 700,
        letterSpacing: 2, textTransform: "uppercase", color: c.textFaint, fontFamily: tpl.typography.bodyFont }}>PROMOLY</div>
    </div>
  );
};

// ── KineticHeadline: hero / fallback ──────────────────────────────────────────

const KineticHeadline: React.FC<AnySceneProps> = ({ headline, subheadline, badge }) => {
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();
  const c = tpl.colors;
  const frame = useCurrentFrame();
  const lineW = interpolate(frame, [30, 52], [0, 220], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      textAlign: "center", fontFamily: tpl.typography.headingFont }}>
      <GlowBackground variant="cta" startFrame={0} />

      <div style={{ position: "relative", zIndex: 1, padding: "0 120px" }}>
        <Badge text={badge} startFrame={4} />
        <h1 style={{
          fontSize: Math.round(104 * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight, color: c.text,
          lineHeight: tpl.typography.lineHeight, letterSpacing: tpl.typography.letterSpacing,
          margin: "16px auto 0", maxWidth: "18ch", textTransform: tpl.typography.textTransform,
        }}>
          <TextReveal text={headline} startFrame={8} wordDelay={5} />
        </h1>
        <div style={{ width: lineW, height: 4, background: c.accent, borderRadius: 2, margin: "32px auto 0" }} />
        {subheadline && (
          <p style={{ fontSize: 28, color: c.textMuted, marginTop: 28, maxWidth: "40ch", marginLeft: "auto", marginRight: "auto" }}>
            <TextReveal text={subheadline} startFrame={30} wordDelay={2} color={c.textMuted} />
          </p>
        )}
      </div>

      <div style={{ position: "absolute", bottom: 28, right: 36, fontSize: 11, fontWeight: 700,
        letterSpacing: 2, textTransform: "uppercase", color: c.textFaint, fontFamily: tpl.typography.bodyFont }}>PROMOLY</div>
    </div>
  );
};
