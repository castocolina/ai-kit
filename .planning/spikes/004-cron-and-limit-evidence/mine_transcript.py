"""Spike 004: list a Claude Code session transcript's cron-prompt deliveries and usage-limit replies.

Usage: python3 mine_transcript.py <session.jsonl> [<prompt marker>]
Prints UTC timestamps only: no message bodies beyond the limit line, never a token.
"""
import json
import re
import sys

path, marker = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "Quota-resume check")
events = []
for line in open(path, encoding="utf-8"):
    try:
        events.append(json.loads(line))
    except ValueError:
        continue


def text(ev):
    msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return str(ev.get("content", ""))


LIMIT = re.compile(r"You've hit your (session|weekly) limit · resets [^\n]+")
for i, ev in enumerate(events):
    ts, body = ev.get("timestamp", "")[:19], text(ev)
    if ev.get("type") == "user" and marker in body:
        nxt = next((e for e in events[i + 1:i + 40] if e.get("type") == "assistant" and text(e).strip()), None)
        hit = LIMIT.search(text(nxt)) if nxt else None
        print(ts, "fire", "-> " + hit.group(0) if hit else "-> answered")
    elif ev.get("type") == "system" and "Goal paused" in body:
        print(ts, "system", body[:90])
