import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { easeOutCubic } from "../lib/easing";

interface Props {
  text: string;
  startFrame?: number;
  wordDelay?: number;
  style?: React.CSSProperties;
  color?: string;
}

export const TextReveal: React.FC<Props> = ({
  text,
  startFrame = 0,
  wordDelay = 5,
  style = {},
  color = "#ffffff",
}) => {
  const frame = useCurrentFrame();
  const words = text.split(" ");

  return (
    <span style={{ display: "inline", ...style }}>
      {words.map((word, i) => {
        const start = startFrame + i * wordDelay;
        const opacity = interpolate(frame, [start, start + 10], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: easeOutCubic,
        });
        const y = interpolate(frame, [start, start + 14], [18, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: easeOutCubic,
        });
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity,
              transform: `translateY(${y}px)`,
              color,
              marginRight: "0.25em",
            }}
          >
            {word}
          </span>
        );
      })}
    </span>
  );
};
