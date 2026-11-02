// Measure-only pi extension (21.2 D-17). Logs compaction events to
// AI_KIT_MEASURE_LOG; never returns a compaction, so pi's default flow runs.
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

export default function main(pi: any): void {
  pi.on("session_before_compact", (event: any, _ctx: any) => {
    const prep = event?.preparation ?? {};
    log("session_before_compact", {
      reason: event?.reason ?? null,
      tokensBefore: prep.tokensBefore ?? null,
      messages: Array.isArray(prep.messagesToSummarize) ? prep.messagesToSummarize.length : null,
      previousSummary: typeof prep.previousSummary === "string" ? prep.previousSummary.length : null,
    });
    return undefined;
  });
  pi.on("session_compact", (event: any, ctx: any) => {
    log("session_compact", {
      entry: event?.compaction ?? null,
      usage: event?.usage ?? null,
      contextUsage: ctx?.getContextUsage?.() ?? null,
    });
  });
}
