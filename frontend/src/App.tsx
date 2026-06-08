import { useState, useRef, useEffect, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Stage = "idle" | "validating" | "capturing" | "generating" | "done" | "error";

interface ProgressResponse {
  stage: string;
  pct: number;
  message: string;
}

interface GenerateResult {
  status: string;
  video: string;
  session_id: string;
  duration: number;
  resolution: string;
  fps: number;
  scenes: number;
  page_text: Record<string, string>;
}

interface VideoMeta {
  url: string;
  duration: number;
  resolution: string;
  fps: number;
  scenes: number;
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function LogoIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="3" width="15" height="14" rx="2" fill="#6366f1" />
      <path d="M17 8l5 4-5 4V8z" fill="#a5b4fc" />
      <rect x="5" y="7" width="6" height="1.5" rx="0.75" fill="white" opacity="0.8" />
      <rect x="5" y="10" width="9" height="1.5" rx="0.75" fill="white" opacity="0.5" />
      <rect x="5" y="13" width="7" height="1.5" rx="0.75" fill="white" opacity="0.3" />
    </svg>
  );
}

function SpinnerIcon({ size = 16 }: { size?: number }) {
  return (
    <svg
      style={{ width: size, height: size }}
      className="animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

// ─── Progress step ────────────────────────────────────────────────────────────

type StepStatus = "done" | "active" | "pending";

const STEPS: { key: Stage; label: string; sub: string }[] = [
  { key: "validating", label: "Validating URL",        sub: "Checking URL format" },
  { key: "capturing",  label: "Capturing screenshots", sub: "Playwright auto-scrolls and captures 6 sections" },
  { key: "generating", label: "Generating video",      sub: "Ken Burns • xfade transitions • text overlays" },
  { key: "done",       label: "Complete",              sub: "Your marketing reel is ready" },
];

const STAGE_ORDER: Stage[] = ["idle", "validating", "capturing", "generating", "done", "error"];
const stageIdx = (s: Stage) => STAGE_ORDER.indexOf(s);

function ProgressStep({
  label, sub, status, liveMsg,
}: { label: string; sub: string; status: StepStatus; liveMsg?: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-0.5 flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center
        transition-all duration-500 text-white
        ${status === "done"   ? "bg-emerald-500" :
          status === "active" ? "bg-indigo-500"  : "bg-white/10"}`}>
        {status === "done"   ? <CheckIcon /> :
         status === "active" ? <SpinnerIcon size={14} /> :
         <span className="w-1.5 h-1.5 rounded-full bg-white/20" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium transition-colors duration-300
          ${status === "pending" ? "text-white/35" : "text-white"}`}>
          {label}
        </p>
        {status === "active" && (
          <p className="text-xs text-indigo-300/70 mt-0.5 truncate">
            {liveMsg || sub}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Stat badge ───────────────────────────────────────────────────────────────

function StatBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center px-4 py-2 rounded-xl bg-white/5 border border-white/10">
      <span className="text-xs text-white/40 uppercase tracking-wider">{label}</span>
      <span className="text-sm font-semibold text-white mt-0.5">{value}</span>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

function generateUUID(): string {
  return "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx".replace(/x/g, () =>
    Math.floor(Math.random() * 16).toString(16)
  ).replace(/-/g, "");
}

export default function App() {
  const [url, setUrl]             = useState("");
  const [targetDuration, setTargetDuration] = useState(20);
  const [stage, setStage]         = useState<Stage>("idle");
  const [liveMsg, setLiveMsg]     = useState("");
  const [progress, setProgress]   = useState(0);
  const [errorMsg, setErrorMsg]   = useState("");
  const [videoUrl, setVideoUrl]   = useState("");
  const [meta, setMeta]           = useState<VideoMeta | null>(null);
  const [playing, setPlaying]     = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const pollRef  = useRef<ReturnType<typeof setInterval> | null>(null);

  const isLoading = stage === "validating" || stage === "capturing" || stage === "generating";

  // Map server stage string → UI stage
  const mapServerStage = (s: string): Stage => {
    if (s === "validating") return "validating";
    if (s === "capturing")  return "capturing";
    if (s === "generating") return "generating";
    if (s === "done")       return "done";
    return "generating";
  };

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
  }, []);

  const startPolling = useCallback((sid: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/progress/${sid}`);
        const data: ProgressResponse = await res.json();
        if (data.pct > 0) {
          setProgress(data.pct);
          setStage(mapServerStage(data.stage));
          if (data.message) setLiveMsg(data.message);
        }
      } catch {/* ignore */}
    }, 1200);
  }, [stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  async function handleGenerate() {
    if (!url.trim() || isLoading) return;

    const sid = generateUUID();
    setStage("validating");
    setProgress(5);
    setLiveMsg("");
    setErrorMsg("");
    setVideoUrl("");
    setMeta(null);

    startPolling(sid);

    try {
      const res = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), session_id: sid, target_duration: targetDuration }),
      });

      stopPolling();

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail ?? `Server error ${res.status}`);
      }

      const data: GenerateResult = await res.json();
      setVideoUrl(`/${data.video}`);
      setMeta({
        url: url.trim(),
        duration: data.duration,
        resolution: data.resolution,
        fps: data.fps,
        scenes: data.scenes,
      });
      setProgress(100);
      setStage("done");
    } catch (err: unknown) {
      stopPolling();
      setErrorMsg(err instanceof Error ? err.message : "Unknown error occurred.");
      setStage("error");
    }
  }

  function stepStatus(key: Stage): StepStatus {
    if (stage === "error") return "pending";
    const cur = stageIdx(stage);
    const tgt = stageIdx(key);
    if (cur > tgt) return "done";
    if (cur === tgt) return "active";
    return "pending";
  }

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) { videoRef.current.play(); setPlaying(true); }
    else { videoRef.current.pause(); setPlaying(false); }
  };

  return (
    <div className="min-h-screen bg-[#080810] flex flex-col">

      {/* ── Header ── */}
      <header className="sticky top-0 z-10 border-b border-white/[0.07] bg-[#080810]/80 backdrop-blur-xl px-6 py-3.5 flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600">
            <LogoIcon />
          </div>
          <span className="text-base font-bold tracking-tight text-white">Promoly</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/15 text-indigo-300 font-medium border border-indigo-500/20">
            Beta
          </span>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="flex-1 flex flex-col items-center px-4 py-10 gap-6 max-w-2xl mx-auto w-full">

        {/* Hero */}
        <div className="text-center space-y-2 pb-2">
          <h1 className="text-3xl font-bold tracking-tight text-white leading-tight">
            Turn Any Website Into A<br />
            <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
              Marketing Video Instantly
            </span>
          </h1>
          <p className="text-sm text-white/40 max-w-sm mx-auto">
            Paste a URL. Get a cinematic 9:16 promo reel with Ken Burns effects, smooth transitions, and text overlays.
          </p>
        </div>

        {/* ── URL Input card ── */}
        <div className="w-full rounded-2xl bg-white/[0.04] border border-white/[0.08] p-5 space-y-3 shadow-2xl shadow-black/40">
          <label className="text-xs font-medium text-white/50 uppercase tracking-widest">Website URL</label>
          <div className="flex gap-2.5">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
              placeholder="https://stripe.com"
              disabled={isLoading}
              className="flex-1 bg-white/[0.06] border border-white/[0.10] rounded-xl px-4 py-3 text-sm text-white
                placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500/40
                transition disabled:opacity-40 disabled:cursor-not-allowed"
            />
            <button
              onClick={handleGenerate}
              disabled={isLoading || !url.trim()}
              className="flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-white
                bg-gradient-to-r from-indigo-600 to-violet-600
                hover:from-indigo-500 hover:to-violet-500
                disabled:from-indigo-900 disabled:to-violet-900 disabled:cursor-not-allowed
                transition-all duration-200 shadow-lg shadow-indigo-900/40 whitespace-nowrap"
            >
              {isLoading ? (
                <><SpinnerIcon size={15} /> Processing…</>
              ) : (
                <><PlayIcon /> Generate Video</>
              )}
            </button>
          </div>
          {/* Duration slider */}
          <div className="space-y-2 pt-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-white/50">Video Duration</label>
              <span className="text-xs font-semibold tabular-nums text-indigo-300 bg-indigo-500/15 px-2 py-0.5 rounded-full">
                {targetDuration}s
              </span>
            </div>
            <div className="relative">
              <input
                type="range"
                min={8}
                max={30}
                step={1}
                value={targetDuration}
                disabled={isLoading}
                onChange={(e) => setTargetDuration(Number(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none cursor-pointer disabled:cursor-not-allowed
                  bg-white/10 accent-indigo-500"
                style={{
                  background: `linear-gradient(to right, #6366f1 0%, #6366f1 ${((targetDuration - 8) / 22) * 100}%, rgba(255,255,255,0.1) ${((targetDuration - 8) / 22) * 100}%, rgba(255,255,255,0.1) 100%)`
                }}
              />
              <div className="flex justify-between text-[10px] text-white/25 mt-1 px-0.5">
                <span>8s</span>
                <span>15s</span>
                <span>22s</span>
                <span>30s</span>
              </div>
            </div>
          </div>

          <p className="text-xs text-white/25">
            Works on any public website — Playwright auto-scrolls and captures key sections.
          </p>
        </div>

        {/* ── Progress card ── */}
        {stage !== "idle" && (
          <div className="w-full rounded-2xl bg-white/[0.04] border border-white/[0.08] p-5 space-y-5">
            {/* Header row */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white/60 uppercase tracking-widest">Progress</span>
              <span className="text-xs font-mono text-white/40">{progress}%</span>
            </div>

            {/* Progress bar */}
            <div className="w-full h-1 rounded-full bg-white/[0.08] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>

            {/* Steps */}
            <div className="space-y-4 pt-1">
              {STEPS.map((s) => (
                <ProgressStep
                  key={s.key}
                  label={s.label}
                  sub={s.sub}
                  status={stepStatus(s.key)}
                  liveMsg={liveMsg}
                />
              ))}
            </div>

            {/* Error */}
            {stage === "error" && (
              <div className="mt-1 p-4 rounded-xl bg-red-500/10 border border-red-500/25">
                <p className="text-sm font-semibold text-red-400">Error</p>
                <p className="text-xs text-red-300/70 mt-1 leading-relaxed">{errorMsg}</p>
                <button
                  onClick={() => setStage("idle")}
                  className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 underline"
                >
                  Try again
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Video preview card ── */}
        {videoUrl && stage === "done" && meta && (
          <div className="w-full rounded-2xl bg-white/[0.04] border border-white/[0.08] p-5 space-y-5">
            {/* Title row */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white/60 uppercase tracking-widest">Preview</span>
              <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full
                bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Ready
              </span>
            </div>

            {/* Player — landscape 16:9 */}
            <div
              className="relative group cursor-pointer rounded-xl overflow-hidden
                border border-white/15 shadow-2xl shadow-indigo-950/60"
              onClick={togglePlay}
            >
              <video
                ref={videoRef}
                src={videoUrl}
                loop
                playsInline
                className="w-full block"
                style={{ aspectRatio: "16/9" }}
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
              />
              {!playing && (
                <div className="absolute inset-0 flex items-center justify-center
                  bg-black/30 group-hover:bg-black/20 transition-colors">
                  <div className="w-14 h-14 rounded-full bg-white/15 backdrop-blur-sm
                    flex items-center justify-center border border-white/20 shadow-xl">
                    <PlayIcon />
                  </div>
                </div>
              )}
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-4 gap-2">
              <StatBadge label="Duration"   value={`${meta.duration}s`} />
              <StatBadge label="Resolution" value={meta.resolution} />
              <StatBadge label="FPS"        value={`${meta.fps}`} />
              <StatBadge label="Scenes"     value={`${meta.scenes}`} />
            </div>

            {/* Download */}
            <a
              href={videoUrl}
              download="promoly_video.mp4"
              className="flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm font-semibold
                text-white bg-gradient-to-r from-indigo-600 to-violet-600
                hover:from-indigo-500 hover:to-violet-500 transition-all duration-200
                shadow-lg shadow-indigo-900/40"
            >
              <DownloadIcon />
              Download MP4
            </a>

            {/* Generate another */}
            <button
              onClick={() => { setStage("idle"); setVideoUrl(""); setMeta(null); setUrl(""); setProgress(0); }}
              className="w-full text-xs text-white/35 hover:text-white/60 transition-colors py-1"
            >
              Generate another →
            </button>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-white/[0.06] px-6 py-3 text-center">
        <p className="text-xs text-white/15">Promoly — Local MVP · No cloud, no auth, no limits</p>
      </footer>
    </div>
  );
}
