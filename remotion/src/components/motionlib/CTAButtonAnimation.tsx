import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { theme, fonts } from "../../lib/theme";
import { easeOutBack, easeOutCubic } from "../../lib/easing";

export interface CTAButtonAnimationProps {
  label: string;
  variant?: "primary" | "outline" | "ghost";
  accentColor?: string;
  icon?: string;
  startFrame?: number;
  exitStartFrame?: number;
  style?: React.CSSProperties;
}

export const CTAButtonAnimation: React.FC<CTAButtonAnimationProps> = ({
  label,
  variant = "primary",
  accentColor = theme.accent,
  icon,
  startFrame = 0,
  exitStartFrame = 999,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;

  // Enter: bounce in
  const scale = spring({ frame: f, fps, config: { damping: 10, stiffness: 140, mass: 0.7 } });
  const opacity = interpolate(f, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Idle: shimmer sweep
  const shimmerX = interpolate((f % 80) / 80, [0, 1], [-200, 400]);

  // Idle: subtle scale breathe
  const breathe = 1 + interpolate(Math.sin((f / fps) * Math.PI * 0.7), [-1, 1], [-0.01, 0.01]);

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 15], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exitScale = interpolate(exitF, [0, 15], [1, 0.88], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const isExiting = frame >= exitStartFrame;
  const finalOpacity = isExiting ? exitOpacity : opacity;
  const finalScale = isExiting ? exitScale : scale * breathe;

  const isPrimary = variant === "primary";
  const isOutline = variant === "outline";

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 14,
        padding: "24px 56px",
        background: isPrimary ? accentColor : isOutline ? "transparent" : `${accentColor}15`,
        border: `2px solid ${isPrimary ? "transparent" : accentColor}`,
        borderRadius: 16,
        opacity: finalOpacity,
        transform: `scale(${finalScale})`,
        position: "relative",
        overflow: "hidden",
        cursor: "pointer",
        boxShadow: isPrimary ? `0 8px 40px ${accentColor}55` : "none",
        fontFamily: fonts.heading,
        ...style,
      }}
    >
      {/* Shimmer (primary only) */}
      {isPrimary && f > 10 && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: shimmerX,
            width: 120,
            height: "100%",
            background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent)",
            transform: "skewX(-20deg)",
            pointerEvents: "none",
          }}
        />
      )}
      {icon && <span style={{ fontSize: 24 }}>{icon}</span>}
      <span
        style={{
          fontSize: 24,
          fontWeight: 700,
          color: isPrimary ? "#ffffff" : accentColor,
          letterSpacing: "1px",
          position: "relative",
        }}
      >
        {label}
      </span>
    </div>
  );
};
