// Supervise the Rex Python bridge as a child process.
// Launches Hermes's venv Python running bridge.py and keeps it alive.
import { spawn } from "node:child_process";
import { loadConfig, ROOT_DIR } from "./config.mjs";
import { join } from "node:path";

export function startPythonDaemon() {
  const config = loadConfig();
  const hermesExe = config.hermes_exe;
  const venvPy = hermesExe.replace(/hermes\.exe$/i, "python.exe");
  const bridge = join(ROOT_DIR, "src", "py", "bridge.py");

  const proc = spawn(venvPy, [bridge], {
    cwd: join(ROOT_DIR, "src", "py"),
    stdio: ["ignore", "inherit", "inherit"],
    windowsHide: true,
  });

  proc.on("exit", (code) => {
    console.error(`[rex] python bridge exited (${code}); restart logic here.`);
  });

  return proc;
}
