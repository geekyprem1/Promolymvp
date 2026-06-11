import React from "react";
import { useCurrentFrame, spring, interpolate, useVideoConfig } from "remotion";
import { useTemplate } from "../../../lib/templates";

interface Props {
  intensity?: number;
  startFrame?: number;
  stars?: number;
  size?: number;
}

export const StarBurst: React.FC<Props> = ({
  intensity = 0.8,
  startFrame = 0,
  stars = 5,
  size = 200,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const f = Math.max(0, frame - startFrame);

  const starScales = Array.from({ length: stars }, (_, i) =>
    spring({ frame: Math.max(0, f - i * 5), fps, config: { stiffness: 280, damping: 14 } })
  );

  // Burst particles for the last star (most dramatic)
  const burstProg = spring({ frame: Math.max(0, f - (stars - 1) * 5 - 4), fps, config: { stiffness: 100, damping: 18 } });
  const particles = Array.from({ length: 8 }, (_, i) => {
    const angle = (i / 8) * Math.PI * 2;
    const dist = burstProg * 22 * intensity;
    return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist, a: 1 - burstProg * 0.8 };
  });

  const starW = size / (stars + 0.5);
  const gap = starW * 0.1;
  const totalW = stars * starW + (stars - 1) * gap;
  const startX = (size - totalW) / 2;

  const starPath = (cx: number, cy: number, r: number) => {
    const pts = [];
    for (let i = 0; i < 10; i++) {
      const angle = (i * Math.PI) / 5 - Math.PI / 2;
      const radius = i % 2 === 0 ? r : r * 0.42;
      pts.push(`${cx + Math.cos(angle) * radius},${cy + Math.sin(angle) * radius}`);
    }
    return "M" + pts.join("L") + "Z";
  };

  const cy = size * 0.45;
  const r = starW * 0.42;

  return (
    <svg width={size} height={size * 0.6} viewBox={`0 0 ${size} ${size * 0.6}`} style={{ overflow: "visible" }}>
      {/* Burst particles from last star */}
      {particles.map((p, i) => {
        const lastCX = startX + (stars - 1) * (starW + gap) + starW / 2;
        return (
          <circle
            key={i}
            cx={lastCX + p.x}
            cy={cy + p.y}
            r={2}
            fill={tpl.colors.accent}
            opacity={p.a * intensity}
          />
        );
      })}

      {/* Stars */}
      {Array.from({ length: stars }, (_, i) => {
        const cx = startX + i * (starW + gap) + starW / 2;
        const sc = starScales[i];
        return (
          <g key={i} transform={`translate(${cx},${cy}) scale(${sc}) translate(${-cx},${-cy})`}>
            {/* Glow */}
            <path d={starPath(cx, cy, r * 1.3)} fill={tpl.colors.accent} opacity={0.25} style={{ filter: "blur(4px)" }} />
            {/* Star */}
            <path d={starPath(cx, cy, r)} fill={tpl.colors.accent} />
          </g>
        );
      })}
    </svg>
  );
};
