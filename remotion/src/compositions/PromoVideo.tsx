import React from "react";
import { AbsoluteFill, Series, useVideoConfig } from "remotion";
import { PromoVideoProps, AnySceneProps } from "../lib/types";
import { HeroScene } from "../scenes/HeroScene";
import { FeaturesScene } from "../scenes/FeaturesScene";
import { BenefitsScene } from "../scenes/BenefitsScene";
import { TestimonialsScene } from "../scenes/TestimonialsScene";
import { CTAScene } from "../scenes/CTAScene";

// Transition overlay between scenes
const SceneTransition: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  return (
    <AbsoluteFill style={{ background: "transparent" }} />
  );
};

function renderScene(scene: AnySceneProps): React.ReactNode {
  switch (scene.type) {
    case "hero":
      return <HeroScene {...scene} />;
    case "features":
      return <FeaturesScene {...scene} />;
    case "benefits":
      return <BenefitsScene {...scene} />;
    case "testimonials":
      return <TestimonialsScene {...scene} />;
    case "cta":
      return <CTAScene {...scene} />;
    case "content":
      // Render as features scene
      return <FeaturesScene
        {...scene}
        type="features"
        bullets={scene.bodyText ? scene.bodyText.split(".").filter(s => s.trim().length > 5).slice(0, 4) : []}
      />;
    default:
      return null;
  }
}

export const PromoVideo: React.FC<PromoVideoProps> = ({ scenes }) => {
  const { fps } = useVideoConfig();

  if (!scenes || scenes.length === 0) {
    return (
      <AbsoluteFill style={{ background: "#070712", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "white", fontSize: 32, fontFamily: "sans-serif" }}>No scenes provided</div>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ background: "#070712", fontFamily: "'Inter', sans-serif" }}>
      <Series>
        {scenes.map((scene, i) => (
          <Series.Sequence
            key={i}
            durationInFrames={scene.durationInFrames}
            name={`Scene ${i + 1}: ${scene.type}`}
          >
            <AbsoluteFill>
              {renderScene(scene)}
            </AbsoluteFill>
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
