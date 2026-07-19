import json
import tempfile
import unittest
from pathlib import Path

from audit.online_shoppers_audit import EXPECTED_COLUMNS, audit_and_split


class OnlineShoppersAuditTests(unittest.TestCase):
    def test_audit_and_split_are_deterministic(self):
        rows = []
        for index in range(10):
            row = {column: "0" for column in EXPECTED_COLUMNS}
            row["Administrative"] = str(index)
            row["Month"] = "May"; row["VisitorType"] = "Returning_Visitor"
            row["Weekend"] = "FALSE"; row["Revenue"] = "TRUE" if index in {1, 7} else "FALSE"
            rows.append(",".join(row[column] for column in EXPECTED_COLUMNS))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source.csv"
            source.write_text(",".join(EXPECTED_COLUMNS) + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
            first = audit_and_split(source, root / "first.json", root / "first.csv")
            second = audit_and_split(source, root / "second.json", root / "second.csv")
            self.assertEqual(first["split"]["train_fingerprint_sha256"], second["split"]["train_fingerprint_sha256"])
            self.assertEqual(first["split"]["test_fingerprint_sha256"], second["split"]["test_fingerprint_sha256"])
            self.assertEqual(first["shape"]["rows"], 10)
            self.assertEqual(first["target"]["values"], {"FALSE": 8, "TRUE": 2})
            self.assertEqual(json.loads((root / "first.json").read_text())["exact_duplicate_rows"], 0)


if __name__ == "__main__":
    unittest.main()
