import React from "react";
import { useCurrentFrame, interpolate, useVideoConfig } from "remotion";

export interface AnimatedGridProps {
  color?: string;
  dotSize?: number;
  spacing?: number;
  opacity?: number;
  startFrame?: number;
  scanLine?: boolean;
}

export const AnimatedGrid: React.FC<AnimatedGridProps> = ({
  color = "#ffffff",
  dotSize = 1.5,
  spacing = 60,
  opacity = 0.12,
  startFrame = 0,
  scanLine = true,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const f = frame - startFrame;

  const fieldOpacity = interpolate(f, [0, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Scan-line sweeps top→bottom every ~3 seconds
  const scanPeriod = fps * 3;
  const scanPos = ((f % scanPeriod) / scanPeriod) * (height + 80) - 40;
  const scanOpacity = interpolate(
    Math.sin(((f % scanPeriod) / scanPeriod) * Math.PI),
    [0, 1],
    [0, 0.5],
  );

  const cols = Math.ceil(width / spacing) + 1;
  const rows = Math.ceil(height / spacing) + 1;
  const dots: { cx: number; cy: number }[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      dots.push({ cx: c * spacing, cy: r * spacing });
    }
  }

  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden", opacity: fieldOpacity }}>
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        {dots.map((d, i) => {
          // Dots near scan-line glow brighter
          const distToScan = Math.abs(d.cy - scanPos);
          const glowBoost = interpolate(distToScan, [0, 60], [3, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const r = dotSize + glowBoost * 0.8;
          const dotOpacity = opacity + glowBoost * 0.04;

          return (
            <circle
              key={i}
              cx={d.cx}
              cy={d.cy}
              r={r}
              fill={color}
              opacity={dotOpacity}
            />
          );
        })}

        {/* Scan-line bar */}
        {scanLine && (
          <rect
            x={0}
            y={scanPos - 1}
            width={width}
            height={3}
            fill={`url(#scan-gradient-${startFrame})`}
            opacity={scanOpacity}
          />
        )}

        <defs>
          <linearGradient id={`scan-gradient-${startFrame}`} x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%"   stopColor={color} stopOpacity="0" />
            <stop offset="20%"  stopColor={color} stopOpacity="0.8" />
            <stop offset="50%"  stopColor={color} stopOpacity="1" />
            <stop offset="80%"  stopColor={color} stopOpacity="0.8" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};
