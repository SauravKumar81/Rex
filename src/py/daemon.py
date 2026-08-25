#!/usr/bin/env python3
"""Rex Python daemon: wake word -> offline STT -> Hermes agent.

Modes (standalone):
  python daemon.py --selftest sample.wav   # prove the STT+gate+agent chain
  python daemon.py --mic                   # live always-on listener (needs mic)

Bridge mode (used by the JS control layer):
  python bridge.py                          # starts WS+HTTP server on 127.0.0.1
"""
import argparse
import json
import os
import sys

import stt
import wake
import agent

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(HERE, "..", "..", "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def handle_audio(path, config):
    text = stt.transcribe(path, size=config["stt_model"], language=config["language"])
    print(f"[stt] {text!r}")
    kw, command = wake.detect(text, config["wake_words"])
    if kw is None:
        print("[wake] no wake word detected, ignoring.")
        return None
    if wake.is_command_empty(command):
        print("[wake] wake word heard but no command.")
        return "Yes?"
    print(f"[wake] keyword={kw!r} command={command!r}")
    if config.get("confirm_dangerous", True) and agent.is_dangerous(command):
        print("[safe] dangerous command blocked pending confirmation.")
        reply = "That looks destructive; I'll ask before doing it."
        agent.speak(reply, config)
        return reply
    reply = agent.run(command, config)
    print(f"[agent] returned {len(reply)} chars")
    agent.speak(reply, config)
    return reply


def selftest(wav_path, config):
    if not os.path.exists(wav_path):
        print(f"selftest: file not found: {wav_path}")
        return 1
    handle_audio(wav_path, config)
    return 0


def live(config):
    import mic
    print("[daemon] starting always-on listener. Ctrl+C to stop.")
    while True:
        try:
            path = mic.listen_once(config)
            handle_audio(path, config)
        except KeyboardInterrupt:
            print("\n[daemon] stopped.")
            break
        except Exception as e:
            print(f"[daemon] error: {e}")


def main():
    ap = argparse.ArgumentParser(description="Rex wake-word daemon")
    ap.add_argument("--selftest", metavar="WAV", help="run pipeline on a WAV file")
    ap.add_argument("--mic", action="store_true", help="live always-on listener")
    args = ap.parse_args()
    config = load_config()
    if args.selftest:
        sys.exit(selftest(args.selftest, config))
    elif args.mic:
        live(config)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
