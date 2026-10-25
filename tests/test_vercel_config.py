import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VercelConfigTests(unittest.TestCase):
    def test_fastapi_entrypoint_and_runtime_dependencies_are_declared(self):
        with (ROOT / "pyproject.toml").open("rb") as file:
            project = tomllib.load(file)

        self.assertEqual(project["tool"]["vercel"]["entrypoint"], "api.index:app")
        self.assertEqual(project["project"]["requires-python"], ">=3.12,<3.15")
        dependencies = project["project"]["dependencies"]
        for package in ("fastapi", "httpx", "pydantic"):
            self.assertTrue(any(item.lower().startswith(package) for item in dependencies))
        self.assertFalse(project["tool"]["uv"]["package"])

    def test_built_frontend_is_not_excluded_from_fastapi_function(self):
        with (ROOT / "vercel.json").open(encoding="utf-8") as file:
            config = json.load(file)

        excludes = config["functions"]["api/index.py"]["excludeFiles"]
        self.assertNotIn("dist", excludes)


if __name__ == "__main__":
    unittest.main()
