import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { TestimonialsSceneProps } from "../lib/types";
import { TextReveal } from "../components/TextReveal";
import { GlowBackground } from "../components/GlowBackground";
import { WebsiteCard } from "../components/WebsiteCard";
import { SlideIn } from "../components/SlideIn";
import { easeOutCubic } from "../lib/easing";
import { useTemplate } from "../lib/templates";

export const TestimonialsScene: React.FC<TestimonialsSceneProps> = ({
  headline, subheadline, badge, screenshotUrl, quote, author, company,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const tpl = useTemplate();

  const quoteText  = quote || subheadline || headline;
  const authorText = author || "Happy Customer";
  const companyText = company || "";

  const quoteMarkOpacity = interpolate(frame, [0, 20], [0, 0.2], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const cardScale = spring({ fps, frame, config: { stiffness: tpl.spring.stiffness, damping: tpl.spring.damping, mass: tpl.spring.mass }, durationInFrames: 40 });
  const authorY = interpolate(frame, [40, 55], [20, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });
  const authorOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const c = tpl.colors;
  const b = tpl.badge;

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      display: "flex", fontFamily: tpl.typography.headingFont,
    }}>
      <GlowBackground variant="split" startFrame={0} />

      {/* Text left */}
      <div style={{
        position: "relative", zIndex: 1, width: "48%",
        display: "flex", flexDirection: "column", justifyContent: "center",
        padding: "90px 60px 90px 100px",
      }}>
        <SlideIn startFrame={5} direction="left" distance={50}>
          {/* Badge */}
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            fontSize: 13, fontWeight: 700, letterSpacing: 3,
            textTransform: "uppercase", color: b.text,
            background: b.bg,
            border: `1px solid ${b.border}`,
            padding: "8px 18px", borderRadius: b.borderRadius, marginBottom: 24,
          }}>{b.prefix}{badge}</div>

          {/* Big quote mark */}
          <div style={{
            fontSize: 160, lineHeight: 0.8, color: c.accent,
            opacity: quoteMarkOpacity, marginBottom: 10,
          }}>"</div>

          <p style={{
            fontSize: 30, fontWeight: 500, color: c.text,
            lineHeight: 1.55, margin: 0, maxWidth: "28ch",
          }}>
            <TextReveal text={quoteText} startFrame={12} wordDelay={4} color={c.text} />
          </p>

          <div style={{
            marginTop: 32, opacity: authorOpacity,
            transform: `translateY(${authorY}px)`,
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: c.text }}>{authorText}</div>
            {companyText && (
              <div style={{ fontSize: 15, color: c.textMuted, marginTop: 4 }}>{companyText}</div>
            )}
          </div>
        </SlideIn>
      </div>

      {/* Card right */}
      <div style={{
        position: "relative", zIndex: 1, width: "52%",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "60px 80px 60px 20px",
      }}>
        <div style={{ width: "100%", transform: `scale(${cardScale})` }}>
          <WebsiteCard screenshotUrl={screenshotUrl} startFrame={8} />
        </div>
      </div>

      <div style={{
        position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2,
        textTransform: "uppercase", color: c.textFaint,
      }}>PROMOLY</div>
    </div>
  );
};
