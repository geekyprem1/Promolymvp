import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { easeOutBack, easeOutCubic } from "../../lib/easing";
import { useTemplate } from "../../lib/templates";

export interface FloatingBadgeProps {
  text: string;
  icon?: string;
  accentColor?: string;
  variant?: "pill" | "tag" | "chip";
  startFrame?: number;
  exitStartFrame?: number;
  style?: React.CSSProperties;
}

export const FloatingBadge: React.FC<FloatingBadgeProps> = ({
  text,
  icon,
  accentColor,
  variant = "pill",
  startFrame = 0,
  exitStartFrame = 999,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const accent = accentColor ?? tpl.colors.accent;
  const f = frame - startFrame;

  // Enter: pop + fade
  const scale = spring({ frame: f, fps, config: { damping: 10, stiffness: 180, mass: 0.6 } });
  const opacity = interpolate(f, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Idle: bobbing float
  const floatY = interpolate(Math.sin((f / fps) * Math.PI * 0.9), [-1, 1], [-8, 8]);
  const floatRotate = interpolate(Math.sin((f / fps) * Math.PI * 0.5), [-1, 1], [-2, 2]);

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 12], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exitScale = interpolate(exitF, [0, 12], [1, 0.7], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const isExiting = frame >= exitStartFrame;
  const finalOpacity = isExiting ? exitOpacity : opacity;
  const finalScale = isExiting ? exitScale : scale;
  const finalY = isExiting ? 0 : (f > 15 ? floatY : 0);
  const finalRot = f > 15 ? floatRotate : 0;

  const borderRadius = variant === "pill" ? 999 : variant === "tag" ? 6 : 10;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: variant === "chip" ? "8px 18px" : "10px 22px",
        background: `${accent}22`,
        border: `1.5px solid ${accent}66`,
        borderRadius,
        opacity: finalOpacity,
        transform: `scale(${finalScale}) translateY(${finalY}px) rotate(${finalRot}deg)`,
        boxShadow: `0 4px 24px ${accent}30`,
        fontFamily: tpl.typography.bodyFont,
        ...style,
      }}
    >
      {icon && <span style={{ fontSize: 18 }}>{icon}</span>}
      <span
        style={{
          fontSize: 16,
          fontWeight: 700,
          color: accent,
          letterSpacing: "1.5px",
          textTransform: "uppercase",
        }}
      >
        {text}
      </span>
    </div>
  );
};
