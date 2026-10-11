import re, pathlib
p = pathlib.Path("jb/scripts/jev_review.py"); src = p.read_text().splitlines(keepends=True)
# delete lines 22-29 (1-based) and insert task2 impl
t2 = pathlib.Path("t2_impl.txt").read_text()
t2 = t2.replace("import math  # already present\n", "")
src = src[:21] + [t2] + src[29:]
text = "".join(src)
# request_body signature
text = text.replace("def request_body(payload):", "def request_body(payload, model):")
text = text.replace('return {"model": MODEL, "state": payload, "questions": questions}, specs', 'return {"model": model, "state": payload, "questions": questions}, specs')
# replace checked_response
start = text.index("def checked_response(response, specs):"); end = text.index("def _opencode_auth_key")
text = text[:start] + pathlib.Path("t3_a.txt").read_text().replace('def request_body(payload, model):\n    ...  # unchanged validation\n    return {"model": model, "state": payload, "questions": questions}, specs\n\n\n','') + "\n\n" + pathlib.Path("t3_cr.txt").read_text() + "\n\n" + text[end:]
start = text.index("def screen():"); end = text.index("def main():")
text = text[:start] + pathlib.Path("t3_screen.txt").read_text() + "\n\n" + text[end:]
start = text.index("def main():"); end = text.index('if __name__ == "__main__":')
text = text[:start] + pathlib.Path("t2_main.txt").read_text() + "\n\n" + text[end:]
p.write_text(text)
