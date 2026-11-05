# Folding policy

The one text for folding a unit's commits before its branch moves. Each rule below is pinned by a doc-contract check in `tests/test_arch.py`; change a rule here and its pin together.

- **FOLD-1** one commit per logical feature, so a plan with two features gives two commits.
- **FOLD-2** never one squash per plan or per phase.
- **FOLD-3** each folded commit carries its code with its tests and docs.
- **FOLD-4** the folded tip's tree equals the tested tree before the branch moves.
- **FOLD-5** the old tip gets a local backup tag before the branch moves.
- **FOLD-6** that backup tag is deleted when the unit's PR merges.
- **FOLD-7** no `reset --hard`.
- **FOLD-8** commits reachable from main (the base branch) or from a branch whose PR has merged are never rewritten.
- **FOLD-9** a rewritten pushed branch is pushed only with `--force-with-lease`.
- **FOLD-10** pushes go to the primary remote only.
- **FOLD-11** the fold runs before every push of a unit's branch and needs no confirmation.

Commits already pushed to an unmerged branch may be folded again (FLOW-01, amended).

Grouping limit: rule grouping merges features only on a shared changed path or a code file with its `test_<stem>.py`. A feature that depends on a file a later feature adds (an import across features) is not detected, so an intermediate folded commit is not proven to build on its own; only the folded tip's tree is proven (FOLD-4). List such features as one candidate.

Enforcement: FOLD-4, FOLD-5 and FOLD-7 are enforced by this skill's script. FOLD-8 is enforced for the base branch always; its merged-branch half is enforced by the unit flow's checkpoint, which passes the recorded merged unit branches as merged refs. FOLD-6, FOLD-9, FOLD-10 and FOLD-11 are enforced by ai-kit's unit flow; they are recorded here so that playbooks carry the whole policy.
