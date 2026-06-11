import React from "react";
import { useCurrentFrame, spring, interpolate, useVideoConfig } from "remotion";
import { useTemplate } from "../../../lib/templates";

interface Props {
  intensity?: number;
  startFrame?: number;
  size?: number;
}

// 3-layer network: 3 input, 4 hidden, 3 output
const LAYERS = [
  [{ x: 12, y: 20 }, { x: 12, y: 50 }, { x: 12, y: 80 }],
  [{ x: 44, y: 12 }, { x: 44, y: 38 }, { x: 44, y: 62 }, { x: 44, y: 88 }],
  [{ x: 76, y: 26 }, { x: 76, y: 50 }, { x: 76, y: 74 }],
  [{ x: 96, y: 50 }],
];

export const NeuralNetwork: React.FC<Props> = ({
  intensity = 0.8,
  startFrame = 0,
  size = 200,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const f = Math.max(0, frame - startFrame);

  const reveal = spring({ frame: f, fps, config: { stiffness: 30, damping: 20 } });

  // Pulse wave travelling left to right
  const wave = (f % 40) / 40;

  const edges: { x1: number; y1: number; x2: number; y2: number; li: number }[] = [];
  LAYERS.forEach((layer, li) => {
    if (li >= LAYERS.length - 1) return;
    layer.forEach((a) => {
      LAYERS[li + 1].forEach((b) => {
        edges.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, li });
      });
    });
  });

  return (
    <svg width={size} height={size * 0.55} viewBox="0 0 108 100" style={{ overflow: "visible" }}>
      {/* Edges */}
      {edges.map((e, i) => {
        const layerReveal = interpolate(reveal, [e.li / LAYERS.length, (e.li + 1) / LAYERS.length], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const pulseProg = ((wave + e.li * 0.25) % 1);
        const px = e.x1 + (e.x2 - e.x1) * pulseProg;
        const py = e.y1 + (e.y2 - e.y1) * pulseProg;
        return (
          <g key={i}>
            <line
              x1={e.x1} y1={e.y1}
              x2={e.x1 + (e.x2 - e.x1) * layerReveal}
              y2={e.y1 + (e.y2 - e.y1) * layerReveal}
              stroke={tpl.colors.accent}
              strokeWidth={0.5}
              opacity={0.25 * intensity}
            />
            {layerReveal > 0.95 && (
              <circle cx={px} cy={py} r={1.5} fill={tpl.colors.accent} opacity={0.7 * intensity} />
            )}
          </g>
        );
      })}

      {/* Nodes */}
      {LAYERS.flat().map((n, i) => {
        const layerIdx = LAYERS.findIndex((l) => l.includes(n));
        const ns = spring({ frame: Math.max(0, f - layerIdx * 8), fps, config: { stiffness: 200, damping: 14 } });
        const pulse = 0.6 + 0.4 * Math.sin(f * 0.15 + i * 0.8);
        return (
          <g key={i} transform={`translate(${n.x},${n.y}) scale(${ns})`}>
            <circle r={5} fill={tpl.colors.accent} opacity={0.15 * pulse} style={{ filter: "blur(3px)" }} />
            <circle r={3} fill={tpl.colors.surface} stroke={tpl.colors.accent} strokeWidth={1} opacity={0.9} />
            <circle r={1.5} fill={tpl.colors.accent} opacity={pulse * intensity} />
          </g>
        );
      })}
    </svg>
  );
};
