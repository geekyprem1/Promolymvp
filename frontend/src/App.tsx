import { useState, useRef, useEffect, useCallback, useMemo } from "react";

// ─── Theme ────────────────────────────────────────────────────────────────────

const THEMES = {
  dark: {
    bg:         "#080808",
    bgCard:     "#0e0e0e",
    bgInput:    "#111",
    bgStat:     "#0e0e0e",
    border:     "#1e1e1e",
    borderSub:  "#141414",
    borderInput:"#252525",
    text:       "#e8e8e8",
    textMuted:  "#555",
    textDim:    "#333",
    textDimmer: "#2a2a2a",
    btnBg:      "#e8e8e8",
    btnText:    "#080808",
    btnHover:   "#ffffff",
    segFilled:  "#e8e8e8",
    segEmpty:   "#1e1e1e",
    trackEmpty: "#2a2a2a",
    accent:     "#ff2d2d",
    green:      "#2dff7a",
    stepDone:   "#e8e8e8",
    stepDoneText:"#080808",
    dotColor:   "white",
    sliderFg:   "#e8e8e8",
    sliderBg:   "#2a2a2a",
    footerText: "#2a2a2a",
  },
  light: {
    bg:         "#f5f5f5",
    bgCard:     "#ffffff",
    bgInput:    "#fafafa",
    bgStat:     "#ffffff",
    border:     "#e0e0e0",
    borderSub:  "#ebebeb",
    borderInput:"#d0d0d0",
    text:       "#0a0a0a",
    textMuted:  "#777",
    textDim:    "#aaa",
    textDimmer: "#bbb",
    btnBg:      "#0a0a0a",
    btnText:    "#ffffff",
    btnHover:   "#222222",
    segFilled:  "#0a0a0a",
    segEmpty:   "#e0e0e0",
    trackEmpty: "#d0d0d0",
    accent:     "#ff2d2d",
    green:      "#00b84a",
    stepDone:   "#0a0a0a",
    stepDoneText:"#ffffff",
    dotColor:   "black",
    sliderFg:   "#0a0a0a",
    sliderBg:   "#d0d0d0",
    footerText: "#ccc",
  },
};

type ThemeKey = keyof typeof THEMES;
type ThemeTokens = typeof THEMES.dark;

// ─── Template Picker colors (matches remotion/src/lib/templates.ts) ──────────

const TEMPLATE_SWATCHES: Record<string, { from: string; to: string; accent: string }> = {
  "modern-saas": { from: "#6366f1", to: "#8b5cf6", accent: "#6366f1" },
  "apple":       { from: "#0071e3", to: "#005cbf", accent: "#0071e3" },
  "startup":     { from: "#ff3b30", to: "#ff9f0a", accent: "#ff3b30" },
  "minimal":     { from: "#111111", to: "#444444", accent: "#888888" },
};

interface TemplateInfo { id: string; name: string; description: string; }

// ─── Types ────────────────────────────────────────────────────────────────────

type Stage =
  | "idle" | "validating" | "capturing" | "analyzing"
  | "rendering" | "encoding" | "done" | "error";

interface ProgressResponse { stage: string; pct: number; message: string; }
interface GenerateResult {
  status: string; video: string; session_id: string;
  duration: number; resolution: string; fps: number;
  scenes: number; ai_used: boolean;
  storyboard: { website_type: string; video_style: string; scenes?: SceneInfo[] };
}
interface VideoMeta {
  duration: number; resolution: string; fps: number;
  scenes: number; website_type: string; video_style: string; ai_used: boolean;
}
interface SceneInfo {
  type: string; headline: string; narration?: string;
  durationInFrames: number;
}

// ─── Steps ────────────────────────────────────────────────────────────────────

const STEPS: { key: Stage; label: string; sub: string }[] = [
  { key: "validating", label: "VALIDATING URL",      sub: "Checking URL format & reachability" },
  { key: "capturing",  label: "CAPTURING SECTIONS",  sub: "Playwright DOM analysis + screenshots" },
  { key: "analyzing",  label: "AI STORYBOARD",       sub: "OpenRouter / Gemini 2.5 Flash directing" },
  { key: "rendering",  label: "RENDERING SCENES",    sub: "Remotion compositing animations" },
  { key: "encoding",   label: "ENCODING VIDEO",      sub: "H.264 export at 1920×1080" },
  { key: "done",       label: "COMPLETE",            sub: "Your marketing video is ready" },
];

const STAGE_ORDER: Stage[] = ["idle","validating","capturing","analyzing","rendering","encoding","done","error"];
const stageIdx = (s: Stage) => STAGE_ORDER.indexOf(s);
type StepStatus = "done" | "active" | "pending";

// ─── UUID ─────────────────────────────────────────────────────────────────────
function uuid() {
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

// ─── Dot Grid SVG background ──────────────────────────────────────────────────
function DotGrid({ color = "white" }: { color?: string }) {
  const id = `dots-${color.replace("#","")}`;
  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ opacity: 0.04 }} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id={id} x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="1" fill={color}/>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`}/>
    </svg>
  );
}

// ─── Spinner ──────────────────────────────────────────────────────────────────
function Spinner({ size = 14 }: { size?: number }) {
  return (
    <svg style={{ width: size, height: size }} className="animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"/>
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
    </svg>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [url, setUrl]                     = useState("");
  const [geminiKey, setGeminiKey]         = useState(() => localStorage.getItem("openrouter_key") || "");
  const [keySaved, setKeySaved]           = useState(!!localStorage.getItem("openrouter_key"));
  const [showAdvanced, setShowAdvanced]   = useState(false);
  const [voiceTestState, setVoiceTestState] = useState<"idle"|"testing"|"ok"|"fail">("idle");
  const [voiceTestMsg, setVoiceTestMsg]   = useState("");
  const [targetDuration, setTargetDuration] = useState(20);
  const [stage, setStage]                 = useState<Stage>("idle");
  const [liveMsg, setLiveMsg]             = useState("");
  const [progress, setProgress]           = useState(0);
  const [errorMsg, setErrorMsg]           = useState("");
  const [videoUrl, setVideoUrl]           = useState("");
  const [meta, setMeta]                   = useState<VideoMeta | null>(null);
  const [scenes, setScenes]               = useState<SceneInfo[]>([]);
  const [showStoryboard, setShowStoryboard] = useState(false);
  const [playing, setPlaying]             = useState(false);
  const [aiFallbackDialog, setAiFallbackDialog] = useState<{ reason: string; sid: string } | null>(null);
  const [blink, setBlink]                 = useState(true);
  const [themeKey, setThemeKey]           = useState<ThemeKey>(() =>
    (localStorage.getItem("promoly_theme") as ThemeKey) || "dark"
  );
  const [templateId, setTemplateId]       = useState<string>(() =>
    localStorage.getItem("promoly_template") || "modern-saas"
  );
  const [templateList, setTemplateList]   = useState<TemplateInfo[]>([
    { id: "modern-saas", name: "Modern SaaS",  description: "Bold gradients, animated overlays" },
    { id: "apple",       name: "Apple Style",   description: "Elegant, minimal motion" },
    { id: "startup",     name: "Startup Pitch", description: "High energy, bouncy, stats-forward" },
    { id: "minimal",     name: "Minimal",       description: "Light background, static camera" },
  ]);
  const [kokoroVoice, setKokoroVoice]     = useState<string>(() =>
    localStorage.getItem("promoly_voice") || "af_heart"
  );
  const [videoStyle, setVideoStyle]       = useState<string>(() =>
    localStorage.getItem("promoly_style") || "hybrid"
  );
  const [styleList, setStyleList]         = useState<TemplateInfo[]>([
    { id: "hybrid",           name: "Hybrid",           description: "Motion-graphics story + real screenshots. Premium." },
    { id: "website-showcase", name: "Website Showcase", description: "Real screenshots, cursor & zoom — a live demo." },
    { id: "motion-graphics",  name: "Motion Graphics",  description: "Animated cards & kinetic type — a SaaS ad." },
  ]);
  const t: ThemeTokens = useMemo(() => THEMES[themeKey], [themeKey]);

  const toggleTheme = () => {
    const next: ThemeKey = themeKey === "dark" ? "light" : "dark";
    setThemeKey(next);
    localStorage.setItem("promoly_theme", next);
  };

  const selectTemplate = (id: string) => {
    setTemplateId(id);
    localStorage.setItem("promoly_template", id);
  };

  const selectStyle = (id: string) => {
    setVideoStyle(id);
    localStorage.setItem("promoly_style", id);
  };

  const selectVoice = (id: string) => {
    setKokoroVoice(id);
    localStorage.setItem("promoly_voice", id);
  };

  // Fetch template + style lists from backend (non-blocking, updates if different)
  useEffect(() => {
    fetch("/templates")
      .then(r => r.json())
      .then(d => { if (d.templates?.length) setTemplateList(d.templates); })
      .catch(() => { /* keep defaults */ });
    fetch("/styles")
      .then(r => r.json())
      .then(d => { if (d.styles?.length) setStyleList(d.styles); })
      .catch(() => { /* keep defaults */ });
  }, []);

  const videoRef = useRef<HTMLVideoElement>(null);
  const pollRef  = useRef<ReturnType<typeof setInterval> | null>(null);

  const isLoading = !["idle","done","error"].includes(stage);

  // Blinking cursor
  useEffect(() => {
    const t = setInterval(() => setBlink(v => !v), 530);
    return () => clearInterval(t);
  }, []);

  const mapStage = (s: string): Stage => {
    const valid: Stage[] = ["validating","capturing","analyzing","rendering","encoding","done"];
    return valid.includes(s as Stage) ? s as Stage : "encoding";
  };

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
  }, []);

  const startPolling = useCallback((sid: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`/progress/${sid}`);
        const d: ProgressResponse = await r.json();
        if (d.pct > 0) {
          setProgress(d.pct);
          setStage(mapStage(d.stage));
          if (d.message) setLiveMsg(d.message);
        }
      } catch { /* ignore */ }
    }, 1000);
  }, [stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  async function callGenerate(sid: string, withKey: boolean) {
    startPolling(sid);
    try {
      const res = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          session_id: sid,
          target_duration: targetDuration,
          gemini_api_key: withKey ? (geminiKey.trim() || undefined) : undefined,
          template_id: templateId,
          video_style: videoStyle,
          kokoro_voice: kokoroVoice,
        }),
      });
      stopPolling();
      if (res.status === 402) {
        const d = await res.json().catch(() => ({}));
        const detail = d?.detail ?? {};
        const reason = typeof detail === "object" ? detail.reason : String(detail);
        setStage("idle"); setProgress(0);
        setAiFallbackDialog({ reason, sid });
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(typeof d?.detail === "string" ? d.detail : `Server error ${res.status}`);
      }
      const data: GenerateResult = await res.json();
      setVideoUrl(`/${data.video}`);
      setMeta({
        duration: data.duration, resolution: data.resolution, fps: data.fps,
        scenes: data.scenes,
        website_type: data.storyboard?.website_type ?? "saas",
        video_style: data.storyboard?.video_style ?? "explainer",
        ai_used: data.ai_used ?? false,
      });
      setScenes(data.storyboard?.scenes ?? []);
      setProgress(100); setStage("done");
    } catch (err: unknown) {
      stopPolling();
      setErrorMsg(err instanceof Error ? err.message : "Unknown error.");
      setStage("error");
    }
  }

  async function handleGenerate() {
    if (!url.trim() || isLoading) return;
    const sid = uuid();
    setStage("validating"); setProgress(5);
    setLiveMsg(""); setErrorMsg(""); setVideoUrl(""); setMeta(null);
    await callGenerate(sid, true);
  }

  async function handleFallbackContinue() {
    if (!aiFallbackDialog) return;
    const { sid } = aiFallbackDialog;
    setAiFallbackDialog(null);
    setStage("validating"); setProgress(5);
    setLiveMsg(""); setErrorMsg("");
    await callGenerate(sid, false);
  }

  function stepStatus(key: Stage): StepStatus {
    if (stage === "error") return "pending";
    const cur = stageIdx(stage), tgt = stageIdx(key);
    if (cur > tgt) return "done";
    if (cur === tgt) return "active";
    return "pending";
  }

  const fallbackReasonText = (r: string) => {
    if (r === "prepaid_credits_depleted") return "Google AI Studio prepaid credits depleted";
    if (r === "quota_exceeded") return "API quota exceeded — rate limited";
    if (r === "invalid_api_key") return "API key invalid or expired";
    return r;
  };

  async function handleVoiceTest() {
    const key = geminiKey.trim();
    if (!key) { setVoiceTestMsg("Key daalo pehle"); setVoiceTestState("fail"); return; }
    setVoiceTestState("testing"); setVoiceTestMsg("");
    try {
      const res = await fetch("/test-voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key, voice: kokoroVoice, text: "Hello from Promoly. This is a voiceover test." }),
      });
      const d = await res.json();
      if (d.ok) {
        setVoiceTestState("ok");
        setVoiceTestMsg(`✓ ${(d.bytes/1024).toFixed(1)} KB audio generated`);
        // Play the test audio
        const a = new Audio(d.audio_url);
        a.play().catch(() => {});
      } else {
        setVoiceTestState("fail");
        setVoiceTestMsg(d.error?.slice(0,120) || "Failed");
      }
    } catch(e) {
      setVoiceTestState("fail");
      setVoiceTestMsg("Network error");
    }
  }

  const sliderPct = ((targetDuration - 8) / 22) * 100;

  // Segment-style progress blocks (20 segments)
  const totalSeg = 20;
  const filledSeg = Math.round((progress / 100) * totalSeg);

  return (
    <div className="min-h-screen flex flex-col" style={{
      background: t.bg, fontFamily: "'Space Mono', monospace", color: t.text,
      transition: "background 0.3s, color 0.3s",
    }}>

      {/* ── AI Fallback Dialog ─────────────────────────────────────────────── */}
      {aiFallbackDialog && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: themeKey === "dark" ? "rgba(0,0,0,0.88)" : "rgba(0,0,0,0.55)",
          backdropFilter: "blur(8px)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{
            background: t.bgCard, border: `1px solid ${t.accent}`,
            maxWidth: 460, width: "calc(100% - 32px)", padding: 32,
          }}>
            <div style={{ fontSize: 10, color: t.accent, letterSpacing: "0.15em", marginBottom: 16 }}>!! SYSTEM ALERT</div>
            <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, letterSpacing: "-0.01em", color: t.text }}>AI ENGINE FAILURE</div>
            <div style={{ fontSize: 11, color: t.textMuted, lineHeight: 1.8, marginBottom: 20, fontFamily: "'Inter', sans-serif" }}>
              {fallbackReasonText(aiFallbackDialog.reason)}
            </div>
            <div style={{ background: t.bgInput, border: `1px solid ${t.border}`, padding: "12px 16px", marginBottom: 24, fontSize: 11, color: t.textMuted, lineHeight: 1.7, fontFamily: "'Inter', sans-serif" }}>
              ⚠ Continuing will use <span style={{ color: t.text, fontFamily: "'Space Mono', monospace" }}>RULE-BASED</span> pipeline.<br/>No AI storyboard will be generated.
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <button onClick={() => { setAiFallbackDialog(null); setStage("idle"); }}
                style={{ flex: 1, padding: "12px 0", background: "transparent", border: `1px solid ${t.border}`, color: t.textMuted, fontSize: 11, cursor: "pointer", letterSpacing: "0.1em", fontFamily: "'Space Mono', monospace" }}
                onMouseEnter={e => e.currentTarget.style.borderColor = t.text}
                onMouseLeave={e => e.currentTarget.style.borderColor = t.border}
              >CANCEL</button>
              <button onClick={handleFallbackContinue}
                style={{ flex: 1, padding: "12px 0", background: t.btnBg, border: `1px solid ${t.btnBg}`, color: t.btnText, fontSize: 11, cursor: "pointer", letterSpacing: "0.1em", fontWeight: 700, fontFamily: "'Space Mono', monospace" }}
                onMouseEnter={e => e.currentTarget.style.background = t.btnHover}
                onMouseLeave={e => e.currentTarget.style.background = t.btnBg}
              >CONTINUE ANYWAY</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <header style={{
        borderBottom: `1px solid ${t.border}`, padding: "0 24px", height: 52,
        display: "flex", alignItems: "center", background: t.bg,
        position: "sticky", top: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 28, height: 28, border: `1px solid ${t.text}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ width: 8, height: 8, background: t.accent, borderRadius: "50%" }}/>
          </div>
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.12em" }}>PROMOLY</span>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.15em" }}>AI VIDEO GENERATOR</span>

          {/* ── Theme toggle ── */}
          <button
            onClick={toggleTheme}
            title={themeKey === "dark" ? "Switch to Light" : "Switch to Dark"}
            style={{
              background: "none", border: `1px solid ${t.border}`, cursor: "pointer",
              padding: "4px 10px", display: "flex", alignItems: "center", gap: 6,
              fontFamily: "'Space Mono', monospace", fontSize: 9,
              color: t.textMuted, letterSpacing: "0.1em",
              transition: "all 0.2s",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = t.text; e.currentTarget.style.color = t.text; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.color = t.textMuted; }}
          >
            {themeKey === "dark" ? "◑ LIGHT" : "◐ DARK"}
          </button>

          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: isLoading ? t.accent : t.green,
            boxShadow: isLoading ? `0 0 6px ${t.accent}` : `0 0 6px ${t.green}`,
            animation: isLoading ? "pulse 1s ease-in-out infinite" : "none",
          }}/>
        </div>
      </header>

      {/* ── Main ──────────────────────────────────────────────────────────── */}
      <main style={{
        flex: 1, display: "flex", flexDirection: "column",
        alignItems: "center", padding: "40px 16px 60px",
        gap: 20, maxWidth: 640, margin: "0 auto", width: "100%",
      }}>

        {/* Hero */}
        <div style={{ textAlign: "center", marginBottom: 8 }}>
          <div style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em", marginBottom: 14 }}>
            ·  ·  ·  WEBSITE TO VIDEO ENGINE  ·  ·  ·
          </div>
          <h1 style={{ fontSize: 30, fontWeight: 700, lineHeight: 1.2, letterSpacing: "-0.02em", margin: 0, color: t.text }}>
            Turn any website into<br/>
            <span style={{ color: t.accent }}>a marketing video.</span>
          </h1>
          <p style={{ marginTop: 12, fontSize: 11, color: t.textMuted, lineHeight: 1.8, fontFamily: "'Inter', sans-serif", letterSpacing: "0.02em" }}>
            Playwright captures · OpenRouter/Gemini 2.5 Flash directs · Remotion renders
          </p>
        </div>

        {/* ── Input Card ────────────────────────────────────────────────── */}
        <div style={{ width: "100%", background: t.bgCard, border: `1px solid ${t.border}`, padding: "24px", position: "relative", overflow: "hidden" }}>
          <DotGrid color={t.dotColor} />

          {/* URL */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em", display: "block", marginBottom: 10 }}>WEBSITE URL</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="text" value={url}
                onChange={e => setUrl(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleGenerate()}
                placeholder="https://stripe.com"
                disabled={isLoading}
                style={{
                  flex: 1, background: t.bgInput, border: `1px solid ${t.borderInput}`,
                  color: t.text, padding: "11px 14px", fontSize: 12,
                  fontFamily: "'Space Mono', monospace", outline: "none",
                  transition: "border-color 0.15s", opacity: isLoading ? 0.4 : 1,
                }}
                onFocus={e => e.currentTarget.style.borderColor = t.text}
                onBlur={e => e.currentTarget.style.borderColor = t.borderInput}
              />
              <button onClick={handleGenerate} disabled={isLoading || !url.trim()}
                style={{
                  padding: "11px 20px", fontSize: 11, fontWeight: 700,
                  letterSpacing: "0.1em", cursor: isLoading || !url.trim() ? "not-allowed" : "pointer",
                  fontFamily: "'Space Mono', monospace", whiteSpace: "nowrap", transition: "all 0.15s",
                  background: isLoading || !url.trim() ? t.bgInput : t.btnBg,
                  border: isLoading || !url.trim() ? `1px solid ${t.border}` : `1px solid ${t.btnBg}`,
                  color: isLoading || !url.trim() ? t.textDim : t.btnText,
                  display: "flex", alignItems: "center", gap: 8,
                }}
                onMouseEnter={e => { if (!isLoading && url.trim()) e.currentTarget.style.background = t.btnHover; }}
                onMouseLeave={e => { if (!isLoading && url.trim()) e.currentTarget.style.background = t.btnBg; }}
              >
                {isLoading ? <><Spinner size={12}/> <span>PROCESSING</span></> : <span>▶ GENERATE</span>}
              </button>
            </div>
          </div>

          {/* Duration */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <label style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em" }}>VIDEO DURATION</label>
              <span style={{ fontSize: 11, color: t.text, fontWeight: 700 }}>{targetDuration}S</span>
            </div>
            <div style={{ display: "flex", gap: 3, marginBottom: 10, pointerEvents: "none" }}>
              {Array.from({ length: 22 }).map((_, i) => {
                const filled = i < Math.round(((targetDuration - 8) / 22) * 22);
                return <div key={i} style={{ flex: 1, height: 4, background: filled ? t.segFilled : t.segEmpty, transition: "background 0.1s" }}/>;
              })}
            </div>
            <input
              type="range" min={8} max={30} step={1} value={targetDuration}
              disabled={isLoading}
              onChange={e => setTargetDuration(Number(e.target.value))}
              style={{
                width: "100%", cursor: isLoading ? "not-allowed" : "pointer", display: "block",
                accentColor: t.sliderFg,
                background: `linear-gradient(to right, ${t.sliderFg} 0%, ${t.sliderFg} ${sliderPct}%, ${t.sliderBg} ${sliderPct}%, ${t.sliderBg} 100%)`,
              }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: t.textDim, marginTop: 6 }}>
              <span>8S</span><span>15S</span><span>22S</span><span>30S</span>
            </div>
          </div>

          {/* Video Style Selector */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em", display: "block", marginBottom: 10 }}>
              VIDEO STYLE
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
              {styleList.map(st => {
                const isSelected = videoStyle === st.id;
                const accent = t.accent;
                return (
                  <button
                    key={st.id}
                    onClick={() => selectStyle(st.id)}
                    disabled={isLoading}
                    title={st.description}
                    style={{
                      position: "relative",
                      background: isSelected ? (themeKey === "dark" ? "#111" : "#fff") : "transparent",
                      border: isSelected ? `1px solid ${accent}` : `1px solid ${t.border}`,
                      cursor: isLoading ? "not-allowed" : "pointer",
                      padding: "11px 8px 10px",
                      textAlign: "center",
                      transition: "all 0.15s",
                      opacity: isLoading ? 0.5 : 1,
                    }}
                    onMouseEnter={e => { if (!isLoading) e.currentTarget.style.borderColor = accent; }}
                    onMouseLeave={e => { if (!isLoading) e.currentTarget.style.borderColor = isSelected ? accent : t.border; }}
                  >
                    <div style={{
                      fontSize: 8, fontWeight: 700, letterSpacing: "0.08em",
                      color: isSelected ? accent : t.textMuted,
                      fontFamily: "'Space Mono', monospace", lineHeight: 1.35,
                    }}>
                      {st.name.toUpperCase()}
                      {st.id === "hybrid" && <span style={{ color: t.textDim, fontSize: 7 }}> ★</span>}
                    </div>
                    {isSelected && (
                      <div style={{ position: "absolute", top: 4, right: 5, fontSize: 7, color: accent,
                        fontFamily: "'Space Mono', monospace" }}>✓</div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Template Picker */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em", display: "block", marginBottom: 10 }}>
              VIDEO TEMPLATE
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
              {templateList.map(tpl => {
                const swatch = TEMPLATE_SWATCHES[tpl.id] ?? { from: "#888", to: "#555", accent: "#888" };
                const isSelected = templateId === tpl.id;
                return (
                  <button
                    key={tpl.id}
                    onClick={() => selectTemplate(tpl.id)}
                    disabled={isLoading}
                    title={tpl.description}
                    style={{
                      position: "relative",
                      background: isSelected ? (themeKey === "dark" ? "#111" : "#fff") : "transparent",
                      border: isSelected ? `1px solid ${swatch.accent}` : `1px solid ${t.border}`,
                      cursor: isLoading ? "not-allowed" : "pointer",
                      padding: "10px 8px 9px",
                      textAlign: "center",
                      transition: "all 0.15s",
                      opacity: isLoading ? 0.5 : 1,
                    }}
                    onMouseEnter={e => { if (!isLoading) e.currentTarget.style.borderColor = swatch.accent; }}
                    onMouseLeave={e => { if (!isLoading) e.currentTarget.style.borderColor = isSelected ? swatch.accent : t.border; }}
                  >
                    {/* Color swatch */}
                    <div style={{
                      width: 22, height: 6,
                      borderRadius: 2,
                      background: `linear-gradient(90deg, ${swatch.from}, ${swatch.to})`,
                      margin: "0 auto 7px",
                    }} />
                    <div style={{
                      fontSize: 8, fontWeight: 700, letterSpacing: "0.1em",
                      color: isSelected ? swatch.accent : t.textMuted,
                      fontFamily: "'Space Mono', monospace",
                      lineHeight: 1.3,
                    }}>
                      {tpl.name.toUpperCase().replace(" ", "\n")}
                    </div>
                    {isSelected && (
                      <div style={{
                        position: "absolute", top: 4, right: 5,
                        fontSize: 7, color: swatch.accent,
                        fontFamily: "'Space Mono', monospace",
                      }}>✓</div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Voice Picker */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <label style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em" }}>VOICEOVER</label>
              <span style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.1em" }}>// KOKORO-82M · OPENROUTER</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
              {([
                { id: "af_heart",   label: "HEART",   desc: "Female · Warm",     tag: "★" },
                { id: "af_nova",    label: "NOVA",    desc: "Female · Clear",    tag: "F" },
                { id: "af_sky",     label: "SKY",     desc: "Female · Bright",   tag: "F" },
                { id: "am_echo",    label: "ECHO",    desc: "Male · Clear",      tag: "M" },
                { id: "am_michael", label: "MICHAEL", desc: "Male · Deep",       tag: "M" },
                { id: "bm_george",  label: "GEORGE",  desc: "Male · British",    tag: "M" },
              ] as { id: string; label: string; desc: string; tag: string }[]).map(v => {
                const isSelected = kokoroVoice === v.id;
                const isFemale = v.id.startsWith("a") && v.id[1] === "f";
                const dotColor = isFemale ? "#a78bfa" : "#60a5fa";
                return (
                  <button
                    key={v.id}
                    onClick={() => selectVoice(v.id)}
                    disabled={isLoading}
                    title={v.desc}
                    style={{
                      position: "relative",
                      background: isSelected ? (themeKey === "dark" ? "#111" : "#fff") : "transparent",
                      border: isSelected ? `1px solid ${dotColor}` : `1px solid ${t.border}`,
                      cursor: isLoading ? "not-allowed" : "pointer",
                      padding: "9px 8px 8px",
                      textAlign: "center",
                      transition: "all 0.15s",
                      opacity: isLoading ? 0.5 : 1,
                    }}
                    onMouseEnter={e => { if (!isLoading) e.currentTarget.style.borderColor = dotColor; }}
                    onMouseLeave={e => { if (!isLoading) e.currentTarget.style.borderColor = isSelected ? dotColor : t.border; }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 5, marginBottom: 3 }}>
                      <div style={{ width: 5, height: 5, borderRadius: "50%", background: isSelected ? dotColor : t.textDimmer, flexShrink: 0 }}/>
                      <span style={{
                        fontSize: 8, fontWeight: 700, letterSpacing: "0.08em",
                        color: isSelected ? dotColor : t.textMuted,
                        fontFamily: "'Space Mono', monospace",
                      }}>{v.label}</span>
                    </div>
                    <div style={{ fontSize: 8, color: t.textDimmer, fontFamily: "'Inter', sans-serif", letterSpacing: "0.02em" }}>{v.desc}</div>
                    {isSelected && (
                      <div style={{ position: "absolute", top: 3, right: 5, fontSize: 7, color: dotColor, fontFamily: "'Space Mono', monospace" }}>✓</div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Advanced */}
          <div>
            <button onClick={() => setShowAdvanced(v => !v)}
              style={{ background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex", alignItems: "center", gap: 8, fontSize: 9, color: t.textDim, letterSpacing: "0.2em", fontFamily: "'Space Mono', monospace" }}
            >
              <span style={{ transform: showAdvanced ? "rotate(90deg)" : "rotate(0deg)", display: "inline-block", transition: "transform 0.2s" }}>▶</span>
              ADVANCED SETTINGS
              {geminiKey && <span style={{ fontSize: 9, padding: "2px 7px", border: `1px solid ${t.accent}`, color: t.accent, letterSpacing: "0.1em" }}>AI ON</span>}
            </button>

            {showAdvanced && (
              <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${t.borderSub}` }}>
                <label style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em", display: "block", marginBottom: 10 }}>
                  OPENROUTER API KEY <span style={{ color: t.textDimmer, marginLeft: 12 }}>// OPTIONAL · GEMINI 2.5 FLASH</span>
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    type="password" value={geminiKey}
                    onChange={e => { setGeminiKey(e.target.value); setKeySaved(false); }}
                    placeholder="sk-or-v1-..."
                    disabled={isLoading}
                    style={{
                      flex: 1, background: t.bgInput, border: `1px solid ${t.borderInput}`,
                      color: t.text, padding: "10px 14px", fontSize: 11,
                      fontFamily: "'Space Mono', monospace", outline: "none",
                      opacity: isLoading ? 0.4 : 1,
                    }}
                    onFocus={e => e.currentTarget.style.borderColor = t.textMuted}
                    onBlur={e => e.currentTarget.style.borderColor = t.borderInput}
                  />
                  <button
                    onClick={() => {
                      if (geminiKey.trim()) { localStorage.setItem("openrouter_key", geminiKey.trim()); setKeySaved(true); }
                      else { localStorage.removeItem("openrouter_key"); setKeySaved(false); }
                    }}
                    disabled={isLoading}
                    style={{
                      padding: "10px 16px", fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", cursor: "pointer",
                      fontFamily: "'Space Mono', monospace",
                      background: keySaved ? t.btnBg : "transparent",
                      border: keySaved ? `1px solid ${t.btnBg}` : `1px solid ${t.border}`,
                      color: keySaved ? t.btnText : t.textMuted,
                      transition: "all 0.15s",
                    }}
                  >{keySaved ? "SAVED ✓" : "SAVE"}</button>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
                  {geminiKey
                    ? <span style={{ fontSize: 9, color: t.green, letterSpacing: "0.1em" }}>✓ KEY STORED IN BROWSER</span>
                    : <span style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.1em" }}>GET KEY AT OPENROUTER.AI/KEYS</span>
                  }
                  {geminiKey && (
                    <button onClick={() => { localStorage.removeItem("openrouter_key"); setGeminiKey(""); setKeySaved(false); setVoiceTestState("idle"); setVoiceTestMsg(""); }}
                      style={{ background: "none", border: "none", cursor: "pointer", padding: 0, fontSize: 9, color: t.accent, letterSpacing: "0.1em", fontFamily: "'Space Mono', monospace" }}
                    >CLEAR</button>
                  )}
                </div>

                {/* Voice test button */}
                {geminiKey && (
                  <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 10 }}>
                    <button
                      onClick={handleVoiceTest}
                      disabled={voiceTestState === "testing"}
                      style={{
                        padding: "8px 14px", fontSize: 9, fontWeight: 700,
                        letterSpacing: "0.1em", cursor: voiceTestState === "testing" ? "not-allowed" : "pointer",
                        fontFamily: "'Space Mono', monospace",
                        background: "transparent",
                        border: `1px solid ${voiceTestState === "ok" ? t.green : voiceTestState === "fail" ? t.accent : t.border}`,
                        color: voiceTestState === "ok" ? t.green : voiceTestState === "fail" ? t.accent : t.textMuted,
                        display: "flex", alignItems: "center", gap: 6, transition: "all 0.15s",
                      }}
                    >
                      {voiceTestState === "testing" ? <><Spinner size={10}/> TESTING…</> : "▶ TEST VOICE"}
                    </button>
                    {voiceTestMsg && (
                      <span style={{
                        fontSize: 9, letterSpacing: "0.08em",
                        color: voiceTestState === "ok" ? t.green : t.accent,
                        fontFamily: "'Space Mono', monospace",
                      }}>{voiceTestMsg}</span>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Progress Card ─────────────────────────────────────────────────── */}
        {stage !== "idle" && (
          <div style={{ width: "100%", background: t.bgCard, border: `1px solid ${t.border}`, padding: "24px", position: "relative", overflow: "hidden" }}>
            <DotGrid color={t.dotColor} />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <span style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em" }}>PIPELINE STATUS</span>
              <span style={{ fontSize: 11, color: t.text, fontWeight: 700 }}>
                {progress}<span style={{ fontSize: 9, color: t.textDim, marginLeft: 2 }}>%</span>
              </span>
            </div>
            <div style={{ display: "flex", gap: 2, marginBottom: 22 }}>
              {Array.from({ length: totalSeg }).map((_, i) => (
                <div key={i} style={{
                  flex: 1, height: 3,
                  background: i < filledSeg ? (stage === "error" ? t.accent : t.segFilled) : t.segEmpty,
                  transition: "background 0.4s ease",
                }}/>
              ))}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {STEPS.map((s, idx) => {
                const status = stepStatus(s.key);
                const isLast = idx === STEPS.length - 1;
                return (
                  <div key={s.key} style={{
                    display: "flex", alignItems: "flex-start", gap: 14,
                    paddingBottom: isLast ? 0 : 14, marginBottom: isLast ? 0 : 14,
                    borderBottom: isLast ? "none" : `1px solid ${t.borderSub}`,
                  }}>
                    <div style={{ width: 18, height: 18, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", marginTop: 1 }}>
                      {status === "done" ? (
                        <div style={{ width: 18, height: 18, background: t.stepDone, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: t.stepDoneText }}>✓</div>
                      ) : status === "active" ? (
                        <div style={{ width: 18, height: 18, display: "flex", alignItems: "center", justifyContent: "center" }}><Spinner size={14}/></div>
                      ) : (
                        <div style={{ width: 6, height: 6, borderRadius: "50%", background: t.segEmpty, border: `1px solid ${t.border}`, margin: "0 auto" }}/>
                      )}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", transition: "color 0.3s",
                        color: status === "pending" ? t.textDimmer : status === "active" ? t.text : t.textMuted,
                      }}>{s.label}</div>
                      {status === "active" && (
                        <div style={{ fontSize: 10, color: t.textMuted, marginTop: 3, fontFamily: "'Inter', sans-serif", letterSpacing: "0.02em" }}>
                          {liveMsg || s.sub}<span style={{ opacity: blink ? 1 : 0 }}>_</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            {stage === "error" && (
              <div style={{ marginTop: 16, padding: "14px 16px", border: `1px solid ${t.accent}`, background: themeKey === "dark" ? "#1a0a0a" : "#fff5f5" }}>
                <div style={{ fontSize: 9, color: t.accent, letterSpacing: "0.2em", marginBottom: 6 }}>!! ERROR</div>
                <div style={{ fontSize: 11, color: t.accent, lineHeight: 1.6, fontFamily: "'Inter', sans-serif" }}>{errorMsg}</div>
                <button onClick={() => setStage("idle")}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0, marginTop: 10, fontSize: 10, color: t.text, letterSpacing: "0.1em", fontFamily: "'Space Mono', monospace" }}
                >→ RETRY</button>
              </div>
            )}
          </div>
        )}

        {/* ── Video Result ──────────────────────────────────────────────────── */}
        {videoUrl && stage === "done" && meta && (
          <div style={{ width: "100%", background: t.bgCard, border: `1px solid ${t.border}`, padding: "24px", position: "relative", overflow: "hidden" }}>
            <DotGrid color={t.dotColor} />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <span style={{ fontSize: 9, color: t.textDim, letterSpacing: "0.2em" }}>OUTPUT</span>
              <div style={{ display: "flex", gap: 8 }}>
                {meta.ai_used
                  ? <span style={{ fontSize: 9, padding: "3px 8px", border: `1px solid ${t.accent}`, color: t.accent, letterSpacing: "0.1em" }}>GEMINI AI</span>
                  : <span style={{ fontSize: 9, padding: "3px 8px", border: `1px solid ${t.border}`, color: t.textDim, letterSpacing: "0.1em" }}>RULE-BASED</span>
                }
                {(() => { const sw = TEMPLATE_SWATCHES[templateId]; return sw ? <span style={{ fontSize: 9, padding: "3px 8px", border: `1px solid ${sw.accent}`, color: sw.accent, letterSpacing: "0.1em" }}>{templateId.toUpperCase()}</span> : null; })()}
                <span style={{ fontSize: 9, padding: "3px 8px", border: `1px solid ${t.green}`, color: t.green, letterSpacing: "0.1em" }}>READY</span>
              </div>
            </div>
            <div style={{ position: "relative", cursor: "pointer", border: `1px solid ${t.borderInput}`, aspectRatio: "16/9", background: "#000", overflow: "hidden" }}
              onClick={() => { if (!videoRef.current) return; videoRef.current.paused ? videoRef.current.play() : videoRef.current.pause(); }}
            >
              <video ref={videoRef} src={videoUrl} loop playsInline
                style={{ width: "100%", display: "block", aspectRatio: "16/9" }}
                onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
              />
              {!playing && (
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.5)" }}>
                  <div style={{ width: 52, height: 52, border: "1px solid #e8e8e8", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, color: "#e8e8e8" }}>▶</div>
                </div>
              )}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 1, background: t.border, marginTop: 12 }}>
              {[
                { label: "DUR", value: `${meta.duration}S` },
                { label: "RES", value: meta.resolution.replace("×","x") },
                { label: "FPS", value: `${meta.fps}` },
                { label: "SCN", value: `${meta.scenes}` },
                { label: "TYPE", value: meta.website_type.toUpperCase() },
              ].map(stat => (
                <div key={stat.label} style={{ background: t.bgStat, padding: "10px 6px", textAlign: "center" }}>
                  <div style={{ fontSize: 8, color: t.textDim, letterSpacing: "0.15em", marginBottom: 4 }}>{stat.label}</div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: t.text }}>{stat.value}</div>
                </div>
              ))}
            </div>
            <a href={videoUrl} download="promoly.mp4"
              style={{
                display: "flex", alignItems: "center", justifyContent: "center",
                gap: 10, width: "100%", padding: "14px 0", marginTop: 12,
                background: t.btnBg, border: `1px solid ${t.btnBg}`,
                color: t.btnText, fontSize: 11, fontWeight: 700,
                letterSpacing: "0.12em", textDecoration: "none",
                fontFamily: "'Space Mono', monospace", transition: "background 0.15s",
              }}
              onMouseEnter={e => e.currentTarget.style.background = t.btnHover}
              onMouseLeave={e => e.currentTarget.style.background = t.btnBg}
            >↓ DOWNLOAD MP4</a>
            {/* Regenerate: same URL, same template — just re-run */}
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button
                onClick={async () => {
                  const sid = uuid();
                  setStage("validating"); setProgress(5);
                  setLiveMsg(""); setErrorMsg(""); setVideoUrl(""); setMeta(null); setScenes([]);
                  await callGenerate(sid, true);
                }}
                style={{
                  flex: 1, padding: "12px 0", background: "transparent",
                  border: `1px solid ${t.border}`, cursor: "pointer",
                  fontSize: 10, fontWeight: 700, color: t.textMuted,
                  letterSpacing: "0.12em", fontFamily: "'Space Mono', monospace",
                  transition: "all 0.15s",
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = t.text; e.currentTarget.style.color = t.text; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.color = t.textMuted; }}
              >↺ REGENERATE</button>
              <button
                onClick={() => { setStage("idle"); setVideoUrl(""); setMeta(null); setScenes([]); setUrl(""); setProgress(0); }}
                style={{
                  flex: 1, padding: "12px 0", background: "transparent",
                  border: `1px solid ${t.border}`, cursor: "pointer",
                  fontSize: 10, color: t.textDim,
                  letterSpacing: "0.12em", fontFamily: "'Space Mono', monospace",
                  transition: "all 0.15s",
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = t.textMuted; e.currentTarget.style.color = t.textMuted; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.color = t.textDim; }}
              >→ NEW VIDEO</button>
            </div>

            {/* Storyboard accordion */}
            {scenes.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <button
                  onClick={() => setShowStoryboard(v => !v)}
                  style={{
                    width: "100%", background: "none", border: `1px solid ${t.borderSub}`,
                    cursor: "pointer", padding: "10px 14px", textAlign: "left",
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    fontFamily: "'Space Mono', monospace", fontSize: 9,
                    color: t.textDim, letterSpacing: "0.15em",
                    transition: "border-color 0.15s",
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = t.border}
                  onMouseLeave={e => e.currentTarget.style.borderColor = t.borderSub}
                >
                  <span>STORYBOARD  ({scenes.length} SCENES)</span>
                  <span style={{ transform: showStoryboard ? "rotate(180deg)" : "none", display: "inline-block", transition: "transform 0.2s" }}>▼</span>
                </button>
                {showStoryboard && (
                  <div style={{ border: `1px solid ${t.borderSub}`, borderTop: "none" }}>
                    {scenes.map((sc, i) => (
                      <div key={i} style={{
                        padding: "10px 14px",
                        borderBottom: i < scenes.length - 1 ? `1px solid ${t.borderSub}` : "none",
                        display: "flex", gap: 12, alignItems: "flex-start",
                      }}>
                        <div style={{
                          fontSize: 8, fontWeight: 700, letterSpacing: "0.1em",
                          color: t.accent, minWidth: 14, paddingTop: 1,
                          fontFamily: "'Space Mono', monospace",
                        }}>{String(i + 1).padStart(2, "0")}</div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: sc.narration ? 4 : 0 }}>
                            <span style={{
                              fontSize: 8, color: t.textDim, letterSpacing: "0.1em",
                              border: `1px solid ${t.borderSub}`, padding: "1px 5px",
                              fontFamily: "'Space Mono', monospace",
                            }}>{sc.type.toUpperCase()}</span>
                            <span style={{ fontSize: 11, color: t.text, fontFamily: "'Inter', sans-serif" }}>{sc.headline}</span>
                            <span style={{ marginLeft: "auto", fontSize: 9, color: t.textDim, fontFamily: "'Space Mono', monospace" }}>
                              {(sc.durationInFrames / 30).toFixed(0)}S
                            </span>
                          </div>
                          {sc.narration && (
                            <div style={{ fontSize: 10, color: t.textMuted, fontFamily: "'Inter', sans-serif", lineHeight: 1.6, fontStyle: "italic" }}>
                              "{sc.narration}"
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer style={{
        borderTop: `1px solid ${t.borderSub}`, padding: "16px 24px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <span style={{ fontSize: 9, color: t.footerText, letterSpacing: "0.15em" }}>
          PROMOLY © 2025
        </span>
        <span style={{ fontSize: 9, color: t.footerText, letterSpacing: "0.1em" }}>
          GEMINI · PLAYWRIGHT · REMOTION
        </span>
      </footer>

      <style>{`
        * { box-sizing: border-box; }
        body { margin: 0; -webkit-font-smoothing: antialiased; }

        input[type=range] {
          -webkit-appearance: none;
          appearance: none;
          height: 2px;
          background: #2a2a2a;
          outline: none;
          border: none;
          padding: 0;
        }
        input[type=range]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 14px;
          height: 14px;
          background: #e8e8e8;
          cursor: pointer;
          border: none;
          border-radius: 0;
        }
        input[type=range]::-moz-range-thumb {
          width: 14px;
          height: 14px;
          background: #e8e8e8;
          cursor: pointer;
          border: none;
          border-radius: 0;
        }
        input[type=range]::-webkit-slider-runnable-track {
          height: 2px;
          background: #2a2a2a;
        }
        input[type=range]:disabled::-webkit-slider-thumb { background: #333; cursor: not-allowed; }

        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
      `}</style>
    </div>
  );
}
