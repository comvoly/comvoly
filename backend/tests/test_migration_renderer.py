from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


class MigrationRendererTests(unittest.TestCase):
    def test_renderer_is_transactional_versioned_and_data_safe(self) -> None:
        script = Path(__file__).resolve().parents[1] / "tools" / "render_v2_migrations.py"
        spec = importlib.util.spec_from_file_location("render_v2_migrations", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        sql = module.render()

        self.assertTrue(sql.startswith("BEGIN;"))
        self.assertIn("COMMIT;", sql)
        self.assertIn("v2_secure_multi_community_foundation", sql)
        self.assertIn("v2_account_workspace_experience", sql)
        self.assertEqual(sql.count("ON CONFLICT (version) DO NOTHING"), 2)
        self.assertNotIn("INSERT INTO accounts", sql)
        self.assertNotIn("INSERT INTO workspaces", sql)


if __name__ == "__main__":
    unittest.main()
