import React from "react";
import { useCurrentFrame, interpolate, useVideoConfig } from "remotion";
import { FeaturesSceneProps } from "../lib/types";
import { TextReveal } from "../components/TextReveal";
import { Badge } from "../components/Badge";
import { WebsiteCard } from "../components/WebsiteCard";
import { SlideIn } from "../components/SlideIn";
import { GlowBackground } from "../components/GlowBackground";
import { HighlightBox } from "../components/HighlightBox";
import { MetricCounter } from "../components/motionlib/MetricCounter";
import { easeOutCubic } from "../lib/easing";
import { useTemplate } from "../lib/templates";

const METRIC_RE = /(\d[\d,\.]*)\s*(%|x|\+|k|K|M|B)?/;

export const FeaturesScene: React.FC<FeaturesSceneProps> = ({
  headline,
  subheadline,
  badge,
  screenshotUrl,
  bullets,
  reverse,
  bodyText,
  motionPlan,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();
  const safeB = bullets?.length ? bullets : (bodyText ? [bodyText] : ["Powerful and fast", "Easy to integrate", "Scales with you"]);

  const textDir = reverse ? "right" : "left";
  const cardDir = reverse ? "left"  : "right";
  const c = tpl.colors;

  // MetricCounter: extract the first metric from bullets if motionComponent says so
  const showMetric = motionPlan?.motionComponent === "metricCounter";
  const metricBullet = showMetric ? safeB.find(b => METRIC_RE.test(b)) : null;
  const metricMatch  = metricBullet ? METRIC_RE.exec(metricBullet) : null;
  const metricValue  = metricMatch ? parseFloat(metricMatch[1].replace(/,/g, "")) : 0;
  const metricSuffix = metricMatch?.[2] ?? "";
  const metricLabel  = metricBullet ? metricBullet.replace(METRIC_RE, "").trim().slice(0, 30) : "";

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      display: "flex", flexDirection: reverse ? "row-reverse" : "row",
      fontFamily: tpl.typography.headingFont,
    }}>
      <GlowBackground variant="split" startFrame={0} />

      {/* Text column */}
      <div style={{
        position: "relative", zIndex: 1,
        width: "44%", display: "flex", flexDirection: "column",
        justifyContent: "center",
        padding: reverse ? "90px 80px 90px 60px" : "90px 60px 90px 100px",
      }}>
        <SlideIn startFrame={5} direction={textDir} distance={50}>
          <Badge text={badge} startFrame={5} />
          <h2 style={{
            fontSize: Math.round(72 * tpl.typography.sizeScale),
            fontWeight: tpl.typography.headingWeight,
            color: c.text,
            lineHeight: tpl.typography.lineHeight,
            letterSpacing: tpl.typography.letterSpacing,
            margin: 0, maxWidth: "14ch",
            textTransform: tpl.typography.textTransform,
          }}>
            <TextReveal text={headline} startFrame={10} wordDelay={5} />
          </h2>
          {subheadline && (
            <p style={{ fontSize: 24, color: c.textMuted, marginTop: 16, maxWidth: "38ch" }}>
              <TextReveal text={subheadline} startFrame={20} wordDelay={3} color={c.textMuted} />
            </p>
          )}
        </SlideIn>

        {/* Bullets */}
        <ul style={{ listStyle: "none", padding: 0, margin: "28px 0 0", display: "flex", flexDirection: "column", gap: 16 }}>
          {safeB.slice(0, 4).map((b, i) => {
            const bulletStart = 25 + i * 12;
            const bulletOpacity = interpolate(frame, [bulletStart, bulletStart + 12], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
            });
            const bulletX = interpolate(frame, [bulletStart, bulletStart + 14], [-30, 0], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
            });
            const isHighlight = i === 0 && frame > 60;
            const content = (
              <li style={{
                display: "flex", alignItems: "flex-start", gap: 14,
                fontSize: 22, color: c.textMuted, lineHeight: 1.4,
                opacity: bulletOpacity,
                transform: `translateX(${bulletX}px)`,
              }}>
                <span style={{ color: c.accent, fontWeight: 800, fontSize: 18, marginTop: 2, flexShrink: 0 }}>✓</span>
                {b.slice(0, 70)}
              </li>
            );
            return isHighlight ? <HighlightBox key={i} startFrame={60}>{content}</HighlightBox> : <div key={i}>{content}</div>;
          })}
        </ul>
      </div>

      {/* Card column */}
      <div style={{
        position: "relative", zIndex: 1,
        width: "56%", display: "flex",
        alignItems: "center", justifyContent: "center",
        padding: reverse ? "60px 60px 60px 20px" : "60px 80px 60px 20px",
      }}>
        <div style={{
          position: "absolute", width: 500, height: 500, borderRadius: "50%",
          background: `radial-gradient(circle, ${c.accentGlow} 0%, transparent 70%)`,
          filter: "blur(40px)", pointerEvents: "none",
        }} />
        <SlideIn startFrame={8} direction={cardDir} distance={70} style={{ width: "100%" }}>
          <WebsiteCard screenshotUrl={screenshotUrl} startFrame={8} />
        </SlideIn>
        {/* MetricCounter overlay — appears over card when a metric is detected */}
        {showMetric && metricValue > 0 && (
          <div style={{
            position: "absolute", bottom: 100, left: "50%",
            transform: "translateX(-50%)",
            zIndex: 10,
          }}>
            <MetricCounter
              from={0}
              to={metricValue}
              suffix={metricSuffix}
              label={metricLabel}
              accentColor={c.accent}
              startFrame={30}
              exitStartFrame={999}
            />
          </div>
        )}
      </div>

      <div style={{ position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2,
        textTransform: "uppercase", color: c.textFaint,
        fontFamily: tpl.typography.bodyFont,
      }}>PROMOLY</div>
    </div>
  );
};
