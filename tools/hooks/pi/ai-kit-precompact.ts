// ai-kit PreCompact pre-summary extension for pi (SPEC R6; D-07, D-08, D-18).
//
// On `session_before_compact` this hands `preparation.messagesToSummarize`,
// `turnPrefixMessages`, `previousSummary` and `fileOps`, plus the session id,
// name and cwd, to `python3 -S precompact_core.py pi` on stdin, and returns the
// core's pre-summary as `{compaction: {summary, firstKeptEntryId, tokensBefore,
// details}}` with the event's own ids. On ANY failure it returns `undefined`,
// so pi's default compaction runs — this shim must never fail a compaction.
//
// This file is one self-contained link on purpose: pi loads every direct
// .ts/.js file in `extensions/`, so a helper file beside it would load as a
// second extension. Its helpers (`corePath`, `runCore`, `replacer`) are
// therefore repeated verbatim in the opencode plugin; neither file can import
// a sibling. Erasable TypeScript only (type annotations, no enums/namespaces),
// so node's type stripping and pi's loader both run it. No npm dependency.

import { spawn } from "node:child_process";
import { realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// The whole handler, process start included, must finish inside this budget
// (SPEC R8); the child is killed at the deadline.
const TIMEOUT_MS = 10000;

// The core lives one directory up from this file's realpath, so a symlink in
// pi's `extensions/` still reaches `tools/hooks/precompact_core.py`.
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

// JSON.stringify replacer: Sets (pi's fileOps) become arrays and image blocks
// lose their base64 `data`, so megabytes never reach the Python child's stdin.
function replacer(_key: string, value: unknown): unknown {
  if (value instanceof Set) {
    return [...value];
  }
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (record.type === "image") {
      return { ...record, data: "" };
    }
  }
  return value;
}

// Spawn the core with an argv array and no shell, write `input` on stdin, keep
// at most 4 MiB of stdout, kill the child at the timeout or on `signal`, and
// resolve the parsed JSON object — or `undefined` on ANY failure (a throw
// inside the close callback would escape the handler's try and reach pi).
function runCore(core: string, entry: string, input: string, signal?: AbortSignal,
                 timeoutMs: number = TIMEOUT_MS): Promise<Record<string, unknown> | undefined> {
  return new Promise((resolve) => {
    let child;
    let stdout = "";
    let settled = false;
    let timer;
    const finish = (result: Record<string, unknown> | undefined) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      if (signal) {
        signal.removeEventListener("abort", onAbort);
      }
      resolve(result);
    };
    const kill = () => {
      try {
        if (child.pid) process.kill(-child.pid, "SIGKILL");
      } catch {
        // already gone or process groups unavailable
      }
    };
    const onAbort = () => {
      kill();
    };
    try {
      child = spawn(process.env.AI_KIT_PYTHON || "python3", ["-S", core, entry],
                    { stdio: ["pipe", "pipe", "ignore"], detached: true });
      child.stdout?.setEncoding("utf8");
    } catch {
      resolve(undefined);
      return;
    }
    timer = setTimeout(kill, timeoutMs);
    if (signal) {
      if (signal.aborted) {
        onAbort();
      } else {
        signal.addEventListener("abort", onAbort, { once: true });
      }
    }
    child.on("error", () => finish(undefined));
    child.stdout?.on("data", (chunk: string) => {
      if (stdout.length < 4 * 1024 * 1024) {
        stdout += chunk;
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

// The default export pi's extension loader calls; it registers exactly one
// event handler and never raises.
export default function (pi: any) {
  pi.on("session_before_compact", async (event: any, ctx: any) => {
    try {
      const core = corePath();
      if (!core) {
        return undefined;
      }
      const preparation = event?.preparation ?? {};
      const manager = ctx?.sessionManager;
      const input = JSON.stringify({
        preparation: {
          messagesToSummarize: preparation.messagesToSummarize,
          turnPrefixMessages: preparation.turnPrefixMessages,
          previousSummary: preparation.previousSummary,
          fileOps: preparation.fileOps,
        },
        sessionId: manager?.getSessionId?.(),
        sessionName: manager?.getSessionName?.(),
        cwd: manager?.getCwd?.() ?? process.cwd(),
      }, replacer);
      const result = await runCore(core, "pi", input, event?.signal);
      if (result && typeof result.summary === "string" && result.summary) {
        return {
          compaction: {
            summary: result.summary,
            firstKeptEntryId: preparation.firstKeptEntryId,
            tokensBefore: preparation.tokensBefore,
            details: result.details,
          },
        };
      }
      return undefined;
    } catch {
      return undefined;
    }
  });
}
