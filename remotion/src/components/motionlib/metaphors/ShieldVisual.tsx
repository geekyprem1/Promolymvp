import React from "react";
import { useCurrentFrame, spring, interpolate, useVideoConfig } from "remotion";
import { useTemplate } from "../../../lib/templates";

interface Props {
  intensity?: number;
  startFrame?: number;
  size?: number;
}

export const ShieldVisual: React.FC<Props> = ({
  intensity = 0.6,
  startFrame = 0,
  size = 160,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const f = Math.max(0, frame - startFrame);

  const draw = spring({ frame: f, fps, config: { stiffness: 50, damping: 22 } });
  const checkScale = spring({ frame: Math.max(0, f - 20), fps, config: { stiffness: 200, damping: 16 } });

  // Pulse rings
  const pulseRings = [0, 18, 36].map((offset) => {
    const pf = Math.max(0, f - offset);
    const prog = interpolate(pf % 60, [0, 60], [0, 1], { extrapolateRight: "clamp" });
    const r = interpolate(prog, [0, 1], [38, 68]);
    const a = interpolate(prog, [0, 0.3, 1], [0, 0.4 * intensity, 0]);
    return { r, a };
  });

  // Shield path (simplified)
  const shieldPath = "M50,8 L88,22 L88,52 C88,72 50,92 50,92 C50,92 12,72 12,52 L12,22 Z";
  // Circumference of shield outline ~200px
  const dashLen = 200;
  const dashOffset = interpolate(draw, [0, 1], [dashLen, 0]);

  const glowA = 0.1 + 0.08 * Math.sin(f * 0.08) * intensity;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      style={{ overflow: "visible" }}
    >
      {/* Pulse rings */}
      {pulseRings.map((pr, i) => (
        <circle key={i} cx={50} cy={52} r={pr.r} fill="none" stroke={tpl.colors.accent} strokeWidth={1.5} opacity={pr.a} />
      ))}

      {/* Shield glow bg */}
      <path d={shieldPath} fill={tpl.colors.accent} opacity={glowA} style={{ filter: "blur(8px)" }} />

      {/* Shield body fill */}
      <path d={shieldPath} fill={tpl.colors.surface} opacity={0.9 * draw} />

      {/* Shield outline draw-on */}
      <path
        d={shieldPath}
        fill="none"
        stroke={tpl.colors.accent}
        strokeWidth={3}
        strokeDasharray={dashLen}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Checkmark */}
      <g transform={`translate(50,52) scale(${checkScale})`}>
        <path
          d="M-14,0 L-4,10 L14,-10"
          fill="none"
          stroke={tpl.colors.accent}
          strokeWidth={5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
    </svg>
  );
};
