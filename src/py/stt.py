"""Offline speech-to-text using Hermes's bundled faster-whisper."""
import faster_whisper as fw

_CACHE = {}


def get_model(size="base", device="cpu", compute_type="int8"):
    key = (size, device, compute_type)
    if key not in _CACHE:
        _CACHE[key] = fw.WhisperModel(size, device=device, compute_type=compute_type)
    return _CACHE[key]


def transcribe(path, size="base", language="en"):
    """Return transcribed text from an audio file (wav/mp3)."""
    model = get_model(size)
    segs, _info = model.transcribe(path, beam_size=5, language=language)
    return " ".join(s.text for s in segs).strip()
