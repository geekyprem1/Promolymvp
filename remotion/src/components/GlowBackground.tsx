import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { theme } from "../lib/theme";

interface Props {
  variant?: "hero" | "split" | "cta";
  startFrame?: number;
}

export const GlowBackground: React.FC<Props> = ({ variant = "split", startFrame = 0 }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [startFrame, startFrame + 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Slow floating animation
  const float = Math.sin(frame / 80) * 20;

  const backgrounds: Record<string, string> = {
    hero: `
      radial-gradient(ellipse 100% 80% at ${30 + float * 0.1}% ${40 + float * 0.05}%,
        rgba(99,102,241,0.22) 0%, transparent 60%),
      radial-gradient(ellipse 80% 100% at 75% 60%,
        rgba(139,92,246,0.14) 0%, transparent 55%),
      ${theme.bg}
    `,
    split: `
      radial-gradient(ellipse 70% 100% at ${20 + float * 0.1}% 50%,
        rgba(99,102,241,0.10) 0%, transparent 60%),
      ${theme.bg}
    `,
    cta: `
      radial-gradient(ellipse 120% 80% at 50% ${20 + float * 0.1}%,
        rgba(99,102,241,0.20) 0%, transparent 55%),
      radial-gradient(ellipse 80% 120% at 80% 90%,
        rgba(139,92,246,0.15) 0%, transparent 55%),
      #050510
    `,
  };

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: backgrounds[variant],
        opacity,
      }}
    />
  );
};
