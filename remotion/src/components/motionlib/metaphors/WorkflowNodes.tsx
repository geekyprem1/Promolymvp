import React from "react";
import { useCurrentFrame, spring, interpolate, useVideoConfig } from "remotion";
import { useTemplate } from "../../../lib/templates";

interface Props {
  intensity?: number;
  startFrame?: number;
  size?: number;
}

const NODES = [
  { x: 20, y: 30, label: "Input" },
  { x: 50, y: 18, label: "AI" },
  { x: 80, y: 30, label: "Route" },
  { x: 35, y: 60, label: "Action" },
  { x: 65, y: 60, label: "Output" },
];

const EDGES = [
  [0, 1], [1, 2], [0, 3], [2, 4], [3, 4], [1, 3],
];

export const WorkflowNodes: React.FC<Props> = ({
  intensity = 0.75,
  startFrame = 0,
  size = 200,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tpl = useTemplate();
  const f = Math.max(0, frame - startFrame);

  const nodeScales = NODES.map((_, i) => {
    return spring({ frame: Math.max(0, f - i * 6), fps, config: { stiffness: 180, damping: 16 } });
  });

  // Animated pulse dot along each edge
  const pulseProg = (f % 45) / 45;

  return (
    <svg width={size} height={size * 0.8} viewBox="0 0 100 80" style={{ overflow: "visible" }}>
      {/* Edges */}
      {EDGES.map(([a, b], i) => {
        const na = NODES[a], nb = NODES[b];
        const edgeDraw = spring({ frame: Math.max(0, f - i * 4), fps, config: { stiffness: 40, damping: 20 } });
        const mx = na.x + (nb.x - na.x) * edgeDraw;
        const my = na.y + (nb.y - na.y) * edgeDraw;
        return (
          <g key={i}>
            <line
              x1={na.x} y1={na.y}
              x2={mx} y2={my}
              stroke={tpl.colors.accent}
              strokeWidth={1}
              opacity={0.4}
            />
            {/* Pulse dot */}
            {edgeDraw > 0.9 && (
              <circle
                cx={na.x + (nb.x - na.x) * ((pulseProg + i * 0.17) % 1)}
                cy={na.y + (nb.y - na.y) * ((pulseProg + i * 0.17) % 1)}
                r={2.5}
                fill={tpl.colors.accent}
                opacity={0.8 * intensity}
              />
            )}
          </g>
        );
      })}

      {/* Nodes */}
      {NODES.map((n, i) => (
        <g key={i} transform={`translate(${n.x},${n.y}) scale(${nodeScales[i]})`}>
          <circle r={7} fill={tpl.colors.surface} stroke={tpl.colors.accent} strokeWidth={1.5} opacity={0.9} />
          <circle r={3.5} fill={tpl.colors.accent} opacity={0.7} />
        </g>
      ))}
    </svg>
  );
};
