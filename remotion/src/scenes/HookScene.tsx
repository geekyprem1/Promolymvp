import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { HookSceneProps } from "../lib/types";
import { easeOutCubic } from "../lib/easing";
import { TextReveal } from "../components/TextReveal";
import { FloatingBadge } from "../components/motionlib/FloatingBadge";
import { ParticleField } from "../components/motionlib/ParticleField";
import { useTemplate } from "../lib/templates";

export const HookScene: React.FC<HookSceneProps> = ({
  headline,
  subheadline,
  badge,
  screenshotUrl,
  stat,
  statLabel,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const tpl = useTemplate();
  const c = tpl.colors;

  const bgScale   = interpolate(frame, [0, 120], [1.1, 1.03], { extrapolateRight: "clamp" });
  const bgOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  const statScale   = spring({ frame: frame - 5, fps, config: { damping: tpl.spring.damping, stiffness: tpl.spring.stiffness * 1.3, mass: tpl.spring.mass * 0.8 } });
  const statOpacity = interpolate(frame, [5, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  const labelY = interpolate(frame, [18, 34], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const labelOpacity = interpolate(frame, [18, 34], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const lineW = interpolate(frame, [30, 50], [0, 200], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  const headlineOpacity = interpolate(frame, [35, 50], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const badgeScale = spring({ frame: frame - 2, fps, config: { damping: tpl.spring.damping, stiffness: tpl.spring.stiffness * 2, mass: tpl.spring.mass * 0.5 } });

  const glowPulse = interpolate(Math.sin((frame / fps) * Math.PI * 0.5), [-1, 1], [0.5, 1.0]);

  const hasStat = stat && stat.length > 0;
  const b = tpl.badge;

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", fontFamily: tpl.typography.headingFont }}>

      {/* Background */}
      <div style={{ position: "absolute", inset: 0, opacity: bgOpacity, transform: `scale(${bgScale})` }}>
        {screenshotUrl ? (
          <img src={screenshotUrl} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} />
        ) : (
          <div style={{ width: "100%", height: "100%", background: c.bg2 }} />
        )}
        <div style={{ position: "absolute", inset: 0, backdropFilter: tpl.backdropBlur > 0 ? `blur(${tpl.backdropBlur}px)` : undefined, background: `${c.bg}99` }} />
      </div>

      {/* Gradient accent overlay */}
      <div style={{
        position: "absolute", inset: 0,
        background: tpl.colors.heroOverlay,
      }} />

      {/* Secondary — particle energy + badge chips */}
      <ParticleField color={c.accent} count={12} startFrame={10} intensity={0.5} />
      {hasStat && (
        <div style={{ position: "absolute", top: 52, left: 60, zIndex: 4, display: "flex", gap: 12 }}>
          <FloatingBadge text="Hook" icon="⚡" variant="chip" startFrame={8} />
          <FloatingBadge text={statLabel || "Key Stat"} variant="chip" startFrame={20} />
        </div>
      )}

      {/* Central layout */}
      <div style={{
        position: "relative", zIndex: 2,
        width: "100%", height: "100%",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        textAlign: "center", gap: 0, padding: "0 160px",
      }}>

        {/* Badge */}
        <div style={{
          transform: `scale(${badgeScale})`,
          display: "inline-flex", alignItems: "center", gap: 8,
          padding: "8px 20px", borderRadius: b.borderRadius,
          background: b.bg,
          border: `1.5px solid ${b.border}`,
          marginBottom: 40,
        }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: b.text, letterSpacing: "2px" }}>
            {b.prefix}{badge}
          </span>
        </div>

        {/* Big stat (if provided) */}
        {hasStat && (
          <div style={{
            opacity: statOpacity,
            transform: `scale(${statScale})`,
            display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
            marginBottom: 16,
          }}>
            <div style={{
              fontSize: 180,
              fontWeight: tpl.typography.headingWeight,
              lineHeight: 0.9,
              letterSpacing: tpl.typography.letterSpacing - 5,
              color: c.accent,
              textShadow: `0 0 ${80 * glowPulse}px ${c.accentGlow}`,
            }}>
              {stat}
            </div>
            {statLabel && (
              <div style={{
                opacity: labelOpacity,
                transform: `translateY(${labelY}px)`,
                fontSize: 24, fontWeight: 500, color: c.textMuted,
                letterSpacing: "4px", textTransform: "uppercase", marginTop: 8,
              }}>
                {statLabel}
              </div>
            )}
          </div>
        )}

        {/* Divider */}
        <div style={{
          width: lineW, height: 3, borderRadius: 2,
          background: `linear-gradient(90deg, ${c.gradientFrom}, ${c.gradientTo})`,
          marginBottom: 36,
          marginTop: hasStat ? 24 : 0,
        }} />

        {/* Headline */}
        <h1 style={{
          fontSize: Math.round((hasStat ? 72 : 110) * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight,
          color: c.text,
          lineHeight: tpl.typography.lineHeight,
          letterSpacing: tpl.typography.letterSpacing,
          margin: 0, maxWidth: "16ch",
          opacity: headlineOpacity,
          textTransform: tpl.typography.textTransform,
        }}>
          <TextReveal text={headline} startFrame={38} wordDelay={6} />
        </h1>

        {/* Subheadline */}
        {subheadline && (
          <p style={{
            fontSize: 26, fontWeight: 400, color: c.textMuted,
            lineHeight: 1.6, marginTop: 20, maxWidth: "52ch",
          }}>
            <TextReveal text={subheadline} startFrame={48} wordDelay={4} color={c.textMuted} />
          </p>
        )}
      </div>

      {/* Watermark */}
      <div style={{
        position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase",
        color: c.textFaint, fontFamily: tpl.typography.bodyFont,
      }}>PROMOLY</div>
    </div>
  );
};
