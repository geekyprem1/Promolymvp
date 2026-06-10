import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { theme, fonts } from "../../lib/theme";
import { easeOutCubic } from "../../lib/easing";

export interface MetricCounterProps {
  from?: number;
  to: number;
  prefix?: string;
  suffix?: string;
  label?: string;
  decimals?: number;
  accentColor?: string;
  startFrame?: number;
  exitStartFrame?: number;
  style?: React.CSSProperties;
}

export const MetricCounter: React.FC<MetricCounterProps> = ({
  from = 0,
  to,
  prefix = "",
  suffix = "",
  label = "",
  decimals = 0,
  accentColor = theme.accent,
  startFrame = 0,
  exitStartFrame = 999,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;

  // Enter
  const opacity = interpolate(f, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const scale = spring({ frame: f, fps, config: { damping: 12, stiffness: 100 } });

  // Count-up via spring
  const progress = spring({ frame: f, fps, config: { damping: 18, stiffness: 60, mass: 1.2 } });
  const currentValue = from + (to - from) * progress;

  // Idle: number glow pulse
  const glowPulse = interpolate(Math.sin((f / fps) * Math.PI * 0.8), [-1, 1], [0.4, 1]);

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 15], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const isExiting = frame >= exitStartFrame;
  const finalOpacity = isExiting ? exitOpacity : opacity;

  const displayValue = currentValue.toFixed(decimals);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 14,
        opacity: finalOpacity,
        transform: `scale(${scale})`,
        fontFamily: fonts.heading,
        ...style,
      }}
    >
      <div
        style={{
          fontSize: 96,
          fontWeight: 800,
          color: accentColor,
          lineHeight: 1,
          letterSpacing: "-2px",
          textShadow: `0 0 ${40 * glowPulse}px ${accentColor}88`,
        }}
      >
        {prefix}{displayValue}{suffix}
      </div>
      {label && (
        <div
          style={{
            fontSize: 20,
            fontWeight: 500,
            color: theme.textMuted,
            textTransform: "uppercase",
            letterSpacing: "3px",
          }}
        >
          {label}
        </div>
      )}
      <div style={{ width: 60, height: 2, background: accentColor, borderRadius: 1, opacity: 0.5 }} />
    </div>
  );
};
