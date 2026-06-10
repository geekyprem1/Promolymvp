import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { useTemplate } from "../lib/templates";

interface Props {
  variant?: "hero" | "split" | "cta";
  startFrame?: number;
}

export const GlowBackground: React.FC<Props> = ({ variant = "split", startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const tpl = useTemplate();

  const opacity = interpolate(frame, [startFrame, startFrame + 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const float = Math.sin(frame / 80) * 20;
  const a = tpl.colors.accent;
  const s = tpl.colors.secondary;
  const bg = tpl.colors.bg;

  // Convert hex to rgba helper (inline for simplicity)
  const toRgba = (hex: string, alpha: number) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  };

  // Only use toRgba for 6-char hex colors; fall back to tpl.colors.accentGlow otherwise
  const accentGlow = a.startsWith("#") && a.length === 7 ? toRgba(a, 0.22) : tpl.colors.accentGlow;
  const secGlow    = s.startsWith("#") && s.length === 7 ? toRgba(s, 0.14) : tpl.colors.accentGlow;

  const backgrounds: Record<string, string> = {
    hero: `
      radial-gradient(ellipse 100% 80% at ${30 + float * 0.1}% ${40 + float * 0.05}%,
        ${accentGlow} 0%, transparent 60%),
      radial-gradient(ellipse 80% 100% at 75% 60%,
        ${secGlow} 0%, transparent 55%),
      ${bg}
    `,
    split: `
      radial-gradient(ellipse 70% 100% at ${20 + float * 0.1}% 50%,
        ${a.startsWith("#") && a.length === 7 ? toRgba(a, 0.10) : tpl.colors.accentGlow} 0%, transparent 60%),
      ${bg}
    `,
    cta: `
      radial-gradient(ellipse 120% 80% at 50% ${20 + float * 0.1}%,
        ${a.startsWith("#") && a.length === 7 ? toRgba(a, 0.20) : tpl.colors.accentGlow} 0%, transparent 55%),
      radial-gradient(ellipse 80% 120% at 80% 90%,
        ${secGlow} 0%, transparent 55%),
      ${bg}
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
