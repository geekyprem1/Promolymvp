"""
audio_mixer.py – FFmpeg-based audio mixer for Promoly.

Supports three modes:
  A)  Video + Music only
  B)  Video + Voiceover only
  C)  Video + Voiceover + Music (voiceover at 100%, music ducked to 8%)

Volume rules:
  • Music only:       15% volume, fade-in 2s, fade-out 2s
  • With voiceover:   Music 8%, Voiceover 100%

Audio is always trimmed to the exact video duration.
FFmpeg must be installed and available in PATH.

Returns the output path on success. On FFmpeg failure the original
video path is returned unchanged so the pipeline never crashes.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

FADE_SECONDS  = 2      # fade in + fade out duration
MUSIC_VOL     = 0.15   # music-only volume
MUSIC_DUC_VOL = 0.08   # music volume when voiceover present
VO_VOL        = 1.0    # voiceover always full volume


def _find_ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


async def _get_video_duration(video_path: Path) -> float:
    """Use ffprobe to get video duration in seconds."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        ffprobe = shutil.which("ffmpeg")  # sometimes bundled together
    if not ffprobe:
        return 0.0
    proc = await asyncio.create_subprocess_exec(
        ffprobe, "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    try:
        return float(stdout.decode().strip())
    except (ValueError, AttributeError):
        return 0.0


def _build_ffmpeg_cmd(
    video_path: Path,
    output_path: Path,
    duration: float,
    music_path: Path | None,
    voiceover_path: Path | None,
) -> list[str]:
    """
    Build FFmpeg command for audio mixing.

    Filter graph strategy:
      - Music: atrim → afade in → afade out → volume
      - Voiceover: volume (full)
      - Mix: amix (normalize=0 so levels are additive not averaged)
    """
    has_music = music_path is not None
    has_vo    = voiceover_path is not None

    music_vol = MUSIC_DUC_VOL if has_vo else MUSIC_VOL

    cmd = ["ffmpeg", "-y"]

    # Input 0: video
    cmd += ["-i", str(video_path)]

    # Input 1: music (if present) — loop so short tracks cover long videos
    if has_music:
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]

    # Input 2: voiceover (if present)
    if has_vo:
        cmd += ["-i", str(voiceover_path)]

    # ── Filter graph ──────────────────────────────────────────────────────────
    fade_out_start = max(0.0, duration - FADE_SECONDS)

    filters: list[str] = []
    mix_inputs: list[str] = ""

    if has_music:
        music_idx = 1
        # Trim to video duration, fade in, fade out, volume
        filters.append(
            f"[{music_idx}:a]"
            f"atrim=0:{duration:.3f},"
            f"afade=t=in:st=0:d={FADE_SECONDS},"
            f"afade=t=out:st={fade_out_start:.3f}:d={FADE_SECONDS},"
            f"volume={music_vol:.3f},"
            f"aresample=44100"
            f"[music]"
        )
        mix_inputs += "[music]"

    if has_vo:
        vo_idx = 2 if has_music else 1
        filters.append(
            f"[{vo_idx}:a]"
            f"volume={VO_VOL:.3f},"
            f"aresample=44100"
            f"[vo]"
        )
        mix_inputs += "[vo]"

    if has_music or has_vo:
        n_inputs = (1 if has_music else 0) + (1 if has_vo else 0)
        if n_inputs > 1:
            filters.append(
                f"{mix_inputs}amix=inputs={n_inputs}:normalize=0[aout]"
            )
            audio_label = "[aout]"
        else:
            # Single audio source — no amix needed
            audio_label = "[music]" if has_music else "[vo]"

        filter_complex = ";".join(filters)
        cmd += ["-filter_complex", filter_complex]
        cmd += ["-map", "0:v", "-map", audio_label]
    else:
        # No audio at all — just copy video stream
        cmd += ["-map", "0:v"]

    # ── Encoding settings ─────────────────────────────────────────────────────
    cmd += [
        "-c:v", "copy",          # don't re-encode video
        "-c:a", "aac",           # AAC audio
        "-b:a", "192k",
        "-ar", "44100",
        "-t", f"{duration:.3f}", # hard trim output to exact video duration
        "-movflags", "+faststart",
        str(output_path),
    ]

    return cmd


async def mix_audio(
    video_path: Path,
    music_path: Path | None = None,
    voiceover_path: Path | None = None,
) -> Path:
    """
    Mix audio into a video file using FFmpeg.

    Args:
        video_path:     Input MP4 (Remotion output, may have no audio).
        music_path:     Optional background music file.
        voiceover_path: Optional voiceover WAV/MP3.

    Returns:
        Path to the mixed output file (replaces video_path in-place).
        Returns video_path unchanged if FFmpeg is unavailable or fails.
    """
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        log.warning("[Audio] FFmpeg not found — skipping audio mix.")
        print("[Audio] FFmpeg not found — video will have no background music.", flush=True)
        return video_path

    if music_path is None and voiceover_path is None:
        log.info("[Audio] No audio sources — skipping mix.")
        return video_path

    # Validate sources exist
    if music_path and not music_path.exists():
        log.warning("[Audio] Music path missing: %s", music_path)
        music_path = None
    if voiceover_path and not voiceover_path.exists():
        log.warning("[Audio] Voiceover path missing: %s", voiceover_path)
        voiceover_path = None

    if music_path is None and voiceover_path is None:
        return video_path

    # Get exact video duration
    duration = await _get_video_duration(video_path)
    if duration <= 0:
        log.warning("[Audio] Could not determine video duration — skipping mix.")
        return video_path

    mode = "music+vo" if (music_path and voiceover_path) else ("music" if music_path else "vo")
    print(
        f"[Audio] Mixing ({mode}) — duration={duration:.1f}s  "
        f"music={music_path.name if music_path else 'none'}  "
        f"vo={voiceover_path.name if voiceover_path else 'none'}",
        flush=True,
    )

    # Write to a temp file, then replace original
    temp_path = video_path.with_suffix(".mixed.mp4")

    cmd = _build_ffmpeg_cmd(video_path, temp_path, duration, music_path, voiceover_path)
    log.info("[Audio] FFmpeg cmd: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            err = stderr.decode(errors="replace")[-600:]
            log.error("[Audio] FFmpeg failed (exit %d):\n%s", proc.returncode, err)
            print(f"[Audio] FFmpeg error — continuing without audio mix.\n{err}", flush=True)
            temp_path.unlink(missing_ok=True)
            return video_path

        # Replace original with mixed version
        temp_path.replace(video_path)
        size_mb = video_path.stat().st_size / (1024 * 1024)
        print(f"[Audio] Mix complete → {video_path.name}  ({size_mb:.1f} MB)", flush=True)
        log.info("[Audio] Final file: %s  (%.1f MB)", video_path.name, size_mb)
        return video_path

    except asyncio.TimeoutError:
        log.error("[Audio] FFmpeg timed out after 5 minutes.")
        temp_path.unlink(missing_ok=True)
        return video_path
    except Exception as exc:
        log.error("[Audio] Unexpected error: %s", exc)
        temp_path.unlink(missing_ok=True)
        return video_path
