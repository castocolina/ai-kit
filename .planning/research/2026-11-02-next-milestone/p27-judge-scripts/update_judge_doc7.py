"""Record round 7 in 27-SKILL-JUDGE.md and move the other Phase 27 lines from round 6 to round 7."""

import os

BASE = os.path.join(os.path.dirname(__file__), "..", "..", ".planning", "phases",
                    "27-one-shot-goal-and-loop-prompt-skill")
SHA = open(os.path.join(os.path.dirname(__file__), "judge", "r7-digest.txt")).read().strip()


def edit(name, pairs):
    path = os.path.join(BASE, name)
    text = open(path, encoding="utf-8").read()
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit(f"{name}: {text.count(old)} matches for {old[:70]!r}")
        text = text.replace(old, new)
    open(path, "w", encoding="utf-8").write(text)


def cut_tail(name, marker, new_tail):
    path = os.path.join(BASE, name)
    text = open(path, encoding="utf-8").read()
    head = text.split(marker, 1)[0]
    open(path, "w", encoding="utf-8").write(head + new_tail)


edit("27-SKILL-JUDGE.md", [
    ("**Round 6 judges (2026-11-02):**", "**Round 6 and 7 judges (2026-11-02):**"),
    ("(`--route-pi router --mode review`), one lane each. `my-referee-two` answered a PONG probe with `503 ... service_unavailable`\n"
     "in each of four probes during the round and was replaced",
     "(`--route-pi router --mode review`), one lane each in both rounds. `my-referee-two` answered every PONG probe (four in round 6,\n"
     "one in round 7) with `503 ... service_unavailable` and was replaced"),
    ("**Rounds:** the original loop ran at most three; rounds 4 to 6 are", "**Rounds:** the original loop ran at most three; rounds 4 to 7 are"),
    ("block and the evidence reference; round 6 is the last, there is no round 7).",
     "block and the evidence reference, round 7 after the `## Full objective` section and the corrected SKILL.md statements;\n"
     "round 8 would run only after a real critical or high finding was fixed)."),
    ("Post-review confirmation rounds: 4,5,6", "Post-review confirmation rounds: 4,5,6,7"),
    ("fixed. No critical or high finding was a defect of this change, so no fix and no round 7 ran. Probes:",
     "fixed then. The owner afterwards told this change to fix it (see round 7). Probes:"),
    ("  which is above 80 and above the base 90.4.\n",
     "  which is above 80 and above the base 90.4. That digest is now stale.\n"
     "- Post-review confirmation, round 7 (2026-11-02, start commit 1651b90's parent 65aa32f plus commits 7b61f3c, bb364f7, 3577128 and\n"
     "  the checker commit; two judges; the prompt adds a note on the `## Full objective` section, the corrected `tmp/` and re-render\n"
     "  statements and the moved e2e read): referee-one 118/125, 94.4%, grade A, 0 critical, 2 high (D6-1 and D8-2, the same two\n"
     "  findings refuted in round 6), 1 medium and 0 low, 458 s; referee-three 109/125, 87.2%, grade B, 0 critical, 0 high, 2\n"
     "  medium and 7 low, 103 s. Both digests equal the committed package. The objective-loss finding (high in round 6) and the false\n"
     "  re-render sentence did not come back. No new critical or high finding, so no round 8 ran. Probes: referee-one and\n"
     "  referee-three answered PONG; referee-two returned 503. The lowest percent is 87.2 (referee-three): above 80 but below the\n"
     "  base 90.4, so the verdict is UNRESOLVED, as in round 4. referee-three moved from 91.2 to 87.2 between rounds 6 and 7 with\n"
     "  only medium and low findings, within the noise recorded below.\n"),
    ("Verdict: PASS\nRound: 6\n", "Verdict: UNRESOLVED\nRound: 7\n"),
    ("Reviewed-sha256: c3f5572f493a3c01c69dfe2b3d497e95e86532adb70bbe2959e07711db894bde\nBase percent",
     f"Reviewed-sha256: {SHA}\nBase percent"),
    ("Score: 114/125\nPercent: 91.2\nGrade: A\nCritical findings: 0\nImportant findings: 3\n"
     "Rule: lowest percent 91.2 (referee-one 92.8, referee-three 91.2); ((C0 and I3) -> False) or 91.2 >= 80 -> True; 91.2 >= 90.4 -> True.\n"
     "Reports: skill-judge/r6/ai-kit-spec-goal-prompt-my-referee-one.md, skill-judge/r6/ai-kit-spec-goal-prompt-my-referee-three.md",
     "Score: 109/125\nPercent: 87.2\nGrade: B\nCritical findings: 0\nImportant findings: 2\n"
     "Rule: lowest percent 87.2 (referee-one 94.4, referee-three 87.2); ((C0 and I2) -> False) or 87.2 >= 80 -> True; 87.2 >= 90.4 -> False.\n"
     "Reports: skill-judge/r7/ai-kit-spec-goal-prompt-my-referee-one.md, skill-judge/r7/ai-kit-spec-goal-prompt-my-referee-three.md"),
    ("scripts/gp_sections.py:356; the owner's rule", "scripts/gp_sections.py:369; the owner's rule"),
    ("scripts/gp_sections.py:62 lists", "scripts/gp_sections.py:64 lists"),
    ("from scripts/gp_sections.py:273 and the sentence from scripts/gp_render.py:394)",
     "from scripts/gp_sections.py:286 and the sentence from scripts/gp_render.py:404). Round 7 (referee-one) repeated both findings\n"
     "  (D6-1 at scripts/gp_sections.py:369, D8-2 at scripts/gp_sections.py:283); the refutations stand."),
    ("The third, D8-1 (a long objective is cut to one capped rule line outside the `/goal` block), is not refuted: it is real. See Pending acceptance.",
     "The third, D8-1 (a long objective is cut to one capped rule line outside the `/goal` block), was real and is fixed since: the\n"
     "line now ends with a pointer and the file keeps the whole text in `## Full objective` (scripts/gp_sections.py:170)."),
])
cut_tail("27-SKILL-JUDGE.md", "## Owner decision needed", """## Owner decision needed

The verdict is UNRESOLVED (87.2 is above 80 but below the 90.4 base); the checker's `--gate` lists it as pending until an
owner decision exists. Context for the owner: the same skill scored 88.8, 92.0, 88.8 and 92.0 in rounds 2 to 5 with one
judge, and in rounds 6 and 7 two judges gave 92.8 and 91.2, then 94.4 and 87.2, so one judge's result has about 4 points of
noise. The package improved since round 6 (a real information-loss defect and a false sentence were fixed) and referee-one
scored it higher (94.4), while referee-three scored it lower with medium and low findings only. No Owner-decision line was written.

## Owner decisions

none

## Pending acceptance

Open findings of round 7 (judged, not fixed; no critical or high finding of the change is open):

- ai-kit-spec-goal-prompt: UNRESOLVED (D8-1 medium, referee-one: a plan work set names plans by title only, so a single plan
  without a dependency has no file name in the prompt, scripts/gp_render.py:571)
- ai-kit-spec-goal-prompt: UNRESOLVED (D2-1 and D4-1 medium, referee-three: the mindset paragraph gives no fit check of the strategy
  against the user's intent, SKILL.md:13; the description has no boundary against running the phases now, SKILL.md:3)
- ai-kit-spec-goal-prompt: UNRESOLVED (D1-1, D1-2, D3-1, D5-1, D6-1, D7-1, D8-1, D8-2, low or medium, referee-three: Unverified section
  repeats reference text, a generic NEVER line, no Gotchas section, the worked-example pointer, the `--tools` step, no eval for a
  free-text work set or the `tmp/` refusal, the hand-edit sentence, the stop-run wording)

Fixed after round 6 and judged in round 7: the objective cut (a `## Full objective` section), the false re-render sentence, the
`tmp/` statements, the e2e read order. Fixed after round 7: none. The judge is non-deterministic, so the verdict is that of the
last judged round, whose digest equals the committed package; earlier reports (r1-r6) are kept.
""")

edit("27-OWNER-CAPTURES.md", [
    ("(ai-kit-spec-goal-prompt: PASS, post-review confirmation round 6, two judges: referee-one "
     "116/125 = 92.8% and referee-three 114/125 = 91.2%, both grade A, 0 critical; referee-one "
     "listed 3 high findings, 2 refuted and 1 real and left open on purpose, see "
     "`27-SKILL-JUDGE.md`; the verdict takes the lower 91.2% against the 90.4 base; round 4 had "
     "scored 88.8%, UNRESOLVED; referee-two returned 503 and was replaced by referee-three, no "
     "native Opus ran).",
     "(ai-kit-spec-goal-prompt: post-review confirmation round 7, two judges: referee-one 118/125 = "
     "94.4% and referee-three 109/125 = 87.2%, 0 critical; verdict UNRESOLVED, the lower 87.2% is "
     "below the 90.4 base, so `--gate` prints `gate pending` until an owner decision exists; round 6 "
     "had passed at 91.2% before later fixes; referee-two returned 503 and was replaced by "
     "referee-three, no native Opus ran)."),
    ("The open round-6 findings are still unaccepted by an owner (see `27-SKILL-JUDGE.md` "
     "`## Pending acceptance`). The verdict rests on two judges (referee-one and referee-three; "
     "referee-two returned 503, no native Opus), 91.2% (the lower of the two) against a 90.4% "
     "base (round 6).",
     "The open round-7 findings are still unaccepted by an owner (see `27-SKILL-JUDGE.md` "
     "`## Pending acceptance`). The verdict rests on two judges (referee-one and referee-three; "
     "referee-two returned 503, no native Opus), 87.2% (the lower of the two) against a 90.4% "
     "base (round 7), UNRESOLVED."),
    ("Steps: read the findings in `skill-judge/r6/`.", "Steps: read the findings in `skill-judge/r7/`."),
    ("`check_verdicts.py` prints `verdicts ok`; `--gate` prints `gate ok` (", "`check_verdicts.py` prints `verdicts ok`; `--gate` prints `gate pending` ("),
])
