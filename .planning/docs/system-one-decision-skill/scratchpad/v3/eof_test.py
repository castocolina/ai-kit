import pathlib, subprocess, sys; sys.path.insert(0, str(pathlib.Path(__file__).parent)); import test_shell as t
orig = subprocess.run
def run(*a, **k):
    if k.get("input") in ("\n\n",): k["input"] = ""
    return orig(*a, **k)
def test_eof(tmp_path):
    t.subprocess.run = run
    try:
        result, calls, config = t.run_setup_no_gpu(tmp_path)
    finally:
        t.subprocess.run = orig
    print(result.returncode, result.stdout[-300:], result.stderr[-300:])
    assert result.returncode == 0
