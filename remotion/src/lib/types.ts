export type TransitionType = "fade" | "slideLeft" | "slideRight" | "zoomIn" | "dissolve";
export type MotionComponent = "textReveal" | "metricCounter" | "ctaAnimation" | "successPulse" | "zoomHighlight" | "cursorClick" | "none";

// ── Motion Planner types ──────────────────────────────────────────────────────

export interface CameraMotion {
  zoomFrom: number;
  zoomTo: number;
  panX: number;
  panY: number;
  focusX: number; // transform-origin X 0-1
  focusY: number; // transform-origin Y 0-1
}

export interface CursorWaypoint {
  x: number;
  y: number;
  frame: number;
}

export interface CursorMotion {
  enabled: boolean;
  waypoints: CursorWaypoint[];
  clickAtFrame: number | null;
  showTrail: boolean;
  color: string;
}

export interface HighlightTarget {
  x: number;
  y: number;
  radius: number;
  startFrame: number;
  exitFrame: number;
  color: string;
}

export interface BadgePlacement {
  text: string;
  icon: string | null;
  x: number;
  y: number;
  startFrame: number;
  exitFrame: number;
  color: string;
}

export interface TransitionMotion {
  in: TransitionType;
  out: TransitionType;
  easing: string;
}

export interface MotionPlan {
  sceneId: string;
  camera: CameraMotion;
  cursor: CursorMotion;
  highlights: HighlightTarget[];
  badges: BadgePlacement[];
  transitions: TransitionMotion;
  motionComponent: MotionComponent;
}

// ── Video Style System ──────────────────────────────────────────────────────
export type VideoStyle = "hybrid" | "website-showcase" | "motion-graphics";
export type ComponentRole = "screenshot" | "motion";
export type MotionIntent = "zoom" | "highlight" | "cursor" | "animate";

export interface HighlightBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BaseSceneProps {
  from: number;
  durationInFrames: number;
  headline: string;
  subheadline: string;
  badge: string;
  screenshotUrl: string;
  transition: TransitionType;
  narration?: string;
  motionPlan?: MotionPlan;

  // ── Video Style System (set by style_engine.py) ──
  videoStyle?: VideoStyle;
  componentType?: string;       // Remotion renderer key ("ScreenshotScene" / motion name)
  componentRole?: ComponentRole;
  motionIntent?: MotionIntent;

  // ── Visual Mapper (set by visual_mapper.py) ──
  visualTargetId?: string | null;
  focusX?: number;
  focusY?: number;
  highlightBox?: HighlightBox | null;
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

// ── Story-arc scene types ─────────────────────────────────────────────────────

export interface HookSceneProps extends BaseSceneProps {
  type: "hook";
  stat?: string;
  statLabel?: string;
}

export interface ProblemSceneProps extends BaseSceneProps {
  type: "problem";
  painPoints: string[];
}

export interface SolutionSceneProps extends BaseSceneProps {
  type: "solution";
  checkpoints: string[];
}

export type AnySceneProps =
  | HeroSceneProps
  | FeaturesSceneProps
  | BenefitsSceneProps
  | TestimonialsSceneProps
  | CTASceneProps
  | ContentSceneProps
  | HookSceneProps
  | ProblemSceneProps
  | SolutionSceneProps;

export interface PromoVideoProps {
  scenes: AnySceneProps[];
  websiteType: string;
  videoStyle: string;
  templateId?: string;
  templateSpring?: { stiffness: number; damping: number; mass: number };
}
