import { useState, useRef, useEffect, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Stage =
  | "idle" | "validating" | "capturing" | "analyzing"
  | "rendering" | "encoding" | "done" | "error";

interface ProgressResponse {
  stage: string; pct: number; message: string;
}
interface GenerateResult {
  status: string; video: string; session_id: string;
  duration: number; resolution: string; fps: number;
  scenes: number; ai_used: boolean;
  storyboard: { website_type: string; video_style: string };
}
interface VideoMeta {
  duration: number; resolution: string; fps: number;
  scenes: number; website_type: string; video_style: string;
  ai_used: boolean;
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function LogoIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="3" width="15" height="14" rx="2" fill="#6366f1"/>
      <path d="M17 8l5 4-5 4V8z" fill="#a5b4fc"/>
      <rect x="5" y="7" width="6" height="1.5" rx="0.75" fill="white" opacity="0.8"/>
      <rect x="5" y="10" width="9" height="1.5" rx="0.75" fill="white" opacity="0.5"/>
      <rect x="5" y="13" width="7" height="1.5" rx="0.75" fill="white" opacity="0.3"/>
    </svg>
  );
}
function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg style={{ width: size, height: size }} className="animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
      <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
    </svg>
  );
}
function Check() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
    </svg>
  );
}
function Play() {
  return <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>;
}
function Download() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"/>
    </svg>
  );
}
function ChevronDown() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
    </svg>
  );
}
function SparkleIcon() {
  return (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2l2.4 7.6H22l-6.4 4.6 2.4 7.6L12 17.2l-6 4.6 2.4-7.6L2 9.6h7.6z"/>
    </svg>
  );
}

// ─── Progress steps ───────────────────────────────────────────────────────────

const STEPS: { key: Stage; label: string; sub: string; icon: string }[] = [
  { key: "validating", label: "Validating URL",       sub: "Checking URL format",                          icon: "🔗" },
  { key: "capturing",  label: "Detecting sections",    sub: "Playwright analyses DOM & captures sections",  icon: "🔍" },
  { key: "analyzing",  label: "AI Storyboard",         sub: "Gemini acts as marketing video director",      icon: "✨" },
  { key: "rendering",  label: "Rendering scenes",      sub: "Building designed layouts for each scene",     icon: "🎨" },
  { key: "encoding",   label: "Encoding video",        sub: "FFmpeg Ken Burns + xfade transitions",         icon: "🎬" },
  { key: "done",       label: "Complete",              sub: "Your marketing video is ready",                icon: "✅" },
];

const STAGE_ORDER: Stage[] = [
  "idle","validating","capturing","analyzing","rendering","encoding","done","error"
];
const stageIdx = (s: Stage) => STAGE_ORDER.indexOf(s);
type StepStatus = "done" | "active" | "pending";

function ProgressStep({ label, sub, icon, status, liveMsg }:
  { label: string; sub: string; icon: string; status: StepStatus; liveMsg?: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-0.5 flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center
        transition-all duration-500 text-white text-sm
        ${status === "done"   ? "bg-emerald-500" :
          status === "active" ? "bg-indigo-500"  : "bg-white/8"}`}>
        {status === "done"   ? <Check /> :
         status === "active" ? <Spinner size={14} /> :
         <span className="text-white/20 text-xs">{icon}</span>}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium transition-colors duration-300
          ${status === "pending" ? "text-white/30" : "text-white"}`}>
          {label}
        </p>
        {status === "active" && (
          <p className="text-xs text-indigo-300/70 mt-0.5 truncate">{liveMsg || sub}</p>
        )}
      </div>
    </div>
  );
}

// ─── Stat badge ───────────────────────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center px-3 py-2 rounded-xl bg-white/5 border border-white/8">
      <span className="text-[10px] text-white/35 uppercase tracking-wider">{label}</span>
      <span className="text-sm font-semibold text-white mt-0.5">{value}</span>
    </div>
  );
}

// ─── UUID ─────────────────────────────────────────────────────────────────────

function uuid() {
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [url, setUrl]                     = useState("");
  const [geminiKey, setGeminiKey]         = useState(() => localStorage.getItem("gemini_key") || "");
  const [keySaved, setKeySaved]           = useState(false);
  const [showAdvanced, setShowAdvanced]   = useState(false);
  const [targetDuration, setTargetDuration] = useState(20);
  const [stage, setStage]                 = useState<Stage>("idle");
  const [liveMsg, setLiveMsg]             = useState("");
  const [progress, setProgress]           = useState(0);
  const [errorMsg, setErrorMsg]           = useState("");
  const [videoUrl, setVideoUrl]           = useState("");
  const [meta, setMeta]                   = useState<VideoMeta | null>(null);
  const [playing, setPlaying]             = useState(false);
  const videoRef  = useRef<HTMLVideoElement>(null);
  const pollRef   = useRef<ReturnType<typeof setInterval> | null>(null);

  const isLoading = !["idle","done","error"].includes(stage);

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

  async function handleGenerate() {
    if (!url.trim() || isLoading) return;

    const sid = uuid();
    setStage("validating"); setProgress(5);
    setLiveMsg(""); setErrorMsg(""); setVideoUrl(""); setMeta(null);

    startPolling(sid);

    try {
      const res = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          session_id: sid,
          target_duration: targetDuration,
          gemini_api_key: geminiKey.trim() || undefined,
        }),
      });

      stopPolling();
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d?.detail ?? `Server error ${res.status}`);
      }

      const data: GenerateResult = await res.json();
      setVideoUrl(`/${data.video}`);
      setMeta({
        duration: data.duration,
        resolution: data.resolution,
        fps: data.fps,
        scenes: data.scenes,
        website_type: data.storyboard?.website_type ?? "saas",
        video_style: data.storyboard?.video_style ?? "explainer",
        ai_used: data.ai_used ?? false,
      });
      setProgress(100); setStage("done");
    } catch (err: unknown) {
      stopPolling();
      setErrorMsg(err instanceof Error ? err.message : "Unknown error.");
      setStage("error");
    }
  }

  function stepStatus(key: Stage): StepStatus {
    if (stage === "error") return "pending";
    const cur = stageIdx(stage), tgt = stageIdx(key);
    if (cur > tgt) return "done";
    if (cur === tgt) return "active";
    return "pending";
  }

  const sliderPct = ((targetDuration - 8) / 22) * 100;

  return (
    <div className="min-h-screen bg-[#070712] flex flex-col">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-10 border-b border-white/[0.07]
        bg-[#070712]/80 backdrop-blur-xl px-6 py-3.5 flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600
            flex items-center justify-center">
            <LogoIcon />
          </div>
          <span className="text-base font-bold tracking-tight text-white">Promoly</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/15 text-indigo-300
            font-medium border border-indigo-500/20 flex items-center gap-1.5">
            <SparkleIcon /> AI-Powered
          </span>
        </div>
      </header>

      {/* ── Main ──────────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col items-center px-4 py-10 gap-5 max-w-2xl mx-auto w-full">

        {/* Hero text */}
        <div className="text-center space-y-2.5 pb-1">
          <h1 className="text-3xl font-bold tracking-tight text-white leading-tight">
            Turn Any Website Into A<br/>
            <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
              Marketing Video Instantly
            </span>
          </h1>
          <p className="text-sm text-white/40 max-w-sm mx-auto">
            Gemini AI acts as the creative director. Playwright captures semantic sections.
            FFmpeg renders cinematic motion.
          </p>
        </div>

        {/* ── Input card ────────────────────────────────────────────────── */}
        <div className="w-full rounded-2xl bg-white/[0.04] border border-white/[0.08] p-5 space-y-4 shadow-2xl shadow-black/40">
          <label className="text-xs font-medium text-white/50 uppercase tracking-widest">Website URL</label>
          <div className="flex gap-2.5">
            <input
              type="text" value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleGenerate()}
              placeholder="https://stripe.com"
              disabled={isLoading}
              className="flex-1 bg-white/[0.06] border border-white/[0.10] rounded-xl px-4 py-3 text-sm
                text-white placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-indigo-500/60
                focus:border-indigo-500/40 transition disabled:opacity-40 disabled:cursor-not-allowed"
            />
            <button onClick={handleGenerate} disabled={isLoading || !url.trim()}
              className="flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-white
                bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500
                disabled:from-indigo-900 disabled:to-violet-900 disabled:cursor-not-allowed
                transition-all shadow-lg shadow-indigo-900/40 whitespace-nowrap">
              {isLoading ? <><Spinner size={15}/> Processing…</> : <><Play/> Generate</>}
            </button>
          </div>

          {/* Duration slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-white/50">Video Duration</label>
              <span className="text-xs font-semibold text-indigo-300 bg-indigo-500/15
                px-2 py-0.5 rounded-full tabular-nums">{targetDuration}s</span>
            </div>
            <input type="range" min={8} max={30} step={1} value={targetDuration}
              disabled={isLoading}
              onChange={e => setTargetDuration(Number(e.target.value))}
              className="w-full h-1.5 rounded-full appearance-none cursor-pointer disabled:cursor-not-allowed"
              style={{ background: `linear-gradient(to right,#6366f1 0%,#6366f1 ${sliderPct}%,rgba(255,255,255,0.1) ${sliderPct}%,rgba(255,255,255,0.1) 100%)` }}
            />
            <div className="flex justify-between text-[10px] text-white/25 px-0.5">
              <span>8s</span><span>15s</span><span>22s</span><span>30s</span>
            </div>
          </div>

          {/* Advanced: Gemini API key */}
          <div>
            <button onClick={() => setShowAdvanced(v => !v)}
              className="flex items-center gap-1.5 text-xs text-white/35 hover:text-white/60 transition-colors">
              <span className={`transition-transform duration-200 ${showAdvanced ? "rotate-180" : ""}`}>
                <ChevronDown/>
              </span>
              Advanced settings
              {geminiKey && (
                <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full
                  bg-violet-500/20 text-violet-300 border border-violet-500/25">
                  ✨ Gemini saved
                </span>
              )}
            </button>
            {showAdvanced && (
              <div className="mt-3 space-y-2">
                <label className="text-xs text-white/40">
                  Gemini API Key
                  <span className="ml-2 text-white/20">(optional — falls back to rule-based)</span>
                </label>
                <div className="flex gap-2">
                  <input type="password" value={geminiKey}
                    onChange={e => { setGeminiKey(e.target.value); setKeySaved(false); }}
                    placeholder="AIzaSy… ya AQ.Ab8…"
                    disabled={isLoading}
                    className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded-xl px-4 py-2.5
                      text-sm text-white placeholder-white/15 focus:outline-none focus:ring-2
                      focus:ring-indigo-500/50 transition disabled:opacity-40"
                  />
                  <button
                    onClick={() => {
                      if (geminiKey.trim()) {
                        localStorage.setItem("gemini_key", geminiKey.trim());
                        setKeySaved(true);
                      } else {
                        localStorage.removeItem("gemini_key");
                        setKeySaved(false);
                      }
                    }}
                    disabled={isLoading}
                    className="px-4 py-2.5 rounded-xl text-xs font-semibold transition-all
                      bg-indigo-600/80 hover:bg-indigo-500 text-white border border-indigo-500/30
                      disabled:opacity-40 whitespace-nowrap">
                    {keySaved ? "✓ Saved!" : "Save"}
                  </button>
                </div>
                {geminiKey && (
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] text-emerald-400/70">
                      ✓ Key saved in browser — auto-loaded on refresh
                    </p>
                    <button onClick={() => {
                      localStorage.removeItem("gemini_key");
                      setGeminiKey(""); setKeySaved(false);
                    }} className="text-[10px] text-red-400/50 hover:text-red-400 transition-colors">
                      Clear
                    </button>
                  </div>
                )}
                {!geminiKey && (
                  <p className="text-[10px] text-white/25">
                    Get a free key at <span className="text-indigo-400/70">aistudio.google.com</span>
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Progress card ──────────────────────────────────────────────── */}
        {stage !== "idle" && (
          <div className="w-full rounded-2xl bg-white/[0.04] border border-white/[0.08] p-5 space-y-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white/60 uppercase tracking-widest">Progress</span>
              <span className="text-xs font-mono text-white/40">{progress}%</span>
            </div>

            <div className="w-full h-1 rounded-full bg-white/[0.07] overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500
                transition-all duration-700 ease-out" style={{ width: `${progress}%` }}/>
            </div>

            <div className="space-y-3.5 pt-1">
              {STEPS.map(s => (
                <ProgressStep key={s.key} label={s.label} sub={s.sub} icon={s.icon}
                  status={stepStatus(s.key)} liveMsg={liveMsg}/>
              ))}
            </div>

            {stage === "error" && (
              <div className="mt-1 p-4 rounded-xl bg-red-500/10 border border-red-500/25">
                <p className="text-sm font-semibold text-red-400">Error</p>
                <p className="text-xs text-red-300/70 mt-1 leading-relaxed">{errorMsg}</p>
                <button onClick={() => setStage("idle")}
                  className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 underline">
                  Try again
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Video preview card ─────────────────────────────────────────── */}
        {videoUrl && stage === "done" && meta && (
          <div className="w-full rounded-2xl bg-white/[0.04] border border-white/[0.08] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white/60 uppercase tracking-widest">Preview</span>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300
                  border border-indigo-500/20 capitalize font-medium">{meta.video_style}</span>
                {meta.ai_used ? (
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full
                    bg-violet-500/15 text-violet-300 border border-violet-500/25 font-medium">
                    ✨ Gemini AI
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full
                    bg-white/5 text-white/35 border border-white/10 font-medium">
                    Rule-based
                  </span>
                )}
                <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full
                  bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"/>Ready
                </span>
              </div>
            </div>

            {/* 16:9 player */}
            <div className="relative group cursor-pointer rounded-xl overflow-hidden
              border border-white/15 shadow-2xl shadow-indigo-950/60"
              onClick={() => {
                if (!videoRef.current) return;
                videoRef.current.paused ? videoRef.current.play() : videoRef.current.pause();
              }}>
              <video ref={videoRef} src={videoUrl} loop playsInline
                className="w-full block" style={{ aspectRatio: "16/9" }}
                onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}/>
              {!playing && (
                <div className="absolute inset-0 flex items-center justify-center
                  bg-black/30 group-hover:bg-black/20 transition-colors">
                  <div className="w-14 h-14 rounded-full bg-white/15 backdrop-blur-sm
                    flex items-center justify-center border border-white/20 shadow-xl"><Play/></div>
                </div>
              )}
            </div>

            {/* Stats */}
            <div className="grid grid-cols-5 gap-2">
              <Stat label="Duration"   value={`${meta.duration}s`}/>
              <Stat label="Resolution" value={meta.resolution}/>
              <Stat label="FPS"        value={`${meta.fps}`}/>
              <Stat label="Scenes"     value={`${meta.scenes}`}/>
              <Stat label="Type"       value={meta.website_type}/>
            </div>

            <a href={videoUrl} download="promoly_video.mp4"
              className="flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm
                font-semibold text-white bg-gradient-to-r from-indigo-600 to-violet-600
                hover:from-indigo-500 hover:to-violet-500 transition-all shadow-lg shadow-indigo-900/40">
              <Download/> Download MP4
            </a>

            <button onClick={() => { setStage("idle"); setVideoUrl(""); setMeta(null); setUrl(""); setProgress(0); }}
              className="w-full text-xs text-white/30 hover:text-white/60 transition-colors py-1">
              Generate another →
            </button>
          </div>
        )}
      </main>

      <footer className="border-t border-white/[0.06] px-6 py-3 text-center">
        <p className="text-xs text-white/15">
          Promoly — Gemini Director · Playwright Capture · FFmpeg Renderer
        </p>
      </footer>
    </div>
  );
}
