"""Tests for the layered, byte-preserving [models] config settings."""

import os
import pathlib
import shutil
import sys
import tempfile
import threading
import tomllib
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import config_io, models_config


class TestModelsConfig(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-p35-models-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.cwd = os.path.join(self.root, "project")
        os.makedirs(os.path.join(self.cwd, ".aikit"))
        self.env = {
            "HOME": os.path.join(self.root, "home"),
            "XDG_CONFIG_HOME": os.path.join(self.root, "config"),
        }
        self.user_path = config_io.cfg_global_path(self.env)
        self.project_path = config_io.cfg_local_path(self.cwd)

    def _write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_write_keeps_other_bytes(self):
        original = "# keep me\n[lanes]\nmode = \"review\"\n"
        self._write(self.user_path, original)
        models_config.write_models_settings(
            self.user_path, sources=["models.dev", "arena"], cache_days={"arena": 3}
        )
        text = pathlib.Path(self.user_path).read_text(encoding="utf-8")
        parsed = tomllib.loads(text)
        self.assertIn("# keep me", text)
        self.assertIn("[lanes]", text)
        self.assertEqual(parsed["models"]["sources"], ["models.dev", "arena"])
        self.assertEqual(parsed["models"]["cache_days"]["arena"], 3)

    def test_project_over_user(self):
        self._write(
            self.user_path,
            '[models]\nsources = ["arena"]\n\n[models.cache_days]\narena = 3\n',
        )
        self._write(self.project_path, '[models]\nsources = ["models.dev"]\n')
        settings = models_config.read_models_settings(self.cwd, self.env)
        self.assertEqual(settings.sources, ("models.dev",))
        self.assertEqual(settings.cache_days, {
            "models_dev": 7, "artificial_analysis": 7, "arena": 3
        })

    def test_defaults_when_absent(self):
        self.assertEqual(
            models_config.read_models_settings(self.cwd, self.env),
            models_config.ModelsSettings(
                ("models.dev", "artificial-analysis", "arena"),
                {"models_dev": 7, "artificial_analysis": 7, "arena": 7},
                (),
            ),
        )

    def test_context_round_trip(self):
        expected = (
            models_config.ContextOverride("pi", "router-env/placeholder-model-1", 131072),
        )
        as_dict = {
            "runtime": "pi",
            "model": "router-env/placeholder-model-1",
            "tokens": 131072,
        }
        for context in (list(expected), [as_dict]):
            models_config.write_models_settings(self.project_path, context=context)
            self.assertEqual(
                models_config.read_models_settings(self.cwd, self.env).context, expected
            )

    def test_first_write_creates_file(self):
        self.assertFalse(os.path.exists(self.project_path))
        models_config.write_models_settings(self.project_path, sources=["arena"])
        self.assertEqual(
            tomllib.loads(pathlib.Path(self.project_path).read_text(encoding="utf-8")),
            {"models": {"sources": ["arena"]}},
        )

    def test_key_never_written(self):
        models_config.write_models_settings(
            self.project_path, sources=["arena"], cache_days={"arena": 3}, context=[]
        )
        text = pathlib.Path(self.project_path).read_text(encoding="utf-8")
        self.assertNotIn("ARTIFICIAL_ANALYSIS_API_KEY", text)

    def test_unknown_source_named(self):
        self._write(self.project_path, '[models]\nsources = ["models.dev", "lmsys"]\n')
        with self.assertRaisesRegex(
            config_io.ConfigError,
            "unknown source 'lmsys'.*known: models.dev, artificial-analysis, arena",
        ):
            models_config.read_models_settings(self.cwd, self.env)

    def test_bad_cache_days(self):
        for table, named in (("arena = 0", "arena"), ("arena = true", "arena"), ("foo = 3", "foo")):
            with self.subTest(table=table):
                self._write(self.project_path, f"[models.cache_days]\n{table}\n")
                with self.assertRaisesRegex(config_io.ConfigError, named):
                    models_config.read_models_settings(self.cwd, self.env)

    def test_bad_context_entry(self):
        for body in (
            'runtime = "pi"\nmodel = "router-env/placeholder-model-1"\ntokens = 1.5',
            'runtime = "pi"\nmodel = "router-env/placeholder-model-1"\ntokens = 0',
            'model = "router-env/placeholder-model-1"\ntokens = 1',
        ):
            with self.subTest(body=body):
                self._write(self.project_path, f"[models]\n\n[[models.context]]\n{body}\n")
                with self.assertRaisesRegex(config_io.ConfigError, "entry 0"):
                    models_config.read_models_settings(self.cwd, self.env)

    def test_project_array_replaces_user_array(self):
        user_text = (
            '[[models.context]]\nruntime = "pi"\n'
            'model = "router-env/placeholder-model-1"\ntokens = 100\n\n'
            '[[models.context]]\nruntime = "pi"\n'
            'model = "router-env/placeholder-model-2"\ntokens = 200\n'
        )
        project_text = (
            '[[models.context]]\nruntime = "pi"\n'
            'model = "router-env/placeholder-model-3"\ntokens = 300\n'
        )
        self._write(self.user_path, user_text)
        self._write(self.project_path, project_text)
        self.assertEqual(
            models_config.read_models_settings(self.cwd, self.env).context,
            (models_config.ContextOverride("pi", "router-env/placeholder-model-3", 300),),
        )

    def test_unknown_key(self):
        self._write(self.project_path, '[models]\ncolour = "x"\n')
        with self.assertRaisesRegex(config_io.ConfigError, "unknown key 'colour'"):
            models_config.read_models_settings(self.cwd, self.env)

    def test_invalid_write_changes_nothing(self):
        self._write(self.project_path, '# unchanged\n[lanes]\nmode = "review"\n')
        original = pathlib.Path(self.project_path).read_bytes()
        with self.assertRaises(config_io.ConfigError):
            models_config.write_models_settings(self.project_path, sources=["lmsys"])
        self.assertEqual(pathlib.Path(self.project_path).read_bytes(), original)

    def test_two_writers_keep_one_value(self):
        self._write(self.project_path, "# keep\n")
        errors = []

        def write(source):
            try:
                models_config.write_models_settings(self.project_path, sources=[source])
            except Exception as error:  # surfaced below, including any unexpected splice race
                errors.append(error)

        writers = [
            threading.Thread(target=write, args=(source,))
            for source in ("arena", "models.dev")
        ]
        for writer in writers:
            writer.start()
        for writer in writers:
            writer.join()
        self.assertEqual(errors, [])
        sources = tomllib.loads(
            pathlib.Path(self.project_path).read_text(encoding="utf-8")
        )["models"]["sources"]
        self.assertIn(sources, (["arena"], ["models.dev"]))

    def test_empty_project_array_replaces_user_array(self):
        self._write(
            self.user_path,
            '[[models.context]]\nruntime = "pi"\n'
            'model = "router-env/placeholder-model-1"\ntokens = 100\n',
        )
        models_config.write_models_settings(self.project_path, context=[])
        project_text = pathlib.Path(self.project_path).read_text(encoding="utf-8")
        self.assertIn("context = []", project_text)
        self.assertEqual(models_config.read_models_settings(self.cwd, self.env).context, ())
        models_config.write_models_settings(
            self.project_path,
            context=[models_config.ContextOverride("pi", "router-env/placeholder-model-1", 64000)],
        )
        project_text = pathlib.Path(self.project_path).read_text(encoding="utf-8")
        self.assertNotIn("context = []", project_text)
        self.assertEqual(
            models_config.read_models_settings(self.cwd, self.env).context,
            (models_config.ContextOverride("pi", "router-env/placeholder-model-1", 64000),),
        )


if __name__ == "__main__":
    unittest.main()
