import React from "react";
import { useCurrentFrame, spring, interpolate, useVideoConfig } from "remotion";
import { useTemplate } from "../../../lib/templates";

interface Props {
  intensity?: number;
  startFrame?: number;
  size?: number;
}

export const GrowthChart: React.FC<Props> = ({
  intensity = 0.8,
  startFrame = 0,
  size = 200,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const f = Math.max(0, frame - startFrame);

  const bars = [
    { delay: 0,  height: 0.35 },
    { delay: 6,  height: 0.55 },
    { delay: 12, height: 0.45 },
    { delay: 18, height: 0.70 },
    { delay: 24, height: 0.60 },
    { delay: 30, height: 0.90 },
  ];

  const chartH = 100;
  const chartW = 120;
  const barW = 14;
  const gap = 6;

  // Animated line path for the trend overlay
  const lineProgress = spring({ frame: f, fps, config: { stiffness: 40, damping: 20 } });

  const barHeights = bars.map(({ delay, height }) => {
    const prog = spring({ frame: Math.max(0, f - delay), fps, config: { stiffness: 60, damping: 18 } });
    return chartH * height * intensity * prog;
  });

  // Build line path
  const linePoints = bars.map((_, i) => {
    const x = i * (barW + gap) + barW / 2;
    const y = chartH - barHeights[i];
    return `${x},${y}`;
  });
  const linePath = `M ${linePoints.slice(0, Math.ceil(linePoints.length * lineProgress)).join(" L ")}`;

  const glowOpacity = 0.15 + 0.1 * Math.sin(f * 0.1);

  return (
    <svg
      width={size}
      height={size * 0.75}
      viewBox={`-10 -10 ${chartW + 20} ${chartH + 20}`}
      style={{ overflow: "visible" }}
    >
      {/* Glow bg */}
      <rect
        x={-10} y={-10}
        width={chartW + 20} height={chartH + 20}
        fill={tpl.colors.accent}
        opacity={glowOpacity}
        rx={8}
        style={{ filter: "blur(12px)" }}
      />

      {/* Bars */}
      {bars.map((_, i) => (
        <g key={i}>
          <rect
            x={i * (barW + gap)}
            y={chartH - barHeights[i]}
            width={barW}
            height={barHeights[i]}
            rx={3}
            fill={tpl.colors.accent}
            opacity={0.85}
          />
          {/* Highlight top */}
          <rect
            x={i * (barW + gap)}
            y={chartH - barHeights[i]}
            width={barW}
            height={4}
            rx={2}
            fill="#ffffff"
            opacity={0.4}
          />
        </g>
      ))}

      {/* Trend line */}
      {lineProgress > 0.05 && (
        <polyline
          points={linePoints.slice(0, Math.ceil(linePoints.length * lineProgress)).join(" ")}
          fill="none"
          stroke="#ffffff"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.8}
        />
      )}

      {/* X axis */}
      <line x1={0} y1={chartH} x2={chartW - gap} y2={chartH} stroke={tpl.colors.text} strokeWidth={1} opacity={0.2} />
    </svg>
  );
};
