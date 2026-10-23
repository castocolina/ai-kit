// One node harness for both precompact shims (SPEC R6, R7; D-18).
//
// Usage: node run_shim.mjs <host> <shim path> <fixture path> [mode]
//   host pi       — loads the shim, fakes the pi extension API, calls the
//                   registered `session_before_compact` handler with the
//                   fixture's preparation (fileOps arrays rebuilt as Sets),
//                   an AbortController signal (pre-aborted in mode `abort`)
//                   and a ctx from the fixture; prints the result JSON (or
//                   `null`). Mode `exports` prints the module's export names.
//   host opencode — loads the plugin, fakes the SDK client (mode `array`:
//                   bare array result; `throw`: rejects; `hang`: never
//                   settles) and the output object, calls the
//                   `experimental.session.compacting` hook once (twice in
//                   mode `twice`); prints `{output, promptSet, calls}`.
// No test starts a real pi or opencode process.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const [host, shimPath, fixturePath, mode = ""] = process.argv.slice(2);
const fixture = JSON.parse(readFileSync(fixturePath, "utf-8"));
const mod = await import(pathToFileURL(shimPath).href);

if (mode === "exports") {
  console.log(JSON.stringify(Object.keys(mod)));
  process.exit(0);
}

if (host === "pi") {
  const handlers = {};
  const pi = { on(name, fn) { handlers[name] = fn; } };
  mod.default(pi);
  const handler = handlers.session_before_compact;
  const controller = new AbortController();
  if (mode === "abort") controller.abort();
  const ops = fixture.preparation.fileOps;
  const fileOps = {
    read: new Set(ops.read),
    written: new Set(ops.written),
    edited: new Set(ops.edited),
  };
  const event = { preparation: { ...fixture.preparation, fileOps }, signal: controller.signal };
  const ctx = {
    sessionManager: {
      getSessionId: () => fixture.ctx.sessionId,
      getSessionName: () => fixture.ctx.sessionName,
      getCwd: () => fixture.ctx.cwd,
    },
  };
  const result = await handler(event, ctx);
  console.log(JSON.stringify(result ?? null));
} else if (host === "opencode") {
  const calls = [];
  let client;
  if (mode === "throw") {
    client = { session: { messages: () => Promise.reject(new Error("backend down")) } };
  } else if (mode === "hang") {
    client = { session: { messages: () => new Promise(() => {}) } };
  } else {
    client = {
      session: {
        messages: (args) => {
          calls.push({ client: args });
          return mode === "array" ? fixture.messages : Promise.resolve({ data: fixture.messages });
        },
      },
    };
  }
  const plugin = await mod.AiKitPrecompact({ client, directory: fixture.directory });
  const hook = plugin["experimental.session.compacting"];
  const output = { context: [...(fixture.existingContext ?? [])] };
  const times = mode === "twice" ? 2 : 1;
  for (let index = 0; index < times; index += 1) {
    calls.push({ hook: index });
    await hook({ sessionID: fixture.sessionID }, output);
  }
  console.log(JSON.stringify({
    output,
    promptSet: Object.hasOwn(output, "prompt"),
    calls: calls.length,
  }));
} else {
  console.error(`unknown host: ${host}`);
  process.exit(2);
}
