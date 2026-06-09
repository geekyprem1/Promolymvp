import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

interface Props {
  children: React.ReactNode;
  startFrame?: number;
  color?: string;
}

export const HighlightBox: React.FC<Props> = ({
  children,
  startFrame = 0,
  color = "#6366f1",
}) => {
  const frame = useCurrentFrame();

  const visible = frame >= startFrame;
  const pulse = frame % 50;
  const glowOpacity = visible
    ? interpolate(pulse, [0, 25, 50], [0.4, 0.9, 0.4], { extrapolateRight: "clamp" })
    : 0;

  const borderOpacity = visible
    ? interpolate(frame, [startFrame, startFrame + 15], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  return (
    <div
      style={{
        position: "relative",
        borderRadius: 8,
        padding: "6px 10px",
        border: `2px solid rgba(99,102,241,${borderOpacity})`,
        boxShadow: `0 0 20px rgba(99,102,241,${glowOpacity * 0.5})`,
        transition: "none",
      }}
    >
      {children}
    </div>
  );
};
