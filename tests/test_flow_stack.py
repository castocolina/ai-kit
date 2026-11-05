"""Stack reconciliation tests (plan 29.1-03 fills this module; plan 29.1-01 registers it).

Plan 29.1-01 only proves that the flow modules import and that the CLI parses a checkpoint
command. Restack, hotfix and merge-chain behaviour tests land with plan 03.
"""

import pathlib
import sys
import unittest

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))


class TestFlowScriptsImport(unittest.TestCase):
    def test_flow_scripts_import(self):
        import flow_git  # noqa: F401
        import flow_pr  # noqa: F401
        import flow_record  # noqa: F401
        import flow_stack  # noqa: F401
        import flow_unit  # noqa: F401
        import fold

        args = fold.build_parser().parse_args(["checkpoint", "--unit", "-"])
        self.assertEqual(args.command, "checkpoint")
        self.assertEqual(args.unit_file, "-")


if __name__ == "__main__":
    unittest.main()
