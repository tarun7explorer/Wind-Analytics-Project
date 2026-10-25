"""Build the Vite frontend before Vercel packages the FastAPI application."""

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NPM = "npm.cmd" if os.name == "nt" else "npm"

subprocess.run([NPM, "ci"], cwd=ROOT, check=True)
subprocess.run([NPM, "run", "build"], cwd=ROOT, check=True)

index_html = ROOT / "dist" / "index.html"
asset_files = list((ROOT / "dist" / "assets").glob("**/*")) if (ROOT / "dist" / "assets").is_dir() else []
if not index_html.is_file():
    raise RuntimeError("Vite build completed without producing dist/index.html")
if not any(path.is_file() for path in asset_files):
    raise RuntimeError("Vite build completed without producing files under dist/assets")

print(f"Verified Vite output: {index_html.relative_to(ROOT)} and {sum(path.is_file() for path in asset_files)} asset file(s)")
