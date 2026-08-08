#!/usr/bin/env python3
"""Render a harness assessment as one self-contained HTML file.

    python3 report/render.py <project-dir> [-o out.html]

Reads <project-dir>/harness/scores.yaml, the machine-readable result of the
transform, and writes a single file with no external requests. It runs on the
reviewer's machine, never inside the assessed project, so the promise that
harness-kit installs nothing into a target repository still holds.

The page is built around the rule that decides the number: the overall level is
the minimum across applicable primitives, never the average. The primitive that
sets the floor is named at the top and marked in the table, because a report
that buries it invites the reader to average twelve numbers in their head.

Requires PyYAML, which harness-kit's own CI already uses.
"""

import argparse
import html
import pathlib
import sys

from verify import verify

try:
    import yaml
except ImportError:
    print("FAIL PyYAML is required: python3 -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

ANCHORS = {
    0: "Absent",
    1: "Ad hoc",
    2: "Partial",
    3: "Defined",
    4: "Managed",
    5: "Compounding",
}

# Spec 0.2.0-draft section 2.2. Execution environment is exempt and sequenced
# first by severity, because its gaps are security findings rather than maturity
# observations. Anything unlisted falls after, in primitive order.
REMEDIATION_ORDER = [
    "execution_environment",
    "tool_interface",
    "context_management",
    "durable_state",
    "orchestration",
    "instruction",
]


TRUST_LAYER = ("verification", "observability", "governance")


def remediation_rank(key: str, all_keys: list, risk: str = "internal") -> int:
    """Order the work.

    The spec ranks by business risk first: verification, observability and
    governance outrank everything for regulated or client-facing work, because
    capability without trust is a liability. Only where risk is comparable does
    the ablation-derived sequence break the tie. Execution environment is exempt
    from both and sequenced first by severity, since its gaps are security
    findings.

    `risk` comes from scores.yaml. Defaulting to internal is the conservative
    choice: it declines to reorder the list on an assumption the assessment did
    not state.
    """
    if key == "execution_environment":
        return 0
    if risk in ("client_facing", "regulated") and key in TRUST_LAYER:
        return 1 + TRUST_LAYER.index(key)
    base = 10
    if key in REMEDIATION_ORDER:
        return base + REMEDIATION_ORDER.index(key)
    return base + len(REMEDIATION_ORDER) + all_keys.index(key)


def build_prompt(p: dict, contract: dict, project: str) -> str:
    """The paste-into-your-agent brief for one gap.

    Deliberately plain text and vendor-neutral: it goes into Claude Code, Codex,
    Cursor or a chat window without editing. The generic half is the contract's
    own level-4 text from harness-kit, so the requirement and its falsifying
    check are the same words that defined the gap; the specific half is this
    project's evidence and shortfall. Neither half is paraphrased, because a
    paraphrased requirement is how a check ends up testing something adjacent.
    """
    target = str(p["target"])
    spec = (contract.get("targets") or {}).get(target, {})
    lines = [
        f'Raise primitive {p["id"]} {p["name"]} from {p["current"]} to {p["target"]} in {project}.',
        "",
        "This is the twelve-primitive agent harness maturity model. The overall level is",
        "the minimum across primitives, never the average, so this one is holding the",
        "system down. A primitive carried only by a guide caps at 3: to reach 4 the rule",
        "must be enforced by something that fails when it is broken.",
        "",
        "WHAT IS THERE NOW",
        f'  {" ".join(str(p.get("evidence", "")).split())}',
        "",
        "THE GAP",
        f'  {" ".join(str(p.get("gap") or "").split())}',
        "",
    ]
    if spec.get("requirement"):
        lines += [f"REQUIREMENT FOR LEVEL {target}", f'  {" ".join(spec["requirement"].split())}', ""]
    if spec.get("artifact"):
        lines += ["ARTIFACT TO PRODUCE", f'  {" ".join(spec["artifact"].split())}', ""]
    if spec.get("check"):
        lines += [
            "ACCEPTANCE, AND THE ONLY THING THAT COUNTS AS DONE",
            f'  {" ".join(spec["check"].split())}',
            "",
        ]
    if contract.get("anti_pattern"):
        lines += ["DO NOT SHIP THIS INSTEAD", f'  {" ".join(contract["anti_pattern"].split())}', ""]
    lines += [
        "RULES FOR THE WORK",
        "  Read the code before proposing a change. Smallest diff that actually enforces",
        "  the rule; no new dependency for something a few lines can do.",
        "  The check must run on every change and must block, not warn. A check that",
        "  reports and does not gate leaves this primitive at 3.",
        "  Its failure message names the fix, not just the failure, because an agent",
        "  reads that message and acts on it.",
        "  Break the thing deliberately, watch the check go red, and paste that output",
        "  into the proof. A check never observed failing has not been shown able to fail.",
        "  Then name the check in the instruction file on the rule it carries, and remove",
        "  that rule's unenforced marker.",
    ]
    return "\n".join(lines)

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --ground:#f7f8fa; --surface:#ffffff; --sunken:#eef1f4;
  --ink:#16191d; --slate:#5a6470; --faint:#8b949e;
  --rule:#dde1e5; --rule-strong:#c6ccd3;
  --enforced:#0e7c86; --enforced-soft:#d7ecee;
  --guide:#b26b00; --guide-soft:#f6e8d0;
  --floor:#a8322d; --floor-soft:#f7dedc;
  --track:#e3e7eb;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#14171a; --surface:#1c2024; --sunken:#22272c;
    --ink:#e6e9ec; --slate:#9aa4ae; --faint:#6f7983;
    --rule:#2b3137; --rule-strong:#3a424a;
    --enforced:#3fb3bd; --enforced-soft:#123b40;
    --guide:#d9931f; --guide-soft:#3d2f14;
    --floor:#e06b62; --floor-soft:#40201e;
    --track:#2b3137;
  }
}
:root[data-theme="dark"]{
  --ground:#14171a; --surface:#1c2024; --sunken:#22272c;
  --ink:#e6e9ec; --slate:#9aa4ae; --faint:#6f7983;
  --rule:#2b3137; --rule-strong:#3a424a;
  --enforced:#3fb3bd; --enforced-soft:#123b40;
  --guide:#d9931f; --guide-soft:#3d2f14;
  --floor:#e06b62; --floor-soft:#40201e;
  --track:#2b3137;
}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:var(--sans); font-size:16px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:60rem;margin:0 auto;padding:3rem 1.5rem 5rem;display:flex;flex-direction:column;gap:3rem}
h1,h2,h3{text-wrap:balance;margin:0;font-weight:640;letter-spacing:-0.012em}
h1{font-size:1.75rem}
h2{font-size:1.0625rem}
p{margin:0}
.eyebrow{
  font-family:var(--mono); font-size:0.6875rem; text-transform:uppercase;
  letter-spacing:0.1em; color:var(--faint);
}
.lede{color:var(--slate);max-width:62ch}

/* Header ------------------------------------------------------------- */
header{display:flex;flex-direction:column;gap:1.5rem}
.masthead{display:flex;flex-wrap:wrap;gap:2rem;align-items:flex-end;justify-content:space-between}
.score{display:flex;align-items:baseline;gap:0.75rem}
.score .n{
  font-family:var(--mono); font-size:4.5rem; line-height:0.85; font-weight:600;
  letter-spacing:-0.04em; color:var(--floor); font-variant-numeric:tabular-nums;
}
.score .of{font-family:var(--mono);font-size:1.125rem;color:var(--faint)}
.score .anchor{font-size:0.9375rem;color:var(--slate)}
.floorcall{
  border-left:3px solid var(--floor); background:var(--floor-soft);
  padding:0.875rem 1.125rem; border-radius:0 6px 6px 0; max-width:62ch;
}
.floorcall strong{font-family:var(--mono);font-weight:600}

/* Table -------------------------------------------------------------- */
.tablewrap{overflow-x:auto;border:1px solid var(--rule);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;min-width:44rem}
caption{text-align:left;padding:1rem 1.125rem 0;font-size:0.875rem;color:var(--slate)}
th{
  text-align:left; font-family:var(--mono); font-size:0.6875rem; font-weight:600;
  text-transform:uppercase; letter-spacing:0.08em; color:var(--faint);
  padding:0.875rem 0.75rem; border-bottom:1px solid var(--rule-strong);
}
td{padding:0.8125rem 0.75rem;border-bottom:1px solid var(--rule);vertical-align:top}
tr:last-child td{border-bottom:none}
td:first-child,th:first-child{padding-left:1.125rem}
td:last-child,th:last-child{padding-right:1.125rem}
.pid{font-family:var(--mono);color:var(--faint);font-variant-numeric:tabular-nums}
.pname{font-weight:560}
.pnote{display:block;color:var(--slate);font-size:0.8125rem;margin-top:0.25rem;max-width:46ch}
tr.is-floor{background:var(--floor-soft)}
tr.is-floor .pname{color:var(--floor)}

/* 0-5 track ---------------------------------------------------------- */
.track{display:flex;gap:3px;align-items:center}
.cell{
  width:1.375rem;height:0.5rem;border-radius:2px;background:var(--track);position:relative;
}
.cell.filled{background:var(--enforced)}
.cell.gained{background:var(--enforced);opacity:0.55}
.cell.target::after{
  content:"";position:absolute;inset:-4px -1px;border:1.5px dashed var(--slate);
  border-radius:4px;
}
tr.is-floor .cell.filled{background:var(--floor)}
.trackmeta{font-family:var(--mono);font-size:0.75rem;color:var(--slate);font-variant-numeric:tabular-nums;white-space:nowrap}
.delta{color:var(--enforced);font-weight:600}

/* Chips -------------------------------------------------------------- */
.chip{
  display:inline-block;font-family:var(--mono);font-size:0.6875rem;font-weight:600;
  padding:0.1875rem 0.5rem;border-radius:3px;letter-spacing:0.03em;white-space:nowrap;
}
.chip.sensor{background:var(--enforced-soft);color:var(--enforced)}
.chip.guide{background:var(--guide-soft);color:var(--guide)}
.chip.both{background:var(--sunken);color:var(--slate);border:1px solid var(--rule-strong)}
.chip.met{background:var(--enforced-soft);color:var(--enforced)}
.chip.short{background:var(--guide-soft);color:var(--guide)}

/* Cards -------------------------------------------------------------- */
section{display:flex;flex-direction:column;gap:1rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(17rem,1fr));gap:0.875rem}
.card{
  background:var(--surface);border:1px solid var(--rule);border-radius:8px;
  padding:1rem 1.125rem;display:flex;flex-direction:column;gap:0.5rem;
}
.card.gap{border-left:3px solid var(--guide)}
.card.sensor{border-left:3px solid var(--enforced)}
.card h3{font-family:var(--mono);font-size:0.8125rem;font-weight:600}
.card p{font-size:0.875rem;color:var(--slate)}
.card .for{font-family:var(--mono);font-size:0.6875rem;color:var(--faint);text-transform:uppercase;letter-spacing:0.06em}

/* Remediation -------------------------------------------------------- */
.fix{background:var(--surface);border:1px solid var(--rule);border-radius:8px;overflow:hidden}
.fix + .fix{margin-top:0.875rem}
.fixhead{
  display:flex;flex-wrap:wrap;gap:0.75rem;align-items:center;justify-content:space-between;
  padding:0.9375rem 1.125rem;border-bottom:1px solid var(--rule);
}
.fixtitle{display:flex;align-items:baseline;gap:0.625rem;flex-wrap:wrap}
.fixtitle .seq{
  font-family:var(--mono);font-size:0.6875rem;color:var(--surface);background:var(--slate);
  padding:0.125rem 0.4375rem;border-radius:3px;font-weight:600;
}
.fixtitle .name{font-weight:600}
.fixtitle .move{font-family:var(--mono);font-size:0.8125rem;color:var(--slate);font-variant-numeric:tabular-nums}
.fixwhy{padding:0 1.125rem 0.9375rem;color:var(--slate);font-size:0.875rem;max-width:64ch}
button.copy{
  font:inherit;font-family:var(--mono);font-size:0.75rem;font-weight:600;cursor:pointer;
  background:var(--enforced);color:#fff;border:none;padding:0.4375rem 0.8125rem;border-radius:5px;
}
button.copy:hover{filter:brightness(1.08)}
button.copy:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
button.copy[data-done="1"]{background:var(--slate)}
details.prompt{border-top:1px solid var(--rule)}
details.prompt summary{
  cursor:pointer;padding:0.6875rem 1.125rem;font-family:var(--mono);font-size:0.75rem;
  color:var(--slate);list-style:none;
}
details.prompt summary::-webkit-details-marker{display:none}
details.prompt summary::before{content:"\\25B8  ";color:var(--faint)}
details.prompt[open] summary::before{content:"\\25BE  "}
details.prompt pre{
  margin:0;padding:0 1.125rem 1.125rem;overflow-x:auto;background:var(--sunken);
  font-family:var(--mono);font-size:0.75rem;line-height:1.6;color:var(--ink);
  white-space:pre-wrap;word-break:break-word;
}
.sev{font-family:var(--mono);font-size:0.6875rem;color:var(--floor);font-weight:600;letter-spacing:0.04em}

/* Legend and footer -------------------------------------------------- */
.legend{display:flex;flex-wrap:wrap;gap:1.25rem;font-size:0.8125rem;color:var(--slate)}
.legend span{display:flex;align-items:center;gap:0.4375rem}
.key{width:1.375rem;height:0.5rem;border-radius:2px;flex:none}
.key.f{background:var(--enforced)} .key.g{background:var(--enforced);opacity:0.55}
.key.t{background:var(--track);border:1.5px dashed var(--slate)}
footer{border-top:1px solid var(--rule);padding-top:1.25rem;color:var(--faint);font-size:0.8125rem;display:flex;flex-direction:column;gap:0.375rem}
footer code{font-family:var(--mono)}
a{color:var(--enforced)}
a:focus-visible,summary:focus-visible{outline:2px solid var(--enforced);outline-offset:2px;border-radius:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:34rem){.score .n{font-size:3.25rem}.wrap{padding:2rem 1rem 3rem;gap:2.25rem}}
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def track(baseline: int, current: int, target: int) -> str:
    cells = []
    for level in range(6):
        classes = ["cell"]
        if level <= baseline and level > 0:
            classes.append("filled")
        elif baseline < level <= current:
            classes.append("gained")
        if level == target:
            classes.append("target")
        cells.append(f'<span class="{" ".join(classes)}"></span>')
    moved = current - baseline
    meta = f"{baseline}"
    if moved:
        meta += f' <span class="delta">&rarr; {current}</span>'
    meta += f" / {target}"
    return (
        f'<div class="track">{"".join(cells)}</div>'
        f'<div class="trackmeta">{meta}</div>'
    )


def render(data: dict, contracts: dict) -> str:
    overall = data.get("overall", {})
    prims = data.get("primitives", [])
    floor_key = overall.get("set_by")
    current = overall.get("current", 0)
    project = data.get("project", "this project")

    rows = []
    for p in prims:
        met = p["current"] >= p["target"]
        is_floor = p.get("key") == floor_key
        control = p.get("control", "both")
        note = p.get("gap") or p.get("note") or ""
        rows.append(
            f'<tr class="{"is-floor" if is_floor else ""}">'
            f'<td class="pid">{esc(p["id"])}</td>'
            f'<td><span class="pname">{esc(p["name"])}</span>'
            f'{f"<span class=pnote>{esc(note)}</span>" if note else ""}</td>'
            f'<td><span class="chip {esc(control)}">{esc(control)}</span></td>'
            f'<td>{track(p["baseline"], p["current"], p["target"])}</td>'
            f'<td><span class="chip {"met" if met else "short"}">'
            f'{"met" if met else "short"}</span></td>'
            f"</tr>"
        )

    gaps = "".join(
        f'<article class="card gap"><span class="for">primitive {esc(u["primitive"])}</span>'
        f'<h3>{esc(u["check"])}</h3><p>{esc(u["rule"])}</p></article>'
        for u in data.get("unenforced", [])
    )
    sensors = "".join(
        f'<article class="card sensor"><span class="for">primitive {esc(s["primitive"])}'
        f'{" &middot; blocking" if s.get("blocking") else ""}</span>'
        f'<h3>{esc(s["id"])}</h3>'
        f'<p>{esc(s["negative_controls"])} negative controls recorded. '
        f'<code>{esc(s["check"])}</code></p></article>'
        for s in data.get("sensors", [])
    )

    # Remediation, in the spec's order: security severity first, then the
    # ablation-derived sequence, then everything else. The floor is called out
    # wherever it lands, because closing it is the only work that moves overall.
    keys = [p["key"] for p in prims]
    risk = data.get("risk", "internal")
    todo = sorted(
        (p for p in prims if p["current"] < p["target"]),
        key=lambda p: remediation_rank(p["key"], keys, risk),
    )
    fixes = []
    for n, p in enumerate(todo, start=1):
        contract = contracts.get(p["key"], {})
        prompt = build_prompt(p, contract, project)
        is_floor = p.get("key") == floor_key
        why = (
            "Closing this is the only work in this list that raises the overall level."
            if is_floor
            else "Raises this layer. The overall level will not move until the floor does."
        )
        sev = (
            '<span class="sev">SECURITY SEVERITY</span>'
            if p["key"] == "execution_environment"
            else ""
        )
        fixes.append(
            f'<article class="fix">'
            f'<div class="fixhead"><div class="fixtitle">'
            f'<span class="seq">{n}</span>'
            f'<span class="name">{esc(p["name"])}</span>'
            f'<span class="move">{p["current"]} &rarr; {p["target"]}</span>{sev}</div>'
            f'<button class="copy" type="button" data-prompt="p{n}">Copy brief</button></div>'
            f'<p class="fixwhy">{esc(" ".join(str(p.get("gap") or "").split()))} {why}</p>'
            f'<details class="prompt"><summary>Show the brief</summary>'
            f'<pre id="p{n}">{esc(prompt)}</pre></details>'
            f"</article>"
        )

    floor_name = next((p["name"] for p in prims if p.get("key") == floor_key), floor_key)
    moved = [p for p in prims if p["current"] > p["baseline"]]
    short = [p for p in prims if p["current"] < p["target"]]

    movement = (
        f'{len(moved)} of twelve moved this pass ('
        + ", ".join(f'{esc(p["name"].lower())} {p["baseline"]} to {p["current"]}' for p in moved)
        + ")."
        if moved
        else "No primitive moved this pass."
    )

    return f"""<title>{esc(data.get("project"))} harness assessment</title>
<style>{CSS}</style>
<div class="wrap">
<header>
  <div>
    <p class="eyebrow">Agent harness maturity &middot; spec {esc(data.get("spec_version"))}</p>
    <h1>{esc(data.get("project"))}</h1>
    <p class="lede">{esc(data.get("description"))}</p>
  </div>
  <div class="masthead">
    <div class="score">
      <span class="n">{esc(current)}</span>
      <span class="of">/ 5</span>
      <span class="anchor">{esc(ANCHORS.get(current, ""))}</span>
    </div>
    <p class="eyebrow">assessed {esc(data.get("assessed"))}<br>{esc(data.get("assessor"))}</p>
  </div>
  <div class="floorcall">
    <p>The overall level is the <strong>minimum</strong> across applicable primitives,
    never the average. This system is a {esc(current)} because
    <strong>{esc(floor_name)}</strong> is a {esc(current)}. {esc(movement)}
    Averaging the twelve would report a
    {sum(p["current"] for p in prims) / len(prims):.1f}, and would be wrong.</p>
  </div>
</header>

<section>
  <h2>The twelve primitives</h2>
  <div class="legend">
    <span><i class="key f"></i>at baseline</span>
    <span><i class="key g"></i>gained this pass</span>
    <span><i class="key t"></i>target</span>
    <span><i class="chip sensor">sensor</i>enforced by the system</span>
    <span><i class="chip guide">guide</i>carried by discipline, caps at 3</span>
  </div>
  <div class="tablewrap">
    <table>
      <caption>Every score carries a path or an explicit statement of where the reviewer looked.
      A primitive carried only by a guide caps at 3, because a rule with nothing checking it is discipline.</caption>
      <thead><tr><th>#</th><th>Primitive</th><th>Control</th><th>Baseline &rarr; now / target</th><th>Status</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>Sensors added</h2>
  <p class="lede">A check that has never been observed failing has not been shown to be
  capable of failing. Each of these was deliberately broken and watched to go red.</p>
  <div class="cards">{sensors}</div>
</section>

<section>
  <h2>Still carried by a guide</h2>
  <p class="lede">{len(short)} rows sit short of target. Each names the check that would close it,
  marked in the instruction file so a scan reports it as a work item.</p>
  <div class="cards">{gaps}</div>
</section>

<section>
  <h2>Remediation</h2>
  <p class="lede">One brief per gap. Security severity first, then {"the trust layer, because this work is " + esc(risk).replace("_", " ") + " and capability without trust is a liability" if risk in ("client_facing", "regulated") else "tools, context, state and orchestration ahead of instruction, because the gain localises there rather than in the prompt"}.
  Each brief is plain text. Paste it into Claude Code, Codex, Cursor or a chat window unedited.</p>
  {"".join(fixes) if fixes else '<p class="lede">Every row is at target. Nothing to remediate.</p>'}
</section>

<footer>
  <p>Assessed against the
  <a href="https://github.com/Mariano215/agent-harness-maturity">Agent Harness Maturity Specification</a>
  {esc(data.get("spec_version"))}, remediated with
  <a href="https://github.com/Mariano215/harness-kit">harness-kit</a>
  contracts {esc(data.get("contracts_version"))}.</p>
  <p>Scores taken against a draft rubric are not comparable across time or across codebases.
  Generated from <code>harness/scores.yaml</code>.</p>
</footer>
</div>
<script>
// Copy the brief. Falls back to selecting the text when the clipboard API is
// unavailable, which it is on a plain file:// open in some browsers: better to
// hand the reader a selection than a button that silently does nothing.
document.querySelectorAll("button.copy").forEach(function (button) {{
  button.addEventListener("click", function () {{
    var pre = document.getElementById(button.dataset.prompt);
    if (!pre) return;
    var done = function (label) {{
      button.textContent = label;
      button.dataset.done = "1";
      setTimeout(function () {{
        button.textContent = "Copy brief";
        delete button.dataset.done;
      }}, 2000);
    }};
    var select = function () {{
      var details = pre.closest("details");
      if (details) details.open = true;
      var range = document.createRange();
      range.selectNodeContents(pre);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      done("Selected, press copy");
    }};
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(pre.textContent).then(function () {{
        done("Copied");
      }}, select);
    }} else {{
      select();
    }}
  }});
}});
</script>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=pathlib.Path, help="directory holding harness/scores.yaml")
    ap.add_argument("-o", "--out", type=pathlib.Path, help="output file (default: harness/report.html)")
    ap.add_argument(
        "--contracts",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent.parent / "contracts.yaml",
        help="harness-kit contracts.yaml, the source of the level-4 requirement in each brief",
    )
    ap.add_argument("--run-sensors", action="store_true",
                    help="execute each sensor's check as part of verification (runs commands from scores.yaml)")
    ap.add_argument("--force", action="store_true",
                    help="render even when verification fails. The page will be wrong; label it draft.")
    args = ap.parse_args()

    scores = args.project / "harness" / "scores.yaml"
    if not scores.exists():
        print(f"FAIL {scores} not found.", file=sys.stderr)
        print("     Step 5 of TRANSFORM.md writes it. Without it there is nothing to render.", file=sys.stderr)
        return 1

    data = yaml.safe_load(scores.read_text())
    count = len(data.get("primitives", []))
    if count != 12:
        print(f"FAIL {scores} has {count} primitives, expected 12.", file=sys.stderr)
        return 1

    if not args.contracts.exists():
        print(f"FAIL {args.contracts} not found.", file=sys.stderr)
        print("     The remediation briefs quote the contract's own level-4 text.", file=sys.stderr)
        print("     Point --contracts at harness-kit's contracts.yaml.", file=sys.stderr)
        return 1
    contracts_doc = yaml.safe_load(args.contracts.read_text())
    contracts = {c["key"]: c for c in contracts_doc.get("contracts", [])}

    # A stale scores.yaml renders a confident, wrong page with confident, wrong
    # work orders attached. Refuse rather than publish it.
    report = verify(args.project, data, contracts_doc, run=args.run_sensors)
    for w in report.warnings:
        print(w, file=sys.stderr)
    if not report.ok():
        for f in report.failures:
            print(f, file=sys.stderr)
        print(f"\nFAIL {len(report.failures)} problem(s) in scores.yaml. Nothing rendered.", file=sys.stderr)
        print("     Fix them, or pass --force to render anyway and label the result draft.", file=sys.stderr)
        if not args.force:
            return 1
        print("warn: rendering anyway because --force was passed.", file=sys.stderr)

    out = args.out or (args.project / "harness" / "report.html")
    out.write_text(render(data, contracts))

    briefs = args.project / "harness" / "remediation.md"
    todo = sorted(
        (p for p in data["primitives"] if p["current"] < p["target"]),
        key=lambda p: remediation_rank(
            p["key"], [x["key"] for x in data["primitives"]], data.get("risk", "internal")
        ),
    )
    briefs.write_text(
        f'# Remediation briefs: {data.get("project")}\n\n'
        "In the spec's remediation order. Each block is plain text, paste it into your\n"
        "agent unedited. Close one, prove it, then take the next.\n\n"
        + "\n\n".join(
            f'## {n}. {p["name"]} {p["current"]} to {p["target"]}\n\n```\n'
            f'{build_prompt(p, contracts.get(p["key"], {}), data.get("project", ""))}\n```'
            for n, p in enumerate(todo, start=1)
        )
        + "\n"
    )

    print(f"OK {out} ({out.stat().st_size // 1024}KB, self-contained)")
    print(f"OK {briefs} ({len(todo)} briefs, plain text)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
