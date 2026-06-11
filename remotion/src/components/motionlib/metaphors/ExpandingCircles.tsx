import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { useTemplate } from "../../../lib/templates";

interface Props {
  intensity?: number;
  startFrame?: number;
  size?: number;
  rings?: number;
}

export const ExpandingCircles: React.FC<Props> = ({
  intensity = 0.8,
  startFrame = 0,
  size = 180,
  rings = 5,
}) => {
  const frame = useCurrentFrame();
  const tpl = useTemplate();
  const f = Math.max(0, frame - startFrame);

  const cx = size / 2;
  const cy = size / 2;
  const maxR = size * 0.48;

  const ringData = Array.from({ length: rings }, (_, i) => {
    const cycleLen = 60;
    const delay = (i / rings) * cycleLen;
    const prog = ((f + delay) % cycleLen) / cycleLen;
    const r = interpolate(prog, [0, 1], [10, maxR * intensity]);
    const a = interpolate(prog, [0, 0.15, 0.8, 1], [0, 0.6, 0.15, 0]);
    return { r, a };
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: "visible" }}>
      {/* Center dot */}
      <circle cx={cx} cy={cy} r={8} fill={tpl.colors.accent} opacity={0.9} />
      <circle cx={cx} cy={cy} r={4} fill="#ffffff" opacity={0.6} />

      {/* Expanding rings */}
      {ringData.map((rd, i) => (
        <circle
          key={i}
          cx={cx}
          cy={cy}
          r={rd.r}
          fill="none"
          stroke={tpl.colors.accent}
          strokeWidth={2 - i * 0.25}
          opacity={rd.a}
        />
      ))}
    </svg>
  );
};
