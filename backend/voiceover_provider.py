"""
voiceover_provider.py – Pluggable voiceover architecture for Promoly.

Architecture:
  VoiceoverProvider (abstract base)
      ├── StubProvider        – no-op, returns None (current default)
      ├── KokoroProvider      – OpenRouter hexgrad/kokoro-82m TTS  ← ACTIVE
      ├── ElevenLabsProvider  – ElevenLabs TTS (stub)
      ├── OpenAITTSProvider   – OpenAI TTS (stub)
      └── GoogleTTSProvider   – Google Cloud TTS (stub)

The render pipeline in main.py calls:
    vo_path = await get_voiceover_provider().generate_voiceover(script, voice_id)
and passes vo_path to audio_mixer.mix_audio().
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

log = logging.getLogger(__name__)

OPENROUTER_TTS_URL = "https://openrouter.ai/api/v1/audio/speech"


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bit_depth: int = 16) -> bytes:
    """Wrap raw PCM bytes in a proper WAV container so FFmpeg can read it."""
    import struct
    byte_rate   = sample_rate * channels * bit_depth // 8
    block_align = channels * bit_depth // 8
    data_size   = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16,
        1,            # PCM
        channels, sample_rate, byte_rate, block_align, bit_depth,
        b"data", data_size,
    )
    return header + pcm_data

# Kokoro voices available via OpenRouter
# Female: af_heart (warm), af_nova, af_sarah, af_sky, af_bella, af_jessica
# Male:   am_echo, am_michael, am_liam, bm_george, bm_daniel
KOKORO_DEFAULT_VOICE = "af_heart"


# ── Abstract base ─────────────────────────────────────────────────────────────

class VoiceoverProvider(ABC):
    """All voiceover providers must implement this interface."""

    @abstractmethod
    async def generate_voiceover(
        self,
        script: str,
        voice_id: str | None = None,
        output_path: Path | None = None,
    ) -> Path | None:
        """
        Generate a voiceover audio file from script text.

        Args:
            script:      The narration text to synthesize.
            voice_id:    Provider-specific voice identifier.
            output_path: Where to save the audio. If None, provider chooses.

        Returns:
            Path to the generated audio file, or None if generation failed.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name for logging."""


# ── Kokoro via OpenRouter ─────────────────────────────────────────────────────

class KokoroProvider(VoiceoverProvider):
    """
    OpenRouter hexgrad/kokoro-82m TTS provider.

    Uses the OpenAI-compatible audio/speech endpoint on OpenRouter.
    The same OPENROUTER_API_KEY used for Gemini works here.

    Available voices:
      Female: af_heart, af_nova, af_sarah, af_sky, af_bella, af_jessica
      Male:   am_echo, am_michael, am_liam, bm_george, bm_daniel
    """

    MODEL = "hexgrad/kokoro-82m"

    def __init__(
        self,
        api_key: str,
        voice: str = KOKORO_DEFAULT_VOICE,
        output_dir: Path | None = None,
    ):
        self.api_key    = api_key
        self.voice      = voice
        self.output_dir = output_dir or Path("output")

    @property
    def name(self) -> str:
        return "kokoro"

    async def generate_voiceover(
        self,
        script: str,
        voice_id: str | None = None,
        output_path: Path | None = None,
    ) -> Path | None:
        import httpx

        voice = voice_id or self.voice
        if output_path is None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"vo_{uuid.uuid4().hex[:8]}.mp3"

        # Truncate very long scripts — Kokoro has a ~500 token limit
        if len(script) > 1800:
            script = script[:1800]
            print(f"[Voiceover] Script truncated to 1800 chars", flush=True)

        payload = {
            "model": self.MODEL,
            "input": script,
            "voice": voice,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://promoly.app",
            "X-Title":       "Promoly",
        }

        print(f"[Voiceover] Kokoro: {len(script)} chars, voice={voice}", flush=True)
        print(f"[Voiceover] Script preview: {script[:120]}…", flush=True)

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(OPENROUTER_TTS_URL, headers=headers, json=payload)

                print(f"[Voiceover] HTTP {resp.status_code}  content-type={resp.headers.get('content-type','?')}  bytes={len(resp.content)}", flush=True)

                if resp.status_code != 200:
                    print(f"[Voiceover] ERROR body: {resp.text[:400]}", flush=True)
                    return None

                # OpenRouter may return JSON error even with 200
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    print(f"[Voiceover] Got JSON instead of audio: {resp.text[:300]}", flush=True)
                    return None

                if len(resp.content) < 1000:
                    print(f"[Voiceover] Response too small ({len(resp.content)} bytes) — likely an error", flush=True)
                    print(f"[Voiceover] Body: {resp.text[:300]}", flush=True)
                    return None

                # Kokoro returns raw PCM — wrap in WAV so FFmpeg can read it
                if "pcm" in ct:
                    # Parse rate from content-type e.g. "audio/pcm;rate=24000;channels=1"
                    import re as _re
                    rate_m = _re.search(r"rate=(\d+)", ct)
                    ch_m   = _re.search(r"channels=(\d+)", ct)
                    sample_rate = int(rate_m.group(1)) if rate_m else 24000
                    channels    = int(ch_m.group(1))   if ch_m   else 1
                    audio_data  = _pcm_to_wav(resp.content, sample_rate, channels)
                    output_path = output_path.with_suffix(".wav")
                    print(f"[Voiceover] PCM {sample_rate}Hz ch={channels} → WAV", flush=True)
                else:
                    audio_data = resp.content

                output_path.write_bytes(audio_data)
                print(f"[Voiceover] Saved → {output_path.name}  ({len(audio_data)/1024:.1f} KB)", flush=True)
                return output_path

        except httpx.HTTPStatusError as e:
            print(f"[Voiceover] HTTP error {e.response.status_code}: {e.response.text[:300]}", flush=True)
            return None
        except httpx.TimeoutException:
            print(f"[Voiceover] Request timed out after 120s", flush=True)
            return None
        except Exception as e:
            print(f"[Voiceover] Exception: {type(e).__name__}: {e}", flush=True)
            return None


# ── Stub provider (current default — no API calls) ────────────────────────────

class StubProvider(VoiceoverProvider):
    """
    No-op provider. Returns None immediately.
    Used when no voiceover API key is configured.
    """

    @property
    def name(self) -> str:
        return "stub"

    async def generate_voiceover(
        self,
        script: str,
        voice_id: str | None = None,
        output_path: Path | None = None,
    ) -> Path | None:
        log.debug("[Voiceover] StubProvider — no voiceover generated.")
        return None


# ── ElevenLabs (architecture stub — not implemented) ─────────────────────────

class ElevenLabsProvider(VoiceoverProvider):
    """
    ElevenLabs TTS provider.

    To activate:
      1. pip install elevenlabs
      2. Pass api_key from env: ELEVENLABS_API_KEY
      3. Replace the NotImplementedError body with:
            from elevenlabs.client import AsyncElevenLabs
            client = AsyncElevenLabs(api_key=self.api_key)
            audio = await client.generate(text=script, voice=voice_id or self.default_voice)
            output_path.write_bytes(audio)
            return output_path
    """

    DEFAULT_VOICE = "Rachel"   # ElevenLabs default voice

    def __init__(self, api_key: str, default_voice: str = DEFAULT_VOICE):
        self.api_key       = api_key
        self.default_voice = default_voice

    @property
    def name(self) -> str:
        return "elevenlabs"

    async def generate_voiceover(
        self,
        script: str,
        voice_id: str | None = None,
        output_path: Path | None = None,
    ) -> Path | None:
        # TODO: implement when ElevenLabs key is available
        log.warning("[Voiceover] ElevenLabs not yet implemented.")
        raise NotImplementedError(
            "ElevenLabs provider is not yet implemented. "
            "See voiceover_provider.py for integration instructions."
        )


# ── OpenAI TTS (architecture stub — not implemented) ─────────────────────────

class OpenAITTSProvider(VoiceoverProvider):
    """
    OpenAI TTS provider (tts-1 / tts-1-hd).

    To activate:
      1. pip install openai
      2. Pass api_key from env: OPENAI_API_KEY
      3. Replace NotImplementedError with openai.audio.speech.create(...)
    """

    DEFAULT_VOICE = "nova"
    DEFAULT_MODEL = "tts-1"

    def __init__(self, api_key: str, voice: str = DEFAULT_VOICE, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.voice   = voice
        self.model   = model

    @property
    def name(self) -> str:
        return "openai-tts"

    async def generate_voiceover(
        self,
        script: str,
        voice_id: str | None = None,
        output_path: Path | None = None,
    ) -> Path | None:
        # TODO: implement when OpenAI key is available
        log.warning("[Voiceover] OpenAI TTS not yet implemented.")
        raise NotImplementedError("OpenAI TTS provider is not yet implemented.")


# ── Google TTS (architecture stub — not implemented) ─────────────────────────

class GoogleTTSProvider(VoiceoverProvider):
    """Google Cloud Text-to-Speech provider (architecture stub)."""

    @property
    def name(self) -> str:
        return "google-tts"

    async def generate_voiceover(
        self,
        script: str,
        voice_id: str | None = None,
        output_path: Path | None = None,
    ) -> Path | None:
        log.warning("[Voiceover] Google TTS not yet implemented.")
        raise NotImplementedError("Google TTS provider is not yet implemented.")


# ── Factory ───────────────────────────────────────────────────────────────────

_PROVIDERS: dict[str, type[VoiceoverProvider]] = {
    "kokoro":     KokoroProvider,
    "elevenlabs": ElevenLabsProvider,
    "openai":     OpenAITTSProvider,
    "google":     GoogleTTSProvider,
    "stub":       StubProvider,
}


def get_voiceover_provider(
    provider_name: str = "kokoro",
    api_key: str | None = None,
    **kwargs,
) -> VoiceoverProvider:
    """
    Factory function. Returns a VoiceoverProvider instance.

    Default provider is "kokoro" (OpenRouter hexgrad/kokoro-82m).
    Falls back to stub if no API key is available.
    """
    cls = _PROVIDERS.get(provider_name, StubProvider)

    if cls is StubProvider:
        return StubProvider()

    if not api_key:
        log.warning("[Voiceover] No API key for %s — falling back to stub.", provider_name)
        return StubProvider()

    try:
        return cls(api_key=api_key, **kwargs)
    except Exception as exc:
        log.error("[Voiceover] Failed to init %s: %s — using stub.", provider_name, exc)
        return StubProvider()
