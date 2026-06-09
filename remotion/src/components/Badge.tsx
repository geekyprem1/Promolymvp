import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { easeOutCubic } from "../lib/easing";
import { theme } from "../lib/theme";

interface Props {
  text: string;
  startFrame?: number;
}

export const Badge: React.FC<Props> = ({ text, startFrame = 0 }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [startFrame, startFrame + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOutCubic,
  });
  const x = interpolate(frame, [startFrame, startFrame + 16], [-20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOutCubic,
  });

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: 13,
        fontWeight: 700,
        letterSpacing: 3,
        textTransform: "uppercase",
        color: "#a5b4fc",
        background: "rgba(99,102,241,0.12)",
        border: "1px solid rgba(99,102,241,0.25)",
        padding: "8px 18px",
        borderRadius: 100,
        marginBottom: 24,
        opacity,
        transform: `translateX(${x}px)`,
      }}
    >
      <span style={{ fontSize: 10 }}>✦</span>
      {text}
    </div>
  );
};
