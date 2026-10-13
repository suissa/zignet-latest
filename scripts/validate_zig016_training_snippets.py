#!/usr/bin/env python3
"""Compile every Zig 0.16.0 target snippet found in the migration JSONL dataset."""
from __future__ import annotations
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

FENCE_RE = re.compile(r"\`\`\`(?:zig)?[ \t]*\r?\n(.*?)\`\`\`", re.DOTALL | re.IGNORECASE)
TARGET_LABEL_RE = re.compile(r"Alvo\s+0\.16\.0\s*:", re.IGNORECASE)

def is_executable_zig(source: str) -> bool:
    remaining = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    lines = [re.sub(r"//.*$", "", line).strip() for line in remaining.splitlines()]
    return any(lines)

def load_target_snippets(path: Path) -> list[dict[str, Any]]:
    snippets = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            output = record.get("output")
            if not isinstance(output, str):
                raise ValueError(f"{path}:{line_number}: output must be a string")
            target = TARGET_LABEL_RE.search(output)
            meta = record.get("metadata") or {}
            common = {"file": str(path), "line": line_number, "scenario": meta.get("scenario", "unknown")}
            if not target:
                snippets.append({**common, "source": "", "error": 'missing "Alvo 0.16.0:" section'})
                continue
            fence = FENCE_RE.search(output[target.end():])
            if not fence:
                snippets.append({**common, "source": "", "error": "target section has no fenced Zig snippet"})
                continue
            snippets.append({**common, "source": fence.group(1).strip() + "\n"})
    return snippets

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "training" / "v0.16.0")
    parser.add_argument("--zig-version", default="0.16.0")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    version = subprocess.run(["zig", "version"], capture_output=True, text=True, check=False)
    actual = version.stdout.strip()
    if version.returncode or actual != args.zig_version:
        print(f"ERROR: expected Zig {args.zig_version}, got {actual or version.stderr.strip() or 'unavailable'}", file=sys.stderr)
        return 2
    excluded = {"dataset-train.jsonl", "dataset-validation.jsonl", "dataset-test.jsonl"}
    files = sorted(p for p in args.data_dir.glob("*.jsonl") if p.name not in excluded)
    if not files:
        print(f"ERROR: no category JSONL files found in {args.data_dir}", file=sys.stderr)
        return 2
    results = []
    for path in files:
        try:
            snippets = load_target_snippets(path)
        except (OSError, ValueError) as exc:
            results.append({"file": str(path), "status": "failed", "error": str(exc)})
            continue
        for index, item in enumerate(snippets, start=1):
            location = f"{path.name}:{item['line']} ({item['scenario']})"
            if item.get("error"):
                item["status"] = "failed"
                print(f"FAIL {location}: {item['error']}")
                results.append(item)
                continue
            source = item["source"]
            if not is_executable_zig(source):
                item["status"] = "failed"
                item["error"] = "target snippet is empty or comment-only; no Zig code is being tested"
                print(f"FAIL {location}: {item['error']}")
                results.append(item)
                continue
            with tempfile.TemporaryDirectory(prefix="zignet-zig016-") as tmp:
                source_path = Path(tmp) / f"snippet-{index}.zig"
                source_path.write_text(source, encoding="utf-8")
                command = ["zig", "test", str(source_path), "--color", "off"]
                run = subprocess.run(command, capture_output=True, text=True, check=False)
                item.update({
                    "command": "zig test <snippet> --color off",
                    "returncode": run.returncode,
                    "stdout": run.stdout[-4000:],
                    "stderr": run.stderr[-4000:],
                    "status": "passed" if run.returncode == 0 else "failed",
                })
                if run.returncode == 0:
                    print(f"PASS {location}")
                else:
                    item["error"] = "zig test exited non-zero"
                    print(f"FAIL {location}: zig test exited {run.returncode}")
                    if run.stderr:
                        print(run.stderr[-2000:])
                results.append(item)
    passed = sum(item.get("status") == "passed" for item in results)
    failed = len(results) - passed
    report = {"zig_version": actual, "data_dir": str(args.data_dir), "snippets_checked": len(results), "passed": passed, "failed": failed, "results": results}
    print(f"\nZig {actual}: {passed}/{len(results)} target snippets passed; {failed} failed.")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Report written to {args.report}")
    return 0 if results and failed == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
