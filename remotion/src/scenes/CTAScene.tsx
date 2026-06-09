import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { CTASceneProps } from "../lib/types";
import { TextReveal } from "../components/TextReveal";
import { GlowBackground } from "../components/GlowBackground";
import { easeOutBack } from "../lib/easing";

export const CTAScene: React.FC<CTASceneProps> = ({
  headline, badge, ctaLabel, domain,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();

  const cardOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const cardScale = spring({ fps, frame, config: { stiffness: 80, damping: 16 }, durationInFrames: 45 });

  const btnScale = spring({ fps, frame: frame - 40, config: { stiffness: 200, damping: 14 }, durationInFrames: 30 });
  const btnOpacity = interpolate(frame, [38, 52], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Sparkle float
  const sparkleY = interpolate(frame, [0, 90], [0, -8], { extrapolateRight: "clamp" });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'Inter', sans-serif",
    }}>
      <GlowBackground variant="cta" startFrame={0} />

      <div style={{
        textAlign: "center",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 28,
        padding: "90px 120px",
        backdropFilter: "blur(8px)",
        boxShadow: "0 40px 120px rgba(0,0,0,0.5)",
        minWidth: 1100,
        opacity: cardOpacity,
        transform: `scale(${cardScale})`,
      }}>
        {/* Sparkles */}
        <div style={{
          fontSize: 22, marginBottom: 20, opacity: 0.6, letterSpacing: 8,
          transform: `translateY(${sparkleY}px)`,
        }}>✦ ✦ ✦</div>

        {/* Badge */}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          fontSize: 13, fontWeight: 700, letterSpacing: 3,
          textTransform: "uppercase", color: "#a5b4fc",
          background: "rgba(99,102,241,0.12)",
          border: "1px solid rgba(99,102,241,0.25)",
          padding: "8px 18px", borderRadius: 100, marginBottom: 32,
        }}>✦ {badge}</div>

        <h2 style={{
          fontSize: 110, fontWeight: 800, color: "#fff",
          lineHeight: 1.05, letterSpacing: -3,
          margin: "0 auto 0", maxWidth: "16ch",
        }}>
          <TextReveal text={headline} startFrame={10} wordDelay={6} />
        </h2>

        {/* CTA Button */}
        <div style={{
          display: "inline-block", marginTop: 52,
          opacity: btnOpacity, transform: `scale(${btnScale})`,
        }}>
          <div style={{
            padding: "22px 70px", borderRadius: 100,
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            fontSize: 32, fontWeight: 700, color: "white",
            boxShadow: "0 8px 40px rgba(99,102,241,0.45)",
            letterSpacing: -0.5,
          }}>
            {ctaLabel || "Get Started Free"}
          </div>
        </div>

        {/* Domain */}
        {domain && (
          <div style={{
            marginTop: 36, fontSize: 20, fontWeight: 500,
            letterSpacing: 1, color: "rgba(255,255,255,0.3)",
          }}>
            {domain}
          </div>
        )}
      </div>

      <div style={{
        position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2,
        textTransform: "uppercase", color: "rgba(255,255,255,0.18)",
      }}>PROMOLY</div>
    </div>
  );
};
