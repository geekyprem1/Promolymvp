import React from "react";
import { useCurrentFrame, spring, interpolate, useVideoConfig } from "remotion";
import { useTemplate } from "../../../lib/templates";

interface Props {
  intensity?: number;
  startFrame?: number;
  size?: number;
}

export const RocketAnimation: React.FC<Props> = ({
  intensity = 1.0,
  startFrame = 0,
  size = 180,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const f = Math.max(0, frame - startFrame);

  const lift = spring({ frame: f, fps, config: { stiffness: 60, damping: 18 } });
  const y = interpolate(lift, [0, 1], [0, -120 * intensity]);
  const tilt = interpolate(Math.sin(f * 0.08), [-1, 1], [-6, 6]);

  // Fire trail flicker
  const flicker = 0.6 + 0.4 * Math.sin(f * 0.6);
  const trailLen = interpolate(lift, [0, 1], [10, 60 * intensity]);

  // Smoke puffs
  const puffs = [0, 12, 24, 36].map((offset) => {
    const pf = Math.max(0, f - offset);
    const a = interpolate(pf, [0, 8, 24], [0, 0.35, 0], { extrapolateRight: "clamp" });
    const py = interpolate(pf, [0, 24], [0, 40]);
    const ps = interpolate(pf, [0, 24], [4, 18]);
    return { a, py, ps };
  });

  return (
    <svg
      width={size}
      height={size * 1.4}
      viewBox="0 0 100 140"
      style={{ transform: `translateY(${y}px) rotate(${tilt}deg)`, overflow: "visible" }}
    >
      {/* Smoke puffs */}
      {puffs.map((p, i) => (
        <circle
          key={i}
          cx={50}
          cy={120 + p.py}
          r={p.ps}
          fill="#888"
          opacity={p.a}
        />
      ))}

      {/* Fire trail */}
      <ellipse
        cx={50}
        cy={118}
        rx={10}
        ry={trailLen * 0.4 * flicker}
        fill={tpl.colors.accent}
        opacity={0.85 * flicker}
        style={{ filter: `blur(4px)` }}
      />
      <ellipse
        cx={50}
        cy={118}
        rx={5}
        ry={trailLen * 0.25}
        fill="#ffffff"
        opacity={0.6 * flicker}
      />

      {/* Rocket body */}
      <path
        d="M50 10 C35 20 30 55 30 80 L70 80 C70 55 65 20 50 10 Z"
        fill={tpl.colors.accent}
      />
      {/* Nose cone */}
      <path
        d="M50 10 C44 22 44 35 50 38 C56 35 56 22 50 10 Z"
        fill={tpl.colors.secondary}
        opacity={0.7}
      />
      {/* Window */}
      <circle cx={50} cy={52} r={8} fill={tpl.colors.bg} opacity={0.9} />
      <circle cx={50} cy={52} r={5} fill={tpl.colors.accent} opacity={0.5} />

      {/* Fins */}
      <path d="M30 80 L18 100 L30 95 Z" fill={tpl.colors.secondary} />
      <path d="M70 80 L82 100 L70 95 Z" fill={tpl.colors.secondary} />
    </svg>
  );
};
