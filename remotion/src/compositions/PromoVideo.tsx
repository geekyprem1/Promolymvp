import React from "react";
import { AbsoluteFill, Series, useVideoConfig } from "remotion";
import { PromoVideoProps, AnySceneProps, MotionPlan } from "../lib/types";
import { HeroScene } from "../scenes/HeroScene";
import { HookScene } from "../scenes/HookScene";
import { ProblemScene } from "../scenes/ProblemScene";
import { SolutionScene } from "../scenes/SolutionScene";
import { FeaturesScene } from "../scenes/FeaturesScene";
import { BenefitsScene } from "../scenes/BenefitsScene";
import { TestimonialsScene } from "../scenes/TestimonialsScene";
import { CTAScene } from "../scenes/CTAScene";
import { ScreenshotScene } from "../scenes/ScreenshotScene";
import { MotionGraphicsScene } from "../scenes/MotionGraphicsScene";
import { SceneMotionLayer } from "../components/SceneMotionLayer";
import { TemplateContext, getTemplate } from "../lib/templates";

// Default no-op motion plan used when backend hasn't supplied one
const DEFAULT_MOTION_PLAN: MotionPlan = {
  sceneId: "default",
  camera: { zoomFrom: 1.0, zoomTo: 1.0, panX: 0, panY: 0, focusX: 0.5, focusY: 0.5 },
  cursor: { enabled: false, waypoints: [], clickAtFrame: null, showTrail: false, color: "#ffffff" },
  highlights: [],
  badges: [],
  transitions: { in: "fade", out: "fade", easing: "easeOutCubic" },
  motionComponent: "none",
};

function renderSceneContent(scene: AnySceneProps): React.ReactNode {
  // ── Video Style System dispatch ──
  // The style engine sets componentType per scene:
  //   "ScreenshotScene"  → website showcase renderer
  //   anything else (motion component name / "MotionGraphicsScene") → motion graphics
  // When componentType is absent (legacy props), fall back to type-based dispatch.
  if (scene.componentType) {
    if (scene.componentType === "ScreenshotScene") {
      return <ScreenshotScene {...scene} />;
    }
    return <MotionGraphicsScene {...scene} />;
  }

  switch (scene.type) {
    // Story-arc scenes
    case "hook":
      return <HookScene {...scene} />;
    case "problem":
      return <ProblemScene {...scene} />;
    case "solution":
      return <SolutionScene {...scene} />;
    // Existing scenes
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
      return (
        <FeaturesScene
          {...scene}
          type="features"
          bullets={
            scene.bodyText
              ? scene.bodyText.split(".").filter((s) => s.trim().length > 5).slice(0, 4)
              : []
          }
        />
      );
    default:
      return null;
  }
}

export const PromoVideo: React.FC<PromoVideoProps> = ({ scenes, templateId }) => {
  const template = getTemplate(templateId);

  if (!scenes || scenes.length === 0) {
    return (
      <AbsoluteFill
        style={{
          background: template.colors.bg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ color: template.colors.text, fontSize: 32, fontFamily: template.typography.headingFont }}>
          No scenes provided
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <TemplateContext.Provider value={template}>
      <AbsoluteFill style={{ background: template.colors.bg, fontFamily: template.typography.headingFont }}>
        <Series>
          {scenes.map((scene, i) => {
            const motionPlan = scene.motionPlan ?? DEFAULT_MOTION_PLAN;
            return (
              <Series.Sequence
                key={i}
                durationInFrames={scene.durationInFrames}
                name={`Scene ${i + 1}: ${scene.type}`}
              >
                <SceneMotionLayer motionPlan={motionPlan}>
                  {renderSceneContent(scene)}
                </SceneMotionLayer>
              </Series.Sequence>
            );
          })}
        </Series>
      </AbsoluteFill>
    </TemplateContext.Provider>
  );
};
