/**
 * templates.ts – Remotion Visual Template Registry
 *
 * Defines the visual layer of each template: colors, typography, CTA style,
 * and spring physics. Behavioral decisions (camera, transitions, overlay
 * placements) live in backend/templates.py.
 *
 * Adding a new template: create a TemplateConfig object, add it to TEMPLATES,
 * and add the id to TEMPLATE_IDS. No other changes required.
 */

import React from "react";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface TemplateColors {
  bg:           string;
  bg2:          string;
  surface:      string;
  border:       string;
  text:         string;
  textMuted:    string;
  textFaint:    string;
  accent:       string;
  accentGlow:   string;
  secondary:    string;
  gradientFrom: string;
  gradientTo:   string;
  /** Background overlay gradient (CSS background shorthand) */
  heroOverlay:  string;
  splitOverlay: string;
  ctaOverlay:   string;
}

export interface TemplateTypography {
  headingFont:      string;   // CSS font-family
  bodyFont:         string;
  headingWeight:    number;   // 600–900
  sizeScale:        number;   // 1.0 = default scene sizes
  letterSpacing:    number;   // px on headings
  lineHeight:       number;
  textTransform:    "none" | "uppercase" | "capitalize";
}

export interface TemplateSpring {
  stiffness: number;
  damping:   number;
  mass:      number;
}

export interface TemplateCTA {
  buttonStyle:  "filled" | "outline" | "glass";
  buttonRadius: number;   // border-radius px (999 = pill)
  showGlow:     boolean;
  showShimmer:  boolean;
  buttonBg:     string;
  buttonText:   string;
  buttonShadow: string;
}

export interface TemplateBadge {
  bg:           string;
  border:       string;
  text:         string;
  borderRadius: number;
  prefix:       string;   // e.g. "✦ " or ""
}

export interface TemplateConfig {
  id:          string;
  name:        string;
  description: string;
  colors:      TemplateColors;
  typography:  TemplateTypography;
  spring:      TemplateSpring;
  cta:         TemplateCTA;
  badge:       TemplateBadge;
  /** Whether to render the dot-grid background pattern */
  showDotGrid: boolean;
  /** Whether the background image is used in scenes (vs. solid color) */
  useScreenshot: boolean;
  /** Backdrop blur strength in px */
  backdropBlur: number;
}

// ── Template definitions ───────────────────────────────────────────────────────

const MODERN_SAAS: TemplateConfig = {
  id:          "modern-saas",
  name:        "Modern SaaS",
  description: "Bold gradients, animated overlays, indigo palette",
  colors: {
    bg:           "#070712",
    bg2:          "#0d0d1f",
    surface:      "rgba(255,255,255,0.04)",
    border:       "rgba(255,255,255,0.08)",
    text:         "#ffffff",
    textMuted:    "rgba(255,255,255,0.55)",
    textFaint:    "rgba(255,255,255,0.30)",
    accent:       "#6366f1",
    accentGlow:   "rgba(99,102,241,0.25)",
    secondary:    "#8b5cf6",
    gradientFrom: "#6366f1",
    gradientTo:   "#8b5cf6",
    heroOverlay: `
      radial-gradient(ellipse 100% 80% at 30% 40%, rgba(99,102,241,0.22) 0%, transparent 60%),
      radial-gradient(ellipse 80% 100% at 75% 60%, rgba(139,92,246,0.14) 0%, transparent 55%),
      linear-gradient(to bottom, rgba(7,7,18,0.3) 0%, rgba(7,7,18,0.55) 50%, rgba(7,7,18,0.80) 100%)
    `,
    splitOverlay: `radial-gradient(ellipse 70% 100% at 20% 50%, rgba(99,102,241,0.10) 0%, transparent 60%), #070712`,
    ctaOverlay: `
      radial-gradient(ellipse 120% 80% at 50% 20%, rgba(99,102,241,0.20) 0%, transparent 55%),
      radial-gradient(ellipse 80% 120% at 80% 90%, rgba(139,92,246,0.15) 0%, transparent 55%),
      #050510
    `,
  },
  typography: {
    headingFont:   "'Inter', -apple-system, 'Segoe UI', sans-serif",
    bodyFont:      "'Inter', -apple-system, 'Segoe UI', sans-serif",
    headingWeight: 800,
    sizeScale:     1.0,
    letterSpacing: -3,
    lineHeight:    1.05,
    textTransform: "none",
  },
  spring:  { stiffness: 100, damping: 14, mass: 1.0 },
  cta: {
    buttonStyle:  "glass",
    buttonRadius: 100,
    showGlow:     true,
    showShimmer:  false,
    buttonBg:     "linear-gradient(135deg, #6366f1, #8b5cf6)",
    buttonText:   "#ffffff",
    buttonShadow: "0 8px 40px rgba(99,102,241,0.45)",
  },
  badge: {
    bg:           "rgba(99,102,241,0.12)",
    border:       "rgba(99,102,241,0.25)",
    text:         "#a5b4fc",
    borderRadius: 100,
    prefix:       "✦ ",
  },
  showDotGrid:   false,
  useScreenshot: true,
  backdropBlur:  28,
};

const APPLE_STYLE: TemplateConfig = {
  id:          "apple",
  name:        "Apple Style",
  description: "Elegant, minimal motion, SF-style typography",
  colors: {
    bg:           "#000000",
    bg2:          "#0a0a0a",
    surface:      "rgba(255,255,255,0.06)",
    border:       "rgba(255,255,255,0.10)",
    text:         "#f5f5f7",
    textMuted:    "rgba(245,245,247,0.60)",
    textFaint:    "rgba(245,245,247,0.30)",
    accent:       "#0071e3",
    accentGlow:   "rgba(0,113,227,0.20)",
    secondary:    "#30d158",
    gradientFrom: "#0071e3",
    gradientTo:   "#005cbf",
    heroOverlay: `
      radial-gradient(ellipse 90% 70% at 50% 50%, rgba(0,113,227,0.12) 0%, transparent 65%),
      linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.6) 100%)
    `,
    splitOverlay: `radial-gradient(ellipse 60% 80% at 20% 50%, rgba(0,113,227,0.06) 0%, transparent 50%), #000000`,
    ctaOverlay:   `radial-gradient(ellipse 100% 60% at 50% 30%, rgba(0,113,227,0.14) 0%, transparent 55%), #000000`,
  },
  typography: {
    headingFont:   "-apple-system, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif",
    bodyFont:      "-apple-system, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif",
    headingWeight: 700,
    sizeScale:     0.95,
    letterSpacing: -2,
    lineHeight:    1.08,
    textTransform: "none",
  },
  spring:  { stiffness: 55, damping: 24, mass: 1.2 },
  cta: {
    buttonStyle:  "filled",
    buttonRadius: 980,
    showGlow:     false,
    showShimmer:  false,
    buttonBg:     "#0071e3",
    buttonText:   "#ffffff",
    buttonShadow: "none",
  },
  badge: {
    bg:           "rgba(0,113,227,0.12)",
    border:       "rgba(0,113,227,0.20)",
    text:         "#0071e3",
    borderRadius: 6,
    prefix:       "",
  },
  showDotGrid:   false,
  useScreenshot: true,
  backdropBlur:  40,
};

const STARTUP_PITCH: TemplateConfig = {
  id:          "startup",
  name:        "Startup Pitch",
  description: "High energy, bold red, bouncy animations, stats-forward",
  colors: {
    bg:           "#080808",
    bg2:          "#100303",
    surface:      "rgba(255,59,48,0.06)",
    border:       "rgba(255,59,48,0.15)",
    text:         "#ffffff",
    textMuted:    "rgba(255,255,255,0.60)",
    textFaint:    "rgba(255,255,255,0.25)",
    accent:       "#ff3b30",
    accentGlow:   "rgba(255,59,48,0.30)",
    secondary:    "#ff9f0a",
    gradientFrom: "#ff3b30",
    gradientTo:   "#ff9f0a",
    heroOverlay: `
      radial-gradient(ellipse 90% 70% at 50% 45%, rgba(255,59,48,0.20) 0%, transparent 60%),
      radial-gradient(ellipse 60% 60% at 80% 20%, rgba(255,159,10,0.12) 0%, transparent 50%),
      linear-gradient(to bottom, rgba(8,8,8,0.2) 0%, rgba(8,8,8,0.65) 100%)
    `,
    splitOverlay: `radial-gradient(ellipse 70% 80% at 20% 50%, rgba(255,59,48,0.08) 0%, transparent 55%), #080808`,
    ctaOverlay: `
      radial-gradient(ellipse 100% 70% at 50% 30%, rgba(255,59,48,0.25) 0%, transparent 55%),
      radial-gradient(ellipse 60% 60% at 80% 80%, rgba(255,159,10,0.15) 0%, transparent 50%),
      #060606
    `,
  },
  typography: {
    headingFont:   "'Inter', -apple-system, 'Segoe UI', sans-serif",
    bodyFont:      "'Inter', -apple-system, 'Segoe UI', sans-serif",
    headingWeight: 900,
    sizeScale:     1.05,
    letterSpacing: -4,
    lineHeight:    1.0,
    textTransform: "none",
  },
  spring:  { stiffness: 240, damping: 8, mass: 0.8 },
  cta: {
    buttonStyle:  "filled",
    buttonRadius: 12,
    showGlow:     true,
    showShimmer:  true,
    buttonBg:     "#ff3b30",
    buttonText:   "#ffffff",
    buttonShadow: "0 8px 40px rgba(255,59,48,0.55)",
  },
  badge: {
    bg:           "rgba(255,59,48,0.15)",
    border:       "rgba(255,59,48,0.40)",
    text:         "#ff3b30",
    borderRadius: 6,
    prefix:       "",
  },
  showDotGrid:   false,
  useScreenshot: true,
  backdropBlur:  24,
};

const MINIMAL: TemplateConfig = {
  id:          "minimal",
  name:        "Minimal",
  description: "Light background, static camera, opacity-only motion",
  colors: {
    bg:           "#fafafa",
    bg2:          "#f0f0f0",
    surface:      "rgba(0,0,0,0.03)",
    border:       "rgba(0,0,0,0.08)",
    text:         "#111111",
    textMuted:    "rgba(17,17,17,0.55)",
    textFaint:    "rgba(17,17,17,0.28)",
    accent:       "#111111",
    accentGlow:   "rgba(17,17,17,0.10)",
    secondary:    "#555555",
    gradientFrom: "#111111",
    gradientTo:   "#444444",
    heroOverlay: `
      linear-gradient(to bottom, rgba(250,250,250,0.05) 0%, rgba(250,250,250,0.5) 100%)
    `,
    splitOverlay: `rgba(250,250,250,0.7)`,
    ctaOverlay:   `rgba(250,250,250,0.8)`,
  },
  typography: {
    headingFont:   "system-ui, -apple-system, 'Segoe UI', sans-serif",
    bodyFont:      "system-ui, -apple-system, 'Segoe UI', sans-serif",
    headingWeight: 500,
    sizeScale:     0.9,
    letterSpacing: -1,
    lineHeight:    1.12,
    textTransform: "none",
  },
  spring:  { stiffness: 40, damping: 28, mass: 1.5 },
  cta: {
    buttonStyle:  "outline",
    buttonRadius: 8,
    showGlow:     false,
    showShimmer:  false,
    buttonBg:     "transparent",
    buttonText:   "#111111",
    buttonShadow: "none",
  },
  badge: {
    bg:           "transparent",
    border:       "rgba(17,17,17,0.15)",
    text:         "rgba(17,17,17,0.60)",
    borderRadius: 4,
    prefix:       "",
  },
  showDotGrid:   false,
  useScreenshot: true,
  backdropBlur:  0,
};

// ── Registry ──────────────────────────────────────────────────────────────────

export const TEMPLATES: Record<string, TemplateConfig> = {
  "modern-saas": MODERN_SAAS,
  "apple":       APPLE_STYLE,
  "startup":     STARTUP_PITCH,
  "minimal":     MINIMAL,
};

export const DEFAULT_TEMPLATE_ID = "modern-saas";

export function getTemplate(id: string | undefined): TemplateConfig {
  return TEMPLATES[id ?? DEFAULT_TEMPLATE_ID] ?? MODERN_SAAS;
}

// ── React Context ──────────────────────────────────────────────────────────────

export const TemplateContext = React.createContext<TemplateConfig>(MODERN_SAAS);

export function useTemplate(): TemplateConfig {
  return React.useContext(TemplateContext);
}
