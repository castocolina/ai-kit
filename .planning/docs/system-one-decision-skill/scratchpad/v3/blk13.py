    if "--calibrate" in sys.argv:
        import re
        if not RESULTS.exists():
            print("notes/eval-results.json missing; Task 5 aborted", file=sys.stderr)
            return 1
        doc = json.loads(RESULTS.read_text(encoding="utf-8"))
        proposed = {e["backend"]: calibrate(e["cases"]) for e in doc.get("results", [])}
        print(json.dumps({"JEV_MIN_CONFIDENCE": proposed}, sort_keys=True))
        path = ROOT / "scripts" / "jev_review.py"
        text = path.read_text(encoding="utf-8")
        for backend, winner in proposed.items():
            if winner is None:
                print(f"{backend}: leave 0.7; say why in backends/{backend}.md", file=sys.stderr)
                continue
            text, n = re.subn(rf'("{backend}": \{{.*?"min_confidence": )\d+(?:\.\d+)?', rf"\g<1>{winner}", text, count=1, flags=re.S)
            if n != 1: raise SystemExit(backend)
        path.write_text(text, encoding="utf-8")
        return 0
