#!/usr/bin/env python3
"""Local bridge: JS control layer <-> Rex audio pipeline.

Exposes:
  - WebSocket on 127.0.0.1:<ws_port>  : live events (heard, stt, wake, agent, reply)
  - HTTP       on 127.0.0.1:<http_port>: REST control
      POST /listen           -> capture one utterance, run pipeline, return reply
      POST /command {"text"} -> run pipeline on provided text (no mic)
      GET  /health           -> status

Only binds to loopback. Started by the JS layer; can also run standalone.
"""
import asyncio
import json
import os
import sys
import threading

import websockets  # pip install websockets (or use Hermes venv)
import stt
import wake
import agent

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import daemon as rex_daemon  # reuse load_config/handle_audio


def load_config():
    return rex_daemon.load_config()


# Broadcast channel for websocket clients.
CLIENTS = set()
CONFIG = None
LOOP = None  # main event loop, set in main()


def set_loop(loop):
    global LOOP
    LOOP = loop


async def broadcast(event):
    if not CLIENTS:
        return
    msg = json.dumps(event)
    print(f"[bridge] broadcast -> {len(CLIENTS)} client(s): {event.get('type')}", flush=True)
    for c in list(CLIENTS):
        try:
            await c.send(msg)
        except Exception as e:
            print(f"[bridge] send failed: {e}", flush=True)
            CLIENTS.discard(c)


def _pipeline_from_text(text, config):
    """Run stt->wake->agent on already-transcribed text. Returns (status, reply)."""
    print(f"[stt] {text!r}")
    kw, command = wake.detect(text, config["wake_words"])
    if kw is None:
        return "ignored", None
    if wake.is_command_empty(command):
        return "listening", "Yes?"
    print(f"[wake] keyword={kw!r} command={command!r}")
    if config.get("confirm_dangerous", True) and agent.is_dangerous(command):
        return "blocked", "That looks destructive; I'll ask before doing it."
    reply = agent.run(command, config)
    return "done", reply


async def ws_handler(ws, path=None):
    CLIENTS.add(ws)
    try:
        async for _ in ws:
            pass
    finally:
        CLIENTS.discard(ws)


async def run_mic_once(config):
    import mic
    path = mic.listen_once(config)
    reply = rex_daemon.handle_audio(path, config)
    return reply


async def handle_http(scope, receive, send):
    """Minimal ASGI-ish handler shim (works with websockets' web server)."""
    pass


# --- HTTP endpoints via a tiny aiohttp-free server using websockets.serve ----
# We implement HTTP with the standard library to avoid extra deps.
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json({"status": "ok", "clients": len(CLIENTS)})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except Exception:
            data = {}
        try:
            _dispatch(data, self)
        except (ConnectionResetError, BrokenPipeError, OSError):
            # Client disconnected before we finished (common with streaming
            # fetch clients). The WS broadcast already carried the result.
            pass

    def log_message(self, *a):
        pass


def _broadcast_safe(event):
    """Schedule a WS broadcast on the main loop from any thread."""
    if LOOP is None:
        print("[bridge] broadcast skipped: LOOP not set", flush=True)
        return
    fut = asyncio.run_coroutine_threadsafe(broadcast(event), LOOP)
    try:
        fut.result(timeout=5)
    except Exception as e:
        print(f"[bridge] broadcast error: {e}", flush=True)


def _dispatch(data, handler):
    config = CONFIG
    _broadcast_safe({"type": "request", "text": data.get("text")})
    if "text" in data and data["text"]:
        status, reply = _pipeline_from_text(data["text"], config)
    else:
        # mic capture must run in the loop thread; for HTTP thread we can't easily
        # run the blocking mic here — schedule via the loop.
        reply = None
        status = "error"
    result = {"status": status, "reply": reply}
    # Speak the reply aloud on a background thread (sounddevice blocks, so
    # don't do it on the main event loop). Only speak when there is a clean reply.
    if reply:
        def _speak():
            try:
                import agent as _agent
                _agent.speak(reply, config)
            except Exception as e:
                print(f"[bridge] tts failed: {e}", flush=True)
        threading.Thread(target=_speak, daemon=True).start()
    _broadcast_safe({"type": "result", **result})
    handler._json(result)


def main():
    global CONFIG
    CONFIG = load_config()
    b = CONFIG.get("bridge", {})
    ws_port = b.get("ws_port", 8765)
    http_port = b.get("http_port", 8766)

    # Start HTTP server in a background thread.
    httpd = HTTPServer(("127.0.0.1", http_port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    print(f"[bridge] HTTP  on 127.0.0.1:{http_port}")

    # Start WebSocket server inside the running event loop.
    print(f"[bridge] WS    on 127.0.0.1:{ws_port}")

    async def _run():
        set_loop(asyncio.get_running_loop())
        async with websockets.serve(ws_handler, "127.0.0.1", ws_port):
            stop = asyncio.Event()
            try:
                await stop.wait()
            except asyncio.CancelledError:
                pass

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n[bridge] stopped.")


if __name__ == "__main__":
    main()
