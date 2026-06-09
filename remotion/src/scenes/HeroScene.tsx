import React from "react";
import { useCurrentFrame, interpolate, useVideoConfig } from "remotion";
import { HeroSceneProps } from "../lib/types";
import { TextReveal } from "../components/TextReveal";
import { Badge } from "../components/Badge";
import { easeOutCubic } from "../lib/easing";

export const HeroScene: React.FC<HeroSceneProps> = ({
  headline,
  subheadline,
  badge,
  screenshotUrl,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  // Blurred background pan
  const bgScale = interpolate(frame, [0, 120], [1.08, 1.02], { extrapolateRight: "clamp" });
  const bgX     = interpolate(frame, [0, 120], [0, -15],     { extrapolateRight: "clamp" });
  const bgOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  // Content fade-in
  const contentOpacity = interpolate(frame, [8, 28], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });

  // Accent line slide-in
  const lineWidth = interpolate(frame, [35, 55], [0, 72], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", fontFamily: "'Inter', sans-serif" }}>

      {/* Blurred background */}
      <div style={{
        position: "absolute", inset: 0, opacity: bgOpacity,
        transform: `scale(${bgScale}) translateX(${bgX}px)`,
      }}>
        <img
          src={screenshotUrl}
          style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }}
        />
        <div style={{
          position: "absolute", inset: 0,
          backdropFilter: "blur(28px)",
          background: "rgba(7,7,18,0.55)",
        }} />
      </div>

      {/* Gradient overlays */}
      <div style={{
        position: "absolute", inset: 0,
        background: `
          radial-gradient(ellipse 100% 80% at 30% 40%, rgba(99,102,241,0.22) 0%, transparent 60%),
          radial-gradient(ellipse 80% 100% at 75% 60%, rgba(139,92,246,0.14) 0%, transparent 55%),
          linear-gradient(to bottom, rgba(7,7,18,0.3) 0%, rgba(7,7,18,0.55) 50%, rgba(7,7,18,0.80) 100%)
        `,
      }} />

      {/* Content */}
      <div style={{
        position: "relative", zIndex: 2,
        width: "100%", height: "100%",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        textAlign: "center", padding: "0 240px",
        opacity: contentOpacity,
      }}>
        <Badge text={badge} startFrame={5} />

        <h1 style={{
          fontSize: 108, fontWeight: 800, color: "#fff",
          lineHeight: 1.05, letterSpacing: -3, margin: 0,
          maxWidth: "14ch",
        }}>
          <TextReveal text={headline} startFrame={12} wordDelay={6} />
        </h1>

        {subheadline && (
          <p style={{
            fontSize: 28, fontWeight: 400,
            color: "rgba(255,255,255,0.55)",
            lineHeight: 1.6, marginTop: 20,
            maxWidth: "50ch",
          }}>
            <TextReveal text={subheadline} startFrame={22} wordDelay={4} color="rgba(255,255,255,0.55)" />
          </p>
        )}

        {/* Accent line */}
        <div style={{
          width: lineWidth, height: 4, borderRadius: 2, marginTop: 36,
          background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
        }} />
      </div>

      {/* Promoly watermark */}
      <div style={{
        position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase",
        color: "rgba(255,255,255,0.18)",
        fontFamily: "'Inter', sans-serif",
      }}>PROMOLY</div>
    </div>
  );
};
