import React from "react";
import { useCurrentFrame, interpolate, useVideoConfig } from "remotion";
import { theme } from "../../lib/theme";
import { easeInOutCubic } from "../../lib/easing";

export interface Waypoint {
  x: number;
  y: number;
  /** frame at which cursor should be at this waypoint */
  frame: number;
}

export interface CursorTrailProps {
  waypoints: Waypoint[];
  color?: string;
  trailLength?: number;
  showTrail?: boolean;
  startFrame?: number;
  exitStartFrame?: number;
}

function lerpWaypoints(waypoints: Waypoint[], frame: number): { x: number; y: number } {
  if (waypoints.length === 0) return { x: 0, y: 0 };
  if (frame <= waypoints[0].frame) return { x: waypoints[0].x, y: waypoints[0].y };
  if (frame >= waypoints[waypoints.length - 1].frame)
    return { x: waypoints[waypoints.length - 1].x, y: waypoints[waypoints.length - 1].y };

  for (let i = 0; i < waypoints.length - 1; i++) {
    const a = waypoints[i];
    const b = waypoints[i + 1];
    if (frame >= a.frame && frame <= b.frame) {
      const t = interpolate(frame, [a.frame, b.frame], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: easeInOutCubic,
      });
      return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
    }
  }
  return { x: waypoints[waypoints.length - 1].x, y: waypoints[waypoints.length - 1].y };
}

export const CursorTrail: React.FC<CursorTrailProps> = ({
  waypoints,
  color = "#ffffff",
  trailLength = 12,
  showTrail = true,
  startFrame = 0,
  exitStartFrame = 999,
}) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame - startFrame, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exitOpacity = interpolate(frame - exitStartFrame, [0, 12], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const finalOpacity = frame >= exitStartFrame ? exitOpacity : opacity;

  const pos = lerpWaypoints(waypoints, frame);

  // Build trail dots from past frames
  const trailDots = showTrail
    ? Array.from({ length: trailLength }, (_, i) => {
        const pastFrame = frame - (i + 1) * 1.5;
        return lerpWaypoints(waypoints, pastFrame);
      })
    : [];

  return (
    <svg
      style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "visible" }}
      width="1920"
      height="1080"
      opacity={finalOpacity}
    >
      {/* Trail dots */}
      {trailDots.map((dot, i) => (
        <circle
          key={i}
          cx={dot.x}
          cy={dot.y}
          r={5 - i * (4 / trailLength)}
          fill={color}
          opacity={(1 - i / trailLength) * 0.4}
        />
      ))}
      {/* Cursor */}
      <g transform={`translate(${pos.x}, ${pos.y})`}>
        <path
          d="M0,0 L0,28 L7,21 L12,32 L16,30 L11,19 L20,19 Z"
          fill={color}
          stroke="#00000088"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
        {/* Glow ring */}
        <circle r={16} fill="none" stroke={color} strokeWidth={1} opacity={0.2} />
      </g>
    </svg>
  );
};
