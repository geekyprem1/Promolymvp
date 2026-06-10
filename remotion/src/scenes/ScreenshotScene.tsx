import React from "react";
import { useCurrentFrame, interpolate, useVideoConfig, Img } from "remotion";
import { AnySceneProps } from "../lib/types";
import { TextReveal } from "../components/TextReveal";
import { easeOutCubic } from "../lib/easing";
import { useTemplate } from "../lib/templates";

/**
 * ScreenshotScene — the WEBSITE SHOWCASE renderer.
 *
 * Renders the real website screenshot full-bleed with an animated lower-third
 * (headline + subheadline + badge). Camera zoom/pan, cursor and highlight rings
 * are applied by SceneMotionLayer from the motion plan — this component only
 * owns the screenshot surface and the text overlay, so it works for ANY scene
 * type (hook, features, cta, …).
 */
export const ScreenshotScene: React.FC<AnySceneProps> = (scene) => {
  const { headline, subheadline, badge, screenshotUrl } = scene;
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const tpl = useTemplate();
  const c = tpl.colors;
  const b = tpl.badge;

  // Lower-third panel slides up + fades in
  const panelY = interpolate(frame, [6, 26], [60, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOutCubic,
  });
  const panelOpacity = interpolate(frame, [6, 24], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Screenshot fades in
  const shotOpacity = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <div style={{ width, height, position: "relative", overflow: "hidden",
      background: c.bg, fontFamily: tpl.typography.headingFont }}>

      {/* Full-bleed website screenshot */}
      {screenshotUrl ? (
        <Img
          src={screenshotUrl}
          style={{
            position: "absolute", inset: 0,
            width: "100%", height: "100%",
            objectFit: "cover", objectPosition: "top center",
            opacity: shotOpacity,
          }}
        />
      ) : (
        <div style={{ position: "absolute", inset: 0, background: c.surface, opacity: shotOpacity }} />
      )}

      {/* Bottom gradient scrim for text legibility */}
      <div style={{
        position: "absolute", left: 0, right: 0, bottom: 0, height: "42%",
        background: `linear-gradient(to top, ${c.bg} 4%, ${c.heroOverlay ?? "rgba(0,0,0,0.55)"} 40%, transparent 100%)`,
        pointerEvents: "none",
      }} />

      {/* Lower-third text overlay */}
      <div style={{
        position: "absolute", left: 90, right: 90, bottom: 80,
        opacity: panelOpacity, transform: `translateY(${panelY}px)`,
      }}>
        {badge && (
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            fontSize: 14, fontWeight: 700, letterSpacing: 3,
            textTransform: "uppercase", color: b.text,
            background: b.bg, border: `1px solid ${b.border}`,
            padding: "7px 16px", borderRadius: b.borderRadius, marginBottom: 20,
          }}>{b.prefix}{badge}</div>
        )}
        <h2 style={{
          fontSize: Math.round(76 * tpl.typography.sizeScale),
          fontWeight: tpl.typography.headingWeight,
          color: c.text, lineHeight: tpl.typography.lineHeight,
          letterSpacing: tpl.typography.letterSpacing,
          margin: 0, maxWidth: "24ch",
          textTransform: tpl.typography.textTransform,
          textShadow: "0 4px 40px rgba(0,0,0,0.6)",
        }}>
          <TextReveal text={headline} startFrame={12} wordDelay={4} />
        </h2>
        {subheadline && (
          <p style={{ fontSize: 26, color: c.textMuted, marginTop: 16, maxWidth: "44ch",
            textShadow: "0 2px 24px rgba(0,0,0,0.6)" }}>
            <TextReveal text={subheadline} startFrame={22} wordDelay={2} color={c.textMuted} />
          </p>
        )}
      </div>

      <div style={{ position: "absolute", bottom: 28, right: 36,
        fontSize: 11, fontWeight: 700, letterSpacing: 2,
        textTransform: "uppercase", color: c.textFaint,
        fontFamily: tpl.typography.bodyFont }}>PROMOLY</div>
    </div>
  );
};
