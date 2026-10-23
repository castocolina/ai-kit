// Scratch opencode spike only: never shipped and never linked by setup.
// Tests whether tool.execute.after output mutation reaches the model.

import { appendFile } from "node:fs/promises";

export const AiKitAppendSpike = async (_input: unknown) => ({
  "tool.execute.after": async (
    input: { tool?: string; args?: Record<string, unknown> } | undefined,
    output: { output?: unknown } | undefined,
  ) => {
    try {
      const log = process.env.AI_KIT_SPIKE_LOG;
      if (log) {
        await appendFile(log, `${JSON.stringify({
          tool: input?.tool,
          argKeys: Object.keys(input?.args ?? {}),
          outputType: typeof output?.output,
        })}\n`, "utf8");
      }
      if (typeof output?.output === "string") {
        output.output += "\n\nAIKIT-SPIKE-MARKER: ai-kit tool.execute.after append reached the model.";
      }
    } catch {
      // This evidence-only hook must not affect a tool call.
    }
  },
});
