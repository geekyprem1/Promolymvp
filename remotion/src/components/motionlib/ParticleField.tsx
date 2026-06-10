import React from "react";
import { useCurrentFrame, interpolate, useVideoConfig } from "remotion";

interface Particle {
  x: number;
  y: number;
  size: number;
  speed: number;
  phase: number;
  drift: number;
  opacity: number;
}

const PARTICLES: Particle[] = [
  { x: 0.08, y: 0.15, size: 3, speed: 0.7, phase: 0,    drift: 0.12, opacity: 0.6 },
  { x: 0.18, y: 0.72, size: 2, speed: 0.5, phase: 1.2,  drift: 0.08, opacity: 0.4 },
  { x: 0.27, y: 0.38, size: 4, speed: 0.9, phase: 2.4,  drift: 0.15, opacity: 0.5 },
  { x: 0.35, y: 0.88, size: 2, speed: 0.6, phase: 0.8,  drift: 0.10, opacity: 0.35 },
  { x: 0.44, y: 0.22, size: 3, speed: 1.0, phase: 3.1,  drift: 0.14, opacity: 0.55 },
  { x: 0.52, y: 0.61, size: 2, speed: 0.4, phase: 1.7,  drift: 0.09, opacity: 0.3 },
  { x: 0.63, y: 0.44, size: 5, speed: 0.8, phase: 2.0,  drift: 0.18, opacity: 0.45 },
  { x: 0.71, y: 0.10, size: 2, speed: 0.6, phase: 0.4,  drift: 0.07, opacity: 0.4 },
  { x: 0.79, y: 0.78, size: 3, speed: 0.7, phase: 1.5,  drift: 0.11, opacity: 0.5 },
  { x: 0.88, y: 0.33, size: 2, speed: 0.9, phase: 2.8,  drift: 0.13, opacity: 0.35 },
  { x: 0.12, y: 0.55, size: 4, speed: 0.5, phase: 0.6,  drift: 0.16, opacity: 0.4 },
  { x: 0.24, y: 0.92, size: 2, speed: 0.8, phase: 3.5,  drift: 0.08, opacity: 0.3 },
  { x: 0.39, y: 0.05, size: 3, speed: 0.6, phase: 1.1,  drift: 0.12, opacity: 0.55 },
  { x: 0.57, y: 0.83, size: 2, speed: 1.0, phase: 2.3,  drift: 0.09, opacity: 0.35 },
  { x: 0.68, y: 0.28, size: 4, speed: 0.7, phase: 0.2,  drift: 0.17, opacity: 0.5 },
  { x: 0.82, y: 0.65, size: 2, speed: 0.5, phase: 1.9,  drift: 0.10, opacity: 0.4 },
  { x: 0.93, y: 0.50, size: 3, speed: 0.8, phase: 3.0,  drift: 0.14, opacity: 0.45 },
  { x: 0.47, y: 0.97, size: 2, speed: 0.6, phase: 2.6,  drift: 0.08, opacity: 0.3 },
];

export interface ParticleFieldProps {
  color?: string;
  count?: number;
  startFrame?: number;
  intensity?: number;
}

export const ParticleField: React.FC<ParticleFieldProps> = ({
  color = "#ffffff",
  count = 18,
  startFrame = 0,
  intensity = 1,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const f = frame - startFrame;

  const fieldOpacity = interpolate(f, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const visible = PARTICLES.slice(0, count);

  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}>
      {visible.map((p, i) => {
        const t = f / fps;
        const floatY = Math.sin(t * Math.PI * p.speed + p.phase) * 40 * p.drift * intensity;
        const floatX = Math.cos(t * Math.PI * p.speed * 0.7 + p.phase) * 20 * p.drift * intensity;
        const pulse  = 0.6 + Math.sin(t * Math.PI * p.speed * 1.3 + p.phase) * 0.4;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: p.x * width + floatX,
              top:  p.y * height + floatY,
              width:  p.size,
              height: p.size,
              borderRadius: "50%",
              background: color,
              opacity: fieldOpacity * p.opacity * pulse * intensity,
              boxShadow: p.size >= 4 ? `0 0 ${p.size * 4}px ${color}88` : "none",
            }}
          />
        );
      })}
    </div>
  );
};
