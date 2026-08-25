"""Dispatch a transcribed instruction to the full Hermes agent (all tools)."""
import subprocess
import json
import os
import re

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Strip the Hermes CLI decorative box frame (╭─ ⚕ Hermes ─╮ ... ╰─╯) and
# the "Query: ..." / "Initializing agent..." / session footer lines, keeping
# the actual answer text clean for TTS and display.
_FRAME = re.compile(r"[╭╮╰╯─╴╶╵╷╞╡├┤┬┴┼═║╔╗╚╝].*\n?", re.UNICODE)
_SESSION = re.compile(r"\n(Resume this session with:.*|Session:.*|Duration:.*|Messages:.*|Initializing agent\.\.\.)", re.DOTALL)


def _clean(out):
    out = _ANSI.sub("", out)
    out = _FRAME.sub("", out)
    out = _SESSION.sub("", out)
    out = re.sub(r"Query:\s*.*", "", out)
    out = re.sub(r"\n{2,}", "\n", out).strip()
    return out


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run(command, config=None, timeout=None):
    """Run `hermes chat -q <command>` with full agent access. Returns stdout."""
    config = config or load_config()
    hermes = config["hermes_exe"]
    timeout = timeout or config.get("agent_timeout", 300)
    cmd = [hermes, "chat", "-q", command]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    return _clean(out)


# Commands that should require a spoken confirmation before executing.
DANGEROUS = ("delete", "remove", "rm ", "format", "shutdown", "kill", "drop ")


def is_dangerous(command):
    c = command.lower()
    return any(d in c for d in DANGEROUS)


def speak(text, config=None):
    """Speak `text` aloud via edge-tts (offline). Skips if speak_reply is off
    or text is empty. Raises on failure so callers can decide to swallow.
    """
    cfg = config or load_config()
    if not cfg.get("speak_reply", False) or not text:
        return
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError("TTS requested but edge_tts not installed (pip install edge-tts).")
    import asyncio
    from pathlib import Path
    tmp = Path("_rex_tts.wav")
    try:
        comm = edge_tts.Communicate(text, cfg.get("tts_voice", "en-US-ChristopherNeural"))
        asyncio.run(comm.save(str(tmp)))
        import sounddevice as sd
        import soundfile as sf
        data, sr = sf.read(str(tmp))
        sd.play(data, sr)
        sd.wait()
    finally:
        if tmp.exists():
            tmp.unlink()
