import { Easing } from "remotion";

export const easeOutCubic  = Easing.out(Easing.cubic);
export const easeOutQuart  = Easing.out(Easing.quad);
export const easeInOutCubic = Easing.inOut(Easing.cubic);
export const easeOutBack   = Easing.out(Easing.back(1.4));
export const easeOutElastic = Easing.out(Easing.elastic(0.6));
