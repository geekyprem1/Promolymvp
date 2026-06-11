import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { useTemplate } from "../../../lib/templates";

interface Props {
  intensity?: number;
  startFrame?: number;
  width?: number;
  height?: number;
}

// Generate deterministic lines
const LINES = Array.from({ length: 14 }, (_, i) => ({
  y: 6 + i * 7,
  speed: 0.6 + (i % 3) * 0.4,
  length: 40 + (i % 5) * 20,
  delay: (i * 7) % 30,
  opacity: 0.3 + (i % 4) * 0.15,
}));

export const SpeedLines: React.FC<Props> = ({
  intensity = 0.9,
  startFrame = 0,
  width = 220,
  height = 100,
}) => {
  const frame = useCurrentFrame();
  const tpl = useTemplate();
  const f = Math.max(0, frame - startFrame);

  const fadeIn = interpolate(f, [0, 12], [0, 1], { extrapolateRight: "clamp" });

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: "hidden" }}>
      {LINES.map((line, i) => {
        const offset = ((f * line.speed * intensity * 3 + line.delay * 8) % (width + line.length));
        const x = width - offset;
        return (
          <line
            key={i}
            x1={x}
            y1={line.y}
            x2={x + line.length}
            y2={line.y}
            stroke={tpl.colors.accent}
            strokeWidth={i % 4 === 0 ? 2 : 1}
            opacity={line.opacity * fadeIn * intensity}
            strokeLinecap="round"
          />
        );
      })}
      {/* Fast center streak */}
      {(() => {
        const cx = width - ((f * 6 * intensity) % (width + 80));
        return (
          <line
            x1={cx}
            y1={height / 2}
            x2={cx + 80}
            y2={height / 2}
            stroke="#ffffff"
            strokeWidth={2}
            opacity={0.5 * fadeIn}
            strokeLinecap="round"
          />
        );
      })()}
    </svg>
  );
};
