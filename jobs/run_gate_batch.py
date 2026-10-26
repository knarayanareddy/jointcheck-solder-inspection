"""Evaluate JSONL measurement assertions with the local fail-closed rule gate."""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Any, TextIO

# Make the backend package importable when invoked from a source checkout.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.gate.gate import DeterministicGate


def process(input_stream: TextIO, output_stream: TextIO) -> int:
    processed = 0
    for line_number, line in enumerate(input_stream, start=1):
        if not line.strip():
            continue
        try:
            request: Any = json.loads(line)
            if not isinstance(request, dict):
                raise TypeError("each JSONL record must be an object")
            rule_id = request.get("rule_id")
            assertion = request.get("assertion")
            if not isinstance(rule_id, str) or not isinstance(assertion, dict):
                raise TypeError("record requires string rule_id and object assertion")
        except (json.JSONDecodeError, TypeError) as exc:
            print(f"invalid input at line {line_number}: {exc}", file=sys.stderr)
            return 2
        result = DeterministicGate.evaluate(rule_id, assertion)
        output_stream.write(json.dumps(result, allow_nan=False) + "\n")
        processed += 1
    output_stream.flush()
    return 0 if processed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input JSONL file, or '-' for stdin")
    parser.add_argument(
        "--output", default="-", help="Output JSONL file (default: stdout)"
    )
    args = parser.parse_args()

    with ExitStack() as stack:
        input_stream = (
            sys.stdin
            if args.input == "-"
            else stack.enter_context(open(args.input, encoding="utf-8"))
        )
        output_stream = (
            sys.stdout
            if args.output == "-"
            else stack.enter_context(open(args.output, "w", encoding="utf-8"))
        )
        return process(input_stream, output_stream)


if __name__ == "__main__":
    raise SystemExit(main())
