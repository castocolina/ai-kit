Plan B’s last task is now a two-lane final skill evaluation, and the header says that task needs Plan A complete.

- The execution-order note no longer treats Task 8 as runnable without Laya. It requires `system_one.enabled: true` and a healthy `http://127.0.0.1:8010`.
- Task 8 is “Final skill evaluation.” The old single-judge step, the per-dimension maxima table, and the `notes/skill-judge.md` acceptance are gone.
- Both lanes are external `cursor-agent` processes (`glm-5.2-max` and `gemini-3.1-pro`), run in parallel. One line records that `glm-5.3` is not offered. The prompt is in the task, tells each judge not to edit files, and covers anatomy (lower lane ≥ 96/120, and any dimension under 80% of its maximum), the 12-line `evals/activation.jsonl` set, the `--probe` / `backends/<selected>.md` citations, and the seven live Laya commands with pass rules.
- After each round the executor writes `notes/eval-findings-<round>.md`, appends one dated `CHANGELOG.md` line, and, if the round failed, fixes with `grok-4.7-high-fast` (skill files only). Three rounds maximum; after a failed round 3 it stops and points at the lower lane’s report.

I did not run the judges or confirm those model slugs on this machine. Check 2 can fail if something else posts to `system-one` in the same second, and check 3 can fail if Laya’s probabilities move between two calls by more than 1e-3.
