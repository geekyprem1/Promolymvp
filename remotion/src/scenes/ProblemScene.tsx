import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { ProblemSceneProps } from "../lib/types";
import { easeOutCubic, easeOutBack } from "../lib/easing";
import { TextReveal } from "../components/TextReveal";
import { useTemplate } from "../lib/templates";

// Pain red is semantic — intentional regardless of template
const PAIN_COLOR = "#ef4444";
const PAIN_DIM   = "rgba(239,68,68,0.18)";

export const ProblemScene: React.FC<ProblemSceneProps> = ({
  headline,
  subheadline,
  badge,
  screenshotUrl,
  painPoints = [],
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const tpl = useTemplate();
  const c = tpl.colors;

  const bgOpacity = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });
  const bgScale   = interpolate(frame, [0, 120], [1.06, 1.0], { extrapolateRight: "clamp" });

  const badgeScale = spring({ frame: frame - 2, fps, config: { damping: tpl.spring.damping, stiffness: tpl.spring.stiffness * 2, mass: tpl.spring.mass * 0.5 } });

  const headlineOpacity = interpolate(frame, [10, 26], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const headlineY       = interpolate(frame, [10, 26], [24, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  const subOpacity = interpolate(frame, [22, 38], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  const redPulse = interpolate(Math.sin((frame / fps) * Math.PI * 0.7), [-1, 1], [0.08, 0.18]);

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", fontFamily: tpl.typography.headingFont }}>

      {/* Background */}
      <div style={{ position: "absolute", inset: 0, opacity: bgOpacity, transform: `scale(${bgScale})` }}>
        {screenshotUrl ? (
          <img src={screenshotUrl} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} />
        ) : (
          <div style={{ width: "100%", height: "100%", background: "#1a0505" }} />
        )}
        <div style={{ position: "absolute", inset: 0, backdropFilter: tpl.backdropBlur > 0 ? `blur(${tpl.backdropBlur}px)` : undefined, background: "rgba(18,5,5,0.72)" }} />
      </div>

      {/* Red tint pulse overlay */}
      <div style={{
        position: "absolute", inset: 0,
        background: `
          radial-gradient(ellipse 80% 60% at 50% 50%, rgba(239,68,68,${redPulse}) 0%, transparent 65%),
          linear-gradient(to bottom, rgba(12,4,4,0.1) 0%, rgba(12,4,4,0.6) 100%)
        `,
        pointerEvents: "none",
      }} />

      {/* Content */}
      <div style={{
        position: "relative", zIndex: 2,
        width: "100%", height: "100%",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "0 160px", textAlign: "center", gap: 0,
      }}>

        {/* Badge */}
        <div style={{
          transform: `scale(${badgeScale})`,
          display: "inline-flex", alignItems: "center", gap: 8,
          padding: "8px 20px", borderRadius: 999,
          background: `${PAIN_COLOR}22`,
          border: `1.5px solid ${PAIN_COLOR}55`,
          marginBottom: 36,
        }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: PAIN_COLOR, display: "inline-block" }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: PAIN_COLOR, letterSpacing: "2px" }}>
            {badge}
          </span>
        </div>

        {/* Headline */}
        <h1 style={{
          fontSize: Math.round(96 * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight,
          color: c.text,
          lineHeight: tpl.typography.lineHeight,
          letterSpacing: tpl.typography.letterSpacing,
          margin: 0, maxWidth: "16ch",
          opacity: headlineOpacity,
          transform: `translateY(${headlineY}px)`,
          textTransform: tpl.typography.textTransform,
        }}>
          {headline}
        </h1>

        {/* Subheadline */}
        {subheadline && (
          <p style={{
            fontSize: 26, fontWeight: 400,
            color: "rgba(255,255,255,0.45)",
            lineHeight: 1.6, marginTop: 18, maxWidth: "50ch",
            opacity: subOpacity,
          }}>
            {subheadline}
          </p>
        )}

        {/* Pain points */}
        {painPoints.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 48, alignItems: "center" }}>
            {painPoints.map((point, i) => {
              const itemOpacity = interpolate(frame, [38 + i * 10, 52 + i * 10], [0, 1], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
              });
              const itemX = interpolate(frame, [38 + i * 10, 54 + i * 10], [-30, 0], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutBack,
              });
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 16,
                  opacity: itemOpacity,
                  transform: `translateX(${itemX}px)`,
                  background: PAIN_DIM,
                  border: `1px solid ${PAIN_COLOR}33`,
                  borderRadius: 12,
                  padding: "14px 28px",
                  minWidth: 500,
                }}>
                  <span style={{
                    width: 28, height: 28, borderRadius: "50%",
                    background: `${PAIN_COLOR}33`,
                    border: `1.5px solid ${PAIN_COLOR}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 14, color: PAIN_COLOR, fontWeight: 700, flexShrink: 0,
                  }}>✕</span>
                  <span style={{ fontSize: 20, color: "rgba(255,255,255,0.7)", fontWeight: 500 }}>
                    {point}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Bottom red bar */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 3,
        background: `linear-gradient(90deg, transparent, ${PAIN_COLOR}, transparent)`,
        opacity: 0.6,
      }} />

      {/* Watermark */}
      <div style={{
        position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase",
        color: c.textFaint, fontFamily: tpl.typography.bodyFont,
      }}>PROMOLY</div>
    </div>
  );
};
