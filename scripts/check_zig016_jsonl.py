#!/usr/bin/env python3
"""Compile Zig target snippets from JSONL records with a bounded, resumable batch."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

FENCE_RE = re.compile(r"`{3}(?:zig)?[ \t]*\r?\n(.*?)`{3}", re.DOTALL | re.IGNORECASE)
TARGET_LABEL_RE = re.compile(
    r"(?:Alvo(?:/migração)?\s*(?:\(\s*0\.16\.0\s*\)|0\.16\.0)|"
    r"Alvo\s+ilustrativo|"
    r"Migração(?:\s+para)?\s*\(\s*0\.16\.0\s*\))\s*:",
    re.IGNORECASE,
)


def extract_target(output: Any) -> tuple[str | None, str | None]:
    if not isinstance(output, str):
        return None, "output is missing or is not a string"
    target = TARGET_LABEL_RE.search(output)
    if not target:
        return None, "no recognized Zig 0.16.0 target label"
    fence = FENCE_RE.search(output[target.end():])
    if not fence:
        return None, "target section has no fenced code block"
    source = fence.group(1).strip() + "\n"
    code_without_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    lines = [re.sub(r"//.*$", "", line).strip() for line in code_without_comments.splitlines()]
    if not any(lines):
        return None, "target code is empty or contains only comments"
    return source, None


def load_records(data_dir: Path) -> list[dict[str, Any]]:
    excluded = {"dataset-train.jsonl", "dataset-validation.jsonl", "dataset-test.jsonl"}
    files = sorted(p for p in data_dir.glob("*.jsonl") if p.name not in excluded)
    records: list[dict[str, Any]] = []
    for path in files:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    records.append({"file": path, "line": line_number, "scenario": "invalid-json", "source": None, "error": str(exc)})
                    continue
                source, error = extract_target(record.get("output"))
                metadata = record.get("metadata") or {}
                records.append({
                    "file": path,
                    "line": line_number,
                    "scenario": metadata.get("scenario", f"{path.stem}-line-{line_number}"),
                    "source": source,
                    "error": error,
                })
    unique_records: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for record in records:
        source = record.get("source")
        if source:
            if source in seen_sources:
                continue
            seen_sources.add(source)
        unique_records.append(record)
    return unique_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "training" / "v0.16.0")
    parser.add_argument("--zig-version", default="0.16.0")
    parser.add_argument("--offset", type=int, default=0, help="number of records to skip in the sorted JSONL stream")
    parser.add_argument("--limit", type=int, default=10, help="maximum records to compile in this batch; use 0 for all remaining")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    version = subprocess.run(["zig", "version"], capture_output=True, text=True, check=False)
    actual = version.stdout.strip()
    if version.returncode or actual != args.zig_version:
        print(f"ERROR: expected Zig {args.zig_version}, got {actual or version.stderr.strip() or 'unavailable'}", file=sys.stderr)
        return 2
    if args.offset < 0 or args.limit < 0:
        parser.error("--offset and --limit must be non-negative")

    try:
        all_records = load_records(args.data_dir)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    selected = all_records[args.offset:]
    if args.limit:
        selected = selected[:args.limit]
    if not selected:
        print(f"ERROR: no records selected (offset={args.offset}, total={len(all_records)})", file=sys.stderr)
        return 2

    results = []
    for index, item in enumerate(selected, start=args.offset + 1):
        path = item["file"]
        label = f"{path.name}:{item['line']} ({item['scenario']})"
        result = {"index": index, "file": str(path), "line": item["line"], "scenario": item["scenario"]}
        if item["error"]:
            result.update(status="failed", error=item["error"])
            print(f"FAIL [{index}] {label}: {item['error']}")
            results.append(result)
            continue

        with tempfile.TemporaryDirectory(prefix="zignet-zig016-") as tmp:
            source_path = Path(tmp) / "snippet.zig"
            source_path.write_text(item["source"], encoding="utf-8")
            command = ["zig", "test", "--color", "off", str(source_path)]
            run = subprocess.run(command, capture_output=True, text=True, check=False)
            result.update(
                status="passed" if run.returncode == 0 else "failed",
                command="zig test --color off <snippet>",
                returncode=run.returncode,
                stdout=run.stdout[-3000:],
                stderr=run.stderr[-3000:],
            )
            if run.returncode == 0:
                print(f"PASS [{index}] {label}")
            else:
                result["error"] = "zig test exited non-zero"
                print(f"FAIL [{index}] {label}: zig test exited {run.returncode}")
                if run.stderr:
                    print(run.stderr[-1500:])
            results.append(result)

    passed = sum(row["status"] == "passed" for row in results)
    failed = len(results) - passed
    print(f"\nZig {actual}: {passed}/{len(results)} records passed; {failed} failed. Batch range: {args.offset + 1}-{args.offset + len(results)} of {len(all_records)}.")
    report = {
        "zig_version": actual,
        "data_dir": str(args.data_dir),
        "offset": args.offset,
        "limit": args.limit,
        "total_records": len(all_records),
        "passed": passed,
        "failed": failed,
        "results": results,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Report written to {args.report}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
