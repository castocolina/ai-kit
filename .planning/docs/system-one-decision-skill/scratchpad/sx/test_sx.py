import runpy, pathlib
def test_run():
    runpy.run_path(str(pathlib.Path(__file__).parent / "mod.py"), run_name="__main__")
