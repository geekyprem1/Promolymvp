import React from "react";
import { BenefitsSceneProps, FeaturesSceneProps } from "../lib/types";
import { FeaturesScene } from "./FeaturesScene";

export const BenefitsScene: React.FC<BenefitsSceneProps> = (props) => {
  const adapted: FeaturesSceneProps = {
    ...props,
    type: "features",
    bullets: props.bodyText ? props.bodyText.split(".").filter(s => s.trim().length > 5).slice(0, 4) : [],
    reverse: props.reverse,
    bodyText: props.bodyText,
  };
  return <FeaturesScene {...adapted} />;
};
