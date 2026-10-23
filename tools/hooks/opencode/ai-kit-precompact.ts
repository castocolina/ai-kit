// ai-kit PreCompact pre-summary plugin for opencode (SPEC R7; D-09, D-18).
//
// EXPERIMENTAL: the upstream `experimental.session.compacting` hook is marked
// experimental, and whether installed opencode v2 still calls it is unverified
// until the phase's S4 check records otherwise. The plugin only APPENDS the
// core's pre-summary onto `output.context` — it never assigns `output.prompt`,
// so opencode's own compaction prompt always stays in charge — and on ANY
// failure it leaves `output` untouched, so it can never fail a compaction.
//
// This file is one self-contained link on purpose: opencode links one file per
// plugin, so its helpers (`corePath`, `runCore`, `replacer`) are repeated
// verbatim from the pi extension; neither file can import a sibling. Erasable
// TypeScript only (type annotations, no enums/namespaces), so node's type
// stripping runs it. No npm dependency.

import { spawn } from "node:child_process";
import { realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// One shared deadline covers the session fetch below and the core run: the
// whole hook must finish inside this budget (SPEC R8).
const TIMEOUT_MS = 10000;

// The core lives one directory up from this file's realpath, so a symlink in
// opencode's global `plugins/` dir still reaches `tools/hooks/precompact_core.py`.
function corePath(): string | undefined {
  let here: string | undefined;
  try {
    here = fileURLToPath(import.meta.url);
  } catch {
    const globalFilename = (globalThis as { __filename?: unknown }).__filename;
    here = typeof globalFilename === "string" ? globalFilename : undefined;
  }
  if (here === undefined) {
    return undefined;
  }
  try {
    return join(dirname(realpathSync(here)), "..", "precompact_core.py");
  } catch {
    return undefined;
  }
}

// JSON.stringify replacer: Sets become arrays, image blocks lose their base64
// `data`, and a `file` part's `data:` URL is blanked — megabytes never reach
// the Python child's stdin. This copy also blanks `data:` file URLs; the pi
// shim's copy has no file parts to blank.
function replacer(_key: string, value: unknown): unknown {
  if (value instanceof Set) {
    return [...value];
  }
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (record.type === "image") {
      return { ...record, data: "" };
    }
    if (record.type === "file" && typeof record.url === "string"
        && record.url.startsWith("data:")) {
      return { ...record, url: "" };
    }
  }
  return value;
}

// Spawn the core with an argv array and no shell, write `input` on stdin, keep
// at most 4 MiB of stdout, kill the child at `timeoutMs`, and resolve the
// parsed JSON object — or `undefined` on ANY failure (a throw inside the close
// callback would escape the handler's try and reach opencode). Unlike the pi
// copy there is no abort signal; the deadline comes in as `timeoutMs`.
function runCore(core: string, entry: string, input: string,
                 timeoutMs: number = TIMEOUT_MS): Promise<Record<string, unknown> | undefined> {
  return new Promise((resolve) => {
    let child;
    let stdout = "";
    let settled = false;
    const finish = (result: Record<string, unknown> | undefined) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const kill = () => {
      try {
        child.kill("SIGKILL");
      } catch {
        // already gone
      }
    };
    try {
      child = spawn(process.env.AI_KIT_PYTHON || "python3", ["-S", core, entry],
                    { stdio: ["pipe", "pipe", "ignore"] });
    } catch {
      resolve(undefined);
      return;
    }
    const timer = setTimeout(kill, timeoutMs);
    child.on("error", () => finish(undefined));
    child.stdout?.on("data", (chunk: Buffer) => {
      if (stdout.length < 4 * 1024 * 1024) {
        stdout += chunk.toString("utf-8");
      }
    });
    child.stdin?.on("error", () => {
      // the core may exit early; its failure shows up in `close`
    });
    child.stdin?.end(input);
    child.on("close", (code) => {
      if (code !== 0) {
        finish(undefined);
        return;
      }
      try {
        finish(JSON.parse(stdout) as Record<string, unknown>);
      } catch {
        finish(undefined);
      }
    });
  });
}

// The one named export; opencode calls every exported plugin function, so this
// module exports nothing else and the hooks object carries only this hook.
export const AiKitPrecompact = async (input: any) => ({
  "experimental.session.compacting": async (hookInput: any, output: any) => {
    try {
      const client = input?.client;
      const deadline = Date.now() + TIMEOUT_MS;
      const fetchMessages = client?.session?.messages?.({ path: { id: hookInput?.sessionID } });
      let timer;
      const raced: unknown = await Promise.race([
        fetchMessages,
        new Promise((resolve) => {
          timer = setTimeout(() => resolve(undefined), TIMEOUT_MS);
        }),
      ]);
      clearTimeout(timer);
      const remaining = deadline - Date.now();
      if (raced === undefined || remaining < 1) {
        return; // the fetch never settled inside the shared deadline
      }
      const holder = raced as { data?: unknown };
      const messages = holder && typeof holder === "object" && "data" in holder
        ? holder.data
        : raced;
      if (!Array.isArray(messages) || !Array.isArray(output?.context)) {
        return;
      }
      const core = corePath();
      if (!core) {
        return;
      }
      const payload = JSON.stringify({
        sessionID: hookInput?.sessionID,
        directory: input?.directory,
        messages,
      }, replacer);
      const result = await runCore(core, "opencode", payload, remaining);
      if (result && typeof result.context === "string" && result.context) {
        output.context.push(result.context);
      }
    } catch {
      // never fail a compaction: leave `output` untouched
    }
  },
});
