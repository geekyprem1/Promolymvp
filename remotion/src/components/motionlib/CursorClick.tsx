import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { theme } from "../../lib/theme";
import { easeOutCubic } from "../../lib/easing";

export interface CursorClickProps {
  x: number;
  y: number;
  color?: string;
  clickFrame?: number;
  startFrame?: number;
  exitStartFrame?: number;
}

export const CursorClick: React.FC<CursorClickProps> = ({
  x,
  y,
  color = "#ffffff",
  clickFrame = 20,
  startFrame = 0,
  exitStartFrame = 999,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  const cf = frame - (startFrame + clickFrame);

  // Enter: cursor slides in from slightly above
  const cursorOpacity = interpolate(f, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });
  const cursorOffY = interpolate(f, [0, 16], [-20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic });

  // Click press: scale down then bounce
  const pressScale = cf >= 0
    ? spring({ frame: cf, fps, config: { damping: 8, stiffness: 300, mass: 0.5 } })
    : 1;
  // 1 → 0.85 → 1 bounce
  const clickScale = cf >= 0
    ? interpolate(pressScale, [0, 1], [0.85, 1])
    : 1;

  // Ripple waves on click
  const ripple1Radius = cf >= 0 ? interpolate(cf, [0, 25], [5, 60], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic }) : 0;
  const ripple1Opacity = cf >= 0 ? interpolate(cf, [0, 25], [0.8, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const ripple2Radius = cf >= 0 ? interpolate(cf, [4, 30], [5, 80], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic }) : 0;
  const ripple2Opacity = cf >= 0 ? interpolate(cf, [4, 30], [0.5, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 12], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const isExiting = frame >= exitStartFrame;
  const finalOpacity = isExiting ? exitOpacity : cursorOpacity;

  return (
    <g
      style={{ pointerEvents: "none" }}
      transform={`translate(${x}, ${y + cursorOffY})`}
      opacity={finalOpacity}
    >
      {/* Ripple rings */}
      {cf >= 0 && (
        <>
          <circle r={ripple1Radius} fill="none" stroke={color} strokeWidth={2} opacity={ripple1Opacity} />
          <circle r={ripple2Radius} fill="none" stroke={color} strokeWidth={1.5} opacity={ripple2Opacity} />
        </>
      )}
      {/* Cursor arrow */}
      <g transform={`scale(${clickScale})`}>
        <path
          d="M0,0 L0,28 L7,21 L12,32 L16,30 L11,19 L20,19 Z"
          fill={color}
          stroke="#000"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
      </g>
    </g>
  );
};

// Wrapper for use outside SVG
export const CursorClickOverlay: React.FC<CursorClickProps> = (props) => (
  <svg
    style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "visible" }}
    width="1920"
    height="1080"
  >
    <CursorClick {...props} />
  </svg>
);
