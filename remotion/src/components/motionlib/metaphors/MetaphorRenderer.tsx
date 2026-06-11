/**
 * MetaphorRenderer — pluggable visual metaphor dispatcher.
 *
 * To add a new metaphor:
 *   1. Create the Remotion component.
 *   2. Add it to METAPHOR_MAP below (component key matches visual_metaphors.py `component` field).
 *   3. Add a MetaphorSpec entry to visual_metaphors.py.
 *   Done — no pipeline changes needed.
 */
import React from "react";
import { RocketAnimation } from "./RocketAnimation";
import { GrowthChart } from "./GrowthChart";
import { ShieldVisual } from "./ShieldVisual";
import { WorkflowNodes } from "./WorkflowNodes";
import { SpeedLines } from "./SpeedLines";
import { NeuralNetwork } from "./NeuralNetwork";
import { StarBurst } from "./StarBurst";
import { ExpandingCircles } from "./ExpandingCircles";

type MetaphorComponentProps = {
  intensity?: number;
  startFrame?: number;
  size?: number;
};

type MetaphorComponent = React.FC<MetaphorComponentProps>;

const METAPHOR_MAP: Record<string, MetaphorComponent> = {
  // Growth
  RocketAnimation,
  GrowthChart,
  // Security
  ShieldVisual,
  // Automation
  WorkflowNodes,
  // Speed
  SpeedLines,
  // AI
  NeuralNetwork,
  // Social proof
  StarBurst,
  // Scale
  ExpandingCircles,
};

interface MetaphorRendererProps {
  /** value of sceneDesign.visualMetaphor — resolved to component name via visual_metaphors.py */
  metaphorComponent?: string;
  intensity?: number;
  startFrame?: number;
  size?: number;
  style?: React.CSSProperties;
}

export const MetaphorRenderer: React.FC<MetaphorRendererProps> = ({
  metaphorComponent,
  intensity = 0.8,
  startFrame = 0,
  size = 180,
  style,
}) => {
  if (!metaphorComponent) return null;

  const Component = METAPHOR_MAP[metaphorComponent];
  if (!Component) return null;

  return (
    <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", ...style }}>
      <Component intensity={intensity} startFrame={startFrame} size={size} />
    </div>
  );
};
