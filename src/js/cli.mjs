// Rex control-layer entry point.
// Starts the Python audio bridge, connects over WebSocket, prints live events.
import { startPythonDaemon } from "./daemon.mjs";
import { RexClient } from "./client.mjs";
import { loadConfig } from "./config.mjs";

const config = loadConfig();
const bridge = config.bridge || {};

console.log("[rex] starting Python audio bridge...");
const py = startPythonDaemon();

const client = new RexClient({
  wsPort: bridge.ws_port ?? 8765,
  host: bridge.host ?? "127.0.0.1",
});

async function main() {
  await new Promise((r) => setTimeout(r, 1500));
  try {
    await client.connect();
  } catch (err) {
    console.error("[rex] could not connect to bridge:", err.message);
    console.error("[rex] is the Python venv python reachable? Check config.hermes_exe.");
    process.exit(1);
  }

  client.onEvent((ev) => {
    const tag = (ev.type || "event").toUpperCase();
    if (ev.type === "result") {
      console.log(`[result] status=${ev.status}`);
      if (ev.reply) console.log(`  Hermes: ${ev.reply}`);
    } else if (ev.type === "request") {
      console.log(`[request] ${ev.text ?? "(mic)"}`);
    } else {
      console.log(`[${tag}] ${JSON.stringify(ev)}`);
    }
  });

  console.log("[rex] ready. Say your wake word (live mic needs --mic mode),");
  console.log("[rex] or trigger a command programmatically:");
  console.log('  client.command("hey hermes, what is 2 plus 2")');

  const arg = process.argv.slice(2).join(" ").trim();
  if (arg) {
    const res = await client.command(arg);
    console.log("Reply:", res.reply ?? res);
  }

  process.on("SIGINT", () => {
    console.log("\n[rex] shutting down.");
    py.kill();
    process.exit(0);
  });
}

main();
