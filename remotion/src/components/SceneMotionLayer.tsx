import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig } from "remotion";
import { MotionPlan } from "../lib/types";
import { HighlightRing } from "./motionlib/HighlightRing";
import { CursorTrail } from "./motionlib/CursorTrail";
import { CursorClickOverlay } from "./motionlib/CursorClick";
import { FloatingBadge } from "./motionlib/FloatingBadge";
import { easeOutCubic } from "../lib/easing";

interface Props {
  motionPlan: MotionPlan;
  children: React.ReactNode;
}

/**
 * Wraps any scene with camera motion (zoom/pan on the content layer) and
 * renders motion overlay elements: HighlightRings, cursor, and FloatingBadges.
 *
 * Camera is applied via CSS transform on an inner container so overlays
 * sit outside the camera transform and remain at their absolute positions.
 */
export const SceneMotionLayer: React.FC<Props> = ({ motionPlan, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames: dur } = useVideoConfig();
  const { camera, cursor, highlights, badges } = motionPlan;

  // ── Camera: interpolate zoom and pan across the full scene duration ──────
  const zoom = interpolate(frame, [0, dur], [camera.zoomFrom, camera.zoomTo], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOutCubic,
  });
  const panX = interpolate(frame, [0, dur], [0, camera.panX], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const panY = interpolate(frame, [0, dur], [0, camera.panY], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const originX = `${camera.focusX * 100}%`;
  const originY = `${camera.focusY * 100}%`;

  return (
    <AbsoluteFill>
      {/* Camera-transformed content */}
      <AbsoluteFill
        style={{
          transform: `scale(${zoom}) translate(${panX}px, ${panY}px)`,
          transformOrigin: `${originX} ${originY}`,
        }}
      >
        {children}
      </AbsoluteFill>

      {/* ── Overlays (outside camera transform → stay in screen space) ── */}

      {/* Highlight rings */}
      {highlights.map((h, i) => (
        <HighlightRing
          key={i}
          x={h.x}
          y={h.y}
          radius={h.radius}
          color={h.color}
          startFrame={h.startFrame}
          exitStartFrame={h.exitFrame}
        />
      ))}

      {/* Cursor trail / click */}
      {cursor.enabled && cursor.waypoints.length > 0 && (
        cursor.clickAtFrame !== null ? (
          <>
            <CursorTrail
              waypoints={cursor.waypoints}
              color={cursor.color}
              showTrail={cursor.showTrail}
              exitStartFrame={cursor.clickAtFrame + 5}
            />
            <CursorClickOverlay
              x={cursor.waypoints[cursor.waypoints.length - 1].x}
              y={cursor.waypoints[cursor.waypoints.length - 1].y}
              color={cursor.color}
              startFrame={cursor.clickAtFrame - 5}
              clickFrame={8}
              exitStartFrame={dur - 10}
            />
          </>
        ) : (
          <CursorTrail
            waypoints={cursor.waypoints}
            color={cursor.color}
            showTrail={cursor.showTrail}
            exitStartFrame={dur - 10}
          />
        )
      )}

      {/* Floating badges */}
      {badges.map((b, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: b.x,
            top: b.y,
            transform: "translate(-50%, -50%)",
          }}
        >
          <FloatingBadge
            text={b.text}
            icon={b.icon ?? undefined}
            accentColor={b.color}
            startFrame={b.startFrame}
            exitStartFrame={b.exitFrame}
          />
        </div>
      ))}
    </AbsoluteFill>
  );
};
