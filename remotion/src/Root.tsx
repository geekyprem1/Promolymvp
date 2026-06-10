import React from "react";
import { Composition } from "remotion";
import { PromoVideo } from "./compositions/PromoVideo";
import { ComponentDemo } from "./compositions/ComponentDemo";
import { PromoVideoProps } from "./lib/types";

const defaultProps: PromoVideoProps = {
  websiteType: "saas",
  videoStyle: "explainer",
  scenes: [
    {
      type: "hero",
      from: 0,
      durationInFrames: 150,
      headline: "Build Something Great",
      subheadline: "The platform teams love",
      badge: "INTRO",
      screenshotUrl: "https://picsum.photos/1920/1080?random=1",
      transition: "fade",
    },
    {
      type: "features",
      from: 150,
      durationInFrames: 150,
      headline: "Powerful Features",
      subheadline: "Everything you need",
      badge: "FEATURES",
      screenshotUrl: "https://picsum.photos/1920/1080?random=2",
      bullets: ["Fast API", "Realtime sync", "One-click deploy", "Global CDN"],
      reverse: false,
      bodyText: "",
      transition: "slideLeft",
    },
    {
      type: "cta",
      from: 300,
      durationInFrames: 120,
      headline: "Start Free Today",
      subheadline: "",
      badge: "GET STARTED",
      screenshotUrl: "",
      ctaLabel: "Get Started Free",
      domain: "example.com",
      transition: "zoomIn",
    },
  ],
};

export const RemotionRoot: React.FC = () => {
  const totalFrames = defaultProps.scenes.reduce(
    (sum: number, s: { durationInFrames: number }) => sum + s.durationInFrames,
    0
  );

  return (
    <>
    <Composition
      id="PromoVideo"
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      component={PromoVideo as any}
      durationInFrames={totalFrames}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={defaultProps}
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      calculateMetadata={({ props }: any) => {
        const p = props as PromoVideoProps;
        const total = p.scenes.reduce(
          (sum: number, s: { durationInFrames: number }) => sum + s.durationInFrames,
          0
        );
        return { durationInFrames: Math.max(total, 1) };
      }}
    />
    <Composition
      id="ComponentDemo"
      component={ComponentDemo}
      durationInFrames={900}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{}}
    />
    </>
  );
};
