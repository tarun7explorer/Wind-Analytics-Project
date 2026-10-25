import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api.index import app


ROOT = Path(__file__).resolve().parents[1]
DIST_INDEX = ROOT / "dist" / "index.html"


@unittest.skipUnless(DIST_INDEX.is_file(), "Run npm run build before the frontend serving test")
class FrontendServingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_frontend_root_serves_built_react_document(self):
        response = self.client.get("/", headers={"accept": "text/html"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn('id="root"', response.text)

    def test_referenced_vite_assets_are_served(self):
        html_response = self.client.get("/", headers={"accept": "text/html"})
        self.assertEqual(html_response.status_code, 200)
        asset_paths = set(re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html_response.text))
        self.assertTrue(asset_paths, "Built HTML should reference hashed Vite assets")

        for asset_path in asset_paths:
            with self.subTest(asset=asset_path):
                response = self.client.get(asset_path)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content)


if __name__ == "__main__":
    unittest.main()
