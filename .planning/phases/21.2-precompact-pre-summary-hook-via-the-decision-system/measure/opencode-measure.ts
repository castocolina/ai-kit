// Measure-only opencode plugin (21.2 D-17). Logs the compacting hook and the
// session.compacted event to AI_KIT_MEASURE_LOG; never touches `output`.
// Erasable TypeScript only (type annotations and `import type`).
import { appendFileSync } from "node:fs";

function log(event: string, data: Record<string, unknown>): void {
  const file = process.env.AI_KIT_MEASURE_LOG;
  if (!file) return;
  const line = JSON.stringify({
    ts_wall: new Date().toISOString(),
    ts_mono_ns: process.hrtime.bigint().toString(),
    event,
    ...data,
  }) + "\n";
  try {
    appendFileSync(file, line);
  } catch {
    // measurement must never break the session
  }
}

export const AiKitMeasure = async (_ctx: any) => ({
  "experimental.session.compacting": async (_input: any, _output: any) => {
    log("experimental.session.compacting", {
      sessionID: _input?.sessionID ?? null,
    });
    // never touch output
  },
  event: async (e: any) => {
    if (e?.type === "session.compacted") {
      log("session.compacted", {
        sessionID: e?.properties?.info?.sessionID ?? e?.properties?.sessionID ?? null,
      });
    }
  },
});
