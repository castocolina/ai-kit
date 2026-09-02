# Loop control-flow diagram

Optional visual companion to the textual Steps 1-5 in SKILL.md, which fully specify the loop's
behavior on their own — this diagram is not needed to execute the loop correctly. Consult it only
if you find the branching in Steps 1-5 hard to trace on a first read (e.g. sorting out how
Step 3's four routes rejoin the main loop, or which paths hit Step 3c validation before returning
to Step 1).

```dot
digraph review_spec {
    "Start" [shape=doublecircle];
    "Dispatch reviewer(s) (fresh)" [shape=box];
    "Read EFFECTIVE_REPORT_PATH" [shape=box];
    "Parse Status line" [shape=diamond];
    "Approved" [shape=box, style=filled, fillcolor=lightgreen];
    "Issues Found?" [shape=diamond];
    "Iter < cap?" [shape=diamond];
    "Resolve route per archetype" [shape=diamond];
    "Step 3a generic fixer" [shape=box];
    "Parse fixer Status" [shape=diamond];
    "Step 3b-skill native revise" [shape=box];
    "Step 3b-cmd native command" [shape=box];
    "Slash tool available?" [shape=diamond];
    "Step 3b-surface" [shape=box];
    "Native revise handed off" [shape=box, style=filled, fillcolor=orange];
    "Step 3c validate?" [shape=diamond];
    "Cap reached" [shape=box, style=filled, fillcolor=orange];
    "Surface to user" [shape=doublecircle];

    "Start" -> "Dispatch reviewer(s) (fresh)";
    "Dispatch reviewer(s) (fresh)" -> "Read EFFECTIVE_REPORT_PATH";
    "Read EFFECTIVE_REPORT_PATH" -> "Parse Status line";
    "Parse Status line" -> "Approved" [label="Approved"];
    "Parse Status line" -> "Issues Found?" [label="Issues Found"];
    "Issues Found?" -> "Iter < cap?" [label="yes"];
    "Issues Found?" -> "Surface to user" [label="no"];
    "Iter < cap?" -> "Resolve route per archetype" [label="yes"];
    "Iter < cap?" -> "Cap reached" [label="no"];

    "Resolve route per archetype" -> "Step 3a generic fixer" [label="direct edit"];
    "Resolve route per archetype" -> "Step 3b-skill native revise" [label="skill:<name>"];
    "Resolve route per archetype" -> "Step 3b-cmd native command" [label="slash_command"];
    "Resolve route per archetype" -> "Step 3b-surface" [label="surface"];

    "Step 3a generic fixer" -> "Parse fixer Status";
    "Parse fixer Status" -> "Dispatch reviewer(s) (fresh)" [label="Edits Applied (next iter)"];
    "Parse fixer Status" -> "Surface to user" [label="Escalation Required"];
    "Parse fixer Status" -> "Surface to user" [label="No Edits"];

    "Step 3b-skill native revise" -> "Step 3c validate?" [label="Edits Applied (route has validate)"];
    "Step 3b-skill native revise" -> "Dispatch reviewer(s) (fresh)" [label="Edits Applied (no validate, next iter)"];
    "Step 3b-skill native revise" -> "Step 3b-surface" [label="Needs Input"];
    "Step 3b-skill native revise" -> "Surface to user" [label="No Edits"];

    "Step 3b-cmd native command" -> "Slash tool available?" ;
    "Slash tool available?" -> "Step 3c validate?" [label="yes (route has validate)"];
    "Slash tool available?" -> "Dispatch reviewer(s) (fresh)" [label="yes (no validate, next iter)"];
    "Slash tool available?" -> "Step 3b-surface" [label="no"];

    "Step 3c validate?" -> "Dispatch reviewer(s) (fresh)" [label="sound (next iter)"];
    "Step 3c validate?" -> "Surface to user" [label="blocking"];

    "Step 3b-surface" -> "Native revise handed off";
    "Native revise handed off" -> "Surface to user";

    "Approved" -> "Surface to user";
    "Cap reached" -> "Surface to user";
}
```
