import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { SolutionSceneProps } from "../lib/types";
import { easeOutBack, easeOutCubic } from "../lib/easing";
import { TextReveal } from "../components/TextReveal";
import { SuccessAnimation } from "../components/motionlib/SuccessAnimation";
import { FloatingBadge } from "../components/motionlib/FloatingBadge";
import { ParticleField } from "../components/motionlib/ParticleField";
import { useTemplate } from "../lib/templates";

// Green is semantic for "solution" — intentional regardless of template
const SOLUTION_COLOR = "#22c55e";

export const SolutionScene: React.FC<SolutionSceneProps> = ({
  headline,
  subheadline,
  badge,
  screenshotUrl,
  checkpoints = [],
  motionPlan,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const tpl = useTemplate();
  const c = tpl.colors;
  const showSuccess = motionPlan?.motionComponent === "successPulse";
  // Success fires after last checkpoint finishes: 50 + (n-1)*10 + 12 frames
  const successStartFrame = checkpoints.length > 0
    ? 50 + (checkpoints.length - 1) * 10 + 20
    : 60;

  const bgOpacity  = interpolate(frame, [0, 16], [0, 1], { extrapolateRight: "clamp" });
  const bgScale    = interpolate(frame, [0, 120], [1.04, 1.0], { extrapolateRight: "clamp" });
  const revealGlow = interpolate(frame, [0, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  const badgeScale = spring({ frame: frame - 2, fps, config: { damping: tpl.spring.damping, stiffness: tpl.spring.stiffness * 2, mass: tpl.spring.mass * 0.5 } });

  const headlineScale   = spring({ frame: frame - 8, fps, config: { damping: tpl.spring.damping, stiffness: tpl.spring.stiffness * 1.2, mass: tpl.spring.mass * 0.9 } });
  const headlineOpacity = interpolate(frame, [8, 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const subOpacity = interpolate(frame, [22, 36], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  const glowPulse = interpolate(Math.sin((frame / fps) * Math.PI * 0.6), [-1, 1], [0.15, 0.30]);

  const lineW = interpolate(frame, [28, 46], [0, 120], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", fontFamily: tpl.typography.headingFont }}>

      {/* Background */}
      <div style={{ position: "absolute", inset: 0, opacity: bgOpacity, transform: `scale(${bgScale})` }}>
        {screenshotUrl ? (
          <img src={screenshotUrl} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} />
        ) : (
          <div style={{ width: "100%", height: "100%", background: "#03120a" }} />
        )}
        <div style={{ position: "absolute", inset: 0, backdropFilter: tpl.backdropBlur > 0 ? `blur(${tpl.backdropBlur}px)` : undefined, background: "rgba(3,14,9,0.68)" }} />
      </div>

      {/* Green reveal glow */}
      <div style={{
        position: "absolute", inset: 0,
        background: `
          radial-gradient(ellipse 70% 55% at 50% 45%, rgba(34,197,94,${glowPulse}) 0%, transparent 60%),
          radial-gradient(ellipse 40% 40% at 80% 80%, ${c.accentGlow} 0%, transparent 50%),
          linear-gradient(to bottom, rgba(3,12,8,0.1) 0%, rgba(3,12,8,0.65) 100%)
        `,
        opacity: revealGlow,
        pointerEvents: "none",
      }} />

      {/* Secondary — particles + "The Fix" badge */}
      <ParticleField color={SOLUTION_COLOR} count={12} startFrame={8} intensity={0.45} />
      <div style={{ position: "absolute", top: 52, right: 60, zIndex: 4 }}>
        <FloatingBadge text="The Fix" icon="✓" variant="chip" startFrame={12} accentColor={SOLUTION_COLOR} />
      </div>

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
          display: "inline-flex", alignItems: "center", gap: 10,
          padding: "8px 22px", borderRadius: 999,
          background: `${SOLUTION_COLOR}20`,
          border: `1.5px solid ${SOLUTION_COLOR}50`,
          marginBottom: 36,
        }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: SOLUTION_COLOR, display: "inline-block",
            boxShadow: `0 0 8px ${SOLUTION_COLOR}`,
          }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: SOLUTION_COLOR, letterSpacing: "2px" }}>
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
          margin: 0, maxWidth: "18ch",
          opacity: headlineOpacity,
          transform: `scale(${headlineScale})`,
          textTransform: tpl.typography.textTransform,
        }}>
          <TextReveal text={headline} startFrame={10} wordDelay={7} />
        </h1>

        {/* Subheadline */}
        {subheadline && (
          <p style={{
            fontSize: 26, fontWeight: 400,
            color: "rgba(255,255,255,0.55)",
            lineHeight: 1.6, marginTop: 18, maxWidth: "50ch",
            opacity: subOpacity,
          }}>
            {subheadline}
          </p>
        )}

        {/* Divider */}
        <div style={{
          width: lineW, height: 3, borderRadius: 2,
          background: `linear-gradient(90deg, ${SOLUTION_COLOR}, ${c.accent})`,
          marginTop: 32, marginBottom: 40,
        }} />

        {/* Checkpoints */}
        {checkpoints.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
            {checkpoints.map((point, i) => {
              const itemOpacity = interpolate(frame, [46 + i * 10, 60 + i * 10], [0, 1], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
              });
              const itemX = interpolate(frame, [46 + i * 10, 62 + i * 10], [30, 0], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutBack,
              });
              const checkDraw = interpolate(frame, [50 + i * 10, 62 + i * 10], [0, 1], {
                extrapolateLeft: "clamp", extrapolateRight: "clamp",
              });

              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 16,
                  opacity: itemOpacity,
                  transform: `translateX(${itemX}px)`,
                  background: `${SOLUTION_COLOR}12`,
                  border: `1px solid ${SOLUTION_COLOR}30`,
                  borderRadius: 12,
                  padding: "14px 28px",
                  minWidth: 500,
                }}>
                  <svg width="28" height="28" style={{ flexShrink: 0 }}>
                    <circle cx="14" cy="14" r="13" fill={`${SOLUTION_COLOR}25`} stroke={SOLUTION_COLOR} strokeWidth="1.5" />
                    <polyline
                      points="7,14 11,18 21,10"
                      fill="none"
                      stroke={SOLUTION_COLOR}
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray="20"
                      strokeDashoffset={20 * (1 - checkDraw)}
                    />
                  </svg>
                  <span style={{ fontSize: 20, color: "rgba(255,255,255,0.82)", fontWeight: 500 }}>
                    {point}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SuccessAnimation — fires after last checkpoint */}
      {showSuccess && (
        <div style={{
          position: "absolute",
          bottom: 80, right: 100,
          zIndex: 10,
        }}>
          <SuccessAnimation
            color={SOLUTION_COLOR}
            size={100}
            label="Done!"
            startFrame={successStartFrame}
            exitStartFrame={9999}
          />
        </div>
      )}

      {/* Bottom green bar */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 3,
        background: `linear-gradient(90deg, transparent, ${SOLUTION_COLOR}, ${c.accent}, transparent)`,
        opacity: 0.7,
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
