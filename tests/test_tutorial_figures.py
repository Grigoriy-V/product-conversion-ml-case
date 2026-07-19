from __future__ import annotations

import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_tutorial_figures import STEMS  # noqa: E402


class TutorialFiguresTests(unittest.TestCase):
    def test_expected_stems_are_fixed(self) -> None:
        self.assertEqual(STEMS, (
            "data_workflow",
            "cross_validation_folds",
            "preprocessing_pipeline",
            "logistic_vs_tree",
            "random_forest_aggregation",
        ))

    def test_cli_creates_readable_png_and_svg_outputs(self) -> None:
        subprocess.run([sys.executable, "tools/build_tutorial_figures.py"], cwd=ROOT, check=True)
        assets = ROOT / "docs" / "assets" / "tutorial"
        for stem in STEMS:
            png = assets / f"{stem}.png"
            svg = assets / f"{stem}.svg"
            self.assertTrue(png.exists() and png.stat().st_size > 10_000)
            self.assertTrue(svg.exists() and svg.stat().st_size > 1_000)
            with png.open("rb") as handle:
                self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")
                width, height = struct.unpack(">II", handle.read(16)[8:16])
            self.assertGreaterEqual(width, 1_200)
            self.assertGreaterEqual(height, 550)
            self.assertIn("<svg", svg.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
