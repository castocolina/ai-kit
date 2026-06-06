# Build a Universal Commit Message Generator

## Context

We need to help users write better commit messages. This will improve the developer experience and also handle release notes, changelog generation, and documentation. Users have been complaining about commit quality.

## Approach

We will build a new tool from scratch that:

1. Reads the staged diff
2. Calls an LLM
3. Returns a suggested commit message
4. Optionally posts the suggestion as a Slack message
5. Optionally generates a release note
6. Optionally updates the changelog
7. Generates social media announcements about big commits

The tool will be invoked as `~/.claude/tools/commit-helper.sh`. It supports both conventional commits and a new format we'll call "expressive commits" which we'll define later.

## Components

- **Diff Reader** — reads `git diff --staged`
- **Message Generator** — wraps an LLM
- **Slack Poster** — posts to Slack when desired
- **Release Note Generator** — produces release notes
- **Social Announcer** — drafts tweets

## Implementation

The Diff Reader uses git directly. The Message Generator should use whatever LLM is available. Errors are handled appropriately.

## Notes

We may also want this to integrate with the existing Claude Code commit flow eventually, but that's out of scope for now. We'll figure out the exact integration later.
