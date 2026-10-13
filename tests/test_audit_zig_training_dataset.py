from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_zig_training_dataset.py"


def valid_record(output: str = "pub fn main() void {}") -> dict:
    return {
        "instruction": "Validate this Zig 0.16 example.",
        "input": "pub fn main() void {}",
        "output": output,
        "metadata": {
            "change_id": "test-example",
            "scenario": "minimal-main",
            "version_from": "0.15.x",
            "version_to": "0.16.0",
            "compiler_validated": True,
            "validation_status": "passed",
            "compiler_version": "0.16.0",
            "validation_command": "zig test sample.zig",
            "validation_exit_code": 0,
            "source": "https://ziglang.org/download/0.16.0/release-notes.html",
        },
    }


class DatasetAuditTests(unittest.TestCase):
    def run_audit(self, lines: list[str], *extra_args: str) -> subprocess.CompletedProcess[str]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        data_dir = Path(temp_dir.name)
        (data_dir / "examples.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--data-dir", str(data_dir), *extra_args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_record_passes(self) -> None:
        record = valid_record()
        result = self.run_audit([json.dumps(record)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Training ready: YES", result.stdout)

    def test_unvalidated_record_blocks_training(self) -> None:
        record = valid_record()
        record["metadata"]["compiler_validated"] = False
        record["metadata"]["validation_status"] = "snippet_only"
        result = self.run_audit([json.dumps(record)])
        self.assertEqual(result.returncode, 2)
        self.assertIn("Training ready: NO", result.stdout)
        self.assertIn("missing compiler evidence", result.stdout)

    def test_placeholder_blocks_training(self) -> None:
        record = valid_record("TODO: implement the migration")
        result = self.run_audit([json.dumps(record)])
        self.assertEqual(result.returncode, 2)
        self.assertIn("placeholder_or_scaffold", result.stdout)

    def test_duplicate_records_block_training(self) -> None:
        record = valid_record()
        line = json.dumps(record)
        result = self.run_audit([line, line])
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate_example", result.stdout)

    def test_invalid_json_fails_structural_audit(self) -> None:
        result = self.run_audit(["{not-json"], "--audit-only")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid_json", result.stdout)


if __name__ == "__main__":
    unittest.main()
