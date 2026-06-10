import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { easeOutCubic } from "../lib/easing";
import { useTemplate } from "../lib/templates";

interface Props {
  text: string;
  startFrame?: number;
}

export const Badge: React.FC<Props> = ({ text, startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const tpl = useTemplate();
  const b = tpl.badge;

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
    <div style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      fontSize: 13,
      fontWeight: 700,
      letterSpacing: 3,
      textTransform: "uppercase",
      color: b.text,
      background: b.bg,
      border: `1px solid ${b.border}`,
      padding: "8px 18px",
      borderRadius: b.borderRadius,
      marginBottom: 24,
      opacity,
      transform: `translateX(${x}px)`,
    }}>
      {b.prefix && <span style={{ fontSize: 10 }}>{b.prefix.trim()}</span>}
      {text}
    </div>
  );
};
