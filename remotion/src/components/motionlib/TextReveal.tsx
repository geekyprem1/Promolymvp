import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { easeOutCubic } from "../../lib/easing";

export type RevealMode = "words" | "chars" | "lines" | "mask";

export interface TextRevealProps {
  text: string;
  mode?: RevealMode;
  startFrame?: number;
  exitStartFrame?: number;
  stagger?: number;
  style?: React.CSSProperties;
  color?: string;
  maskColor?: string;
}

export const TextReveal: React.FC<TextRevealProps> = ({
  text,
  mode = "words",
  startFrame = 0,
  exitStartFrame = 999,
  stagger = 5,
  style = {},
  color = "#ffffff",
  maskColor = "#6366f1",
}) => {
  const frame = useCurrentFrame();
  const f = frame - startFrame;

  // Exit
  const exitF = frame - exitStartFrame;
  const exitOpacity = interpolate(exitF, [0, 15], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const isExiting = frame >= exitStartFrame;

  if (mode === "mask") {
    // Sliding mask reveal
    const revealWidth = interpolate(f, [0, 30], [0, 100], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easeOutCubic,
    });
    return (
      <div style={{ position: "relative", display: "inline-block", overflow: "hidden", opacity: isExiting ? exitOpacity : 1, ...style }}>
        <span style={{ color, opacity: 0.15 }}>{text}</span>
        <div
          style={{
            position: "absolute",
            inset: 0,
            overflow: "hidden",
            width: `${revealWidth}%`,
          }}
        >
          <span style={{ color, whiteSpace: "nowrap" }}>{text}</span>
        </div>
      </div>
    );
  }

  if (mode === "chars") {
    const chars = text.split("");
    return (
      <span style={{ display: "inline", opacity: isExiting ? exitOpacity : 1, ...style }}>
        {chars.map((char, i) => {
          const start = startFrame + i * (stagger * 0.7);
          const opacity = interpolate(frame, [start, start + 10], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: easeOutCubic,
          });
          const y = interpolate(frame, [start, start + 12], [20, 0], {
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
                whiteSpace: char === " " ? "pre" : undefined,
              }}
            >
              {char === " " ? " " : char}
            </span>
          );
        })}
      </span>
    );
  }

  if (mode === "lines") {
    const lines = text.split("\n");
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.25em", opacity: isExiting ? exitOpacity : 1, ...style }}>
        {lines.map((line, i) => {
          const start = startFrame + i * (stagger * 3);
          const opacity = interpolate(frame, [start, start + 16], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: easeOutCubic,
          });
          const x = interpolate(frame, [start, start + 20], [-30, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: easeOutCubic,
          });
          return (
            <div key={i} style={{ opacity, transform: `translateX(${x}px)`, color, overflow: "hidden" }}>
              {line}
            </div>
          );
        })}
      </div>
    );
  }

  // Default: words
  const words = text.split(" ");
  return (
    <span style={{ display: "inline", opacity: isExiting ? exitOpacity : 1, ...style }}>
      {words.map((word, i) => {
        const start = startFrame + i * stagger;
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
