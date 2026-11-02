"""Move the Phase 27 validation and verification lines from the round 6 PASS to round 7."""

import os

BASE = os.path.join(os.path.dirname(__file__), "..", "..", ".planning", "phases",
                    "27-one-shot-goal-and-loop-prompt-skill")

PAIRS = {
    "27-VALIDATION.md": [
        ("post-review confirmation rounds 4 to 6 re-judged the shipped package; round 6 (referee-one "
         "116/125 = 92.8%, referee-three 114/125 = 91.2%, both A, 0 critical; the verdict takes 91.2, "
         "PASS vs base 90.4) matches the committed package and the checker reproduces it; round 4 "
         "(88.8%) was UNRESOLVED before the INT-1 quota-rule fix. Two judges now",
         "post-review confirmation rounds 4 to 7 re-judged the shipped package; round 7 (referee-one "
         "118/125 = 94.4%, referee-three 109/125 = 87.2%, 0 critical; the verdict takes 87.2, "
         "UNRESOLVED vs base 90.4) matches the committed package and the checker reproduces it; "
         "round 6 had passed at 91.2% before later fixes. Two judges now; `--gate` is pending until "
         "an owner decision"),
        ("27-12-3 was re-judged in post-review round 6: PASS 91.2%, `gate ok`; round 4 had been "
         "UNRESOLVED at 88.8%",
         "27-12-3 was re-judged in post-review round 7: UNRESOLVED 87.2%, `gate pending`; round 6 "
         "had passed at 91.2%"),
        ("the verdict is current (round 6: 114/125 = 91.2% lowest of two judges, A, 0 critical, PASS "
         "vs base 90.4)",
         "the verdict is current (round 7: 109/125 = 87.2% lowest of two judges, B, 0 critical, "
         "UNRESOLVED vs base 90.4)"),
    ],
    "27-VERIFICATION.md": [
        ("post-review confirmation round 6 re-judged the shipped package (PASS)",
         "post-review confirmation round 7 re-judged the shipped package (UNRESOLVED)"),
        ("`--gate` prints `gate ok`; see OWNER-CAPTURES item 7",
         "`--gate` prints `gate pending`; see OWNER-CAPTURES item 7"),
        ("Owner optionally accepts the PASS (114/125, 91.2% lowest of two judges, grade A, 0 critical, "
         "base 90.4%) with an Owner-decision line; two judges (referee-one 92.8%, referee-three 91.2%) "
         "backed it, and the same skill scored 88.8, 92.0, 88.8 and 92.0 in rounds 2 to 5 with one judge",
         "Owner decides on the UNRESOLVED verdict (109/125, 87.2% lowest of two judges, grade B, 0 "
         "critical, base 90.4%): accept it with an Owner-decision line or ask for a fix and a new round; "
         "two judges scored 94.4% (referee-one) and 87.2% (referee-three), round 6 had passed at 91.2%, "
         "and the same skill scored 88.8, 92.0, 88.8 and 92.0 in rounds 2 to 5 with one judge"),
        ("skill-judge re-judged at HEAD (round 6: 91.2%, PASS, two judges)",
         "skill-judge re-judged at HEAD (round 7: 87.2%, UNRESOLVED, two judges)"),
        ("VERIFIED: jev VERIFIED, skill-judge PASS at HEAD (round 6, two judges)",
         "VERIFIED: jev VERIFIED; skill-judge UNRESOLVED at HEAD (round 7, two judges, owner decision pending)"),
        ("post-review confirmation round 6 judged the package at HEAD (referee-one 116/125 = 92.8%, "
         "referee-three 114/125 = 91.2%, A, 0 critical); `check_verdicts.py` prints `verdicts ok` and "
         "`--gate` prints `gate ok` (91.2% >= base 90.4%).",
         "post-review confirmation round 7 judged the package at HEAD (referee-one 118/125 = 94.4%, "
         "referee-three 109/125 = 87.2%, 0 critical); `check_verdicts.py` prints `verdicts ok` and "
         "`--gate` prints `gate pending` (87.2% < base 90.4%)."),
        ("skill-judge half judged at HEAD (round 6: 91.2%, PASS vs base 90.4%, two judges)",
         "skill-judge half judged at HEAD (round 7: 87.2%, UNRESOLVED vs base 90.4%, two judges)"),
        ("(round 6: 91.2% vs its 90.4% base, two judges; the owner may add an acceptance line)",
         "(round 7: 87.2% vs its 90.4% base, two judges, UNRESOLVED; the owner decides)"),
    ],
}

for name, pairs in PAIRS.items():
    path = os.path.join(BASE, name)
    text = open(path, encoding="utf-8").read()
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit(f"{name}: {text.count(old)} matches: {old[:70]}")
        text = text.replace(old, new)
    open(path, "w", encoding="utf-8").write(text)
    print("updated", name)
