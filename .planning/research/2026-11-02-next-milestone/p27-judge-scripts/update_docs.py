"""Point the Phase 27 capture, validation and verification lines at the round 6 verdict."""

import os

BASE = os.path.join(os.path.dirname(__file__), "..", "..", ".planning", "phases",
                    "27-one-shot-goal-and-loop-prompt-skill")

PAIRS = {
    "27-OWNER-CAPTURES.md": [
        ("(ai-kit-spec-goal-prompt: PASS, post-review confirmation round 5, 115/125 = 92.0%, grade A, "
         "0 critical, 0 high; base 90.4; round 4 had scored 88.8%, UNRESOLVED). One judge only "
         "(referee-two; referee-three was down, referee-one not used, no native Opus ran).",
         "(ai-kit-spec-goal-prompt: PASS, post-review confirmation round 6, two judges: referee-one "
         "116/125 = 92.8% and referee-three 114/125 = 91.2%, both grade A, 0 critical; referee-one "
         "listed 3 high findings, 2 refuted and 1 real and left open on purpose, see "
         "`27-SKILL-JUDGE.md`; the verdict takes the lower 91.2% against the 90.4 base; round 4 had "
         "scored 88.8%, UNRESOLVED; referee-two returned 503 and was replaced by referee-three, no "
         "native Opus ran)."),
        ("The open round-5 findings are still unaccepted by an owner: medium D4-1, D7-1, D8-1 and low "
         "D1-1, D2-1, D3-1, D5-1, D8-2 (see `27-SKILL-JUDGE.md` `## Pending acceptance`). The verdict "
         "rests on one judge (referee-two; referee-three and referee-one were down, no native Opus), "
         "92.0% against a 90.4% base (round 5).",
         "The open round-6 findings are still unaccepted by an owner (see `27-SKILL-JUDGE.md` "
         "`## Pending acceptance`). The verdict rests on two judges (referee-one and referee-three; "
         "referee-two returned 503, no native Opus), 91.2% (the lower of the two) against a 90.4% "
         "base (round 6)."),
        ("Steps: read the eight findings in `skill-judge/r5/ai-kit-spec-goal-prompt-my-referee-two.md`; "
         "optionally re-judge with a second lane when one is up.",
         "Steps: read the findings in `skill-judge/r6/`."),
    ],
    "27-VALIDATION.md": [
        ("post-review confirmation rounds 4 and 5 re-judged the shipped package; round 5 (referee-two: "
         "115/125 = 92.0%, A, 0 critical, 0 high, PASS vs base 90.4) matches the committed package and "
         "the checker reproduces it; round 4 (88.8%) was UNRESOLVED before the INT-1 quota-rule fix. "
         "One judge only, so the owner may still want a second lane",
         "post-review confirmation rounds 4 to 6 re-judged the shipped package; round 6 (referee-one "
         "116/125 = 92.8%, referee-three 114/125 = 91.2%, both A, 0 critical; the verdict takes 91.2, "
         "PASS vs base 90.4) matches the committed package and the checker reproduces it; round 4 "
         "(88.8%) was UNRESOLVED before the INT-1 quota-rule fix. Two judges now"),
        ("27-12-3 was re-judged in post-review round 5: PASS 92.0%, `gate ok`; round 4 had been "
         "UNRESOLVED at 88.8%",
         "27-12-3 was re-judged in post-review round 6: PASS 91.2%, `gate ok`; round 4 had been "
         "UNRESOLVED at 88.8%"),
        ("the verdict is current (round 5: 115/125 = 92.0%, A, 0/0, PASS vs base 90.4; one judge only)",
         "the verdict is current (round 6: 114/125 = 91.2% lowest of two judges, A, 0 critical, PASS "
         "vs base 90.4)"),
    ],
    "27-VERIFICATION.md": [
        ("post-review confirmation round 5 re-judged the shipped package (PASS)",
         "post-review confirmation round 6 re-judged the shipped package (PASS)"),
        ("Owner optionally accepts the PASS (115/125, 92.0%, grade A, 0 critical, 0 high, base 90.4%) "
         "with an Owner-decision line or asks for a second judge lane; one judge only (referee-two) "
         "backed it, and the same skill scored 88.8, 92.0, 88.8 and 92.0 in rounds 2 to 5",
         "Owner optionally accepts the PASS (114/125, 91.2% lowest of two judges, grade A, 0 critical, "
         "base 90.4%) with an Owner-decision line; two judges (referee-one 92.8%, referee-three 91.2%) "
         "backed it, and the same skill scored 88.8, 92.0, 88.8 and 92.0 in rounds 2 to 5 with one judge"),
        ("skill-judge re-judged at HEAD (round 5: 92.0%, PASS, one judge)",
         "skill-judge re-judged at HEAD (round 6: 91.2%, PASS, two judges)"),
        ("VERIFIED: jev VERIFIED, skill-judge PASS at HEAD (round 5, one judge)",
         "VERIFIED: jev VERIFIED, skill-judge PASS at HEAD (round 6, two judges)"),
        ("post-review confirmation round 5 judged the package at HEAD (referee-two, 115/125 = 92.0%, A, "
         "0 critical, 0 high); `check_verdicts.py` prints `verdicts ok` and `--gate` prints `gate ok` "
         "(92.0% >= base 90.4%).",
         "post-review confirmation round 6 judged the package at HEAD (referee-one 116/125 = 92.8%, "
         "referee-three 114/125 = 91.2%, A, 0 critical); `check_verdicts.py` prints `verdicts ok` and "
         "`--gate` prints `gate ok` (91.2% >= base 90.4%)."),
        ("skill-judge half judged at HEAD (round 5: 92.0%, PASS vs base 90.4%, one judge)",
         "skill-judge half judged at HEAD (round 6: 91.2%, PASS vs base 90.4%, two judges)"),
        ("(round 5: 92.0% vs its 90.4% base, one judge only; the owner may add an acceptance line)",
         "(round 6: 91.2% vs its 90.4% base, two judges; the owner may add an acceptance line)"),
    ],
}

for name, pairs in PAIRS.items():
    path = os.path.join(BASE, name)
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit(f"{name}: expected one match, got {text.count(old)}: {old[:60]}")
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("updated", name, len(pairs))
