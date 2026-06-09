import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { easeOutCubic } from "../lib/easing";

type Direction = "left" | "right" | "up" | "down";

interface Props {
  children: React.ReactNode;
  startFrame?: number;
  duration?: number;
  direction?: Direction;
  distance?: number;
  style?: React.CSSProperties;
}

export const SlideIn: React.FC<Props> = ({
  children,
  startFrame = 0,
  duration = 20,
  direction = "up",
  distance = 60,
  style = {},
}) => {
  const frame = useCurrentFrame();

  const progress = interpolate(frame, [startFrame, startFrame + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOutCubic,
  });

  const opacity = interpolate(frame, [startFrame, startFrame + duration * 0.6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const offset = (1 - progress) * distance;
  const transforms: Record<Direction, string> = {
    left:  `translateX(${-offset}px)`,
    right: `translateX(${offset}px)`,
    up:    `translateY(${offset}px)`,
    down:  `translateY(${-offset}px)`,
  };

  return (
    <div
      style={{
        opacity,
        transform: transforms[direction],
        ...style,
      }}
    >
      {children}
    </div>
  );
};
