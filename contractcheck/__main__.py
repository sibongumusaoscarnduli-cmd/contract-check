from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import ContractError, load_document, report, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contractcheck", description="Check an OpenAPI JSON contract against a local service.")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run", help="run response checks for supported operations")
    command.add_argument("schema", help="path to an OpenAPI 3 JSON document")
    command.add_argument("--url", required=True, help="local base URL, for example http://127.0.0.1:8070")
    command.add_argument("--json", dest="json_path", help="write a machine-readable report to this path")
    args = parser.parse_args(argv)
    try:
        result = report(run(load_document(args.schema), args.url))
    except ContractError as exc:
        print(f"Safety or contract error: {exc}", file=sys.stderr)
        return 2
    print(f"ContractCheck: {result['summary']['passed']}/{result['summary']['total']} operations passed")
    for item in result["checks"]:
        mark = "PASS" if item["passed"] else "FAIL"
        print(f"{mark:4} {item['method']} {item['path']} (expected {item['expected_status']}, received {item['actual_status']})")
        for finding in item["findings"]:
            print(f"     {finding}")
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
