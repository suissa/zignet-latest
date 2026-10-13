#!/usr/bin/env python3
"""Audit ZigNet migration JSONL before fine-tuning.

This script validates structure, provenance, duplication, placeholder leakage, and
recorded compiler evidence. It does NOT run Zig or infer that code compiles. A
record is eligible only when a separate compiler-validation workflow has stored
traceable, successful evidence in its metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SPLIT_FILES = {
    "dataset-train.jsonl",
    "dataset-validation.jsonl",
    "dataset-test.jsonl",
}
REQUIRED_FIELDS = {"instruction", "input", "output", "metadata"}
PLACEHOLDER_PATTERNS = [
    re.compile(r"\b(?:TODO|FIXME|TBD)\b", re.IGNORECASE),
    re.compile(r"\bplaceholder\b", re.IGNORECASE),
    re.compile(r"assumir comportamento idêntico", re.IGNORECASE),
    re.compile(r"\bexample_dependency\b", re.IGNORECASE),
    re.compile(r"must be replaced", re.IGNORECASE),
    re.compile(r"\billustrative(?: only)?\b", re.IGNORECASE),
    re.compile(r"insert\s+(?:code|value|name|implementation)\s+here", re.IGNORECASE),
    re.compile(r"replace with (?:a )?real\b", re.IGNORECASE),
]
REQUIRED_EVIDENCE_FIELDS = ("validation_command",)
VALID_STATUSES = {"compiler_validated", "passed"}


def normalized_hash(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("instruction", "")).strip(),
        str(row.get("input", "")).strip(),
        str(row.get("output", "")).strip(),
    ]
    normalized = "\n".join(re.sub(r"\s+", " ", part) for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def evidence_errors(row: dict[str, Any]) -> list[str]:
    meta = row.get("metadata")
    if not isinstance(meta, dict):
        return ["metadata must be an object"]
    errors: list[str] = []
    if meta.get("compiler_validated") is not True:
        errors.append("compiler_validated must be true")
    if meta.get("validation_status") not in VALID_STATUSES:
        errors.append("validation_status must be compiler_validated or passed")
    if meta.get("compiler_version") != "0.16.0":
        errors.append("compiler_version must be pinned to 0.16.0")
    for field in REQUIRED_EVIDENCE_FIELDS:
        if not isinstance(meta.get(field), str) or not meta[field].strip():
            errors.append(f"{field} is missing")
    if meta.get("validation_exit_code") != 0 and meta.get("validation_result") != "passed":
        errors.append("successful compiler result (validation_exit_code=0 or validation_result=passed) is missing")
    if not (meta.get("source") or meta.get("source_url")):
        errors.append("source/source_url is missing")
    if not (meta.get("change_id") or meta.get("scenario_family") or meta.get("scenario")):
        errors.append("change/scenario identifier is missing")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "training" / "v0.16.0",
        help="Directory containing one JSONL file per migration category.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional path for a JSON audit report.",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Return success after structural audit even when the data is not training-ready.",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    if not data_dir.is_dir():
        print(f"ERROR: dataset directory not found: {data_dir}", file=sys.stderr)
        return 2

    files = sorted(
        path for path in data_dir.glob("*.jsonl")
        if path.name not in SPLIT_FILES and not path.name.startswith(".")
    )
    if not files:
        print(f"ERROR: no category JSONL files found in {data_dir}", file=sys.stderr)
        return 2

    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    duplicate_locations: dict[str, list[str]] = defaultdict(list)
    counts_by_file: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()

    for file_path in files:
        with file_path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    continue
                location = f"{file_path.name}:{line_number}"
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    issues.append({"location": location, "kind": "invalid_json", "detail": str(exc)})
                    continue
                if not isinstance(row, dict):
                    issues.append({"location": location, "kind": "invalid_record", "detail": "each line must be a JSON object"})
                    continue

                missing = sorted(REQUIRED_FIELDS - set(row))
                if missing:
                    issues.append({"location": location, "kind": "missing_fields", "detail": missing})
                    continue
                if any(not isinstance(row.get(field), str) for field in ("instruction", "input", "output")):
                    issues.append({
                        "location": location,
                        "kind": "invalid_text_fields",
                        "detail": "instruction, input, and output must be strings",
                    })
                    continue
                if not isinstance(row.get("metadata"), dict):
                    issues.append({"location": location, "kind": "invalid_metadata", "detail": "metadata must be an object"})
                    continue
                if not row["instruction"].strip() or not row["output"].strip():
                    issues.append({"location": location, "kind": "empty_text", "detail": "instruction/output must not be empty"})

                records.append(row)
                counts_by_file[file_path.name] += 1
                meta = row["metadata"]
                status = str(meta.get("validation_status", "missing"))
                validation_counts[status] += 1

                for pattern in PLACEHOLDER_PATTERNS:
                    match = pattern.search(row["input"] + "\n" + row["output"])
                    if match:
                        issues.append({
                            "location": location,
                            "kind": "placeholder_or_scaffold",
                            "detail": f"matched {pattern.pattern!r}: {match.group(0)!r}",
                        })
                        break

                duplicate_locations[normalized_hash(row)].append(location)
                evidence = evidence_errors(row)
                if evidence:
                    warnings.append({
                        "location": location,
                        "kind": "missing_compiler_evidence",
                        "detail": evidence,
                    })

    for locations in duplicate_locations.values():
        if len(locations) > 1:
            issues.append({
                "location": ", ".join(locations),
                "kind": "duplicate_example",
                "detail": f"same normalized instruction/input/output occurs {len(locations)} times",
            })

    ready = bool(records) and not issues and not warnings
    report = {
        "dataset_dir": str(data_dir),
        "files_scanned": len(files),
        "records_scanned": len(records),
        "counts_by_file": dict(sorted(counts_by_file.items())),
        "validation_status_counts": dict(sorted(validation_counts.items())),
        "issue_count": len(issues),
        "records_missing_compiler_evidence": len(warnings),
        "issues": issues,
        "evidence_warnings": warnings,
        "training_ready": ready,
        "note": "This audit does not run Zig. Compiler evidence must come from an actual pinned Zig 0.16.0 validation run.",
    }

    print(f"Files scanned: {len(files)}")
    print(f"Records scanned: {len(records)}")
    print(f"Structural/quality issues: {len(issues)}")
    print(f"Records missing compiler evidence: {len(warnings)}")
    print(f"Training ready: {'YES' if ready else 'NO'}")
    if issues:
        print("\nFirst issues:")
        for issue in issues[:20]:
            print(f"- {issue['location']} [{issue['kind']}]: {issue['detail']}")
    if warnings:
        print("\nFirst records missing compiler evidence:")
        for warning in warnings[:10]:
            print(f"- {warning['location']}: {'; '.join(warning['detail'])}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nReport written: {args.report}")

    if args.audit_only:
        return 0 if records and not any(issue["kind"] in {"invalid_json", "missing_fields", "invalid_record", "invalid_metadata", "invalid_text_fields"} for issue in issues) else 2
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
