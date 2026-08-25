// WebSocket client for the Rex Python bridge (127.0.0.1).
// Streams live events: request -> stt -> wake -> agent -> result.
//
// In the browser / Electron, the native WebSocket global is used.
// In plain Node, set globalThis.WebSocket (Node 21+) or install `ws`
// and assign globalThis.WebSocket = (await import('ws')).WebSocket.

export class RexClient {
  constructor({ wsPort = 8765, httpPort = 8766, host = "127.0.0.1" } = {}) {
    this.wsUrl = `ws://${host}:${wsPort}`;
    this.httpBase = `http://${host}:${httpPort}`;
    this.ws = null;
    this.listeners = new Set();
  }

  onEvent(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        const WS = globalThis.WebSocket;
        if (!WS) {
          reject(new Error("WebSocket unavailable: set globalThis.WebSocket (Node 21+) or `npm i ws`."));
          return;
        }
        this.ws = new WS(this.wsUrl);
        this.ws.onopen = () => resolve();
        this.ws.onerror = (e) => reject(e);
        this.ws.onmessage = (ev) => {
          let data;
          try { data = JSON.parse(ev.data); } catch { return; }
          this.listeners.forEach((fn) => fn(data));
        };
      } catch (err) {
        reject(err);
      }
    });
  }

  async listenOnce() {
    const res = await fetch(`${this.httpBase}/listen`, { method: "POST" });
    return res.json();
  }

  async command(text) {
    const res = await fetch(`${this.httpBase}/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    return res.json();
  }
}
