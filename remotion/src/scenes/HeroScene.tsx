import React from "react";
import { useCurrentFrame, interpolate, useVideoConfig } from "remotion";
import { HeroSceneProps } from "../lib/types";
import { TextReveal } from "../components/TextReveal";
import { Badge } from "../components/Badge";
import { easeOutCubic } from "../lib/easing";
import { useTemplate } from "../lib/templates";

export const HeroScene: React.FC<HeroSceneProps> = ({
  headline,
  subheadline,
  badge,
  screenshotUrl,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();

  const bgScale   = interpolate(frame, [0, 120], [1.08, 1.02], { extrapolateRight: "clamp" });
  const bgX       = interpolate(frame, [0, 120], [0, -15],     { extrapolateRight: "clamp" });
  const bgOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  const contentOpacity = interpolate(frame, [8, 28], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });

  const lineWidth = interpolate(frame, [35, 55], [0, 72], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });

  const blur = tpl.backdropBlur;

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden", fontFamily: tpl.typography.headingFont }}>

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
          backdropFilter: blur > 0 ? `blur(${blur}px)` : undefined,
          background: `${tpl.colors.bg}99`,
        }} />
      </div>

      {/* Gradient overlays */}
      <div style={{
        position: "absolute", inset: 0,
        background: tpl.colors.heroOverlay,
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
          fontSize: Math.round(108 * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight,
          color: tpl.colors.text,
          lineHeight: tpl.typography.lineHeight,
          letterSpacing: tpl.typography.letterSpacing,
          margin: 0,
          maxWidth: "14ch",
          textTransform: tpl.typography.textTransform,
        }}>
          <TextReveal text={headline} startFrame={12} wordDelay={6} />
        </h1>

        {subheadline && (
          <p style={{
            fontSize: 28, fontWeight: 400,
            color: tpl.colors.textMuted,
            lineHeight: 1.6, marginTop: 20,
            maxWidth: "50ch",
          }}>
            <TextReveal text={subheadline} startFrame={22} wordDelay={4} color={tpl.colors.textMuted} />
          </p>
        )}

        {/* Accent line */}
        <div style={{
          width: lineWidth, height: 4, borderRadius: 2, marginTop: 36,
          background: `linear-gradient(90deg, ${tpl.colors.gradientFrom}, ${tpl.colors.gradientTo})`,
        }} />
      </div>

      {/* Watermark */}
      <div style={{
        position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase",
        color: tpl.colors.textFaint,
        fontFamily: tpl.typography.bodyFont,
      }}>PROMOLY</div>
    </div>
  );
};
