#!/usr/bin/env python3
"""Check that an assessment's scores.yaml is true before anyone renders it.

    python3 report/verify.py <project-dir> [--run] [--contracts path]

scores.yaml is hand-written during step 5 and is the file every downstream
artifact trusts: the report, the remediation briefs, any comparison across
projects. A stale one produces a confident, wrong page with confident, wrong
work orders attached, which is worse than no page at all. This is the sensor for
the kit's own output.

Four kinds of check, cheapest first:

  structure    the twelve keys, in spec order, with valid control types and
               scores in range
  coherence    claims that contradict each other inside the file: a row short of
               target with no gap, an overall that is not the minimum, a set_by
               that does not name a primitive actually at the floor
  currency     scores.yaml older than the proof documents or the sensor sources
               it describes, and a spec version that does not match the
               contracts the briefs quote
  enforcement  every unenforced check id appears in an instruction file, every
               sensor names a script that exists, and with --run, every sensor
               actually runs and passes

--run executes commands out of scores.yaml. That is opt-in on purpose: this tool
is pointed at other people's repositories, and a verifier that silently runs
whatever a YAML file tells it to is its own finding.
"""

import argparse
import pathlib
import re
import shlex
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("FAIL PyYAML is required: python3 -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

KEYS = [
    "instruction", "context_delivery", "context_management", "tool_interface",
    "execution_environment", "durable_state", "orchestration", "sub_agents",
    "skills", "verification", "observability", "governance",
]
CONTROLS = {"guide", "sensor", "both"}
RISKS = {"internal", "client_facing", "regulated"}
INSTRUCTION_FILES = ["AGENTS.md", "CLAUDE.md", ".cursorrules"]


class Report:
    def __init__(self):
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def fail(self, where: str, what: str, fix: str) -> None:
        self.failures.append(f"FAIL {where}: {what}\n     {fix}")

    def warn(self, where: str, what: str) -> None:
        self.warnings.append(f"warn {where}: {what}")

    def ok(self) -> bool:
        return not self.failures


def check_structure(data: dict, r: Report) -> None:
    prims = data.get("primitives") or []
    keys = [p.get("key") for p in prims]
    if keys != KEYS:
        missing = [k for k in KEYS if k not in keys]
        extra = [k for k in keys if k not in KEYS]
        detail = f"missing {missing}" if missing else f"unexpected {extra}" if extra else "out of spec order"
        r.fail("primitives", f"not the twelve in spec order, {detail}",
               "Every primitive is scored, including the ones at N/A. A missing row is not a zero.")
        return
    for p in prims:
        key = p["key"]
        for field in ("baseline", "current", "target"):
            v = p.get(field)
            if not isinstance(v, int) or not 0 <= v <= 5:
                r.fail(key, f"{field} is {v!r}, not an integer 0 to 5",
                       "N/A rows are recorded in target.yaml, not scored here.")
        if p.get("control") not in CONTROLS:
            r.fail(key, f"control is {p.get('control')!r}",
                   f"Must be one of {sorted(CONTROLS)}, from spec section 2.3.")
        if not str(p.get("evidence") or "").strip():
            r.fail(key, "no evidence",
                   "A score without evidence is an opinion. Name a path, or say where you looked.")
    risk = data.get("risk", "internal")
    if risk not in RISKS:
        r.fail("risk", f"{risk!r} is not recognised",
               f"One of {sorted(RISKS)}. It decides remediation order.")


def check_coherence(data: dict, r: Report) -> None:
    prims = data.get("primitives") or []
    if not prims or any(not isinstance(p.get("current"), int) for p in prims):
        return  # structure already failed; do not pile on
    for p in prims:
        key, cur, tgt = p["key"], p["current"], p["target"]
        gap = str(p.get("gap") or "").strip()
        if cur < tgt and not gap:
            r.fail(key, f"is {cur} against a target of {tgt} and states no gap",
                   "Say what stands between them. A shortfall with no gap produces an empty work order.")
        if cur >= tgt and gap:
            r.fail(key, f"is {cur}, at or above its target of {tgt}, but still states a gap",
                   "Clear the gap or lower the score. The report will call this row met and print the gap anyway.")
        if p["baseline"] > cur:
            r.warn(key, f"regressed from {p['baseline']} to {cur}. Intended?")
        if p.get("control") == "guide" and cur > 3:
            r.fail(key, f"is carried by a guide and scores {cur}",
                   "A primitive carried only by a guide caps at 3. Name the sensor, or lower the score.")

    overall = data.get("overall") or {}
    floor = min(p["current"] for p in prims)
    if overall.get("current") != floor:
        r.fail("overall.current", f"says {overall.get('current')}, the minimum is {floor}",
               "The overall level is the minimum across applicable primitives, never the average.")
    at_floor = [p["key"] for p in prims if p["current"] == floor]
    if overall.get("set_by") not in at_floor:
        r.fail("overall.set_by", f"names {overall.get('set_by')!r}, which is not at the floor",
               f"At the floor: {', '.join(at_floor)}.")


def check_currency(project: pathlib.Path, data: dict, contracts_doc: dict, r: Report) -> None:
    scores = project / "harness" / "scores.yaml"
    stamp = scores.stat().st_mtime
    newer = []
    proofs = sorted((project / "harness" / "proof").glob("*.md"))
    for f in proofs:
        if f.stat().st_mtime > stamp:
            newer.append(f.relative_to(project).as_posix())
    for s in data.get("sensors") or []:
        for token in shlex.split(str(s.get("check", ""))):
            candidate = project / token
            if candidate.exists() and candidate.is_file() and candidate.stat().st_mtime > stamp:
                newer.append(candidate.relative_to(project).as_posix())
    if newer:
        r.fail("scores.yaml", f"is older than {', '.join(sorted(set(newer)))}",
               "Something changed after the scores were written. Re-read it and restate the scores, "
               "or touch the file once you have confirmed it is still true.")
    if not proofs:
        r.warn("harness/proof/", "no proof documents. Step 5 records the negative controls there.")

    for field in ("spec_version", "contracts_version"):
        theirs, ours = data.get(field), contracts_doc.get(field)
        if theirs != ours:
            r.fail(field, f"assessment says {theirs!r}, harness-kit says {ours!r}",
                   "The briefs quote the contracts. Rescore against this vintage, or render with the "
                   "contracts the assessment was scored against.")


def check_enforcement(project: pathlib.Path, data: dict, run: bool, r: Report) -> None:
    instructions = ""
    found = []
    for name in INSTRUCTION_FILES:
        f = project / name
        if f.exists():
            instructions += f.read_text(errors="ignore")
            found.append(name)
    if not found:
        r.warn("instruction file", f"none of {', '.join(INSTRUCTION_FILES)} found")

    for u in data.get("unenforced") or []:
        check = str(u.get("check", ""))
        if found and check and check not in instructions:
            r.fail("unenforced", f"{check} is claimed but appears in no instruction file",
                   f"Mark the rule it carries in {found[0]} with the unenforced token and this id, "
                   "so a scan reports it as a work item.")

    for s in data.get("sensors") or []:
        sid = s.get("id", "?")
        tokens = shlex.split(str(s.get("check", "")))
        scripts = [t for t in tokens if "/" in t or t.endswith((".py", ".mjs", ".sh", ".js", ".ts"))]
        for script in scripts:
            if not (project / script).exists():
                r.fail(f"sensor {sid}", f"names {script}, which does not exist",
                       "A sensor whose script is gone is not a control. Fix the path or drop the sensor.")
        if not s.get("negative_controls"):
            r.fail(f"sensor {sid}", "records no negative controls",
                   "A check never observed failing has not been shown able to fail. Break it, watch it "
                   "go red, and record the count.")
        if s.get("blocking") is not True:
            r.warn(f"sensor {sid}", "is not marked blocking. A check that reports and does not gate caps its primitive at 3.")

    if not run:
        return
    for s in data.get("sensors") or []:
        sid = s.get("id", "?")
        cmd = str(s.get("check", ""))
        if not cmd:
            continue
        try:
            proc = subprocess.run(shlex.split(cmd), cwd=project, capture_output=True,
                                  text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as err:
            r.fail(f"sensor {sid}", f"could not run: {err}",
                   "The assessment claims this enforces a score. If it cannot run, it does not.")
            continue
        if proc.returncode != 0:
            tail = (proc.stdout + proc.stderr).strip().splitlines()
            r.fail(f"sensor {sid}", f"is red (exit {proc.returncode}): {tail[-1] if tail else 'no output'}",
                   "The assessment scores this primitive as enforced. Green it or lower the score.")


def verify(project: pathlib.Path, data: dict, contracts_doc: dict, run: bool = False) -> Report:
    r = Report()
    check_structure(data, r)
    check_coherence(data, r)
    check_currency(project, data, contracts_doc, r)
    check_enforcement(project, data, run, r)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a harness assessment before it is rendered.")
    ap.add_argument("project", type=pathlib.Path)
    ap.add_argument("--run", action="store_true",
                    help="also execute each sensor's check. Runs commands from scores.yaml; opt-in.")
    ap.add_argument("--contracts", type=pathlib.Path,
                    default=pathlib.Path(__file__).resolve().parent.parent / "contracts.yaml")
    args = ap.parse_args()

    scores = args.project / "harness" / "scores.yaml"
    if not scores.exists():
        print(f"FAIL {scores} not found. Step 5 of TRANSFORM.md writes it.", file=sys.stderr)
        return 1

    data = yaml.safe_load(scores.read_text())
    contracts_doc = yaml.safe_load(args.contracts.read_text()) if args.contracts.exists() else {}
    r = verify(args.project, data, contracts_doc, args.run)

    for w in r.warnings:
        print(w)
    for f in r.failures:
        print(f)
    if r.ok():
        n = len(data.get("primitives") or [])
        ran = ", sensors run" if args.run else ""
        print(f"OK scores.yaml is internally consistent and current ({n} primitives{ran})")
        return 0
    print(f"\n{len(r.failures)} failure(s). Do not render this assessment until they are closed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
