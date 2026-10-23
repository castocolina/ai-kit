// pi tool_result reminder: append a post-tool reminder after the untouched bash result.
// No tool_call handler on purpose: failures there can block execution. This is one
// self-contained link because pi loads every extension file; helpers repeat on purpose.
// Erasable TypeScript only, with node built-ins and no npm or host-package imports.
import { spawn } from "node:child_process";
import { realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const TIMEOUT_MS = 2000;

function corePath(): string | undefined {
  let here: string | undefined;
  try {
    here = fileURLToPath(import.meta.url);
  } catch {
    const globalFilename = (globalThis as { __filename?: unknown }).__filename;
    here = typeof globalFilename === "string" ? globalFilename : undefined;
  }
  if (here === undefined) return undefined;
  try {
    return join(dirname(realpathSync(here)), "..", "advisor_core.py");
  } catch {
    return undefined;
  }
}

function runCore(core: string, input: string): Promise<Record<string, unknown> | undefined> {
  return new Promise((resolve) => {
    let child;
    let stdout = "";
    let settled = false;
    let timer;
    const finish = (value: Record<string, unknown> | undefined) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(value);
    };
    try {
      child = spawn(process.env.AI_KIT_PYTHON || "python3", ["-S", core, "pi"],
                    { stdio: ["pipe", "pipe", "ignore"] });
    } catch {
      resolve(undefined);
      return;
    }
    timer = setTimeout(() => {
      try { child.kill("SIGKILL"); } catch { /* already exited */ }
    }, TIMEOUT_MS);
    child.on("error", () => finish(undefined));
    child.stdout?.setEncoding("utf8");
    child.stdout?.on("data", (chunk: string) => {
      if (stdout.length < 1024 * 1024) stdout += chunk.slice(0, 1024 * 1024 - stdout.length);
    });
    child.stdin?.on("error", () => { /* child may exit before accepting input */ });
    child.stdin?.end(input);
    child.on("close", (code) => {
      if (code !== 0) {
        finish(undefined);
        return;
      }
      try { finish(JSON.parse(stdout) as Record<string, unknown>); }
      catch { finish(undefined); }
    });
  });
}

export default function (pi: any) {
  pi.on("tool_result", async (event: any, ctx: any) => {
    try {
      if (typeof event?.toolName !== "string" || event.toolName.toLowerCase() !== "bash") {
        return undefined;
      }
      const core = corePath();
      if (!core) return undefined;
      const content = Array.isArray(event.content) ? event.content : [];
      const text = content.filter((block: any) => block?.type === "text" &&
        typeof block.text === "string").map((block: any) => block.text).join("\n");
      const manager = ctx?.sessionManager;
      const payload = JSON.stringify({
        kind: "reminder", toolName: event.toolName, input: event.input,
        toolCallId: event.toolCallId,
        sessionId: manager?.getSessionId?.(), cwd: manager?.getCwd?.(),
        details: event.details, text,
      });
      const result = await runCore(core, payload);
      if (typeof result?.text !== "string" || !result.text) return undefined;
      return {
        content: [...content, { type: "text", text: result.text }],
        ...(event.structuredContent !== undefined &&
          { structuredContent: event.structuredContent }),
      };
    } catch {
      return undefined;
    }
  });
}
