import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { easeOutCubic } from "../lib/easing";

interface Props {
  screenshotUrl: string;
  startFrame?: number;
  width?: number | string;
  showChrome?: boolean;
}

export const WebsiteCard: React.FC<Props> = ({
  screenshotUrl,
  startFrame = 0,
  width = "100%",
  showChrome = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    fps,
    frame: frame - startFrame,
    config: { stiffness: 120, damping: 18, mass: 0.8 },
    durationInFrames: 40,
  });

  const opacity = interpolate(frame, [startFrame, startFrame + 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOutCubic,
  });

  const shadowIntensity = interpolate(frame, [startFrame, startFrame + 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width,
        opacity,
        transform: `scale(${scale})`,
        borderRadius: 14,
        overflow: "hidden",
        background: "#12121e",
        boxShadow: `0 0 0 1px rgba(255,255,255,0.08),
                    0 ${30 * shadowIntensity}px ${80 * shadowIntensity}px rgba(0,0,0,0.6)`,
      }}
    >
      {showChrome && (
        <div
          style={{
            height: 36,
            background: "#16162a",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            alignItems: "center",
            padding: "0 14px",
            gap: 7,
          }}
        >
          <div style={{ width: 11, height: 11, borderRadius: "50%", background: "#ff5f57" }} />
          <div style={{ width: 11, height: 11, borderRadius: "50%", background: "#ffbd2e" }} />
          <div style={{ width: 11, height: 11, borderRadius: "50%", background: "#28c840" }} />
        </div>
      )}
      <img
        src={screenshotUrl}
        style={{ width: "100%", display: "block" }}
        alt="Website screenshot"
      />
    </div>
  );
};
