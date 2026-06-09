export type TransitionType = "fade" | "slideLeft" | "slideRight" | "zoomIn" | "dissolve";

export interface BaseSceneProps {
  from: number;
  durationInFrames: number;
  headline: string;
  subheadline: string;
  badge: string;
  screenshotUrl: string;
  transition: TransitionType;
}

export interface HeroSceneProps extends BaseSceneProps {
  type: "hero";
}

export interface FeaturesSceneProps extends BaseSceneProps {
  type: "features";
  bullets: string[];
  reverse: boolean;
  bodyText: string;
}

export interface BenefitsSceneProps extends BaseSceneProps {
  type: "benefits";
  reverse: boolean;
  bodyText: string;
}

export interface TestimonialsSceneProps extends BaseSceneProps {
  type: "testimonials";
  quote: string;
  author: string;
  company: string;
}

export interface CTASceneProps extends BaseSceneProps {
  type: "cta";
  ctaLabel: string;
  domain: string;
}

export interface ContentSceneProps extends BaseSceneProps {
  type: "content";
  reverse: boolean;
  bodyText: string;
}

export type AnySceneProps =
  | HeroSceneProps
  | FeaturesSceneProps
  | BenefitsSceneProps
  | TestimonialsSceneProps
  | CTASceneProps
  | ContentSceneProps;

export interface PromoVideoProps {
  scenes: AnySceneProps[];
  websiteType: string;
  videoStyle: string;
}
