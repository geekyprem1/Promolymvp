import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { theme } from "../../lib/theme";
import { easeOutCubic } from "../../lib/easing";

export interface HighlightRingProps {
  x: number;
  y: number;
  radius?: number;
  color?: string;
  thickness?: number;
  startFrame?: number;
  exitStartFrame?: number;
}

export const HighlightRing: React.FC<HighlightRingProps> = ({
  x,
  y,
  radius = 60,
  color = theme.accent,
  thickness = 3,
  startFrame = 0,
  exitStartFrame = 999,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;

  // Enter: ring expands in
  const ringScale = spring({ frame: f, fps, config: { damping: 14, stiffness: 120 } });
  const enterOpacity = interpolate(f, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Idle: dual pulse rings
  const pulse1 = interpolate(Math.sin((f / fps) * Math.PI * 1.2), [-1, 1], [0, 1]);
  const pulse2 = interpolate(Math.sin((f / fps) * Math.PI * 1.2 + Math.PI), [-1, 1], [0, 1]);
  const pulse1Size = radius + 20 * pulse1;
  const pulse1Opacity = 0.6 * (1 - pulse1);
  const pulse2Size = radius + 35 * pulse2;
  const pulse2Opacity = 0.35 * (1 - pulse2);

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 15], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exitScale = interpolate(exitF, [0, 15], [1, 1.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const isExiting = frame >= exitStartFrame;
  const finalOpacity = isExiting ? exitOpacity : enterOpacity;
  const finalScale = isExiting ? exitScale : ringScale;

  const size = (radius + 40) * 2;

  return (
    <svg
      style={{
        position: "absolute",
        left: x - size / 2,
        top: y - size / 2,
        opacity: finalOpacity,
        transform: `scale(${finalScale})`,
        pointerEvents: "none",
        overflow: "visible",
      }}
      width={size}
      height={size}
    >
      {/* Pulse ring 2 (outer) */}
      {f > 10 && (
        <circle
          cx={size / 2}
          cy={size / 2}
          r={pulse2Size}
          fill="none"
          stroke={color}
          strokeWidth={thickness * 0.5}
          opacity={pulse2Opacity}
        />
      )}
      {/* Pulse ring 1 */}
      {f > 10 && (
        <circle
          cx={size / 2}
          cy={size / 2}
          r={pulse1Size}
          fill="none"
          stroke={color}
          strokeWidth={thickness * 0.7}
          opacity={pulse1Opacity}
        />
      )}
      {/* Main ring */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={thickness}
        filter={`drop-shadow(0 0 8px ${color})`}
      />
      {/* Center dot */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={4}
        fill={color}
        opacity={0.8}
      />
    </svg>
  );
};
