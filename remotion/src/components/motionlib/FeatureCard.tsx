import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { easeOutBack, easeOutCubic } from "../../lib/easing";
import { useTemplate } from "../../lib/templates";

export interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  accentColor?: string;
  startFrame?: number;
  exitStartFrame?: number;
  style?: React.CSSProperties;
}

export const FeatureCard: React.FC<FeatureCardProps> = ({
  icon,
  title,
  description,
  accentColor,
  startFrame = 0,
  exitStartFrame = 999,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const accent = accentColor ?? tpl.colors.accent;
  const f = frame - startFrame;

  // Enter
  const scale = spring({ frame: f, fps, config: { damping: 14, stiffness: 120, mass: 0.8 } });
  const opacity = interpolate(f, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const translateY = interpolate(f, [0, 20], [40, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Idle: gentle float
  const idleFloat = interpolate(Math.sin((f / fps) * Math.PI * 0.6), [-1, 1], [-4, 4]);

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 15], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exitScale = interpolate(exitF, [0, 15], [1, 0.92], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const isExiting = frame >= exitStartFrame;
  const finalOpacity = isExiting ? exitOpacity : opacity;
  const finalScale = isExiting ? exitScale : scale;
  const finalY = isExiting ? 0 : translateY + (f > 20 ? idleFloat : 0);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        padding: "44px 40px",
        background: tpl.colors.surface,
        border: `1.5px solid ${accent}33`,
        borderRadius: 20,
        width: 380,
        opacity: finalOpacity,
        transform: `scale(${finalScale}) translateY(${finalY}px)`,
        boxShadow: `0 0 40px ${accent}18`,
        fontFamily: tpl.typography.bodyFont,
        ...style,
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: 16,
          background: `${accent}22`,
          border: `1.5px solid ${accent}44`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 30,
        }}
      >
        {icon}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: tpl.colors.text, lineHeight: 1.2 }}>
        {title}
      </div>
      <div style={{ fontSize: 18, color: tpl.colors.textMuted, lineHeight: 1.6 }}>
        {description}
      </div>
      <div style={{ width: 48, height: 3, borderRadius: 2, background: accent, marginTop: 4 }} />
    </div>
  );
};
