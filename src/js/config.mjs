// Load and expose Rex config (mirrors config.json at repo root).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..", "..");

export function loadConfig() {
  const raw = readFileSync(join(ROOT, "config.json"), "utf8");
  return JSON.parse(raw);
}

export const ROOT_DIR = ROOT;
