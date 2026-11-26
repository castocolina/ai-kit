# Loop control-flow diagram

Optional visual companion to the textual Steps 1-5 in SKILL.md, which fully specify the loop's
behavior on their own — this diagram is not needed to execute the loop correctly. Consult it only
if you find the branching in Steps 1-5 hard to trace on a first read (e.g. sorting out how
Step 3's four routes rejoin the main loop, or which paths hit Step 3c validation before returning
to Step 1).

The ping, the flagged-lane switch, the fold check and the partial status are described in [lane-failure.md](lane-failure.md).

```dot
digraph review_spec {
    "Start" [shape=doublecircle];
    "Size review (size-review)" [shape=box];
    "Ping lanes (ping-lanes)" [shape=box];
    "No lane left" [shape=box, style=filled, fillcolor=orange];
    "Lane pending (hard tier)" [shape=box, style=filled, fillcolor=orange];
    "Flagged lane hit quota?" [shape=diamond];
    "Switch to fallback (switch-lane)" [shape=box];
    "Fold check (check-fold-step)" [shape=box];
    "Merge reports (lane log)" [shape=box];
    "Approved (partial)" [shape=box, style=filled, fillcolor=yellow];
    "Not reviewed" [shape=box, style=filled, fillcolor=orange];
    "Classify disagreements (classify-disagreements)" [shape=box];
    "Dispatch reviewer(s) (fresh)" [shape=box];
    "Read EFFECTIVE_REPORT_PATH" [shape=box];
    "Parse Status line" [shape=diamond];
    "Approved" [shape=box, style=filled, fillcolor=lightgreen];
    "Revisions authorized?" [shape=diamond];
    "Iter < cap?" [shape=diamond];
    "Resolve route per archetype" [shape=diamond];
    "Step 3a generic fixer" [shape=box];
    "Parse fixer Status" [shape=diamond];
    "Listed skip or escalation?" [shape=diamond];
    "Step 3b-skill native revise" [shape=box];
    "Step 3b-cmd native command" [shape=box];
    "Slash tool available?" [shape=diamond];
    "Step 3b-surface" [shape=box];
    "Native revise handed off" [shape=box, style=filled, fillcolor=orange];
    "Step 3c validate?" [shape=diamond];
    "Cap reached" [shape=box, style=filled, fillcolor=orange];
    "Surface to user" [shape=doublecircle];

    "Start" -> "Dispatch reviewer(s) (fresh)" [label="--no-cross-ai or session default: no sizing, no ping"];
    "Start" -> "Size review (size-review)" [label="active cross-AI path"];
    "Size review (size-review)" -> "Ping lanes (ping-lanes)";
    "Ping lanes (ping-lanes)" -> "Dispatch reviewer(s) (fresh)" [label="at least one lane"];
    "Ping lanes (ping-lanes)" -> "No lane left" [label="exit 3"];
    "Ping lanes (ping-lanes)" -> "Dispatch reviewer(s) (fresh)" [label="next iter off the active cross-AI path: no ping"];
    "Dispatch reviewer(s) (fresh)" -> "Flagged lane hit quota?";
    "Flagged lane hit quota?" -> "Switch to fallback (switch-lane)" [label="yes: switched"];
    "Switch to fallback (switch-lane)" -> "Fold check (check-fold-step)" [label="fallback dispatched this iteration"];
    "Flagged lane hit quota?" -> "Fold check (check-fold-step)" [label="no, or not switched (lane stays failed)"];
    "Fold check (check-fold-step)" -> "Merge reports (lane log)" [label="round log exists"];
    "Fold check (check-fold-step)" -> "Read EFFECTIVE_REPORT_PATH" [label="no round log: merge only for 2 entries or a fold finding"];
    "Merge reports (lane log)" -> "Read EFFECTIVE_REPORT_PATH";
    "Read EFFECTIVE_REPORT_PATH" -> "Parse Status line";
    "Parse Status line" -> "Approved" [label="Approved"];
    "Parse Status line" -> "Lane pending (hard tier)" [label="a lane is pending (checked first)"];
    "Parse Status line" -> "Approved (partial)" [label="Approved (partial)"];
    "Parse Status line" -> "Not reviewed" [label="Failure — not reviewed"];
    "Parse Status line" -> "Iter < cap?" [label="Issues Found"];
    "Iter < cap?" -> "Revisions authorized?" [label="yes"];
    "Revisions authorized?" -> "Resolve route per archetype" [label="yes, or the user says yes when asked"];
    "Revisions authorized?" -> "Surface to user" [label="no (findings surfaced)"];
    "Iter < cap?" -> "Cap reached" [label="no"];

    "Resolve route per archetype" -> "Step 3a generic fixer" [label="direct edit"];
    "Resolve route per archetype" -> "Step 3b-skill native revise" [label="skill:<name>"];
    "Resolve route per archetype" -> "Step 3b-cmd native command" [label="slash_command"];
    "Resolve route per archetype" -> "Step 3b-surface" [label="surface"];

    "Step 3a generic fixer" -> "Listed skip or escalation?";
    "Listed skip or escalation?" -> "Classify disagreements (classify-disagreements)" [label="yes: classify first, whatever the Status"];
    "Listed skip or escalation?" -> "Parse fixer Status" [label="no"];
    "Classify disagreements (classify-disagreements)" -> "Step 3a generic fixer" [label="mechanical, iter < cap (one re-pass)"];
    "Classify disagreements (classify-disagreements)" -> "Parse fixer Status" [label="no fixer item left"];
    "Classify disagreements (classify-disagreements)" -> "Surface to user" [label="at the cap: owner items, skipped items"];
    "Parse fixer Status" -> "Ping lanes (ping-lanes)" [label="Edits Applied (next iter)"];
    "Parse fixer Status" -> "Surface to user" [label="Escalation Required or No Edits"];

    "Step 3b-skill native revise" -> "Step 3c validate?" [label="Edits Applied (route has validate)"];
    "Step 3b-skill native revise" -> "Ping lanes (ping-lanes)" [label="Edits Applied (no validate, next iter)"];
    "Step 3b-skill native revise" -> "Step 3b-surface" [label="Needs Input"];
    "Step 3b-skill native revise" -> "Surface to user" [label="No Edits"];

    "Step 3b-cmd native command" -> "Slash tool available?" ;
    "Slash tool available?" -> "Step 3c validate?" [label="yes (route has validate)"];
    "Slash tool available?" -> "Ping lanes (ping-lanes)" [label="yes (no validate, next iter)"];
    "Slash tool available?" -> "Step 3b-surface" [label="no"];

    "Step 3c validate?" -> "Ping lanes (ping-lanes)" [label="sound (next iter)"];
    "Step 3c validate?" -> "Surface to user" [label="blocking"];

    "Step 3b-surface" -> "Native revise handed off";
    "Native revise handed off" -> "Surface to user";

    "Approved" -> "Surface to user";
    "Approved (partial)" -> "Surface to user";
    "Not reviewed" -> "Surface to user";
    "No lane left" -> "Surface to user";
    "Lane pending (hard tier)" -> "Surface to user";
    "Cap reached" -> "Classify disagreements (classify-disagreements)";
}
```
