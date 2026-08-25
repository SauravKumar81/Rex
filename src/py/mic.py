"""Microphone capture + voice activity detection (VAD) using sounddevice."""
import os
import tempfile

try:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
    _HAVE_AUDIO = True
except Exception as e:
    _HAVE_AUDIO = False
    _IMPORT_ERR = e


def listen_once(config):
    """Record until silence, return path to a WAV file."""
    if not _HAVE_AUDIO:
        raise RuntimeError(f"Audio deps missing: {_IMPORT_ERR}")
    samplerate = int(config.get("samplerate", 16000))
    threshold = float(config.get("speech_threshold", 0.012))
    silence = float(config.get("silence_seconds", 1.2))

    recording = []
    silent_for = 0.0
    block = int(samplerate * 0.2)
    print("[mic] listening...")
    with sd.InputStream(samplerate=samplerate, channels=1, blocksize=block) as stream:
        while True:
            data, _ = stream.read(block)
            amp = float(np.abs(data).max()) if data.size else 0.0
            recording.append(data)
            if amp < threshold:
                silent_for += block / samplerate
                if silent_for >= silence and len(recording) > 5:
                    break
            else:
                silent_for = 0.0
    audio = np.concatenate(recording, axis=0)
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="rex_")
    os.close(fd)
    sf.write(path, audio, samplerate)
    return path
