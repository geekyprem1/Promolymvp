import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { easeInOutCubic } from "../lib/easing";

interface Waypoint {
  x: number;
  y: number;
  frame: number;
}

interface Props {
  waypoints: Waypoint[];
  startFrame?: number;
  size?: number;
}

export const CursorAnimation: React.FC<Props> = ({
  waypoints,
  startFrame = 0,
  size = 28,
}) => {
  const frame = useCurrentFrame();

  if (waypoints.length === 0 || frame < startFrame) return null;

  // Find current segment
  let x = waypoints[0].x;
  let y = waypoints[0].y;
  let clickOpacity = 0;

  for (let i = 0; i < waypoints.length - 1; i++) {
    const a = waypoints[i];
    const b = waypoints[i + 1];
    if (frame >= a.frame && frame <= b.frame) {
      x = interpolate(frame, [a.frame, b.frame], [a.x, b.x], {
        easing: easeInOutCubic,
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      y = interpolate(frame, [a.frame, b.frame], [a.y, b.y], {
        easing: easeInOutCubic,
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      // click ripple at each waypoint arrival
      if (frame >= b.frame - 5 && frame <= b.frame + 10) {
        clickOpacity = interpolate(
          frame, [b.frame - 5, b.frame, b.frame + 10], [0, 1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
      }
    }
  }

  const lastWp = waypoints[waypoints.length - 1];
  if (frame >= lastWp.frame) {
    x = lastWp.x;
    y = lastWp.y;
  }

  const cursorOpacity = interpolate(frame, [startFrame, startFrame + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        pointerEvents: "none",
        zIndex: 100,
        opacity: cursorOpacity,
      }}
    >
      {/* Click ripple */}
      {clickOpacity > 0 && (
        <div
          style={{
            position: "absolute",
            width: size * 2,
            height: size * 2,
            borderRadius: "50%",
            border: "2px solid rgba(99,102,241,0.6)",
            transform: `translate(-50%, -50%) scale(${1 + clickOpacity * 0.8})`,
            opacity: clickOpacity * 0.5,
          }}
        />
      )}
      {/* Cursor SVG */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        style={{ filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.5))" }}
      >
        <path
          d="M5.5 3.5L18.5 12L12 13.5L9 20L5.5 3.5Z"
          fill="white"
          stroke="#333"
          strokeWidth="1"
        />
      </svg>
    </div>
  );
};
