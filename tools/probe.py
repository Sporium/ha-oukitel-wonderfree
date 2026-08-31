#!/usr/bin/env python3
"""Helpers for turning a Wonderfree traffic capture into api.py's field map.

Two modes:

  paths <file.json>          Print every leaf path in a captured response with
                             its value, so the telemetry fields can be picked
                             out and pasted into FIELD_MAP.

  call <method> <url>        Replay a captured request, optionally with a
                             bearer token and a JSON body, and pretty-print the
                             response. Useful for confirming an endpoint still
                             answers outside the app.

Deliberately dependency-free apart from `requests`, so it can run anywhere.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def leaf_paths(node: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Flatten a payload into (dotted path, value) pairs."""
    out: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            out.extend(leaf_paths(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            out.extend(leaf_paths(value, f"{prefix}.{index}"))
    else:
        out.append((prefix, node))
    return out


def cmd_paths(args: argparse.Namespace) -> int:
    with open(args.file, encoding="utf-8") as handle:
        payload = json.load(handle)

    rows = leaf_paths(payload)
    if args.numeric:
        rows = [(p, v) for p, v in rows if isinstance(v, (int, float))
                and not isinstance(v, bool)]

    width = max((len(p) for p, _ in rows), default=0)
    for path, value in rows:
        print(f"{path:<{width}}  =  {value!r}")
    print(f"\n{len(rows)} leaves", file=sys.stderr)
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    try:
        import requests
    except ImportError:
        print("pip install requests", file=sys.stderr)
        return 1

    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    for raw in args.header or []:
        name, _, value = raw.partition(":")
        headers[name.strip()] = value.strip()

    body = json.loads(args.data) if args.data else None
    response = requests.request(
        args.method.upper(), args.url, headers=headers, json=body, timeout=30
    )
    print(f"HTTP {response.status_code}", file=sys.stderr)
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print(response.text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_paths = sub.add_parser("paths", help="flatten a captured JSON response")
    p_paths.add_argument("file")
    p_paths.add_argument(
        "--numeric", action="store_true", help="only numeric leaves (telemetry)"
    )
    p_paths.set_defaults(func=cmd_paths)

    p_call = sub.add_parser("call", help="replay a captured request")
    p_call.add_argument("method")
    p_call.add_argument("url")
    p_call.add_argument("--token")
    p_call.add_argument("--header", action="append")
    p_call.add_argument("--data")
    p_call.set_defaults(func=cmd_call)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
