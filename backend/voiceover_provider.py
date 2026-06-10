"""
voiceover_provider.py – Pluggable voiceover architecture for Promoly.

Architecture:
  VoiceoverProvider (abstract base)
      ├── StubProvider        – no-op, returns None (current default)
      ├── ElevenLabsProvider  – ElevenLabs TTS (not yet implemented)
      ├── OpenAITTSProvider   – OpenAI TTS (not yet implemented)
      └── GoogleTTSProvider   – Google Cloud TTS (not yet implemented)

Usage (when ready):
    provider = ElevenLabsProvider(api_key="...")
    path = await provider.generate_voiceover(script="...", voice_id="...")

The render pipeline in main.py calls:
    vo_path = await get_voiceover_provider().generate_voiceover(script, voice_id)
and passes vo_path to audio_mixer.mix_audio(). Swapping providers never
requires changing the pipeline.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

log = logging.getLogger(__name__)


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
    "elevenlabs": ElevenLabsProvider,
    "openai":     OpenAITTSProvider,
    "google":     GoogleTTSProvider,
    "stub":       StubProvider,
}


def get_voiceover_provider(
    provider_name: str = "stub",
    api_key: str | None = None,
    **kwargs,
) -> VoiceoverProvider:
    """
    Factory function. Returns a VoiceoverProvider instance.

    Args:
        provider_name: "stub" | "elevenlabs" | "openai" | "google"
        api_key:       API key for the provider (ignored for stub).
        **kwargs:      Extra options passed to provider __init__.

    Examples:
        get_voiceover_provider("stub")
        get_voiceover_provider("elevenlabs", api_key=os.getenv("ELEVENLABS_API_KEY"))
        get_voiceover_provider("openai",     api_key=os.getenv("OPENAI_API_KEY"), voice="nova")
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
