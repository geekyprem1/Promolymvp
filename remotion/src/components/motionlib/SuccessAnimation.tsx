import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { theme } from "../../lib/theme";
import { easeOutBack, easeOutCubic } from "../../lib/easing";

export interface SuccessAnimationProps {
  color?: string;
  size?: number;
  label?: string;
  startFrame?: number;
  exitStartFrame?: number;
  style?: React.CSSProperties;
}

export const SuccessAnimation: React.FC<SuccessAnimationProps> = ({
  color = "#22c55e",
  size = 120,
  label = "Success!",
  startFrame = 0,
  exitStartFrame = 999,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;

  // Circle scale-in
  const circleScale = spring({ frame: f, fps, config: { damping: 10, stiffness: 160, mass: 0.8 } });

  // Checkmark stroke-draw
  const checkProgress = interpolate(f, [8, 28], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Burst particles (8 lines)
  const burstProgress = interpolate(f, [20, 45], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const burstOpacity = interpolate(f, [20, 50], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Label fade-in
  const labelOpacity = interpolate(f, [30, 44], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const labelY = interpolate(f, [30, 44], [12, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Idle: gentle pulse
  const idlePulse = 1 + interpolate(Math.sin((f / fps) * Math.PI * 0.6), [-1, 1], [-0.03, 0.03]);

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 15], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exitScale = interpolate(exitF, [0, 15], [1, 1.2], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const isExiting = frame >= exitStartFrame;
  const finalScale = isExiting ? exitScale : circleScale * idlePulse;
  const finalOpacity = isExiting ? exitOpacity : 1;

  const r = size / 2;
  const checkLen = 80;
  // Checkmark path: from (r*0.35, r) to (r*0.6, r*1.3) to (r*1.1, r*0.5)
  const cx = r, cy = r;
  const p1 = { x: cx - r * 0.28, y: cy + r * 0.08 };
  const p2 = { x: cx - r * 0.05, y: cy + r * 0.32 };
  const p3 = { x: cx + r * 0.38, y: cy - r * 0.22 };
  const totalLen = 70; // approximate checkmark path length in SVG units
  const dashOffset = totalLen * (1 - checkProgress);

  const burstLines = Array.from({ length: 8 }, (_, i) => {
    const angle = (i / 8) * Math.PI * 2;
    const r1 = r * 1.2 + burstProgress * r * 0.6;
    const r2 = r1 + burstProgress * r * 0.5;
    return {
      x1: cx + Math.cos(angle) * r1,
      y1: cy + Math.sin(angle) * r1,
      x2: cx + Math.cos(angle) * r2,
      y2: cy + Math.sin(angle) * r2,
    };
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 24,
        opacity: finalOpacity,
        transform: `scale(${finalScale})`,
        ...style,
      }}
    >
      <svg width={size * 2.4} height={size * 2.4} style={{ overflow: "visible" }}>
        <g transform={`translate(${size * 0.7}, ${size * 0.7})`}>
          {/* Burst lines */}
          {f > 20 && burstLines.map((line, i) => (
            <line
              key={i}
              x1={line.x1} y1={line.y1}
              x2={line.x2} y2={line.y2}
              stroke={color}
              strokeWidth={3}
              strokeLinecap="round"
              opacity={burstOpacity}
            />
          ))}
          {/* Background circle */}
          <circle cx={cx} cy={cy} r={r} fill={`${color}22`} stroke={`${color}44`} strokeWidth={2} />
          {/* Main circle (scales in) */}
          <circle
            cx={cx} cy={cy} r={r}
            fill={`${color}15`}
            stroke={color}
            strokeWidth={3}
            style={{ filter: `drop-shadow(0 0 12px ${color}88)` }}
          />
          {/* Checkmark */}
          <polyline
            points={`${p1.x},${p1.y} ${p2.x},${p2.y} ${p3.x},${p3.y}`}
            fill="none"
            stroke={color}
            strokeWidth={5}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={totalLen}
            strokeDashoffset={dashOffset}
          />
        </g>
      </svg>
      {label && (
        <div
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: color,
            opacity: labelOpacity,
            transform: `translateY(${labelY}px)`,
            letterSpacing: "2px",
          }}
        >
          {label}
        </div>
      )}
    </div>
  );
};
