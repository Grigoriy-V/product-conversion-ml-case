from __future__ import annotations

import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_portfolio_figures import EXPECTED, load_evidence  # noqa: E402


class PortfolioFiguresTests(unittest.TestCase):
    def test_accepted_metrics_are_loaded_from_json(self) -> None:
        evidence = load_evidence()
        self.assertEqual(evidence["aps"], tuple(EXPECTED.values()))
        labels = [point["label"] for point in evidence["operating_points"]]
        self.assertEqual(labels, ["Default 0.50", "Recall ≥ 0.50", "Recall ≥ 0.60", "Recall ≥ 0.70", "Selected F2"])

    def test_cli_creates_readable_png_and_svg_outputs(self) -> None:
        subprocess.run([sys.executable, "tools/build_portfolio_figures.py"], cwd=ROOT, check=True)
        for stem in ("model_ap_comparison", "threshold_tradeoff"):
            png = ROOT / "docs" / "assets" / f"{stem}.png"
            svg = ROOT / "docs" / "assets" / f"{stem}.svg"
            self.assertTrue(png.exists() and png.stat().st_size > 10_000)
            self.assertTrue(svg.exists() and svg.stat().st_size > 1_000)
            with png.open("rb") as handle:
                self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")
                width, height = struct.unpack(">II", handle.read(16)[8:16])
            self.assertGreaterEqual(width, 1_000)
            self.assertGreaterEqual(height, 700)
            self.assertIn("<svg", svg.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
