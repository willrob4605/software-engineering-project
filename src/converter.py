"""
converter.py  –  PDF to Audiobook · TTS Conversion Engine
Wraps pyttsx3 and provides voice enumeration + audio file generation.
"""

from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field
import threading

try:
    import pyttsx3
    PYTTSX3_OK = True
except ImportError:
    PYTTSX3_OK = False


class TTSError(Exception):
    """Raised when TTS initialisation or conversion fails."""


@dataclass
class Voice:
    id: str
    name: str
    languages: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return self.name


_voice_cache: list[Voice] | None = None
_cache_lock = threading.Lock()


def list_voices(english_only: bool = True) -> list[Voice]:
    """
    Return available TTS voices (cached after first call).

    Parameters
    ----------
    english_only : If True, filter to voices whose language list contains 'en'.
                   Falls back to all voices if filtering yields nothing.
    """
    global _voice_cache
    with _cache_lock:
        if _voice_cache is not None:
            return _voice_cache

        if not PYTTSX3_OK:
            return []

        try:
            eng = pyttsx3.init()
            raw = eng.getProperty("voices") or []
            eng.stop()
        except Exception:
            return []

        voices = [Voice(v.id, v.name, list(v.languages or [])) for v in raw]

        if english_only:
            en = [v for v in voices if any("en" in str(lang).lower()
                                            for lang in v.languages)]
            voices = en if en else voices

        _voice_cache = voices[:50]          # safety cap
        return _voice_cache


def default_voice_id() -> str | None:
    """Return the voice id of the preferred US English voice, or None."""
    voices = list_voices()
    # prefer voices whose name contains "America" or "United States"
    for v in voices:
        if any(k in v.name for k in ("America)", "United States", "Zira", "David")):
            return v.id
    return voices[0].id if voices else None


def convert_to_audio(text: str,
                     output_path: str | Path,
                     voice_id: str | None = None,
                     speed_wpm: int = 150,
                     volume: float = 1.0) -> Path:
    """
    Convert *text* to a WAV audio file at *output_path*.

    Parameters
    ----------
    text        : The text to synthesise.
    output_path : Destination .wav file path.
    voice_id    : pyttsx3 voice id.  None uses the system default.
    speed_wpm   : Words-per-minute rate (60 – 280).
    volume      : 0.0 – 1.0.

    Returns
    -------
    Path to the created WAV file.

    Raises
    ------
    TTSError on any failure.
    """
    if not PYTTSX3_OK:
        raise TTSError(
            "pyttsx3 is not installed.\n"
            "Run:  pip install pyttsx3\n"
            "On Linux you also need espeak-ng:  sudo apt install espeak-ng"
        )

    if not text.strip():
        raise TTSError("No text provided for conversion.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    speed_wpm = max(60, min(280, speed_wpm))
    volume    = max(0.0, min(1.0, volume))

    try:
        engine = pyttsx3.init()

        if voice_id:
            engine.setProperty("voice", voice_id)
        engine.setProperty("rate",   speed_wpm)
        engine.setProperty("volume", volume)

        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
        engine.stop()
    except Exception as exc:
        raise TTSError(f"TTS engine error: {exc}") from exc

    if not output_path.exists() or output_path.stat().st_size < 100:
        raise TTSError(
            "Audio file was not created or is empty.\n"
            "Make sure espeak-ng is installed:  sudo apt install espeak-ng"
        )

    return output_path
