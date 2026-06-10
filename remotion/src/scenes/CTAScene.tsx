import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { CTASceneProps } from "../lib/types";
import { TextReveal } from "../components/TextReveal";
import { GlowBackground } from "../components/GlowBackground";
import { CTAButtonAnimation } from "../components/motionlib/CTAButtonAnimation";
import { useTemplate } from "../lib/templates";

export const CTAScene: React.FC<CTASceneProps> = ({
  headline, badge, ctaLabel, domain, motionPlan,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const tpl = useTemplate();
  const useAnimBtn = motionPlan?.motionComponent === "ctaAnimation";

  const cardOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const cardScale = spring({ fps, frame, config: { stiffness: tpl.spring.stiffness, damping: tpl.spring.damping, mass: tpl.spring.mass }, durationInFrames: 45 });

  const btnScale = spring({ fps, frame: frame - 40, config: { stiffness: tpl.spring.stiffness * 2, damping: tpl.spring.damping }, durationInFrames: 30 });
  const btnOpacity = interpolate(frame, [38, 52], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const sparkleY = interpolate(frame, [0, 90], [0, -8], { extrapolateRight: "clamp" });

  const c = tpl.colors;
  const ct = tpl.cta;
  const b = tpl.badge;

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: tpl.typography.headingFont,
    }}>
      <GlowBackground variant="cta" startFrame={0} />

      <div style={{
        textAlign: "center",
        background: c.surface,
        border: `1px solid ${c.border}`,
        borderRadius: 28,
        padding: "90px 120px",
        backdropFilter: tpl.backdropBlur > 0 ? `blur(${tpl.backdropBlur * 0.3}px)` : undefined,
        boxShadow: "0 40px 120px rgba(0,0,0,0.5)",
        minWidth: 1100,
        opacity: cardOpacity,
        transform: `scale(${cardScale})`,
      }}>
        {/* Sparkles */}
        <div style={{
          fontSize: 22, marginBottom: 20, opacity: 0.6, letterSpacing: 8,
          color: c.accent,
          transform: `translateY(${sparkleY}px)`,
        }}>✦ ✦ ✦</div>

        {/* Badge */}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          fontSize: 13, fontWeight: 700, letterSpacing: 3,
          textTransform: "uppercase", color: b.text,
          background: b.bg,
          border: `1px solid ${b.border}`,
          padding: "8px 18px", borderRadius: b.borderRadius, marginBottom: 32,
        }}>{b.prefix}{badge}</div>

        <h2 style={{
          fontSize: Math.round(110 * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight,
          color: c.text,
          lineHeight: tpl.typography.lineHeight,
          letterSpacing: tpl.typography.letterSpacing,
          margin: "0 auto 0", maxWidth: "16ch",
          textTransform: tpl.typography.textTransform,
        }}>
          <TextReveal text={headline} startFrame={10} wordDelay={6} />
        </h2>

        {/* CTA Button */}
        {useAnimBtn ? (
          <div style={{ marginTop: 52 }}>
            <CTAButtonAnimation
              label={ctaLabel || "Get Started Free"}
              variant={ct.buttonStyle === "outline" ? "outline" : "primary"}
              accentColor={c.accent}
              startFrame={40}
              style={{ fontSize: 32, padding: "22px 70px", borderRadius: ct.buttonRadius }}
            />
          </div>
        ) : (
          <div style={{
            display: "inline-block", marginTop: 52,
            opacity: btnOpacity, transform: `scale(${btnScale})`,
          }}>
            <div style={{
              padding: `22px 70px`,
              borderRadius: ct.buttonRadius,
              background: ct.buttonStyle === "outline" ? "transparent" : ct.buttonBg,
              border: ct.buttonStyle === "outline" ? `2px solid ${c.accent}` : "none",
              fontSize: 32, fontWeight: 700,
              color: ct.buttonStyle === "outline" ? c.accent : ct.buttonText,
              boxShadow: ct.showGlow ? ct.buttonShadow : "none",
              letterSpacing: -0.5,
            }}>
              {ctaLabel || "Get Started Free"}
            </div>
          </div>
        )}

        {/* Domain */}
        {domain && (
          <div style={{
            marginTop: 36, fontSize: 20, fontWeight: 500,
            letterSpacing: 1, color: c.textFaint,
          }}>
            {domain}
          </div>
        )}
      </div>

      <div style={{
        position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2,
        textTransform: "uppercase", color: c.textFaint,
      }}>PROMOLY</div>
    </div>
  );
};
