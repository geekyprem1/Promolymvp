import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { easeOutCubic } from "../../lib/easing";
import { useTemplate } from "../../lib/templates";

export interface ProgressBarProps {
  fromPercent?: number;
  toPercent: number;
  label?: string;
  showValue?: boolean;
  accentColor?: string;
  height?: number;
  startFrame?: number;
  exitStartFrame?: number;
  style?: React.CSSProperties;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  fromPercent = 0,
  toPercent,
  label,
  showValue = true,
  accentColor,
  height = 16,
  startFrame = 0,
  exitStartFrame = 999,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const accent = accentColor ?? tpl.colors.accent;
  const f = frame - startFrame;

  // Enter: bar fills from left via spring
  const progress = spring({ frame: f, fps, config: { damping: 18, stiffness: 55, mass: 1.1 } });
  const currentPct = fromPercent + (toPercent - fromPercent) * progress;

  const opacity = interpolate(f, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const slideY = interpolate(f, [0, 18], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Idle: glow shimmer
  const shimmerXNum = interpolate((f % 70) / 70, [0, 1], [-10, 110]);
  const shimmerX = `${shimmerXNum}%`;
  const glowOpacity = interpolate(Math.sin((f / fps) * Math.PI * 1.0), [-1, 1], [0.3, 0.7]);

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 15], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const isExiting = frame >= exitStartFrame;
  const finalOpacity = isExiting ? exitOpacity : opacity;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        width: "100%",
        opacity: finalOpacity,
        transform: `translateY(${slideY}px)`,
        fontFamily: tpl.typography.bodyFont,
        ...style,
      }}
    >
      {(label || showValue) && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          {label && (
            <span style={{ fontSize: 18, fontWeight: 600, color: tpl.colors.textMuted, letterSpacing: "1px" }}>
              {label}
            </span>
          )}
          {showValue && (
            <span style={{ fontSize: 20, fontWeight: 700, color: accent }}>
              {Math.round(currentPct)}%
            </span>
          )}
        </div>
      )}
      {/* Track */}
      <div
        style={{
          width: "100%",
          height,
          background: tpl.colors.surface,
          border: `1px solid ${tpl.colors.border}`,
          borderRadius: height,
          overflow: "hidden",
          position: "relative",
        }}
      >
        {/* Fill */}
        <div
          style={{
            width: `${currentPct}%`,
            height: "100%",
            background: `linear-gradient(90deg, ${accent}cc, ${accent})`,
            borderRadius: height,
            position: "relative",
            overflow: "hidden",
            boxShadow: `0 0 16px ${accent}88`,
            transition: "width 0.1s",
          }}
        >
          {/* Shimmer */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: shimmerX,
              width: "30%",
              height: "100%",
              background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)",
              opacity: glowOpacity,
            }}
          />
        </div>
        {/* End glow dot */}
        {currentPct > 2 && (
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: `${Math.min(currentPct, 98)}%`,
              transform: "translate(-50%, -50%)",
              width: height + 4,
              height: height + 4,
              borderRadius: "50%",
              background: accent,
              boxShadow: `0 0 12px ${accent}`,
              opacity: glowOpacity,
            }}
          />
        )}
      </div>
    </div>
  );
};
