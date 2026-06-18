#!/usr/bin/env python3
"""Score K judge-agent verdicts over labeled mermaid fixtures.

A verdict file is JSON: {"<fixture>.md": ["C1", "S1", ...], ...} — the rules that
judge flagged per fixture. gold.json is the same shape with the TRUE labels.

Two metrics per rule:
  * agreement  — fraction of judges that flagged a rule on a fixture where gold
    says it belongs. A rule is "well-formed" if agreement >= threshold on every
    fixture that legitimately violates it (objective enough that judges concur).
  * accuracy   — precision/recall of judges vs gold across all fixtures, plus a
    false-positive rate on clean fixtures (gold == []).

Usage:
    score_consensus.py --gold gold.json --verdicts <dir-of-judge-json> [--threshold 0.8]
"""
import argparse
import json
import os
import sys


def load_verdicts(path):
    """Load every *.json verdict file in a directory (sorted)."""
    out = []
    for f in sorted(os.listdir(path)):
        if f.endswith(".json"):
            with open(os.path.join(path, f), encoding="utf-8") as fh:
                out.append(json.load(fh))
    return out


def _rules_in_gold(gold):
    rules = set()
    for labels in gold.values():
        rules.update(labels)
    return rules


def score(gold, verdicts, threshold=0.8):
    k = max(len(verdicts), 1)
    agreement = {}           # fixture -> rule -> fraction of judges that flagged it
    for fixture, labels in gold.items():
        agreement[fixture] = {}
        for rule in labels:
            hits = sum(1 for v in verdicts if rule in v.get(fixture, []))
            agreement[fixture][rule] = hits / k

    # a rule is well-formed if, on EVERY fixture that truly has it, judges concur
    rule_well_formed = {}
    for rule in _rules_in_gold(gold):
        fixtures_with = [fx for fx, lbl in gold.items() if rule in lbl]
        rule_well_formed[rule] = bool(fixtures_with) and all(
            agreement[fx][rule] >= threshold for fx in fixtures_with)

    # false-positive rate on clean fixtures (gold == [])
    false_positive_rate = {}
    for fixture, labels in gold.items():
        if not labels:
            fp = sum(1 for v in verdicts if v.get(fixture))
            false_positive_rate[fixture] = fp / k

    # global precision/recall vs gold
    tp = fp = fn = 0
    for v in verdicts:
        for fixture, gold_labels in gold.items():
            got = set(v.get(fixture, []))
            want = set(gold_labels)
            tp += len(got & want)
            fp += len(got - want)
            fn += len(want - got)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    return {
        "judges": k,
        "threshold": threshold,
        "agreement": agreement,
        "rule_well_formed": rule_well_formed,
        "false_positive_rate": false_positive_rate,
        "precision": precision,
        "recall": recall,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score judge consensus vs gold labels.")
    ap.add_argument("--gold", required=True)
    ap.add_argument("--verdicts", required=True, help="dir of judge *.json files")
    ap.add_argument("--threshold", type=float, default=0.8)
    a = ap.parse_args(argv)
    with open(a.gold, encoding="utf-8") as fh:
        gold = json.load(fh)
    report = score(gold, load_verdicts(a.verdicts), a.threshold)
    print(json.dumps(report, indent=2))
    weak = [r for r, ok in report["rule_well_formed"].items() if not ok]
    if weak:
        print(f"WEAK (judges split, < {a.threshold}): {', '.join(sorted(weak))}",
              file=sys.stderr)
    sys.exit(1 if weak else 0)


if __name__ == "__main__":
    main()
