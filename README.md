# Rex

A voice wake-word layer that gives you hands-free access to your **full Hermes
agent**. Say the keyword, then your instruction — Hermes runs it with all its
tools (files, terminal, browser, computer_use). Offline, private, no cloud.

```
mic -> VAD -> offline STT (faster-whisper) -> wake gate -> hermes chat -q -> TTS reply
```

The **JS control layer** (the part you imagined as "a JavaScript system with
access to Hermes") is a real Node process. It speaks to an always-on **Python
audio daemon** over a local socket, because the audio/ML core (`faster-whisper`,
`sounddevice`) is already bundled inside Hermes's own Python venv and is far
more reliable than native audio on Node 24.

## Layout
```
rex/
  src/
    py/            # Python audio daemon + pipeline (reuses Hermes venv)
      daemon.py    # orchestrator: --selftest | --mic
      stt.py       # offline faster-whisper transcription
      wake.py      # keyword gate + command split
      agent.py     # hermes chat -q dispatch + dangerous-command guard
      mic.py       # microphone capture + voice activity detection
      bridge.py    # local HTTP/WS server the JS layer connects to
    js/            # JavaScript control layer
      cli.mjs      # entry point (starts daemon, opens control UI)
      daemon.mjs   # manages the python process + IPC
      client.mjs   # talks to the python bridge (WS)
      config.mjs   # load/merge config
  config.json      # wake words, models, safety toggles, hermes path
  samples/         # test audio clips
```

## Setup
Run the Python pieces with Hermes's own Python so the ML deps resolve:
```
C:\Users\Saura\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe src/py/daemon.py --selftest samples/sample.wav
```

Run the JS control layer (which launches and supervises the Python daemon):
```
npm install
npm start
```

## Config
See `config.json`. Key fields:
- `wake_words` — phrases that trigger the agent
- `stt_model` / `wake_model` — faster-whisper sizes
- `hermes_exe` — path to Hermes's CLI
- `speak_reply` — speak the answer back (Edge TTS)
- `confirm_dangerous` — block destructive spoken commands pending confirmation

## Safety
- Hermes runs with `approvals.mode: smart` so destructive tool calls still prompt.
- A dangerous-command guard blocks obviously destructive spoken instructions.
- The Python daemon and JS layer communicate only over `127.0.0.1`.
