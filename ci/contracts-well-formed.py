#!/usr/bin/env python3
"""contracts.yaml parses, covers twelve primitives, and every field is present.

The check that matters here is that no requirement ships without its falsifier.
A requirement whose `check` cannot be written is vapid by construction, and the
whole point of making the field required is to surface that while authoring
rather than in front of a client. An empty string passes yaml and fails this.

Signal ids cite gxproof for traceability. The citation is one way and gxproof
does not read this file, so a stale id is an inaccurate cross reference rather
than a broken scorer: it is reported as a warning when gxproof is checked out
here, and ignored when it is not.
"""

import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SIGNALS = ROOT.parent / "gxproof" / "src" / "gxproof" / "data" / "signals.yaml"

KEYS = [
    "instruction",
    "context_delivery",
    "context_management",
    "tool_interface",
    "execution_environment",
    "durable_state",
    "orchestration",
    "sub_agents",
    "skills",
    "verification",
    "observability",
    "governance",
]
TARGET_FIELDS = ("requirement", "artifact", "evidence", "check", "signals")
ENTRY_FIELDS = ("anti_pattern", "compounding", "cost")

failures = []


def fail(message):
    failures.append(message)


def main():
    try:
        doc = yaml.safe_load((ROOT / "contracts.yaml").read_text())
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        print(f"FAIL contracts.yaml does not parse{where}: {getattr(error, 'problem', error)}")
        print(
            "     Fix the yaml before anything else here can run. A long field "
            "usually wants the folded block form, 'check: >-' on its own line "
            "with the text indented beneath it."
        )
        return 1

    for field in ("contracts_version", "spec_version"):
        if not str(doc.get(field, "")).strip():
            fail(f"top level: {field} is missing or empty")

    entries = doc.get("contracts") or []
    keys = [e.get("key") for e in entries]
    if keys != KEYS:
        fail(f"primitives are wrong or out of spec order: {keys}")

    cited = set()
    for entry in entries:
        key = entry.get("key", "<unkeyed>")
        if not re.fullmatch(r"\d{2}", str(entry.get("id", ""))):
            fail(f"{key}: id must be a two digit string")
        for field in ENTRY_FIELDS:
            if not str(entry.get(field, "")).strip():
                fail(f"{key}: {field} is missing or empty")
        targets = entry.get("targets") or {}
        if set(targets) != {"3", "4"}:
            fail(f"{key}: targets must be exactly 3 and 4, found {sorted(targets)}")
            continue
        for level, target in targets.items():
            for field in TARGET_FIELDS:
                value = target.get(field)
                if field == "signals":
                    if not isinstance(value, list) or not value:
                        fail(f"{key} level {level}: signals must be a non-empty list")
                    else:
                        cited.update(value)
                elif not str(value or "").strip():
                    fail(f"{key} level {level}: {field} is missing or empty")

    # Definitions live in the spec. Restating them here is how drift starts.
    for entry in entries:
        for borrowed in ("definition", "na_condition", "limit", "severity", "control_type"):
            if borrowed in entry:
                fail(
                    f"{entry.get('key')}: '{borrowed}' belongs to the spec and "
                    "must not be restated in contracts.yaml"
                )

    if SIGNALS.exists():
        real = set(re.findall(r"- id: (\w+)", SIGNALS.read_text()))
        for stale in sorted(cited - real):
            print(f"warn: signal '{stale}' is not in gxproof signals.yaml")

    if failures:
        for message in failures:
            print(f"FAIL {message}")
        return 1
    print(f"OK 12 primitives, {len(cited)} signals cited, every check present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
